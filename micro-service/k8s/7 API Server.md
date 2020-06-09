# API Server

[TOC]

在app里访问pod的元数据和其他的一些资源有三种方式:

* 容器内的环境变量
* Downward API
* API Server

### 环境变量

可以通过环境变量访问一些动态信息即pod启动时才知道的数值，如Pod的ip地址等。

![1585969706764](./${img}\1585969706764.png)
![1585969733077](./${img}\1585969733077.png)


![1585969847788](./${img}\1585969847788.png)
### Downward API

Downward API 并非一组API接口，而是挂载到容器内的数据卷。容器通过访问挂载的数据卷内的文件来访问pod的元数据。如下图所示

![1585969063607](./${img}\1585969063607.png)




downwardAPI 可以传递到容器的信息，如下图所示。大部分信息既可以通过环境变量也可以通过DownwardAPI访问，但label和annotation 只能通过DownwardAPI访问

![1585969312672](./${img}\1585969312672.png)


下图展示的是通过挂载DownwardAPI 数据卷的形式访问元数据：

![1585969986418](./${img}\1585969986418.png)


![1585970023814](./${img}\1585970023814.png)


![1585970123973](./${img}\1585970123973.png)


### API Server

##### kubectl proxy

访问API Server最简单的方式是使用kubectl proxy命令。该命令会在当前Node上运行一个http服务器。如下图所示:



![1585968182898](./${img}\1585968182898.png)


访问proxy的结果:

![1585968263519](./${img}\1585968263519.png)


##### 在app内访问API Server

使用API Server，首先需要知道API Server使用的IP地址。在k8s中API server使用的服务是kubernetes,如下图所示。可以看到API Server的IP地址及端口。

![1585966114735](./${img}\1585966114735.png)


进入到某个容器，执行curl https://kubernetes 可以看到需要提供SSL证书，如下图所示。证书放在哪呢

![1585966260721](./${img}\1585966260721.png)


在/var/run/secrets/kubernetes.io/serviceaccount目录下可以看到有三个文件

* ca.crt  访问kubernetes的证书
* namespace 当前pod所属的命名空间
* token 访问kubernetes需要的认证token

![1585966423435](./${img}\1585966423435.png)


在curl中指定证书后，访问API Server提示没有权限。这时候需要指定token

![1585966751641](./${img}\1585966751641.png)


指定token，继续访问API Server,仍然提示访问被禁止。



![1585967214235](./${img}\1585967214235.png)
这是因为k8s的RBAC权限控制机制导致的。可以用如下命令失效权限控制。在生产环境不建议这样做

![1585967378128](./${img}\1585967378128.png)


![1585968830870](./${img}\1585968830870.png)
