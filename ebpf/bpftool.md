

# bpftool

[TOC]



## bpftool 子命令

### prog

kprobe类型程序

~~~
bpftool prog load kprobe_kern.o /sys/fs/bpf/kprobe_kern
~~~

用bpftool虽然能挂载成功，但ebpf代码不会被执行，还需要其他操作

删除kprobe类型，可以直接删除/sys/fs/bpf/kprobe_kern文件

### cgroup

挂载cgroup 类型

~~~
bpftool cgroup attach /sys/fs/cgroup/unified/ebpf_cgroup_test connect4 id 59
~~~

卸载

~~~
bpftool cgroup detach /sys/fs/cgroup/unified/ebpf_cgroup_test/ connect4 id 59
~~~

查看挂载到指定cgroup的所有ebpf程序:

~~~
bpftool cgroup tree /sys/fs/cgroup/unified/ebpf_cgroup_test
~~~

### gen

从ebpf 目标文件生成辅助加载的源文件

bpftool 5.4版本不支持



~~~
bpftool gen skeleton kprobe_kern.o > kprobe.h
~~~



### net

用于挂载xdp、tc类型ebpf程序

~~~
Usage: /usr/lib/linux-tools/5.4.0-166-generic/bpftool net { show | list } [dev <devname>]
       /usr/lib/linux-tools/5.4.0-166-generic/bpftool net attach ATTACH_TYPE PROG dev <devname> [ overwrite ]
       /usr/lib/linux-tools/5.4.0-166-generic/bpftool net detach ATTACH_TYPE dev <devname>
       /usr/lib/linux-tools/5.4.0-166-generic/bpftool net help

       PROG := { id PROG_ID | pinned FILE | tag PROG_TAG }
       ATTACH_TYPE := { xdp | xdpgeneric | xdpdrv | xdpoffload }

Note: Only xdp and tc attachments are supported now.
      For progs attached to cgroups, use "bpftool cgroup"
      to dump program attachments. For program types
      sk_{filter,skb,msg,reuseport} and lwt/
~~~



### btf

生成vmlinux.h文件, vmlinux.h文件目的参考: https://www.kernel.org/doc/html/latest/bpf/libbpf/libbpf_overview.html。使用vmlinux.h可以避免引用一些kernel未暴露出来的头文件，不然需要在samples/bpf/目录下编译

~~~
bpftool btf dump file /sys/kernel/btf/vmlinux format c > vmlinux.h
~~~



## 查看日志

查看ebpf调用bpf_printk输出的日志

~~~bash
bpftool prog tracelog
~~~

## 源码

bpftool源码位于内核 tools/bpf/bpftool目录下

## 参考

* bpftool命令教程  https://qmonnet.github.io/whirl-offload/2021/09/23/bpftool-features-thread/