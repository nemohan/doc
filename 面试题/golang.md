# golang

[TOC]

以下是面试过程中会遇到的一些关于golang的问题

### new 和make的区别

我认为new和make的区别在于两个方面：

* new 是用来为指定类型分配一块内存，并返回其地址；make则是创建指定类型的对象
* make创建指定类型的对象时，还会做一些必要的初始化工作

###　作用域

问题是下面的代码能否编译通过，这个是考察变量作用域的问题。都知道在同一个作用域不能定义两个相同名称的变量。而在不同的作用域则可以。**但我不能确定的是if语句本身引入的作用域和其语句块｛｝是否是同一作用域**。**经验证不是**，下面的代码可以编译通过

~~~go
package main

import(
        "fmt"
)

var i int
func main(){
        var i  = 0

        if i := test(); i == 1{//这里的作用域
                fmt.Printf("%d\n", i)
                i := is() //这个和上面if语句引入的作用域是同一个么
                fmt.Printf("%v\n", i)

        }
        fmt.Printf("%d\n", i)
        {
                i := "xx"
                fmt.Printf("%v\n", i)

        }

}

func test()int{
        return 1
}

func is()bool{
        return false
}

~~~



### interface 的实现

interface的实现未开始

### select的实现或处理case的顺序

处理case的顺序

### channel 的实现

关于channel的实现，已经分析完成

### map 的实现

map的实现，分析完成