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

## kretprobe

获取被hook函数的返回值用PT_REGS_RC函数

### 函数原型

int hook(pt_regs *ctx)