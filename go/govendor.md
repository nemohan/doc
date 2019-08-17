# govendor

#### 背景

govendor是golang的包管理工具

#### 问题

在windows平台的git bash上，使用govendor init 时，出现如下错误:

Error: FindFirstFile src: The system cannot find the file specified.

在项目目录 下添加一个src目录解决此问题。为什么会依赖于一个src目录呢