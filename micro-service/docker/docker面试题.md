# docker 面试题

[TOC]

面试过程中偶尔会碰到一些docker相关的问题，之前从学到的忘的七七八八了已经



## 常见

### RUN 和 CMD的区别

* RUN 的作用是执行一条命令,并创建一个`层`,RUN是在构建时执行的。官方文档是这样说的

~~~
The RUN instruction will execute any commands in a new layer on top of the current image and commit the results. The resulting committed image will be used for the next step in the Dockerfile.

RUN 指令会在当前镜像的基础上创建一个新layer，并执行指令，然后提交
~~~



* CMD用来指定容器内最终运行的进程