# docker 部署golang项目失败

#### 背景

新写的golang微服务原型要部署到阿里云的k8s服务中。因为使用的是阿里云的云效的集成部署工具，所以不用自己提供构建docker镜像的脚本。不过部署工具可以使用笔者提供的Dockerfile，实际自己提供Dokerfile构建时也经历了一些心酸啊

#### 部署过程

~~~dockerfile
#最初的dockerfile 
FROM golang:latest
COPY ./ /game
CMD /game/game --server_address=:8080
~~~

使用上述Dockerfile构建时，构建倒是没问题。容器却始终无法启动，看日志显示没有找到game二进制文件。经过一番调试，估摸着是提供了Dockerfile之后，编译工作就落到了笔者身上。

调整之后的Dockerfile如下:

~~~dockerfile
#v2
FROM golang:latest
COPY ./ /game

CMD go build & /game/game --server_address=:8080
~~~

提交部署之后仍然失败，好心塞啊。看日志显示是没有找到.go文件，估计是路径不对。只好先在容器内启动一个其他进程，进入容器内看看当前的go的编译环境，发现在容器内GOPATH=/go，而我的项目目录是/game.所以需要将我的项目目录拷贝到容器内/go/src目录下。就有了以下版本的Dockerfile

~~~dockerfile
#v3
FROM golang:latest
COPY ./ /go/src/game
CMD go build & /go/src/game/game --server_address=:8080
~~~

修改之后，再次失败。查看日志显示仍然是没有找到.go文件，这次只可能是执行go build 时的当前工作目录不是/go/src/game目录。当前容器默认的路径是/go。所以要切换到/go/src/game目录中。

~~~dockerfile
#v4
FROM golang:latest
COPY ./ /go/src/game
RUN cd /go/src/game & go build 

#v5
FROM golang:latest
COPY ./ /go/src/game
CMD cd /go/src/game & go build 
~~~

上面两个版本还是不行。原因待确定？？？

最终版本

~~~dockerfile
FROM golang:latest
COPY ./ /go/src/game
CMD /go/src/game/build.sh


~~~



~~~bash
#!/bin/bash
cd /go/src/game
go build
./game/game --server_address=:8080
~~~



2019/8/5