# poller

[TOC]

### 总结

##### 协程等待IO就绪



##### IO就绪后

是谁在调用netpoll

### pollDesc 

net/fd_poll_runtime.go

pollDesc只是对runtime/netpoll.go 中定义的pollDesc的简单封装

~~~go
type pollDesc struct {
	runtimeCtx uintptr
}
~~~



##### pollDesc.init

net/fd_poll_runtime.go

* 调用runtime_pollServerInit(runtime/netpoll.go )初始化轮询器

~~~go
func (pd *pollDesc) init(fd *netFD) error {
	serverInit.Do(runtime_pollServerInit)
	ctx, errno := runtime_pollOpen(uintptr(fd.sysfd))
	runtime.KeepAlive(fd)
	if errno != 0 {
		return syscall.Errno(errno)
	}
	pd.runtimeCtx = ctx
	return nil
}
~~~



##### pollDesc.prepareRead

在读取IO数据前都会调用prepareRead

~~~go
func (pd *pollDesc) prepareRead() error {
	return pd.prepare('r')
}
~~~



##### pollDesc.prepare

~~~go
func (pd *pollDesc) prepare(mode int) error {
	res := runtime_pollReset(pd.runtimeCtx, mode)
	return convertErr(res)
}
~~~





##### pollDesc.waitRead 等待数据可读

net/fd_poll_runtime.go

~~~go
func (pd *pollDesc) waitRead() error {
	return pd.wait('r')
}
~~~



##### pollDesc.wait

[<sup>net_runtime_pollWait</sup>](#net_runtime_pollWait)

* 实际调用runtime.net_runtime_pollWait

~~~go

func (pd *pollDesc) wait(mode int) error {
	res := runtime_pollWait(pd.runtimeCtx, mode)
	return convertErr(res)
}
~~~



##### pollDesc.evict 调用conn.Close会执行到这里

~~~go
// Evict evicts fd from the pending list, unblocking any I/O running on fd.
func (pd *pollDesc) evict() {
	if pd.runtimeCtx == 0 {
		return
	}
	runtime_pollUnblock(pd.runtimeCtx)
}
~~~



##### pollDesc.close 会被谁调用

net/fd_poll_runtime.go

* netFD.destroy会调用pollDesc.close，谁又调用netFD.destroy。netFD.decref会调用

~~~go
func (pd *pollDesc) close() {
	if pd.runtimeCtx == 0 {
		return
	}
	runtime_pollClose(pd.runtimeCtx)
	pd.runtimeCtx = 0
}
~~~



##### convertErr

~~~go
func convertErr(res int) error {
	switch res {
	case 0:
		return nil
	case 1:
		return errClosing
	case 2:
		return errTimeout
	}
	println("unreachable: ", res)
	panic("unreachable")
}
~~~



### 位于runtime独立于平台的poller接口

runtime/netpoll.go



##### pollDesc的定义

~~~go
// Integrated network poller (platform-independent part).
// A particular implementation (epoll/kqueue) must define the following functions:
// func netpollinit()			// to initialize the poller
// func netpollopen(fd uintptr, pd *pollDesc) int32	// to arm edge-triggered notifications
// and associate fd with pd.
// An implementation must call the following function to denote that the pd is ready.
// func netpollready(gpp **g, pd *pollDesc, mode int32)

// pollDesc contains 2 binary semaphores, rg and wg, to park reader and writer
// goroutines respectively. The semaphore can be in the following states:
// pdReady - io readiness notification is pending;
//           a goroutine consumes the notification by changing the state to nil.
// pdWait - a goroutine prepares to park on the semaphore, but not yet parked;
//          the goroutine commits to park by changing the state to G pointer,
//          or, alternatively, concurrent io notification changes the state to READY,
//          or, alternatively, concurrent timeout/close changes the state to nil.
// G pointer - the goroutine is blocked on the semaphore;
//             io notification or timeout/close changes the state to READY or nil respectively
//             and unparks the goroutine.
// nil - nothing of the above.
const (
	pdReady uintptr = 1
	pdWait  uintptr = 2
)

const pollBlockSize = 4 * 1024

// Network poller descriptor.
//
// No heap pointers.
//
//go:notinheap
type pollDesc struct {
	link *pollDesc // in pollcache, protected by pollcache.lock

	// The lock protects pollOpen, pollSetDeadline, pollUnblock and deadlineimpl operations.
	// This fully covers seq, rt and wt variables. fd is constant throughout the PollDesc lifetime.
	// pollReset, pollWait, pollWaitCanceled and runtime·netpollready (IO readiness notification)
	// proceed w/o taking the lock. So closing, rg, rd, wg and wd are manipulated
	// in a lock-free way by all operations.
	// NOTE(dvyukov): the following code uses uintptr to store *g (rg/wg),
	// that will blow up when GC starts moving objects.
	lock    mutex // protects the following fields
	fd      uintptr
	closing bool
	seq     uintptr // protects from stale timers and ready notifications
    
    //rg 存储的值是pdReady, pdWait整形状态值或 g
	rg      uintptr // pdReady, pdWait, G waiting for read or nil
	rt      timer   // read deadline timer (set if rt.f != nil)
	rd      int64   // read deadline
	wg      uintptr // pdReady, pdWait, G waiting for write or nil
	wt      timer   // write deadline timer
	wd      int64   // write deadline
	user    uint32  // user settable cookie
}

type pollCache struct {
	lock  mutex
	first *pollDesc
	// PollDesc objects must be type-stable,
	// because we can get ready notification from epoll/kqueue
	// after the descriptor is closed/reused.
	// Stale notifications are detected using seq variable,
	// seq is incremented when deadlines are changed or descriptor is reused.
}

var (
	netpollInited uint32
	pollcache     pollCache
)
~~~



对每个新建的套接字，不论是监听套接字还是接收而来的套接字，都会调用一次runtime_pollOpen

#####  net_runtime_pollServerInit 调用平台的poller初始化接口，初始化poller

runtime/netpoll.go

* 调用netpollinit创建poller, netpollinit根据平台的不同实现不同

~~~go
//go:linkname net_runtime_pollServerInit net.runtime_pollServerInit
func net_runtime_pollServerInit() {
	netpollinit()
	atomic.Store(&netpollInited, 1)
}

func netpollinited() bool {
	return atomic.Load(&netpollInited) != 0
}


~~~



##### net_runtime_pollOpen 获取pollDesc并初始化

runtime/netpoll.go

* 调用pollcache.alloc分配pollDesc
* 初始化新分配的pollDesc
* 调用netpollopen,将`文件描述符`添加到epoll中

~~~go
//go:linkname net_runtime_pollOpen net.runtime_pollOpen
func net_runtime_pollOpen(fd uintptr) (*pollDesc, int) {
	pd := pollcache.alloc()
	lock(&pd.lock)
	if pd.wg != 0 && pd.wg != pdReady {
		throw("netpollOpen: blocked write on free descriptor")
	}
	if pd.rg != 0 && pd.rg != pdReady {
		throw("netpollOpen: blocked read on free descriptor")
	}
	pd.fd = fd
	pd.closing = false
	pd.seq++
	pd.rg = 0
	pd.rd = 0
	pd.wg = 0
	pd.wd = 0
	unlock(&pd.lock)

	var errno int32
	errno = netpollopen(fd, pd)
	return pd, int(errno)
}
~~~



##### net_runtime_pollReset

runtime/netpoll.go

~~~go
//go:linkname net_runtime_pollReset net.runtime_pollReset
func net_runtime_pollReset(pd *pollDesc, mode int) int {
	err := netpollcheckerr(pd, int32(mode))
	if err != 0 {
		return err
	}
	if mode == 'r' {
		pd.rg = 0
	} else if mode == 'w' {
		pd.wg = 0
	}
	return 0
}
~~~



##### net_runtime_pollClose 主动关闭

runtime/netpoll.go

~~~go
//go:linkname net_runtime_pollClose net.runtime_pollClose
func net_runtime_pollClose(pd *pollDesc) {
	if !pd.closing {
		throw("netpollClose: close w/o unblock")
	}
	if pd.wg != 0 && pd.wg != pdReady {
		throw("netpollClose: blocked write on closing descriptor")
	}
	if pd.rg != 0 && pd.rg != pdReady {
		throw("netpollClose: blocked read on closing descriptor")
	}
	netpollclose(pd.fd)
	pollcache.free(pd)
}
~~~



##### netpollcheckerr  检查pd是否关闭或超时

runtime/netpoll.go

* 超时后没有重置pd.rd，若后续也没有重置超时时间，则pd.rd会一直小于0。导致后续读取返回超时错误

~~~go
func netpollcheckerr(pd *pollDesc, mode int32) int {
	if pd.closing {
		return 1 // errClosing
	}
	if (mode == 'r' && pd.rd < 0) || (mode == 'w' && pd.wd < 0) {
		return 2 // errTimeout
	}
	return 0
}
~~~



#### 等待IO

##### net_runtime_pollWait

 <div id="net_runtime_pollWait"></div>

runtime/netpoll.go

* 调用netpollcheckerr
* 调用netpollblock, 若netpollblock返回false说明IO仍未就绪

~~~go
//go:linkname net_runtime_pollWait net.runtime_pollWait
func net_runtime_pollWait(pd *pollDesc, mode int) int {
	err := netpollcheckerr(pd, int32(mode))
	if err != 0 {
		return err
	}
	// As for now only Solaris uses level-triggered IO.
	if GOOS == "solaris" {
		netpollarm(pd, mode)
	}
    //netpollblock说明IO仍未就绪
	for !netpollblock(pd, int32(mode), false) {
		err = netpollcheckerr(pd, int32(mode))
		if err != 0 {
			return err
		}
		// Can happen if timeout has fired and unblocked us,
		// but before we had a chance to run, timeout has been reset.
		// Pretend it has not happened and retry.
	}
	return 0
}
~~~



##### netpollblock 使协程进入等待

runtime/netpoll.go

返回值：

* 返回true, 若IO就绪
* 返回false，若超时或文件描述符被关闭



执行过程：

* 设置pd的状态为pdWait
* <font color="red">若waitio是true,或netpollcheckerr返回0，则进入等待状态。进入等待状态时,pd.rg或pd.wg保存了指向当前协程的g结构体的指针</font>
* 被唤醒后，检查pd的状态

~~~go
// returns true if IO is ready, or false if timedout or closed
// waitio - wait only for completed IO, ignore errors
func netpollblock(pd *pollDesc, mode int32, waitio bool) bool {
	gpp := &pd.rg
	if mode == 'w' {
		gpp = &pd.wg
	}

	// set the gpp semaphore to WAIT
	for {
		old := *gpp
        //IO是否就绪,可读或可写
		if old == pdReady {
			*gpp = 0
			return true
		}
		if old != 0 {
			throw("netpollblock: double wait")
		}
        //再次检查状态, CAS 若内存位置的值和指定的值一样，则将内存位置的值替换为新值，并返回内存位置现在的值
        //若gpp原值是0，则新值是pdWait.就会跳出循环
        //若gpp原值不是0，则原值保持不变，也会跳出循环
		if atomic.Casuintptr(gpp, 0, pdWait) {
			break
		}
	}

	// need to recheck error states after setting gpp to WAIT
	// this is necessary because runtime_pollUnblock/runtime_pollSetDeadline/deadlineimpl
	// do the opposite: store to closing/rd/wd, membarrier, load of rg/wg
    //若pd已经被关闭，则netpollcheckerr返回1，超时返回2，否则返回0
	if waitio || netpollcheckerr(pd, mode) == 0 {
		gopark(netpollblockcommit, unsafe.Pointer(gpp), "IO wait", traceEvGoBlockNet, 5)
	}
	// be careful to not lose concurrent READY notification
	old := atomic.Xchguintptr(gpp, 0)
	if old > pdWait {
		throw("netpollblock: corrupted state")
	}
	return old == pdReady
}
~~~



##### netpollblockcommit

~~~go
func netpollblockcommit(gp *g, gpp unsafe.Pointer) bool {
	return atomic.Casuintptr((*uintptr)(gpp), pdWait, uintptr(unsafe.Pointer(gp)))
}
~~~



#### IO就绪



##### netpollready 就绪1-获取IO就绪的协程

* 调用netpollunblock

runtime/netpoll.go

~~~go
// make pd ready, newly runnable goroutines (if any) are returned in rg/wg
// May run during STW, so write barriers are not allowed.
//go:nowritebarrier
func netpollready(gpp *guintptr, pd *pollDesc, mode int32) {
	var rg, wg guintptr
	if mode == 'r' || mode == 'r'+'w' {
		rg.set(netpollunblock(pd, 'r', true))
	}
	if mode == 'w' || mode == 'r'+'w' {
		wg.set(netpollunblock(pd, 'w', true))
	}
	if rg != 0 {
		rg.ptr().schedlink = *gpp
		*gpp = rg
	}
	if wg != 0 {
		wg.ptr().schedlink = *gpp
		*gpp = wg
	}
}
~~~



##### netpollunblock 使等待IO的协程就绪

* 若协程处于等待读的状态，则pd.rg保存的是指向g的指针

runtime/netpoll.go

~~~go
func netpollunblock(pd *pollDesc, mode int32, ioready bool) *g {
	gpp := &pd.rg
	if mode == 'w' {
		gpp = &pd.wg
	}

	for {
		old := *gpp
        //若pd.rg指向等待的协程的g,则不满足这
		if old == pdReady {
			return nil
		}
        //不满足
		if old == 0 && !ioready {
			// Only set READY for ioready. runtime_pollWait
			// will check for timeout/cancel before waiting.
			return nil
		}
		var new uintptr
       
		if ioready {
			new = pdReady
		}
		if atomic.Casuintptr(gpp, old, new) {
			if old == pdReady || old == pdWait {
				old = 0
			}
			return (*g)(unsafe.Pointer(old))
		}
	}
}
~~~



#### 设置超时时间

##### net_runtime_pollSetDeadline 设置读写的超时时间

参数:

* d 以纳秒为单位的绝对时间

runtime/netpoll.go

* 加锁,pd.lock

* 检查pd是否被关闭,若被关闭，立即返回
* 增加定时器使用的序列号,取消之前设置定时器

* <font color="red">若超时时间是未来的某个时间，调用addtimer添加定时器到定时器队列</font>
* <font color="red">若设置的超时时间是过去的某个时间点，则调用netpollunblock唤醒等待的协程</font>

疑问: 只设置读取的超时时间，为何会重置写入的超时时间

~~~go
//go:linkname net_runtime_pollSetDeadline net.runtime_pollSetDeadline
func net_runtime_pollSetDeadline(pd *pollDesc, d int64, mode int) {
	lock(&pd.lock)
	if pd.closing {
		unlock(&pd.lock)
		return
	}
	pd.seq++ // invalidate current timers
	// Reset current timers.
	if pd.rt.f != nil {
		deltimer(&pd.rt)
		pd.rt.f = nil
	}
    //只设置读取的超时时间，为何要重置写入的超时设置
	if pd.wt.f != nil {
		deltimer(&pd.wt)
		pd.wt.f = nil
	}
	// Setup new timers.
	if d != 0 && d <= nanotime() {
		d = -1
	}
	if mode == 'r' || mode == 'r'+'w' {
		pd.rd = d
	}
	if mode == 'w' || mode == 'r'+'w' {
		pd.wd = d
	}
    //mode 是r + w 才会导致pd.rd == pd.wd
	if pd.rd > 0 && pd.rd == pd.wd {
		pd.rt.f = netpollDeadline
		pd.rt.when = pd.rd
		// Copy current seq into the timer arg.
		// Timer func will check the seq against current descriptor seq,
		// if they differ the descriptor was reused or timers were reset.
		pd.rt.arg = pd
		pd.rt.seq = pd.seq
		addtimer(&pd.rt)
	} else {
		if pd.rd > 0 {
			pd.rt.f = netpollReadDeadline
			pd.rt.when = pd.rd
			pd.rt.arg = pd
			pd.rt.seq = pd.seq
			addtimer(&pd.rt)
		}
		if pd.wd > 0 {
			pd.wt.f = netpollWriteDeadline
			pd.wt.when = pd.wd
			pd.wt.arg = pd
			pd.wt.seq = pd.seq
			addtimer(&pd.wt)
		}
	}
	// If we set the new deadline in the past, unblock currently pending IO if any.
	var rg, wg *g
	atomicstorep(unsafe.Pointer(&wg), nil) // full memory barrier between stores to rd/wd and load of rg/wg in netpollunblock
	if pd.rd < 0 {
		rg = netpollunblock(pd, 'r', false)
	}
	if pd.wd < 0 {
		wg = netpollunblock(pd, 'w', false)
	}
	unlock(&pd.lock)
	if rg != nil {
		goready(rg, 3)
	}
	if wg != nil {
		goready(wg, 3)
	}
}
~~~



##### netpollReadDeadline 超时后调用此函数

runtime/netpoll.go

~~~go
func netpollReadDeadline(arg interface{}, seq uintptr) {
	netpolldeadlineimpl(arg.(*pollDesc), seq, true, false)
}
~~~



##### netpolldeadlineimpl 就绪等待IO的协程

runtime/netpoll.go

* 根据定时器的序列，检查该定时器是否是过时的

~~~go
func netpolldeadlineimpl(pd *pollDesc, seq uintptr, read, write bool) {
	lock(&pd.lock)
	// Seq arg is seq when the timer was set.
	// If it's stale, ignore the timer event.
	if seq != pd.seq {
		// The descriptor was reused or timers were reset.
		unlock(&pd.lock)
		return
	}
	var rg *g
	if read {
		if pd.rd <= 0 || pd.rt.f == nil {
			throw("netpolldeadlineimpl: inconsistent read deadline")
		}
		pd.rd = -1
		atomicstorep(unsafe.Pointer(&pd.rt.f), nil) // full memory barrier between store to rd and load of rg in netpollunblock
		rg = netpollunblock(pd, 'r', false)
	}
	var wg *g
	if write {
		if pd.wd <= 0 || pd.wt.f == nil && !read {
			throw("netpolldeadlineimpl: inconsistent write deadline")
		}
		pd.wd = -1
		atomicstorep(unsafe.Pointer(&pd.wt.f), nil) // full memory barrier between store to wd and load of wg in netpollunblock
		wg = netpollunblock(pd, 'w', false)
	}
	unlock(&pd.lock)
	if rg != nil {
		goready(rg, 0)
	}
	if wg != nil {
		goready(wg, 0)
	}
}
~~~



##### net_runtime_pollUnblock 

runtime/netpoll.go

netFD被关闭时会调用此函数

* 若已经被关闭，则报错
* 设置pd.closing并增加序列号
* 删除读/写设置的超时定时器
* 唤醒正在等待的协程

~~~go
//go:linkname net_runtime_pollUnblock net.runtime_pollUnblock
func net_runtime_pollUnblock(pd *pollDesc) {
	lock(&pd.lock)
	if pd.closing {
		throw("netpollUnblock: already closing")
	}
	pd.closing = true
	pd.seq++
	var rg, wg *g
	atomicstorep(unsafe.Pointer(&rg), nil) // full memory barrier between store to closing and read of rg/wg in netpollunblock
	rg = netpollunblock(pd, 'r', false)
	wg = netpollunblock(pd, 'w', false)
	if pd.rt.f != nil {
		deltimer(&pd.rt)
		pd.rt.f = nil
	}
	if pd.wt.f != nil {
		deltimer(&pd.wt)
		pd.wt.f = nil
	}
	unlock(&pd.lock)
	if rg != nil {
		goready(rg, 3)
	}
	if wg != nil {
		goready(wg, 3)
	}
}
~~~









### pollCache



##### pollCache.alloc

~~~go
func (c *pollCache) alloc() *pollDesc {
	lock(&c.lock)
	if c.first == nil {
		const pdSize = unsafe.Sizeof(pollDesc{})
		n := pollBlockSize / pdSize
		if n == 0 {
			n = 1
		}
		// Must be in non-GC memory because can be referenced
		// only from epoll/kqueue internals.
		mem := persistentalloc(n*pdSize, 0, &memstats.other_sys)
		for i := uintptr(0); i < n; i++ {
			pd := (*pollDesc)(add(mem, i*pdSize))
			pd.link = c.first
			c.first = pd
		}
	}
	pd := c.first
	c.first = pd.link
	unlock(&c.lock)
	return pd
}
~~~



### epoll



##### netpollinit 创建epoll使用的文件描述符

runtime/netpoll_epoll.go

~~~go
func netpollinit() {
	epfd = epollcreate1(_EPOLL_CLOEXEC)
	if epfd >= 0 {
		return
	}
	epfd = epollcreate(1024)
	if epfd >= 0 {
		closeonexec(epfd)
		return
	}
	println("netpollinit: failed to create epoll descriptor", -epfd)
	throw("netpollinit: failed to create descriptor")
}
~~~



##### netpollopen

runtime/netpoll_epoll.go

~~~go
func netpollopen(fd uintptr, pd *pollDesc) int32 {
	var ev epollevent
	ev.events = _EPOLLIN | _EPOLLOUT | _EPOLLRDHUP | _EPOLLET
	*(**pollDesc)(unsafe.Pointer(&ev.data)) = pd
	return -epollctl(epfd, _EPOLL_CTL_ADD, int32(fd), &ev)
}
~~~



##### netpoll 轮询IO事件

runtime/netpoll_epoll.go

* 是谁在调用netpoll轮询， findrunnable 会调用netpoll(false)
* 调用netpollready 将IO就绪的协程放入单链表，然后返回此单链表

~~~go
// polls for ready network connections
// returns list of goroutines that become runnable
func netpoll(block bool) *g {
	if epfd == -1 {
		return nil
	}
	waitms := int32(-1)
	if !block {
		waitms = 0
	}
	var events [128]epollevent
retry:
	n := epollwait(epfd, &events[0], int32(len(events)), waitms)
	if n < 0 {
		if n != -_EINTR {
			println("runtime: epollwait on fd", epfd, "failed with", -n)
			throw("epollwait failed")
		}
		goto retry
	}
	var gp guintptr
	for i := int32(0); i < n; i++ {
		ev := &events[i]
		if ev.events == 0 {
			continue
		}
		var mode int32
		if ev.events&(_EPOLLIN|_EPOLLRDHUP|_EPOLLHUP|_EPOLLERR) != 0 {
			mode += 'r'
		}
		if ev.events&(_EPOLLOUT|_EPOLLHUP|_EPOLLERR) != 0 {
			mode += 'w'
		}
		if mode != 0 {
			pd := *(**pollDesc)(unsafe.Pointer(&ev.data))

			netpollready(&gp, pd, mode)
		}
	}
	if block && gp == 0 {
		goto retry
	}
	return gp.ptr()
}

~~~

