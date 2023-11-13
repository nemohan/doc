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



## bpf 内核源码

* bpf 系统调用函数的实现在kernel/bpf/syscall.c文件中。

* bpftool 源码在tools/bpf/bpftool目录中

## 开发工具

* c 语言， libbpf
* go, cilium ebpf
* 

## 内核中ebpf程序示例

内核中有大量的ebpf示例程序，分别位于以下两个目录中:

* samplse/bpf
* tools/testing/selftests/bpf



## 内核中samples/bpf中的代码编译

在内核树下面编译步骤:

* make menuconfig
* make prepare
* make M=samples/bpf 编译指定模块

## 经验

### 如何确定ebpf中hook函数的原型

在写和cgroup相关的ebpf程序中，想确定BPF_PROG_TYPE_CGROUP_INET4_CONNECT类型的hook的函数原型，从网上搜索没有找到想要的答案。因为INET4_CONNECT类型的hook是tcp尝试连接ipv4类型的地址时调用。所以优先从内核树net/ipv4/tcp_ipv4.c文件中搜索，搜索结果图所示。由此可以确定hook的原型为int xxx(struct sock *sk, struct sockaddr *uaddr)，按照上面的分析写了一个挂载到"cgroup/connect4"的程序时，编译无法通过，函数原型不对 :(



![image-20231030102132606](D:\个人笔记\doc\epbf\ebpf.assets\image-20231030102132606.png)



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

使用bpf_get_current_pid_tgid 获取的id作为map的key, 关联kprobe/uprobe的上下文信息，会不会有问题(并发问题)。tgid用于标识进程，pid用于标识线程。一个线程不会有并发应该不会有问题。



## 限制

虽然eBPF功能强大，但是内核中的eBPF技术还是使用了很多限制以确保内核处理的安全和及时。但是随着技术的发展和演进，这些限制可能会逐步放宽或者提供了相应的解决方案:

- eBPF程序并不能随意调用内核参数，而是仅仅限制在内核模块列出的 `BPF Helper` 函数。不过这个支持函数列表随着内核发展而增长
- eBPF 程序不允许包含无法访问的指令，以防止加载无效代码和延迟程序终止
- eBPF 程序中的循环数量是有限的，并且必须在有限的时间内结束，这主要用于防止在 kprobes 中插入任意循环，从而导致锁定整个系统
  - 解决方案包括扩展循环和为需要循环的常见用途添加辅助函数
  - Linux 5.3 在 BPF 中包含对有界循环的支持，它在运行时具有可验证的上限
- eBPF 堆栈大小限制为 `MAX_BPF_STACK` ，这个值从内核5.8开始设置为 512 ; 详细参考 `include/linux/filter.h`
  - 当在堆栈上存储多个字符串缓冲区时，此限制特别相关: 一个 char[256] 缓冲区将消耗此堆栈的一半
  - 注意: 没有增加这个限制的计划 – 解决方案是切换到 bpf 映射存储，这实际上是无限的
- eBPF字节码大小最初限制为 4096 条指令，但从内核 Linux 5.8 开始，现在已经放宽到 100 万条指令（ `BPF_COMPLEXITY_LIMIT_INSNS` ）详细参考 `include/linux/bpf.h`
  - 4096 条指令限制（ `BPF_MAXINSNS` ）仍然是 保留给非特权 BPF 程序
  - 新版本的eBPF还支持级联调用多个eBPF程序(不过传递信息方面存在一定限制)，可以组合起来实现更多强大功能



## 参考文档

* 内核源码 samples/bpf/bpf_load.c
* bpf 文档 https://docs.kernel.org/bpf/index.html
* xdp https://github.com/xdp-project/xdp-tools

* The eXpress Data Path: Fast Programmable Packet Processing in the Operating System Kernel https://dl.acm.org/doi/pdf/10.1145/3281411.3281443
* ebpf程序可使用的helper 函数文档 https://www.man7.org/linux/man-pages/man7/bpf-helpers.7.html
* libbpf-bootstrap、libbpf