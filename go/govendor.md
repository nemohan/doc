# govendor

#### 背景

govendor是golang的包管理工具

#### 问题

在windows平台的git bash上，使用govendor init 时，出现如下错误:

Error: FindFirstFile src: The system cannot find the file specified.

在项目目录 下添加一个src目录解决此问题。为什么会依赖于一个src目录呢





#### 解决vendor和GOPATH下，同一包冲突导致的错误

2019/9/5

~~~bash

.\main.go:34:37: cannot use srv.Server() (type "xx.com/gateway/vendor/github.com/micro/go-micro/server".Server) as type "github.com/micro/go-micro/server".Server in argument to go_micro_srv_greeter.RegisterSayHandler:
        "xx.com/gateway/vendor/github.com/micro/go-micro/server".Server does not implement "github.com/micro/go-micro/server".Server (wrong type for Handle method)        
                have Handle("xx.com/gateway/vendor/github.com/micro/go-micro/server".Handler) error
                want Handle("github.com/micro/go-micro/server".Handler) error
~~~

