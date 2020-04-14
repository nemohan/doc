# Deployment



[TOC]



### app升级方式

在k8s中如何升级app

* 删除所有旧版本的pod,然后启动新版本的
* 启动新版本的然后删除所有旧版本的

第一种方案会导致短暂的服务不可用。第二种方案需要新、旧版本数据兼容(比如在新版本更新了数据库表字段)



第一种方式: 更改ReplicationController资源文件中模板使用的镜像，然后删除所有旧的Pod

![1586230542572](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1586230542572.png)





##### 蓝绿部署(blue-green deployment)

先启动所有新版本的pod，然后通过更改Service的pod 的selector来升级。这种方式也叫做蓝绿部署

![1586230973846](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1586230973846.png)



##### 滚动升级(rolling update)

滚动升级不像蓝绿部署那样，一开始就启动所有新版本的Pod。而是一步一步来，先启动一个新版本的pod,然后释放一个旧版本的Pod。直到旧版本的都被释放。如下图所示

![1586231726392](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1586231726392.png)



### 使用kubectl 升级Pod

使用kubectl rolling-update 命令来升级，如下图所示。

![1586232601841](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1586232601841.png)



rolling-update的工作原理: k8s通过复制RC kubia-v1的资源文件创建kubia-v2。复制后的文件的image会被更改从而使用新的镜像。kubia-v1和kubia-v2的Pod selector都会被更改，多一个deployment label。之前被kubia-v1管理的pod也会多一个deployment label，使得v1和v2管理不同版本的pod

1) 更改kubia-v2的image和selector

![1586232875293](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1586232875293.png)



2)更改kubia-v1的selector

![1586232990660](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1586232990660.png)



3)最终结果

![1586233035968](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1586233035968.png)



4）接着通过伸缩新版本的Pod，然后释放旧版本的Pod如下图

![1586233125496](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1586233125496.png)



![1586232703180](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1586232703180.png)



### 使用Deployment升级

deployment 是在RC/RS之上的更高一级抽象

![1586397373062](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1586397373062.png)



Deployment的资源描述文件

![1586397646102](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1586397646102.png)

##### 升级

deployment可用的两种升级策略：

* recreate 首先删除所有的旧版本的pod，然后创建新版本的Pod。会造成短暂的服务不可用，但适用于新、旧版本不能同时运行的情况
* rollingUpdate 滚动升级



几个比较重要的设置选项：

* minReadySeconds

* maxSurge  指定升级时最多启动几个新版本的pod
* maxUnavailable 升级时最多删除几个旧版本的pod
* revisionHistoryLimit 保留历史版本的ReplicaSet数目上限

![1586480364101](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1586480364101.png)

查看当前的升级状态:

~~~
kubectl rollout status deploy <deploy-name>
~~~



##### 暂停升级

~~~
kubectl rollout pause deploy <deploy-name>
~~~

恢复升级:

~~~
kubectl rollout resume deploy <deploy-name>
~~~



##### 回退

回退到上一个版本：

~~~
kubectl rollout undo deploy <deploy-name>
~~~

回退到指定版本：

~~~
kubectl rollout updo deploy <deploy-name> --to-revision=<number>
~~~



查看部署历史的历史版本:

~~~
kubectl rollout history deploy <deploy-name>
~~~

下图中的revision可以用于回退到特定版本。

![1586397254818](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1586397254818.png)



deployment的回退机制是通过保留旧版本的ReplicaSet来实现的

![1586398988324](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1586398988324.png)



### 更改k8s已经存在资源的几种方式

![1586309779337](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1586309779337.png)

### 常用命令

~~~
kubectl set selector 			#更改service 使用的pod selector
kubectl rolling-update <v1> <v2> --image=<image-name> 	#滚动升级
kubectl rolling-update <v1> <v2> --image=<image-name> --v 6 # 增加详细的日志，可以看到kubectl 和api server的交互


kubectl patch deployment kubia -p '{"spec": {"minReadySeconds": 10}}' #修改资源文件的某个或某些属性

kubectl set image deployment kubia nodejs=luksa/kubia:v2  #更改deployment、rc、rs使用的镜像文件

kubectl rollout status deployment kubia   #查看升级状态
kubectl rollout undo deployment kubia     # 回退到之前版本
kubectl rollout history deployment xd-t-admin  # 升级历史
kubectl create -f kubia-deployment-v1.yaml --record # 创建deployment
~~~

