# vi 命令

[TOC]

## 窗口

将当前窗口一分为二，进入`命令行模式`,然后输入`:sp`

~~~bash
:sp
~~~

在第二个屏，打开其他文件, 进入`命令行模式`,然后输入`:open filename`

~~~
:open filename
~~~



## 查找替换

 全局替换 :s/old/new/g



## 写代码常用

 跳转到函数定义: g +d 。 回跳：ctrl + o

多行注释

* v 进入visual模式

* control +v 进入列模式
* I 进入插入模式, 输入//
* 连按两下ESC

取消多行注释:

第一步，第二步同上，第三步按d



## 执行shell命令

不退出vi执行shell命令的方式，进入`命令行模式`,然后输入`!command`。这种方式对写python 脚本超nice

~~~
:!ls
~~~

