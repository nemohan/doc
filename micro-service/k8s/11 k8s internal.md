# k8s internal



[TOC]



### k8s的架构

#### k8s的组成

k8s集群由以下两部分组成:

* Control Plane (控制面板) 控制整个集群的工作

* Worker Node



##### Control Plane 由以下几部分组成:

* etcd
* API Server
* Scheduler
* Controller Manager

control Plane组件一般运行在master node 上

在同一个K8s集群中，每个Control Plane组件可以运行多个实例。但只有一个Scheduler和Controller Manager实例处于激活模式，其他实例处于待机状态

查看Control plane组件的状态:

~~~bash
$ kubectl get componentstatuses
NAME STATUS MESSAGE ERROR
scheduler Healthy ok
controller-manager Healthy ok
etcd-0 Healthy {"health": "true"}
~~~

![1587176891349](./${img}\1587176891349.png)
##### 在worker node上运行的组件:

* Kubelet
* Kubernetes Service Proxy(kube-proxy)服务代理
* Container Runtime(Docker, rkt获取其他)。容器运行时环境



##### 插件

* k8s DNS server
* Dashboard
* Ingress controller
* Heapster
* Container Network Interface (容器网络接口)



架构示意图如下:

![1587174246390](./${img}\1587174246390.png)




##### 组件间的通信方式

k8s的组件都只和API Server通信，其他组件直间没有通信。API server 负责和etcd通信



##### 组件运行方式

Control Plane的组件既可以直接以二进制的方式运行在系统上,也可以以pod方式运行。Kubelet是唯一一个直接运行在系统上的组件。kubelet可以让其他组件以pod方式运行

查看以pod方式运行的control plane 组件: custom-columns 选项指定显示的列, sort-by指定排序列

~~~
kubectl get po -o custom-columns=POD:metadata.name,NODE:spec.nodeName --sort-by spec.nodeName -n kube-system
~~~



##### etcd的使用

#### API Server的工作机制

![1587175168427](./${img}\1587175168427.png)


##### 事件通知机制

API server 并不会创建pod,也不会管理service 的endoints，这些都是Controller Manager的工作。也不会命令这些控制器该做什么。而是使用事件通知的方式，控制器订阅自己感兴趣的事件，当事件发生时采取对应的行动。

![1587180731268](./${img}\1587180731268.png)


当部署Pod时，可以用下面命令观察事件:

~~~
kubectl get pods --watch
~~~



#### scheduler 调度器



#### controller manager

常见的controller:

* Replication Manager
* ReplicaSet、DaemonSet、Job controller
* Deployment controller
* Node controller
* StatefulSet controller
* Service controller
* EndPoints controller
* Namespace controller
* PersistentVolume controller
* 其他

### Kubelet 和 k8s service proxy

#### kubelet

简单来讲，kubelet负责worker node的一切工作。开始时将其所在的node作为资源注册到API server，然后监视API server 关于pod的事件，如pod调度到当前node,kubelet则启动容器并监视容器运行，此外还有pod的删除、live probe

##### 不依赖API server的情况下运行静态Pod

如下图，一般用于以pod方式运行的Control Plane组件

![1587258789835](./${img}\1587258789835.png)


#### k8s service proxy(服务代理-kube-proxy)

初代的service proxy 以运行在用户态的代理来实现, 即一个服务进程接收链接并代理到Pod。为了拦截到service ip的链接，service proxy 会配置iptables

![1587258934970](./${img}\1587258934970.png)


现代版本的service proxy 直接通过修改iptables,将链接直接转发到对应的pod，而不再经过proxy server。也叫做iptables proxy

![1587259196442](./${img}\1587259196442.png)


二者的差异:

* 使用代理服务器的service-proxy 效率较低，数据包要经过用户空间的代理服务器，再转发到pod。而使用iptables proxy的数据包不经过用户空间
* 使用代理服务器的service-proxy以round-robin算法选择pod, iptables proxy则随机选择pod



### 以pod的创建为例，展示k8s的完整工作流程

![1587261172582](./${img}\1587261172582.png)




![1587261231562](./${img}\1587261231562.png)


### 构建高可用k8s集群

为构建高可用k8s集群，control plane 的每个组件需要运行多个实例，如下图所示：

control plane 所包含的组件:

* etcd etcd是一个分布式的高可用的kv存储系统，所以运行多个实例毫无问题
* API server 是无状态的服务器，所以也可以多个实例同时运行。通过将API server和 etcd运行在一起，可以避免使用load balancer 来访问api server。
* Scheduler 
* Controller Manager



![1587430082686](./${img}\1587430082686.png)


controller manager 和scheduler 需要使用leader-election(领导选举)算法，来产生主节点。这些组件使用的选举算法是通过在API server上创建资源(endpoints资源）来实现，第一个创建资源成功的就是leader

![1587431189604](./${img}\1587431189604.png)


下图中control-plane.alpha.kubernetes.io/leader, holderIdentity的值即leader的名称

![1587431435804](./${img}\1587431435804.png)
### 常用命令

~~~
kubectl attach 					#类似kubectl exec， 不过是附加到容器的主进程，而不是运行其他进程

kubectl get po -o custom-columns=POD:metadata.name,NODE:spec.nodeName --sort-by spec.nodeName -n kube-system   # 查看以pod方式运行的Control plane 组件

kubectl get pods --watch 		#监听事件
~~~

