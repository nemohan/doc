# go Runtime 分析（1） 起点



使用的命令：
objdump -dS main_goroutine > main_objdump

GOARCH=386 go build -gcflags "-E" -o main_goroutine main.go

objdump -DgSlF main_goroutine > main_goroutine_objdump

OARCH=386 go build -gccgoflags "-gstabs" -o main_goroutine main.go

###  为什么要分析go runtime

1 理解协程的实现及调度机制

2 理解go的垃圾回收机制



### runtime的一些约定

栈自高地址开始，向低地址方向拓展。



go运行时的栈帧结构如下：

~~~
______   高地址
|参数1 
|_____
|参数2
|____
|返回地址
|_____  低地址

参数入栈方向从右到左
~~~



### 如何确定go程序的入口点

~~~
[hanzhao@localhost internal]$ objdump -M i386 -f test

test:     file format elf32-i386
architecture: i386, flags 0x00000112:
EXEC_P, HAS_SYMS, D_PAGED
start address 0x080887b0
~~~





下面代码相对简单，就是调用位于80887d0处的main函数，main函数定义在。0x8(%esp)的值是参数么

若参数，是argc还是argv

~~~asm

版本 go 1.8.3  rt0_linux_386.s

TEXT _rt0_386_linux(SB),NOSPLIT,$8
 80887b0:	83 ec 08             	sub    $0x8,%esp
/usr/local/lib/go/src/runtime/rt0_linux_386.s:8
	MOVL	8(SP), AX
 80887b3:	8b 44 24 08          	mov    0x8(%esp),%eax   //argc
/usr/local/lib/go/src/runtime/rt0_linux_386.s:9
	LEAL	12(SP), BX
 80887b7:	8d 5c 24 0c          	lea    0xc(%esp),%ebx   //argv
/usr/local/lib/go/src/runtime/rt0_linux_386.s:10
	MOVL	AX, 0(SP)
 80887bb:	89 04 24             	mov    %eax,(%esp)
/usr/local/lib/go/src/runtime/rt0_linux_386.s:11
	MOVL	BX, 4(SP)
 80887be:	89 5c 24 04          	mov    %ebx,0x4(%esp)
/usr/local/lib/go/src/runtime/rt0_linux_386.s:12
	CALL	main(SB)
 80887c2:	e8 09 00 00 00       	call   80887d0 <main>   
/usr/local/lib/go/src/runtime/rt0_linux_386.s:13

call 80887d0 <main> 调用 TEXT main(SB),NOSPLIT,$0 rt0_linux_386.s line_75

// ###################翻译成C语言
void start(int argc, char* argv[]){
    main(argc, argv)
}

~~~





main函数的定义，main函数只有一条语句即调用下面的rutime.rt0_go

~~~
//main 函数定义在rt0_linux_386.s
TEXT main(SB),NOSPLIT,$0
	JMP	runtime·rt0_go(SB)

TEXT main(SB),NOSPLIT,$0
 144156     JMP runtime路rt0_go(SB)
 144157  80887d0:   e9 9b d7 ff ff          jmp    8085f70 <runtime.rt0_go>
 144158  80887d5:   cc                      int3
 144159  80887d6:   cc                      int3

~~~





### g的结构体

g 的结构体声明在runtime/runtime2.go

~~~go
// Stack describes a Go execution stack.
// The bounds of the stack are exactly [lo, hi),
// with no implicit data structures on either side.
type stack struct {
	lo uintptr
	hi uintptr
}

// stkbar records the state of a G's stack barrier.
type stkbar struct {
	savedLRPtr uintptr // location overwritten by stack barrier PC
	savedLRVal uintptr // value overwritten at savedLRPtr
}

type g struct {
	// Stack parameters.
	// stack describes the actual stack memory: [stack.lo, stack.hi).
	// stackguard0 is the stack pointer compared in the Go stack growth prologue.
	// It is stack.lo+StackGuard normally, but can be StackPreempt to trigger a preemption.
	// stackguard1 is the stack pointer compared in the C stack growth prologue.
	// It is stack.lo+StackGuard on g0 and gsignal stacks.
	// It is ~0 on other goroutine stacks, to trigger a call to morestackc (and crash).
	stack       stack   // offset known to runtime/cgo
	stackguard0 uintptr // offset known to liblink
	stackguard1 uintptr // offset known to liblink

	_panic         *_panic // innermost panic - offset known to liblink
	_defer         *_defer // innermost defer
	m              *m      // current m; offset known to arm liblink
	stackAlloc     uintptr // stack allocation is [stack.lo,stack.lo+stackAlloc)
	sched          gobuf
	syscallsp      uintptr        // if status==Gsyscall, syscallsp = sched.sp to use during gc
	syscallpc      uintptr        // if status==Gsyscall, syscallpc = sched.pc to use during gc
	stkbar         []stkbar       // stack barriers, from low to high (see top of mstkbar.go)
	stkbarPos      uintptr        // index of lowest stack barrier not hit
	stktopsp       uintptr        // expected sp at top of stack, to check in traceback
	param          unsafe.Pointer // passed parameter on wakeup
	atomicstatus   uint32
	stackLock      uint32 // sigprof/scang lock; TODO: fold in to atomicstatus
	goid           int64
	waitsince      int64  // approx time when the g become blocked
	waitreason     string // if status==Gwaiting
	schedlink      guintptr
	preempt        bool     // preemption signal, duplicates stackguard0 = stackpreempt
	paniconfault   bool     // panic (instead of crash) on unexpected fault address
	preemptscan    bool     // preempted g does scan for gc
	gcscandone     bool     // g has scanned stack; protected by _Gscan bit in status
	gcscanvalid    bool     // false at start of gc cycle, true if G has not run since last scan; transition from true to false by calling queueRescan and false to true by calling dequeueRescan
	throwsplit     bool     // must not split stack
	raceignore     int8     // ignore race detection events
	sysblocktraced bool     // StartTrace has emitted EvGoInSyscall about this goroutine
	sysexitticks   int64    // cputicks when syscall has returned (for tracing)
	traceseq       uint64   // trace event sequencer
	tracelastp     puintptr // last P emitted an event for this goroutine
	lockedm        *m
	sig            uint32
	writebuf       []byte
	sigcode0       uintptr
	sigcode1       uintptr
	sigpc          uintptr
	gopc           uintptr // pc of go statement that created this goroutine
	startpc        uintptr // pc of goroutine function
	racectx        uintptr
	waiting        *sudog    // sudog structures this g is waiting on (that have a valid elem ptr); in lock order
	cgoCtxt        []uintptr // cgo traceback context

	// Per-G GC state

	// gcRescan is this G's index in work.rescan.list. If this is
	// -1, this G is not on the rescan list.
	//
	// If gcphase != _GCoff and this G is visible to the garbage
	// collector, writes to this are protected by work.rescan.lock.
	gcRescan int32

	// gcAssistBytes is this G's GC assist credit in terms of
	// bytes allocated. If this is positive, then the G has credit
	// to allocate gcAssistBytes bytes without assisting. If this
	// is negative, then the G must correct this by performing
	// scan work. We track this in bytes to make it fast to update
	// and check for debt in the malloc hot path. The assist ratio
	// determines how this corresponds to scan work debt.
	gcAssistBytes int64
}
~~~



#### runtim.rt0_go 

此函数定义在runtime/asm_386.s 是一个比较大的函数，我们分段来看看rt0_go都做了哪些事情

下面这段代码主要初始化g0，设置g0使用的大约64KB的栈空间

~~~assembly

函数  int main(int argc, char *argv[])

08085f70 <runtime.rt0_go>:
runtime.rt0_go():
/usr/local/lib/go/src/runtime/asm_386.s:12
#include "funcdata.h"
#include "textflag.h"


TEXT runtime·rt0_go(SB),NOSPLIT,$0
	// copy arguments forward on an even stack
	MOVL	argc+0(FP), AX
 8085f70:	8b 44 24 04          	mov    0x4(%esp),%eax   // eax=argc
/usr/local/lib/go/src/runtime/asm_386.s:13
	MOVL	argv+4(FP), BX
 8085f74:	8b 5c 24 08          	mov    0x8(%esp),%ebx   //ebx = argv
/usr/local/lib/go/src/runtime/asm_386.s:14
	SUBL	$128, SP		// plenty of scratch
 8085f78:	81 ec 80 00 00 00    	sub    $0x80,%esp
/usr/local/lib/go/src/runtime/asm_386.s:15
	ANDL	$~15, SP
 8085f7e:	83 e4 f0             	and    $0xfffffff0,%esp
/usr/local/lib/go/src/runtime/asm_386.s:16
	MOVL	AX, 120(SP)		// save argc, argv away
 8085f81:	89 44 24 78          	mov    %eax,0x78(%esp)	//保存argc, 到局部变量
/usr/local/lib/go/src/runtime/asm_386.s:17
	MOVL	BX, 124(SP)
 8085f85:	89 5c 24 7c          	mov    %ebx,0x7c(%esp)
/usr/local/lib/go/src/runtime/asm_386.s:21


//#########  全局变量 runtime.g0的地址 0x80c92e0 此变量位于 proc.go 
	// set default stack bounds.
	// _cgo_init may update stackguard.
	MOVL	$runtime·g0(SB), BP
 8085f89:	bd e0 92 0c 08       	mov    $0x80c92e0,%ebp   
 
 
 
/usr/local/lib/go/src/runtime/asm_386.s:22
	LEAL	(-64*1024+104)(SP), BX
 8085f8e:	8d 9c 24 68 00 ff ff 	lea    -0xff98(%esp),%ebx  //保留大约64k空间的底部地址
 ==============
 byte array[64 * 1024 -104]
 end = &(array[64* 1024 -104])
 g0.stackguard0 = end
 g0.stackgurad1 = end
 g0.stack.lo = end
 g0.stack.hi = esp
 ==================
 
/usr/local/lib/go/src/runtime/asm_386.s:23
	MOVL	BX, g_stackguard0(BP)
 8085f95:	89 5d 08             	mov    %ebx,0x8(%ebp)   //g0.stackguard0 = end
/usr/local/lib/go/src/runtime/asm_386.s:24
	MOVL	BX, g_stackguard1(BP)
 8085f98:	89 5d 0c             	mov    %ebx,0xc(%ebp)
/usr/local/lib/go/src/runtime/asm_386.s:25
	MOVL	BX, (g_stack+stack_lo)(BP)
 8085f9b:	89 5d 00             	mov    %ebx,0x0(%ebp)
/usr/local/lib/go/src/runtime/asm_386.s:26
	MOVL	SP, (g_stack+stack_hi)(BP)
 8085f9e:	89 65 04             	mov    %esp,0x4(%ebp)



~~~



​	获取cpu的信息,先确定cpu是否支持CPUID指令，确定方法见我的汇编语言中提到的。

* 确定CPU是否支持CPUID
* 不支持则程序退出
* 

~~~asm
/***********************************
确定当前的cpu是否支持cpuid指令，若能设置或清除EFLAGS寄存器的第21位则代表支持CPUID指令。下面就是通过设置第21位是否生效来检查。
我原本以为test是目的操作数减去源操作数再设置ZF标志。其实是目标操作数AND源操作数，根据结果设置ZF、PF、SF
xorl $0x200000, (%esp)指令会设置或清除第21位
**********************************************/
/usr/local/lib/go/src/runtime/asm_386.s:33
	// find out information about the processor we're on
#ifdef GOOS_nacl // NaCl doesn't like PUSHFL/POPFL
	JMP 	has_cpuid
#else
	//保存EFLAGS的旧值，稍后恢复
	// first see if CPUID instruction is supported.
	PUSHFL
 8085fa1:	9c                   	pushf  
 
/usr/local/lib/go/src/runtime/asm_386.s:34
	PUSHFL
 8085fa2:	9c                   	pushf  
/usr/local/lib/go/src/runtime/asm_386.s:35
	XORL	$(1<<21), 0(SP) // flip ID bit
 8085fa3:	81 34 24 00 00 20 00 	xorl   $0x200000,(%esp)
/usr/local/lib/go/src/runtime/asm_386.s:36
	POPFL
 8085faa:	9d                   	popf   
/usr/local/lib/go/src/runtime/asm_386.s:37
	PUSHFL
 8085fab:	9c                   	pushf  
/usr/local/lib/go/src/runtime/asm_386.s:38
	POPL	AX
 8085fac:	58                   	pop    %eax
/usr/local/lib/go/src/runtime/asm_386.s:39
	XORL	0(SP), AX
 8085fad:	33 04 24             	xor    (%esp),%eax
/usr/local/lib/go/src/runtime/asm_386.s:40
	POPFL	// restore EFLAGS
 8085fb0:	9d                   	popf   
 
 //按我的推算，应该是相等才表明支持cpuid
 //对test指令理解有误
/usr/local/lib/go/src/runtime/asm_386.s:41
	TESTL	$(1<<21), AX
 8085fb1:	a9 00 00 20 00       	test   $0x200000,%eax
 
 //不相等则跳转
/usr/local/lib/go/src/runtime/asm_386.s:42
	JNE 	has_cpuid
 8085fb6:	75 2a                	jne    8085fe2 <runtime.rt0_go+0x72>
/usr/local/lib/go/src/runtime/asm_386.s:46
#endif



/********************************
若不支持cpuid则退出程序
***********************************/
bad_proc: // show that the program requires MMX.
	MOVL	$2, 0(SP)
 8085fb8:	c7 04 24 02 00 00 00 	movl   $0x2,(%esp)
/usr/local/lib/go/src/runtime/asm_386.s:47
	MOVL	$bad_proc_msg<>(SB), 4(SP)
 8085fbf:	c7 44 24 04 20 50 0a 	movl   $0x80a5020,0x4(%esp)
 8085fc6:	08 
/usr/local/lib/go/src/runtime/asm_386.s:48
	MOVL	$0x3d, 8(SP)
 8085fc7:	c7 44 24 08 3d 00 00 	movl   $0x3d,0x8(%esp)
 8085fce:	00 
/usr/local/lib/go/src/runtime/asm_386.s:49
	CALL	runtime·write(SB)
 8085fcf:	e8 7c 28 00 00       	call   8088850 <runtime.write>
/usr/local/lib/go/src/runtime/asm_386.s:50
	MOVL	$1, 0(SP)
 8085fd4:	c7 04 24 01 00 00 00 	movl   $0x1,(%esp)
/usr/local/lib/go/src/runtime/asm_386.s:51
	CALL	runtime·exit(SB)
 8085fdb:	e8 00 28 00 00       	call   80887e0 <runtime.exit>
/usr/local/lib/go/src/runtime/asm_386.s:52
	INT	$3
 8085fe0:	cd 03                	int    $0x3
/usr/local/lib/go/src/runtime/asm_386.s:55


/****************************************
支持CPUID指令
1 检查CPUID支持的最大参数,EAX为0调用CPUID时在EAX中的返回值即是
2
*******************************************/
has_cpuid:
	MOVL	$0, AX
 8085fe2:	31 c0                	xor    %eax,%eax
/usr/local/lib/go/src/runtime/asm_386.s:56
	CPUID
 8085fe4:	0f a2                	cpuid  
/usr/local/lib/go/src/runtime/asm_386.s:57
	MOVL	AX, SI
 8085fe6:	89 c6                	mov    %eax,%esi
/usr/local/lib/go/src/runtime/asm_386.s:58
	CMPL	AX, $0
 8085fe8:	83 f8 00             	cmp    $0x0,%eax
/usr/local/lib/go/src/runtime/asm_386.s:59
	JE	nocpuinfo
 8085feb:	74 50                	je     808603d <runtime.rt0_go+0xcd>
/usr/local/lib/go/src/runtime/asm_386.s:64

	// Figure out how to serialize RDTSC.
	// On Intel processors LFENCE is enough. AMD requires MFENCE.
	// Don't know about the rest, so let's do MFENCE.
	CMPL	BX, $0x756E6547  // "Genu"
 8085fed:	81 fb 47 65 6e 75    	cmp    $0x756e6547,%ebx
/usr/local/lib/go/src/runtime/asm_386.s:65
	JNE	notintel
 8085ff3:	75 17                	jne    808600c <runtime.rt0_go+0x9c>
/usr/local/lib/go/src/runtime/asm_386.s:66
	CMPL	DX, $0x49656E69  // "ineI"
 8085ff5:	81 fa 69 6e 65 49    	cmp    $0x49656e69,%edx
/usr/local/lib/go/src/runtime/asm_386.s:67
	JNE	notintel
 8085ffb:	75 0f                	jne    808600c <runtime.rt0_go+0x9c>
/usr/local/lib/go/src/runtime/asm_386.s:68
	CMPL	CX, $0x6C65746E  // "ntel"
 8085ffd:	81 f9 6e 74 65 6c    	cmp    $0x6c65746e,%ecx
/usr/local/lib/go/src/runtime/asm_386.s:69
	JNE	notintel
 8086003:	75 07                	jne    808600c <runtime.rt0_go+0x9c>
/usr/local/lib/go/src/runtime/asm_386.s:70
	MOVB	$1, runtime·lfenceBeforeRdtsc(SB)
 8086005:	c6 05 4d 8d 0d 08 01 	movb   $0x1,0x80d8d4d
/usr/local/lib/go/src/runtime/asm_386.s:74
notintel:

	// Load EAX=1 cpuid flags
	MOVL	$1, AX
 808600c:	b8 01 00 00 00       	mov    $0x1,%eax
/usr/local/lib/go/src/runtime/asm_386.s:75
	CPUID
 8086011:	0f a2                	cpuid  
/usr/local/lib/go/src/runtime/asm_386.s:76
	MOVL	CX, AX // Move to global variable clobbers CX when generating PIC
 8086013:	89 c8                	mov    %ecx,%eax
/usr/local/lib/go/src/runtime/asm_386.s:77
	MOVL	AX, runtime·cpuid_ecx(SB)
 8086015:	89 05 78 8d 0d 08    	mov    %eax,0x80d8d78
/usr/local/lib/go/src/runtime/asm_386.s:78
	MOVL	DX, runtime·cpuid_edx(SB)
 808601b:	89 15 7c 8d 0d 08    	mov    %edx,0x80d8d7c
/usr/local/lib/go/src/runtime/asm_386.s:81

	// Check for MMX support
	TESTL	$(1<<23), DX	// MMX
 8086021:	f7 c2 00 00 80 00    	test   $0x800000,%edx
/usr/local/lib/go/src/runtime/asm_386.s:82
	JZ 	bad_proc
 8086027:	74 8f                	je     8085fb8 <runtime.rt0_go+0x48>
/usr/local/lib/go/src/runtime/asm_386.s:85

	// Load EAX=7/ECX=0 cpuid flags
	CMPL	SI, $7
 8086029:	83 fe 07             	cmp    $0x7,%esi
/usr/local/lib/go/src/runtime/asm_386.s:86
	JLT	nocpuinfo
 808602c:	7c 0f                	jl     808603d <runtime.rt0_go+0xcd>
/usr/local/lib/go/src/runtime/asm_386.s:87
	MOVL	$7, AX
 808602e:	b8 07 00 00 00       	mov    $0x7,%eax
/usr/local/lib/go/src/runtime/asm_386.s:88
	MOVL	$0, CX
 8086033:	31 c9                	xor    %ecx,%ecx
/usr/local/lib/go/src/runtime/asm_386.s:89
	CPUID
 8086035:	0f a2                	cpuid  
/usr/local/lib/go/src/runtime/asm_386.s:90
	MOVL	BX, runtime·cpuid_ebx7(SB)
 8086037:	89 1d 74 8d 0d 08    	mov    %ebx,0x80d8d74
/usr/local/lib/go/src/runtime/asm_386.s:97
nocpuinfo:	
~~~



~~~assembly
/****************************
_cgo_init 定义在runtim/cgo.go 文件中
如果_cgo_init的值为0，则调用ldt0setup
***************************************/
===========================
	// if there is an _cgo_init, call it to let it
	// initialize and to set up GS.  if not,
	// we set up GS ourselves.
	MOVL	_cgo_init(SB), AX
 808603d:	8b 05 a0 8f 0c 08    	mov    0x80c8fa0,%eax  //看_cgo_init的值
/usr/local/lib/go/src/runtime/asm_386.s:98
	TESTL	AX, AX
 8086043:	85 c0                	test   %eax,%eax  
/usr/local/lib/go/src/runtime/asm_386.s:99
	JZ	needtls
 8086045:	74 7d                	je     80860c4 <runtime.rt0_go+0x154> ====
 
 /******************************
 
 
 ****************************************/
/usr/local/lib/go/src/runtime/asm_386.s:100
	MOVL	$setg_gcc<>(SB), BX
 8086047:	bb f0 76 08 08       	mov    $0x80876f0,%ebx
/usr/local/lib/go/src/runtime/asm_386.s:101
	MOVL	BX, 4(SP)
 808604c:	89 5c 24 04          	mov    %ebx,0x4(%esp)
/usr/local/lib/go/src/runtime/asm_386.s:102
	MOVL	BP, 0(SP)
 8086050:	89 2c 24             	mov    %ebp,(%esp)
/usr/local/lib/go/src/runtime/asm_386.s:103
	CALL	AX
 8086053:	ff d0                	call   *%eax
/usr/local/lib/go/src/runtime/asm_386.s:106

	// update stackguard after _cgo_init
	MOVL	$runtime·g0(SB), CX
 8086055:	b9 e0 92 0c 08       	mov    $0x80c92e0,%ecx
/usr/local/lib/go/src/runtime/asm_386.s:107
	MOVL	(g_stack+stack_lo)(CX), AX
 808605a:	8b 01                	mov    (%ecx),%eax
/usr/local/lib/go/src/runtime/asm_386.s:108
	ADDL	$const__StackGuard, AX
 808605c:	05 70 03 00 00       	add    $0x370,%eax
/usr/local/lib/go/src/runtime/asm_386.s:109
	MOVL	AX, g_stackguard0(CX)
 8086061:	89 41 08             	mov    %eax,0x8(%ecx)
/usr/local/lib/go/src/runtime/asm_386.s:110
	MOVL	AX, g_stackguard1(CX)
 8086064:	89 41 0c             	mov    %eax,0xc(%ecx)
/usr/local/lib/go/src/runtime/asm_386.s:134
	CMPL	AX, $0x123
	JEQ	ok
	MOVL	AX, 0	// abort
	
	
	
	
	{
        m0.tls[0] = &g0
        m0.g0 = &g0
        g0->m = &m0
        
	}
ok:
	// set up m and g "registers"
	get_tls(BX)
 8086067:	65 8b 1d 00 00 00 00 	mov    %gs:0x0,%ebx
/usr/local/lib/go/src/runtime/asm_386.s:135
	LEAL	runtime·g0(SB), DX
 808606e:	8d 15 e0 92 0c 08    	lea    0x80c92e0,%edx      
 //################# g0 地址 80c92e0 m0地址:   0x80c9520
 //############## edx = g0
 
 
/usr/local/lib/go/src/runtime/asm_386.s:136
	MOVL	DX, g(BX)
 8086074:	89 93 fc ff ff ff    	mov    %edx,-0x4(%ebx) 
 //################ m.tls[0] = &g0
 
/usr/local/lib/go/src/runtime/asm_386.s:137
	LEAL	runtime·m0(SB), AX
 808607a:	8d 05 20 95 0c 08    	lea    0x80c9520,%eax
/usr/local/lib/go/src/runtime/asm_386.s:140
	MOVL	DX, m_g0(AX)
 8086080:	89 10                	mov    %edx,(%eax)
 	//#################### save m->g0 = g0
 	
 	
/usr/local/lib/go/src/runtime/asm_386.s:142
	// save g0->m = m0
	MOVL	AX, g_m(DX)
 8086082:	89 42 18             	mov    %eax,0x18(%edx)
/usr/local/lib/go/src/runtime/asm_386.s:144

	CALL	runtime·emptyfunc(SB)	// fault if stack check is wrong
 8086085:	e8 36 17 00 00       	call   80877c0 <runtime.emptyfunc>
 // 检查栈空间是否满了
 // ##############见第二篇
 
 
/usr/local/lib/go/src/runtime/asm_386.s:147

	// convention is D is always cleared
	CLD
 808608a:	fc                   	cld    
/usr/local/lib/go/src/runtime/asm_386.s:149

	CALL	runtime·check(SB)
 808608b:	e8 50 db fe ff       	call   8073be0 <runtime.check>
/usr/local/lib/go/src/runtime/asm_386.s:152

	// saved argc, argv
	MOVL	120(SP), AX
 8086090:	8b 44 24 78          	mov    0x78(%esp),%eax
/usr/local/lib/go/src/runtime/asm_386.s:153
	MOVL	AX, 0(SP)
 8086094:	89 04 24             	mov    %eax,(%esp)
/usr/local/lib/go/src/runtime/asm_386.s:154
	MOVL	124(SP), AX
 8086097:	8b 44 24 7c          	mov    0x7c(%esp),%eax
/usr/local/lib/go/src/runtime/asm_386.s:155
	MOVL	AX, 4(SP)
 808609b:	89 44 24 04          	mov    %eax,0x4(%esp)
/usr/local/lib/go/src/runtime/asm_386.s:156
	CALL	runtime·args(SB)
 808609f:	e8 bc d4 fe ff       	call   8073560 <runtime.args>
 //######### runtime1.go args 函数
 
/usr/local/lib/go/src/runtime/asm_386.s:157
	CALL	runtime·osinit(SB)
 80860a4:	e8 27 fe fd ff       	call   8065ed0 <runtime.osinit>
 // ########### 见 第6篇
 
/usr/local/lib/go/src/runtime/asm_386.s:158
	CALL	runtime·schedinit(SB)
 80860a9:	e8 72 3d fe ff       	call   8069e20 <runtime.schedinit>
 // ######## 见第7篇
 
/usr/local/lib/go/src/runtime/asm_386.s:161
	// create a new goroutine to start program
	PUSHL	$runtime·mainPC(SB)	// entry
 80860ae:	68 f8 4c 0a 08       	push   $0x80a4cf8
 // ########## 变量 runtime.mainPC 的值是 runtime.main 的地址 08068c90
 // ######## runtime.main 位于proc.go 106 行
 
/usr/local/lib/go/src/runtime/asm_386.s:162
	PUSHL	$0	// arg size
 80860b3:	6a 00                	push   $0x0
/usr/local/lib/go/src/runtime/asm_386.s:163
	CALL	runtime·newproc(SB)
 80860b5:	e8 76 91 fe ff       	call   806f230 <runtime.newproc>
 // ########## 看第8篇
 
/usr/local/lib/go/src/runtime/asm_386.s:164
	POPL	AX
 80860ba:	58                   	pop    %eax
/usr/local/lib/go/src/runtime/asm_386.s:165
	POPL	AX
 80860bb:	58                   	pop    %eax
/usr/local/lib/go/src/runtime/asm_386.s:168

	// start this M
	CALL	runtime·mstart(SB)
 80860bc:	e8 5f 55 fe ff       	call   806b620 <runtime.mstart>
 //################# runtime.mstart的分析见第9篇
 
/usr/local/lib/go/src/runtime/asm_386.s:170

	INT $3
 80860c1:	cd 03                	int    $0x3
/usr/local/lib/go/src/runtime/asm_386.s:171
	RET 
 80860c3:	c3                   	ret
~~~





#### runtime.ldt0setup 定义在runtime/asm_386.s中

调用定义在runtime/asm_386.s中的runtime.ldt0setup, ldt0setup会设置gs寄存器

因为将基地址设置为m0.tls[1], 所以通过检查m0.tls[1]的值和从gs:0x0取得的值比较，相同则说明设置成功



~~~asm
//设置ldt
 =============  80860c4
 
 void _ldt0setup(){
     
 }
 
/usr/local/lib/go/src/runtime/asm_386.s:123
	CALL	runtime·ldt0setup(SB)
 80860c4:	e8 c7 16 00 00       	call   8087790 <runtime.ldt0setup>
/usr/local/lib/go/src/runtime/asm_386.s:126
	get_tls(BX)
 80860c9:	65 8b 1d 00 00 00 00 	mov    %gs:0x0,%ebx
 
 // ########应该是检查之前的selldt是否生效了
/usr/local/lib/go/src/runtime/asm_386.s:127
	MOVL	$0x123, g(BX)
 80860d0:	c7 83 fc ff ff ff 23 	movl   $0x123,-0x4(%ebx)
 80860d7:	01 00 00 
/usr/local/lib/go/src/runtime/asm_386.s:128
	MOVL	runtime·m0+m_tls(SB), AX
 80860da:	8b 05 58 95 0c 08    	mov    0x80c9558,%eax
/usr/local/lib/go/src/runtime/asm_386.s:129
	CMPL	AX, $0x123
 80860e0:	3d 23 01 00 00       	cmp    $0x123,%eax
/usr/local/lib/go/src/runtime/asm_386.s:130
	JEQ	ok
 80860e5:	74 80                	je     8086067 <runtime.rt0_go+0xf7>
 
 //########## 有效的地址，跳到上面的rt0_go
 
/usr/local/lib/go/src/runtime/asm_386.s:131
	MOVL	AX, 0	// abort
 80860e7:	89 05 00 00 00 00    	mov    %eax,0x0
/usr/local/lib/go/src/runtime/asm_386.s:134
	get_tls(BX)
 80860ed:	e9 75 ff ff ff       	jmp    8086067 <runtime.rt0_go+0xf7>
 80860f2:	cc                   	int3   
 80860f3:	cc                   	int3   
 80860f4:	cc                   	int3   
 80860f5:	cc                   	int3   
 80860f6:	cc                   	int3   
 80860f7:	cc                   	int3   
 80860f8:	cc                   	int3   
 80860f9:	cc                   	int3   
 80860fa:	cc                   	int3   
 80860fb:	cc                   	int3   
 80860fc:	cc                   	int3   
 80860fd:	cc                   	int3   
 80860fe:	cc                   	int3   
 80860ff:	cc                   	int3   

08086100 <runtime.asminit>:
runtime.asminit():
/usr/local/lib/go/src/runtime/asm_386.s:196
TEXT runtime·asminit(SB),NOSPLIT,$0-0
	// Linux and MinGW start the FPU in extended double precision.
	// Other operating systems use double precision.
	// Change to double precision to match them,
	// and to match other hardware that only has double.
	FLDCW	runtime·controlWord64(SB)
 8086100:	d9 2d 02 80 0c 08    	fldcw  0x80c8002
/usr/local/lib/go/src/runtime/asm_386.s:197
	RET
~~~

#### ldt0setup 定义在runtime/asm_386.s中，ldt0setup的工作:

* 调用setldt(0x7, m0.tls,  0x20)(定义在runtime/sys_linux_386.s)设置m0.tls(m0定义在runtime/proc2.go)

~~~assembly


	
//func =============================  ldt0setup  ==================
void ldt0setup(){
    setldt(0x7, m0.tls, 0x20)
}

08087790 <runtime.ldt0setup>:
runtime.ldt0setup():
/usr/local/lib/go/src/runtime/asm_386.s:854

TEXT runtime·ldt0setup(SB),NOSPLIT,$16-0
 8087790:	83 ec 10             	sub    $0x10,%esp   //保留16字节栈空间
/usr/local/lib/go/src/runtime/asm_386.s:858
	// set up ldt 7 to point at m0.tls
	// ldt 1 would be fine on Linux, but on OS X, 7 is as low as we can go.
	// the entry number is just a hint.  setldt will set up GS with what it used.
	MOVL	$7, 0(SP)
 8087793:	c7 04 24 07 00 00 00 	movl   $0x7,(%esp)   //放到栈上
 
 
 //#### runtime.m0 的地址是080c9520  但是从 runtime2.go 的m结构体定义来看，tls地址偏移量为68而不是56  ??????????????????
 即 0x80c9520 + 0x44 = 0x80c9564
/usr/local/lib/go/src/runtime/asm_386.s:859
	LEAL	runtime·m0+m_tls(SB), AX
 808779a:	8d 05 58 95 0c 08    	lea    0x80c9558,%eax
/usr/local/lib/go/src/runtime/asm_386.s:860
	MOVL	AX, 4(SP)
 80877a0:	89 44 24 04          	mov    %eax,0x4(%esp) //入栈
/usr/local/lib/go/src/runtime/asm_386.s:861
	MOVL	$32, 8(SP)	// sizeof(tls array)
 80877a4:	c7 44 24 08 20 00 00 	movl   $0x20,0x8(%esp) //入栈
 80877ab:	00 
/usr/local/lib/go/src/runtime/asm_386.s:862
	CALL	runtime·setldt(SB)
 80877ac:	e8 bf 14 00 00       	call   8088c70 
<runtime.setldt>
/usr/local/lib/go/src/runtime/asm_386.s:863
	RET
	
~~~

#### setldt(runtime/sys_linux_386.s),setldt的任务是调用系统调用set_thread_area设置GDT的tls入口

第一个和第三个参数未使用

系统调用 set_thread_area

~~~
These calls provide architecture-specific support for a thread-local
       storage implementation.  At the moment, set_thread_area() is
       available on m68k, MIPS, and x86 (both 32-bit and 64-bit variants);
       get_thread_area() is available on m68k and x86.

       On m68k and MIPS, set_thread_area() allows storing an arbitrary
       pointer (provided in the tp argument on m68k and in the addr argument
       on MIPS) in the kernel data structure associated with the calling
       thread; this pointer can later be retrieved using get_thread_area()
       (see also NOTES for information regarding obtaining the thread
       pointer on MIPS).

       On x86, Linux dedicates three global descriptor table (GDT) entries
       for thread-local storage.  For more information about the GDT, see
       the Intel Software Developer's Manual or the AMD Architecture
       Programming Manual.

       Both of these system calls take an argument that is a pointer to a
       structure of the following type:

           struct user_desc {
               unsigned int  entry_number;
               unsigned long base_addr;
               unsigned int  limit;
               unsigned int  seg_32bit:1;
               unsigned int  contents:2;
               unsigned int  read_exec_only:1;
               unsigned int  limit_in_pages:1;
               unsigned int  seg_not_present:1;
               unsigned int  useable:1;
           #ifdef __x86_64__
               unsigned int  lm:1;
           #endif
           };

       get_thread_area() reads the GDT entry indicated by u_info->entry_num‐
       ber and fills in the rest of the fields in u_info.

       set_thread_area() sets a TLS entry in the GDT.

       The TLS array entry set by set_thread_area() corresponds to the value
       of u_info->entry_number passed in by the user.  If this value is in
       bounds, set_thread_area() writes the TLS descriptor pointed to by
       u_info into the thread's TLS array.

       When set_thread_area() is passed an entry_number of -1, it searches
       for a free TLS entry.  If set_thread_area() finds a free TLS entry,
       the value of u_info->entry_number is set upon return to show which
       entry was changed.

       A user_desc is considered "empty" if read_exec_only and
       seg_not_present are set to 1 and all of the other fields are 0.  If
       an "empty" descriptor is passed to set_thread_area(), the correspond‐
       ing TLS entry will be cleared.  See BUGS for additional details.

       Since Linux 3.19, set_thread_area() cannot be used to write non-
       present segments, 16-bit segments, or code segments, although clear‐
       ing a segment is still acceptable.
RETURN VALUE         top

       On x86, these system calls return 0 on success, and -1 on failure,
       with errno set appropriately.

       On MIPS and m68k, set_thread_area() always returns 0.  On m68k,
       get_thread_area() returns the thread area pointer value (previously
       set via set_thread_area()).
~~~





~~~assembly

|
|0x20
______   高地址
|m0.tls
|_____
|0x7  entry number
|____
|返回地址
|_____  低地址
	
// func ========================= setldt===========================================

void setldt(int entry, int address, int limit){
    address += 4;
    m0.tls[1] = address; // m0.tls[1] = &(m0.tls[1])
    user_info uinfo ={
        entry_number = tls_entry_number,
        base_addrr = &(m0.tls[1]),
        limit = 0xfffff,
    }
    if (set_thread_area(&uinfo) != -1){
       abort();
    }
    
    tls_entry_number = uinfo.entry_number;
    //计算段寄存器 gs 的值
}

08088c70 <runtime.setldt>:
runtime.setldt():
/usr/local/lib/go/src/runtime/sys_linux_386.s:445
// setldt(int entry, int address, int limit)
// We use set_thread_area, which mucks with the GDT, instead of modify_ldt,
// which would modify the LDT, but is disabled on some kernels.
// The name, setldt, is a misnomer, although we leave this name as it is for
// the compatibility with other platforms.
TEXT runtime·setldt(SB),NOSPLIT,$32
 8088c70:	83 ec 20             	sub    $0x20,%esp
 
/usr/local/lib/go/src/runtime/sys_linux_386.s:446
	MOVL	address+4(FP), DX	// base address
 8088c73:	8b 54 24 28          	mov    0x28(%esp),%edx      //edx = &(m0.tls)
 
/usr/local/lib/go/src/runtime/sys_linux_386.s:470										 edx = edx + 4
	 * the address here and bump the limit to 0xffffffff (no limit)
	 * so that -4(GS) maps to 0(address).
	 * Also, the final 0(GS) (current 4(DX)) has to point
	 * to itself, to mimic ELF.
	 */
	ADDL	$0x4, DX	// address
 8088c77:	83 c2 04             	add    $0x4,%edx
 
/usr/local/lib/go/src/runtime/sys_linux_386.s:471
	MOVL	DX, 0(DX)
 8088c7a:	89 12                	mov    %edx,(%edx) // m0.tls[1]= &(m0.tls[1])
/usr/local/lib/go/src/runtime/sys_linux_386.s:475
#endif

	//##############0x80c8020 是全局变量 tls_entry_number的地址
	// get entry number
	MOVL	runtime·tls_entry_number(SB), CX
 8088c7c:	8b 0d 20 80 0c 08    	mov    0x80c8020,%ecx   #tls_entry_number 的值是-1
/usr/local/lib/go/src/runtime/sys_linux_386.s:478




/***********************************
准备系统调用set_thread_area的参数
在栈上分配user_desc并初始化
user_desc的定义见set_thread_area
tls_entry_number定义在runtime/sys_linux_386.s,默认值为-1
user_desc.entry_number = tls_entry_number 
user_desc.base_addr = &m0.tls[1]
user_desc.


******************************/
	// set up user_desc  下面初始化user_desc 然后调用set_thread_area
	LEAL	16(SP), AX	// struct user_desc
 8088c82:	8d 44 24 10          	lea    0x10(%esp),%eax  
 // ############从栈上保留一块空间，有点类似将一个数组指针强转为一个结构体指针user_desc *
 
/usr/local/lib/go/src/runtime/sys_linux_386.s:479
	MOVL	CX, 0(AX)	// unsigned int entry_number
 8088c86:	89 08                	mov    %ecx,(%eax) 
 // user_desc->entry_number=-1
 
/usr/local/lib/go/src/runtime/sys_linux_386.s:480
	MOVL	DX, 4(AX)	// unsigned long base_addr
 8088c88:	89 50 04             	mov    %edx,0x4(%eax) 
 
//########### user_desc->base_addr= &(m0.tls[1])
 
/usr/local/lib/go/src/runtime/sys_linux_386.s:481
	MOVL	$0xfffff, 8(AX)	// unsigned int limit
 8088c8b:	c7 40 08 ff ff 0f 00 	movl  $0xfffff,0x8(%eax) 
 
 //############ user_desc->limit=0xfffff  1M大小
 

/usr/local/lib/go/src/runtime/sys_linux_386.s:482
	MOVL	$(SEG_32BIT|LIMIT_IN_PAGES|USEABLE|CONTENTS_DATA), 12(AX)	// flag bits
 8088c92:	c7 40 0c 51 00 00 00 	movl   $0x51,0xc(%eax)
/usr/local/lib/go/src/runtime/sys_linux_386.s:485

/***************************
调用set_thread_area

*******************************************/
	// call set_thread_area
	MOVL	AX, BX	// user_desc
 8088c99:	89 c3                	mov    %eax,%ebx
/usr/local/lib/go/src/runtime/sys_linux_386.s:486
	MOVL	$243, AX	// syscall - set_thread_area
 8088c9b:	b8 f3 00 00 00       	mov    $0xf3,%eax
/usr/local/lib/go/src/runtime/sys_linux_386.s:488
	// We can't call this via 0x10(GS) because this is called from setldt0 to set that up.
	INT     $0x80
 8088ca0:	cd 80                	int    $0x80                
 //########### 系统调用参数传递方式 ebx first param, ecx second param, edx third param
 //###########上面是系统调用 set_thread_area(struct user_desc *u_info)
 
   struct user_desc {
               unsigned int  entry_number;
               unsigned long base_addr;
               unsigned int  limit;
               unsigned int  seg_32bit:1;
               unsigned int  contents:2;
               unsigned int  read_exec_only:1;
               unsigned int  limit_in_pages:1;
               unsigned int  seg_not_present:1;
               unsigned int  useable:1;
           };
 
 
 /*****************************
 若系统调用失败则中断
 若成功获取分配的user_desc.entry_number保存到tls_entry_number
 
 *********************************/
 
/usr/local/lib/go/src/runtime/sys_linux_386.s:491

	// breakpoint on error
	CMPL AX, $0xfffff001
 8088ca2:	3d 01 f0 ff ff       	cmp    $0xfffff001,%eax
/usr/local/lib/go/src/runtime/sys_linux_386.s:492
	JLS 2(PC)
 8088ca7:	76 02                	jbe    8088cab <runtime.setldt+0x3b>  
 //###### 如果eax < $0xfffff001, eax 为-1不跳转， 0跳转
 
/usr/local/lib/go/src/runtime/sys_linux_386.s:493
	INT $3
 8088ca9:	cd 03                	int    $0x3
 
 

 //########## 系统调用成功
/usr/local/lib/go/src/runtime/sys_linux_386.s:496
	// read allocated entry number back out of user_desc  ==========================
	LEAL	16(SP), AX	// get our user_desc back
 8088cab:	8d 44 24 10          	lea    0x10(%esp),%eax
 
 
/usr/local/lib/go/src/runtime/sys_linux_386.s:497
	MOVL	0(AX), AX
 8088caf:	8b 00                	mov    (%eax),%eax
/usr/local/lib/go/src/runtime/sys_linux_386.s:500
// ####### eax= user_desc->entry_number


//##########  store entry number if the kernel allocated it
## ecx 此时的值是 tls_entry_number 全局变量
	CMPL	CX, $-1
 8088cb1:	83 f9 ff             	cmp    $0xffffffff,%ecx
 
/usr/local/lib/go/src/runtime/sys_linux_386.s:501
	JNE	2(PC)
 8088cb4:	75 06                	jne    8088cbc <runtime.setldt+0x4c>
 
/usr/local/lib/go/src/runtime/sys_linux_386.s:502
	MOVL	AX, runtime·tls_entry_number(SB)
 8088cb6:	89 05 20 80 0c 08    	mov    %eax,0x80c8020
 //####### 保存 分配的 entry_number 到 tls_entry_number
 
 
/usr/local/lib/go/src/runtime/sys_linux_386.s:505

	// compute segment selector - (entry*8+3)
	SHLL	$3, AX
 8088cbc:	c1 e0 03             	shl    $0x3,%eax
/usr/local/lib/go/src/runtime/sys_linux_386.s:506
	ADDL	$3, AX
 8088cbf:	83 c0 03             	add    $0x3,%eax
/usr/local/lib/go/src/runtime/sys_linux_386.s:507
	MOVW	AX, GS
 8088cc2:	8e e8                	mov    %eax,%gs
/usr/local/lib/go/src/runtime/sys_linux_386.s:509

	RET
 8088cc4:	83 c4 20             	add    $0x20,%esp
 

~~~

