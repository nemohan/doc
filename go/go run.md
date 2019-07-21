# go run 命令

2019/7/19

今天有朋友问我关于go run的使用遇到的一个问题。

朋友的项目结构是这样的：

project 目录

​	main.go

​	hasn.go

只有一个main包，有两个文件main.go、hash.go。如下：

~~~go
//main.go
package main
func main(){
    test() 
}

//hash.go
package main
func test(){
    
}


~~~

执行 go run main.go得到test未定义的错误，如果执行go run main.go hash.go 则成功。我尝试了一下果真是这样。因我平时用惯了go build，一时也有点纳闷。纳闷的是按照go的项目结构的规范来看，为什么不能找到当前目录下的依赖呢？ 

查了一下go run的帮助文档，有两种解决方式:

* 在main.go的父目录，执行go run project 
* 在main.go的当前目录， 执行go run . (此处的"."是当前目录)

如此看来，从技术的角度来讲支持go run main.go应该问题不大。所以这算是个go run的缺陷么







