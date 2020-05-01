---
typora-root-url: ./
---

# ReplicationCtroller

[TOC]



### pod的存活检查机制(live probe)

在某些情况下，程序宕机并非进程崩溃而是因为死锁。k8s无法检测这种程序宕机也就无法重启。这时就需要存活检查机制。

k8s支持三种存活检查机制:

* http GET 请求, 请求app的一个指定路径，若响应是2xx或3xx则表明app正常运行。若响应的是其他错误码或没有响应，则认为app已经宕机。k8s就会重启
* TCP socket 会打开一个到指定容器端口的链接，如果链接成功，则表明app正常。否则重启

* exec  在容器内运行特定的命令并检查命令的返回码，若返回码为0，则表明app正常。否则重启



下图是使用http get 请求存活机制的实例：

![1585291425638](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1585291425638.png)



存活检查机制的参数:

* delay  设定容器启动之后多久开始进行存活检查，若delay=0s,容器一起动则立马进行存活检查
* timeout app响应存活检查请求的超时时间，若超过timeout设定的时间，则认为检查失败
* period 存活检查的时间间隔
* failure 存活检查失败次数。若连续失败次数超过设定值，则重启
* <font color="red">initialDelaySeconds 进行第一次存活检查的等待时间。若不设置这个值，容器启动之后立马进行存活检查很可能导致检查失败，不断重启容器</font>

注意:

* 可以通过使用kubectl describe pod < pod-name> 查看pod重启原因



### ReplicationController

k8s本身可以保证pod的健康存活，如果有崩溃的pod，k8s会自动创重启pod(kubelet负责重启)。但是当node宕机后，仅依靠k8s本身的机制，无法保证pod继续存活。引入的ReplicationController可以在node 宕机之后，迁移pod到其他的node。

<font color="red">rc的工作就是确保总是有期望数量且匹配指定标签的pod在运行</font>



##### rc的工作流程

![1585292561922](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1585292561922.png)

##### rc的三个关键组成部分

* label selector--决定哪些pod在rc的管辖范围内
* pod模板--创建pod副本时使用
* 期望的pod副本数量

![1585292684928](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1585292684928.png)





rc描述文件:

![1585293124792](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1585293124792.png)



![1585293194173](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1585293194173.png)



##### rc 的优势

高可靠、易伸缩

* 当pod被移除后，通过创建新的。确保指定数量的Pod持续运行。
* 集群node失效后，迁移pod到其他节点
* 可以通过手动或自动方式自动伸缩pod数量

##### <font color="red">注意</font>

* 更改了rc使用的pod模板不会影响当前正在运行的pod。稍后创建的pod才会受影响
* 更改了rc使用的label selector。当前正在运行的pod不受影响,但是当前在运行的pod不再rc的管辖范围内；另一方面更改之后，满足当前label selector的pod的数量可能为0. 则会创建指定数量的pod

### ReplicaSet 

ReplicaSet 是新版本的ReplicationController。和rc相比，rs有更强的label selector 表达能力

* rc 的label selector 只允许匹配包含特定label的pod, rs 还允匹配不包含特定label或特定的label key,而不关心label的值是什么。如rc不能同时匹配包含label env=production 和 env=devel的pods,只能匹配env=production或env=devel的pods；rs则能同时匹配二者



##### matchExpressions

![1585374728342](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1585374728342.png)

每个matchExpression 必须包含key、operator和values

支持的操作符:

* in label的值匹配其中某个指定的值
* notIn label的值不匹配指定的任意值
* Exists Pod必须包含特定key的label。这时可以不指定values。
* DoesNotExist Pod 必须不包label,不提供values





### DaemonSet

ds 确保每个集群node只运行一个pod实例，也可以通过label selector, 使pod运行在集群的某些node上。当某个运行pod的node失效后，在该node上运行且被ds管理的pod不会迁移到其他node上。当有新的node 加入集群，ds可以自动在新node上部署pod

若删除node的用于匹配ds的label, pod也会随之结束运行

删除ds会删除所有的pod

下图展示的是ds管理的pod只运行在有标签disk-ssd的node上

![1585376817430](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1585376817430.png)

### Job

### 常用命令

~~~
kubectl scale rc kubia --replicas=10				# 更改pod副本数量
kubectl delete rc kubia --cascade					# 删除ReplicationController，但不删除被管理的pods
kubectl get rc 										# rc列表
kubectl create -f kubia-rc.yaml						#根据rc描述文件，创建rc
kubectl delete rs <rs-name> 						# 删除replicaSet

kubectl get dc										#dc列表
kubectl get job										# job列表

~~~

