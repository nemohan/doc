# cgroup

[TOC]



几个bpf helper函数，具体使用场景尚不明确

```
bpf_current_task_under_cgroup
bpf_get_current_cgroup_id
bpf_sk_cgroup_id
```

## bpftool管理挂载到cgroup上的ebpf程序

bpftool貌似不支持cgroup v1.

cgroup相关ebpf程序应该都是挂载到cgroupv2文件系统的上的某个目录的文件描述符

挂载:

首先需要将ebpf加载到内核中，指定的cgroup必须存在

~~~
bpftool cgroup attach /sys/fs/cgroup/unified/ebpf_cgroup_test connect4 id 59
~~~

查看挂载到指定cgroup的所有ebpf程序:

~~~
bpftool cgroup tree /sys/fs/cgroup/unified/ebpf_cgroup_test
bpftool cgroup tree 查看所有挂载的cgroup类型的程序
~~~

卸载:

~~~
bpftool cgroup detach /sys/fs/cgroup/unified/ebpf_cgroup_test/ connect4 id 59
~~~



## cgroup 相关的bpf 程序类型

| 程序类型                       | SEC                                                          | attach type                                                  | 描述                                                         |
| ------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ |
| BPF_PROG_TYPE_SOCK_OPS         | sockops                                                      | BPF_CGROUP_SOCK_OPS                                          | The kernel calls this program on various TCP events. The program can adjust the behavior of the kernel TCP stack, including custom TCP header options, and so on. |
| BPF_PROG_TYPE_CGROUP_SOCK_ADDR | BPF_CGROUP_INET4_BIND<br/>cgroup/bind4<br/><br/>BPF_CGROUP_INET4_CONNECT<br/>cgroup/connect4<br/><br/>BPF_CGROUP_INET4_GETPEERNAME<br/>cgroup/getpeername4<br/><br/>BPF_CGROUP_INET4_GETSOCKNAME<br/>cgroup/getsockname4<br/><br/>BPF_CGROUP_INET6_BIND<br/>cgroup/bind6<br/><br/>BPF_CGROUP_INET6_CONNECT<br/>cgroup/connect6<br/><br/>BPF_CGROUP_INET6_GETPEERNAME<br/>cgroup/getpeername6<br/><br/>BPF_CGROUP_INET6_GETSOCKNAME<br/>cgroup/getsockname6<br/><br/>BPF_CGROUP_UDP4_RECVMSG<br/>cgroup/recvmsg4<br/><br/>BPF_CGROUP_UDP4_SENDMSG<br/>cgroup/sendmsg4<br/><br/>BPF_CGROUP_UDP6_RECVMSG<br/>cgroup/recvmsg6<br/><br/>BPF_CGROUP_UDP6_SENDMSG<br/>cgroup/sendmsg6<br/><br/>BPF_CGROUP_UNIX_CONNECT<br/>cgroup/connect_unix<br/><br/>BPF_CGROUP_UNIX_SENDMSG<br/>cgroup/sendmsg_unix<br/><br/>BPF_CGROUP_UNIX_RECVMSG<br/>cgroup/recvmsg_unix<br/><br/>BPF_CGROUP_UNIX_GETPEERNAME<br/>cgroup/getpeername_unix<br/><br/>BPF_CGROUP_UNIX_GETSOCKNAME<br/>cgroup/getsockname_unix |                                                              | he kernel calls this program during connect, bind, sendto, recvmsg, getpeername, and getsockname operations. This program allows changing IP addresses and ports. This is useful when you implement socket-based network address translation (NAT) in eBPF. |
| BPF_PROG_TYPE_CGROUP_SOCKOPT   | BPF_CGROUP_GETSOCKOPT<br />BPF_CGROUP_SETSOCKOPT             | cgroup/getsockopt<br />cgroup/setsockopt                     | The kernel calls this program during setsockopt and getsockopt operations and allows changing the options. |
| BPF_PROG_TYPE_CGROUP_SOCK      | BPF_CGROUP_INET4_POST_BIND<br />BPF_CGROUP_INET6_POST_BIND<br />BPF_CGROUP_INET_SOCK_CREATE<br />BPF_CGROUP_INET_SOCK_RELEASE | cgroup/post_bind4<br />cgroup/post_bind6<br /><br />cgroup/sock_create<br />cgroup/sock<br />cgroup/sock_release | The kernel calls this program during socket creation, socket releasing, and binding to addresses. You can use these programs to allow or deny the operation, or only to inspect socket creation for statistics. |
| BPF_PROG_TYPE_CGROUP_SKB       | BPF_CGROUP_INET_EGRESS<br />BPF_CGROUP_INET_INGRESS          | cgroup_skb/egress<br />cgroup_skb/ingress                    | This program filters individual packets on ingress and egress, and can accept or reject packets. |
| BPF_PROG_TYPE_CGROUP_SYSCTL    | cgroup/sysctl                                                | BPF_CGROUP_SYSCTL                                            | This program allows filtering of access to system controls (sysctl). |
| BPF_PROG_TYPE_CGROUP_DEVICE    | BPF_CGROUP_DEVICE                                            | cgroup/dev                                                   |                                                              |



注意:

~~~
In RHEL, you can use multiple types of eBPF programs that you can attach to a cgroup. The kernel executes these programs when a program in the given cgroup performs an operation. Note that you can use only cgroups version 2.

~~~

## 代码示例

### BPF_PROG_TYPE_SOCK_OPS

可以修改tcp选项

~~~c
SEC("sockops")
int bpf_sockmap(struct bpf_sock_ops *skops)
{
	__u32 lport, rport;
	int op, err = 0, index, key, ret;


	op = (int) skops->op;
	bpf_printk("skops\n");
	switch (op) {
	case BPF_SOCK_OPS_PASSIVE_ESTABLISHED_CB:
		lport = skops->local_port;
		rport = skops->remote_port;

		bpf_printk("accept lport:%d rport:%d\n", lport, bpf_ntohl(rport));
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

		bpf_printk("connect lport:%d rport:%d\n", lport, bpf_ntohl(rport));
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

### BPF_PROG_TYPE_CGROUP_SOCK_ADDR

~~~c
//go:build ignore
#include <linux/version.h>
#include <linux/ptrace.h>
//#include <uapi/linux/bpf.h>
#include <linux/bpf.h>
#include <linux/filter.h>
#include <bpf/bpf_helpers.h>
#include<bpf/bpf_endian.h>
#include <sys/socket.h>
#include <netinet/in.h>


char __license[] SEC("license") = "Dual MIT/GPL";


SEC("cgroup/connect4")
static int connect_hook(struct bpf_sock_addr *sk) {
    bpf_printk("connect hook\n");
	return 1;
}

SEC("cgroup/bind4")
static int bind_hook(struct bpf_sock_addr *sk) {
    bpf_printk("bind hook\n");
	return 1;
}
~~~



### BPF_PROG_TYPE_CGROUP_SKB

~~~c

#define PACKET_PASS 1
#define PACKET_DROP 0
SEC("cgroup_skb/egress")
int skb_egress(struct __sk_buff *skb){
    if(skb->local_port != 8000 && bpf_ntohl(skb->remote_port) != 8000){
        //return PACKET_PASS;
    }
    bpf_printk("egress cookie:%lu\n", bpf_get_socket_cookie(skb));
    bpf_printk("egress. src:%x:%d\n", bpf_ntohl(skb->local_ip4), skb->local_port);
    bpf_printk("egress. dest:%x:%d\n", bpf_ntohl(skb->remote_ip4), bpf_ntohl(skb->remote_port));
    u16 sport = bpf_ntohl(skb->local_port) >> 16; 
    u16 dport = (skb->remote_port) >> 16;
    struct bpf_sock_tuple  tuple = {
        .ipv4.saddr = skb->local_ip4,
        .ipv4.daddr = skb->remote_ip4,
        .ipv4.sport = sport,
        .ipv4.dport = dport,
        
    };
    return PACKET_PASS;
}

~~~



## 触发执行的条件

### BPF_PROG_TYPE_CGROUP_SKB

~~~c
static int ip_finish_output(struct net *net, struct sock *sk, struct sk_buff *skb)
{
	int ret;

	ret = BPF_CGROUP_RUN_PROG_INET_EGRESS(sk, skb);
	switch (ret) {
	case NET_XMIT_SUCCESS:
		return __ip_finish_output(net, sk, skb);
	case NET_XMIT_CN:
		return __ip_finish_output(net, sk, skb) ? : ret;
	default:
		kfree_skb(skb);
		return ret;
	}
}

#define BPF_CGROUP_RUN_PROG_INET_EGRESS(sk, skb)			       \
({									       \
	int __ret = 0;							       \
	if (cgroup_bpf_enabled && sk && sk == skb->sk) {		       \
		typeof(sk) __sk = sk_to_full_sk(sk);			       \
		if (sk_fullsock(__sk))					       \
			__ret = __cgroup_bpf_run_filter_skb(__sk, skb,	       \
						      BPF_CGROUP_INET_EGRESS); \
	}								       
	__ret;								       \
})
~~~



## 遇到的问题

### 问题1：

在Ubuntu 20.04 LTS, 内核版本Linux 5.4.0-165-generic #182-Ubuntu SMP Mon Oct 2 19:43:28 UTC 2023 x86_64 x86_64 x86_64 GNU/Linux的系统上测试时(系统同时挂载了cgroup v1和cgroup v2, cgroup v2 挂载在/sys/fs/cgroup/unified目录下)，发现"cgroup/connect4"挂载到 /sys/fs/cgroup/unified根目录时，可以正常工作。若在/sys/fs/cgroup/unified目录下创建一个子目录test，将"cgroup/connect4"挂载到/sys/fs/cgroup/unified/test时，可以挂载成功，但程序并没有执行。

若在Ubuntu 22.04 LTS,内核版本 Linux monster 5.15.0-37-generic #39-Ubuntu SMP Wed Jun 1 19:16:45 UTC 2022 x86_64 x86_64 x86_64 GNU/Linux(系统上只挂载了cgroup v2在 /sys/fs/cgroup)，挂载上述同样的ebpf程序到子目录下，则可以正常工作

挂载程序使用的是 cilium的ebpf github.com/cilium/ebpf v0.12.2 支持cgroup v2 

测试用的ebpf程序:

~~~c
//go:build ignore
#include <linux/version.h>
#include <linux/ptrace.h>
//#include <uapi/linux/bpf.h>
#include <linux/bpf.h>
#include <linux/filter.h>
#include <bpf/bpf_helpers.h>
#include<bpf/bpf_endian.h>
#include <sys/socket.h>
#include <netinet/in.h>


char __license[] SEC("license") = "Dual MIT/GPL";


SEC("cgroup/connect4")
static int connect_hook(struct bpf_sock_addr *sk) {
    bpf_printk("connect hook\n");
	return 1;
}

SEC("cgroup/bind4")
static int bind_hook(struct bpf_sock_addr *sk) {
    bpf_printk("bind hook\n");
	return 1;
}
~~~

### 问题2：

在Ubuntu 20.04 LTS, 内核版本Linux 5.4.0-165-generic #182-Ubuntu SMP Mon Oct 2 19:43:28 UTC 2023 x86_64 x86_64 x86_64 GNU/Linux的系统上测试时(系统同时挂载了cgroup v1和cgroup v2, cgroup v2 挂载在/sys/fs/cgroup/unified目录下)。尝试挂载到cgroup v1的某个层级的子目录时比如/sys/fs/cgroup/cpu/ebpf_cgroup_test 时报EBADF错误

<font color='red'>cgroup 类型ebpf程序支持cgroup v1么</font>

### 问题2 剖析

分析一下cgroup类型 ebpf程序的挂载，看看linux-5.4.0内核是否支持cgroup v1

#### bpf_prog_attach

系统调用bpf传入BPF_PROG_ATTACH命令参数，实际调用的是bpf_prog_attach(kernel/bpf/syscall.c)。下面简单看一下bpf_prog_attach针对BPF_PROG_TYPE_CGROUP_SOCK_ADDR类型挂载的执行过程：

* 权限检查

* 通过attr->attach_type确定程序类型ptype。可以发现BPF_CGROUP_INET4_BIND、BPF_CGROUP_INET4_CONNECT等挂载类型的程序类型都是BPF_PROG_TYPE_CGROUP_SOCK_ADDR

* 针对ptype为BPF_PROG_TYPE_CGROUP_SOCK_ADDR的类型，实际是调用cgroup_bpf_prog_attach 进一步处理

  

~~~c
static int bpf_prog_attach(const union bpf_attr *attr)
{
	enum bpf_prog_type ptype;
	struct bpf_prog *prog;
	int ret;

	if (!capable(CAP_NET_ADMIN))
		return -EPERM;

	if (CHECK_ATTR(BPF_PROG_ATTACH))
		return -EINVAL;

	if (attr->attach_flags & ~BPF_F_ATTACH_MASK)
		return -EINVAL;

	switch (attr->attach_type) {
	case BPF_CGROUP_INET_INGRESS:
	case BPF_CGROUP_INET_EGRESS:
		ptype = BPF_PROG_TYPE_CGROUP_SKB;
		break;
	case BPF_CGROUP_INET_SOCK_CREATE:
	case BPF_CGROUP_INET4_POST_BIND:
	case BPF_CGROUP_INET6_POST_BIND:
		ptype = BPF_PROG_TYPE_CGROUP_SOCK;
		break;
	case BPF_CGROUP_INET4_BIND:
	case BPF_CGROUP_INET6_BIND:
	case BPF_CGROUP_INET4_CONNECT:
	case BPF_CGROUP_INET6_CONNECT:
	case BPF_CGROUP_UDP4_SENDMSG:
	case BPF_CGROUP_UDP6_SENDMSG:
	case BPF_CGROUP_UDP4_RECVMSG:
	case BPF_CGROUP_UDP6_RECVMSG:
		ptype = BPF_PROG_TYPE_CGROUP_SOCK_ADDR;
		break;
	case BPF_CGROUP_SOCK_OPS:
		ptype = BPF_PROG_TYPE_SOCK_OPS;
		break;
	case BPF_CGROUP_DEVICE:
		ptype = BPF_PROG_TYPE_CGROUP_DEVICE;
		break;
	case BPF_SK_MSG_VERDICT:
		ptype = BPF_PROG_TYPE_SK_MSG;
		break;
	case BPF_SK_SKB_STREAM_PARSER:
	case BPF_SK_SKB_STREAM_VERDICT:
		ptype = BPF_PROG_TYPE_SK_SKB;
		break;
	case BPF_LIRC_MODE2:
		ptype = BPF_PROG_TYPE_LIRC_MODE2;
		break;
	case BPF_FLOW_DISSECTOR:
		ptype = BPF_PROG_TYPE_FLOW_DISSECTOR;
		break;
	case BPF_CGROUP_SYSCTL:
		ptype = BPF_PROG_TYPE_CGROUP_SYSCTL;
		break;
	case BPF_CGROUP_GETSOCKOPT:
	case BPF_CGROUP_SETSOCKOPT:
		ptype = BPF_PROG_TYPE_CGROUP_SOCKOPT;
		break;
	default:
		return -EINVAL;
	}

	prog = bpf_prog_get_type(attr->attach_bpf_fd, ptype);
	if (IS_ERR(prog))
		return PTR_ERR(prog);

	if (bpf_prog_attach_check_attach_type(prog, attr->attach_type)) {
		bpf_prog_put(prog);
		return -EINVAL;
	}

	switch (ptype) {
	case BPF_PROG_TYPE_SK_SKB:
	case BPF_PROG_TYPE_SK_MSG:
		ret = sock_map_get_from_fd(attr, prog);
		break;
	case BPF_PROG_TYPE_LIRC_MODE2:
		ret = lirc_prog_attach(attr, prog);
		break;
	case BPF_PROG_TYPE_FLOW_DISSECTOR:
		ret = skb_flow_dissector_bpf_prog_attach(attr, prog);
		break;
	default:
		ret = cgroup_bpf_prog_attach(attr, ptype, prog);
	}

	if (ret)
		bpf_prog_put(prog);
	return ret;
}
~~~



#### cgroup_bpf_prog_attach

执行过程:

* attr->target_fd实际是cgroup 目录的路径对应的fd, 调用cgroup_get_from_fd 

~~~c
int cgroup_bpf_prog_attach(const union bpf_attr *attr,
			   enum bpf_prog_type ptype, struct bpf_prog *prog)
{
	struct cgroup *cgrp;
	int ret;

	cgrp = cgroup_get_from_fd(attr->target_fd);
	if (IS_ERR(cgrp))
		return PTR_ERR(cgrp);

	ret = cgroup_bpf_attach(cgrp, prog, attr->attach_type,
				attr->attach_flags);
	cgroup_put(cgrp);
	return ret;
}
~~~

#### cgroup_get_from_fd

目前发现只有cgroup_get_from_fd会返回EBADF错误，有两个地方会返回此错误：css_tryget_online_from_dir、cgroup_on_dfl。打算用kprobe确定一下是哪个函数返回的

~~~c

/**
 * cgroup_get_from_fd - get a cgroup pointer from a fd
 * @fd: fd obtained by open(cgroup2_dir)
 *
 * Find the cgroup from a fd which should be obtained
 * by opening a cgroup directory.  Returns a pointer to the
 * cgroup on success. ERR_PTR is returned if the cgroup
 * cannot be found.
 */
struct cgroup *cgroup_get_from_fd(int fd)
{
	struct cgroup_subsys_state *css;
	struct cgroup *cgrp;
	struct file *f;

	f = fget_raw(fd);
	if (!f)
		return ERR_PTR(-EBADF);

	css = css_tryget_online_from_dir(f->f_path.dentry, NULL);
	fput(f);
	if (IS_ERR(css))
		return ERR_CAST(css);

	cgrp = css->cgroup;
	if (!cgroup_on_dfl(cgrp)) {
		cgroup_put(cgrp);
		return ERR_PTR(-EBADF);
	}

	return cgrp;
}
~~~



## cgroup 类型ebpf对内核的要求

* linux 5.4.0 不支持ebpf 挂载到cgroup v1

## 参考

* ebpf程序类型和对应的attach type https://www.kernel.org/doc/html/latest/bpf/libbpf/program_types.html