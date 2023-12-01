# cstream parser

[TOC]

stream parser可使用两种类型ebpf程序: BPF_PROG_TYPE_SK_MSG、BPF_PROG_TYPE_SK_SKB

## 挂载

挂载到类型为`BPF_MAP_TYPE_SOCKMAP`  或 `BPF_MAP_TYPE_SOCKHASH` 的map的fd上。可使用的挂载类型为:



| 类型                 | 挂载类型                                                | SEC    | 描述                    |
| -------------------- | ------------------------------------------------------- | ------ | ----------------------- |
| BPF_PROG_TYPE_SK_MSG | BPF_SK_MSG_VERDICT                                      | 无要求 | sendmsg、sendpage时调用 |
| BPF_PROG_TYPE_SK_SKB | BPF_SK_SKB_STREAM_PARSER<br />BPF_SK_SKB_STREAM_VERDICT | 无要求 | recvmsg时调用           |
|                      |                                                         |        |                         |

BPF_SK_SKB_VERDICT 5.4内核不支持

注意：

<font color='red'>不允许用户将`stream_verdict` and `skb_verdict` 程序挂载到同一个map.</font>

挂载到map上的ebpf程序是何时被触发执行的？？？ 内核树中net/ipv4/tcp_bpf.c中或许有答案



### 内核中的挂载流程

以下代码均出自于内核5.4

bpf_prog_attach （kernel/bpf/syscall.c ）中挂载BPF_PROG_TYPE_SK_SKB、BPF_PROG_TYPE_SK_MSG类型的的ebpf程序的代码片段

![image-20231129135218655](D:\个人笔记\doc\ebpf\stream parser.assets\image-20231129135218655.png)

#### sock_map_get_from_fd 根据map的fd获取map

~~~c
int sock_map_get_from_fd(const union bpf_attr *attr, struct bpf_prog *prog)
{
	u32 ufd = attr->target_fd;
	struct bpf_map *map;
	struct fd f;
	int ret;

	f = fdget(ufd);
	map = __bpf_map_get(f);
	if (IS_ERR(map))
		return PTR_ERR(map);
	ret = sock_map_prog_update(map, prog, NULL, attr->attach_type);
	fdput(f);
	return ret;
}
~~~



### sock_map_prog_update

sock_map_prog_update定义在内核树net/core/sock_map.c中, sock_map_prog_update用于将ebpf程序设置到结构体sk_psock_progs对应的成员中

~~~c

struct sk_psock_progs {
	struct bpf_prog			*msg_parser;
	struct bpf_prog			*skb_parser;
	struct bpf_prog			*skb_verdict;
};

static struct sk_psock_progs *sock_map_progs(struct bpf_map *map)
{
    //container_of 用于根据结构体成员地址，获取结构体的地址
	switch (map->map_type) {
	case BPF_MAP_TYPE_SOCKMAP:
		return &container_of(map, struct bpf_stab, map)->progs;
	case BPF_MAP_TYPE_SOCKHASH:
		return &container_of(map, struct bpf_htab, map)->progs;
	default:
		break;
	}
	return NULL;
}


int sock_map_prog_update(struct bpf_map *map, struct bpf_prog *prog,
			 struct bpf_prog *old, u32 which)
{
	struct sk_psock_progs *progs = sock_map_progs(map);
	struct bpf_prog **pprog;

	if (!progs)
		return -EOPNOTSUPP;

	switch (which) {
	case BPF_SK_MSG_VERDICT:
		pprog = &progs->msg_parser;
		break;
	case BPF_SK_SKB_STREAM_PARSER:
		pprog = &progs->skb_parser;
		break;
	case BPF_SK_SKB_STREAM_VERDICT:
		pprog = &progs->skb_verdict;
		break;
	default:
		return -EOPNOTSUPP;
	}

	if (old)
		return psock_replace_prog(pprog, prog, old);

	psock_set_prog(pprog, prog);
	return 0;
}

~~~

## 内核依赖

- `BPF_MAP_TYPE_SOCKMAP` was introduced in kernel version 4.14
- `BPF_MAP_TYPE_SOCKHASH` was introduced in kernel version 4.18

## 代码示例

### BPF_PROG_TYPE_SK_SKB

~~~c
SEC("sk_skb2")
int bpf_prog2(struct __sk_buff *skb)
{
        __u32 lport = skb->local_port;
        __u32 rport = skb->remote_port;
        int len, *f, ret, zero = 0;
        __u64 flags = 0;

        if (lport == 10000)
                ret = 10;
        else
                ret = 1;

        len = (__u32)skb->data_end - (__u32)skb->data;
        f = bpf_map_lookup_elem(&sock_skb_opts, &zero);
        if (f && *f) {
                ret = 3;
                flags = *f;
        }

        bpf_printk("sk_skb2: redirect(%iB) flags=%i\n",
                   len, flags);
#ifdef SOCKMAP
        return bpf_sk_redirect_map(skb, &sock_map, ret, flags);
#else
        return bpf_sk_redirect_hash(skb, &sock_map, &ret, flags);
#endif

}

~~~



### BPF_PROG_TYPE_SK_MSG

~~~c
SEC("sk_msg1")
int bpf_prog4(struct sk_msg_md *msg)
{
	int *bytes, zero = 0, one = 1, two = 2, three = 3, four = 4, five = 5;
	int *start, *end, *start_push, *end_push, *start_pop, *pop;

	bpf_printk("sk_msg1 pf_prog4\n");
	bytes = bpf_map_lookup_elem(&sock_apply_bytes, &zero);
	if (bytes)
		bpf_msg_apply_bytes(msg, *bytes);
	bytes = bpf_map_lookup_elem(&sock_cork_bytes, &zero);
	if (bytes)
		bpf_msg_cork_bytes(msg, *bytes);
	start = bpf_map_lookup_elem(&sock_bytes, &zero);
	end = bpf_map_lookup_elem(&sock_bytes, &one);
	if (start && end)
		bpf_msg_pull_data(msg, *start, *end, 0);
	start_push = bpf_map_lookup_elem(&sock_bytes, &two);
	end_push = bpf_map_lookup_elem(&sock_bytes, &three);
	if (start_push && end_push)
		bpf_msg_push_data(msg, *start_push, *end_push, 0);
	start_pop = bpf_map_lookup_elem(&sock_bytes, &four);
	pop = bpf_map_lookup_elem(&sock_bytes, &five);
	if (start_pop && pop)
		bpf_msg_pop_data(msg, *start_pop, *pop, 0);
	return SK_PASS;
}
~~~



### 内核中代码示例分析

tools/testing/selftests/bpf/test_sockmap_kern.h

~~~c
struct {
	__uint(type, TEST_MAP_TYPE);
	__uint(max_entries, 20);
	__uint(key_size, sizeof(int));
	__uint(value_size, sizeof(int));
} sock_map SEC(".maps");

struct {
	__uint(type, TEST_MAP_TYPE);
	__uint(max_entries, 20);
	__uint(key_size, sizeof(int));
	__uint(value_size, sizeof(int));
} sock_map_txmsg SEC(".maps");

struct {
	__uint(type, TEST_MAP_TYPE);
	__uint(max_entries, 20);
	__uint(key_size, sizeof(int));
	__uint(value_size, sizeof(int));
} sock_map_redir SEC(".maps");

struct {
	__uint(type, BPF_MAP_TYPE_ARRAY);
	__uint(max_entries, 1);
	__type(key, int);
	__type(value, int);
} sock_apply_bytes SEC(".maps");

struct {
	__uint(type, BPF_MAP_TYPE_ARRAY);
	__uint(max_entries, 1);
	__type(key, int);
	__type(value, int);
} sock_cork_bytes SEC(".maps");

struct {
	__uint(type, BPF_MAP_TYPE_ARRAY);
	__uint(max_entries, 6);
	__type(key, int);
	__type(value, int);
} sock_bytes SEC(".maps");

struct {
	__uint(type, BPF_MAP_TYPE_ARRAY);
	__uint(max_entries, 1);
	__type(key, int);
	__type(value, int);
} sock_redir_flags SEC(".maps");

struct {
	__uint(type, BPF_MAP_TYPE_ARRAY);
	__uint(max_entries, 1);
	__type(key, int);
	__type(value, int);
} sock_skb_opts SEC(".maps");


//应用程序将bpf_prg1 挂载到sock_map
SEC("sk_skb1")
int bpf_prog1(struct __sk_buff *skb)
{
	return skb->len;
}

//应用程序将bpf_prog2 挂载到sock_map
SEC("sk_skb2")
int bpf_prog2(struct __sk_buff *skb)
{
	__u32 lport = skb->local_port;
	__u32 rport = skb->remote_port;
	int len, *f, ret, zero = 0;
	__u64 flags = 0;

    //本地端口10000， 是服务端监听端口
	if (lport == 10000)
		ret = 10;
	else
		ret = 1;

	len = (__u32)skb->data_end - (__u32)skb->data;
	f = bpf_map_lookup_elem(&sock_skb_opts, &zero);
	if (f && *f) {
		ret = 3;
		flags = *f;
	}

	bpf_printk("sk_skb2: redirect(%iB) flags=%i\n",
		   len, flags);
#ifdef SOCKMAP
	return bpf_sk_redirect_map(skb, &sock_map, ret, flags);
#else
	return bpf_sk_redirect_hash(skb, &sock_map, &ret, flags);
#endif

}

SEC("sockops")
int bpf_sockmap(struct bpf_sock_ops *skops)
{
	__u32 lport, rport;
	int op, err = 0, index, key, ret;


	op = (int) skops->op;

	switch (op) {
	case BPF_SOCK_OPS_PASSIVE_ESTABLISHED_CB:
		lport = skops->local_port;
		rport = skops->remote_port;

		if (lport == 10000) {
			ret = 1;
#ifdef SOCKMAP
			err = bpf_sock_map_update(skops, &sock_map, &ret,
						  BPF_NOEXIST);
#else
			err = bpf_sock_hash_update(skops, &sock_map, &ret,
						   BPF_NOEXIST);
#endif
			bpf_printk("passive(%i -> %i) map ctx update err: %d\n",
				   lport, bpf_ntohl(rport), err);
		}
		break;
	case BPF_SOCK_OPS_ACTIVE_ESTABLISHED_CB:
		lport = skops->local_port;
		rport = skops->remote_port;

		if (bpf_ntohl(rport) == 10001) {
			ret = 10;
#ifdef SOCKMAP
			err = bpf_sock_map_update(skops, &sock_map, &ret,
						  BPF_NOEXIST);
#else
			err = bpf_sock_hash_update(skops, &sock_map, &ret,
						   BPF_NOEXIST);
#endif
			bpf_printk("active(%i -> %i) map ctx update err: %d\n",
				   lport, bpf_ntohl(rport), err);
		}
		break;
	default:
		break;
	}

	return 0;
}

~~~



~~~c
SEC("sk_msg1")
int bpf_prog4(struct sk_msg_md *msg)
{
	int *bytes, zero = 0, one = 1, two = 2, three = 3, four = 4, five = 5;
	int *start, *end, *start_push, *end_push, *start_pop, *pop;

	bytes = bpf_map_lookup_elem(&sock_apply_bytes, &zero);
	if (bytes)
		bpf_msg_apply_bytes(msg, *bytes);
	bytes = bpf_map_lookup_elem(&sock_cork_bytes, &zero);
	if (bytes)
		bpf_msg_cork_bytes(msg, *bytes);
	start = bpf_map_lookup_elem(&sock_bytes, &zero);
	end = bpf_map_lookup_elem(&sock_bytes, &one);
	if (start && end)
		bpf_msg_pull_data(msg, *start, *end, 0);
	start_push = bpf_map_lookup_elem(&sock_bytes, &two);
	end_push = bpf_map_lookup_elem(&sock_bytes, &three);
	if (start_push && end_push)
		bpf_msg_push_data(msg, *start_push, *end_push, 0);
	start_pop = bpf_map_lookup_elem(&sock_bytes, &four);
	pop = bpf_map_lookup_elem(&sock_bytes, &five);
	if (start_pop && pop)
		bpf_msg_pop_data(msg, *start_pop, *pop, 0);
	return SK_PASS;
}

~~~



应用程序分别在10000、10001端口开启服务。各有一个客户端连接到这两个端口。 c1 和10000端口服务建立连接。 c2和10001端口建立连接



## 内核中帮助函数实现

### BPF_MAP_TYPE_SOCKMAP 

BPF_MAP_TYPE_SOCKMAP类型map对应的操作都定义在net/core/sock_map.c文件中。以下是sock_map_ops的定义

~~~c
const struct bpf_map_ops sock_map_ops = {
	.map_alloc		= sock_map_alloc,
	.map_free		= sock_map_free,
	.map_get_next_key	= sock_map_get_next_key,
	.map_update_elem	= sock_map_update_elem,
	.map_delete_elem	= sock_map_delete_elem,
	.map_lookup_elem	= sock_map_lookup,
	.map_release_uref	= sock_map_release_progs,
	.map_check_btf		= map_check_no_btf,
};

~~~

### bpf_msg_xxxx_bytes的实现

5.4内核树net/core/filter.c

~~~c
BPF_CALL_2(bpf_msg_apply_bytes, struct sk_msg *, msg, u32, bytes)
{
	msg->apply_bytes = bytes;
	return 0;
}

static const struct bpf_func_proto bpf_msg_apply_bytes_proto = {
	.func           = bpf_msg_apply_bytes,
	.gpl_only       = false,
	.ret_type       = RET_INTEGER,
	.arg1_type	= ARG_PTR_TO_CTX,
	.arg2_type      = ARG_ANYTHING,
};

BPF_CALL_2(bpf_msg_cork_bytes, struct sk_msg *, msg, u32, bytes)
{
	msg->cork_bytes = bytes;
	return 0;
}
static const struct bpf_func_proto bpf_msg_cork_bytes_proto = {
	.func           = bpf_msg_cork_bytes,
	.gpl_only       = false,
	.ret_type       = RET_INTEGER,
	.arg1_type	= ARG_PTR_TO_CTX,
	.arg2_type      = ARG_ANYTHING,
};
~~~

### sock map的更新

sock map的更新可以使用bpf_sock_map_update、bpf_map_update_elem。二者最终都会调用sock_map_update_common(非helper函数)。两种方式的使用时机略有区别，流程图如下:

![image-20231130170321821](D:\个人笔记\doc\ebpf\stream parser.assets\image-20231130170321821.png)



#### sock_map_sk_update_elem

~~~c
static bool sock_map_sk_is_suitable(const struct sock *sk)
{
	return sk->sk_type == SOCK_STREAM &&
	       sk->sk_protocol == IPPROTO_TCP;
}

static int sock_map_update_elem(struct bpf_map *map, void *key,
				void *value, u64 flags)
{
	u32 ufd = *(u32 *)value;
	u32 idx = *(u32 *)key;
	struct socket *sock;
	struct sock *sk;
	int ret;

	sock = sockfd_lookup(ufd, &ret);
	if (!sock)
		return ret;
	sk = sock->sk;
	if (!sk) {
		ret = -EINVAL;
		goto out;
	}
	if (!sock_map_sk_is_suitable(sk)) {
		ret = -EOPNOTSUPP;
		goto out;
	}

	sock_map_sk_acquire(sk);
	if (sk->sk_state != TCP_ESTABLISHED)
		ret = -EOPNOTSUPP;
	else
		ret = sock_map_update_common(map, idx, sk, flags);
	sock_map_sk_release(sk);
out:
	fput(sock->file);
	return ret;
}
~~~

#### sock_map_update_common

net/cor/sock_map.c

~~~c

struct bpf_stab {
	struct bpf_map map;
	struct sock **sks;
	struct sk_psock_progs progs;
	raw_spinlock_t lock;
};

struct sk_psock_link {
	struct list_head		list;
	struct bpf_map			*map;
	void				*link_raw;
};

//include/linux/skmsg.h 
struct sk_psock {
	struct sock			*sk;
	struct sock			*sk_redir;
	u32				apply_bytes;
	u32				cork_bytes;
	u32				eval;
	struct sk_msg			*cork;
	struct sk_psock_progs		progs;
	struct sk_psock_parser		parser;
	struct sk_buff_head		ingress_skb;
	struct list_head		ingress_msg;
	unsigned long			state;
	struct list_head		link;
	spinlock_t			link_lock;
	refcount_t			refcnt;
	void (*saved_unhash)(struct sock *sk);
	void (*saved_close)(struct sock *sk, long timeout);
	void (*saved_write_space)(struct sock *sk);
	struct proto			*sk_proto;
	struct sk_psock_work_state	work_state;
	struct work_struct		work;
	union {
		struct rcu_head		rcu;
		struct work_struct	gc;
	};
};

static int sock_map_update_common(struct bpf_map *map, u32 idx,
				  struct sock *sk, u64 flags)
{
	struct bpf_stab *stab = container_of(map, struct bpf_stab, map);
	struct inet_connection_sock *icsk = inet_csk(sk);
	struct sk_psock_link *link;
	struct sk_psock *psock;
	struct sock *osk;
	int ret;

	WARN_ON_ONCE(!rcu_read_lock_held());
	if (unlikely(flags > BPF_EXIST))
		return -EINVAL;
	if (unlikely(idx >= map->max_entries))
		return -E2BIG;
	if (unlikely(rcu_access_pointer(icsk->icsk_ulp_data)))
		return -EINVAL;

	link = sk_psock_init_link();
	if (!link)
		return -ENOMEM;

	ret = sock_map_link(map, &stab->progs, sk);
	if (ret < 0)
		goto out_free;

	psock = sk_psock(sk);
	WARN_ON_ONCE(!psock);

	raw_spin_lock_bh(&stab->lock);
	osk = stab->sks[idx];
	if (osk && flags == BPF_NOEXIST) {
		ret = -EEXIST;
		goto out_unlock;
	} else if (!osk && flags == BPF_EXIST) {
		ret = -ENOENT;
		goto out_unlock;
	}

	sock_map_add_link(psock, link, map, &stab->sks[idx]);
	stab->sks[idx] = sk;
	if (osk)
		sock_map_unref(osk, &stab->sks[idx]);
	raw_spin_unlock_bh(&stab->lock);
	return 0;
out_unlock:
	raw_spin_unlock_bh(&stab->lock);
	if (psock)
		sk_psock_put(sk, psock);
out_free:
	sk_psock_free_link(link);
	return ret;
}
~~~

### BPF_PROG_TYPE_SK_MSG执行时机

tcp_bpf_send_verdict(net/ipv4/tcp_bpf.c)调用sk_psock_msg_verdict

~~~c
int sk_psock_msg_verdict(struct sock *sk, struct sk_psock *psock,
			 struct sk_msg *msg)
{
	struct bpf_prog *prog;
	int ret;

	preempt_disable();
	rcu_read_lock();
	prog = READ_ONCE(psock->progs.msg_parser);
	if (unlikely(!prog)) {
		ret = __SK_PASS;
		goto out;
	}

	sk_msg_compute_data_pointers(msg);
	msg->sk = sk;
	ret = BPF_PROG_RUN(prog, msg);
	ret = sk_psock_map_verd(ret, msg->sk_redir);
	psock->apply_bytes = msg->apply_bytes;
	if (ret == __SK_REDIRECT) {
		if (psock->sk_redir)
			sock_put(psock->sk_redir);
		psock->sk_redir = msg->sk_redir;
		if (!psock->sk_redir) {
			ret = __SK_DROP;
			goto out;
		}
		sock_hold(psock->sk_redir);
	}
out:
	rcu_read_unlock();
	preempt_enable();
	return ret;
}
~~~

### BPF_PROG_TYPE_SK_SKB 执行时机

BPF_PROG_TYPE_SK_SKB类型ebpf程序的执行时机，大致如下图所示。涉及到的几个关键函数在后面给出

<img src="D:\个人笔记\doc\ebpf\stream parser.assets\image-20231201173310154.png" alt="image-20231201173310154"  />

主要涉及到的内核源文件(net/core/skmsg.c、net/strparser/strparser.c 5.4内核)

#### sk_psock_init_strp

~~~c
int sk_psock_init_strp(struct sock *sk, struct sk_psock *psock)
{
	static const struct strp_callbacks cb = {
		.rcv_msg	= sk_psock_strp_read,
		.read_sock_done	= sk_psock_strp_read_done,
		.parse_msg	= sk_psock_strp_parse,
	};

	psock->parser.enabled = false;
	return strp_init(&psock->parser.strp, sk, &cb);
}
~~~

#### strp_init

~~~c
int strp_init(struct strparser *strp, struct sock *sk,
	      const struct strp_callbacks *cb)
{

	.....

	strp->sk = sk;

	strp->cb.lock = cb->lock ? : strp_sock_lock;
	strp->cb.unlock = cb->unlock ? : strp_sock_unlock;
	strp->cb.rcv_msg = cb->rcv_msg;
	strp->cb.parse_msg = cb->parse_msg;
	strp->cb.read_sock_done = cb->read_sock_done ? : default_read_sock_done;
	strp->cb.abort_parser = cb->abort_parser ? : strp_abort_strp;
	......
	return 0;
}
~~~

#### sk_psock_start_strp

~~~c
void sk_psock_start_strp(struct sock *sk, struct sk_psock *psock)
{
	struct sk_psock_parser *parser = &psock->parser;

	if (parser->enabled)
		return;

	parser->saved_data_ready = sk->sk_data_ready;
	sk->sk_data_ready = sk_psock_strp_data_ready;
	sk->sk_write_space = sk_psock_write_space;
	parser->enabled = true;
}

~~~

#### sk_psock_strp_data_ready

~~~c
static void sk_psock_strp_data_ready(struct sock *sk)
{
	struct sk_psock *psock;

	rcu_read_lock();
	psock = sk_psock(sk);
	if (likely(psock)) {
		if (tls_sw_has_ctx_rx(sk)) {
			psock->parser.saved_data_ready(sk);
		} else {
			write_lock_bh(&sk->sk_callback_lock);
			strp_data_ready(&psock->parser.strp);
			write_unlock_bh(&sk->sk_callback_lock);
		}
	}
	rcu_read_unlock();
}

~~~

#### sk_psock_bpf_run 执行ebpf程序

~~~c
static int sk_psock_bpf_run(struct sk_psock *psock, struct bpf_prog *prog,
			    struct sk_buff *skb)
{
	int ret;

	skb->sk = psock->sk;
	bpf_compute_data_end_sk_skb(skb);
	preempt_disable();
	ret = BPF_PROG_RUN(prog, skb);
	preempt_enable();
	/* strparser clones the skb before handing it to a upper layer,
	 * meaning skb_orphan has been called. We NULL sk on the way out
	 * to ensure we don't trigger a BUG_ON() in skb/sk operations
	 * later and because we are not charging the memory of this skb
	 * to any socket yet.
	 */
	skb->sk = NULL;
	return ret;
}

~~~

#### sk_psock_tls_strp_read

~~~c
int sk_psock_tls_strp_read(struct sk_psock *psock, struct sk_buff *skb)
{
	struct bpf_prog *prog;
	int ret = __SK_PASS;

	rcu_read_lock();
	prog = READ_ONCE(psock->progs.skb_verdict);
	if (likely(prog)) {
		tcp_skb_bpf_redirect_clear(skb);
		ret = sk_psock_bpf_run(psock, prog, skb);
		ret = sk_psock_map_verd(ret, tcp_skb_bpf_redirect_fetch(skb));
	}
	sk_psock_tls_verdict_apply(skb, ret);
	rcu_read_unlock();
	return ret;
}
~~~

#### sk_psock_strp_read

~~~c
static void sk_psock_strp_read(struct strparser *strp, struct sk_buff *skb)
{
	struct sk_psock *psock;
	struct bpf_prog *prog;
	int ret = __SK_DROP;
	struct sock *sk;

	rcu_read_lock();
	sk = strp->sk;
	psock = sk_psock(sk);
	if (unlikely(!psock)) {
		kfree_skb(skb);
		goto out;
	}
	prog = READ_ONCE(psock->progs.skb_verdict);
	if (likely(prog)) {
		skb_orphan(skb);
		tcp_skb_bpf_redirect_clear(skb);
		ret = sk_psock_bpf_run(psock, prog, skb);
		ret = sk_psock_map_verd(ret, tcp_skb_bpf_redirect_fetch(skb));
	}
	sk_psock_verdict_apply(psock, skb, ret);
out:
	rcu_read_unlock();
}
~~~



#### sk_psock_strp_parse

~~~c
static int sk_psock_strp_parse(struct strparser *strp, struct sk_buff *skb)
{
	struct sk_psock *psock = sk_psock_from_strp(strp);
	struct bpf_prog *prog;
	int ret = skb->len;

	rcu_read_lock();
	prog = READ_ONCE(psock->progs.skb_parser);
	if (likely(prog))
		ret = sk_psock_bpf_run(psock, prog, skb);
	rcu_read_unlock();
	return ret;
}
~~~



## 注意

BPF_PROG_TYPE_SK_MSG、BPF_PROG_TYPE_SK_SKB对文件ebpf中的文件的SEC没有要求

## xx

~~~
BPF_SK_SKB_STREAM_VERDICT
~~~



## 参考

* https://blogs.oracle.com/linux/post/bpf-a-tour-of-program-types
* https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/configuring_and_managing_networking/assembly_understanding-the-ebpf-features-in-rhel-8_configuring-and-managing-networking
* BPF_MAP_TYPE_SOCKMAP https://www.kernel.org/doc/html/latest/bpf/map_sockmap.html
* https://lwn.net/Articles/748628/
* 5.4 内核 tools/testing/selftests/bpf/test_sockmap_kern.h、test_sockmap.c

