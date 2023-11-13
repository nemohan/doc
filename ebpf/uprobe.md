# uprobe

[TOC]



## uprobe

### hook函数原型

int hook(struct pt_regs *ctx)。使用int hook()也没问题，内核对hook的原型没有要求么？？

获取被hook函数的参数: 

* PT_REGS_PARM1 获取第一个参数
* PT_REGS_PARM2 获取第二个参数
* PT_REGS_PARM3获取第三个参数
* PT_REGS_PARM4获取第四个参数
* PT_REGS_PARM5获取第5个参数

## uretprobe

获取被hook函数的返回值用PT_REGS_RC函数

### 函数原型

int hook(pt_regs *ctx)

## 常用帮助函数或宏

### 宏

* PT_REGS_PARM1 获取第一个参数
* PT_REGS_PARM2 获取第二个参数
* PT_REGS_PARM3获取第三个参数
* PT_REGS_PARM4获取第四个参数
* PT_REGS_PARM5获取第5个参数
* PT_REGS_RC，用于kretprobe或uretprobe类型ebpf程序

### 函数

* bpf_probe_read_user_str、bpf_probe_read_kernel_str 获取用户态传递到内核的字符串参数



## 代码示例

被探查程序

~~~c
#include <stdio.h>
#include <stdlib.h>

int myprint(int arg){
    printf("myprint arg:%d\n", arg);
}

int myadd(int l, int r){
    return l+r;
}
int main(int argc, char **argv){
    if (argc < 2){
        printf("usage. uprobe_target 1\n");
        return 1;
    }
    int arg = atoi(argv[1]);
    if (argc == 2){
        myprint(arg);
    }else{
        int l = atoi(argv[1]);
        int r = atoi(argv[2]);
        printf("myadd result:%d\n", myadd(l, r));
    }
    return 0;
}
~~~



~~~c
#include <linux/version.h>
#include <linux/ptrace.h>
//#include <uapi/linux/bpf.h>
#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_core_read.h>
#include <bpf/bpf_tracing.h>
SEC("uprobe/myprint")
int bpf_prog1(struct pt_regs *ctx)
{
        bpf_printk("uprobe myprint:%llu %llu\n", ctx->rax, ctx->rdi);
        return 0;
}

SEC("uprobe/myadd")
int uprobe_myadd(struct pt_regs *ctx){
        bpf_printk("my add parms:%d %d\n", PT_REGS_PARM1(ctx), PT_REGS_PARM2(ctx));
        return 0;
}

SEC("uretprobe/myadd")
int uretprobe_myadd(struct pt_regs *ctx){
        bpf_printk("my add result:%d \n", PT_REGS_RC(ctx));
        return 0;
}

char _license[] SEC("license") = "GPL";
~~~



### https协议解析

~~~c

#include <linux/version.h>
#include <linux/ptrace.h>
//#include <uapi/linux/bpf.h>
#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_core_read.h>
#include <bpf/bpf_tracing.h>

typedef __u32 u32;
typedef __u64 u64;

struct bpf_map_def SEC("maps") perf_event_buffer ={
    .type = BPF_MAP_TYPE_PERF_EVENT_ARRAY,
    .key_size = sizeof(int), 
    .value_size = sizeof(u32),
    .max_entries = 8,
};

struct bpf_map_def SEC("maps") read_args_map = {
    .type = BPF_MAP_TYPE_PERCPU_HASH,
    .key_size = sizeof(u32),
    .value_size = sizeof(void *),
    .max_entries = 1024,
};

#define MAX_DATA_SIZE 2048
#define EVENT_READ 1
#define EVENT_WRITE 2
struct ssl_event{
    u32 event_type;
    unsigned char payload[MAX_DATA_SIZE];
};
struct bpf_map_def SEC("maps") event_buffer ={
    .type = BPF_MAP_TYPE_PERCPU_ARRAY,
    .key_size = sizeof(int),
    .value_size = sizeof(struct ssl_event),
    .max_entries = 1,
};

//struct bpf_map_def SEC("maps") process_id_map ={
//    .type = BPF_MAP_TYPE_PERCPU_ARRAY,
//    .key_size = sizeof(int),
//    .value_size = sizeof(struct ssl_event),
//    .max_entries = 1,
//};

static __always_inline u32 get_tgid(){
    return bpf_get_current_pid_tgid() >> 32;
}

void process_ssl_data(struct pt_regs *ctx, int event_type, char *buf, int len){
    int key = 0; 
    struct ssl_event *pevent = bpf_map_lookup_elem(&event_buffer, &key);
    if(!pevent){
        bpf_printk("bpf_perf_event_output get event buffer failed. \n");
        return;
    }
    if (len < 0){
        return ;
    }
    pevent->event_type = EVENT_READ;
    //int size = len < MAX_DATA_SIZE ? len : MAX_DATA_SIZE;
    int size = (len < MAX_DATA_SIZE ? (len & (MAX_DATA_SIZE - 1)) : MAX_DATA_SIZE); 
    bpf_probe_read(pevent->payload, size, buf);
    int ret = 0;
    if ((ret = bpf_perf_event_output(ctx, &perf_event_buffer, BPF_F_CURRENT_CPU, pevent, sizeof(*pevent))) < 0){
        bpf_printk("bpf_perf_event_output failed. %d\n", ret);
    }
}
SEC("uprobe/SSL_read")
int uprobe_ssl_read(struct pt_regs *ctx){
    void *buf = PT_REGS_PARM2(ctx);
    u32 tgid = get_tgid();
    bpf_map_update_elem(&read_args_map, &tgid, &buf, BPF_ANY);
    bpf_printk("ssl read pid:%d read:%d\n", tgid, PT_REGS_PARM3(ctx));

    return 0;
}

SEC("uretprobe/SSL_read")
int uretprobe_ssl_read(struct pt_regs *ctx){
    u32 tgid  = get_tgid();

    char **buf = bpf_map_lookup_elem(&read_args_map, &tgid );
    if(!buf){
        bpf_printk("ret ssl read:%d no arg found", tgid);
        return 0;
    }
    int ret = PT_REGS_RC(ctx);
    bpf_map_delete_elem(&read_args_map, &tgid);
    process_ssl_data(ctx, EVENT_READ, (char*)*buf, ret);
    bpf_printk("ret ssl read: %d \n", ret);
    return 0;
}
char _license[] SEC("license") = "GPL";
~~~



## 探查TLS

~~~
nm --dynamic /usr/lib/x86_64-linux-gnu/libssl.so.1.1
~~~



~~~c
static inline struct rtable *ip_route_newports(struct flowi4 *fl4, struct rtable *rt,
					       __be16 orig_sport, __be16 orig_dport,
					       __be16 sport, __be16 dport,
					       struct sock *sk)
{
	if (sport != orig_sport || dport != orig_dport) {
		fl4->fl4_dport = dport;
		fl4->fl4_sport = sport;
		ip_rt_put(rt);
		flowi4_update_output(fl4, sk->sk_bound_dev_if,
				     RT_CONN_FLAGS(sk), fl4->daddr,
				     fl4->saddr);
		security_sk_classify_flow(sk, flowi4_to_flowi(fl4));
		return ip_route_output_flow(sock_net(sk), fl4, sk);
	}
	return rt;
}
~~~



### 本地临时端口分配

~~~
inet_hash_connect
__inet_hash_connect
inet_bind_hash
~~~

### 为sock分配fd

~~~c
static int sock_map_fd(struct socket *sock, int flags)
{
	struct file *newfile;
	int fd = get_unused_fd_flags(flags);
	if (unlikely(fd < 0)) {
		sock_release(sock);
		return fd;
	}

	newfile = sock_alloc_file(sock, flags, NULL);
	if (!IS_ERR(newfile)) {
		fd_install(fd, newfile);
		return fd;
	}

	put_unused_fd(fd);
	return PTR_ERR(newfile);
}
~~~



### 获取connect使用的五元组及文件描述符

~~~
hook __sys_connect 获取fd
inet_bind_hash 获取本地临时端口
~~~





