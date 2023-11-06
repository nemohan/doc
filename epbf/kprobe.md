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

