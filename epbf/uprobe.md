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