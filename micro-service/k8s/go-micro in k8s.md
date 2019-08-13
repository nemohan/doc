# go micro 和k8s

#### 背景

最近项目需要基于微服务进行重新整合。原本的项目都是基于web框架gin开发的，迁移到微服务之后希望可以继续使用gin，这样更便于其他写业务逻辑的同事。

找了两个微服务框架，一个是traefik。没仔细研究，这里就不多讲了。另一个是go micro，micro是一个插件式的微服务框架，不过更像是微服务工具集。

micro 的特性:

* 支持服务发现

* 负载均衡

* RPC通信

* PubSub 异步通信模式

* 编码插件

  

micro的官方文档：https://micro.mu/docs/go-api.html#http-handler

作图工具: http://asciiflow.com/

期望的架构:

~~~
api gateway、service 都运行在k8s管理的容器中
                                     +-----------------+
                                     |                 |
+-----------------+                  |                 |
|                 |                  |                 |
|                 |                  |                 |
|                 |                  |     service     |
|                 +------------------+                 |
|                 |                  |                 |
|      api gateway|                  +-----------------+
|                 |
|                 |                  ------------------+
|                 |                  |                 |
|                 +------------------+     service     |
|                 |                  |                 |
+-----------------+                  |                 |
                                     |                 |
                                     |                 |
                                     |                 |
                                     +-----------------+

~~~



#### 原型搭建

基本架构的原型已经确定，接下来就是搭建基于k8s、micro的微服务架构。

micro 支持基于etcd、mdns、consul、k8s的服务发现机制。基于以上最初确定了3种服务发现机制。

1）通过k8s + mdns，在k8s内使用基于mdns的服务发现机制(没有尝试)

2) 基于k8s + consul, 在k8s内运行consul（没有尝试)

3) 基于k8s. 使用k8s原生的服务发现机制

结合官方文档我认为前两种方式，应该比较容易。那么第三种方案呢

看官网的文章，看了许久也没有明白应该如何让micro 使用k8s原生的服务发现机制。没办法只好去看micro的代码

后端服务

~~~go
package main

import(
        "net/http"
        "os"
        "github.com/micro/go-micro/web"
        k8s "github.com/micro/examples/kubernetes/go/web"
)

func main(){
        service := k8s.NewService(web.Name("hello"))

        service.HandleFunc("/world", func(w http.ResponseWriter, r *http.Request){
                w.Write([]byte(os.Getenv("HOSTNAME")))
        })

        service.HandleFunc("/hello/world", func(w http.ResponseWriter, r *http.Request){
                w.Write([]byte(os.Getenv("HOSTNAME") +"haha"))
        })

        service.Init()
        service.Run()
}

~~~



api 网关

~~~go
package main

import(
        "github.com/micro/go-micro/web"
        //k8s "github.com/micro/examples/kubernetes/go/web"
        "github.com/micro/go-micro/api/handler/http"
        "github.com/micro/go-micro/api/handler"
        "github.com/micro/go-plugins/registry/kubernetes"
        "github.com/micro/go-micro/api/router/registry"
        "github.com/micro/go-micro/api/router"
)

func main(){
        router := registry.NewRouter(router.WithRegistry(kubernetes.NewRegistry()), router.WithHandler("http"))
        httpHandler := http.NewHandler(handler.WithRouter(router))

        service := web.NewService(web.Name("api-gateway"), web.Handler(httpHandler))
        service.Init()
        service.Run()

}

~~~

