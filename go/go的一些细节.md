# go 的一些细节



### 数组
* go 的数组数组大小是类型的一部分，即 a [4]int  和数组b [3]int是不同类型
* go的数组可以直接比较，只要其元素可以比较。只支持==、!= 两个操作符
* 作为函数参数传递时，会拷贝整个数组


### slice
* slice 只支持和nil的比较
* 内置函数len 支持slice 为nil
* slice 可以理解为视图-----------------

### slice 坑
猜猜下面的结果
~~~ golang
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

~~~

真的是"我们不一样"
用数组初始化slice 和slice 初始化slice表现出的不同
~~~
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
~~~
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

### 闭包的坑
猜猜下面的结果
~~~ golang
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
~~~
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
methods may be declared on any named type defined
in the same package , so long as its underlying type is
neither a pointer nor an interface.
出自 the golang programming language  157 page
函数也可以有方法==
两种调用方法都是有效的
~~~
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