# Dockerfile 最佳实践

[TOC]

## 使用方式

Dockerfile包含指示如何构建镜像的命令。在包含Dockerfile的目录下执行`docker build PATH`来构建镜像。PATH指示构建使用的上下文，可以是本地的文件路径也可以是git仓库路径。

~~~
docker build . 以当前目录为构建上下文
~~~

### 注意

* 为使构建的镜像占用空间少，以及加快构建过程。构建上下文中不应该包含不需要的文件。可以使用.dockerignore文件来指定构建上下文中需要忽略的文件
* 每条指令都是独立的运行的并且会创建新的镜像，所以所以`RUN cd /tmp`对下一条指令没有任何影响

## 格式

Dockerfile必须以`FROM`指令开始，在`FROM`指令之前可以有`解析器指示符`、`注释`、`全局变量`



## 指令

### 解析器指示符

### 环境变量替换 Environment replacement



## 参考

* <https://docs.docker.com/develop/develop-images/dockerfile_best-practices/>

