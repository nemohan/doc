# osinit

#### runtime.osinit 定义在runtime/os_linux.go

* osinit 调用getproccount()获取CPU核心数目并保存在全局变量ncpu(定义在runtime/runtime2.go)中

~~~assembly
//#############第一篇的初始化会调用此函数
func osinit() {
 8065ed0:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
 8065ed7:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx
 8065edd:	3b 61 08             	cmp    0x8(%ecx),%esp
 //######### 检查栈是否满
 
 8065ee0:	76 15                	jbe    8065ef7 <runtime.osinit+0x27>
 8065ee2:	83 ec 04             	sub    $0x4,%esp
/usr/local/lib/go/src/runtime/os_linux.go:269
	ncpu = getproccount()
 8065ee5:	e8 66 fa ff ff       	call   8065950 <runtime.getproccount>
 8065eea:	8b 04 24             	mov    (%esp),%eax
 8065eed:	89 05 d4 8d 0d 08    	mov    %eax,0x80d8dd4
 //############# 0x80d8dd4 是runtime.ncpu的地址 eax是系统的CPU数目
 
/usr/local/lib/go/src/runtime/os_linux.go:270
}
 8065ef3:	83 c4 04             	add    $0x4,%esp
 8065ef6:	c3                   	ret
 
 
/usr/local/lib/go/src/runtime/os_linux.go:268
func osinit() {
 8065ef7:	e8 34 04 02 00       	call   8086330 <runtime.morestack_noctxt>
 8065efc:	eb d2                	jmp    8065ed0 <runtime.osinit>
 8065efe:	cc                   	int3   
 8065eff:	cc                   	int3   
 
~~~

~~~assembly


~~~

##### getproccount (runtime/os_linux.go)

* 

~~~asm
08065950 <runtime.getproccount>:
runtime.getproccount():
/usr/local/lib/go/src/runtime/os_linux.go:83

func getproccount() int32 {
 8065950:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
 8065957:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx
 806595d:	8b 71 08             	mov    0x8(%ecx),%esi
 8065960:	81 fe de fa ff ff    	cmp    $0xfffffade,%esi
 8065966:	0f 84 bc 00 00 00    	je     8065a28 <runtime.getproccount+0xd8>
 806596c:	8d 84 24 70 03 00 00 	lea    0x370(%esp),%eax
 8065973:	29 f0                	sub    %esi,%eax
 8065975:	3d 00 23 00 00       	cmp    $0x2300,%eax
 806597a:	0f 86 a8 00 00 00    	jbe    8065a28 <runtime.getproccount+0xd8>
 8065980:	81 ec 10 20 00 00    	sub    $0x2010,%esp
/usr/local/lib/go/src/runtime/os_linux.go:92
	// See golang.org/issue/11823.
	// The suggested behavior here is to keep trying with ever-larger
	// buffers, but we don't have a dynamic memory allocator at the
	// moment, so that's a bit tricky and seems like overkill.
	const maxCPUs = 64 * 1024
	var buf [maxCPUs / (sys.PtrSize * 8)]uintptr
 8065986:	8d 7c 24 10          	lea    0x10(%esp),%edi
 806598a:	b9 00 08 00 00       	mov    $0x800,%ecx
 806598f:	31 c0                	xor    %eax,%eax
 8065991:	f3 ab                	rep stos %eax,%es:(%edi)
/usr/local/lib/go/src/runtime/os_linux.go:93
	r := sched_getaffinity(0, unsafe.Sizeof(buf), &buf[0])
 8065993:	8d 54 24 10          	lea    0x10(%esp),%edx
 8065997:	89 54 24 08          	mov    %edx,0x8(%esp)
 806599b:	c7 04 24 00 00 00 00 	movl   $0x0,(%esp)
 80659a2:	c7 44 24 04 00 20 00 	movl   $0x2000,0x4(%esp)
 80659a9:	00 
 80659aa:	e8 31 33 02 00       	call   8088ce0 <runtime.sched_getaffinity>
 80659af:	8b 54 24 0c          	mov    0xc(%esp),%edx
/usr/local/lib/go/src/runtime/os_linux.go:94
	if r < 0 {
 80659b3:	85 d2                	test   %edx,%edx
 80659b5:	7c 5f                	jl     8065a16 <runtime.getproccount+0xc6>
/usr/local/lib/go/src/runtime/os_linux.go:98
		return 1
	}
	n := int32(0)
	for _, v := range buf[:r/sys.PtrSize] {
 80659b7:	89 d0                	mov    %edx,%eax
 80659b9:	c1 fa 1f             	sar    $0x1f,%edx
 80659bc:	c1 ea 1e             	shr    $0x1e,%edx
 80659bf:	01 d0                	add    %edx,%eax
 80659c1:	c1 f8 02             	sar    $0x2,%eax
 80659c4:	3d 00 08 00 00       	cmp    $0x800,%eax
 80659c9:	77 44                	ja     8065a0f <runtime.getproccount+0xbf>
/usr/local/lib/go/src/runtime/os_linux.go:93
	r := sched_getaffinity(0, unsafe.Sizeof(buf), &buf[0])
 80659cb:	31 c9                	xor    %ecx,%ecx
 80659cd:	8d 54 24 10          	lea    0x10(%esp),%edx
/usr/local/lib/go/src/runtime/os_linux.go:83
func getproccount() int32 {
 80659d1:	31 db                	xor    %ebx,%ebx
/usr/local/lib/go/src/runtime/os_linux.go:98
	for _, v := range buf[:r/sys.PtrSize] {
 80659d3:	39 c1                	cmp    %eax,%ecx
 80659d5:	7d 1d                	jge    80659f4 <runtime.getproccount+0xa4>
 80659d7:	8b 2a                	mov    (%edx),%ebp
/usr/local/lib/go/src/runtime/os_linux.go:99
		for v != 0 {
 80659d9:	85 ed                	test   %ebp,%ebp
 80659db:	74 0f                	je     80659ec <runtime.getproccount+0x9c>
/usr/local/lib/go/src/runtime/os_linux.go:100
			n += int32(v & 1)
 80659dd:	89 ee                	mov    %ebp,%esi
 80659df:	83 e5 01             	and    $0x1,%ebp
 80659e2:	01 eb                	add    %ebp,%ebx
/usr/local/lib/go/src/runtime/os_linux.go:101
			v >>= 1
 80659e4:	d1 ee                	shr    %esi
/usr/local/lib/go/src/runtime/os_linux.go:99
		for v != 0 {
 80659e6:	89 f5                	mov    %esi,%ebp
 80659e8:	85 ed                	test   %ebp,%ebp
 80659ea:	75 f1                	jne    80659dd <runtime.getproccount+0x8d>
/usr/local/lib/go/src/runtime/os_linux.go:98
	for _, v := range buf[:r/sys.PtrSize] {
 80659ec:	83 c2 04             	add    $0x4,%edx
 80659ef:	41                   	inc    %ecx
 80659f0:	39 c1                	cmp    %eax,%ecx
 80659f2:	7c e3                	jl     80659d7 <runtime.getproccount+0x87>
/usr/local/lib/go/src/runtime/os_linux.go:104
		}
	}
	if n == 0 {
 80659f4:	85 db                	test   %ebx,%ebx
 80659f6:	75 13                	jne    8065a0b <runtime.getproccount+0xbb>
/usr/local/lib/go/src/runtime/os_linux.go:95
		return 1
 80659f8:	b8 01 00 00 00       	mov    $0x1,%eax
/usr/local/lib/go/src/runtime/os_linux.go:107
		n = 1
	}
	return n
 80659fd:	89 84 24 14 20 00 00 	mov    %eax,0x2014(%esp)
 8065a04:	81 c4 10 20 00 00    	add    $0x2010,%esp
 8065a0a:	c3                   	ret    
 8065a0b:	89 d8                	mov    %ebx,%eax
 8065a0d:	eb ee                	jmp    80659fd <runtime.getproccount+0xad>
/usr/local/lib/go/src/runtime/os_linux.go:98
	for _, v := range buf[:r/sys.PtrSize] {
 8065a0f:	e8 0c 0a 00 00       	call   8066420 <runtime.panicslice>
 8065a14:	0f 0b                	ud2    
/usr/local/lib/go/src/runtime/os_linux.go:95
		return 1
 8065a16:	c7 84 24 14 20 00 00 	movl   $0x1,0x2014(%esp)
 8065a1d:	01 00 00 00 
 8065a21:	81 c4 10 20 00 00    	add    $0x2010,%esp
 8065a27:	c3                   	ret    
/usr/local/lib/go/src/runtime/os_linux.go:83
func getproccount() int32 {
 8065a28:	e8 03 09 02 00       	call   8086330 <runtime.morestack_noctxt>
 8065a2d:	e9 1e ff ff ff       	jmp    8065950 <runtime.getproccount>
 8065a32:	cc                   	int3   
 8065a33:	cc                   	int3   
 8065a34:	cc                   	int3   
 8065a35:	cc                   	int3   
 8065a36:	cc                   	int3   


~~~







~~~go

//获取CPU核心数
func getproccount() int32 {
	// This buffer is huge (8 kB) but we are on the system stack
	// and there should be plenty of space (64 kB).
	// Also this is a leaf, so we're not holding up the memory for long.
	// See golang.org/issue/11823.
	// The suggested behavior here is to keep trying with ever-larger
	// buffers, but we don't have a dynamic memory allocator at the
	// moment, so that's a bit tricky and seems like overkill.
	const maxCPUs = 64 * 1024
	var buf [maxCPUs / (sys.PtrSize * 8)]uintptr
	r := sched_getaffinity(0, unsafe.Sizeof(buf), &buf[0])
	if r < 0 {
		return 1
	}
	n := int32(0)
	for _, v := range buf[:r/sys.PtrSize] {
		for v != 0 {
			n += int32(v & 1)
			v >>= 1
		}
	}
	if n == 0 {
		n = 1
	}
	return n
}



    


~~~

~~~assembly
 C library/kernel differences
       This manual page describes the glibc interface for the CPU affinity
       calls.  The actual system call interface is slightly different, with
       the mask being typed as unsigned long *, reflecting the fact that the
       underlying implementation of CPU sets is a simple bit mask.  On
       success, the raw sched_getaffinity() system call returns the size (in
       bytes) of the cpumask_t data type that is used internally by the
       kernel to represent the CPU set bit mask.




08088ce0 <runtime.sched_getaffinity>:
runtime.sched_getaffinity():
/usr/local/lib/go/src/runtime/sys_linux_386.s:517

TEXT runtime·sched_getaffinity(SB),NOSPLIT,$0
	MOVL	$242, AX		// syscall - sched_getaffinity
 8088ce0:	b8 f2 00 00 00       	mov    $0xf2,%eax
/usr/local/lib/go/src/runtime/sys_linux_386.s:518
	MOVL	pid+0(FP), BX
 8088ce5:	8b 5c 24 04          	mov    0x4(%esp),%ebx
/usr/local/lib/go/src/runtime/sys_linux_386.s:519
	MOVL	len+4(FP), CX
 8088ce9:	8b 4c 24 08          	mov    0x8(%esp),%ecx
/usr/local/lib/go/src/runtime/sys_linux_386.s:520
	MOVL	buf+8(FP), DX
 8088ced:	8b 54 24 0c          	mov    0xc(%esp),%edx
/usr/local/lib/go/src/runtime/sys_linux_386.s:521
	INVOKE_SYSCALL
 8088cf1:	cd 80                	int    $0x80
/usr/local/lib/go/src/runtime/sys_linux_386.s:522
	MOVL	AX, ret+12(FP)
 8088cf3:	89 44 24 10          	mov    %eax,0x10(%esp)
/usr/local/lib/go/src/runtime/sys_linux_386.s:523
	RET

~~~

