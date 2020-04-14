# go runtime 的一些疑问



[TOC]



### 总结

##### 启动阶段

runtime.rt0_go 调用相关的初始化函数，来设置runtime。其中runtime.sched_init 会准备好m的运行队列。创建主协程运行main.main函数

### syscall的行为

 进入系统调用时，p的状态改变为_Psyscall。 sysmon会将处于 _Psyscall状态的p 安排到其他的m进行调度。有可能会增加线程M的数量

###  什么时候增加m的数量 

* 在启用了netpoll的情况下，injectglist 会根据情况增加系统线程的数量

* 第二种情况见 sysmon

###  什么时候减少m的数量:



### 假设CPU核数目的M处于系统调用。M的数量会不会多余CPU核心数目





