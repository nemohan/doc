# raft

[TOC]

记录实现raft协议过程中的一些细节及想法。加深理解避免二次踩坑

之前实现过raft协议，代码写的很烂，很难维护。这次尝试用设计模式中的state模式，看看是否能让代码更加清晰容易理解

## Leader election

选举过程见paper。

问题：

1) 在一轮选举过程中，共5个节点。假设node-1在term-1 投了node-2一票，此时又收到了node-3的term-2的投票请求，是否应该投票给node-3。原文是"Each server will vote for at most one candidate in a given term"。即可以投票给node-3

![image-20230717161644576](D:\个人笔记\doc\distributed-system\raft.assets\image-20230717161644576.png)



2) 5个节点选举，假设node-1在term-1成为candidate，并发起了投票。此时收到了node-2在term-2的投票请求，是否应该投票给node-2。paper中没有具体指明如何操作。但有这么一段" Rules for all servers:If RPC request or response contains term T > currentTerm: set currentTerm = T, convert to follower "，如此一来，可以投票给node-2，或放弃投票

![image-20230717164828567](D:\个人笔记\doc\distributed-system\raft.assets\image-20230717164828567.png)

3） votedFor 需不需要置空

原文"candidateId that received vote in current term"。是不是意味着当current term自增后，需要将votedFor置空。在实现时我选择了将votedFor置空

![image-20230719182409792](D:\个人笔记\doc\distributed-system\raft.assets\image-20230719182409792.png)



4）requestVote和appendEntry rpc 请求等待时间设置。不设置或设置过大，可能导致节点的election timeout已经超时，而仍然在等待rpc返回结果。从而导致选举时间过长或选举阻塞



### 遇到的bug

* 同一个term，有两个leader即“脑裂”。代码切换节点"角色" 和设置leader的currentTerm之间的并发导致的。加一些Assert很有必要

## Log replication

发往follower的日志的起始点由nextIndex决定:

![image-20230725163606380](D:\个人笔记\doc\distributed-system\raft.assets\image-20230725163606380.png)

commit

![image-20230721135704697](D:\个人笔记\doc\distributed-system\raft.assets\image-20230721135704697.png)



leader 的commitIndex的更新：

![image-20230726151745683](D:\个人笔记\doc\distributed-system\raft.assets\image-20230726151745683.png)



### 忽略的细节

下面是实现raft协议时忽略的细节，导致几个bug

* <font color='green'>处理带log的AppendEntry rpc时，需要检查 log是否重复。若没有重复再添加到本地logs中</font>。

* 除检查prevLogIndex、prevLogTerm是否匹配之外。还需要检查prevLogIndex+1 的log是否存在term冲突。

  

  ~~~
  集群共有5个节点node-0到node-4
  在term-1, node-0成为leader
  	在term-1, node-0到node-4都将index-1、cmd-10的log commit
  	term-1, node-0收到cmd-20的 log。但尚未将其复制到任何其他节点，出现网络故障，因此不能联系到任何其他节点
  	
  	各节点的日志:
  	node-0:	[cmd-10]	[cmd-20]	[]
  	node-1:	[cmd-10]
  	node-2: [cmd-10]
  	node-3:	[cmd-10]
  	node-4: [cmd-10]
  	
  term-10, node-2 成为leader
  	在term-10, node-2、node-1、node-3都将index-2、cmd-30的log commit
  	将term-10、cmd:30、prevIndex-0、prevTerm-1的 appendEntry 发送到node-0时，未检查prevIndex+1的log是否冲突，从而错误的将 index-1、cmd-20的log commit
  
  09:57:51.613889 peer:0 handle append entry:++[ae: term:10 leader:2 prevIndex:0 prevTerm:1 entries:[{Cmd:30 Term:10}] commit:1]++ follower:[me:0 currentTerm:10 start_time:Jul 28 09:57:51.612041, votedFor:0 prev_state:0 
  		election_timeout:321ms] nLogs:2 entry:{Cmd:20 Term:1}, commit:0 applied:0
  09:57:51.613904 peer:0 check log entry. arg:++[ae: term:10 leader:2 prevIndex:0 prevTerm:1 entries:[{Cmd:30 Term:10}] commit:1]++
  09:57:51.613909 peer:0 commit index:0  term:10 cmd:20 real:2
  09:57:51.613914 peer:0 commit index:1  done
  09:57:51.613973 peer:2 send:++[ae: term:10 leader:2 prevIndex:1 prevTerm:10 entries:[{Cmd:1000 Term:10}] commit:1]++ to: server:4 reply:++[aer: term:10 success:false]++ ok:true
  09:57:51.614075 peer:2 send:++[ae: term:10 leader:2 prevIndex:0 prevTerm:1 entries:[{Cmd:30 Term:10}] commit:0]++ to: server:1 reply:++[aer: term:10 success:true]++ ok:true
  09:57:51.614082 peer:2 send:++[ae: term:10 leader:2 prevIndex:0 prevTerm:1 entries:[{Cmd:30 Term:10}] commit:1]++ to: server:0 reply:++[aer: term:10 success:true]++ ok:true
  09:57:51.614095 peer:2  next_index:2 match_index:1 for node:1 ++
  
  
  
  09:57:51.614113 peer:2 sInfo:[me:2 currentTerm:10 start_time:Jul 28 09:57:51.363027, votedFor:2 prev_state:0 
  		election_timeout:252ms] nLogs:3 entry:{Cmd:1000 Term:10}, commit:1 applied:1 match:[0 1 2 1 1] next:[1 2 1 2 2]
  09:57:51.614121 peer:2  next_index:3 match_index:2 for node:3 ++
  09:57:51.614132 peer:2 sInfo:[me:2 currentTerm:10 start_time:Jul 28 09:57:51.363027, votedFor:2 prev_state:0 
  		election_timeout:252ms] nLogs:3 entry:{Cmd:1000 Term:10}, commit:1 applied:1 match:[0 1 2 2 1] next:[1 2 1 3 2]
  09:57:51.614165 0: log map[1:10]; server map[1:10 2:30]
  09:57:51.614179 0: log map[1:10]; server map[1:10 2:30]
  09:57:51.614188 0: log map[1:10]; server map[1:10 2:30]
  09:57:51.614225 apply error: commit index=2 server=0 20 != server=3 30
  ~~~









