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

提交部署之后仍然失败，好心塞啊。



2019/8/5