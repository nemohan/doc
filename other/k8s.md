# k8s

book: devops with kubernets

book: k8s in action

### 1 kubectl 常用命令

查看pod归属于哪个node

kubectl get pod -o wide							  查看pod以及其对应的node

kubectl get pod pod_name -o wide  		查看指定的名为pod_name的pod归属于哪个node

kubectl describe pods pod_name			 描述指定的名为pod_name的pod的yaml配置文件

kubectl run 												   创建deployment

kubectl get service   									获取服务列表

kubectl logs pod_name							  查看pod标准输出.类似docker logs container

kubectl run micro-ui --image=test:micro-ui --port=8082 --generator=run-pod/v1  运行镜像

~~~shell
// using kubectl run to launch the Pods
# kubectl run nginx --image=nginx:1.12.0 --replicas=2 --port=80
deployment "nginx" created

// check the deployment status
# kubectl get deployments
NAME DESIRED CURRENT UP-TO-DATE AVAILABLE AGE
nginx 2 2 2 2 4h
~~~

kubectl expose 曝光端口

~~~shell
// expose port 80 to service port 80
# kubectl expose deployment nginx --port=80 --target-port=80
service "nginx" exposed

// list services
# kubectl get services
NAME CLUSTER-IP EXTERNAL-IP PORT(S) AGE
kubernetes 10.0.0.1 <none> 443/TCP 3d
nginx 10.0.0.94 <none> 80/TCP 5s
~~~

kubectl set image deployment nginx nginx=nginx:1.13.1 升级

### 2 deployment

在k8s 1.2版本之后，deployment是管理、部署程序的最佳方式。支持滚动升级、回滚pods和ReplicaSets

滚动升级的一些配置参数:

minReadySeconds : 认为pod启动成功的最短时间  默认值:zero:

maxSurge：滚动升级时最多可以同时启动几个(每次同时升级几个)

maxUnavailable:  滚动升级时最多有多少个不可用

### 3 service

<font color="red"> Service in Kubernetes is an abstraction layer for routing traffic to a logical set of
pods. With service, we don't need to trace the IP address of each pod. Service usually
uses label selector to select the pods that it needs to route to (in some cases service is
created without selector in purpose). The service abstraction is powerful. It enables
the decoupling and makes communication between micro-services possible.
Currently Kubernetes service supports TCP and UDP. </font>

<font color="blue"> Service doesn't care how we create the pod. Just like ReplicationController, it only
cares that the pods match its label selectors, so the pods could belong to different
ReplicationControllers. The following is an illustration:</font>

Kubernetes creates an endpoints object along with a service object for routing the traffic to matching pods

k8s创建service时也会创建endpoint。



默认情况下，k8s会为每个创建的service暴露7个环境变量。前两个被kube-dns用于服务发现

${SVCNAME}_SERVICE_HOST
${SVCNAME}_SERVICE_PORT
${SVCNAME}_PORT
${SVCNAME}_PORT_${PORT}_${PROTOCAL}
${SVCNAME}_PORT_${PORT}_${PROTOCAL}_PROTO
${SVCNAME}_PORT_${PORT}_${PROTOCAL}_PORT
${SVCNAME}_PORT_${PORT}_${PROTOCAL}_ADDR

service 支持四种服务类型，分别是ClusterIP, NodePort, LoadBalancer, ExternalName

##### ClusterIP(集群ip)

ClusterIP is the default service type. It exposes the service on a cluster-internal IP.
Pods in the cluster could reach the service via the IP address, environment variables,
or DNS. In the following example, we'll learn how to use both native service
environment variables and DNS to access the pods behind services in the cluster

clusterIp是一种集群内部的pod之间的通信方式。

##### NodePort(节点端口)

If the service is set as NodePort, Kubernetes will allocate a port within a certain
range on each node. Any traffic going to nodes on that port will be routed to the
service port. Port number could be user-specified. If not specified, Kubernetes will
randomly choose a port from range 30000 to 32767 without collision. On the other
hand, if specified, the user should be responsible to manage the collision by
themselves. NodePort includes the feature of ClusterIP. Kubernetes assigns an
internal IP to the service. 

使用NodePort，k8s会分配一个端口范围。到service端口的流量都会导向每个使用了上述范围内端口的Node

有点类似于 docker -p port:port 。外部网络可以访问



~~~yaml
#以下面的服务为例
apiVersion: v1
kind: Service
metadata:
  creationTimestamp: '2019-03-20T08:30:23Z'
  name: xd-t-admin-svc
  namespace: default
  resourceVersion: '262040488'
  selfLink: /api/v1/namespaces/default/services/xd-t-admin-svc
  uid: 6777d904-4aea-11e9-81dd-4ed19a359ad4
spec:
  clusterIP: 172.17.10.210
  externalTrafficPolicy: Cluster
  ports:
    - nodePort: 32424 		#映射到的主机端口
      port: 80 				#到端口80的流量，会转发到32424再到内部容器
      protocol: TCP
      targetPort: 8030 		#app实际监听端口  类似:docker -p 32424:8030
  selector:
    app: xd-t-admin
  sessionAffinity: None
  type: NodePort
status:
  loadBalancer: {}
~~~



##### LoadBalancer(负载均衡)

配合云服务商使用

##### ExternalName(外部名称)

##### service without selector

Service uses selectors to match the pods to direct the traffic. However, sometimes
you need to implement a proxy to be the bridge between Kubernetes cluster and
another namespace, another cluster, or external resources. In the following example,
we'll demonstrate how to implement a proxy for http://www.google.com in your cluster.
It's just an example while the source of the proxy might be the endpoint of your
databases or other resources in the cloud:



### 4 Ingress

~~~yaml
apiVersion: extensions/v1beta1
kind: Ingress
metadata:
  annotations:
    nginx.ingress.kubernetes.io/service-weight: ''
  creationTimestamp: '2019-03-20T08:32:19Z'
  generation: 1
  name: xd-t-admin-ingress
  namespace: default
  resourceVersion: '262048222'
  selfLink: /apis/extensions/v1beta1/namespaces/default/ingresses/xd-t-admin-ingress
  uid: acc47acf-4aea-11e9-81dd-4ed19a359ad4
spec:
  rules:
    - host: xd-t-admin-api.vipiao.com
      http:
        paths:
          - backend:
              serviceName: xd-t-admin-svc
              servicePort: 80
            path: /
status:
  loadBalancer:
    ingress:
      - ip: 39.96.133.80 # xd-t-admin-api.vipiao.com 绑定到了此地址

~~~



#### deployment、replicaSet、pod之间的关系

deployment管理replicaSet,replicaSet管理pod