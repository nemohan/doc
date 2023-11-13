# kprobe/kretprobe

[TOC]



## 内核符号表

确定当前内核是否定义了某个函数

/proc/kallsyms

## kprobe

### hook函数原型

int hook(struct pt_regs *ctx)。使用int hook()也没问题，内核对hook的原型没有要求么？？

获取被hook函数的参数: 

* PT_REGS_PARM1 获取第一个参数
* PT_REGS_PARM2 获取第二个参数
* PT_REGS_PARM3获取第三个参数
* PT_REGS_PARM4获取第四个参数
* PT_REGS_PARM5获取第5个参数

### 代码示例

~~~c

SEC("kprobe/do_sys_open")
int kprobe_do_sysopen(struct pt_regs *reg) {
    __u64 pid = bpf_get_current_pid_tgid();
    char filename[32];
    int ret = bpf_probe_read_kernel_str(filename,  sizeof(filename), (void*)PT_REGS_PARM2(reg));
    bpf_printk("sys_open file:%s:   ret:%d %u\n",   filename, ret, pid & 0XFFFFFFFF);
	return 0;
}

~~~



### hook函数原型的另一种表达方式

使用BPF_KPROBE避免了使用宏PT_REGS等获取函数参数

~~~c
SEC("kprobe/__nf_conntrack_hash_insert")
int BPF_KPROBE(kprobe____nf_conntrack_hash_insert, struct nf_conn *ct, unsigned int hash, unsigned int reply_hash){
~~~





## kretprobe

获取被hook函数的返回值用PT_REGS_RC, PT_REGS_RET宏是获取什么的???

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

### 代码示例

~~~c
SEC("kretprobe/do_sys_open")
int kretprobe_do_sysopen(struct pt_regs *reg) {
    __u64 pid = bpf_get_current_pid_tgid();
    bpf_printk("sys_open ret pid:%d ret:%d\n", pid & 0xFFFFFFFF, PT_REGS_RC(reg));
	return 0;
}

~~~



## 代码示例

### 获取内核中的nat转换关系或nf_conntrack_hash 表中的元素

~~~c
#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_core_read.h>
#include <bpf/bpf_tracing.h>
#include <bpf/bpf_endian.h>


#define BPF_F_CURRENT_CPU 0xffffffffULL
typedef __u32 u32;
typedef __u64 u64;


struct tuple{
    u32 src_ip;
    u32 dst_ip;
    u16 src_port;
    u16 dst_port;
};

struct nat_tuple{
    struct tuple origin;   
    struct tuple reply;
    __u32 proto;
};

struct bpf_map_def SEC("maps") nat_map ={
    //.type = BPF_MAP_TYPE_HASH,
    .type = BPF_MAP_TYPE_PERF_EVENT_ARRAY,
    .key_size = sizeof(int),
    .value_size = 0,
    .max_entries = 8,
};

static __always_inline u32 get_tgid(){
    return bpf_get_current_pid_tgid() >> 32;
}

SEC("kprobe/__nf_conntrack_hash_insert")
int kprobe__nf_conntrack_hash_insert(struct pt_regs *ctx){
//int BPF_KPROBE(kprobe____nf_conntrack_hash_insert, struct nf_conn *ct, unsigned int hash, unsigned int reply_hash){
    struct nf_conn *ct = (struct nf_conn *)PT_REGS_PARM1(ctx);
    if(!ct){
        return 0;
    }
    unsigned long pstatus = BPF_CORE_READ(ct, status);
    bpf_printk("nf_conntrack_hash_insert status:%u\n", pstatus);
    if (!(pstatus & IPS_CONFIRMED)){
        bpf_printk("not confirmed status\n");
        return 0;
    }
    //if (!(pstatus &IPS_NAT_MASK)){
    //    return 0;
    //}
  
    struct  nf_conntrack_tuple_hash *tuple_hash= BPF_CORE_READ(ct, tuplehash);
    struct nf_conntrack_tuple *src_tuple = &(tuple_hash[IP_CT_DIR_ORIGINAL].tuple);
    u32 protonum = src_tuple->dst.protonum;
    u32 src_ip = src_tuple->src.u3.ip;
    __u16 src_port = src_tuple->src.u.all;
    u32 dst_ip = src_tuple->dst.u3.ip;
    __u16 dst_port = src_tuple->dst.u.all;
    //bpf_printk("proto:%u dst_ip:%u dst_port:%d\n",protonum , dst_ip, bpf_ntohs(dst_port));
    struct nf_conntrack_tuple *reply_tuple = &(tuple_hash[IP_CT_DIR_REPLY].tuple);
    struct nat_tuple tuple ={
        .origin={
            .src_ip= src_ip,
            .src_port= src_port,
            .dst_ip= dst_ip,
            .dst_port= dst_port,
        },
        .reply={
            .src_ip= reply_tuple->src.u3.ip,
            .src_port= reply_tuple->src.u.all,
            .dst_ip= reply_tuple->dst.u3.ip,
            .dst_port= reply_tuple->dst.u.all,
        },
        .proto= protonum,
    };
    bpf_perf_event_output(ctx, &nat_map, BPF_F_CURRENT_CPU, &tuple, sizeof(tuple));
    return 0;
}

char _license[] SEC("license") = "GPL";
~~~



### hook tcp_connect

~~~c
SEC("kprobe/tcp_connect")
int kprobe_tcp_connect(struct pt_regs *ctx){
    bpf_printk("tcp_connect\n");
    struct sock *sk = PT_REGS_PARM1(ctx); 
    u64 pid_tgid = get_pid_tgid();
    struct sockfd *sockfd = bpf_map_lookup_elem(&fd_sock_addr_map, &pid_tgid);
    if (!sockfd){
        bpf_printk("tcp_connect ret:%d\n");
        return 0;
    }
    struct inet_sock *psock = (struct inet_sock*)sk;
    sockfd->tuple.src_ip = BPF_CORE_READ(psock,inet_saddr);
    sockfd->tuple.src_port = BPF_CORE_READ(psock,inet_sport); 
    int ret = bpf_perf_event_output(ctx, &perf_event_map, 0xffffffffULL, sockfd, sizeof(*sockfd));
    if (ret < 0){
        bpf_printk("bpf_perf_event_output %d\n", ret);
    }
    bpf_map_delete_elem(&fd_sock_addr_map, &pid_tgid);
    return 0;
}
~~~



## 如何确定socket fd关联的五元组

~~~c
struct socket *sock_from_file(struct file *file, int *err)
{
	if (file->f_op == &socket_file_ops)
		return file->private_data;	/* set in sock_map_fd */

	*err = -ENOTSOCK;
	return NULL;
}

struct socket *sockfd_lookup(int fd, int *err)
{
	struct file *file;
	struct socket *sock;

	file = fget(fd);
	if (!file) {
		*err = -EBADF;
		return NULL;
	}

	sock = sock_from_file(file, err);
	if (!sock)
		fput(file);
	return sock;
}
~~~

