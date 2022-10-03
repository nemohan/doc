# kafka

[TOC]

## 生产者



《kafka权威指南》读书笔记

## 4 消费者

### 消费者组

kafka的消费者一般会归属某个消费者组(可能存在不属于任何组的消费者，不常见)。当多个消费者订阅一个topic并且归属同一个消费者组，每个消费者组中的消费者会从topic的不同分片(partition)收到消息。

第一个加入组的消费者是该组的leader。leader拥有全局视图，决定partition分配到哪个consumer



### 再平衡(rebalance)

rebalance: partition重新分配到消费者的机制

当新的消费者加入到消费者组、消费者宕机、离开消费者组都会触发再平衡。再平衡期间会有短暂的窗口期，导致消费者收不到消息

<font color="red">?当再平衡后，消费者会从partition的最近的commited offset位置开始读取记录</font>

### 订阅

一个消费者可以订阅多个topic，topic支持正则表达式



### 配置项

#### fetch.min.bytes

允许消费者指定其想收到的最小字节数。若broker数据不足则等待

#### fetch.max.wait.ms

控制当服务器端数据不足时的最大等待时间。即超过此时间之后即使数据不足，也将数据给消费者

#### max.partition.fetch.bytes

控制broker对每个partition返回给消费者的最大字节数。默认1MB

#### session.timeout.ms

broker认为consumer挂掉的超时时间。默认3秒

#### auto.offset.reset

当消费者读取partition的数据而又没有commited offset或commited offset已经时，决定消费者的行为。默认是"latest"，即从最新的record开始读取(最新是最新的record还是最新的commited offset的record)。另一个是 "earliest",即读取partition的全部数据

#### enable.auto.commit

控制是否允许消费者自动commit offset，默认是true。设置成false，则自己控制何时提交。auto.commit.interval.ms控制自动提交的频率

#### partition.assignment.strategy

partition分配策略：

* Range: 给每个消费者分配其所订阅的topic的连续的几个partition。如有两个消费者C1和C2都订阅了topic T1和T2。每个topic有3个partition。那么C1将会被分配 topic T1和T2的0和1 partition(共4个partition)。C2则会被分配T1、T2的partition 2
* RoundRobin: 将所有订阅的topics的所有partition顺序的分配给消费者。假设上面的例子使用RoundRobin分配策略，则C1会被分配T1的0和2 partition, T2的 partition 1。C2则会被分配T1的partition 1 和 T2的partition 0、partition2
* 自定义策略
* 

#### max.poll.records

### commit and offset

当commited offset小于consumer最后处理的消息的offset时，会导致commited offset 和最后消息的offset之间的数据被重复处理(partition rebalance时容易发生)。

当commited offset 大于consumer最后处理的消息的offset时，commited offset 和最后消息的offset之间的数据会丢失(得不到处理)

#### 提交方式

* 同步提交(出错会自动重试)
* 异步提交(出错不会自动重试)
* 提交指定partition的指定offset



消费者可以指定任意的offset开始读取

### rebalance 监听



### 注意

* 消费者组中的消费者数目超过topic的partition时，多出的消费者会空闲
* 可以使用多个消费者组(每个组属于一个独立的应用)去订阅一个topic。
* 消费者通过心跳保持来维持消费者在消费者组和对partition的所有权的关系
* commit使用不当可能导致数据重复处理或得不到处理
* consumer 需要优雅的退出以及时触发rebalance。而不是通过会话超时触发



### 疑问

* 属于同一个消费者组的消费者可以订阅不同的topic么
* 同一个消费者组的消费者怎么保证收到消息的顺序性，假设应用逻辑要求消息按顺序处理
* 







## 疑问

* 消费者是通过轮询接收数据，还是broker推送数据到消费者