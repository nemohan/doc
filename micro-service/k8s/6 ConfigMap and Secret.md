# ConfigMap and Secret

[TOC]

这一篇主要讲述如何设置app的配置项

### 在k8s中配置app的几种方式

#### 命令行参数

首先看看如何传递命令行参数到运行在docker 容器内的app.

###### ENTRYPOINT 和CMD:

* ENTRYPOINT  定义了当容器启动时要执行的程序
* CMD 定义了传递给ENTRYPOINT的参数。一般用来定义默认参数

通常情况是只使用ENTRYPOINT定义要执行的程序及其参数。CMD仅用于指定默认参数

###### ENTRYPOINT有两种格式:

* shell 形式 如 ENTRYPOINT python app.py
* exec 形式  ENTRYPOINT ["python", "app.py"]

二者的差别是shell形式的ENTRYPOINT以shell子进程的方式运行app, exec则是直接运行app



pod资源描述文件的command 和args选项指定容器运行的app和其参数

![1586748324654](./${img}\1586748324654.png)


#### 环境变量

在K8s中环境变量是定义在pod资源描述文件中的容器下面

注意: 环境变量和命令行参数不可改变，一旦pod被创建



配置方式如下图所示，<font color="red">可以看到环境变量是定义在容器层面，而非pod层面。</font>

![1586748676423](./${img}\1586748676423.png)
###### 使用变量

环境变量的定义还可以使用之前已经定义的变量，如下图所示，SECOND_VAR的值是foobar

![1586748834966](./${img}\1586748834966.png)


#### configMap

##### 创建configmap

创建configmap可以使用下图命令，当然也可以使用kubectl create -f

~~~
kubectl create configmap <configmap-name> --from-literal=key=value --from-literal=key1=value1 --from-literal=key2=value2
~~~

![1586829787089](./${img}\1586829787089.png)


从文件创建configMap:

~~~
kubectl create configmap --from-file=config.conf //config.conf将作为键名称
kubectl create configmap --from-file=key=config.conf //指定自定义键名称
kubectl create configmap --from-file=/path  	//从指定目录下的所有文件创建configmap
~~~



或者多种方式混用来创建configmap， 如下图

![1586830256753](./${img}\1586830256753.png)


结果如下图:

![1586830296838](./${img}\1586830296838.png)


##### 以环境变量的方式使用configmap

下图是某个pod的资源描述文件，定义了环境变量INTERVAL

![1586830798697](./${img}\1586830798697.png)
![1586830972283](./${img}\1586830972283.png)




导出configmap的所有kv为环境变量:

![1586832992607](./${img}\1586832992607.png)
注意：当configmap不存在时，依赖configmap的容器无法启动

##### 以命令行参数的方式使用configmap

![1586833037805](./${img}\1586833037805.png)
##### 以文件方式使用configmap

configmap也可以数据卷的形式挂载到文件系统，configmap包含的每个kv都会形成一个单独的文件，key作为文件名称，value作为文件内容



使用步骤：

* 创建configmap
* 挂载configmap到pod, 在pod资源描述文件中指定

~~~bash
kubectl create configmap fortune-config --from-file=configmap-files
~~~

查看上步创建的configmap:

![1586834819068](./${img}\1586834819068.png)
下图是使用configmap作为volume的pod的资源描述文件:

![1586834383832](./${img}\1586834383832.png)
#### secret

用于配置敏感数据配置项，如密钥



创建https用的证书:

~~~
kubectl create secret generic fortune-https --from-file=https.key
 --from-file=https.cert --from-file=foo
~~~



##### 以环境变量方式使用secret

![1586917832821](./${img}\1586917832821.png)
##### 以数据卷形式使用secret

![1586917705559](./${img}\1586917705559.png)


##### 创建从私有仓库获取docker镜像的secret

可以使用以下命令创建从私有仓库获取docker镜像的secret

~~~
kubectl create secret docker-registry mydockerhubsecret \
--docker-username=myusername --docker-password=mypassword \
--docker-email=my.email@provider.com
~~~

创建secret以后，需要在pod资源描述文件中引用新创建的secret。这种方式需要为每个需要从私有镜像仓库获取镜像的Pod指定secret。可以通过将secret添加到serviceAccount的来避免修改每个pod

![1586918329230](./${img}\1586918329230.png)
### 常用命令

~~~
kubectl create secret tls						#创建tls
kubectl create configmap fortune-config --from-file=configmap-files #创建configmap
~~~

