# schedinit 续 mcommoninit







~~~go

func mcommoninit(mp *m) {
	_g_ := getg()

	// g0 stack won't make sense for user (and is not necessary unwindable).
	if _g_ != _g_.m.g0 {
		callers(1, mp.createstack[:])
	}

	mp.fastrand = 0x49f6428a + uint32(mp.id) + uint32(cputicks())
	if mp.fastrand == 0 {
		mp.fastrand = 0x49f6428a
	}

	lock(&sched.lock)
	mp.id = sched.mcount
	sched.mcount++
    //是否到达上界
	checkmcount()
	mpreinit(mp)
	if mp.gsignal != nil {
		mp.gsignal.stackguard1 = mp.gsignal.stack.lo + _StackGuard
	}

	// Add to allm so garbage collector doesn't free g->m
	// when it is just in a register or thread-local storage.
	mp.alllink = allm

	// NumCgoCall() iterates over allm w/o schedlock,
	// so we need to publish it safely.
	atomicstorep(unsafe.Pointer(&allm), unsafe.Pointer(mp))
	unlock(&sched.lock)

	// Allocate memory to hold a cgo traceback if the cgo call crashes.
	if iscgo || GOOS == "solaris" || GOOS == "windows" {
		mp.cgoCallers = new(cgoCallers)
	}
}


// Called to initialize a new m (including the bootstrap m).
// Called on the parent thread (main thread in case of bootstrap), can allocate memory.
func mpreinit(mp *m) {
	mp.gsignal = malg(32 * 1024)
	mp.gsignal.m = mp
}

func malg(stacksize int32) *g {
	newg := new(g)
	if stacksize >= 0 {
        //多分配一块空间留作他用
		stacksize = round2(_StackSystem + stacksize)
		systemstack(func() {
			newg.stack, newg.stkbar = stackalloc(uint32(stacksize))
		})
        //低地址
		newg.stackguard0 = newg.stack.lo + _StackGuard
        
        //高地址
		newg.stackguard1 = ^uintptr(0)  
		newg.stackAlloc = uintptr(stacksize)
	}
	return newg
}
~~~





~~~asm
0806a210 <runtime.mcommoninit>:
runtime.mcommoninit():
/usr/local/lib/go/src/runtime/proc.go:523

func mcommoninit(mp *m) {
 806a210:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
 806a217:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx
 806a21d:	3b 61 08             	cmp    0x8(%ecx),%esp
 806a220:	0f 86 64 01 00 00    	jbe    806a38a <runtime.mcommoninit+0x17a>
 806a226:	83 ec 14             	sub    $0x14,%esp
/usr/local/lib/go/src/runtime/proc.go:524
	_g_ := getg()
 806a229:	65 8b 05 00 00 00 00 	mov    %gs:0x0,%eax
 806a230:	8b 80 fc ff ff ff    	mov    -0x4(%eax),%eax
/usr/local/lib/go/src/runtime/proc.go:527

	// g0 stack won't make sense for user (and is not necessary unwindable).
	if _g_ != _g_.m.g0 {
 806a236:	8b 48 18             	mov    0x18(%eax),%ecx
 806a239:	8b 09                	mov    (%ecx),%ecx
 806a23b:	39 c8                	cmp    %ecx,%eax
 806a23d:	0f 85 14 01 00 00    	jne    806a357 <runtime.mcommoninit+0x147>
/usr/local/lib/go/src/runtime/proc.go:531
		callers(1, mp.createstack[:])
	}

	mp.fastrand = 0x49f6428a + uint32(mp.id) + uint32(cputicks())
 806a243:	e8 18 d5 01 00       	call   8087760 <runtime.cputicks>
 806a248:	8b 04 24             	mov    (%esp),%eax
 806a24b:	8b 4c 24 18          	mov    0x18(%esp),%ecx
 806a24f:	8b 51 64             	mov    0x64(%ecx),%edx
 806a252:	8d 84 02 8a 42 f6 49 	lea    0x49f6428a(%edx,%eax,1),%eax
 806a259:	89 81 94 00 00 00    	mov    %eax,0x94(%ecx)
/usr/local/lib/go/src/runtime/proc.go:532
	if mp.fastrand == 0 {
 806a25f:	84 01                	test   %al,(%ecx)
 806a261:	85 c0                	test   %eax,%eax
 806a263:	75 0a                	jne    806a26f <runtime.mcommoninit+0x5f>
/usr/local/lib/go/src/runtime/proc.go:533
		mp.fastrand = 0x49f6428a
 806a265:	c7 81 94 00 00 00 8a 	movl   $0x49f6428a,0x94(%ecx)
 806a26c:	42 f6 49 
/usr/local/lib/go/src/runtime/proc.go:536
	}

	lock(&sched.lock)
 806a26f:	8d 05 30 92 0c 08    	lea    0x80c9230,%eax
 806a275:	89 04 24             	mov    %eax,(%esp)
 806a278:	e8 03 61 fe ff       	call   8050380 <runtime.lock>
/usr/local/lib/go/src/runtime/proc.go:537
	mp.id = sched.mcount
 806a27d:	8b 05 40 92 0c 08    	mov    0x80c9240,%eax
 806a283:	8b 4c 24 18          	mov    0x18(%esp),%ecx
 806a287:	89 41 64             	mov    %eax,0x64(%ecx)
/usr/local/lib/go/src/runtime/proc.go:538
	sched.mcount++
 806a28a:	8b 05 40 92 0c 08    	mov    0x80c9240,%eax
 806a290:	40                   	inc    %eax
 806a291:	89 05 40 92 0c 08    	mov    %eax,0x80c9240
/usr/local/lib/go/src/runtime/proc.go:539
	checkmcount()
 806a297:	e8 d4 fe ff ff       	call   806a170 <runtime.checkmcount>
/usr/local/lib/go/src/runtime/proc.go:540
	mpreinit(mp)
 806a29c:	8b 44 24 18          	mov    0x18(%esp),%eax
 806a2a0:	89 04 24             	mov    %eax,(%esp)
 806a2a3:	e8 98 bd ff ff       	call   8066040 <runtime.mpreinit>
/usr/local/lib/go/src/runtime/proc.go:541
	if mp.gsignal != nil {
 806a2a8:	8b 44 24 18          	mov    0x18(%esp),%eax
 806a2ac:	8b 48 2c             	mov    0x2c(%eax),%ecx
 806a2af:	85 c9                	test   %ecx,%ecx
 806a2b1:	74 0b                	je     806a2be <runtime.mcommoninit+0xae>
/usr/local/lib/go/src/runtime/proc.go:542
		mp.gsignal.stackguard1 = mp.gsignal.stack.lo + _StackGuard
 806a2b3:	8b 11                	mov    (%ecx),%edx
 806a2b5:	81 c2 70 03 00 00    	add    $0x370,%edx
 806a2bb:	89 51 0c             	mov    %edx,0xc(%ecx)
/usr/local/lib/go/src/runtime/proc.go:547
	}

	// Add to allm so garbage collector doesn't free g->m
	// when it is just in a register or thread-local storage.
	mp.alllink = allm
 806a2be:	8b 0d 80 8e 0d 08    	mov    0x80d8e80,%ecx
 806a2c4:	8b 15 b8 8f 0c 08    	mov    0x80c8fb8,%edx
 806a2ca:	8d 98 b0 00 00 00    	lea    0xb0(%eax),%ebx
 806a2d0:	85 c9                	test   %ecx,%ecx
 806a2d2:	75 71                	jne    806a345 <runtime.mcommoninit+0x135>
 806a2d4:	89 90 b0 00 00 00    	mov    %edx,0xb0(%eax)
 806a2da:	8d 0d b8 8f 0c 08    	lea    0x80c8fb8,%ecx
/usr/local/lib/go/src/runtime/proc.go:551

	// NumCgoCall() iterates over allm w/o schedlock,
	// so we need to publish it safely.
	atomicstorep(unsafe.Pointer(&allm), unsafe.Pointer(mp))
 806a2e0:	89 0c 24             	mov    %ecx,(%esp)
 806a2e3:	89 44 24 04          	mov    %eax,0x4(%esp)
 806a2e7:	e8 64 fd fd ff       	call   804a050 <runtime.atomicstorep>
/usr/local/lib/go/src/runtime/proc.go:536
	lock(&sched.lock)
 806a2ec:	8d 05 30 92 0c 08    	lea    0x80c9230,%eax
/usr/local/lib/go/src/runtime/proc.go:552
	unlock(&sched.lock)
 806a2f2:	89 04 24             	mov    %eax,(%esp)
 806a2f5:	e8 66 62 fe ff       	call   8050560 <runtime.unlock>
/usr/local/lib/go/src/runtime/proc.go:555

	// Allocate memory to hold a cgo traceback if the cgo call crashes.
	if iscgo || GOOS == "solaris" || GOOS == "windows" {
 806a2fa:	0f b6 05 4b 8d 0d 08 	movzbl 0x80d8d4b,%eax
 806a301:	84 c0                	test   %al,%al
 806a303:	75 04                	jne    806a309 <runtime.mcommoninit+0xf9>
/usr/local/lib/go/src/runtime/proc.go:558
		mp.cgoCallers = new(cgoCallers)
	}
}
 806a305:	83 c4 14             	add    $0x14,%esp
 806a308:	c3                   	ret    
/usr/local/lib/go/src/runtime/proc.go:556
		mp.cgoCallers = new(cgoCallers)
 806a309:	8d 05 40 54 09 08    	lea    0x8095440,%eax
 806a30f:	89 04 24             	mov    %eax,(%esp)
 806a312:	e8 d9 7b fe ff       	call   8051ef0 <runtime.newobject>
 806a317:	8b 05 80 8e 0d 08    	mov    0x80d8e80,%eax
 806a31d:	8b 4c 24 04          	mov    0x4(%esp),%ecx
 806a321:	8b 54 24 18          	mov    0x18(%esp),%edx
 806a325:	8d 9a a8 00 00 00    	lea    0xa8(%edx),%ebx
 806a32b:	85 c0                	test   %eax,%eax
 806a32d:	75 08                	jne    806a337 <runtime.mcommoninit+0x127>
 806a32f:	89 8a a8 00 00 00    	mov    %ecx,0xa8(%edx)
/usr/local/lib/go/src/runtime/proc.go:558
}
 806a335:	eb ce                	jmp    806a305 <runtime.mcommoninit+0xf5>
/usr/local/lib/go/src/runtime/proc.go:556
		mp.cgoCallers = new(cgoCallers)
 806a337:	89 1c 24             	mov    %ebx,(%esp)
 806a33a:	89 4c 24 04          	mov    %ecx,0x4(%esp)
 806a33e:	e8 5d 83 fe ff       	call   80526a0 <runtime.writebarrierptr>
/usr/local/lib/go/src/runtime/proc.go:558
}
 806a343:	eb c0                	jmp    806a305 <runtime.mcommoninit+0xf5>
/usr/local/lib/go/src/runtime/proc.go:547
	mp.alllink = allm
 806a345:	89 1c 24             	mov    %ebx,(%esp)
 806a348:	89 54 24 04          	mov    %edx,0x4(%esp)
 806a34c:	e8 4f 83 fe ff       	call   80526a0 <runtime.writebarrierptr>
/usr/local/lib/go/src/runtime/proc.go:551
	atomicstorep(unsafe.Pointer(&allm), unsafe.Pointer(mp))
 806a351:	8b 44 24 18          	mov    0x18(%esp),%eax
/usr/local/lib/go/src/runtime/proc.go:547
	mp.alllink = allm
 806a355:	eb 83                	jmp    806a2da <runtime.mcommoninit+0xca>
/usr/local/lib/go/src/runtime/proc.go:528
		callers(1, mp.createstack[:])
 806a357:	8b 44 24 18          	mov    0x18(%esp),%eax
 806a35b:	84 00                	test   %al,(%eax)
 806a35d:	8d 88 c0 00 00 00    	lea    0xc0(%eax),%ecx
 806a363:	84 01                	test   %al,(%ecx)
 806a365:	c7 04 24 01 00 00 00 	movl   $0x1,(%esp)
 806a36c:	89 4c 24 04          	mov    %ecx,0x4(%esp)
 806a370:	c7 44 24 08 20 00 00 	movl   $0x20,0x8(%esp)
 806a377:	00 
 806a378:	c7 44 24 0c 20 00 00 	movl   $0x20,0xc(%esp)
 806a37f:	00 
 806a380:	e8 0b 62 01 00       	call   8080590 <runtime.callers>
/usr/local/lib/go/src/runtime/proc.go:531
	mp.fastrand = 0x49f6428a + uint32(mp.id) + uint32(cputicks())
 806a385:	e9 b9 fe ff ff       	jmp    806a243 <runtime.mcommoninit+0x33>
/usr/local/lib/go/src/runtime/proc.go:523
func mcommoninit(mp *m) {
 806a38a:	e8 a1 bf 01 00       	call   8086330 <runtime.morestack_noctxt>
 806a38f:	e9 7c fe ff ff       	jmp    806a210 <runtime.mcommoninit>
 806a394:	cc                   	int3   
 806a395:	cc                   	int3   
 806a396:	cc                   	int3   
 806a397:	cc                   	int3   
 806a398:	cc                   	int3   
 806a399:	cc                   	int3   
 806a39a:	cc                   	int3   
 806a39b:	cc                   	int3   s
 806a39c:	cc                   	int3   
 806a39d:	cc                   	int3   
 806a39e:	cc                   	int3   
 806a39f:	cc                   	int3   
~~~

