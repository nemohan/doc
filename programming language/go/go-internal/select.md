# select 

[TOC]



### 用到的文件

~~~go

package main

import (
	"fmt"
)

var ch_int = make(chan int, 10)

func main() {
	go test_fun()
	select {
	case t := <-ch_int:
		fmt.Printf("%v\n", t)
	default:
	}
}

func test_fun() {
	ch_int <- 0
}

~~~





### 编译和反汇编

GOARCH=386 go build -gcflags "-E" -o main_select main_select.go

objdump -DgSIFls main_select > main_select_objdump



DSlF有行号





### 对应的反汇编

~~~assembly

080b34b0 <main.main>:
	"fmt"
)

var ch_int = make(chan int, 10)

func main() {
 80b34b0:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
 80b34b7:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx
 80b34bd:	3b 61 08             	cmp    0x8(%ecx),%esp
 80b34c0:	0f 86 b4 00 00 00    	jbe    80b357a <main.main+0xca>
 80b34c6:	83 ec 30             	sub    $0x30,%esp
	go test_fun()
 80b34c9:	c7 04 24 00 00 00 00 	movl   $0x0,(%esp)
 80b34d0:	8d 05 3c 8c 0d 08    	lea    0x80d8c3c,%eax
 80b34d6:	89 44 24 04          	mov    %eax,0x4(%esp)
 80b34da:	e8 d1 e7 fb ff       	call   8071cb0 <runtime.newproc>
	select {
	case t := <-ch_int:
 80b34df:	8d 05 a0 eb 0b 08    	lea    0x80beba0,%eax
 80b34e5:	89 04 24             	mov    %eax,(%esp)
 80b34e8:	8d 44 24 24          	lea    0x24(%esp),%eax
 80b34ec:	89 44 24 04          	mov    %eax,0x4(%esp)
 80b34f0:	8b 05 4c ad 11 08    	mov    0x811ad4c,%eax
 80b34f6:	89 44 24 08          	mov    %eax,0x8(%esp)
 80b34fa:	e8 c1 92 f9 ff       	call   804c7c0 <runtime.selectnbrecv>
 80b34ff:	0f b6 44 24 0c       	movzbl 0xc(%esp),%eax
 80b3504:	84 c0                	test   %al,%al
 80b3506:	75 04                	jne    80b350c <main.main+0x5c>
		fmt.Printf("%v\n", t)
	default:
	}
}
 80b3508:	83 c4 30             	add    $0x30,%esp
 80b350b:	c3                   	ret    
var ch_int = make(chan int, 10)

func main() {
	go test_fun()
	select {
	case t := <-ch_int:
 80b350c:	8b 44 24 24          	mov    0x24(%esp),%eax
		fmt.Printf("%v\n", t)
 80b3510:	89 44 24 20          	mov    %eax,0x20(%esp)
 80b3514:	c7 44 24 28 00 00 00 	movl   $0x0,0x28(%esp)
 80b351b:	00 
 80b351c:	c7 44 24 2c 00 00 00 	movl   $0x0,0x2c(%esp)
 80b3523:	00 
 80b3524:	8d 05 00 1e 0c 08    	lea    0x80c1e00,%eax
 80b352a:	89 04 24             	mov    %eax,(%esp)
 80b352d:	8d 44 24 20          	lea    0x20(%esp),%eax
 80b3531:	89 44 24 04          	mov    %eax,0x4(%esp)
 80b3535:	e8 b6 e2 f9 ff       	call   80517f0 <runtime.convT2E>
 80b353a:	8b 44 24 0c          	mov    0xc(%esp),%eax
 80b353e:	8b 4c 24 08          	mov    0x8(%esp),%ecx
 80b3542:	89 4c 24 28          	mov    %ecx,0x28(%esp)
 80b3546:	89 44 24 2c          	mov    %eax,0x2c(%esp)
 80b354a:	8d 05 39 29 0d 08    	lea    0x80d2939,%eax
 80b3550:	89 04 24             	mov    %eax,(%esp)
 80b3553:	c7 44 24 04 03 00 00 	movl   $0x3,0x4(%esp)
 80b355a:	00 
 80b355b:	8d 44 24 28          	lea    0x28(%esp),%eax
 80b355f:	89 44 24 08          	mov    %eax,0x8(%esp)
 80b3563:	c7 44 24 0c 01 00 00 	movl   $0x1,0xc(%esp)
 80b356a:	00 
 80b356b:	c7 44 24 10 01 00 00 	movl   $0x1,0x10(%esp)
 80b3572:	00 
 80b3573:	e8 48 8f ff ff       	call   80ac4c0 <fmt.Printf>
	default:
	}
}
 80b3578:	eb 8e                	jmp    80b3508 <main.main+0x58>
	"fmt"
)

var ch_int = make(chan int, 10)

func main() {
 80b357a:	e8 81 6e fd ff       	call   808a400 <runtime.morestack_noctxt>
 80b357f:	e9 2c ff ff ff       	jmp    80b34b0 <main.main>
 80b3584:	cc                   	int3   
 80b3585:	cc                   	int3   
 80b3586:	cc                   	int3   
 80b3587:	cc                   	int3   
 80b3588:	cc                   	int3   
 80b3589:	cc                   	int3   
 80b358a:	cc                   	int3   
 80b358b:	cc                   	int3   
 80b358c:	cc                   	int3   
 80b358d:	cc                   	int3   
 80b358e:	cc                   	int3   
 80b358f:	cc                   	int3   

080b3590 <main.test_fun>:
		fmt.Printf("%v\n", t)
	default:
	}
}

func test_fun() {
 80b3590:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
 80b3597:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx
 80b359d:	3b 61 08             	cmp    0x8(%ecx),%esp
 80b35a0:	76 2f                	jbe    80b35d1 <main.test_fun+0x41>
 80b35a2:	83 ec 10             	sub    $0x10,%esp
	ch_int <- 0
 80b35a5:	c7 44 24 0c 00 00 00 	movl   $0x0,0xc(%esp)
 80b35ac:	00 
 80b35ad:	8d 05 a0 eb 0b 08    	lea    0x80beba0,%eax
 80b35b3:	89 04 24             	mov    %eax,(%esp)
 80b35b6:	8b 05 4c ad 11 08    	mov    0x811ad4c,%eax
 80b35bc:	89 44 24 04          	mov    %eax,0x4(%esp)
 80b35c0:	8d 44 24 0c          	lea    0xc(%esp),%eax
 80b35c4:	89 44 24 08          	mov    %eax,0x8(%esp)
 80b35c8:	e8 83 7b f9 ff       	call   804b150 <runtime.chansend1>
}
 80b35cd:	83 c4 10             	add    $0x10,%esp
 80b35d0:	c3                   	ret    
		fmt.Printf("%v\n", t)
	default:
	}
}

func test_fun() {
 80b35d1:	e8 2a 6e fd ff       	call   808a400 <runtime.morestack_noctxt>
 80b35d6:	eb b8                	jmp    80b3590 <main.test_fun>
 80b35d8:	cc                   	int3   
 80b35d9:	cc                   	int3   
 80b35da:	cc                   	int3   
 80b35db:	cc                   	int3   
 80b35dc:	cc                   	int3   
 80b35dd:	cc                   	int3   
 80b35de:	cc                   	int3   
 80b35df:	cc                   	int3   

080b35e0 <main.init>:
	ch_int <- 0
}
 80b35e0:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
 80b35e7:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx
 80b35ed:	3b 61 08             	cmp    0x8(%ecx),%esp
 80b35f0:	76 79                	jbe    80b366b <main.init+0x8b>
 80b35f2:	83 ec 10             	sub    $0x10,%esp
 80b35f5:	0f b6 05 82 ac 12 08 	movzbl 0x812ac82,%eax
 80b35fc:	80 f8 01             	cmp    $0x1,%al
 80b35ff:	76 04                	jbe    80b3605 <main.init+0x25>
 80b3601:	83 c4 10             	add    $0x10,%esp
 80b3604:	c3                   	ret    
 80b3605:	75 07                	jne    80b360e <main.init+0x2e>
 80b3607:	e8 24 59 fb ff       	call   8068f30 <runtime.throwinit>
 80b360c:	0f 0b                	ud2    
 80b360e:	c6 05 82 ac 12 08 01 	movb   $0x1,0x812ac82
 80b3615:	e8 26 fc ff ff       	call   80b3240 <fmt.init>

import (
	"fmt"
)

var ch_int = make(chan int, 10)
 80b361a:	8d 05 a0 eb 0b 08    	lea    0x80beba0,%eax
 // ##################### 0x80beba0 这个应该是 第一个参数 chantype* 的指针
 
 80b3620:	89 04 24             	mov    %eax,(%esp)
 80b3623:	c7 44 24 04 0a 00 00 	movl   $0xa,0x4(%esp)
 80b362a:	00 
 80b362b:	c7 44 24 08 00 00 00 	movl   $0x0,0x8(%esp)
 80b3632:	00 
 80b3633:	e8 78 78 f9 ff       	call   804aeb0 <runtime.makechan>
 //####＃＃＃＃＃＃＃＃＃＃ 调用runtime/chan.go 的makechan函数
 
 80b3638:	8b 44 24 0c          	mov    0xc(%esp),%eax
 80b363c:	8b 0d f0 ad 12 08    	mov    0x812adf0,%ecx
 80b3642:	85 c9                	test   %ecx,%ecx
 80b3644:	75 11                	jne    80b3657 <main.init+0x77>
 80b3646:	89 05 4c ad 11 08    	mov    %eax,0x811ad4c
}

func test_fun() {
	ch_int <- 0
}
 80b364c:	c6 05 82 ac 12 08 02 	movb   $0x2,0x812ac82
 80b3653:	83 c4 10             	add    $0x10,%esp
 80b3656:	c3                   	ret    

import (
	"fmt"
)

var ch_int = make(chan int, 10)
 80b3657:	8d 0d 4c ad 11 08    	lea    0x811ad4c,%ecx
 80b365d:	89 0c 24             	mov    %ecx,(%esp)
 80b3660:	89 44 24 04          	mov    %eax,0x4(%esp)
 80b3664:	e8 a7 0a fa ff       	call   8054110 <runtime.writebarrierptr>
 80b3669:	eb e1                	jmp    80b364c <main.init+0x6c>
 80b366b:	e8 90 6d fd ff       	call   808a400 <runtime.morestack_noctxt>
 80b3670:	e9 6b ff ff ff       	jmp    80b35e0 <main.init>


~~~





## 多select 分支



~~~go

package main

import (
	"fmt"
)

var ch_int = make(chan int, 10)
var ch1 = make(chan int, 6)
var ch2 = make(chan bool, 2)

func main() {
	go test_fun()
	select {
	case t := <-ch_int:
		fmt.Printf("%v\n", t)
	case t1 := <-ch1:
		fmt.Printf("%v\n", t1)
	case t2 := <-ch2:
		fmt.Printf("%v\n", t2)
	default:
	}
}

func test_fun() {
	ch_int <- 2
	ch1 <- 1
	ch2 <- false
}


~~~





### 对应的反汇编



~~~assembly

080b57f0 <main.main> (File Offset: 0x6d7f0):
main.main():
/home/hanzhao/workspace/go_runtime/main_select.go:11

var ch_int = make(chan int, 10)
var ch1 = make(chan int, 6)
var ch2 = make(chan bool, 2)

func main() {
 80b57f0:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
 80b57f7:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx
 80b57fd:	8d 44 24 a8          	lea    -0x58(%esp),%eax
 80b5801:	3b 41 08             	cmp    0x8(%ecx),%eax
 80b5804:	0f 86 3e 02 00 00    	jbe    80b5a48 <main.main+0x258> (File Offset: 0x6da48)
 80b580a:	81 ec d8 00 00 00    	sub    $0xd8,%esp
/home/hanzhao/workspace/go_runtime/main_select.go:12
	go test_fun()
 80b5810:	c7 04 24 00 00 00 00 	movl   $0x0,(%esp)
 80b5817:	8d 05 98 b4 0d 08    	lea    0x80db498,%eax
 80b581d:	89 44 24 04          	mov    %eax,0x4(%esp)
 80b5821:	e8 8a c4 fb ff       	call   8071cb0 <runtime.newproc> (File Offset: 0x29cb0)
/home/hanzhao/workspace/go_runtime/main_select.go:13
	select {
 80b5826:	8d 7c 24 4c          	lea    0x4c(%esp),%edi
/home/hanzhao/workspace/go_runtime/main_select.go:12
var ch_int = make(chan int, 10)
var ch1 = make(chan int, 6)
var ch2 = make(chan bool, 2)

func main() {
	go test_fun()
 80b582a:	31 c0                	xor    %eax,%eax
/home/hanzhao/workspace/go_runtime/main_select.go:13
	select {
 80b582c:	e8 cc 8a fd ff       	call   808e2fd <runtime.duffzero+0x5d> (File Offset: 0x462fd)
 80b5831:	8d 44 24 4c          	lea    0x4c(%esp),%eax
 80b5835:	89 04 24             	mov    %eax,(%esp)
 //################ 这是第一个参数  sel *hselect
 
 80b5838:	c7 44 24 04 8c 00 00 	movl   $0x8c,0x4(%esp)
 80b583f:	00 
 //############## selsize 参数
 80b5840:	c7 44 24 08 00 00 00 	movl   $0x0,0x8(%esp)
 //#################  这个0值 很是奇怪???????????????????
 80b5847:	00 
 80b5848:	c7 44 24 0c 04 00 00 	movl   $0x4,0xc(%esp)
 // ############# case 数目  size 参数
 80b584f:	00 
 80b5850:	e8 1b 23 fc ff       	call   8077b70 <runtime.newselect> (File Offset: 0x2fb70)
 //## stack
 0x4
 0
 0x8c
 sel
 ret
 //############## 调用 runtime/select.go  
 //################# newselect(sel *hselect, selsize int64, size int32)
 
 80b5855:	8d 44 24 4c          	lea    0x4c(%esp),%eax
/home/hanzhao/workspace/go_runtime/main_select.go:14
	case t := <-ch_int:
 80b5859:	89 04 24             	mov    %eax,(%esp)
/home/hanzhao/workspace/go_runtime/main_select.go:13
var ch1 = make(chan int, 6)
var ch2 = make(chan bool, 2)

func main() {
	go test_fun()
	select {
 80b585c:	8b 0d 54 dd 11 08    	mov    0x811dd54,%ecx
 //##### ch_int的地址
/home/hanzhao/workspace/go_runtime/main_select.go:14
	case t := <-ch_int:
 80b5862:	89 4c 24 04          	mov    %ecx,0x4(%esp)
 80b5866:	8d 4c 24 30          	lea    0x30(%esp),%ecx
 //########### 0x30(%esp)算是t 的地址应该
 
 80b586a:	89 4c 24 08          	mov    %ecx,0x8(%esp)
 80b586e:	e8 5d 24 fc ff       	call   8077cd0 <runtime.selectrecv> (File Offset: 0x2fcd0)
 //###### stack 的样子
 &t,
 ch_int
 sel
 
 80b5873:	0f b6 44 24 0c       	movzbl 0xc(%esp),%eax
 80b5878:	84 c0                	test   %al,%al
 80b587a:	74 73                	je     80b58ef <main.main+0xff> (File Offset: 0x6d8ef)
 80b587c:	8b 44 24 30          	mov    0x30(%esp),%eax
/home/hanzhao/workspace/go_runtime/main_select.go:15
		fmt.Printf("%v\n", t)
 80b5880:	89 44 24 2c          	mov    %eax,0x2c(%esp)
 80b5884:	c7 44 24 44 00 00 00 	movl   $0x0,0x44(%esp)
 80b588b:	00 
 80b588c:	c7 44 24 48 00 00 00 	movl   $0x0,0x48(%esp)
 80b5893:	00 
 80b5894:	8d 05 a0 40 0c 08    	lea    0x80c40a0,%eax
 80b589a:	89 04 24             	mov    %eax,(%esp)
 80b589d:	8d 44 24 2c          	lea    0x2c(%esp),%eax
 80b58a1:	89 44 24 04          	mov    %eax,0x4(%esp)
 80b58a5:	e8 f6 be f9 ff       	call   80517a0 <runtime.convT2E> (File Offset: 0x97a0)
 80b58aa:	8b 44 24 0c          	mov    0xc(%esp),%eax
 80b58ae:	8b 4c 24 08          	mov    0x8(%esp),%ecx
 80b58b2:	89 4c 24 44          	mov    %ecx,0x44(%esp)
 80b58b6:	89 44 24 48          	mov    %eax,0x48(%esp)
 80b58ba:	8d 05 19 51 0d 08    	lea    0x80d5119,%eax
 80b58c0:	89 04 24             	mov    %eax,(%esp)
 80b58c3:	c7 44 24 04 03 00 00 	movl   $0x3,0x4(%esp)
 80b58ca:	00 
 80b58cb:	8d 44 24 44          	lea    0x44(%esp),%eax
 80b58cf:	89 44 24 08          	mov    %eax,0x8(%esp)
 80b58d3:	c7 44 24 0c 01 00 00 	movl   $0x1,0xc(%esp)
 80b58da:	00 
 80b58db:	c7 44 24 10 01 00 00 	movl   $0x1,0x10(%esp)
 80b58e2:	00 
 80b58e3:	e8 18 8f ff ff       	call   80ae800 <fmt.Printf> (File Offset: 0x66800)
/home/hanzhao/workspace/go_runtime/main_select.go:22
		fmt.Printf("%v\n", t1)
	case t2 := <-ch2:
		fmt.Printf("%v\n", t2)
	default:
	}
}
 80b58e8:	81 c4 d8 00 00 00    	add    $0xd8,%esp
 80b58ee:	c3                   	ret    
/home/hanzhao/workspace/go_runtime/main_select.go:13
var ch1 = make(chan int, 6)
var ch2 = make(chan bool, 2)

func main() {
	go test_fun()
	select {
 80b58ef:	8d 44 24 4c          	lea    0x4c(%esp),%eax
/home/hanzhao/workspace/go_runtime/main_select.go:16
	case t := <-ch_int:
		fmt.Printf("%v\n", t)
	case t1 := <-ch1:
 80b58f3:	89 04 24             	mov    %eax,(%esp)
/home/hanzhao/workspace/go_runtime/main_select.go:13
var ch1 = make(chan int, 6)
var ch2 = make(chan bool, 2)

func main() {
	go test_fun()
	select {
 80b58f6:	8b 0d 4c dd 11 08    	mov    0x811dd4c,%ecx
/home/hanzhao/workspace/go_runtime/main_select.go:16
	case t := <-ch_int:
		fmt.Printf("%v\n", t)
	case t1 := <-ch1:
 80b58fc:	89 4c 24 04          	mov    %ecx,0x4(%esp)
 80b5900:	8d 4c 24 28          	lea    0x28(%esp),%ecx
 80b5904:	89 4c 24 08          	mov    %ecx,0x8(%esp)
 80b5908:	e8 c3 23 fc ff       	call   8077cd0 <runtime.selectrecv> (File Offset: 0x2fcd0)
 80b590d:	0f b6 44 24 0c       	movzbl 0xc(%esp),%eax
 80b5912:	84 c0                	test   %al,%al
 80b5914:	74 71                	je     80b5987 <main.main+0x197> (File Offset: 0x6d987)
 80b5916:	8b 44 24 28          	mov    0x28(%esp),%eax
/home/hanzhao/workspace/go_runtime/main_select.go:17
		fmt.Printf("%v\n", t1)
 80b591a:	89 44 24 24          	mov    %eax,0x24(%esp)
 80b591e:	c7 44 24 3c 00 00 00 	movl   $0x0,0x3c(%esp)
 80b5925:	00 
 80b5926:	c7 44 24 40 00 00 00 	movl   $0x0,0x40(%esp)
 80b592d:	00 
/home/hanzhao/workspace/go_runtime/main_select.go:15

func main() {
	go test_fun()
	select {
	case t := <-ch_int:
		fmt.Printf("%v\n", t)
 80b592e:	8d 05 a0 40 0c 08    	lea    0x80c40a0,%eax
/home/hanzhao/workspace/go_runtime/main_select.go:17
	case t1 := <-ch1:
		fmt.Printf("%v\n", t1)
 80b5934:	89 04 24             	mov    %eax,(%esp)
 80b5937:	8d 44 24 24          	lea    0x24(%esp),%eax
 80b593b:	89 44 24 04          	mov    %eax,0x4(%esp)
 80b593f:	e8 5c be f9 ff       	call   80517a0 <runtime.convT2E> (File Offset: 0x97a0)
 80b5944:	8b 44 24 0c          	mov    0xc(%esp),%eax
 80b5948:	8b 4c 24 08          	mov    0x8(%esp),%ecx
 80b594c:	89 4c 24 3c          	mov    %ecx,0x3c(%esp)
 80b5950:	89 44 24 40          	mov    %eax,0x40(%esp)
 80b5954:	8d 05 19 51 0d 08    	lea    0x80d5119,%eax
 80b595a:	89 04 24             	mov    %eax,(%esp)
 80b595d:	c7 44 24 04 03 00 00 	movl   $0x3,0x4(%esp)
 80b5964:	00 
 80b5965:	8d 44 24 3c          	lea    0x3c(%esp),%eax
 80b5969:	89 44 24 08          	mov    %eax,0x8(%esp)
 80b596d:	c7 44 24 0c 01 00 00 	movl   $0x1,0xc(%esp)
 80b5974:	00 
 80b5975:	c7 44 24 10 01 00 00 	movl   $0x1,0x10(%esp)
 80b597c:	00 
 80b597d:	e8 7e 8e ff ff       	call   80ae800 <fmt.Printf> (File Offset: 0x66800)
/home/hanzhao/workspace/go_runtime/main_select.go:22
	case t2 := <-ch2:
		fmt.Printf("%v\n", t2)
	default:
	}
}
 80b5982:	e9 61 ff ff ff       	jmp    80b58e8 <main.main+0xf8> (File Offset: 0x6d8e8)
/home/hanzhao/workspace/go_runtime/main_select.go:13
var ch1 = make(chan int, 6)
var ch2 = make(chan bool, 2)

func main() {
	go test_fun()
	select {
 80b5987:	8d 44 24 4c          	lea    0x4c(%esp),%eax
/home/hanzhao/workspace/go_runtime/main_select.go:18
	case t := <-ch_int:
		fmt.Printf("%v\n", t)
	case t1 := <-ch1:
		fmt.Printf("%v\n", t1)
	case t2 := <-ch2:
 80b598b:	89 04 24             	mov    %eax,(%esp)
/home/hanzhao/workspace/go_runtime/main_select.go:13
var ch1 = make(chan int, 6)
var ch2 = make(chan bool, 2)

func main() {
	go test_fun()
	select {
 80b598e:	8b 0d 50 dd 11 08    	mov    0x811dd50,%ecx
/home/hanzhao/workspace/go_runtime/main_select.go:18
	case t := <-ch_int:
		fmt.Printf("%v\n", t)
	case t1 := <-ch1:
		fmt.Printf("%v\n", t1)
	case t2 := <-ch2:
 80b5994:	89 4c 24 04          	mov    %ecx,0x4(%esp)
 80b5998:	8d 4c 24 23          	lea    0x23(%esp),%ecx
 80b599c:	89 4c 24 08          	mov    %ecx,0x8(%esp)
 80b59a0:	e8 2b 23 fc ff       	call   8077cd0 <runtime.selectrecv> (File Offset: 0x2fcd0)
 80b59a5:	0f b6 44 24 0c       	movzbl 0xc(%esp),%eax
 80b59aa:	84 c0                	test   %al,%al
 80b59ac:	74 72                	je     80b5a20 <main.main+0x230> (File Offset: 0x6da20)
 80b59ae:	0f b6 44 24 23       	movzbl 0x23(%esp),%eax
/home/hanzhao/workspace/go_runtime/main_select.go:19
		fmt.Printf("%v\n", t2)
 80b59b3:	88 44 24 22          	mov    %al,0x22(%esp)
 80b59b7:	c7 44 24 34 00 00 00 	movl   $0x0,0x34(%esp)
 80b59be:	00 
 80b59bf:	c7 44 24 38 00 00 00 	movl   $0x0,0x38(%esp)
 80b59c6:	00 
 80b59c7:	8d 05 a0 3c 0c 08    	lea    0x80c3ca0,%eax
 80b59cd:	89 04 24             	mov    %eax,(%esp)
 80b59d0:	8d 44 24 22          	lea    0x22(%esp),%eax
 80b59d4:	89 44 24 04          	mov    %eax,0x4(%esp)
 80b59d8:	e8 c3 bd f9 ff       	call   80517a0 <runtime.convT2E> (File Offset: 0x97a0)
 80b59dd:	8b 44 24 0c          	mov    0xc(%esp),%eax
 80b59e1:	8b 4c 24 08          	mov    0x8(%esp),%ecx
 80b59e5:	89 4c 24 34          	mov    %ecx,0x34(%esp)
 80b59e9:	89 44 24 38          	mov    %eax,0x38(%esp)
 80b59ed:	8d 05 19 51 0d 08    	lea    0x80d5119,%eax
 80b59f3:	89 04 24             	mov    %eax,(%esp)
 80b59f6:	c7 44 24 04 03 00 00 	movl   $0x3,0x4(%esp)
 80b59fd:	00 
 80b59fe:	8d 44 24 34          	lea    0x34(%esp),%eax
 80b5a02:	89 44 24 08          	mov    %eax,0x8(%esp)
 80b5a06:	c7 44 24 0c 01 00 00 	movl   $0x1,0xc(%esp)
 80b5a0d:	00 
 80b5a0e:	c7 44 24 10 01 00 00 	movl   $0x1,0x10(%esp)
 80b5a15:	00 
 80b5a16:	e8 e5 8d ff ff       	call   80ae800 <fmt.Printf> (File Offset: 0x66800)
/home/hanzhao/workspace/go_runtime/main_select.go:22
	default:
	}
}
 80b5a1b:	e9 c8 fe ff ff       	jmp    80b58e8 <main.main+0xf8> (File Offset: 0x6d8e8)
/home/hanzhao/workspace/go_runtime/main_select.go:13
var ch1 = make(chan int, 6)
var ch2 = make(chan bool, 2)

func main() {
	go test_fun()
	select {
 80b5a20:	8d 44 24 4c          	lea    0x4c(%esp),%eax
/home/hanzhao/workspace/go_runtime/main_select.go:20
		fmt.Printf("%v\n", t)
	case t1 := <-ch1:
		fmt.Printf("%v\n", t1)
	case t2 := <-ch2:
		fmt.Printf("%v\n", t2)
	default:
 80b5a24:	89 04 24             	mov    %eax,(%esp)
 80b5a27:	e8 04 24 fc ff       	call   8077e30 <runtime.selectdefault> (File Offset: 0x2fe30)
 80b5a2c:	0f b6 44 24 04       	movzbl 0x4(%esp),%eax
 80b5a31:	84 c0                	test   %al,%al
 80b5a33:	74 05                	je     80b5a3a <main.main+0x24a> (File Offset: 0x6da3a)
/home/hanzhao/workspace/go_runtime/main_select.go:22
	}
}
 80b5a35:	e9 ae fe ff ff       	jmp    80b58e8 <main.main+0xf8> (File Offset: 0x6d8e8)
/home/hanzhao/workspace/go_runtime/main_select.go:13
var ch1 = make(chan int, 6)
var ch2 = make(chan bool, 2)

func main() {
	go test_fun()
	select {
 80b5a3a:	8d 44 24 4c          	lea    0x4c(%esp),%eax
 80b5a3e:	89 04 24             	mov    %eax,(%esp)
 80b5a41:	e8 fa 26 fc ff       	call   8078140 <runtime.selectgo> (File Offset: 0x30140)
 80b5a46:	0f 0b                	ud2    
/home/hanzhao/workspace/go_runtime/main_select.go:11

var ch_int = make(chan int, 10)
var ch1 = make(chan int, 6)
var ch2 = make(chan bool, 2)

func main() {
 80b5a48:	e8 c3 6c fd ff       	call   808c710 <runtime.morestack_noctxt> (File Offset: 0x44710)
 80b5a4d:	e9 9e fd ff ff       	jmp    80b57f0 <main.main> (File Offset: 0x6d7f0)
 80b5a52:	cc                   	int3   
 80b5a53:	cc                   	int3   
 80b5a54:	cc                   	int3   
 80b5a55:	cc                   	int3   
 80b5a56:	cc                   	int3   
 80b5a57:	cc                   	int3   
 80b5a58:	cc                   	int3   
 80b5a59:	cc                   	int3   
 80b5a5a:	cc                   	int3   
 80b5a5b:	cc                   	int3   
 80b5a5c:	cc                   	int3   
 80b5a5d:	cc                   	int3   
 80b5a5e:	cc                   	int3   
 80b5a5f:	cc                   	int3   

080b5a60 <main.test_fun> (File Offset: 0x6da60):
main.test_fun():
/home/hanzhao/workspace/go_runtime/main_select.go:24
		fmt.Printf("%v\n", t2)
	default:
	}
}

func test_fun() {
 80b5a60:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
 80b5a67:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx
 80b5a6d:	3b 61 08             	cmp    0x8(%ecx),%esp
 80b5a70:	76 7c                	jbe    80b5aee <main.test_fun+0x8e> (File Offset: 0x6daee)
 80b5a72:	83 ec 18             	sub    $0x18,%esp
/home/hanzhao/workspace/go_runtime/main_select.go:25
	ch_int <- 2
 80b5a75:	c7 44 24 14 02 00 00 	movl   $0x2,0x14(%esp)
 80b5a7c:	00 
 80b5a7d:	8d 05 80 0d 0c 08    	lea    0x80c0d80,%eax
 80b5a83:	89 04 24             	mov    %eax,(%esp)
 80b5a86:	8b 0d 54 dd 11 08    	mov    0x811dd54,%ecx
 80b5a8c:	89 4c 24 04          	mov    %ecx,0x4(%esp)
 80b5a90:	8d 4c 24 14          	lea    0x14(%esp),%ecx
 80b5a94:	89 4c 24 08          	mov    %ecx,0x8(%esp)
 80b5a98:	e8 b3 56 f9 ff       	call   804b150 <runtime.chansend1> (File Offset: 0x3150)
/home/hanzhao/workspace/go_runtime/main_select.go:26
	ch1 <- 1
 80b5a9d:	c7 44 24 10 01 00 00 	movl   $0x1,0x10(%esp)
 80b5aa4:	00 
/home/hanzhao/workspace/go_runtime/main_select.go:25
	default:
	}
}

func test_fun() {
	ch_int <- 2
 80b5aa5:	8d 05 80 0d 0c 08    	lea    0x80c0d80,%eax
/home/hanzhao/workspace/go_runtime/main_select.go:26
	ch1 <- 1
 80b5aab:	89 04 24             	mov    %eax,(%esp)
 80b5aae:	8b 05 4c dd 11 08    	mov    0x811dd4c,%eax
 80b5ab4:	89 44 24 04          	mov    %eax,0x4(%esp)
 80b5ab8:	8d 44 24 10          	lea    0x10(%esp),%eax
 80b5abc:	89 44 24 08          	mov    %eax,0x8(%esp)
 80b5ac0:	e8 8b 56 f9 ff       	call   804b150 <runtime.chansend1> (File Offset: 0x3150)
/home/hanzhao/workspace/go_runtime/main_select.go:27
	ch2 <- false
 80b5ac5:	c6 44 24 0f 00       	movb   $0x0,0xf(%esp)
 80b5aca:	8d 05 40 0d 0c 08    	lea    0x80c0d40,%eax
 80b5ad0:	89 04 24             	mov    %eax,(%esp)
 80b5ad3:	8b 05 50 dd 11 08    	mov    0x811dd50,%eax
 80b5ad9:	89 44 24 04          	mov    %eax,0x4(%esp)
 80b5add:	8d 44 24 0f          	lea    0xf(%esp),%eax
 80b5ae1:	89 44 24 08          	mov    %eax,0x8(%esp)
 80b5ae5:	e8 66 56 f9 ff       	call   804b150 <runtime.chansend1> (File Offset: 0x3150)
/home/hanzhao/workspace/go_runtime/main_select.go:28
}
 80b5aea:	83 c4 18             	add    $0x18,%esp
 80b5aed:	c3                   	ret    
/home/hanzhao/workspace/go_runtime/main_select.go:24
		fmt.Printf("%v\n", t2)
	default:
	}
}

func test_fun() {
 80b5aee:	e8 1d 6c fd ff       	call   808c710 <runtime.morestack_noctxt> (File Offset: 0x44710)
 80b5af3:	e9 68 ff ff ff       	jmp    80b5a60 <main.test_fun> (File Offset: 0x6da60)
 80b5af8:	cc                   	int3   
 80b5af9:	cc                   	int3   
 80b5afa:	cc                   	int3   
 80b5afb:	cc                   	int3   
 80b5afc:	cc                   	int3   
 80b5afd:	cc                   	int3   
 80b5afe:	cc                   	int3   
 80b5aff:	cc                   	int3   

080b5b00 <main.init> (File Offset: 0x6db00):
main.init():
/home/hanzhao/workspace/go_runtime/main_select.go:29
	ch_int <- 2
	ch1 <- 1
	ch2 <- false
}
 80b5b00:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
 80b5b07:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx
 80b5b0d:	3b 61 08             	cmp    0x8(%ecx),%esp
 80b5b10:	0f 86 0c 01 00 00    	jbe    80b5c22 <main.init+0x122> (File Offset: 0x6dc22)
 80b5b16:	83 ec 10             	sub    $0x10,%esp
 80b5b19:	0f b6 05 82 dc 12 08 	movzbl 0x812dc82,%eax
 80b5b20:	80 f8 01             	cmp    $0x1,%al
 80b5b23:	76 04                	jbe    80b5b29 <main.init+0x29> (File Offset: 0x6db29)
 80b5b25:	83 c4 10             	add    $0x10,%esp
 80b5b28:	c3                   	ret    
 80b5b29:	75 07                	jne    80b5b32 <main.init+0x32> (File Offset: 0x6db32)
 80b5b2b:	e8 00 34 fb ff       	call   8068f30 <runtime.throwinit> (File Offset: 0x20f30)
 80b5b30:	0f 0b                	ud2    
 80b5b32:	c6 05 82 dc 12 08 01 	movb   $0x1,0x812dc82
 80b5b39:	e8 42 fa ff ff       	call   80b5580 <fmt.init> (File Offset: 0x6d580)
/home/hanzhao/workspace/go_runtime/main_select.go:7

import (
	"fmt"
)

var ch_int = make(chan int, 10)
 80b5b3e:	8d 05 80 0d 0c 08    	lea    0x80c0d80,%eax
 80b5b44:	89 04 24             	mov    %eax,(%esp)
 80b5b47:	c7 44 24 04 0a 00 00 	movl   $0xa,0x4(%esp)
 80b5b4e:	00 
 80b5b4f:	c7 44 24 08 00 00 00 	movl   $0x0,0x8(%esp)
 80b5b56:	00 
 80b5b57:	e8 54 53 f9 ff       	call   804aeb0 <runtime.makechan> (File Offset: 0x2eb0)
 80b5b5c:	8b 44 24 0c          	mov    0xc(%esp),%eax
 80b5b60:	8b 0d f0 dd 12 08    	mov    0x812ddf0,%ecx
 80b5b66:	85 c9                	test   %ecx,%ecx
 80b5b68:	0f 85 9d 00 00 00    	jne    80b5c0b <main.init+0x10b> (File Offset: 0x6dc0b)
 80b5b6e:	89 05 54 dd 11 08    	mov    %eax,0x811dd54
 //############# 0x811dd54 是 ch_int 的地址
 
 80b5b74:	8d 05 80 0d 0c 08    	lea    0x80c0d80,%eax
/home/hanzhao/workspace/go_runtime/main_select.go:8
var ch1 = make(chan int, 6)
 80b5b7a:	89 04 24             	mov    %eax,(%esp)
 80b5b7d:	c7 44 24 04 06 00 00 	movl   $0x6,0x4(%esp)
 80b5b84:	00 
 80b5b85:	c7 44 24 08 00 00 00 	movl   $0x0,0x8(%esp)
 80b5b8c:	00 
 80b5b8d:	e8 1e 53 f9 ff       	call   804aeb0 <runtime.makechan> (File Offset: 0x2eb0)
 
 
 80b5b92:	8b 44 24 0c          	mov    0xc(%esp),%eax
 80b5b96:	8b 0d f0 dd 12 08    	mov    0x812ddf0,%ecx
 80b5b9c:	85 c9                	test   %ecx,%ecx
 80b5b9e:	75 57                	jne    80b5bf7 <main.init+0xf7> (File Offset: 0x6dbf7)
 80b5ba0:	89 05 4c dd 11 08    	mov    %eax,0x811dd4c
 //################ 0x811dd4c 是ch1 的地址
 
/home/hanzhao/workspace/go_runtime/main_select.go:9
var ch2 = make(chan bool, 2)
 80b5ba6:	8d 05 40 0d 0c 08    	lea    0x80c0d40,%eax
 80b5bac:	89 04 24             	mov    %eax,(%esp)
 80b5baf:	c7 44 24 04 02 00 00 	movl   $0x2,0x4(%esp)
 80b5bb6:	00 
 80b5bb7:	c7 44 24 08 00 00 00 	movl   $0x0,0x8(%esp)
 80b5bbe:	00 
 80b5bbf:	e8 ec 52 f9 ff       	call   804aeb0 <runtime.makechan> (File Offset: 0x2eb0)
 80b5bc4:	8b 44 24 0c          	mov    0xc(%esp),%eax
 80b5bc8:	8b 0d f0 dd 12 08    	mov    0x812ddf0,%ecx
 80b5bce:	85 c9                	test   %ecx,%ecx
 80b5bd0:	75 11                	jne    80b5be3 <main.init+0xe3> (File Offset: 0x6dbe3)
 80b5bd2:	89 05 50 dd 11 08    	mov    %eax,0x811dd50
 //################# 0x811dd50 是ch2的地址
/home/hanzhao/workspace/go_runtime/main_select.go:29
func test_fun() {
	ch_int <- 2
	ch1 <- 1
	ch2 <- false
}
 80b5bd8:	c6 05 82 dc 12 08 02 	movb   $0x2,0x812dc82
 80b5bdf:	83 c4 10             	add    $0x10,%esp
 80b5be2:	c3                   	ret    
/home/hanzhao/workspace/go_runtime/main_select.go:9
	"fmt"
)

var ch_int = make(chan int, 10)
var ch1 = make(chan int, 6)
var ch2 = make(chan bool, 2)
 80b5be3:	8d 0d 50 dd 11 08    	lea    0x811dd50,%ecx
 80b5be9:	89 0c 24             	mov    %ecx,(%esp)
 80b5bec:	89 44 24 04          	mov    %eax,0x4(%esp)
 80b5bf0:	e8 cb e4 f9 ff       	call   80540c0 <runtime.writebarrierptr> (File Offset: 0xc0c0)
/home/hanzhao/workspace/go_runtime/main_select.go:29
func test_fun() {
	ch_int <- 2
	ch1 <- 1
	ch2 <- false
}
 80b5bf5:	eb e1                	jmp    80b5bd8 <main.init+0xd8> (File Offset: 0x6dbd8)
/home/hanzhao/workspace/go_runtime/main_select.go:8
import (
	"fmt"
)

var ch_int = make(chan int, 10)
var ch1 = make(chan int, 6)
 80b5bf7:	8d 0d 4c dd 11 08    	lea    0x811dd4c,%ecx
 80b5bfd:	89 0c 24             	mov    %ecx,(%esp)
 80b5c00:	89 44 24 04          	mov    %eax,0x4(%esp)
 80b5c04:	e8 b7 e4 f9 ff       	call   80540c0 <runtime.writebarrierptr> (File Offset: 0xc0c0)
/home/hanzhao/workspace/go_runtime/main_select.go:9
var ch2 = make(chan bool, 2)
 80b5c09:	eb 9b                	jmp    80b5ba6 <main.init+0xa6> (File Offset: 0x6dba6)
/home/hanzhao/workspace/go_runtime/main_select.go:7

import (
	"fmt"
)

var ch_int = make(chan int, 10)
 80b5c0b:	8d 0d 54 dd 11 08    	lea    0x811dd54,%ecx
 80b5c11:	89 0c 24             	mov    %ecx,(%esp)
 80b5c14:	89 44 24 04          	mov    %eax,0x4(%esp)
 80b5c18:	e8 a3 e4 f9 ff       	call   80540c0 <runtime.writebarrierptr> (File Offset: 0xc0c0)
 80b5c1d:	e9 52 ff ff ff       	jmp    80b5b74 <main.init+0x74> (File Offset: 0x6db74)
 80b5c22:	e8 e9 6a fd ff       	call   808c710 <runtime.morestack_noctxt> (File Offset: 0x44710)
 80b5c27:	e9 d4 fe ff ff       	jmp    80b5b00 <main.init> (File Offset: 0x6db00)


~~~





### newselect 的反汇编

结果为0 ZF置位1. setne 

setne:

Sets the byte in the operand to 1 if the Zero Flag is clear, otherwise sets the operand to 0.

~~~go
08077b70 <runtime.newselect> (File Offset: 0x2fb70):
runtime.newselect():
/usr/lib/golang/src/runtime/select.go:60
		size*unsafe.Sizeof(*hselect{}.lockorder) +
		size*unsafe.Sizeof(*hselect{}.pollorder)
	return round(selsize, sys.Int64Align)
}

 //## stack  实际的参数传递
 0x4 size 
 0
 0x8c
 sel
 ret

// statck
size
selsize
sel
ret 
func newselect(sel *hselect, selsize int64, size int32) {
 8077b70:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
 8077b77:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx
 8077b7d:	3b 61 08             	cmp    0x8(%ecx),%esp
 8077b80:	0f 86 32 01 00 00    	jbe    8077cb8 <runtime.newselect+0x148> (File Offset: 0x2fcb8)
 8077b86:	83 ec 10             	sub    $0x10,%esp
/usr/lib/golang/src/runtime/select.go:61
	if selsize != int64(selectsize(uintptr(size))) {
 8077b89:	8b 44 24 20          	mov    0x20(%esp),%eax
 8077b8d:	89 c1                	mov    %eax,%ecx
  // ############## ecx = size
 8077b8f:	6b c0 1c             	imul   $0x1c,%eax,%eax
  // ###################  eax = size * 28
 8077b92:	8d 54 48 0c          	lea    0xc(%eax,%ecx,2),%edx
   //############# edx = eax + ecx * 2 + 0xc=  (size * 28) + size * 2 + 0xc
 8077b96:	8d 54 4a 03          	lea    0x3(%edx,%ecx,2),%edx
   // ############ edx = edx + 2 * ecx + 0x3 = 
    //  (size * 28) + size * 2 + 0xc + 2 * size + 3
  
        //0xfc  1111 1100
 8077b9a:	83 e2 fc             	and    $0xfffffffc,%edx
 8077b9d:	89 54 24 08          	mov    %edx,0x8(%esp)
 8077ba1:	8b 5c 24 1c          	mov    0x1c(%esp),%ebx
  // ebx 0 为何多传一个0值?????????????????????????
        
 8077ba5:	85 db                	test   %ebx,%ebx
 8077ba7:	87 dd                	xchg   %ebx,%ebp
 8077ba9:	0f 95 c3             	setne  %bl
 // ############# 若ebx 为0， 则zf为1. bl为0
 8077bac:	87 dd                	xchg   %ebx,%ebp
 8077bae:	8b 74 24 18          	mov    0x18(%esp),%esi
 // ##############  esi =selsize
        
 8077bb2:	39 d6                	cmp    %edx,%esi
 // 比较 selsize 和size
 8077bb4:	87 df                	xchg   %ebx,%edi
 8077bb6:	0f 95 c3             	setne  %bl
 // 若 selsize 等于size , 则zf 为1，bl为0,   ebx 始终为旧值。 edi为新值
 8077bb9:	87 df                	xchg   %ebx,%edi
 8077bbb:	09 fd                	or     %edi,%ebp
  // 两个新值 or 操作
        
        
 8077bbd:	89 cf                	mov    %ecx,%edi
        // edi = size
 8077bbf:	d1 e1                	shl    %ecx
 8077bc1:	89 4c 24 0c          	mov    %ecx,0xc(%esp)
        
        
        
 8077bc5:	95                   	xchg   %eax,%ebp
 // ############## eax 为ebp 的值
 8077bc6:	84 c0                	test   %al,%al
 8077bc8:	95                   	xchg   %eax,%ebp
 8077bc9:	75 61                	jne    8077c2c <runtime.newselect+0xbc> (File Offset: 0x2fc2c)
        //##################### 跳转
        
      
/usr/lib/golang/src/runtime/select.go:65
		print("runtime: bad select size ", selsize, ", want ", selectsize(uintptr(size)), "\n")
		throw("bad select size")
	}
	sel.tcase = uint16(size)
 8077bcb:	8b 54 24 14          	mov    0x14(%esp),%edx
 8077bcf:	66 89 3a             	mov    %di,(%edx)
    // sel.tcase = size
    
    
/usr/lib/golang/src/runtime/select.go:66
	sel.ncase = 0
 8077bd2:	66 c7 42 02 00 00    	movw   $0x0,0x2(%edx)
/usr/lib/golang/src/runtime/select.go:67
	sel.lockorder = (*uint16)(add(unsafe.Pointer(&sel.scase), uintptr(size)*unsafe.Sizeof(hselect{}.scase[0])))
 8077bd8:	84 02                	test   %al,(%edx)
 8077bda:	8d 5a 0c             	lea    0xc(%edx),%ebx
 8077bdd:	01 d8                	add    %ebx,%eax
 8077bdf:	8b 1d f0 dd 12 08    	mov    0x812ddf0,%ebx
 8077be5:	8d 6a 08             	lea    0x8(%edx),%ebp
 8077be8:	85 db                	test   %ebx,%ebx
 8077bea:	75 2a                	jne    8077c16 <runtime.newselect+0xa6> (File Offset: 0x2fc16)
 8077bec:	89 42 08             	mov    %eax,0x8(%edx)
/usr/lib/golang/src/runtime/select.go:68
	sel.pollorder = (*uint16)(add(unsafe.Pointer(sel.lockorder), uintptr(size)*unsafe.Sizeof(*hselect{}.lockorder)))
 8077bef:	8b 05 f0 dd 12 08    	mov    0x812ddf0,%eax
 8077bf5:	8b 5a 08             	mov    0x8(%edx),%ebx
 8077bf8:	01 d9                	add    %ebx,%ecx
 8077bfa:	8d 5a 04             	lea    0x4(%edx),%ebx
 8077bfd:	85 c0                	test   %eax,%eax
 8077bff:	75 07                	jne    8077c08 <runtime.newselect+0x98> (File Offset: 0x2fc08)
 8077c01:	89 4a 04             	mov    %ecx,0x4(%edx)
/usr/lib/golang/src/runtime/select.go:73

	if debugSelect {
		print("newselect s=", sel, " size=", size, "\n")
	}
}
 8077c04:	83 c4 10             	add    $0x10,%esp
 8077c07:	c3                   	ret    
/usr/lib/golang/src/runtime/select.go:68
		throw("bad select size")
	}
	sel.tcase = uint16(size)
	sel.ncase = 0
	sel.lockorder = (*uint16)(add(unsafe.Pointer(&sel.scase), uintptr(size)*unsafe.Sizeof(hselect{}.scase[0])))
	sel.pollorder = (*uint16)(add(unsafe.Pointer(sel.lockorder), uintptr(size)*unsafe.Sizeof(*hselect{}.lockorder)))
 8077c08:	89 1c 24             	mov    %ebx,(%esp)
 8077c0b:	89 4c 24 04          	mov    %ecx,0x4(%esp)
 8077c0f:	e8 ac c4 fd ff       	call   80540c0 <runtime.writebarrierptr> (File Offset: 0xc0c0)
/usr/lib/golang/src/runtime/select.go:73

	if debugSelect {
		print("newselect s=", sel, " size=", size, "\n")
	}
}
 8077c14:	eb ee                	jmp    8077c04 <runtime.newselect+0x94> (File Offset: 0x2fc04)
/usr/lib/golang/src/runtime/select.go:67
		print("runtime: bad select size ", selsize, ", want ", selectsize(uintptr(size)), "\n")
		throw("bad select size")
	}
	sel.tcase = uint16(size)
	sel.ncase = 0
	sel.lockorder = (*uint16)(add(unsafe.Pointer(&sel.scase), uintptr(size)*unsafe.Sizeof(hselect{}.scase[0])))
 8077c16:	89 2c 24             	mov    %ebp,(%esp)
 8077c19:	89 44 24 04          	mov    %eax,0x4(%esp)
 8077c1d:	e8 9e c4 fd ff       	call   80540c0 <runtime.writebarrierptr> (File Offset: 0xc0c0)
/usr/lib/golang/src/runtime/select.go:68
	sel.pollorder = (*uint16)(add(unsafe.Pointer(sel.lockorder), uintptr(size)*unsafe.Sizeof(*hselect{}.lockorder)))
 8077c22:	8b 4c 24 0c          	mov    0xc(%esp),%ecx
 8077c26:	8b 54 24 14          	mov    0x14(%esp),%edx
 8077c2a:	eb c3                	jmp    8077bef <runtime.newselect+0x7f> (File Offset: 0x2fbef)
/usr/lib/golang/src/runtime/select.go:62
	return round(selsize, sys.Int64Align)
}




func newselect(sel *hselect, selsize int64, size int32) {
	if selsize != int64(selectsize(uintptr(size))) {
		print("runtime: bad select size ", selsize, ", want ", selectsize(uintptr(size)), "\n")
 8077c2c:	e8 8f 2f ff ff       	call   806abc0 <runtime.printlock> (File Offset: 0x22bc0)
 8077c31:	8d 05 71 7c 0d 08    	lea    0x80d7c71,%eax
 8077c37:	89 04 24             	mov    %eax,(%esp)
 8077c3a:	c7 44 24 04 19 00 00 	movl   $0x19,0x4(%esp)
 8077c41:	00 
 8077c42:	e8 e9 37 ff ff       	call   806b430 <runtime.printstring> (File Offset: 0x23430)
 8077c47:	8b 44 24 18          	mov    0x18(%esp),%eax
 8077c4b:	89 04 24             	mov    %eax,(%esp)
 8077c4e:	8b 44 24 1c          	mov    0x1c(%esp),%eax
 8077c52:	89 44 24 04          	mov    %eax,0x4(%esp)
 8077c56:	e8 15 36 ff ff       	call   806b270 <runtime.printint> (File Offset: 0x23270)
 8077c5b:	8d 05 00 54 0d 08    	lea    0x80d5400,%eax
 8077c61:	89 04 24             	mov    %eax,(%esp)
 8077c64:	c7 44 24 04 07 00 00 	movl   $0x7,0x4(%esp)
 8077c6b:	00 
 8077c6c:	e8 bf 37 ff ff       	call   806b430 <runtime.printstring> (File Offset: 0x23430)
 8077c71:	8b 44 24 08          	mov    0x8(%esp),%eax
 8077c75:	89 04 24             	mov    %eax,(%esp)
 8077c78:	c7 44 24 04 00 00 00 	movl   $0x0,0x4(%esp)
 8077c7f:	00 
 8077c80:	e8 eb 35 ff ff       	call   806b270 <runtime.printint> (File Offset: 0x23270)
 8077c85:	8d 05 b5 50 0d 08    	lea    0x80d50b5,%eax
 8077c8b:	89 04 24             	mov    %eax,(%esp)
 8077c8e:	c7 44 24 04 01 00 00 	movl   $0x1,0x4(%esp)
 8077c95:	00 
 8077c96:	e8 95 37 ff ff       	call   806b430 <runtime.printstring> (File Offset: 0x23430)
 8077c9b:	e8 90 2f ff ff       	call   806ac30 <runtime.printunlock> (File Offset: 0x22c30)
/usr/lib/golang/src/runtime/select.go:63
		throw("bad select size")
 8077ca0:	8d 05 27 62 0d 08    	lea    0x80d6227,%eax
 8077ca6:	89 04 24             	mov    %eax,(%esp)
 8077ca9:	c7 44 24 04 0f 00 00 	movl   $0xf,0x4(%esp)
 8077cb0:	00 
 8077cb1:	e8 4a 26 ff ff       	call   806a300 <runtime.throw> (File Offset: 0x22300)
 8077cb6:	0f 0b                	ud2    
/usr/lib/golang/src/runtime/select.go:60
		size*unsafe.Sizeof(*hselect{}.lockorder) +
		size*unsafe.Sizeof(*hselect{}.pollorder)
	return round(selsize, sys.Int64Align)
}

func newselect(sel *hselect, selsize int64, size int32) {
 8077cb8:	e8 53 4a 01 00       	call   808c710 <runtime.morestack_noctxt> (File Offset: 0x44710)
 8077cbd:	e9 ae fe ff ff       	jmp    8077b70 <runtime.newselect> (File Offset: 0x2fb70)
 8077cc2:	cc                   	int3   
 8077cc3:	cc                   	int3   
 8077cc4:	cc                   	int3   
 8077cc5:	cc                   	int3   
 8077cc6:	cc                   	int3   
 8077cc7:	cc                   	int3   
 8077cc8:	cc                   	int3   
 8077cc9:	cc                   	int3   
 8077cca:	cc                   	int3   
 8077ccb:	cc                   	int3   
 8077ccc:	cc                   	int3   
 8077ccd:	cc                   	int3   
 8077cce:	cc                   	int3   
 8077ccf:	cc                   	int3 
~~~





### newselect 

* 参数size 对应分支数目

~~~go

func selectsize(size uintptr) uintptr {
	selsize := unsafe.Sizeof(hselect{}) +
		(size-1)*unsafe.Sizeof(hselect{}.scase[0]) +
		size*unsafe.Sizeof(*hselect{}.lockorder) +
		size*unsafe.Sizeof(*hselect{}.pollorder)
	return round(selsize, sys.Int64Align)
}

//
func newselect(sel *hselect, selsize int64, size int32) {
	if selsize != int64(selectsize(uintptr(size))) {
		print("runtime: bad select size ", selsize, ", want ", selectsize(uintptr(size)), "\n")
		throw("bad select size")
	}
	sel.tcase = uint16(size)
	sel.ncase = 0
	sel.lockorder = (*uint16)(add(unsafe.Pointer(&sel.scase), uintptr(size)*unsafe.Sizeof(hselect{}.scase[0])))
	sel.pollorder = (*uint16)(add(unsafe.Pointer(sel.lockorder), uintptr(size)*unsafe.Sizeof(*hselect{}.lockorder)))

	if debugSelect {
		print("newselect s=", sel, " size=", size, "\n")
	}
}
~~~





### selectrecv

~~~go
//go:nosplit
func selectrecv(sel *hselect, c *hchan, elem unsafe.Pointer) (selected bool) {
	// nil cases do not compete
	if c != nil {
		selectrecvImpl(sel, c, getcallerpc(unsafe.Pointer(&sel)), elem, nil, uintptr(unsafe.Pointer(&selected))-uintptr(unsafe.Pointer(&sel)))
	}
	return
}



func selectrecvImpl(sel *hselect, c *hchan, pc uintptr, elem unsafe.Pointer, received *bool, so uintptr) {
	i := sel.ncase
	if i >= sel.tcase {
		throw("selectrecv: too many cases")
	}
	sel.ncase = i + 1
	cas := (*scase)(add(unsafe.Pointer(&sel.scase), uintptr(i)*unsafe.Sizeof(sel.scase[0])))
	cas.pc = pc
	cas.c = c
	cas.so = uint16(so)
	cas.kind = caseRecv
	cas.elem = elem
	cas.receivedp = received

	if debugSelect {
		print("selectrecv s=", sel, " pc=", hex(cas.pc), " chan=", cas.c, " so=", cas.so, "\n")
	}
}


~~~



### default 分支

~~~go
//go:nosplit
func selectdefault(sel *hselect) (selected bool) {
	selectdefaultImpl(sel, getcallerpc(unsafe.Pointer(&sel)), uintptr(unsafe.Pointer(&selected))-uintptr(unsafe.Pointer(&sel)))
	return
}

func selectdefaultImpl(sel *hselect, callerpc uintptr, so uintptr) {
	i := sel.ncase
	if i >= sel.tcase {
		throw("selectdefault: too many cases")
	}
	sel.ncase = i + 1
	cas := (*scase)(add(unsafe.Pointer(&sel.scase), uintptr(i)*unsafe.Sizeof(sel.scase[0])))
	cas.pc = callerpc
	cas.c = nil
	cas.so = uint16(so)
	cas.kind = caseDefault

	if debugSelect {
		print("selectdefault s=", sel, " pc=", hex(cas.pc), " so=", cas.so, "\n")
	}
}
~~~



### selectgo





~~~go

// selectgo implements the select statement.
//
// *sel is on the current goroutine's stack (regardless of any
// escaping in selectgo).
//
// selectgo does not return. Instead, it overwrites its return PC and
// returns directly to the triggered select case. Because of this, it
// cannot appear at the top of a split stack.
//
//go:nosplit
func selectgo(sel *hselect) {
	pc, offset := selectgoImpl(sel)
	*(*bool)(add(unsafe.Pointer(&sel), uintptr(offset))) = true
	setcallerpc(unsafe.Pointer(&sel), pc)
}

// selectgoImpl returns scase.pc and scase.so for the select
// case which fired.
func selectgoImpl(sel *hselect) (uintptr, uint16) {
	if debugSelect {
		print("select: sel=", sel, "\n")
	}

	scaseslice := slice{unsafe.Pointer(&sel.scase), int(sel.ncase), int(sel.ncase)}
	scases := *(*[]scase)(unsafe.Pointer(&scaseslice))

	var t0 int64
	if blockprofilerate > 0 {
		t0 = cputicks()
		for i := 0; i < int(sel.ncase); i++ {
			scases[i].releasetime = -1
		}
	}

	// The compiler rewrites selects that statically have
	// only 0 or 1 cases plus default into simpler constructs.
	// The only way we can end up with such small sel.ncase
	// values here is for a larger select in which most channels
	// have been nilled out. The general code handles those
	// cases correctly, and they are rare enough not to bother
	// optimizing (and needing to test).

   	//生成一个随机的pollorder， 一个随机的轮询序列。
    // 为什么生成一个随机的轮询序列???????
    // 难道是为了避免在同一个channel上阻塞。假如是从上到下依次轮询各个channel。第一个channel没有消息， 而其他channel有消息也会在第一个上阻塞。
    
	// generate permuted order
	pollslice := slice{unsafe.Pointer(sel.pollorder), int(sel.ncase), int(sel.ncase)}
	pollorder := *(*[]uint16)(unsafe.Pointer(&pollslice))
	for i := 1; i < int(sel.ncase); i++ {
		j := int(fastrand()) % (i + 1)
		pollorder[i] = pollorder[j]
		pollorder[j] = uint16(i)
	}

	// sort the cases by Hchan address to get the locking order.
	// simple heap sort, to guarantee n log n time and constant stack footprint.
	lockslice := slice{unsafe.Pointer(sel.lockorder), int(sel.ncase), int(sel.ncase)}
	lockorder := *(*[]uint16)(unsafe.Pointer(&lockslice))
	for i := 0; i < int(sel.ncase); i++ {
		j := i
		// Start with the pollorder to permute cases on the same channel.
		c := scases[pollorder[i]].c
		for j > 0 && scases[lockorder[(j-1)/2]].c.sortkey() < c.sortkey() {
			k := (j - 1) / 2
			lockorder[j] = lockorder[k]
			j = k
		}
		lockorder[j] = pollorder[i]
	}
	for i := int(sel.ncase) - 1; i >= 0; i-- {
		o := lockorder[i]
		c := scases[o].c
		lockorder[i] = lockorder[0]
		j := 0
		for {
			k := j*2 + 1
			if k >= i {
				break
			}
			if k+1 < i && scases[lockorder[k]].c.sortkey() < scases[lockorder[k+1]].c.sortkey() {
				k++
			}
			if c.sortkey() < scases[lockorder[k]].c.sortkey() {
				lockorder[j] = lockorder[k]
				j = k
				continue
			}
			break
		}
		lockorder[j] = o
	}
	/*
		for i := 0; i+1 < int(sel.ncase); i++ {
			if scases[lockorder[i]].c.sortkey() > scases[lockorder[i+1]].c.sortkey() {
				print("i=", i, " x=", lockorder[i], " y=", lockorder[i+1], "\n")
				throw("select: broken sort")
			}
		}
	*/

	// lock all the channels involved in the select
	sellock(scases, lockorder)

	var (
		gp     *g
		done   uint32
		sg     *sudog
		c      *hchan
		k      *scase
		sglist *sudog
		sgnext *sudog
		qp     unsafe.Pointer
		nextp  **sudog
	)

loop:
	// pass 1 - look for something already waiting
	var dfl *scase
	var cas *scase
	for i := 0; i < int(sel.ncase); i++ {
		cas = &scases[pollorder[i]]
		c = cas.c

		switch cas.kind {
		case caseRecv:
			sg = c.sendq.dequeue()
			if sg != nil {
				goto recv
			}
			if c.qcount > 0 {
				goto bufrecv
			}
			if c.closed != 0 {
				goto rclose
			}

		case caseSend:
			if raceenabled {
				racereadpc(unsafe.Pointer(c), cas.pc, chansendpc)
			}
			if c.closed != 0 {
				goto sclose
			}
			sg = c.recvq.dequeue()
			if sg != nil {
				goto send
			}
			if c.qcount < c.dataqsiz {
				goto bufsend
			}

		case caseDefault:
			dfl = cas
		}
	}

    
    // 只要上面有任何一个分支的条件是满足的，都不会走到这 
	if dfl != nil {
		selunlock(scases, lockorder)
		cas = dfl
		goto retc
	}

    //只能等待所有的channel，等待条件满足
	// pass 2 - enqueue on all chans
	gp = getg()
	done = 0
	if gp.waiting != nil {
		throw("gp.waiting != nil")
	}
	nextp = &gp.waiting
	for _, casei := range lockorder {
		cas = &scases[casei]
		c = cas.c
		sg := acquireSudog()
		sg.g = gp
		// Note: selectdone is adjusted for stack copies in stack1.go:adjustsudogs
		sg.selectdone = (*uint32)(noescape(unsafe.Pointer(&done)))
		// No stack splits between assigning elem and enqueuing
		// sg on gp.waiting where copystack can find it.
		sg.elem = cas.elem
		sg.releasetime = 0
		if t0 != 0 {
			sg.releasetime = -1
		}
		sg.c = c
		// Construct waiting list in lock order.
		*nextp = sg
		nextp = &sg.waitlink

		switch cas.kind {
		case caseRecv:
			c.recvq.enqueue(sg)

		case caseSend:
			c.sendq.enqueue(sg)
		}
	}

	// wait for someone to wake us up
	gp.param = nil
	gopark(selparkcommit, nil, "select", traceEvGoBlockSelect, 2)

	// While we were asleep, some goroutine came along and completed
	// one of the cases in the select and woke us up (called ready).
	// As part of that process, the goroutine did a cas on done above
	// (aka *sg.selectdone for all queued sg) to win the right to
	// complete the select. Now done = 1.
	//
	// If we copy (grow) our own stack, we will update the
	// selectdone pointers inside the gp.waiting sudog list to point
	// at the new stack. Another goroutine attempting to
	// complete one of our (still linked in) select cases might
	// see the new selectdone pointer (pointing at the new stack)
	// before the new stack has real data; if the new stack has done = 0
	// (before the old values are copied over), the goroutine might
	// do a cas via sg.selectdone and incorrectly believe that it has
	// won the right to complete the select, executing a second
	// communication and attempting to wake us (call ready) again.
	//
	// Then things break.
	//
	// The best break is that the goroutine doing ready sees the
	// _Gcopystack status and throws, as in #17007.
	// A worse break would be for us to continue on, start running real code,
	// block in a semaphore acquisition (sema.go), and have the other
	// goroutine wake us up without having really acquired the semaphore.
	// That would result in the goroutine spuriously running and then
	// queue up another spurious wakeup when the semaphore really is ready.
	// In general the situation can cascade until something notices the
	// problem and causes a crash.
	//
	// A stack shrink does not have this problem, because it locks
	// all the channels that are involved first, blocking out the
	// possibility of a cas on selectdone.
	//
	// A stack growth before gopark above does not have this
	// problem, because we hold those channel locks (released by
	// selparkcommit).
	//
	// A stack growth after sellock below does not have this
	// problem, because again we hold those channel locks.
	//
	// The only problem is a stack growth during sellock.
	// To keep that from happening, run sellock on the system stack.
	//
	// It might be that we could avoid this if copystack copied the
	// stack before calling adjustsudogs. In that case,
	// syncadjustsudogs would need to recopy the tiny part that
	// it copies today, resulting in a little bit of extra copying.
	//
	// An even better fix, not for the week before a release candidate,
	// would be to put space in every sudog and make selectdone
	// point at (say) the space in the first sudog.

	systemstack(func() {
		sellock(scases, lockorder)
	})

	sg = (*sudog)(gp.param)
	gp.param = nil

	// pass 3 - dequeue from unsuccessful chans
	// otherwise they stack up on quiet channels
	// record the successful case, if any.
	// We singly-linked up the SudoGs in lock order.
	cas = nil
	sglist = gp.waiting
	// Clear all elem before unlinking from gp.waiting.
	for sg1 := gp.waiting; sg1 != nil; sg1 = sg1.waitlink {
		sg1.selectdone = nil
		sg1.elem = nil
		sg1.c = nil
	}
	gp.waiting = nil

	for _, casei := range lockorder {
		k = &scases[casei]
		if sglist.releasetime > 0 {
			k.releasetime = sglist.releasetime
		}
		if sg == sglist {
			// sg has already been dequeued by the G that woke us up.
			cas = k
		} else {
			c = k.c
			if k.kind == caseSend {
				c.sendq.dequeueSudoG(sglist)
			} else {
				c.recvq.dequeueSudoG(sglist)
			}
		}
		sgnext = sglist.waitlink
		sglist.waitlink = nil
		releaseSudog(sglist)
		sglist = sgnext
	}

	if cas == nil {
		// We can wake up with gp.param == nil (so cas == nil)
		// when a channel involved in the select has been closed.
		// It is easiest to loop and re-run the operation;
		// we'll see that it's now closed.
		// Maybe some day we can signal the close explicitly,
		// but we'd have to distinguish close-on-reader from close-on-writer.
		// It's easiest not to duplicate the code and just recheck above.
		// We know that something closed, and things never un-close,
		// so we won't block again.
		goto loop
	}

	c = cas.c

	if debugSelect {
		print("wait-return: sel=", sel, " c=", c, " cas=", cas, " kind=", cas.kind, "\n")
	}

	if cas.kind == caseRecv {
		if cas.receivedp != nil {
			*cas.receivedp = true
		}
	}

	if raceenabled {
		if cas.kind == caseRecv && cas.elem != nil {
			raceWriteObjectPC(c.elemtype, cas.elem, cas.pc, chanrecvpc)
		} else if cas.kind == caseSend {
			raceReadObjectPC(c.elemtype, cas.elem, cas.pc, chansendpc)
		}
	}
	if msanenabled {
		if cas.kind == caseRecv && cas.elem != nil {
			msanwrite(cas.elem, c.elemtype.size)
		} else if cas.kind == caseSend {
			msanread(cas.elem, c.elemtype.size)
		}
	}

	selunlock(scases, lockorder)
	goto retc

bufrecv:
	// can receive from buffer
	if raceenabled {
		if cas.elem != nil {
			raceWriteObjectPC(c.elemtype, cas.elem, cas.pc, chanrecvpc)
		}
		raceacquire(chanbuf(c, c.recvx))
		racerelease(chanbuf(c, c.recvx))
	}
	if msanenabled && cas.elem != nil {
		msanwrite(cas.elem, c.elemtype.size)
	}
	if cas.receivedp != nil {
		*cas.receivedp = true
	}
	qp = chanbuf(c, c.recvx)
	if cas.elem != nil {
		typedmemmove(c.elemtype, cas.elem, qp)
	}
	typedmemclr(c.elemtype, qp)
	c.recvx++
	if c.recvx == c.dataqsiz {
		c.recvx = 0
	}
	c.qcount--
	selunlock(scases, lockorder)
	goto retc

bufsend:
	// can send to buffer
	if raceenabled {
		raceacquire(chanbuf(c, c.sendx))
		racerelease(chanbuf(c, c.sendx))
		raceReadObjectPC(c.elemtype, cas.elem, cas.pc, chansendpc)
	}
	if msanenabled {
		msanread(cas.elem, c.elemtype.size)
	}
	typedmemmove(c.elemtype, chanbuf(c, c.sendx), cas.elem)
	c.sendx++
	if c.sendx == c.dataqsiz {
		c.sendx = 0
	}
	c.qcount++
	selunlock(scases, lockorder)
	goto retc

recv:
	// can receive from sleeping sender (sg)
	recv(c, sg, cas.elem, func() { selunlock(scases, lockorder) })
	if debugSelect {
		print("syncrecv: sel=", sel, " c=", c, "\n")
	}
	if cas.receivedp != nil {
		*cas.receivedp = true
	}
	goto retc

rclose:
	// read at end of closed channel
	selunlock(scases, lockorder)
	if cas.receivedp != nil {
		*cas.receivedp = false
	}
	if cas.elem != nil {
		typedmemclr(c.elemtype, cas.elem)
	}
	if raceenabled {
		raceacquire(unsafe.Pointer(c))
	}
	goto retc

send:
	// can send to a sleeping receiver (sg)
	if raceenabled {
		raceReadObjectPC(c.elemtype, cas.elem, cas.pc, chansendpc)
	}
	if msanenabled {
		msanread(cas.elem, c.elemtype.size)
	}
	send(c, sg, cas.elem, func() { selunlock(scases, lockorder) })
	if debugSelect {
		print("syncsend: sel=", sel, " c=", c, "\n")
	}
	goto retc

retc:
	if cas.releasetime > 0 {
		blockevent(cas.releasetime-t0, 2)
	}
	return cas.pc, cas.so

sclose:
	// send on closed channel
	selunlock(scases, lockorder)
	panic(plainError("send on closed channel"))
}
~~~

