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

~~~C
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



## 示例代码

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

## 参考

* 内核5.4 include/linux/syscalls.h
* https://www.kernel.org/doc/html/latest/bpf/libbpf/program_types.html#rawtp

