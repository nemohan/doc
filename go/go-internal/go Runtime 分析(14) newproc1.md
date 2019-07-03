# newproc1

~~~go
// Create a new g running fn with narg bytes of arguments starting
// at argp and returning nret bytes of results.  callerpc is the
// address of the go statement that created this. The new g is put
// on the queue of g's waiting to run.
func newproc1(fn *funcval, argp *uint8, narg int32, nret int32, callerpc uintptr) *g {
	_g_ := getg()

	if fn == nil {
		_g_.m.throwing = -1 // do not dump full stacks
		throw("go of nil func value")
	}
	_g_.m.locks++ // disable preemption because it can be holding p in a local var
	siz := narg + nret
	siz = (siz + 7) &^ 7

	// We could allocate a larger initial stack if necessary.
	// Not worth it: this is almost always an error.
	// 4*sizeof(uintreg): extra space added below
	// sizeof(uintreg): caller's LR (arm) or return address (x86, in gostartcall).
	if siz >= _StackMin-4*sys.RegSize-sys.RegSize {
		throw("newproc: function arguments too large for new goroutine")
	}

	_p_ := _g_.m.p.ptr()
	newg := gfget(_p_)
	if newg == nil {
		newg = malg(_StackMin)
		casgstatus(newg, _Gidle, _Gdead)
		newg.gcRescan = -1
		allgadd(newg) // publishes with a g->status of Gdead so GC scanner doesn't look at uninitialized stack.
	}
	if newg.stack.hi == 0 {
		throw("newproc1: newg missing stack")
	}

	if readgstatus(newg) != _Gdead {
		throw("newproc1: new g is not Gdead")
	}

	totalSize := 4*sys.RegSize + uintptr(siz) + sys.MinFrameSize // extra space in case of reads slightly beyond frame
	totalSize += -totalSize & (sys.SpAlign - 1)                  // align to spAlign
	sp := newg.stack.hi - totalSize
	spArg := sp
	if usesLR {
		// caller's LR
		*(*uintptr)(unsafe.Pointer(sp)) = 0
		prepGoExitFrame(sp)
		spArg += sys.MinFrameSize
	}
	if narg > 0 {
		memmove(unsafe.Pointer(spArg), unsafe.Pointer(argp), uintptr(narg))
		// This is a stack-to-stack copy. If write barriers
		// are enabled and the source stack is grey (the
		// destination is always black), then perform a
		// barrier copy. We do this *after* the memmove
		// because the destination stack may have garbage on
		// it.
		if writeBarrier.needed && !_g_.m.curg.gcscandone {
			f := findfunc(fn.fn)
			stkmap := (*stackmap)(funcdata(f, _FUNCDATA_ArgsPointerMaps))
			// We're in the prologue, so it's always stack map index 0.
			bv := stackmapdata(stkmap, 0)
			bulkBarrierBitmap(spArg, spArg, uintptr(narg), 0, bv.bytedata)
		}
	}

	memclrNoHeapPointers(unsafe.Pointer(&newg.sched), unsafe.Sizeof(newg.sched))
	newg.sched.sp = sp
	newg.stktopsp = sp
	newg.sched.pc = funcPC(goexit) + sys.PCQuantum // +PCQuantum so that previous instruction is in same function
	newg.sched.g = guintptr(unsafe.Pointer(newg))
	gostartcallfn(&newg.sched, fn)
	newg.gopc = callerpc
	newg.startpc = fn.fn
	if isSystemGoroutine(newg) {
		atomic.Xadd(&sched.ngsys, +1)
	}
	// The stack is dirty from the argument frame, so queue it for
	// scanning. Do this before setting it to runnable so we still
	// own the G. If we're recycling a G, it may already be on the
	// rescan list.
	if newg.gcRescan == -1 {
		queueRescan(newg)
	} else {
		// The recycled G is already on the rescan list. Just
		// mark the stack dirty.
		newg.gcscanvalid = false
	}
	casgstatus(newg, _Gdead, _Grunnable)

	if _p_.goidcache == _p_.goidcacheend {
		// Sched.goidgen is the last allocated id,
		// this batch must be [sched.goidgen+1, sched.goidgen+GoidCacheBatch].
		// At startup sched.goidgen=0, so main goroutine receives goid=1.
		_p_.goidcache = atomic.Xadd64(&sched.goidgen, _GoidCacheBatch)
		_p_.goidcache -= _GoidCacheBatch - 1
		_p_.goidcacheend = _p_.goidcache + _GoidCacheBatch
	}
	newg.goid = int64(_p_.goidcache)
	_p_.goidcache++
	if raceenabled {
		newg.racectx = racegostart(callerpc)
	}
	if trace.enabled {
		traceGoCreate(newg, newg.startpc)
	}
	runqput(_p_, newg, true)

	if atomic.Load(&sched.npidle) != 0 && atomic.Load(&sched.nmspinning) == 0 && runtimeInitTime != 0 {
		wakep()
	}
	_g_.m.locks--
	if _g_.m.locks == 0 && _g_.preempt { // restore the preemption request in case we've cleared it in newstack
		_g_.stackguard0 = stackPreempt
	}
	return newg
}


// Allocate a new g, with a stack big enough for stacksize bytes.
func malg(stacksize int32) *g {
	newg := new(g)
	if stacksize >= 0 {
		stacksize = round2(_StackSystem + stacksize)
		systemstack(func() {
			newg.stack, newg.stkbar = stackalloc(uint32(stacksize))
		})
		newg.stackguard0 = newg.stack.lo + _StackGuard
		newg.stackguard1 = ^uintptr(0)
		newg.stackAlloc = uintptr(stacksize)
	}
	return newg
}


const (
	// G status
	//
	// Beyond indicating the general state of a G, the G status
	// acts like a lock on the goroutine's stack (and hence its
	// ability to execute user code).
	//
	// If you add to this list, add to the list
	// of "okay during garbage collection" status
	// in mgcmark.go too.

	// _Gidle means this goroutine was just allocated and has not
	// yet been initialized.
	_Gidle = iota // 0

	// _Grunnable means this goroutine is on a run queue. It is
	// not currently executing user code. The stack is not owned.
	_Grunnable // 1

	// _Grunning means this goroutine may execute user code. The
	// stack is owned by this goroutine. It is not on a run queue.
	// It is assigned an M and a P.
	_Grunning // 2

	// _Gsyscall means this goroutine is executing a system call.
	// It is not executing user code. The stack is owned by this
	// goroutine. It is not on a run queue. It is assigned an M.
	_Gsyscall // 3

	// _Gwaiting means this goroutine is blocked in the runtime.
	// It is not executing user code. It is not on a run queue,
	// but should be recorded somewhere (e.g., a channel wait
	// queue) so it can be ready()d when necessary. The stack is
	// not owned *except* that a channel operation may read or
	// write parts of the stack under the appropriate channel
	// lock. Otherwise, it is not safe to access the stack after a
	// goroutine enters _Gwaiting (e.g., it may get moved).
	_Gwaiting // 4

	// _Gmoribund_unused is currently unused, but hardcoded in gdb
	// scripts.
	_Gmoribund_unused // 5

	// _Gdead means this goroutine is currently unused. It may be
	// just exited, on a free list, or just being initialized. It
	// is not executing user code. It may or may not have a stack
	// allocated. The G and its stack (if any) are owned by the M
	// that is exiting the G or that obtained the G from the free
	// list.
	_Gdead // 6

	// _Genqueue_unused is currently unused.
	_Genqueue_unused // 7

	// _Gcopystack means this goroutine's stack is being moved. It
	// is not executing user code and is not on a run queue. The
	// stack is owned by the goroutine that put it in _Gcopystack.
	_Gcopystack // 8

	// _Gscan combined with one of the above states other than
	// _Grunning indicates that GC is scanning the stack. The
	// goroutine is not executing user code and the stack is owned
	// by the goroutine that set the _Gscan bit.
	//
	// _Gscanrunning is different: it is used to briefly block
	// state transitions while GC signals the G to scan its own
	// stack. This is otherwise like _Grunning.
	//
	// atomicstatus&~Gscan gives the state the goroutine will
	// return to when the scan completes.
	_Gscan         = 0x1000
	_Gscanrunnable = _Gscan + _Grunnable // 0x1001
	_Gscanrunning  = _Gscan + _Grunning  // 0x1002
	_Gscansyscall  = _Gscan + _Gsyscall  // 0x1003
	_Gscanwaiting  = _Gscan + _Gwaiting  // 0x1004
)



//=================================================
// If asked to move to or from a Gscanstatus this will throw. Use the castogscanstatus
// and casfrom_Gscanstatus instead.
// casgstatus will loop if the g->atomicstatus is in a Gscan status until the routine that
// put it in the Gscan state is finished.
//go:nosplit
	_Gscan         = 0x1000
	_Gscanrunnable = _Gscan + _Grunnable // 0x1001
	_Gscanrunning  = _Gscan + _Grunning  // 0x1002
	_Gscansyscall  = _Gscan + _Gsyscall  // 0x1003
	_Gscanwaiting  = _Gscan + _Gwaiting  // 0x1004
//========================================
// newproc1 调用casgstatus(newg, _Gidle, _Gdead)  casgstatus(newg, 0, 6)


func casgstatus(gp *g, oldval, newval uint32) {
	if (oldval&_Gscan != 0) || (newval&_Gscan != 0) || oldval == newval {
		systemstack(func() {
			print("runtime: casgstatus: oldval=", hex(oldval), " newval=", hex(newval), "\n")
			throw("casgstatus: bad incoming values")
		})
	}

	if oldval == _Grunning && gp.gcscanvalid {
		// If oldvall == _Grunning, then the actual status must be
		// _Grunning or _Grunning|_Gscan; either way,
		// we own gp.gcscanvalid, so it's safe to read.
		// gp.gcscanvalid must not be true when we are running.
		print("runtime: casgstatus ", hex(oldval), "->", hex(newval), " gp.status=", hex(gp.atomicstatus), " gp.gcscanvalid=true\n")
		throw("casgstatus")
	}

	// See http://golang.org/cl/21503 for justification of the yield delay.
	const yieldDelay = 5 * 1000
	var nextYield int64

	// loop if gp->atomicstatus is in a scan state giving
	// GC time to finish and change the state to oldval.
    
    // atomic.Cas compare and swap, 如果oldval 等于 gp.atomicsatus ，将
    // newval赋值给gp.atomicstatus。并返回1 .否则返回0
	for i := 0; !atomic.Cas(&gp.atomicstatus, oldval, newval); i++ {
		if oldval == _Gwaiting && gp.atomicstatus == _Grunnable {
			systemstack(func() {
				throw("casgstatus: waiting for Gwaiting but is Grunnable")
			})
		}
		// Help GC if needed.
		// if gp.preemptscan && !gp.gcworkdone && (oldval == _Grunning || oldval == _Gsyscall) {
		// 	gp.preemptscan = false
		// 	systemstack(func() {
		// 		gcphasework(gp)
		// 	})
		// }
		// But meanwhile just yield.
		if i == 0 {
			nextYield = nanotime() + yieldDelay
		}
		if nanotime() < nextYield {
			for x := 0; x < 10 && gp.atomicstatus != oldval; x++ {
				procyield(1)
			}
		} else {
			osyield()
			nextYield = nanotime() + yieldDelay/2
		}
	}
	if newval == _Grunning && gp.gcscanvalid {
		// Run queueRescan on the system stack so it has more space.
		systemstack(func() { queueRescan(gp) })
	}
}
~~~





~~~assembly
// ===================================== newproc1

0806f2a0 <runtime.newproc1>:
runtime.newproc1():
/usr/local/lib/go/src/runtime/proc.go:2853

// Create a new g running fn with narg bytes of arguments starting
// at argp and returning nret bytes of results.  callerpc is the
// address of the go statement that created this. The new g is put
// on the queue of g's waiting to run.


stack 结构:
 callerpc  	0x4c
 nret 		0x48
 narg 		0x44
 argp		0x40
 fn 
 ret 
//##############newproc 调用newproc1时 nret 为0, narag 为siz
func newproc1(fn *funcval, argp *uint8, narg int32, nret int32, callerpc uintptr) *g {
 806f2a0:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
 806f2a7:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx
 806f2ad:	3b 61 08             	cmp    0x8(%ecx),%esp
 806f2b0:	0f 86 ef 04 00 00    	jbe    806f7a5 <runtime.newproc1+0x505>
 //############## 检查栈空间
 
 806f2b6:	83 ec 38             	sub    $0x38,%esp
/usr/local/lib/go/src/runtime/proc.go:2854
	_g_ := getg()
 806f2b9:	65 8b 05 00 00 00 00 	mov    %gs:0x0,%eax
 806f2c0:	8b 80 fc ff ff ff    	mov    -0x4(%eax),%eax
 806f2c6:	89 44 24 24          	mov    %eax,0x24(%esp)
 
/usr/local/lib/go/src/runtime/proc.go:2856
	if fn == nil {
 806f2ca:	8b 4c 24 3c          	mov    0x3c(%esp),%ecx
 806f2ce:	85 c9                	test   %ecx,%ecx
 806f2d0:	0f 84 ad 04 00 00    	je     806f783 <runtime.newproc1+0x4e3>
/usr/local/lib/go/src/runtime/proc.go:2860
		_g_.m.throwing = -1 // do not dump full stacks
		throw("go of nil func value")
	}
	
	_g_.m.locks++ // disable preemption because it can be holding p in a local var
 806f2d6:	8b 50 18             	mov    0x18(%eax),%edx
 806f2d9:	8b 5a 78             	mov    0x78(%edx),%ebx
 806f2dc:	43                   	inc    %ebx
 806f2dd:	89 5a 78             	mov    %ebx,0x78(%edx)
 
 
/usr/local/lib/go/src/runtime/proc.go:2862
	siz := narg + nret
	siz = (siz + 7) &^ 7
 806f2e0:	8b 54 24 48          	mov    0x48(%esp),%edx
 //########## edx = nret
 806f2e4:	8b 5c 24 44          	mov    0x44(%esp),%ebx
 //############ ebx = narg
 806f2e8:	8d 54 13 07          	lea    0x7(%ebx,%edx,1),%edx
 //########## edx = ebx + edx *1 + 0x7 = narg + nret + 7
 806f2ec:	83 e2 f8             	and    $0xfffffff8,%edx
 //############ 0xfffffff8 就是 ^0x7 
 806f2ef:	89 54 24 18          	mov    %edx,0x18(%esp)
 
 
/usr/local/lib/go/src/runtime/proc.go:2868

	// We could allocate a larger initial stack if necessary.
	// Not worth it: this is almost always an error.
	// 4*sizeof(uintreg): extra space added below
	// sizeof(uintreg): caller's LR (arm) or return address (x86, in gostartcall).
	if siz >= _StackMin-4*sys.RegSize-sys.RegSize {
 806f2f3:	81 fa ec 07 00 00    	cmp    $0x7ec,%edx
 806f2f9:	0f 8d 6c 04 00 00    	jge    806f76b <runtime.newproc1+0x4cb>
 //#########_StackMin = 2048  在32位平台 sys.RegSize应该是 4
 
/usr/local/lib/go/src/runtime/proc.go:2872
		throw("newproc: function arguments too large for new goroutine")
	}

	_p_ := _g_.m.p.ptr()
 806f2ff:	8b 68 18             	mov    0x18(%eax),%ebp
 806f302:	8b 6d 5c             	mov    0x5c(%ebp),%ebp
 806f305:	89 6c 24 2c          	mov    %ebp,0x2c(%esp)
 //#################3 m.p是什么时候初始化的 ??????????????????????????
 
 //############启动阶段 newg 为空
/usr/local/lib/go/src/runtime/proc.go:2873
	newg := gfget(_p_)
 806f309:	89 2c 24             	mov    %ebp,(%esp)
 806f30c:	e8 ef 06 00 00       	call   806fa00 <runtime.gfget>
 806f311:	8b 44 24 04          	mov    0x4(%esp),%eax
/usr/local/lib/go/src/runtime/proc.go:2874
	if newg == nil {
 806f315:	85 c0                	test   %eax,%eax
 806f317:	0f 84 03 04 00 00    	je     806f720 <runtime.newproc1+0x480>
/usr/local/lib/go/src/runtime/proc.go:2880
		newg = malg(_StackMin)
		casgstatus(newg, _Gidle, _Gdead)
		newg.gcRescan = -1
		allgadd(newg) // publishes with a g->status of Gdead so GC scanner doesn't look at uninitialized stack.
	}
	if newg.stack.hi == 0 {
 806f31d:	89 44 24 20          	mov    %eax,0x20(%esp)
 806f321:	8b 48 04             	mov    0x4(%eax),%ecx
 806f324:	85 c9                	test   %ecx,%ecx
 806f326:	0f 84 dc 03 00 00    	je     806f708 <runtime.newproc1+0x468>
/usr/local/lib/go/src/runtime/proc.go:2884
		throw("newproc1: newg missing stack")
	}

	if readgstatus(newg) != _Gdead {
 806f32c:	89 04 24             	mov    %eax,(%esp)
 806f32f:	e8 ac b4 ff ff       	call   806a7e0 <runtime.readgstatus>
 806f334:	8b 44 24 04          	mov    0x4(%esp),%eax
 806f338:	83 f8 06             	cmp    $0x6,%eax
 806f33b:	0f 85 af 03 00 00    	jne    806f6f0 <runtime.newproc1+0x450>
/usr/local/lib/go/src/runtime/proc.go:2888
		throw("newproc1: new g is not Gdead")
	}

	totalSize := 4*sys.RegSize + uintptr(siz) + sys.MinFrameSize // extra space in case of reads slightly beyond frame
 806f341:	8b 44 24 18          	mov    0x18(%esp),%eax
 806f345:	83 c0 10             	add    $0x10,%eax
/usr/local/lib/go/src/runtime/proc.go:2890
	totalSize += -totalSize & (sys.SpAlign - 1)                  // align to spAlign
	sp := newg.stack.hi - totalSize
 806f348:	8b 4c 24 20          	mov    0x20(%esp),%ecx
 806f34c:	8b 51 04             	mov    0x4(%ecx),%edx
 806f34f:	29 c2                	sub    %eax,%edx
 806f351:	89 54 24 14          	mov    %edx,0x14(%esp)
/usr/local/lib/go/src/runtime/proc.go:2898
		// caller's LR
		*(*uintptr)(unsafe.Pointer(sp)) = 0
		prepGoExitFrame(sp)
		spArg += sys.MinFrameSize
	}
	if narg > 0 {
 806f355:	8b 44 24 44          	mov    0x44(%esp),%eax
 806f359:	85 c0                	test   %eax,%eax
 806f35b:	0f 8f de 02 00 00    	jg     806f63f <runtime.newproc1+0x39f>
/usr/local/lib/go/src/runtime/proc.go:2915
			bv := stackmapdata(stkmap, 0)
			bulkBarrierBitmap(spArg, spArg, uintptr(narg), 0, bv.bytedata)
		}
	}

	memclrNoHeapPointers(unsafe.Pointer(&newg.sched), unsafe.Sizeof(newg.sched))
 806f361:	8d 41 20             	lea    0x20(%ecx),%eax
 806f364:	89 44 24 28          	mov    %eax,0x28(%esp)
 806f368:	89 04 24             	mov    %eax,(%esp)
 806f36b:	c7 44 24 04 1c 00 00 	movl   $0x1c,0x4(%esp)
 806f372:	00 
 806f373:	e8 a8 90 01 00       	call   8088420 <runtime.memclrNoHeapPointers>
/usr/local/lib/go/src/runtime/proc.go:2916
	newg.sched.sp = sp
 806f378:	8b 44 24 14          	mov    0x14(%esp),%eax
 806f37c:	8b 4c 24 20          	mov    0x20(%esp),%ecx
 806f380:	89 41 20             	mov    %eax,0x20(%ecx)
/usr/local/lib/go/src/runtime/proc.go:2917
	newg.stktopsp = sp
 806f383:	89 41 54             	mov    %eax,0x54(%ecx)
/usr/local/lib/go/src/runtime/proc.go:2918
	newg.sched.pc = funcPC(goexit) + sys.PCQuantum // +PCQuantum so that previous instruction is in same function
 806f386:	8d 05 60 29 09 08    	lea    0x8092960,%eax
 806f38c:	89 44 24 30          	mov    %eax,0x30(%esp)
 806f390:	8d 05 34 25 0a 08    	lea    0x80a2534,%eax
 806f396:	89 44 24 34          	mov    %eax,0x34(%esp)
 806f39a:	8d 44 24 30          	lea    0x30(%esp),%eax
 806f39e:	83 c0 04             	add    $0x4,%eax
 806f3a1:	8b 00                	mov    (%eax),%eax
 806f3a3:	8b 00                	mov    (%eax),%eax
 806f3a5:	40                   	inc    %eax
 806f3a6:	89 41 24             	mov    %eax,0x24(%ecx)
/usr/local/lib/go/src/runtime/proc.go:2919
	newg.sched.g = guintptr(unsafe.Pointer(newg))
 806f3a9:	89 c8                	mov    %ecx,%eax
 806f3ab:	89 41 28             	mov    %eax,0x28(%ecx)
/usr/local/lib/go/src/runtime/proc.go:2920
	gostartcallfn(&newg.sched, fn)
 806f3ae:	8b 44 24 28          	mov    0x28(%esp),%eax
 806f3b2:	89 04 24             	mov    %eax,(%esp)
 806f3b5:	8b 44 24 3c          	mov    0x3c(%esp),%eax
 806f3b9:	89 44 24 04          	mov    %eax,0x4(%esp)
 806f3bd:	e8 ae a7 00 00       	call   8079b70 <runtime.gostartcallfn>
/usr/local/lib/go/src/runtime/proc.go:2921
	newg.gopc = callerpc
 806f3c2:	8b 44 24 4c          	mov    0x4c(%esp),%eax
 806f3c6:	8b 4c 24 20          	mov    0x20(%esp),%ecx
 806f3ca:	89 81 bc 00 00 00    	mov    %eax,0xbc(%ecx)
/usr/local/lib/go/src/runtime/proc.go:2922
	newg.startpc = fn.fn
 806f3d0:	8b 44 24 3c          	mov    0x3c(%esp),%eax
 806f3d4:	8b 00                	mov    (%eax),%eax
 806f3d6:	89 81 c0 00 00 00    	mov    %eax,0xc0(%ecx)
/usr/local/lib/go/src/runtime/proc.go:2923
	if isSystemGoroutine(newg) {
 806f3dc:	8b 15 f8 8d 0d 08    	mov    0x80d8df8,%edx
 806f3e2:	39 d0                	cmp    %edx,%eax
 806f3e4:	75 0f                	jne    806f3f5 <runtime.newproc1+0x155>
 806f3e6:	0f b6 15 44 8d 0d 08 	movzbl 0x80d8d44,%edx
 806f3ed:	84 d2                	test   %dl,%dl
 806f3ef:	0f 84 40 02 00 00    	je     806f635 <runtime.newproc1+0x395>
 806f3f5:	8b 15 60 8d 0d 08    	mov    0x80d8d60,%edx
 806f3fb:	39 d0                	cmp    %edx,%eax
 806f3fd:	0f 85 fa 01 00 00    	jne    806f5fd <runtime.newproc1+0x35d>
/usr/local/lib/go/src/runtime/proc.go:2955
		newg.racectx = racegostart(callerpc)
	}
	if trace.enabled {
		traceGoCreate(newg, newg.startpc)
	}
	runqput(_p_, newg, true)
 806f403:	b8 01 00 00 00       	mov    $0x1,%eax
/usr/local/lib/go/src/runtime/proc.go:2923
	if isSystemGoroutine(newg) {
 806f408:	84 c0                	test   %al,%al
 806f40a:	0f 85 ce 01 00 00    	jne    806f5de <runtime.newproc1+0x33e>
/usr/local/lib/go/src/runtime/proc.go:2930
	if newg.gcRescan == -1 {
 806f410:	8b 81 d8 00 00 00    	mov    0xd8(%ecx),%eax
 806f416:	83 f8 ff             	cmp    $0xffffffff,%eax
 806f419:	0f 84 ae 01 00 00    	je     806f5cd <runtime.newproc1+0x32d>
/usr/local/lib/go/src/runtime/proc.go:2935
		newg.gcscanvalid = false
 806f41f:	c6 81 84 00 00 00 00 	movb   $0x0,0x84(%ecx)
/usr/local/lib/go/src/runtime/proc.go:2937
	casgstatus(newg, _Gdead, _Grunnable)
 806f426:	89 0c 24             	mov    %ecx,(%esp)
 806f429:	c7 44 24 04 06 00 00 	movl   $0x6,0x4(%esp)
 806f430:	00 
 806f431:	c7 44 24 08 01 00 00 	movl   $0x1,0x8(%esp)
 806f438:	00 
 806f439:	e8 c2 b6 ff ff       	call   806ab00 <runtime.casgstatus>
/usr/local/lib/go/src/runtime/proc.go:2939
	if _p_.goidcache == _p_.goidcacheend {
 806f43e:	8b 44 24 2c          	mov    0x2c(%esp),%eax
 806f442:	8b 88 e8 02 00 00    	mov    0x2e8(%eax),%ecx
 806f448:	8b 90 ec 02 00 00    	mov    0x2ec(%eax),%edx
 806f44e:	8b 98 e4 02 00 00    	mov    0x2e4(%eax),%ebx
 806f454:	8b a8 e0 02 00 00    	mov    0x2e0(%eax),%ebp
 806f45a:	39 cd                	cmp    %ecx,%ebp
 806f45c:	0f 94 c1             	sete   %cl
 806f45f:	39 d3                	cmp    %edx,%ebx
 806f461:	0f 94 c2             	sete   %dl
 806f464:	21 d1                	and    %edx,%ecx
 806f466:	84 c9                	test   %cl,%cl
 806f468:	0f 85 fa 00 00 00    	jne    806f568 <runtime.newproc1+0x2c8>
/usr/local/lib/go/src/runtime/proc.go:2947
	newg.goid = int64(_p_.goidcache)
 806f46e:	8b 88 e4 02 00 00    	mov    0x2e4(%eax),%ecx
 806f474:	8b 90 e0 02 00 00    	mov    0x2e0(%eax),%edx
 806f47a:	8b 5c 24 20          	mov    0x20(%esp),%ebx
 806f47e:	89 53 64             	mov    %edx,0x64(%ebx)
 806f481:	89 4b 68             	mov    %ecx,0x68(%ebx)
/usr/local/lib/go/src/runtime/proc.go:2948
	_p_.goidcache++
 806f484:	8b 88 e0 02 00 00    	mov    0x2e0(%eax),%ecx
 806f48a:	83 c1 01             	add    $0x1,%ecx
 806f48d:	8b 90 e4 02 00 00    	mov    0x2e4(%eax),%edx
 806f493:	89 88 e0 02 00 00    	mov    %ecx,0x2e0(%eax)
 806f499:	83 d2 00             	adc    $0x0,%edx
 806f49c:	89 90 e4 02 00 00    	mov    %edx,0x2e4(%eax)
/usr/local/lib/go/src/runtime/proc.go:2952
	if trace.enabled {
 806f4a2:	0f b6 0d a8 0c 0d 08 	movzbl 0x80d0ca8,%ecx
 806f4a9:	84 c9                	test   %cl,%cl
 806f4ab:	0f 85 98 00 00 00    	jne    806f549 <runtime.newproc1+0x2a9>
/usr/local/lib/go/src/runtime/proc.go:2955
	runqput(_p_, newg, true)
 806f4b1:	89 04 24             	mov    %eax,(%esp)
 806f4b4:	89 5c 24 04          	mov    %ebx,0x4(%esp)
 806f4b8:	c6 44 24 08 01       	movb   $0x1,0x8(%esp)
 806f4bd:	e8 6e 38 00 00       	call   8072d30 <runtime.runqput>
/usr/local/lib/go/src/runtime/proc.go:2957

	if atomic.Load(&sched.npidle) != 0 && atomic.Load(&sched.nmspinning) == 0 && runtimeInitTime != 0 {
 806f4c2:	8d 05 50 92 0c 08    	lea    0x80c9250,%eax
 806f4c8:	89 04 24             	mov    %eax,(%esp)
 806f4cb:	e8 60 9b fd ff       	call   8049030 <runtime/internal/atomic.Load>
 806f4d0:	8b 44 24 04          	mov    0x4(%esp),%eax
 806f4d4:	85 c0                	test   %eax,%eax
 806f4d6:	75 36                	jne    806f50e <runtime.newproc1+0x26e>
/usr/local/lib/go/src/runtime/proc.go:2960
		wakep()
	}
	_g_.m.locks--
 806f4d8:	8b 44 24 24          	mov    0x24(%esp),%eax
 806f4dc:	8b 48 18             	mov    0x18(%eax),%ecx
 806f4df:	8b 51 78             	mov    0x78(%ecx),%edx
 806f4e2:	4a                   	dec    %edx
 806f4e3:	89 51 78             	mov    %edx,0x78(%ecx)
/usr/local/lib/go/src/runtime/proc.go:2961
	if _g_.m.locks == 0 && _g_.preempt { // restore the preemption request in case we've cleared it in newstack
 806f4e6:	8b 48 18             	mov    0x18(%eax),%ecx
 806f4e9:	8b 49 78             	mov    0x78(%ecx),%ecx
 806f4ec:	85 c9                	test   %ecx,%ecx
 806f4ee:	75 12                	jne    806f502 <runtime.newproc1+0x262>
 806f4f0:	0f b6 88 80 00 00 00 	movzbl 0x80(%eax),%ecx
 806f4f7:	84 c9                	test   %cl,%cl
 806f4f9:	74 07                	je     806f502 <runtime.newproc1+0x262>
/usr/local/lib/go/src/runtime/proc.go:2962
		_g_.stackguard0 = stackPreempt
 806f4fb:	c7 40 08 de fa ff ff 	movl   $0xfffffade,0x8(%eax)
/usr/local/lib/go/src/runtime/proc.go:2964
	}
	return newg
 806f502:	8b 44 24 20          	mov    0x20(%esp),%eax
 806f506:	89 44 24 50          	mov    %eax,0x50(%esp)
 806f50a:	83 c4 38             	add    $0x38,%esp
 806f50d:	c3                   	ret    
/usr/local/lib/go/src/runtime/proc.go:2957
	if atomic.Load(&sched.npidle) != 0 && atomic.Load(&sched.nmspinning) == 0 && runtimeInitTime != 0 {
 806f50e:	8d 05 54 92 0c 08    	lea    0x80c9254,%eax
 806f514:	89 04 24             	mov    %eax,(%esp)
 806f517:	e8 14 9b fd ff       	call   8049030 <runtime/internal/atomic.Load>
 806f51c:	8b 44 24 04          	mov    0x4(%esp),%eax
 806f520:	85 c0                	test   %eax,%eax
 806f522:	75 b4                	jne    806f4d8 <runtime.newproc1+0x238>
 806f524:	8b 05 48 8e 0d 08    	mov    0x80d8e48,%eax
 806f52a:	8b 0d 4c 8e 0d 08    	mov    0x80d8e4c,%ecx
 806f530:	85 c9                	test   %ecx,%ecx
 806f532:	0f 95 c1             	setne  %cl
 806f535:	85 c0                	test   %eax,%eax
 806f537:	0f 95 c0             	setne  %al
 806f53a:	09 c1                	or     %eax,%ecx
 806f53c:	84 c9                	test   %cl,%cl
 806f53e:	75 02                	jne    806f542 <runtime.newproc1+0x2a2>
/usr/local/lib/go/src/runtime/proc.go:2960
	_g_.m.locks--
 806f540:	eb 96                	jmp    806f4d8 <runtime.newproc1+0x238>
/usr/local/lib/go/src/runtime/proc.go:2958
		wakep()
 806f542:	e8 39 d5 ff ff       	call   806ca80 <runtime.wakep>
/usr/local/lib/go/src/runtime/proc.go:2960
	_g_.m.locks--
 806f547:	eb 8f                	jmp    806f4d8 <runtime.newproc1+0x238>
/usr/local/lib/go/src/runtime/proc.go:2953
		traceGoCreate(newg, newg.startpc)
 806f549:	8b 8b c0 00 00 00    	mov    0xc0(%ebx),%ecx
 806f54f:	89 4c 24 04          	mov    %ecx,0x4(%esp)
 806f553:	89 1c 24             	mov    %ebx,(%esp)
 806f556:	e8 25 e3 00 00       	call   807d880 <runtime.traceGoCreate>
/usr/local/lib/go/src/runtime/proc.go:2955
	runqput(_p_, newg, true)
 806f55b:	8b 44 24 2c          	mov    0x2c(%esp),%eax
 806f55f:	8b 5c 24 20          	mov    0x20(%esp),%ebx
 806f563:	e9 49 ff ff ff       	jmp    806f4b1 <runtime.newproc1+0x211>
/usr/local/lib/go/src/runtime/proc.go:2943
		_p_.goidcache = atomic.Xadd64(&sched.goidgen, _GoidCacheBatch)
 806f568:	8d 0d 20 92 0c 08    	lea    0x80c9220,%ecx
 806f56e:	89 0c 24             	mov    %ecx,(%esp)
 806f571:	c7 44 24 04 10 00 00 	movl   $0x10,0x4(%esp)
 806f578:	00 
 806f579:	c7 44 24 08 00 00 00 	movl   $0x0,0x8(%esp)
 806f580:	00 
 806f581:	e8 ca 9a fd ff       	call   8049050 <runtime/internal/atomic.Xadd64>
 806f586:	8b 44 24 0c          	mov    0xc(%esp),%eax
/usr/local/lib/go/src/runtime/proc.go:2944
		_p_.goidcache -= _GoidCacheBatch - 1
 806f58a:	89 c1                	mov    %eax,%ecx
 806f58c:	83 c0 f1             	add    $0xfffffff1,%eax
/usr/local/lib/go/src/runtime/proc.go:2945
		_p_.goidcacheend = _p_.goidcache + _GoidCacheBatch
 806f58f:	89 c2                	mov    %eax,%edx
 806f591:	83 c0 10             	add    $0x10,%eax
/usr/local/lib/go/src/runtime/proc.go:2943
		_p_.goidcache = atomic.Xadd64(&sched.goidgen, _GoidCacheBatch)
 806f594:	8b 5c 24 10          	mov    0x10(%esp),%ebx
 806f598:	8b 6c 24 2c          	mov    0x2c(%esp),%ebp
 806f59c:	89 9d e4 02 00 00    	mov    %ebx,0x2e4(%ebp)
/usr/local/lib/go/src/runtime/proc.go:2944
		_p_.goidcache -= _GoidCacheBatch - 1
 806f5a2:	89 95 e0 02 00 00    	mov    %edx,0x2e0(%ebp)
 806f5a8:	83 c1 f1             	add    $0xfffffff1,%ecx
 806f5ab:	83 d3 ff             	adc    $0xffffffff,%ebx
 806f5ae:	89 9d e4 02 00 00    	mov    %ebx,0x2e4(%ebp)
/usr/local/lib/go/src/runtime/proc.go:2945
		_p_.goidcacheend = _p_.goidcache + _GoidCacheBatch
 806f5b4:	89 85 e8 02 00 00    	mov    %eax,0x2e8(%ebp)
 806f5ba:	83 c2 10             	add    $0x10,%edx
 806f5bd:	83 d3 00             	adc    $0x0,%ebx
 806f5c0:	89 9d ec 02 00 00    	mov    %ebx,0x2ec(%ebp)
/usr/local/lib/go/src/runtime/proc.go:2947
	newg.goid = int64(_p_.goidcache)
 806f5c6:	89 e8                	mov    %ebp,%eax
 806f5c8:	e9 a1 fe ff ff       	jmp    806f46e <runtime.newproc1+0x1ce>
/usr/local/lib/go/src/runtime/proc.go:2931
		queueRescan(newg)
 806f5cd:	89 0c 24             	mov    %ecx,(%esp)
 806f5d0:	e8 cb d6 fe ff       	call   805cca0 <runtime.queueRescan>
/usr/local/lib/go/src/runtime/proc.go:2937
	casgstatus(newg, _Gdead, _Grunnable)
 806f5d5:	8b 4c 24 20          	mov    0x20(%esp),%ecx
 806f5d9:	e9 48 fe ff ff       	jmp    806f426 <runtime.newproc1+0x186>
/usr/local/lib/go/src/runtime/proc.go:2924
		atomic.Xadd(&sched.ngsys, +1)
 806f5de:	8d 05 48 92 0c 08    	lea    0x80c9248,%eax
 806f5e4:	89 04 24             	mov    %eax,(%esp)
 806f5e7:	c7 44 24 04 01 00 00 	movl   $0x1,0x4(%esp)
 806f5ee:	00 
 806f5ef:	e8 fc 9b fd ff       	call   80491f0 <runtime/internal/atomic.Xadd>
/usr/local/lib/go/src/runtime/proc.go:2930
	if newg.gcRescan == -1 {
 806f5f4:	8b 4c 24 20          	mov    0x20(%esp),%ecx
 806f5f8:	e9 13 fe ff ff       	jmp    806f410 <runtime.newproc1+0x170>
/usr/local/lib/go/src/runtime/proc.go:2923
	if isSystemGoroutine(newg) {
 806f5fd:	8b 15 9c 8d 0d 08    	mov    0x80d8d9c,%edx
 806f603:	39 d0                	cmp    %edx,%eax
 806f605:	75 0a                	jne    806f611 <runtime.newproc1+0x371>
/usr/local/lib/go/src/runtime/proc.go:2955
	runqput(_p_, newg, true)
 806f607:	b8 01 00 00 00       	mov    $0x1,%eax
/usr/local/lib/go/src/runtime/proc.go:2923
	if isSystemGoroutine(newg) {
 806f60c:	e9 f7 fd ff ff       	jmp    806f408 <runtime.newproc1+0x168>
 806f611:	8b 15 10 8e 0d 08    	mov    0x80d8e10,%edx
 806f617:	39 d0                	cmp    %edx,%eax
 806f619:	75 0a                	jne    806f625 <runtime.newproc1+0x385>
/usr/local/lib/go/src/runtime/proc.go:2955
	runqput(_p_, newg, true)
 806f61b:	b8 01 00 00 00       	mov    $0x1,%eax
/usr/local/lib/go/src/runtime/proc.go:2923
	if isSystemGoroutine(newg) {
 806f620:	e9 e3 fd ff ff       	jmp    806f408 <runtime.newproc1+0x168>
 806f625:	8b 15 a4 8d 0d 08    	mov    0x80d8da4,%edx
 806f62b:	39 d0                	cmp    %edx,%eax
 806f62d:	0f 94 c0             	sete   %al
 806f630:	e9 d3 fd ff ff       	jmp    806f408 <runtime.newproc1+0x168>
/usr/local/lib/go/src/runtime/proc.go:2955
	runqput(_p_, newg, true)
 806f635:	b8 01 00 00 00       	mov    $0x1,%eax
/usr/local/lib/go/src/runtime/proc.go:2923
	if isSystemGoroutine(newg) {
 806f63a:	e9 c9 fd ff ff       	jmp    806f408 <runtime.newproc1+0x168>
/usr/local/lib/go/src/runtime/proc.go:2899
		memmove(unsafe.Pointer(spArg), unsafe.Pointer(argp), uintptr(narg))
 806f63f:	89 d3                	mov    %edx,%ebx
 806f641:	89 1c 24             	mov    %ebx,(%esp)
 806f644:	8b 5c 24 40          	mov    0x40(%esp),%ebx
 806f648:	89 5c 24 04          	mov    %ebx,0x4(%esp)
 806f64c:	89 44 24 08          	mov    %eax,0x8(%esp)
 806f650:	e8 ab 8f 01 00       	call   8088600 <runtime.memmove>
/usr/local/lib/go/src/runtime/proc.go:2906
		if writeBarrier.needed && !_g_.m.curg.gcscandone {
 806f655:	0f b6 05 84 8e 0d 08 	movzbl 0x80d8e84,%eax
 806f65c:	84 c0                	test   %al,%al
 806f65e:	0f 84 86 00 00 00    	je     806f6ea <runtime.newproc1+0x44a>
 806f664:	8b 44 24 24          	mov    0x24(%esp),%eax
 806f668:	8b 48 18             	mov    0x18(%eax),%ecx
 806f66b:	8b 49 54             	mov    0x54(%ecx),%ecx
 806f66e:	0f b6 89 83 00 00 00 	movzbl 0x83(%ecx),%ecx
 806f675:	84 c9                	test   %cl,%cl
 806f677:	74 0d                	je     806f686 <runtime.newproc1+0x3e6>
/usr/local/lib/go/src/runtime/proc.go:2915
	memclrNoHeapPointers(unsafe.Pointer(&newg.sched), unsafe.Sizeof(newg.sched))
 806f679:	8b 4c 24 20          	mov    0x20(%esp),%ecx
/usr/local/lib/go/src/runtime/proc.go:2916
	newg.sched.sp = sp
 806f67d:	8b 54 24 14          	mov    0x14(%esp),%edx
/usr/local/lib/go/src/runtime/proc.go:2915
	memclrNoHeapPointers(unsafe.Pointer(&newg.sched), unsafe.Sizeof(newg.sched))
 806f681:	e9 db fc ff ff       	jmp    806f361 <runtime.newproc1+0xc1>
/usr/local/lib/go/src/runtime/proc.go:2907
			f := findfunc(fn.fn)
 806f686:	8b 4c 24 3c          	mov    0x3c(%esp),%ecx
 806f68a:	8b 11                	mov    (%ecx),%edx
 806f68c:	89 14 24             	mov    %edx,(%esp)
 806f68f:	e8 fc bc 00 00       	call   807b390 <runtime.findfunc>
 806f694:	8b 44 24 04          	mov    0x4(%esp),%eax
/usr/local/lib/go/src/runtime/proc.go:2908
			stkmap := (*stackmap)(funcdata(f, _FUNCDATA_ArgsPointerMaps))
 806f698:	89 04 24             	mov    %eax,(%esp)
 806f69b:	c7 44 24 04 00 00 00 	movl   $0x0,0x4(%esp)
 806f6a2:	00 
 806f6a3:	e8 b8 c7 00 00       	call   807be60 <runtime.funcdata>
 806f6a8:	8b 44 24 08          	mov    0x8(%esp),%eax
/usr/local/lib/go/src/runtime/proc.go:2910
			bv := stackmapdata(stkmap, 0)
 806f6ac:	89 04 24             	mov    %eax,(%esp)
 806f6af:	c7 44 24 04 00 00 00 	movl   $0x0,0x4(%esp)
 806f6b6:	00 
 806f6b7:	e8 74 c9 00 00       	call   807c030 <runtime.stackmapdata>
 806f6bc:	8b 44 24 0c          	mov    0xc(%esp),%eax
/usr/local/lib/go/src/runtime/proc.go:2911
			bulkBarrierBitmap(spArg, spArg, uintptr(narg), 0, bv.bytedata)
 806f6c0:	8b 4c 24 14          	mov    0x14(%esp),%ecx
 806f6c4:	89 0c 24             	mov    %ecx,(%esp)
 806f6c7:	89 4c 24 04          	mov    %ecx,0x4(%esp)
 806f6cb:	8b 54 24 44          	mov    0x44(%esp),%edx
 806f6cf:	89 54 24 08          	mov    %edx,0x8(%esp)
 806f6d3:	c7 44 24 0c 00 00 00 	movl   $0x0,0xc(%esp)
 806f6da:	00 
 806f6db:	89 44 24 10          	mov    %eax,0x10(%esp)
 806f6df:	e8 7c 40 fe ff       	call   8053760 <runtime.bulkBarrierBitmap>
/usr/local/lib/go/src/runtime/proc.go:2960
	_g_.m.locks--
 806f6e4:	8b 44 24 24          	mov    0x24(%esp),%eax
/usr/local/lib/go/src/runtime/proc.go:2915
	memclrNoHeapPointers(unsafe.Pointer(&newg.sched), unsafe.Sizeof(newg.sched))
 806f6e8:	eb 8f                	jmp    806f679 <runtime.newproc1+0x3d9>
/usr/local/lib/go/src/runtime/proc.go:2960
	_g_.m.locks--
 806f6ea:	8b 44 24 24          	mov    0x24(%esp),%eax
/usr/local/lib/go/src/runtime/proc.go:2915
	memclrNoHeapPointers(unsafe.Pointer(&newg.sched), unsafe.Sizeof(newg.sched))
 806f6ee:	eb 89                	jmp    806f679 <runtime.newproc1+0x3d9>
/usr/local/lib/go/src/runtime/proc.go:2885
		throw("newproc1: new g is not Gdead")
 806f6f0:	8d 05 a0 07 0a 08    	lea    0x80a07a0,%eax
 806f6f6:	89 04 24             	mov    %eax,(%esp)
 806f6f9:	c7 44 24 04 1c 00 00 	movl   $0x1c,0x4(%esp)
 806f700:	00 
 806f701:	e8 8a 82 ff ff       	call   8067990 <runtime.throw>
 806f706:	0f 0b                	ud2    
/usr/local/lib/go/src/runtime/proc.go:2881
		throw("newproc1: newg missing stack")
 806f708:	8d 05 bc 07 0a 08    	lea    0x80a07bc,%eax
 806f70e:	89 04 24             	mov    %eax,(%esp)
 806f711:	c7 44 24 04 1c 00 00 	movl   $0x1c,0x4(%esp)
 806f718:	00 
 806f719:	e8 72 82 ff ff       	call   8067990 <runtime.throw>
 806f71e:	0f 0b                	ud2    
/usr/local/lib/go/src/runtime/proc.go:2875
		newg = malg(_StackMin)
 806f720:	c7 04 24 00 08 00 00 	movl   $0x800,(%esp)
 806f727:	e8 54 fa ff ff       	call   806f180 <runtime.malg>
 806f72c:	8b 44 24 04          	mov    0x4(%esp),%eax
 806f730:	89 44 24 1c          	mov    %eax,0x1c(%esp)
/usr/local/lib/go/src/runtime/proc.go:2876
		casgstatus(newg, _Gidle, _Gdead)
 806f734:	89 04 24             	mov    %eax,(%esp)
 806f737:	c7 44 24 04 00 00 00 	movl   $0x0,0x4(%esp)
 806f73e:	00 
 806f73f:	c7 44 24 08 06 00 00 	movl   $0x6,0x8(%esp)
 806f746:	00 
 806f747:	e8 b4 b3 ff ff       	call   806ab00 <runtime.casgstatus>
/usr/local/lib/go/src/runtime/proc.go:2877
		newg.gcRescan = -1
 806f74c:	8b 44 24 1c          	mov    0x1c(%esp),%eax
 806f750:	c7 80 d8 00 00 00 ff 	movl   $0xffffffff,0xd8(%eax)
 806f757:	ff ff ff 
/usr/local/lib/go/src/runtime/proc.go:2878
		allgadd(newg) // publishes with a g->status of Gdead so GC scanner doesn't look at uninitialized stack.
 806f75a:	89 04 24             	mov    %eax,(%esp)
 806f75d:	e8 ae a4 ff ff       	call   8069c10 <runtime.allgadd>
/usr/local/lib/go/src/runtime/proc.go:2880
	if newg.stack.hi == 0 {
 806f762:	8b 44 24 1c          	mov    0x1c(%esp),%eax
 806f766:	e9 b2 fb ff ff       	jmp    806f31d <runtime.newproc1+0x7d>
/usr/local/lib/go/src/runtime/proc.go:2869
		throw("newproc: function arguments too large for new goroutine")
 806f76b:	8d 05 35 22 0a 08    	lea    0x80a2235,%eax
 806f771:	89 04 24             	mov    %eax,(%esp)
 806f774:	c7 44 24 04 37 00 00 	movl   $0x37,0x4(%esp)
 806f77b:	00 
 806f77c:	e8 0f 82 ff ff       	call   8067990 <runtime.throw>
 806f781:	0f 0b                	ud2    
/usr/local/lib/go/src/runtime/proc.go:2857
		_g_.m.throwing = -1 // do not dump full stacks
 806f783:	8b 40 18             	mov    0x18(%eax),%eax
 806f786:	c7 40 6c ff ff ff ff 	movl   $0xffffffff,0x6c(%eax)
/usr/local/lib/go/src/runtime/proc.go:2858
		throw("go of nil func value")
 806f78d:	8d 05 99 f7 09 08    	lea    0x809f799,%eax
 806f793:	89 04 24             	mov    %eax,(%esp)
 806f796:	c7 44 24 04 14 00 00 	movl   $0x14,0x4(%esp)
 806f79d:	00 
 806f79e:	e8 ed 81 ff ff       	call   8067990 <runtime.throw>
 806f7a3:	0f 0b                	ud2    
/usr/local/lib/go/src/runtime/proc.go:2853
func newproc1(fn *funcval, argp *uint8, narg int32, nret int32, callerpc uintptr) *g {
 806f7a5:	e8 86 6b 01 00       	call   8086330 <runtime.morestack_noctxt>
 806f7aa:	e9 f1 fa ff ff       	jmp    806f2a0 <runtime.newproc1>
 806f7af:	cc                   	int3   

0806f7b0 <runtime.gfput>:
runtime.gfput():
/usr/local/lib/go/src/runtime/proc.go:2969
}










//========================================= casgstatus=======






0806ab00 <runtime.casgstatus>:
runtime.casgstatus():
/usr/local/lib/go/src/runtime/proc.go:749
// If asked to move to or from a Gscanstatus this will throw. Use the castogscanstatus
// and casfrom_Gscanstatus instead.
// casgstatus will loop if the g->atomicstatus is in a Gscan status until the routine that
// put it in the Gscan state is finished.
//go:nosplit
func casgstatus(gp *g, oldval, newval uint32) {
 806ab00:	83 ec 38             	sub    $0x38,%esp
/usr/local/lib/go/src/runtime/proc.go:750
	if (oldval&_Gscan != 0) || (newval&_Gscan != 0) || oldval == newval {
 806ab03:	8b 44 24 40          	mov    0x40(%esp),%eax
 806ab07:	a9 00 10 00 00       	test   $0x1000,%eax
 806ab0c:	0f 84 b2 02 00 00    	je     806adc4 <runtime.casgstatus+0x2c4>
/usr/local/lib/go/src/runtime/proc.go:751
		systemstack(func() {
 806ab12:	c7 44 24 24 00 00 00 	movl   $0x0,0x24(%esp)
 806ab19:	00 
 806ab1a:	8d 0d 40 55 08 08    	lea    0x8085540,%ecx
 806ab20:	89 4c 24 24          	mov    %ecx,0x24(%esp)
 806ab24:	89 44 24 28          	mov    %eax,0x28(%esp)
 806ab28:	8b 4c 24 44          	mov    0x44(%esp),%ecx
 806ab2c:	89 4c 24 2c          	mov    %ecx,0x2c(%esp)
 806ab30:	8d 54 24 24          	lea    0x24(%esp),%edx
/usr/local/lib/go/src/runtime/proc.go:754
			print("runtime: casgstatus: oldval=", hex(oldval), " newval=", hex(newval), "\n")
			throw("casgstatus: bad incoming values")
		})
 806ab34:	89 14 24             	mov    %edx,(%esp)
 806ab37:	e8 d4 b6 01 00       	call   8086210 <runtime.systemstack>
/usr/local/lib/go/src/runtime/proc.go:757
	}

	if oldval == _Grunning && gp.gcscanvalid {
 806ab3c:	8b 44 24 40          	mov    0x40(%esp),%eax
 806ab40:	83 f8 02             	cmp    $0x2,%eax
 806ab43:	0f 85 72 02 00 00    	jne    806adbb <runtime.casgstatus+0x2bb>
 806ab49:	8b 4c 24 3c          	mov    0x3c(%esp),%ecx
 806ab4d:	0f b6 91 84 00 00 00 	movzbl 0x84(%ecx),%edx
 806ab54:	84 d2                	test   %dl,%dl
 806ab56:	0f 85 a2 01 00 00    	jne    806acfe <runtime.casgstatus+0x1fe>
/usr/local/lib/go/src/runtime/proc.go:772
	const yieldDelay = 5 * 1000
	var nextYield int64

	// loop if gp->atomicstatus is in a scan state giving
	// GC time to finish and change the state to oldval.
	for i := 0; !atomic.Cas(&gp.atomicstatus, oldval, newval); i++ {
 806ab5c:	31 d2                	xor    %edx,%edx
/usr/local/lib/go/src/runtime/proc.go:750
	if (oldval&_Gscan != 0) || (newval&_Gscan != 0) || oldval == newval {
 806ab5e:	31 db                	xor    %ebx,%ebx
/usr/local/lib/go/src/runtime/proc.go:795
			for x := 0; x < 10 && gp.atomicstatus != oldval; x++ {
				procyield(1)
			}
		} else {
			osyield()
			nextYield = nanotime() + yieldDelay/2
 806ab60:	31 ed                	xor    %ebp,%ebp
/usr/local/lib/go/src/runtime/proc.go:786
		if i == 0 {
 806ab62:	89 54 24 1c          	mov    %edx,0x1c(%esp)
/usr/local/lib/go/src/runtime/proc.go:789
		if nanotime() < nextYield {
 806ab66:	89 5c 24 14          	mov    %ebx,0x14(%esp)
 806ab6a:	89 6c 24 18          	mov    %ebp,0x18(%esp)
/usr/local/lib/go/src/runtime/proc.go:772
	for i := 0; !atomic.Cas(&gp.atomicstatus, oldval, newval); i++ {
 806ab6e:	84 01                	test   %al,(%ecx)
 806ab70:	8d 71 5c             	lea    0x5c(%ecx),%esi
 806ab73:	89 34 24             	mov    %esi,(%esp)
 806ab76:	89 44 24 04          	mov    %eax,0x4(%esp)
 806ab7a:	8b 74 24 44          	mov    0x44(%esp),%esi
 806ab7e:	89 74 24 08          	mov    %esi,0x8(%esp)
 806ab82:	e8 89 e5 fd ff       	call   8049110 <runtime/internal/atomic.Cas>
 806ab87:	0f b6 44 24 0c       	movzbl 0xc(%esp),%eax
 806ab8c:	84 c0                	test   %al,%al
 806ab8e:	0f 85 2a 01 00 00    	jne    806acbe <runtime.casgstatus+0x1be>
/usr/local/lib/go/src/runtime/proc.go:773
		if oldval == _Gwaiting && gp.atomicstatus == _Grunnable {
 806ab94:	8b 44 24 40          	mov    0x40(%esp),%eax
 806ab98:	83 f8 04             	cmp    $0x4,%eax
 806ab9b:	0f 85 14 01 00 00    	jne    806acb5 <runtime.casgstatus+0x1b5>
 806aba1:	8b 4c 24 3c          	mov    0x3c(%esp),%ecx
 806aba5:	8b 51 5c             	mov    0x5c(%ecx),%edx
 806aba8:	83 fa 01             	cmp    $0x1,%edx
 806abab:	0f 84 e9 00 00 00    	je     806ac9a <runtime.casgstatus+0x19a>
/usr/local/lib/go/src/runtime/proc.go:786
		if i == 0 {
 806abb1:	8b 54 24 1c          	mov    0x1c(%esp),%edx
 806abb5:	85 d2                	test   %edx,%edx
 806abb7:	0f 84 b6 00 00 00    	je     806ac73 <runtime.casgstatus+0x173>
/usr/local/lib/go/src/runtime/proc.go:789
		if nanotime() < nextYield {
 806abbd:	8b 5c 24 18          	mov    0x18(%esp),%ebx
 806abc1:	8b 6c 24 14          	mov    0x14(%esp),%ebp
 806abc5:	89 5c 24 18          	mov    %ebx,0x18(%esp)
 806abc9:	89 6c 24 14          	mov    %ebp,0x14(%esp)
 806abcd:	e8 de dd 01 00       	call   80889b0 <runtime.nanotime>
 806abd2:	8b 44 24 04          	mov    0x4(%esp),%eax
 806abd6:	8b 0c 24             	mov    (%esp),%ecx
 806abd9:	8b 54 24 18          	mov    0x18(%esp),%edx
 806abdd:	39 d0                	cmp    %edx,%eax
 806abdf:	0f 94 c3             	sete   %bl
 806abe2:	8b 6c 24 14          	mov    0x14(%esp),%ebp
 806abe6:	39 e9                	cmp    %ebp,%ecx
 806abe8:	0f 92 c1             	setb   %cl
 806abeb:	21 cb                	and    %ecx,%ebx
 806abed:	39 d0                	cmp    %edx,%eax
 806abef:	0f 9c c0             	setl   %al
 806abf2:	09 d8                	or     %ebx,%eax
 806abf4:	84 c0                	test   %al,%al
 806abf6:	74 56                	je     806ac4e <runtime.casgstatus+0x14e>
/usr/local/lib/go/src/runtime/proc.go:772
	for i := 0; !atomic.Cas(&gp.atomicstatus, oldval, newval); i++ {
 806abf8:	31 c0                	xor    %eax,%eax
/usr/local/lib/go/src/runtime/proc.go:790
			for x := 0; x < 10 && gp.atomicstatus != oldval; x++ {
 806abfa:	89 44 24 10          	mov    %eax,0x10(%esp)
 806abfe:	83 f8 0a             	cmp    $0xa,%eax
 806ac01:	7d 31                	jge    806ac34 <runtime.casgstatus+0x134>
 806ac03:	8b 4c 24 3c          	mov    0x3c(%esp),%ecx
 806ac07:	8b 59 5c             	mov    0x5c(%ecx),%ebx
 806ac0a:	8b 74 24 40          	mov    0x40(%esp),%esi
 806ac0e:	39 de                	cmp    %ebx,%esi
 806ac10:	74 2a                	je     806ac3c <runtime.casgstatus+0x13c>
/usr/local/lib/go/src/runtime/proc.go:791
				procyield(1)
 806ac12:	c7 04 24 01 00 00 00 	movl   $0x1,(%esp)
 806ac19:	e8 e2 c8 01 00       	call   8087500 <runtime.procyield>
/usr/local/lib/go/src/runtime/proc.go:790
			for x := 0; x < 10 && gp.atomicstatus != oldval; x++ {
 806ac1e:	8b 44 24 10          	mov    0x10(%esp),%eax
 806ac22:	40                   	inc    %eax
/usr/local/lib/go/src/runtime/proc.go:789
		if nanotime() < nextYield {
 806ac23:	8b 54 24 18          	mov    0x18(%esp),%edx
 806ac27:	8b 6c 24 14          	mov    0x14(%esp),%ebp
/usr/local/lib/go/src/runtime/proc.go:790
			for x := 0; x < 10 && gp.atomicstatus != oldval; x++ {
 806ac2b:	89 44 24 10          	mov    %eax,0x10(%esp)
 806ac2f:	83 f8 0a             	cmp    $0xa,%eax
 806ac32:	7c cf                	jl     806ac03 <runtime.casgstatus+0x103>
/usr/local/lib/go/src/runtime/proc.go:772
	for i := 0; !atomic.Cas(&gp.atomicstatus, oldval, newval); i++ {
 806ac34:	8b 4c 24 3c          	mov    0x3c(%esp),%ecx
 806ac38:	8b 74 24 40          	mov    0x40(%esp),%esi
 806ac3c:	8b 7c 24 1c          	mov    0x1c(%esp),%edi
 806ac40:	47                   	inc    %edi
 806ac41:	89 f0                	mov    %esi,%eax
/usr/local/lib/go/src/runtime/proc.go:789
		if nanotime() < nextYield {
 806ac43:	89 eb                	mov    %ebp,%ebx
 806ac45:	89 d5                	mov    %edx,%ebp
/usr/local/lib/go/src/runtime/proc.go:786
		if i == 0 {
 806ac47:	89 fa                	mov    %edi,%edx
 806ac49:	e9 14 ff ff ff       	jmp    806ab62 <runtime.casgstatus+0x62>
/usr/local/lib/go/src/runtime/proc.go:794
			osyield()
 806ac4e:	e8 7d e0 01 00       	call   8088cd0 <runtime.osyield>
/usr/local/lib/go/src/runtime/proc.go:795
			nextYield = nanotime() + yieldDelay/2
 806ac53:	e8 58 dd 01 00       	call   80889b0 <runtime.nanotime>
 806ac58:	8b 04 24             	mov    (%esp),%eax
 806ac5b:	05 c4 09 00 00       	add    $0x9c4,%eax
 806ac60:	8b 54 24 04          	mov    0x4(%esp),%edx
 806ac64:	83 d2 00             	adc    $0x0,%edx
/usr/local/lib/go/src/runtime/proc.go:772
	for i := 0; !atomic.Cas(&gp.atomicstatus, oldval, newval); i++ {
 806ac67:	8b 4c 24 3c          	mov    0x3c(%esp),%ecx
 806ac6b:	8b 74 24 40          	mov    0x40(%esp),%esi
/usr/local/lib/go/src/runtime/proc.go:789
		if nanotime() < nextYield {
 806ac6f:	89 c5                	mov    %eax,%ebp
/usr/local/lib/go/src/runtime/proc.go:772
	for i := 0; !atomic.Cas(&gp.atomicstatus, oldval, newval); i++ {
 806ac71:	eb c9                	jmp    806ac3c <runtime.casgstatus+0x13c>
/usr/local/lib/go/src/runtime/proc.go:787
			nextYield = nanotime() + yieldDelay
 806ac73:	e8 38 dd 01 00       	call   80889b0 <runtime.nanotime>
 806ac78:	8b 04 24             	mov    (%esp),%eax
 806ac7b:	05 88 13 00 00       	add    $0x1388,%eax
 806ac80:	8b 5c 24 04          	mov    0x4(%esp),%ebx
 806ac84:	83 d3 00             	adc    $0x0,%ebx
/usr/local/lib/go/src/runtime/proc.go:790
			for x := 0; x < 10 && gp.atomicstatus != oldval; x++ {
 806ac87:	8b 4c 24 3c          	mov    0x3c(%esp),%ecx
/usr/local/lib/go/src/runtime/proc.go:772
	for i := 0; !atomic.Cas(&gp.atomicstatus, oldval, newval); i++ {
 806ac8b:	8b 54 24 1c          	mov    0x1c(%esp),%edx
/usr/local/lib/go/src/runtime/proc.go:789
		if nanotime() < nextYield {
 806ac8f:	89 c5                	mov    %eax,%ebp
/usr/local/lib/go/src/runtime/proc.go:790
			for x := 0; x < 10 && gp.atomicstatus != oldval; x++ {
 806ac91:	8b 44 24 40          	mov    0x40(%esp),%eax
/usr/local/lib/go/src/runtime/proc.go:789
		if nanotime() < nextYield {
 806ac95:	e9 2b ff ff ff       	jmp    806abc5 <runtime.casgstatus+0xc5>
/usr/local/lib/go/src/runtime/proc.go:776
			})
 806ac9a:	8d 15 c8 24 0a 08    	lea    0x80a24c8,%edx
 806aca0:	89 14 24             	mov    %edx,(%esp)
 806aca3:	e8 68 b5 01 00       	call   8086210 <runtime.systemstack>
/usr/local/lib/go/src/runtime/proc.go:790
			for x := 0; x < 10 && gp.atomicstatus != oldval; x++ {
 806aca8:	8b 44 24 40          	mov    0x40(%esp),%eax
 806acac:	8b 4c 24 3c          	mov    0x3c(%esp),%ecx
/usr/local/lib/go/src/runtime/proc.go:786
		if i == 0 {
 806acb0:	e9 fc fe ff ff       	jmp    806abb1 <runtime.casgstatus+0xb1>
/usr/local/lib/go/src/runtime/proc.go:790
			for x := 0; x < 10 && gp.atomicstatus != oldval; x++ {
 806acb5:	8b 4c 24 3c          	mov    0x3c(%esp),%ecx
/usr/local/lib/go/src/runtime/proc.go:786
		if i == 0 {
 806acb9:	e9 f3 fe ff ff       	jmp    806abb1 <runtime.casgstatus+0xb1>
/usr/local/lib/go/src/runtime/proc.go:798
		}
	}
	if newval == _Grunning && gp.gcscanvalid {
 806acbe:	8b 44 24 44          	mov    0x44(%esp),%eax
 806acc2:	83 f8 02             	cmp    $0x2,%eax
 806acc5:	75 0f                	jne    806acd6 <runtime.casgstatus+0x1d6>
 806acc7:	8b 44 24 3c          	mov    0x3c(%esp),%eax
 806accb:	0f b6 88 84 00 00 00 	movzbl 0x84(%eax),%ecx
 806acd2:	84 c9                	test   %cl,%cl
 806acd4:	75 04                	jne    806acda <runtime.casgstatus+0x1da>
/usr/local/lib/go/src/runtime/proc.go:802
		// Run queueRescan on the system stack so it has more space.
		systemstack(func() { queueRescan(gp) })
	}
}
 806acd6:	83 c4 38             	add    $0x38,%esp
 806acd9:	c3                   	ret    
/usr/local/lib/go/src/runtime/proc.go:800
		systemstack(func() { queueRescan(gp) })
 806acda:	c7 44 24 30 00 00 00 	movl   $0x0,0x30(%esp)
 806ace1:	00 
 806ace2:	8d 0d 40 56 08 08    	lea    0x8085640,%ecx
 806ace8:	89 4c 24 30          	mov    %ecx,0x30(%esp)
 806acec:	89 44 24 34          	mov    %eax,0x34(%esp)
 806acf0:	8d 44 24 30          	lea    0x30(%esp),%eax
 806acf4:	89 04 24             	mov    %eax,(%esp)
 806acf7:	e8 14 b5 01 00       	call   8086210 <runtime.systemstack>
/usr/local/lib/go/src/runtime/proc.go:802
}
 806acfc:	eb d8                	jmp    806acd6 <runtime.casgstatus+0x1d6>
/usr/local/lib/go/src/runtime/proc.go:762
		print("runtime: casgstatus ", hex(oldval), "->", hex(newval), " gp.status=", hex(gp.atomicstatus), " gp.gcscanvalid=true\n")
 806acfe:	8b 49 5c             	mov    0x5c(%ecx),%ecx
 806ad01:	89 4c 24 20          	mov    %ecx,0x20(%esp)
 806ad05:	e8 46 d5 ff ff       	call   8068250 <runtime.printlock>
 806ad0a:	8d 05 89 f8 09 08    	lea    0x809f889,%eax
 806ad10:	89 04 24             	mov    %eax,(%esp)
 806ad13:	c7 44 24 04 14 00 00 	movl   $0x14,0x4(%esp)
 806ad1a:	00 
 806ad1b:	e8 a0 dd ff ff       	call   8068ac0 <runtime.printstring>
 806ad20:	8b 44 24 40          	mov    0x40(%esp),%eax
 806ad24:	89 04 24             	mov    %eax,(%esp)
 806ad27:	c7 44 24 04 00 00 00 	movl   $0x0,0x4(%esp)
 806ad2e:	00 
 806ad2f:	e8 5c dc ff ff       	call   8068990 <runtime.printhex>
 806ad34:	8d 05 ef e2 09 08    	lea    0x809e2ef,%eax
 806ad3a:	89 04 24             	mov    %eax,(%esp)
 806ad3d:	c7 44 24 04 02 00 00 	movl   $0x2,0x4(%esp)
 806ad44:	00 
 806ad45:	e8 76 dd ff ff       	call   8068ac0 <runtime.printstring>
 806ad4a:	8b 44 24 44          	mov    0x44(%esp),%eax
 806ad4e:	89 04 24             	mov    %eax,(%esp)
 806ad51:	c7 44 24 04 00 00 00 	movl   $0x0,0x4(%esp)
 806ad58:	00 
 806ad59:	e8 32 dc ff ff       	call   8068990 <runtime.printhex>
 806ad5e:	8d 05 14 ea 09 08    	lea    0x809ea14,%eax
 806ad64:	89 04 24             	mov    %eax,(%esp)
 806ad67:	c7 44 24 04 0b 00 00 	movl   $0xb,0x4(%esp)
 806ad6e:	00 
 806ad6f:	e8 4c dd ff ff       	call   8068ac0 <runtime.printstring>
 806ad74:	8b 44 24 20          	mov    0x20(%esp),%eax
 806ad78:	89 04 24             	mov    %eax,(%esp)
 806ad7b:	c7 44 24 04 00 00 00 	movl   $0x0,0x4(%esp)
 806ad82:	00 
 806ad83:	e8 08 dc ff ff       	call   8068990 <runtime.printhex>
 806ad88:	8d 05 ed f8 09 08    	lea    0x809f8ed,%eax
 806ad8e:	89 04 24             	mov    %eax,(%esp)
 806ad91:	c7 44 24 04 15 00 00 	movl   $0x15,0x4(%esp)
 806ad98:	00 
 806ad99:	e8 22 dd ff ff       	call   8068ac0 <runtime.printstring>
 806ad9e:	e8 1d d5 ff ff       	call   80682c0 <runtime.printunlock>
/usr/local/lib/go/src/runtime/proc.go:763
		throw("casgstatus")
 806ada3:	8d 05 72 e9 09 08    	lea    0x809e972,%eax
 806ada9:	89 04 24             	mov    %eax,(%esp)
 806adac:	c7 44 24 04 0a 00 00 	movl   $0xa,0x4(%esp)
 806adb3:	00 
 806adb4:	e8 d7 cb ff ff       	call   8067990 <runtime.throw>
 806adb9:	0f 0b                	ud2    
/usr/local/lib/go/src/runtime/proc.go:772
	for i := 0; !atomic.Cas(&gp.atomicstatus, oldval, newval); i++ {
 806adbb:	8b 4c 24 3c          	mov    0x3c(%esp),%ecx
 806adbf:	e9 98 fd ff ff       	jmp    806ab5c <runtime.casgstatus+0x5c>
/usr/local/lib/go/src/runtime/proc.go:750
	if (oldval&_Gscan != 0) || (newval&_Gscan != 0) || oldval == newval {
 806adc4:	8b 4c 24 44          	mov    0x44(%esp),%ecx
 806adc8:	f7 c1 00 10 00 00    	test   $0x1000,%ecx
 806adce:	0f 85 3e fd ff ff    	jne    806ab12 <runtime.casgstatus+0x12>
 806add4:	39 c8                	cmp    %ecx,%eax
 806add6:	0f 85 60 fd ff ff    	jne    806ab3c <runtime.casgstatus+0x3c>
/usr/local/lib/go/src/runtime/proc.go:751
		systemstack(func() {
 806addc:	e9 31 fd ff ff       	jmp    806ab12 <runtime.casgstatus+0x12>
 806ade1:	cc                   	int3   
 806ade2:	cc                   	int3   
 806ade3:	cc                   	int3   
 806ade4:	cc                   	int3   
 806ade5:	cc                   	int3   
 806ade6:	cc                   	int3   
 806ade7:	cc                   	int3   
 806ade8:	cc                   	int3   
 806ade9:	cc                   	int3   
 806adea:	cc                   	int3   
 806adeb:	cc                   	int3   
 806adec:	cc                   	int3   
 806aded:	cc                   	int3   
 806adee:	cc                   	int3   
 806adef:	cc                   	int3   



//========================================

08049110 <runtime/internal/atomic.Cas>:
runtime/internal/atomic.Cas():
/usr/local/lib/go/src/runtime/internal/atomic/asm_386.s:15
//		*val = new;
//		return 1;
//	}else
//		return 0;
TEXT runtime∕internal∕atomic·Cas(SB), NOSPLIT, $0-13
	MOVL	ptr+0(FP), BX
 8049110:	8b 5c 24 04          	mov    0x4(%esp),%ebx
/usr/local/lib/go/src/runtime/internal/atomic/asm_386.s:16
	MOVL	old+4(FP), AX
 8049114:	8b 44 24 08          	mov    0x8(%esp),%eax
/usr/local/lib/go/src/runtime/internal/atomic/asm_386.s:17
	MOVL	new+8(FP), CX
 8049118:	8b 4c 24 0c          	mov    0xc(%esp),%ecx
/usr/local/lib/go/src/runtime/internal/atomic/asm_386.s:18
	LOCK
 804911c:	f0 0f b1 0b          	lock cmpxchg %ecx,(%ebx)
/usr/local/lib/go/src/runtime/internal/atomic/asm_386.s:20
	CMPXCHGL	CX, 0(BX)
	SETEQ	ret+12(FP)
 8049120:	0f 94 44 24 10       	sete   0x10(%esp)
/usr/local/lib/go/src/runtime/internal/atomic/asm_386.s:21
	RET
 8049125:	c3                   	ret    
 8049126:	cc                   	int3   
 8049127:	cc                   	int3   
 8049128:	cc                   	int3   
 8049129:	cc                   	int3   
 804912a:	cc                   	int3   
 804912b:	cc                   	int3   
 804912c:	cc                   	int3   
 804912d:	cc                   	int3   
 804912e:	cc                   	int3   
 804912f:	cc                   	int3   

~~~

