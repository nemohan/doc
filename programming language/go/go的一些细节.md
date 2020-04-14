

# go 的一些细节

[TOC]

最容易入坑的就是slice和append

### range 的几种用法

~~~go
a := []int{1, 2}
//不需要索引和值
for range a{
    
}
//只需要 索引
for i := range a{
    
}

//索引和值
for i, v := range a{
    
}
~~~



### fmt

* "*"的用法

* "#" 以go语法的形式输出内容

* [n]  重复使用同一个参数

~~~go
x := int64(0xdeadbeef)
fmt.Printf("%d %[1]x %#[1]x %#[1]X\n", x)
// 3735928559 deadbeef 0xdeadbeef 0XDEADBEEF
~~~

![1585878487880](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1585878487880.png)



"*"  指示打印可变数量的字符，depth * 2 指定字符数量， "+"指定字符

~~~
fmt.Printf("%*s</%s>\n", depth * 2, "", "fmt")
~~~





### 类型系统

* 基本类型  int、bool等
* 聚合类型 array、struct
* 引用类型 pointer、map、slice、channel、function
* interface



### string

在go中, string 是不可更改类型。

##### 计算字符串长度

* len(s) 是计算字符串s所占的字节数
* 用range循环或utf8.RuneCountInString(s)计算字符串s中字符(英文或其他非英文)个数



### 类型别名

~~~
type name T
~~~

### 操作符

* &^  x &^y  的执行顺序是，先计算^y. 然后再计算&。类似 x &(^y)
* << 左移位  空出来的位置填0
* ">>" 右移位 空出来的位置填符号位

### init 函数

每个.go文件都可以包含任意数目的init函数, 每个文件中的init函数的执行顺序依赖其声明顺序。

每个包被依次初始化，初始化的顺序根据包的依赖关系进行。如包p 引用了包q, 那么q会先被初始化

### 数组
* go 的数组数组大小是类型的一部分，即 a [4]int  和数组b [3]int是不同类型
* go的数组可以直接比较，只要其元素可以比较。只支持==、!= 两个操作符
* 作为函数参数传递时，会拷贝整个数组



~~~
a := [...]int{1,2,3} 		#数组长度由元素个数确定

//大小是类型的一部分，下面会导致编译错误
q := [3]int{1, 2, 3}
q = [4]int{1, 2, 3, 4}

//另类初始化，数组大小为100
r := [...]int{99:-1}
~~~




### slice
* slice 不支持比较操作符(== 和 !=) 只支持和nil的比较
* 内置函数len 支持slice 为nil
* slice 可以理解为视图-----------------
* 零值为nil



slice的三个组成部分:

* data pointer 指向slice可见的第一个数组元素
* len  slice的长度，不能超过cap
* capicity slice的起始点到其低层数组的结束点

~~~
b := [4]int{1, 2, 3, 4}
a := b[1:2]
fmt.Printf("a:%v len:%d cap:%d \n", a, len(a), cap(a))
//结果是:
a:[2] len:1 cap:3
~~~



![1586135935743](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1586135935743.png)



##### 确定slice是否为空用len(s) == 0而不是 s == nil

因为下面的都是成立的:

~~~go
var s []int 		// len(s) == 0, s == nil
s = nil 			// len(s) == 0, s == nil
s = []int(nil) 		// len(s) == 0, s == nil
s = []int{} 		// len(s) == 0, s != nil
~~~

##### slice 的一些坑

猜猜下面的结果
~~~ go
package main
import (
"fmt"
)
func main(){
 a := make([]int, 0, 2)
test(a)
fmt.Printf("%v\n", a)
}

func test(src []int){
 src = append(src, 1)
}












第一次我认为输出结果是：[1]
实际运行输出却是:[]
为什么呢？ 因为开始忽略了a是个slice,这就导致了如下思路。a的长度为0，cap 为2.调用test时，因为cap为2，追加一个元素并不会导致重新分配底层数组。所以a应该也能看到新追加的元素。



~~~

真的是"我们不一样"
用数组初始化slice 和slice 初始化slice表现出的不同

~~~go
package main

import (
	"fmt"
)

func main() {
	a := [...]int{1, 2, 3, 4, 5}

	b := a[:0]
	fmt.Printf("type:%T b len:%d cap:%d\n", a, len(b), cap(b))
	c := b[:0]
	fmt.Printf("c len:%d cap:%d %v\n", len(c), len(c), c)
}
输出:
type:[5]int b len:0 cap:5
c len:0 cap:0  []
~~~

再来一个套路
当把下面的第12行代码替换为
c := b[1:] 会导致panic. 之所以会如此是因为计算b的默认长度相当于用len(b)， 但此时b的长度为0. 就会有一个slice 越界的错误
~~~go
package main

import (
	"fmt"
)

func main() {
	a := [...]int{1, 2, 3, 4, 5}

	b := a[:0]
	fmt.Printf("type:%T b len:%d cap:%d\n", a, len(b), cap(b))
	c := b[1:4] //当 替换为 c := b[1:]会导致panic
	fmt.Printf("c len:%d cap:%d %v\n", len(c), len(c), c)
}

type:[5]int b len:0 cap:5
c len:3 cap:3 [2 3 4]
~~~



### struct

* 若struct的成员都可比较，struct 可支持== 和!=操作符

* 匿名成员的变量名称是隐式的，可以认为其类型名称就是变量名称。所以不能有两个类型相同的匿名成员

* 匿名成员变量为结构体时，若该匿名成员变量的成员变量和包含该匿名成员变量的结构体的其他成员变量名称相同时，会选择该结构体的成员变量


##### 匿名成员



~~~go
type Point struct {
X, Y int
}
type Circle struct {
Center Point
Radius int
}
type Wheel struct {
Circle Circle
Spokes int
}
var w Wheel
w.X = 8 // equivalent to w.Circle.Point.X = 8
w.Y = 8 // equivalent to w.Circle.Point.Y = 8
w.Radius = 5 // equivalent to w.Circle.Radius = 5
w.Spokes = 20

//初始化
w = Wheel{Circle{Point{8, 8}, 5}, 20}
w = Wheel{
Circle: Circle{
Point: Point{X: 8, Y: 8},
Radius: 5,
},
Spokes: 20, // NOTE: trailing comma necessary here (and at Radius)
}
~~~





~~~go
type Point struct{
    x, y int
}
type Circle struct{
	Point
    x int
}
c := Circle{
    Point:Point{x:1, y:2},
    x:3
}
fmt.Printf("c.x:%d\n", c.x)  //结果是3
~~~



~~~
type Point struct{
    x, y int
}
type Point3D struct{
    x,y,z int
}
type Circle struct{
	Point
	Point3D
}
c := Circle{
    Point:Point{x:1, y:2},
    Point3D: Point3D{x:4, y:5, z:6}
}
fmt.Printf("c.x:%d\n", c.x)  //编译错误，c.x歧义
~~~



### append 函数

<font color="red">使用append或slice容易出错。错在忽略slice的改变</font>

* append 必然会改变slice的长度.有可能创建新的数组改变指针和cap



![1586219439842](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1586219439842.png)



常见用法:

~~~go
a := make([]int, 0)
a=append(a, 1)
a=append(a, 1, 2)
a=append(a, x...)
~~~



### map

* map不支取元素地址 &ages["bob"]
* 遍历无序
* 零值为nil
* delete、len、range都可以操作值为nil的map,但是存储值时map不可以为nil,会导致panic
* map不支持比较操作，除了和nil比较



~~~go
ages := make(map[string]int)
ages["bob"] += 1		//支持
ages["bob"]++			//支持
_ = &ages["bob"]		//不支持，哈希表可能进行重新哈希，元素位置改变

var table map[string]int
fmt.Println(table == nil) //true
~~~



### 闭包的坑

猜猜下面的结果
~~~ go
package main
import (
"fmt"
)

func main(){
  for i := 0; i < 2; i++{
    defer func(){
    fmt.Printf("%d\n", i)
    }()
  }
  }



~~~

代码2
~~~go
package main
import(
"fmt")

var a int
func main(){
  f := func(){
    fmt.Printf("a %d\n", a)
  }
  f()
  a = 10
  f()
}

~~~

### defer

* defer函数的调用顺序是LIFO(last in first out)

defer 的新玩法, defer 是先对表达式求值
~~~
func caller(){
  defer test("caller")()
}

func test(name string)func(){
fmt.Printf("call func%s\n, name)
return func(){
fmt.Printf("call func %s end\n", name)}
}
~~~


### method
* methods may be declared on any named type defined in the same package , so long as its underlying type is neither a pointer nor an interface.(可以为任意的在同一个package内的命名的类型声明方法)

* 一般若某个方法的接收者是指针类型，那么该类型的所有方法的接收者应该都是指针类型
* 类型方法的查找规则，首先查找该类型直接声明的方法，若没有则查找该类型的匿名成员提供的方法。若在同一范围内有两个同名方法，将出现歧义的编译错误
* 接收者若可以为nil，最好明确注释

Point 是 *int 类型，不能为Point 声明方法, 编译下面代码

~~~go
package main
import "fmt"

type Point *int

func (p *Point) method() {

}
func main() {
	fmt.Printf("main\n")
}
~~~

编译上面代码将提示错误: invalid receiver type *Point (Point is a pointer type)

#### 类型方法的查找规则

编译下面代码将会提示 ambiguos selector c.dump错误

~~~go
package main

import "fmt"

type Point struct {
	x int
	y int
}

type Point2D struct {
	Point
}

type Circle struct {
	Point
	Point2D
}

func (p *Point) dump() {

}

func (p *Point2D) dump() {

}

func main() {
	c := Circle{}
	c.dump()
	fmt.Printf("main\n")
}
~~~



##### 方法调用

~~~go

package main
import(
"fmt"
)


type testStruct struct{
a int
}

func (t testStruct)method(){
}
func (t *testStruct)method1(){}
func main(){
  t := &testStruct{}
  t1 := testStruct{
  }
  t1.method()
  t1.method1()
  t.method()
  t.method1()
  
  t = nil
  t.method()//这也是合法的
}
~~~



#### method value and expression

~~~
package main
type Point struct{
x int
y int
}
func (p *Point)Add(q Point){

}
func main(){
//method expression
  add := (*Point).Add
  p := Point{x:10, y:10}
  q := Point{x:10, y:10}
  add(p, q) //非法
  add(&p, q)//合法
  //method value
  add2 := p.Add
}
~~~
### 各种坑
* 小心指针的使用
* 带指针结构体的拷贝
* 带slice 或map的结构体的拷贝

~~~
type A struct{
  member int
}

func (a *A)method(){

}
//非法
type B struct{
  A 
  A
}

type C struct{
  A
  member string //A 的member成员变量被隐藏
}
func (c *C)method(){

}
c := &C{}
c.method() //调用C的method方法
c.A.method() //才能调用A的method方法
~~~

### 不确定
* 带map的结构体的拷贝

### interface
可以理解interface 的值包含两部分:type, value
~~~
type writer interface{
  Write(int)
}

type A struct{
  a int
}
func (a A)Write(b int){

}

func main(){
  var wr writer
  a := &A{}
  a = nil
  wr = nil  // wr 为空时其type, value都为nil
  wr =  a // wr的type不为nil, value 为nil

}
~~~

### channel
* 写已经关闭的channel 会导致panic
* 关闭已经关闭的channel也会导致panic
* 读已经关闭的channel会返回channel的基本类型对应的零值
* channel 可以转为only-read channel或only-write channel. 但不能反向进行
* go-routine 泄漏，channel的接收端提早退出。可能导致发送端的go-routine一直等待
* channel 实现令牌机制
~~~
package main

import (
	"fmt"
	"time"
)

func test(ch chan<- int) {
	for i := 0; i < 10; i++ {
		time.Sleep(time.Second)
		ch <- i
	}
	close(ch)
}

func main() {
	ch := make(chan int)
	go test(ch)
	for v := range ch {
		fmt.Printf("%v\n", v)
	}
	fmt.Printf("channel closed:\n")
}
~~~

~~~
package main

import "fmt"

func test(ch chan<- int) {
	ch <- 2
	close(ch)
}
func main() {
	ch := make(chan int)
	go test(ch)
	for {
		v, ok := <-ch
		if !ok {
			fmt.Printf("channel closed: %d\n", v)
			break
		}
		fmt.Printf("%d\n", v)
	}
}
~~~

### Reflection 反射


### Package