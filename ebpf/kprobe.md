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
* PT_REGS_RC获取返回值，用于kretprobe或uretprobe类型ebpf程序

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



## 坑

在5.4内核版本

~~~c
SEC("kprobe/do_sys_open")
int kprobe___do_sys_open(struct pt_regs *regs){
    char comm[TASK_COMM_LEN];
    bpf_get_current_comm(comm, sizeof(comm));
    char filename[32];
    int ret = bpf_probe_read_kernel_str(filename, sizeof(filename), (void*)PT_REGS_PARM2(regs));
    if(ret < 0){
        bpf_printk(" open ret:%d\n",    ret);
        return 0;
    }
    bpf_printk("  open %s\n",  filename);
    return 0;
}
~~~

上面版本可以正常输出打开的文件，下面版本则只会输出" open ret: -14"。bug在哪里

~~~c
SEC("kprobe/do_sys_open")
int kprobe___do_sys_open(struct pt_regs *regs){
    char comm[TASK_COMM_LEN];
    bpf_get_current_comm(comm, sizeof(comm));
    char filename[32];
    int ret = bpf_probe_read_kernel_str(filename, sizeof(filename), (void*)PT_REGS_PARM2(regs));
    if(ret < 0){
        bpf_printk(" open ret:%d\n",    ret);
        return 0;
    }
    bpf_printk(" %s open %s\n", comm, filename);
    return 0;
}
~~~



## 如何确定socket fd关联的五元组

~~~
bpf_sock_from_file
~~~



~~~c
#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_core_read.h>
#include <bpf/bpf_tracing.h>
#include <bpf/bpf_endian.h>


#define BPF_ANY		0 /* create new element or update existing */
#define BPF_NOEXIST	1 /* create new element if it didn't exist */
#define BPF_EXIST	2 /* update existing element */
#define BPF_F_LOCK	4 /* spin_lock-ed map_lookup/map_update */



typedef __u32 u32;
typedef __u64 u64;


struct tuple{
    u32 src_ip;
    u32 dst_ip;
    u16 src_port;
    u16 dst_port;
};

struct sockfd{
    u32 fd;
    struct tuple tuple;
};

struct bpf_map_def SEC("maps") fd_map ={
    .type = BPF_MAP_TYPE_HASH,
    .key_size = sizeof(u64),
    .value_size = 1,
    .max_entries = 512 * 10,
};

struct bpf_map_def SEC("maps") pid_map = {
    .type = BPF_MAP_TYPE_HASH,
    .key_size = sizeof(u32),
    .value_size = sizeof(u32),
    .max_entries = 1,
};

struct bpf_map_def SEC("maps") file_fd_map = {
    .type = BPF_MAP_TYPE_HASH,
    .key_size = sizeof(u64),
    .value_size = sizeof(u32),
    .max_entries = 512 * 10,
};

struct bpf_map_def SEC("maps") fd_sock_addr_map ={
    .type = BPF_MAP_TYPE_HASH,
    .key_size = sizeof(u32),
    .value_size = sizeof(struct sockfd),
    .max_entries = 512 * 10,
};
struct bpf_map_def SEC("maps") perf_event_map ={
    .type = BPF_MAP_TYPE_PERF_EVENT_ARRAY,
    .key_size = sizeof(int),
    .value_size = 0,
    .max_entries = 8,
};


static __always_inline u32 get_tgid(){
    return bpf_get_current_pid_tgid() >> 32;
}
static __always_inline u32 get_taskid(){
    return bpf_get_current_pid_tgid() & 0XFFFFFFFF;
}
static __always_inline u64 get_pid_tgid(){
    return bpf_get_current_pid_tgid();
}


static __always_inline bool can_continue(){
    u32 key = 1;
    u32 *value = bpf_map_lookup_elem(&pid_map, &key);
    if (!value){
        return false;
    }
    u32 tgid = get_tgid();
    return tgid == *value;
}

//获取fd 以及sock地址, fd要和pid结合
SEC("kprobe/__sys_connect")
int BPF_KPROBE(kprobe____sys_connect, int fd, struct sockaddr *uservaddr, int addrlen){
    if (!can_continue()){
        return 0;
    }
    u64 pid_tgid = get_pid_tgid();
    bpf_printk("sys_connect pid:%u tid:%u fd:%d\n", pid_tgid >> 32, pid_tgid & 0XFFFFFFFF, fd);
    struct sockfd value = {.fd = fd};
    bpf_map_update_elem(&fd_sock_addr_map, &fd, &value, BPF_ANY);
    return 0;
}

SEC("kprobe/tcp_v4_connect")
int BPF_KPROBE(kprobe____tcp_v4_connect,struct sock *sk, struct sockaddr *uaddr, int addr_len){
    if (!can_continue()){
        return 0;
    }
    struct socket *psocket = BPF_CORE_READ(sk,sk_socket);
    u64 key = (u64)BPF_CORE_READ(psocket,file);
    u32 *pfd = bpf_map_lookup_elem(&file_fd_map, &key); 
    if (!pfd){
        bpf_printk("tcp_v4_connect. no fd for key:%llu \n", key);
        return 0;
    }
    bpf_printk("tcp_v4_connect fd:%d key:%llu\n", *pfd, key);
    struct sockfd *sockfd = bpf_map_lookup_elem(&fd_sock_addr_map, pfd);
    if (!sockfd){
        bpf_printk("tcp_v4_connect no fd:%d found in fd_sock_addr_map\n", *pfd);
        return 0;
    }
    struct sockaddr_in usin;
    bpf_core_read(&usin, sizeof(usin), uaddr);
    //struct sockfd sockfd;
    sockfd->fd = *pfd;
    sockfd->tuple.dst_port = usin.sin_port;
    sockfd->tuple.dst_ip = usin.sin_addr.s_addr;
    bpf_printk("dst_ip:%d port:%d\n", usin.sin_addr.s_addr, usin.sin_port);


    /*
    int ret =0;
    if ((ret = bpf_map_update_elem(&fd_sock_addr_map, pfd, &sockfd, BPF_ANY)) < 0){
        bpf_printk("tcp_v4_connect update fd_sock_addr_map failed. %d\n", ret);
    }
    */
    return 0;
}

//建立file 到fd的映射关系
SEC("kprobe/fd_install")
int BPF_KPROBE(kprobe____fd_install, unsigned int fd, struct file *file){
//int kprobe____fd_install(struct pt_regs *ctx){
    if (!can_continue()){
        return 0;
    }
    /*
    void *pvalue =  bpf_map_lookup_elem(&fd_map, &fd); 
    if (!pvalue){
        bpf_printk("lookup fd_map failed\n");
        return 0;
    }
    */

    u64 ino = BPF_CORE_READ(file, f_inode, i_ino);
    bpf_printk("fd_install fd:%d %llu\n", fd, ino);
    //u64 key = BPF_CORE_READ(file, f_inode, i_ino);
    u64 key = (u64)file;
    bpf_printk("fd_install fd:%d key:%llu\n", fd, key);
    int ret = 0;
    if ((ret = bpf_map_update_elem(&file_fd_map, &key, &fd, BPF_NOEXIST)) < 0){
        bpf_printk("update file_fd_map failed.%d \n", ret);
        return 0;
    }
    return 0;
}

SEC("kprobe/tcp_connect")
int kprobe_tcp_connect(struct pt_regs *ctx){
    if (!can_continue()){
        return 0;
    }
    bpf_printk("tcp_connect\n");
    struct sock *sk = PT_REGS_PARM1(ctx); 

    struct socket *psocket = BPF_CORE_READ(sk,sk_socket);
    u64 key = (u64)BPF_CORE_READ(psocket,file);
    u32 *pfd = bpf_map_lookup_elem(&file_fd_map, &key); 
    if (!pfd){
        bpf_printk("tcp_v4_connect. no fd for key:%llu \n", key);
        return 0;
    }
    struct sockfd *sockfd = bpf_map_lookup_elem(&fd_sock_addr_map, pfd);
    if (!sockfd){
        bpf_printk("tcp_v4_connect no fd:%d found in fd_sock_addr_map\n", *pfd);
        return 0;
    }

    struct inet_sock *psock = (struct inet_sock*)sk;
    sockfd->tuple.src_ip = BPF_CORE_READ(psock,inet_saddr);
    sockfd->tuple.src_port = BPF_CORE_READ(psock,inet_sport); 
    int ret = bpf_perf_event_output(ctx, &perf_event_map, 0xffffffffULL, sockfd, sizeof(*sockfd));
    if (ret < 0){
        bpf_printk("bpf_perf_event_output %d\n", ret);
    }
    //bpf_map_delete_elem(&fd_sock_addr_map, &pid_tgid);
    return 0;
}

char _license[] SEC("license") = "GPL";
~~~

