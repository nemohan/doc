# tracepoint

[TOC]



## 可用的程序类型

| 程序类型                               | 挂载点 | SEC                             |      |
| -------------------------------------- | ------ | ------------------------------- | ---- |
| BPF_PROG_TYPE_TRACEPOINT               |        | tracepoint/<category>/name      |      |
| BPF_PROG_TYPE_RAW_TRACEPOINT           |        | raw_tracepoint[.w]/<tracepoint> |      |
| BPF_PROG_TYPE_RAW_TRACEPOINT_WRITEABLE |        | raw_tracepoint[.w]/<tracepoint> |      |



## 获取内核中的所有可用tracepoint函数

~~~bash
cat /sys/kernel/tracing/available_events
~~~

bpftrace -l 列出当前内核支持的所有tracepoint和kprobe函数

## tracepoint 入口点

### syscall类型tracepoint的定义

内核树include/linux/syscalls.h

SYSCALL_TRACE_ENTER_EVENT

~~~c
#define SYSCALL_TRACE_ENTER_EVENT(sname)				\
	static struct syscall_metadata __syscall_meta_##sname;		\
	static struct trace_event_call __used				\
	  event_enter_##sname = {					\
		.class			= &event_class_syscall_enter,	\
		{							\
			.name                   = "sys_enter"#sname,	\
		},							\
		.event.funcs            = &enter_syscall_print_funcs,	\
		.data			= (void *)&__syscall_meta_##sname,\
		.flags                  = TRACE_EVENT_FL_CAP_ANY,	\
	};								\
	static struct trace_event_call __used				\
	  __attribute__((section("_ftrace_events")))			\
	 *__event_enter_##sname = &event_enter_##sname;
~~~



SYSCALL_TRACE_EXIT_EVENT

~~~c
#define SYSCALL_TRACE_EXIT_EVENT(sname)					\
	static struct syscall_metadata __syscall_meta_##sname;		\
	static struct trace_event_call __used				\
	  event_exit_##sname = {					\
		.class			= &event_class_syscall_exit,	\
		{							\
			.name                   = "sys_exit"#sname,	\
		},							\
		.event.funcs		= &exit_syscall_print_funcs,	\
		.data			= (void *)&__syscall_meta_##sname,\
		.flags                  = TRACE_EVENT_FL_CAP_ANY,	\
	};								\
	static struct trace_event_call __used				\
	  __attribute__((section("_ftrace_events")))			\
	*__event_exit_##sname = &event_exit_##sname;

~~~



系统调用函数的定义:

~~~c

#define SYSCALL_METADATA(sname, nb, ...)			\
	static const char *types_##sname[] = {			\
		__MAP(nb,__SC_STR_TDECL,__VA_ARGS__)		\
	};							\
	static const char *args_##sname[] = {			\
		__MAP(nb,__SC_STR_ADECL,__VA_ARGS__)		\
	};							\
	SYSCALL_TRACE_ENTER_EVENT(sname);			\
	SYSCALL_TRACE_EXIT_EVENT(sname);			\
	static struct syscall_metadata __used			\
	  __syscall_meta_##sname = {				\
		.name 		= "sys"#sname,			\
		.syscall_nr	= -1,	/* Filled in at boot */	\
		.nb_args 	= nb,				\
		.types		= nb ? types_##sname : NULL,	\
		.args		= nb ? args_##sname : NULL,	\
		.enter_event	= &event_enter_##sname,		\
		.exit_event	= &event_exit_##sname,		\
		.enter_fields	= LIST_HEAD_INIT(__syscall_meta_##sname.enter_fields), \
	};							\
	static struct syscall_metadata __used			\
	  __attribute__((section("__syscalls_metadata")))	\
	 *__p_syscall_meta_##sname = &__syscall_meta_##sname;



#ifndef SYSCALL_DEFINE0
#define SYSCALL_DEFINE0(sname)					\
	SYSCALL_METADATA(_##sname, 0);				\
	asmlinkage long sys_##sname(void);			\
	ALLOW_ERROR_INJECTION(sys_##sname, ERRNO);		\
	asmlinkage long sys_##sname(void)
#endif /* SYSCALL_DEFINE0 */



#define SYSCALL_DEFINE1(name, ...) SYSCALL_DEFINEx(1, _##name, __VA_ARGS__)
#define SYSCALL_DEFINE2(name, ...) SYSCALL_DEFINEx(2, _##name, __VA_ARGS__)
#define SYSCALL_DEFINE3(name, ...) SYSCALL_DEFINEx(3, _##name, __VA_ARGS__)
#define SYSCALL_DEFINE4(name, ...) SYSCALL_DEFINEx(4, _##name, __VA_ARGS__)
#define SYSCALL_DEFINE5(name, ...) SYSCALL_DEFINEx(5, _##name, __VA_ARGS__)
#define SYSCALL_DEFINE6(name, ...) SYSCALL_DEFINEx(6, _##name, __VA_ARGS__)

#define SYSCALL_DEFINE_MAXARGS	6

#define SYSCALL_DEFINEx(x, sname, ...)				\
	SYSCALL_METADATA(sname, x, __VA_ARGS__)			\
	__SYSCALL_DEFINEx(x, sname, __VA_ARGS__)

#define __PROTECT(...) asmlinkage_protect(__VA_ARGS__)
~~~



### syscall类型的ebpf程序的参数类型来源

5.15.47/kernel/trace/trace_syscalls.c

~~~c
static int perf_call_bpf_enter(struct trace_event_call *call, struct pt_regs *regs,
			       struct syscall_metadata *sys_data,
			       struct syscall_trace_enter *rec)
{
	struct syscall_tp_t {
		unsigned long long regs;
		unsigned long syscall_nr;
		unsigned long args[SYSCALL_DEFINE_MAXARGS];
	} param;
	int i;

	*(struct pt_regs **)&param = regs;
	param.syscall_nr = rec->nr;
	for (i = 0; i < sys_data->nb_args; i++)
		param.args[i] = rec->args[i];
	return trace_call_bpf(call, &param);
}
~~~

### Tracepoint在内核中的定义

~~~c
TRACE_EVENT(net_dev_xmit,

	TP_PROTO(struct sk_buff *skb,
		 int rc,
		 struct net_device *dev,
		 unsigned int skb_len),

	TP_ARGS(skb, rc, dev, skb_len),

	TP_STRUCT__entry(
		__field(	void *,		skbaddr		)
		__field(	unsigned int,	len		)
		__field(	int,		rc		)
		__string(	name,		dev->name	)
	),

	TP_fast_assign(
		__entry->skbaddr = skb;
		__entry->len = skb_len;
		__entry->rc = rc;
		__assign_str(name, dev->name);
	),

	TP_printk("dev=%s skbaddr=%p len=%u rc=%d",
		__get_str(name), __entry->skbaddr, __entry->len, __entry->rc)
);
~~~

Tracepoint函数名: TRACE_EVENT的第一个参数即函数名，实际调用该tracepoint时，会在函数名加上"trace_"前缀，即trace_net_dev_xmit

函数原型: TP_PROTO(struct sk_buff *skb, int rc, struct net_device *dev, unsigned int skb_len)声明函数的原型



## 示例代码

### syscalls:sys_enter_accept

~~~c
struct enter_accept_args{
    unsigned long long unused;
	long syscall_nr;
    int sockfd;
    struct sockaddr *addr;
    u32 *addrlen;
};

SEC("tracepoint/syscalls/sys_enter_accept")
//int BPF_PROG(sys__enter_accept,  int sockfd, struct sockaddr *addr, u32 *addrlen){
int sys__enter_accept(struct enter_accept_args *ctx){
    char comm[TASK_COMM_LEN];
    bpf_get_current_comm(comm, sizeof(comm));

    struct socket *sock = fd_to_sock(ctx->sockfd);
    if(!sock){
        bpf_printk("fd %d no sock++++++++++\n", ctx->sockfd);
        return 0;
    }

    //struct inet_sock *psock = (struct inet_sock*)(sock->sk);
    struct inet_sock *psock = (struct inet_sock*)BPF_CORE_READ(sock,sk);
    u32 src_ip = BPF_CORE_READ(psock,inet_saddr);
    u32 src_port = BPF_CORE_READ(psock,inet_sport); 
    bpf_printk("sys_enter_accept %s src_ip:%u src_port:%d\n", comm, bpf_ntohl(src_ip), bpf_ntohs(src_port));
   //bpf_printk("sys_enter_accept %s\n", comm);
    return 0;
}
~~~

### net:net_dev_xmit

~~~c
SEC("tracepoint/net/net_dev_xmit")
int static __always_inline net_dev_xmit(struct net_dev_xmit_args *ctx){
    char comm[TASK_COMM_LEN];
    bpf_get_current_comm(comm, sizeof(comm));
    bpf_printk("comm:%s dev:%s\n", comm, ctx->dev->name);
    return 0;
}
~~~



## 问题记录

~~~c
SEC("tracepoint/syscalls/sys_enter_write")
int static inline sys_enter_write(struct enter_write_args *ctx){
    char comm[TASK_COMM_LEN];
    bpf_get_current_comm(comm, sizeof(comm));
    bpf_printk("sys_enter_write comm:%s fd:%d len:%lld\n", comm, ctx->fd, ctx->count);

    struct write_arg_key key = {
        .tgid_pid = bpf_get_current_pid_tgid(),
    };
    
    void *buf = ctx->buf; 
  	int ret = bpf_map_update_elem(&write_args_map, &key, &buf, BPF_ANY);
    
    //这样写会导致加载失败
    //int ret = bpf_map_update_elem(&write_args_map, &key, &(ctx->buf), BPF_ANY);
    if(ret < 0){
        bpf_printk("map_update_elem failed. %s ret:%d\n", comm, ret);
    }
    return 0;
}

struct enter_write_args{
    unsigned long long unused;
	long syscall_nr;
    unsigned int fd;
    const char* buf;
    size_t count;
};
~~~



尝试挂载上述程序会导致如下错误:

~~~
panic: program sys_enter_write: load program: permission denied: 38: (85) call bpf_map_update_elem#2: R3 type=ctx expected=fp (49 line(s) omitted)
~~~



### invalid indirect read from stack

这种类型的错误是怎么触发的，怎么解决



### tracepoint 未生效

~~~
echo 1 > /sys/kernel/tracing/events/net/net_dev_xmit/enable
~~~

关闭tracepoint:

~~~
echo 0 > /sys/kernel/tracing/events/net/net_dev_xmit/enable
~~~

### BPF_PROG_TYPE_TRACEPOINT 类型bpf函数的原型

内核版本5.4.0-190-generic

开始以为net:netif_rx 是内核源码中的宏TP_PROTO也能确定bpf函数原型，所以bpf函数按如下的方式写的，结果发现skb地址跟内核中的trace_netif_rx输出的skb地址不一致。

~~~c

SEC("tracepoint/net/netif_rx")
static __always_inline int netif_rx(struct sk_buff *skb){
    bpf_printk("skb: %p \n" , skb);
    return 0;
}

~~~

通过使用下面的bpftrace命令:

~~~c
bpftrace -dd -e 'tracepoint:net:netif_rx {printf("%d\n", args->name)}'

cat /sys/kernel/debug/tracing/events/net/netif_rx/format
~~~

确定其使用的参数应该如下：

~~~c
struct netif_rx_args{
  unsigned short common_type;
  unsigned char common_flags;
  unsigned char common_preempt_count;
  int common_pid;
  void * skbaddr;
  unsigned int len;
  int data_loc_name;
};

SEC("tracepoint/net/netif_rx")
static __always_inline int netif_rx(struct netif_rx_args *ctx){
    bpf_printk("skb: %p \n" , ctx->skbaddr);
    return 0;
}

~~~

即  common_type、common_flags、common_preempt_count、common_pid 四个字段加上TP_STRUCT__entry宏定义的结构体中的字段

syscalls:*类型的bpf函数参数也是

## 参考

* 内核5.4 include/linux/syscalls.h
* https://www.kernel.org/doc/html/latest/bpf/libbpf/program_types.html#rawtp
* Tracepoint 详细介绍 https://lwn.net/Articles/379903/

