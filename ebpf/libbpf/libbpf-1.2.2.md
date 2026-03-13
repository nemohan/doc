# libbpf-1.2.2

[TOC]

本文以libbpf-1.2.2版本为分析对象。



## ebpf目标文件解析



## 加载ebpf到内核



## 新特性

* libbpf-1.0竟然支持将多个ebpf目标文件连接成一个目标文件，:))

* SEC("ksyscall/<syscall>")、SEC("kretsyscall")

* 针对uprobes，用户不再需要指定程序或库的绝对路径、函数的偏移量等。libbpf会完成上述动作

* 不再支持"legacy map"定义

  

## 参考



* https://nakryiko.com/posts/libbpf-v1/