# tcp out of memory

[TOC]

最近去客户排查一个前端页面加载特别慢的问题，一个几百kB的js文件需要2分钟左右。系统负载、内存、cpu、磁盘io都比较正常。最终从/var/log/messages看到 TCP: out of memory。查看/proc/net/sockstat  TCP 内存消耗已经到40G。将net.ipv4.tcp_mem的最大值设置为50G，解决了这个问题。但未能排查到是哪个docker 服务或tcp连接消耗了如此多的内存。同事后面通过找到哪个进程占用了最多的socket，找到了目标进程(这些socket已经处于关闭状态，使用ss或nestat命令看不到)

系统中所有的tcp连接(包含docker服务使用的)数量在4000左右

系统tcp配置如下:

~~~
net.ipv4.tcp_wmem = 4096 12582912 16777216
net.ipv4.tcp_rmem = 4096 12582912 16777216
~~~



疑问:

* net.ipv4.tcp_wmem、tcp_rmem的默认值导致的tcp_mem消耗高么
* 如何统计每个tcp的连接的内存消耗



查看系统tcp 消耗的内存:

~~~bash
cat /proc/net/sockstat
sockets: used 196
TCP: inuse 4 orphan 0 tw 0 alloc 7 mem 1
UDP: inuse 4 mem 1
UDPLITE: inuse 0
RAW: inuse 12
FRAG: inuse 0 memory 0

~~~





## 内核中tcp内存计数器

tcp消耗的内存保存在tcp_prot.tcp_memory_allocated中

tcp_prot的定义如下(net/ipv4/tcp_ipv4.c)

~~~c
struct proto tcp_prot = {
	.name			= "TCP",
	.owner			= THIS_MODULE,
	.close			= tcp_close,
	.pre_connect		= tcp_v4_pre_connect,
	.connect		= tcp_v4_connect,
	.disconnect		= tcp_disconnect,
	.accept			= inet_csk_accept,
	.ioctl			= tcp_ioctl,
	.init			= tcp_v4_init_sock,
	.destroy		= tcp_v4_destroy_sock,
	.shutdown		= tcp_shutdown,
	.setsockopt		= tcp_setsockopt,
	.getsockopt		= tcp_getsockopt,
	.keepalive		= tcp_set_keepalive,
	.recvmsg		= tcp_recvmsg,
	.sendmsg		= tcp_sendmsg,
	.sendpage		= tcp_sendpage,
	.backlog_rcv		= tcp_v4_do_rcv,
	.release_cb		= tcp_release_cb,
	.hash			= inet_hash,
	.unhash			= inet_unhash,
	.get_port		= inet_csk_get_port,
	.enter_memory_pressure	= tcp_enter_memory_pressure,
	.leave_memory_pressure	= tcp_leave_memory_pressure,
	.stream_memory_free	= tcp_stream_memory_free,
	.sockets_allocated	= &tcp_sockets_allocated,
	.orphan_count		= &tcp_orphan_count,
	.memory_allocated	= &tcp_memory_allocated,
	.memory_pressure	= &tcp_memory_pressure,
	.sysctl_mem		= sysctl_tcp_mem,
	.sysctl_wmem_offset	= offsetof(struct net, ipv4.sysctl_tcp_wmem),
	.sysctl_rmem_offset	= offsetof(struct net, ipv4.sysctl_tcp_rmem),
	.max_header		= MAX_TCP_HEADER,
	.obj_size		= sizeof(struct tcp_sock),
	.slab_flags		= SLAB_TYPESAFE_BY_RCU,
	.twsk_prot		= &tcp_timewait_sock_ops,
	.rsk_prot		= &tcp_request_sock_ops,
	.h.hashinfo		= &tcp_hashinfo,
	.no_autobind		= true,
#ifdef CONFIG_COMPAT
	.compat_setsockopt	= compat_tcp_setsockopt,
	.compat_getsockopt	= compat_tcp_getsockopt,
#endif
	.diag_destroy		= tcp_abort,
};
~~~



~~~c
static inline long
sk_memory_allocated(const struct sock *sk)
{
	return atomic_long_read(sk->sk_prot->memory_allocated);
}

static inline long
sk_memory_allocated_add(struct sock *sk, int amt)
{
	return atomic_long_add_return(amt, sk->sk_prot->memory_allocated);
}

static inline void
sk_memory_allocated_sub(struct sock *sk, int amt)
{
	atomic_long_sub(amt, sk->sk_prot->memory_allocated);
}

~~~



tcp内存消耗是否进入压力模式可以查看/proc/net/snmp TCPMemoryPressures





sock使用的内存

~~~c
	struct sock{
	socket_lock_t		sk_lock;
	atomic_t		sk_drops;
	int			sk_rcvlowat;
	struct sk_buff_head	sk_error_queue;
	struct sk_buff		*sk_rx_skb_cache;
	struct sk_buff_head	sk_receive_queue;
	/*
	 * The backlog queue is special, it is always used with
	 * the per-socket spinlock held and requires low latency
	 * access. Therefore we special case it's implementation.
	 * Note : rmem_alloc is in this structure to fill a hole
	 * on 64bit arches, not because its logically part of
	 * backlog.
	 */
	struct {
		atomic_t	rmem_alloc;
		int		len;
		struct sk_buff	*head;
		struct sk_buff	*tail;
	} sk_backlog;
#define sk_rmem_alloc sk_backlog.rmem_alloc

	int			sk_forward_alloc;
#ifdef CONFIG_NET_RX_BUSY_POLL
	unsigned int		sk_ll_usec;
	/* ===== mostly read cache line ===== */
	unsigned int		sk_napi_id;
#endif
	int			sk_rcvbuf;
	int			sk_wait_pending;

	struct sk_filter __rcu	*sk_filter;
	union {
		struct socket_wq __rcu	*sk_wq;
		struct socket_wq	*sk_wq_raw;
	};
#ifdef CONFIG_XFRM
	struct xfrm_policy __rcu *sk_policy[2];
#endif
	struct dst_entry __rcu	*sk_rx_dst;
	struct dst_entry __rcu	*sk_dst_cache;
	atomic_t		sk_omem_alloc;
	int			sk_sndbuf;

	/* ===== cache line for TX ===== */
	int			sk_wmem_queued;
	refcount_t		sk_wmem_alloc;
	unsigned long		sk_tsq_flags;
	union {
		struct sk_buff	*sk_send_head;
		struct rb_root	tcp_rtx_queue;
	};
~~~





~~~
struct sock {
    ...
    atomic_t        sk_rmem_alloc;    // r: 接收内存分配
    int             sk_rcvbuf;        // rb: 接收缓冲区大小
    atomic_t        sk_wmem_alloc;    // t: 发送内存分配  
    int             sk_sndbuf;        // tb: 发送缓冲区大小
    int             sk_forward_alloc; // f: 预分配内存
    struct sk_buff_head sk_write_queue; // w: 写队列内存
    unsigned long   sk_optmem;        // o: 选项内存
    struct sk_buff_head sk_backlog;   // bl: backlog队列
    atomic_t        sk_drops;         // d: 丢包计数
    ...
};
~~~



## 找到占用socket最多的进程



~~~bash
find /proc/*/fd -lname 'socket:*' 2>/dev/null | awk -F'/' '{print $3}' | sort | uniq -c | sort -rn | head -10 | awk '{printf "PID: %-10s Socket数: %s\n", $2, $1}'
~~~



## ss命令

ss -s 可以查看socket统计信息，其中很重要的一项是已经关闭，但未释放的socket的数目

~~~
Total: 122554 (kernel 128020)
TCP:   112519 (estab 5, closed 84147, orphaned 0, synrecv 0, timewait 22969/0), ports 0

Transport Total     IP        IPv6
*	  128020    -         -        
RAW	  1         0         1        
UDP	  63        34        29       
TCP	  28372     28307     65       
INET	  28436     28341     95       
FRAG	  0         0         0
~~~

ss -s 中的 closed 是指处于 CLOSED 状态的 TCP socket，还未被释放。

具体来说：

CLOSED 状态：TCP 四次挥手完成后进入此状态，连接逻辑上已结束，但内核的 socket 结构体 (struct sock) 尚未被销毁，仍占用内存
真正释放：需要应用层调用 close() / shutdown() 后，内核引用计数归零，才会调用 sk_free() 真正回收内存
常见导致 closed socket 堆积的原因：

应用程序没有及时 close() 文件描述符
TIME_WAIT 快速回收后残留
内核延迟回收（如 tcp_fin_timeout 超时未到）



ss 工具通过 NETLINK socket (特别是 SOCK_DIAG 协议) 从内核获取这些信息：

用户空间：ss → NETLINK_SOCK_DIAG
内核空间：net/ipv4/tcp_diag.c 或 net/core/sock_diag.c
数据填充：内核函数如 tcp_diag_get_info() 从 struct sock 读取并返回

3. skmem 字段含义

skmem:(r<rmem_alloc>,rb<rcv_buf>,t<wmem_alloc>,tb<snd_buf>,       f<fwd_alloc>,w<wmem_queued>,o<opt_mem>,bl<back_log>,d<sock_drop>)
r (rmem_alloc): 已为接收分配的内存
rb (rcv_buf): 接收缓冲区总大小 (sk_rcvbuf)
t (wmem_alloc): 已为发送分配的内存 (已发送到 L3 层)
tb (snd_buf): 发送缓冲区总大小 (sk_sndbuf)
f (fwd_alloc): socket 预分配的缓存内存
w (wmem_queued): 写队列中的内存
o (opt_mem): socket 选项占用的内存
bl (back_log): backlog 队列内存
d (sock_drop): socket 丢包计数





net/core/sock.c - sock 内存管理
net/ipv4/tcp.c - TCP socket 内存操作
net/ipv4/tcp_diag.c - TCP 诊断接口
include/uapi/linux/sock_diag.h - 用户空间接口定义