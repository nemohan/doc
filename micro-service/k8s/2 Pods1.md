# Pods

[TOC]

在k8s中不是直接部署容器，而是部署Pod。每个Pod可以包含一个或多个相关的容器。当Pod包含多个容器时，所有的容器运行在同一个Node上，即单个Pod不能跨Node边界。如下图所示



![1584941629250](./${img}\1584941629250.png)

##### 为什么需要Pod

###### 多容器 VS 单容器多进程

假设app由多个进程组成，进程之间通过IPC(Inter-Process Communication 进程间通信)、或本地文件进行通信。这就需要这些进程运行在同一台机器。在K8S中进程总是运行在容器中，而每个容器类似一台隔离的机器。因此或许认为将多个进程运行在同一个 容器中比较合理。事实并非如此

容器的设计之初就意在单个容器只运行单个进程(除非进程创建了多个子进程)， 如果你在单个容器中运行多个不想关的进程，你就需要自己负责所有进程的运行、管理日志等。例如如何启动单个宕机的进程、区分进程的日志输出

所以，单个容器只运行单个进程是最佳选项

pod的出现提供了一个稍高一层的抽象，使得多个容器形成一个逻辑单元

Pod逻辑上是一个隔离的环境，有自己的ip地址、进程空间。在同一个pod内的容器共享pod的ip地址、进程空间(默认情况下不共享)。但是不共享文件系统

###### <font color="green">pod 最佳实践</font>

pod最好只包含单个容器。包含单个容器便于pod横向拓展、部署(若包含多个容器，其中一个容器宕机了。不能单独再启动宕机的容器)

若要包含多个容器，最好是多个容器整体上是一个逻辑单元



###### 网络共享

* 在同一个pod内运行的容器共享网络地址和端口空间。所以在同一个pod内的容器需要注意端口冲突的问题。

* 不同的pod有自己独立的网络地址和端口空间，所以运行在不同pod内的容器不会有端口冲突的问题



<font color="red">集群之间的内部网络:</font>

在k8s集群中的所有Pods使用一个平坦、共享的网络地址空间（有点像局域网), 每个pod可以访问任意的其他pod的ip地址(即使pod在不同的node上)。pod之间没有NAT(网络地址转换)。如下图所示.

![1584949901269](./${img}\1584949901269.png)### Pod

pod和其他的k8s资源通常以提供资源描述文件给k8s的REST API server来创建

查看pod的描述文件，如下图:

~~~
kubectl get po kubia-zxzij -o yaml
apiVersion: v1
kind: Pod
metadata:
annotations:
kubernetes.io/created-by: ...
creationTimestamp: 2016-03-18T12:37:50Z
generateName: kubialabels:
run: kubia
name: kubia-zxzij
namespace: default
resourceVersion: "294"
selfLink: /api/v1/namespaces/default/pods/kubia-zxzij
uid: 3a564dc0-ed06-11e5-ba3b-42010af00004
spec:
containers:
- image: luksa/kubia
imagePullPolicy: IfNotPresent
name: kubia
ports:
- containerPort: 8080
protocol: TCP
resources:
requests:
cpu: 100m
Listing 3.1 Full YAML of a deployed pod
Kubernetes API version used
in this YAML descriptor
Type of Kubernetes
object/resource
Pod metadata (name,
labels, annotations,
and so on)
Pod
~~~

##### 描述文件:

描述文件通常由三个主要部分组成:

* Metadata  name、namespace、label和其他一些信息
* Spec 包括pod的容器、volume和其他一些数据
* Status 运行状态信息

下图是一个基本的Pod描述文件：

![1584944977684](./${img}\1584944977684.png)

<font color="red"> 注意:</font>

在描述文件中指定容器监听的端口只是提示作用，忽略端口也不会影响客户端是否能够链接pod的此端口

##### 创建和销毁

可以通过 kubectl create 命令来创建pod：

~~~
kubectl create -f pod描述文件  pod-name
~~~

销毁一个Pod:

~~~
kubectl delete pod <pod-name>
~~~

还可以通过使用标签选择器删除含有特定 标签的一组pod:

~~~
kubectl delete pod -l <label-name=value>
~~~



##### 端口转发

若想在没有service的情况下访问某个pod可以使用端口转发。下图中展示的即是将本机端口8888转发到pod kubia-manul的端口8080

~~~
kubectl port-forward kubia-manual 8888:8080
~~~



###　label(标签)和label selector(标签选择器)

如果想在k8s中对pod进行分组或归类，需要用到label。分组的好处就是可以批量操作指定分组的pod，比如干掉某个分组的pod。

![1585046404303](./${img}\1585046404303.png)在k8s中几乎所有的资源都支持label，label以键值对的形式出现。可以在资源描述文件中指定label或通过命令行。

每个Pod都有两个默认的label:

* app:	 which specifies which app, component, or microservice the pod belongs to
* rel: which shows whether the application running in the pod is a stable, beta,
  or a canary release.

在pod定义文件中指定label:

![1585051959645](./${img}\1585051959645.png)

![1585051981803](./${img}\1585051981803.png)给pod添加一个label,可以执行如下命令:

~~~
$ kubectl label po <pod-name> creation_method=manual
~~~

查看Pod定义的所有标签:

~~~
$ kubectl get pod <pod-name> --show-labels
~~~

查看所有Pod的某个标签的值:

~~~
$ kubectl get pod -L <label-name>
~~~

更改某个Pod的标签值:

~~~
$ kubectl label po kubia-manual-v2 env=debug --overwrite
~~~

##### 标签选择器

标签选择器: 标签选择器可以根据标签来筛选符合条件的资源

* 包含特定label和键的资源
* 包含特定label且特定的键值对
* 包含特定label和键,但键的值不等于指定的值

列出所有包含label env 的pod的命令:

~~~
kubectl get pod -l env
~~~

列出包含label app,值为test的所有pod:

~~~
kubectl get pod -l app=test
~~~

列出不含有label env的所有Pod:

~~~
kubectl get pod -l '!env'
~~~

还可以使用如下的操作符:

~~~
kubectl get pod -l app != test				#列出包含label app 且值不为test
kubectl get pod -l app in (test, test2)		#列出包含label app 且值为test 或test2
kubectl get pod -l app not in(test, test2)	#列出包含label app 且值不为(test, test2)
~~~



##### Pod 部署到指定Node

限定指定的pod的部署到特定的node上，同样用到label。如下图，将pod部署到含有label gpu=true的节点上。

![1585057185832](./${img}\1585057185832.png)

### annotations

### namespace 命名空间

命名空间用于将资源分组，多个开发团队使用一个k8s集群时，可以为每个团队配置不同的命名空间。默认情况下集群有三个命名空间:

* default 在使用kubect l 命令时，若未指定-ns(命名空间)参数，则使用default
* kube-public
* kube-system

命名空间列表:

~~~
kubectl get namespace
~~~

创建命名空间:

~~~
kubectl create namespace <space-name>
~~~

删除命名空间:

~~~
kubectl delete namespace <space-name>
~~~



### 常用命令汇总

~~~

kubectl get nodes 						#查看集群节点列表

kubectl logs pod-name 					#查看Pod日志
$ kubectl logs mypod --previous			#查看当前pod的前一个实例的日志
kubectl logs pod-name container-name 	#查看Pod内指定容器的日志(Pod内有多个容器)
kubectl get pods 						#查看集群Pod列表
kubectl get pods -o wide 				#查看pod在node的分布
kubectl create -f name.yaml 			#创建指定资源
kubectl get pod pod-name -o yaml 		#查看pod的以yaml格式的描述文件
kubectl delete pod  <pod-name> 			#删除Pod
kubectl delete pod -l <label-name=value> #删除含有特定标签的所有pod
kubectl delete pod --all 				#删除所有pod


kubectl get ns 							#查看k8s集群上的命名空间列表
kubectl create namespace <space-name> 	#创建命名空间
kubectl delete all --all				#删除命名空间下的所有资源,但不会删除命名空间本身
kubectl delete namespace <space-name> 	#删除命名空间及其拥有的所有资源
~~~

