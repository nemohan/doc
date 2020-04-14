# Service

[TOC]



### service

为什么要引入service，pod之间可以相互访问、当然也可以外部的客户端访问内部的pod。但随着pod的创建和销毁，其ip地址也在跟着变化。service可以提供固定的ip地址，可以解决这个问题。service可以为一个或多个副本pod提供相同的ip地址。如此一来，客户端便不用关心pod的IP地址，也不用关心有几个pod在提供服务。如下图所示

![1585387188770](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1585387188770.png)

<font color="red"> service 也是根据label selector来确定哪些pod由特定service负责</font>

###### 会话粘性

service 会随机选择请求转发到哪个pod，所以可以设置会话粘性，来确定请求转发到哪个pod。目前有两种方式

* 没有，随机选择
* 根据客户端ip地址

![1585389931571](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1585389931571.png)



##### <font color="red">EndPoint 资源</font>

执行kubectl describe svc <svc-name> 可以看到EndPoints，如下图。EndPoints资源就是一组带端口的IP地址。service 并不是通过label selector 来决定请求发到哪个Pod,而是来建立IP列表并将列表保存在EndPoints资源中。service 正是通过建立的ip地址列表来确定请求的转发。



![1585657631700](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1585657631700.png)



若创建service时，没有指定label selector那么就不会创建EndPoints资源. 如此一来就可以手动创建EndPoints资源，下图是创建EndPoints资源的描述文件

![1585658197721](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1585658197721.png)

注意：

* 是endpints 而不是endpoint
* endpoints的资源描述文件指定的名称必须和使用该资源的service的名称保持一致



##### 访问外部网络

可以通过为外部服务创建service和endpoints的形式，让集群内部的pod访问。

![1585658500955](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1585658500955.png)

###### 为外部服务创建集群内别名

待补充

##### 集群内部之间访问内部service

集群内部pod之间的相互访问，最佳方式当然也是使用service. 但pod如何知道service使用的ip地址呢？有两种方式从

* 环境变量--pod启动时，k8s会在容器内初始化指向当前所有的service的环境变量
* 集群内部的dns服务器。每个service都会在集群内DNS服务器上有对应的DNS记录，知道service的名称就可以通过其FQDN访问service. FQDN的格式如service-name.namespace-name.svc.cluster.local。其中svc.cluster.local是可配置的域名后缀。当被访问的pod和作为客户端的pod在同一个名称空间时，可以用service 名称作为域名访问service.

当service名称作为环境变量的前缀时，"-"会变为"_", 所有字母转为大写

下图所示某个容器内的环境变量:

![1585390971073](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1585390971073.png)



##### 内部pod访问外部网络



##### 外部网络访问service

有三中方式可以让外部网络访问service:

* NodePort	对这种类型的service,每个集群节点开放一个端口，从该端口收到的网络流量重定向到对应的service。
* LoadBalancer NodePort类型的一种拓展，这种负载均衡一般由k8s运行的云基础设施提供。负载均衡器将流量重定向到所有节点的开放的端口上
* Ingress Resource 工作在http层



###### ClusterIP

service 的集群内部地址，外部不可访问

###### NodePort

当新建一个NodePort service，k8s会在集群的所有节点开放指定的相同端口。通过这个开放的端口转发流量到对应的pod



下图是NodePort 类型service的描述文件:

![1585451106680](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1585451106680.png)

上图有三个端口：

* 8080 是pod或容器使用的端口, 
* 30123是Node开放的端口， 可以在节点上使用: curl http://localhost:30123 测试
* 80 是ClusterIP使用的端口，可以在节点上使用 curl http://clusterIp:80测试

<font color="red">为什么会多一个80端口:</font>

估计是集群内部访问pods提供便利



下图是我们运行在阿里云k8s上的一个NodePort类型的service:

![1585451440384](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1585451440384.png)



<font color="red">从某个Node到达的流量不一定会转发到运行在该Node上的Pod上面，如下图所示，假设以Node2 的地址作为对外地址，当链接到达Node2的端口后，该链接既可以转发到运行在Node1的pod上，也可以转发到运行在Node2的Pod上。当然可以设置</font>

![1585453733917](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1585453733917.png)



NodePort类型的进入流量是什么样的？

client -> node port-> service port-> pod port





###### Loadbalancer

Loadbalancer是NodePort的拓展。若单独使用NodePort service，任意一个Node 都可对外提供服务。那么当对外提供服务的某个Node失效后，就无法再访问整个服务了。

使用loadbalancer时也会为每个Node开放一个端口

下图是loadbalancer的资源描述文件，只需要指定loadbalancer使用的端口80和pod使用的端口。k8s会自动分配node使用的端口

![1585454209124](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1585454209124.png)



流量示意图:

![1585454172286](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1585454172286.png)



下图是使用阿里云提供的loadbalancer serivce的一个描述文件:

![1585454484339](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1585454484339.png)



使用loadbalancer后流量:

loadbalancer pot -> node port -> service port -> pod port

###### Ingress

为了使用ingress service，需要先创建ingress controller

为什么需要ingress, 因为每个loadbalancer service 都需要一个公共的ip地址。而ingress只需要一个就能为多个service提供服务。不过仅限于http/https服务

其实ingress controller一般是用nginx，根据域名或路径访问对应的服务

![1585448089867](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1585448089867.png)

ingress的工作示意，ingress controller 并不会将请求转发到service，而是直接将请求递交给pod

![1585446048689](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1585446048689.png)



ingress的资源描述文件:

![1585455915652](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1585455915652.png)



###### <font color="red">两种使用方式</font>

同一个主机域名，不同的路径对应不同的service:

这的servicePort 是barservice使用的端口？ 还是intress controller 使用的端口？

![1585448587621](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1585448587621.png)

<font color="red">不同的主机域名,每个域名对应一个service:</font>

![1585448615931](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1585448615931.png)

为Ingress配置https:

* 创建包含证书的secret资源
* 在ingress service中引用创建的secret



以下命令创建secret:

~~~bash
$ kubectl create secret tls tls-secret --cert=tls.cert --key=tls.key
secret "tls-secret" created
~~~

 

在ingress描述文件中引用上面创建的secret

![1585446708563](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1585446708563.png)





### Ready probe

有点类似live probe机制。ready probe是检测某个pod是否已经准备好处理请求。即是检测失败也不会重启pod只是不会成为service的endpoint。到service的请求也不会派发到该pod

三种方式:

* http GET 请求 若返回2xx或3xx代码表示Pod已准备就绪
* exec 执行一条命令，若命令退出码为0表示就绪
* TCP socket 若能建立与Pod的某个端口的链接表示就绪





### headless service

没有clusterIP 的service。待进一步补充



![1585384355951](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1585384355951.png)





![1585384376354](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1585384376354.png)







![1585384071732](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1585384071732.png)



### 总结

service应该是使用了类似sock5代理的某种代理来转发流量到pod.

### 常用命令

~~~
kubectl exec -it <pod-name> cmd				# 在pod内运行命令
kubectl get svc								# 获取service列表
kubectl create secret tls tls-secret --cert=tls.cert --key=tls.key #创建secret
kubectl apply -f kubia-ingress-tls.yaml		#更新资源的描述文件
kubectl get ingress 						# 获取ingress列表
kubectl get endpoints 						# 获取endpoints 列表
~~~

