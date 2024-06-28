# ebpf

[TOC]



## 编译环境



## 调试工具

bpf_printk 用来输出信息，用法类似printf。bpf_printk实际是bpf_trace_printk的封装。bpf_trace_printk的输出信息可通过/sys/kernel/debug/tracing/trace_pipe查看,亦或通过bpftool prog tracelog查看

bpf_printk的详细介绍:https://nakryiko.com/posts/bpf-tips-printk/

### 反编译bpf字节码

~~~
llvm-objdump -o --source x.o
~~~

### ebpf可使用的帮助函数

可使用的帮助函数所在内核源码树中头文件 include/uapi/linux/bpf.h。bpf.h 定义了helper 函数对应的id，因此可以确定不同版本内核提供了哪些helper 函数。verifier会通过helper 函数id检查helper 函数是否可用

~~~c
#define __BPF_ENUM_FN(x) BPF_FUNC_ ## x
enum bpf_func_id {
	__BPF_FUNC_MAPPER(__BPF_ENUM_FN)
	__BPF_FUNC_MAX_ID,
};
~~~



## bpf 内核相关

### bpf 内核源码

* bpf 系统调用函数的实现在kernel/bpf/syscall.c文件中。

* bpftool 源码在tools/bpf/bpftool目录中

### 内核中ebpf程序示例

内核中有大量的ebpf示例程序，分别位于以下两个目录中:

* samplse/bpf
* tools/testing/selftests/bpf

### 内核中samples/bpf中的代码编译

在内核树下面编译步骤:

* make menuconfig
* make prepare
* make M=samples/bpf 编译指定模块

### 内核对ebpf的支持

参考 https://github.com/iovisor/bcc/blob/master/docs/kernel-versions.md

## 遇到的问题

### 访问内核定义的某个结构体

直接访问某个内核定义的结构体会导致无效内存访问的错误，可以使用BPF_CORE_READ来避免上述错误

~~~c
SEC("kprobe/__nf_conntrack_hash_insert")
int kprobe__nf_conntrack_hash_insert(struct pt_regs *ctx){
    struct nf_conn *ct = (struct nf_conn *)PT_REGS_PARM1(ctx);
    unsigned int hash = (unsigned int) PT_REGS_PARM2(ctx);
    unsigned int reply_hash = (unsigned int)PT_REGS_PARM3(ctx);
    bpf_printk("nf_conntrack_hash_insert\n");
    //struct nf_conntrack_tuple *src_tuple = &ct->tuplehash[IP_CT_DIR_ORIGINAL].tuple;
    //struct nf_conntrack_tuple *src_tuple = BPF_CORE_READ(ct, tuplehash);
    struct  nf_conntrack_tuple_hash *tuple_hash= BPF_CORE_READ(ct, tuplehash);
    struct nf_conntrack_tuple *src_tuple = &(tuple_hash[IP_CT_DIR_ORIGINAL].tuple);
}
~~~



### 如何关联kprobe/uprobe的函数入参和返回值

使用bpf_get_current_pid_tgid() 获取的id((tgid用于标识进程，pid用于标识线程)作为map的key, 关联kprobe/uprobe的上下文信息，会不会有并发问题)。应该会产生lost update 问题。实际发现其他产品基本上是使用的id作为map的key，为什么作为key没有问题

### 如何在不同的ebpf程序共享同一个map

一种设想的方案：

* ebpf 程序1 将map地址传到用户态，
* 用户态再将ebpf 程序1使用的map地址传递到ebpf 程序2
* ebpf程序2 使用该地址

方案2：

* 用户程序将ebpf 程序1使用的map的fd传到ebpf 程序2
* ebpf 程序2 使用bpf_sys_bpf 函数根据 map的fd去访问map 

失败，bpf_sys_bpf 在5.4内核上不支持。目前看好像只有BPF_PROG_TYPE_SYSCALL类型的program才支持使用bpf_sys_bpf函数

方案3：

多种类型的ebpf程序在一个文件

### ebpf程序对应的SEC

可在内核树tools\lib\bpf\libbpf.c文件中找到(5.4内核)

![image-20231129100049155](D:\个人笔记\doc\ebpf\ebpf.assets\image-20231129100049155.png)



### ebpf代码如何分布到不同的文件

* 使用一个.c源文件，然后include 其他源文件
* 使用bpftool gen object 将多个.o文件合并成一个。对bpftool版本有要求

## 常见错误

###  不支持对应的bpf helper 函数

不是每个ebpf程序类型都可以调用所有的ebpf helper函数，每个内核版本支持的helper函数也是不一样的。所以有时会遇到以下错误

~~~
load program: invalid argument: unknown func bpf_sys_bpf#166
~~~

~~~
/* If BPF verifier doesn't recognize BPF helper ID (enum bpf_func_id)
	 * at all, it will emit something like "invalid func unknown#181".
	 * If BPF verifier recognizes BPF helper but it's not supported for
	 * given BPF program type, it will emit "unknown func bpf_sys_bpf#166".
	 * In both cases, provided combination of BPF program type and BPF
	 * helper is not supported by the kernel.
	 * In all other cases, probe_prog_load() above will either succeed (e.g.,
	 * because BPF helper happens to accept no input arguments or it
	 * accepts one input argument and initial PTR_TO_CTX is fine for
	 * that), or we'll get some more specific BPF verifier error about
	 * some unsatisfied conditions.
	 */
~~~



### ebpf程序挂载

### 使用bpf 系统调用

### 使用netlink

在5.4.0内核不支持使用bpf系统调用挂载xdp、tc类型的ebpf程序

* xdp
* tc

## 限制

虽然eBPF功能强大，但是内核中的eBPF技术还是使用了很多限制以确保内核处理的安全和及时。但是随着技术的发展和演进，这些限制可能会逐步放宽或者提供了相应的解决方案:

- eBPF程序并不能随意调用内核参数，而是仅仅限制在内核模块列出的 `BPF Helper` 函数。不过这个支持函数列表随着内核发展而增长
- eBPF 程序不允许包含无法访问的指令，以防止加载无效代码和延迟程序终止
- eBPF 程序中的循环数量是有限的，并且必须在有限的时间内结束，这主要用于防止在 kprobes 中插入任意循环，从而导致锁定整个系统
  - 解决方案包括扩展循环和为需要循环的常见用途添加辅助函数
  - Linux 5.3 在 BPF 中包含对有界循环的支持，它在运行时具有可验证的上限
- eBPF 堆栈大小限制为 `MAX_BPF_STACK` ，这个值从内核5.8开始设置为 512 ; 详细参考 `include/linux/filter.h`
  - 当在堆栈上存储多个字符串缓冲区时，此限制特别相关: 一个 char[256] 缓冲区将消耗此堆栈的一半
  - 注意: 没有增加这个限制的计划 – 解决方案是切换到 bpf map，这实际上是无限的
- eBPF字节码大小最初限制为 4096 条指令，但从内核 Linux 5.8 开始，现在已经放宽到 100 万条指令（ `BPF_COMPLEXITY_LIMIT_INSNS` ）详细参考 `include/linux/bpf.h`
  - 4096 条指令限制（ `BPF_MAXINSNS` ）仍然是 保留给非特权 BPF 程序
  - 新版本的eBPF还支持级联调用多个eBPF程序(不过传递信息方面存在一定限制)，可以组合起来实现更多强大功能



## 参考文档

* 内核源码 samples/bpf/bpf_load.c
* bpf 文档 https://docs.kernel.org/bpf/index.html
* xdp https://github.com/xdp-project/xdp-tools
* The eXpress Data Path: Fast Programmable Packet Processing in the Operating System Kernel https://dl.acm.org/doi/pdf/10.1145/3281411.3281443
* ebpf程序可使用的helper 函数文档 https://www.man7.org/linux/man-pages/man7/bpf-helpers.7.html
* ebpf网络相关的程序类型 https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/9/html/configuring_and_managing_networking/assembly_understanding-the-ebpf-features-in-rhel-9_configuring-and-managing-networking#doc-wrapper
* libbpf-bootstrap、libbpf
* 《bpf performance tools》
* tc https://www.coverfire.com/articles/queueing-in-the-linux-network-stack/
* https://qmonnet.github.io/whirl-offload/2016/09/01/dive-into-bpf/
* 内核版本对ebpf的支持  https://github.com/iovisor/bcc/blob/master/docs/kernel-versions.md
* BPF CO-RE BPF 可移植性 https://nakryiko.com/posts/bpf-portability-and-co-re/

### 内核相关参考文档

* https://blog.packagecloud.io/monitoring-tuning-linux-networking-stack-receiving-data/
* https://blog.packagecloud.io/the-definitive-guide-to-linux-system-calls/
* https://blog.packagecloud.io/how-does-strace-work/

### 应用产品

* Cilium https://static.sched.com/hosted_files/kccncna19/20/eBPF%20and%20the%20Cilium%20Datapath.pdf
* kinding
* pixie
* 

