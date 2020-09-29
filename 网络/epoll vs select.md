# epoll vs select

[TOC]



很久没接触linux kernel，都不知道select和epoll的源代码所在的文件了。经过一番搜索找到其在arch/x86/ia32/sys_ia32.c文件。很多次被问到二者的区别，因为一直没去阅读源码，所以不甚清楚

## select

~~~c
#define __COMPAT_NFDBITS       (8 * sizeof(compat_ulong_t))
~~~



### compat_get_fd_set 拷贝文件描述符

~~~c
/*
 * Ooo, nasty.  We need here to frob 32-bit unsigned longs to
 * 64-bit unsigned longs.
 */
static
int compat_get_fd_set(unsigned long nr, compat_ulong_t __user *ufdset,
			unsigned long *fdset)
{
	nr = DIV_ROUND_UP(nr, __COMPAT_NFDBITS);
	if (ufdset) {
		unsigned long odd;

		if (!access_ok(VERIFY_WRITE, ufdset, nr*sizeof(compat_ulong_t)))
			return -EFAULT;

		odd = nr & 1UL;
        //1UL取反 
		nr &= ~1UL;
		while (nr) {
			unsigned long h, l;
			if (__get_user(l, ufdset) || __get_user(h, ufdset+1))
				return -EFAULT;
			ufdset += 2;
			*fdset++ = h << 32 | l;
			nr -= 2;
		}
		if (odd && __get_user(*fdset, ufdset))
			return -EFAULT;
	} else {
		/* Tricky, must clear full unsigned long in the
		 * kernel fdset at the end, this makes sure that
		 * actually happens.
		 */
		memset(fdset, 0, ((nr + 1) & ~1)*sizeof(compat_ulong_t));
	}
	return 0;
}

~~~



### compat_set_fd_set

~~~c
static
int compat_set_fd_set(unsigned long nr, compat_ulong_t __user *ufdset,
		      unsigned long *fdset)
{
	unsigned long odd;
	nr = DIV_ROUND_UP(nr, __COMPAT_NFDBITS);

	if (!ufdset)
		return 0;

	odd = nr & 1UL;
	nr &= ~1UL;
	while (nr) {
		unsigned long h, l;
		l = *fdset++;
		h = l >> 32;
		if (__put_user(l, ufdset) || __put_user(h, ufdset+1))
			return -EFAULT;
		ufdset += 2;
		nr -= 2;
	}
	if (odd && __put_user(*fdset, ufdset))
		return -EFAULT;
	return 0;
}

~~~



### sys32_old_select 入口

sys32_old_select定义在sys_ia32.c文件中，主要做了以下两件事：

* 将用户态的函数参数拷贝到内核态
* 调用compac_sys_select

~~~c
struct sel_arg_struct {
	unsigned int n;
	unsigned int inp;
	unsigned int outp;
	unsigned int exp;
	unsigned int tvp;
};


asmlinkage long
sys32_old_select (struct sel_arg_struct __user *arg)
{
	struct sel_arg_struct a;

	if (copy_from_user(&a, arg, sizeof(a)))
		return -EFAULT;
	return compat_sys_select(a.n, compat_ptr(a.inp), compat_ptr(a.outp),
				 compat_ptr(a.exp), compat_ptr(a.tvp));
}
~~~



### compact_sys_select

compact_sys_select定义在fs/compact.c文件中。

* 若设置了超时时间，则调用poll_select_set_timeout
* 调用compat_core_sys_select 处理`文件描述符集合`
* 调用poll_select_copy_remaining 处理超时时间



~~~c
asmlinkage long compat_sys_select(int n, compat_ulong_t __user *inp,
	compat_ulong_t __user *outp, compat_ulong_t __user *exp,
	struct compat_timeval __user *tvp)
{
	struct timespec end_time, *to = NULL;
	struct compat_timeval tv;
	int ret;

	if (tvp) {
		if (copy_from_user(&tv, tvp, sizeof(tv)))
			return -EFAULT;

		to = &end_time;
		if (poll_select_set_timeout(to,
				tv.tv_sec + (tv.tv_usec / USEC_PER_SEC),
				(tv.tv_usec % USEC_PER_SEC) * NSEC_PER_USEC))
			return -EINVAL;
	}

	ret = compat_core_sys_select(n, inp, outp, exp, to);
	ret = poll_select_copy_remaining(&end_time, tvp, 1, ret);

	return ret;
}

~~~



### compat_core_sys_select

~~~c
#define FRONTEND_STACK_ALLOC	256
#define SELECT_STACK_ALLOC	FRONTEND_STACK_ALLOC


int compat_core_sys_select(int n, compat_ulong_t __user *inp,
	compat_ulong_t __user *outp, compat_ulong_t __user *exp,
	struct timespec *end_time)
{
	fd_set_bits fds;
	void *bits;
	int size, max_fds, ret = -EINVAL;
	struct fdtable *fdt;
    //SELECT_STACK_ALLOC定义在include/linux/poll.h中，其值是256
    //stack_fds是大小为32或64的long型数组。可容纳2048个位
	long stack_fds[SELECT_STACK_ALLOC/sizeof(long)];

	if (n < 0)
		goto out_nofds;

	/* max_fds can increase, so grab it once to avoid race */
	rcu_read_lock();
	fdt = files_fdtable(current->files);
	max_fds = fdt->max_fds;
	rcu_read_unlock();
	if (n > max_fds)
		n = max_fds;

	/*
	 * We need 6 bitmaps (in/out/ex for both incoming and outgoing),
	 * since we used fdset we need to allocate memory in units of
	 * long-words.
	 */
    //FDS_BYTES确定需要几个LONG型，方可容纳描述符n
	size = FDS_BYTES(n);
	bits = stack_fds;
    //stack_fds是否足够6个size
    //为什么需要6个,虽然上面有注释。但不明白,继续往下看
    //三个用于保存从用户态空间传来的文件描述符集合
    //额外三个用于保存满足条件的文件描述符集合
    //完事之后，再将满足条件的文件描述符集合拷贝到对应的用户态参数
	if (size > sizeof(stack_fds) / 6) {
		bits = kmalloc(6 * size, GFP_KERNEL);
		ret = -ENOMEM;
		if (!bits)
			goto out_nofds;
	}
	fds.in      = (unsigned long *)  bits;
	fds.out     = (unsigned long *) (bits +   size);
	fds.ex      = (unsigned long *) (bits + 2*size);
	fds.res_in  = (unsigned long *) (bits + 3*size);
	fds.res_out = (unsigned long *) (bits + 4*size);
	fds.res_ex  = (unsigned long *) (bits + 5*size);

	if ((ret = compat_get_fd_set(n, inp, fds.in)) ||
	    (ret = compat_get_fd_set(n, outp, fds.out)) ||
	    (ret = compat_get_fd_set(n, exp, fds.ex)))
		goto out;
	zero_fd_set(n, fds.res_in);
	zero_fd_set(n, fds.res_out);
	zero_fd_set(n, fds.res_ex);

	ret = do_select(n, &fds, end_time);

	if (ret < 0)
		goto out;
	if (!ret) {
		ret = -ERESTARTNOHAND;
		if (signal_pending(current))
			goto out;
		ret = 0;
	}

	if (compat_set_fd_set(n, inp, fds.res_in) ||
	    compat_set_fd_set(n, outp, fds.res_out) ||
	    compat_set_fd_set(n, exp, fds.res_ex))
		ret = -EFAULT;
out:
	if (bits != stack_fds)
		kfree(bits);
out_nofds:
	return ret;
}

~~~



### poll_select_coty_remaining(fs/select.c) 处理剩余的超时时间

~~~c
static int poll_select_copy_remaining(struct timespec *end_time, void __user *p,
				      int timeval, int ret)
{
	struct timespec rts;
	struct timeval rtv;

	if (!p)
		return ret;

	if (current->personality & STICKY_TIMEOUTS)
		goto sticky;

	/* No update for zero timeout */
	if (!end_time->tv_sec && !end_time->tv_nsec)
		return ret;

	ktime_get_ts(&rts);
	rts = timespec_sub(*end_time, rts);
	if (rts.tv_sec < 0)
		rts.tv_sec = rts.tv_nsec = 0;

	if (timeval) {
		rtv.tv_sec = rts.tv_sec;
		rtv.tv_usec = rts.tv_nsec / NSEC_PER_USEC;

		if (!copy_to_user(p, &rtv, sizeof(rtv)))
			return ret;

	} else if (!copy_to_user(p, &rts, sizeof(rts)))
		return ret;

	/*
	 * If an application puts its timeval in read-only memory, we
	 * don't want the Linux-specific update to the timeval to
	 * cause a fault after the select has completed
	 * successfully. However, because we're not updating the
	 * timeval, we can't restart the system call.
	 */

sticky:
	if (ret == -ERESTARTNOHAND)
		ret = -EINTR;
	return ret;
}

~~~





### do_select 核心

fs/select.c

* 依次对`文件描述符集合`的文件描述符，获取文件file句柄，然后获取文件的操作集合f_op。

* 调用f_op->poll，对于网络链接的文件描述符， f_op定义在net/socket.c。poll的实现为sock_poll


~~~c
int do_select(int n, fd_set_bits *fds, struct timespec *end_time)
{
	ktime_t expire, *to = NULL;
	struct poll_wqueues table;
	poll_table *wait;
	int retval, i, timed_out = 0;
	unsigned long slack = 0;

	rcu_read_lock();
	retval = max_select_fd(n, fds);
	rcu_read_unlock();

	if (retval < 0)
		return retval;
	n = retval;

	poll_initwait(&table);
	wait = &table.pt;
    //超时时间设置的是0，立即返回
	if (end_time && !end_time->tv_sec && !end_time->tv_nsec) {
		wait = NULL;
		timed_out = 1;
	}
	//大于0的超时时间
	if (end_time && !timed_out)
		slack = estimate_accuracy(end_time);

	retval = 0;
	for (;;) {
		unsigned long *rinp, *routp, *rexp, *inp, *outp, *exp;
		//格式有所调整
		inp = fds->in; 
        outp = fds->out;
        exp = fds->ex;
        
		rinp = fds->res_in; 
        routp = fds->res_out;
        rexp = fds->res_ex;

		for (i = 0; i < n; ++rinp, ++routp, ++rexp) {
            //bit =1
			unsigned long in, out, ex, all_bits, bit = 1, mask, j;
			unsigned long res_in = 0, res_out = 0, res_ex = 0;
			const struct file_operations *f_op = NULL;
			struct file *file = NULL;

            //合并三个文件描述符集合
			in = *inp++;
            out = *outp++;
            ex = *exp++;
			all_bits = in | out | ex;
            //当前的long型没有文件描述符，转到下一个
			if (all_bits == 0) {
				i += __NFDBITS;
				continue;
			}

			for (j = 0; j < __NFDBITS; ++j, ++i, bit <<= 1) {
				int fput_needed;
				if (i >= n)
					break;
                //bit 初始化为1，然后通过依次左移位，来检查all_bits中的位
				if (!(bit & all_bits))
					continue;
				file = fget_light(i, &fput_needed);
				if (file) {
					f_op = file->f_op;
					mask = DEFAULT_POLLMASK;
					if (f_op && f_op->poll)
						mask = (*f_op->poll)(file, retval ? NULL : wait);
					fput_light(file, fput_needed);
					if ((mask & POLLIN_SET) && (in & bit)) {
						res_in |= bit;
						retval++;
					}
					if ((mask & POLLOUT_SET) && (out & bit)) {
						res_out |= bit;
						retval++;
					}
					if ((mask & POLLEX_SET) && (ex & bit)) {
						res_ex |= bit;
						retval++;
					}
				}
			}
			if (res_in)
				*rinp = res_in;
			if (res_out)
				*routp = res_out;
			if (res_ex)
				*rexp = res_ex;
			cond_resched();
		}
		wait = NULL;
		if (retval || timed_out || signal_pending(current))
			break;
		if (table.error) {
			retval = table.error;
			break;
		}

		/*
		 * If this is the first loop and we have a timeout
		 * given, then we convert to ktime_t and set the to
		 * pointer to the expiry value.
		 */
		if (end_time && !to) {
			expire = timespec_to_ktime(*end_time);
			to = &expire;
		}

		if (!poll_schedule_timeout(&table, TASK_INTERRUPTIBLE,
					   to, slack))
			timed_out = 1;
	}

	poll_freewait(&table);

	return retval;
}
~~~



### sock_poll

net/socket.c

* 调用sock->ops->poll， 若是TCP链接,sock->ops的值为inet_stream_ops(定义在net/ipv4/af_inet.c)，那么poll的值就是tcp_poll；若是UDP链接，sock->ops的值为inet_dgram_ops(定义在net/ipv4/af_inet.c)，那么poll的值是udp_poll

~~~c
/* No kernel lock held - perfect */
static unsigned int sock_poll(struct file *file, poll_table *wait)
{
	struct socket *sock;

	/*
	 *      We can't return errors to poll, so it's either yes or no.
	 */
	sock = file->private_data;
	return sock->ops->poll(file, sock, wait);
}
~~~



## epoll

fs/eventpoll.c



### 系统调用部分



### epoll_create1

~~~c
/*
 * Open an eventpoll file descriptor.
 */
SYSCALL_DEFINE1(epoll_create1, int, flags)
{
	int error, fd = -1;
	struct eventpoll *ep;

	/* Check the EPOLL_* constant for consistency.  */
	BUILD_BUG_ON(EPOLL_CLOEXEC != O_CLOEXEC);

	if (flags & ~EPOLL_CLOEXEC)
		return -EINVAL;

	DNPRINTK(3, (KERN_INFO "[%p] eventpoll: sys_epoll_create(%d)\n",
		     current, flags));

	/*
	 * Create the internal data structure ( "struct eventpoll" ).
	 */
	error = ep_alloc(&ep);
	if (error < 0) {
		fd = error;
		goto error_return;
	}

	/*
	 * Creates all the items needed to setup an eventpoll file. That is,
	 * a file structure and a free file descriptor.
	 */
	fd = anon_inode_getfd("[eventpoll]", &eventpoll_fops, ep,
			      flags & O_CLOEXEC);
	if (fd < 0)
		ep_free(ep);

error_return:
	DNPRINTK(3, (KERN_INFO "[%p] eventpoll: sys_epoll_create(%d) = %d\n",
		     current, flags, fd));

	return fd;
}
~~~



#### epoll_create

~~~c
SYSCALL_DEFINE1(epoll_create, int, size)
{
	if (size <= 0)
		return -EINVAL;

	return sys_epoll_create1(0);
}
~~~





#### epoll_ctl

~~~c
/*
 * The following function implements the controller interface for
 * the eventpoll file that enables the insertion/removal/change of
 * file descriptors inside the interest set.
 */
SYSCALL_DEFINE4(epoll_ctl, int, epfd, int, op, int, fd,
		struct epoll_event __user *, event)
{
	int error;
	struct file *file, *tfile;
	struct eventpoll *ep;
	struct epitem *epi;
	struct epoll_event epds;

	DNPRINTK(3, (KERN_INFO "[%p] eventpoll: sys_epoll_ctl(%d, %d, %d, %p)\n",
		     current, epfd, op, fd, event));

	error = -EFAULT;
	if (ep_op_has_event(op) &&
	    copy_from_user(&epds, event, sizeof(struct epoll_event)))
		goto error_return;

	/* Get the "struct file *" for the eventpoll file */
	error = -EBADF;
	file = fget(epfd);
	if (!file)
		goto error_return;

	/* Get the "struct file *" for the target file */
	tfile = fget(fd);
	if (!tfile)
		goto error_fput;

	/* The target file descriptor must support poll */
	error = -EPERM;
	if (!tfile->f_op || !tfile->f_op->poll)
		goto error_tgt_fput;

	/*
	 * We have to check that the file structure underneath the file descriptor
	 * the user passed to us _is_ an eventpoll file. And also we do not permit
	 * adding an epoll file descriptor inside itself.
	 */
	error = -EINVAL;
	if (file == tfile || !is_file_epoll(file))
		goto error_tgt_fput;

	/*
	 * At this point it is safe to assume that the "private_data" contains
	 * our own data structure.
	 */
	ep = file->private_data;

	mutex_lock(&ep->mtx);

	/*
	 * Try to lookup the file inside our RB tree, Since we grabbed "mtx"
	 * above, we can be sure to be able to use the item looked up by
	 * ep_find() till we release the mutex.
	 */
	epi = ep_find(ep, tfile, fd);

	error = -EINVAL;
	switch (op) {
	case EPOLL_CTL_ADD:
		if (!epi) {
			epds.events |= POLLERR | POLLHUP;

			error = ep_insert(ep, &epds, tfile, fd);
		} else
			error = -EEXIST;
		break;
	case EPOLL_CTL_DEL:
		if (epi)
			error = ep_remove(ep, epi);
		else
			error = -ENOENT;
		break;
	case EPOLL_CTL_MOD:
		if (epi) {
			epds.events |= POLLERR | POLLHUP;
			error = ep_modify(ep, epi, &epds);
		} else
			error = -ENOENT;
		break;
	}
	mutex_unlock(&ep->mtx);

error_tgt_fput:
	fput(tfile);
error_fput:
	fput(file);
error_return:
	DNPRINTK(3, (KERN_INFO "[%p] eventpoll: sys_epoll_ctl(%d, %d, %d, %p) = %d\n",
		     current, epfd, op, fd, event, error));

	return error;
}


~~~



#### epoll_wait和 epoll_pwait

~~~c
/*
 * Implement the event wait interface for the eventpoll file. It is the kernel
 * part of the user space epoll_wait(2).
 */
SYSCALL_DEFINE4(epoll_wait, int, epfd, struct epoll_event __user *, events,
		int, maxevents, int, timeout)
{
	int error;
	struct file *file;
	struct eventpoll *ep;

	DNPRINTK(3, (KERN_INFO "[%p] eventpoll: sys_epoll_wait(%d, %p, %d, %d)\n",
		     current, epfd, events, maxevents, timeout));

	/* The maximum number of event must be greater than zero */
	if (maxevents <= 0 || maxevents > EP_MAX_EVENTS)
		return -EINVAL;

	/* Verify that the area passed by the user is writeable */
	if (!access_ok(VERIFY_WRITE, events, maxevents * sizeof(struct epoll_event))) {
		error = -EFAULT;
		goto error_return;
	}

	/* Get the "struct file *" for the eventpoll file */
	error = -EBADF;
	file = fget(epfd);
	if (!file)
		goto error_return;

	/*
	 * We have to check that the file structure underneath the fd
	 * the user passed to us _is_ an eventpoll file.
	 */
	error = -EINVAL;
	if (!is_file_epoll(file))
		goto error_fput;

	/*
	 * At this point it is safe to assume that the "private_data" contains
	 * our own data structure.
	 */
	ep = file->private_data;

	/* Time to fish for events ... */
	error = ep_poll(ep, events, maxevents, timeout);

error_fput:
	fput(file);
error_return:
	DNPRINTK(3, (KERN_INFO "[%p] eventpoll: sys_epoll_wait(%d, %p, %d, %d) = %d\n",
		     current, epfd, events, maxevents, timeout, error));

	return error;
}

#ifdef HAVE_SET_RESTORE_SIGMASK

/*
 * Implement the event wait interface for the eventpoll file. It is the kernel
 * part of the user space epoll_pwait(2).
 */
SYSCALL_DEFINE6(epoll_pwait, int, epfd, struct epoll_event __user *, events,
		int, maxevents, int, timeout, const sigset_t __user *, sigmask,
		size_t, sigsetsize)
{
	int error;
	sigset_t ksigmask, sigsaved;

	/*
	 * If the caller wants a certain signal mask to be set during the wait,
	 * we apply it here.
	 */
	if (sigmask) {
		if (sigsetsize != sizeof(sigset_t))
			return -EINVAL;
		if (copy_from_user(&ksigmask, sigmask, sizeof(ksigmask)))
			return -EFAULT;
		sigdelsetmask(&ksigmask, sigmask(SIGKILL) | sigmask(SIGSTOP));
		sigprocmask(SIG_SETMASK, &ksigmask, &sigsaved);
	}

	error = sys_epoll_wait(epfd, events, maxevents, timeout);

	/*
	 * If we changed the signal mask, we need to restore the original one.
	 * In case we've got a signal while waiting, we do not restore the
	 * signal mask yet, and we allow do_signal() to deliver the signal on
	 * the way back to userspace, before the signal mask is restored.
	 */
	if (sigmask) {
		if (error == -EINTR) {
			memcpy(&current->saved_sigmask, &sigsaved,
			       sizeof(sigsaved));
			set_restore_sigmask();
		} else
			sigprocmask(SIG_SETMASK, &sigsaved, NULL);
	}

	return error;
}

#endif /* HAVE_SET_RESTORE_SIGMASK */

~~~



### epoll内部实现



## 总结

select:

* 无论是在用户态还是在内核态，为检查满足条件的`文件描述符`，都需要扫描整个`文件描述符集合`,时间复杂度O(n)。这就导致了效率低

epoll:



## 参考

* linux-2.6.29.4