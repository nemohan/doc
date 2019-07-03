# GO Runtime 分析之runtime.morestack



### 版本

1.8.3

###  runtime.morestack  asm_386.s

~~~assembly

void morestack(){
    
}


080862a0 <runtime.morestack>:
runtime.morestack():
/usr/local/lib/go/src/runtime/asm_386.s:368
// the top of a stack (for example, morestack calling newstack
// calling the scheduler calling newm calling gc), so we must
// record an argument size. For that purpose, it has no arguments.
TEXT runtime·morestack(SB),NOSPLIT,$0-0
	// Cannot grow scheduler stack (m->g0).
	get_tls(CX)
 80862a0:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
/usr/local/lib/go/src/runtime/asm_386.s:369
	MOVL	g(CX), BX
 80862a7:	8b 99 fc ff ff ff    	mov    -0x4(%ecx),%ebx  
 //######################## ebx= &g0    ebx 为g0地址
 
 
/usr/local/lib/go/src/runtime/asm_386.s:370
	MOVL	g_m(BX), BX
 80862ad:	8b 5b 18             	mov    0x18(%ebx),%ebx
 // ############### ebx= g.m0
 
 
/usr/local/lib/go/src/runtime/asm_386.s:371
	MOVL	m_g0(BX), SI
 80862b0:	8b 33                	mov    (%ebx),%esi
 // ######### esi =  m.g0
 
/usr/local/lib/go/src/runtime/asm_386.s:372
	CMPL	g(CX), SI
 80862b2:	39 b1 fc ff ff ff    	cmp    %esi,-0x4(%ecx)
 //############前面已经将 m.g0 绑定到tls的g0 ，导致调用  runtime.badmorestackg0
 // ############# m.g0 是否等于 tls 里的g0  ??????????????????????????
 
/usr/local/lib/go/src/runtime/asm_386.s:373
	JNE	3(PC)
 80862b8:	75 07                	jne    80862c1 <runtime.morestack+0x21>
/usr/local/lib/go/src/runtime/asm_386.s:374
	CALL	runtime·badmorestackg0(SB)
 80862ba:	e8 d1 38 fe ff       	call   8069b90 <runtime.badmorestackg0>
/usr/local/lib/go/src/runtime/asm_386.s:375
	INT	$3
 80862bf:	cd 03                	int    $0x3
/usr/local/lib/go/src/runtime/asm_386.s:378


//################ m.g0 != tls 的g0跳转到这
	// Cannot grow signal stack.
	MOVL	m_gsignal(BX), SI
 80862c1:	8b 73 2c             	mov    0x2c(%ebx),%esi
 // ############  esi = m.gsignal    gsignal 和g0是同一类型
 
 
/usr/local/lib/go/src/runtime/asm_386.s:379
	CMPL	g(CX), SI
 80862c4:	39 b1 fc ff ff ff    	cmp    %esi,-0x4(%ecx) 
 //############    m.gsiganl 是否等于 g0 , 刚开始 m.gsingal是个指向g的空指针
 
 
 
/usr/local/lib/go/src/runtime/asm_386.s:380
	JNE	3(PC)
 80862ca:	75 07                	jne    80862d3 <runtime.morestack+0x33>
/usr/local/lib/go/src/runtime/asm_386.s:381
	CALL	runtime·badmorestackgsignal(SB)
 80862cc:	e8 ef 38 fe ff       	call   8069bc0 <runtime.badmorestackgsignal>
/usr/local/lib/go/src/runtime/asm_386.s:382
	INT	$3
 80862d1:	cd 03                	int    $0x3
 
 |
 |
 stack 结构:
 ret1
 ret2
 xxxxxxxxxxxxxxxxxxxxx 跳转到这
/usr/local/lib/go/src/runtime/asm_386.s:386

	// Called from f.
	// Set m->morebuf to f's caller.
	MOVL	4(SP), DI	// f's caller's PC
 80862d3:	8b 7c 24 04          	mov    0x4(%esp),%edi
 // ############## edi = （一个返回地址 ret1 )
 
 
/usr/local/lib/go/src/runtime/asm_386.s:387
	MOVL	DI, (m_morebuf+gobuf_pc)(BX)
 80862d7:	89 7b 08             	mov    %edi,0x8(%ebx)
 // ########### m.morebuf.pc = edi (一个返回地址 ret1) ?????
 
 
/usr/local/lib/go/src/runtime/asm_386.s:388
	LEAL	8(SP), CX	// f's caller's SP
 80862da:	8d 4c 24 08          	lea    0x8(%esp),%ecx
 
 
 
/usr/local/lib/go/src/runtime/asm_386.s:389
	MOVL	CX, (m_morebuf+gobuf_sp)(BX)
 80862de:	89 4b 04             	mov    %ecx,0x4(%ebx)
// ############# m.morebuf.sp = ecx  ????????

 
/usr/local/lib/go/src/runtime/asm_386.s:390
	get_tls(CX)
 80862e1:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
/usr/local/lib/go/src/runtime/asm_386.s:391
	MOVL	g(CX), SI
 80862e8:	8b b1 fc ff ff ff    	mov    -0x4(%ecx),%esi
 // ########## esi = g0
 
/usr/local/lib/go/src/runtime/asm_386.s:392
	MOVL	SI, (m_morebuf+gobuf_g)(BX)
 80862ee:	89 73 0c             	mov    %esi,0xc(%ebx)
/usr/local/lib/go/src/runtime/asm_386.s:395
// ########### m.morebuf.g = g0

	// Set g->sched to context in f.
	MOVL	0(SP), AX	// f's PC
 80862f1:	8b 04 24             	mov    (%esp),%eax
  // ############ eax = *(esp)  返回地址 ret2
 
/usr/local/lib/go/src/runtime/asm_386.s:396
	MOVL	AX, (g_sched+gobuf_pc)(SI)
 80862f4:	89 46 24             	mov    %eax,0x24(%esi)
 //############## g0.sched.pc = eax
 
/usr/local/lib/go/src/runtime/asm_386.s:397
	MOVL	SI, (g_sched+gobuf_g)(SI)
 80862f7:	89 76 28             	mov    %esi,0x28(%esi)
 // ########### g0.sched.g = g0
 
/usr/local/lib/go/src/runtime/asm_386.s:398
	LEAL	4(SP), AX	// f's SP
 80862fa:	8d 44 24 04          	lea    0x4(%esp),%eax
 // ########### eax = 第二个返回地址
 
/usr/local/lib/go/src/runtime/asm_386.s:399
	MOVL	AX, (g_sched+gobuf_sp)(SI)
 80862fe:	89 46 20             	mov    %eax,0x20(%esi)
 // ########## g0.sched.sp = eax
 
 {
     m.morebuf.g = g0
     g0.sched.pc = ret2
     g0.sched.g = g0
   
 }
 
 
/usr/local/lib/go/src/runtime/asm_386.s:403
	// newstack will fill gobuf.ctxt.

	// Call newstack on m->g0's stack.
	MOVL	m_g0(BX), BP
 8086301:	8b 2b                	mov    (%ebx),%ebp
 // ########### ebp = m.g0
 
 
/usr/local/lib/go/src/runtime/asm_386.s:404
	MOVL	BP, g(CX)
 8086303:	89 a9 fc ff ff ff    	mov    %ebp,-0x4(%ecx)
 //################  ecx= m.g0  ??????????????????????????????
 
/usr/local/lib/go/src/runtime/asm_386.s:405
	MOVL	(g_sched+gobuf_sp)(BP), AX
 8086309:	8b 45 20             	mov    0x20(%ebp),%eax
 //############### eax = m.g0.sched.sp 
 
/usr/local/lib/go/src/runtime/asm_386.s:406
	MOVL	-4(AX), BX	// fault if CALL would, before smashing SP
 808630c:	8b 58 fc             	mov    -0x4(%eax),%ebx
 //################ ebx = 
 
/usr/local/lib/go/src/runtime/asm_386.s:407
	MOVL	AX, SP
 808630f:	89 c4                	mov    %eax,%esp
 // ################# 
 
/usr/local/lib/go/src/runtime/asm_386.s:408
	PUSHL	DX	// ctxt argument
 8086311:	52                   	push   %edx
 // #################   edx的值 为0
 
 
/usr/local/lib/go/src/runtime/asm_386.s:409
	CALL	runtime·newstack(SB)
 8086312:	e8 f9 2c ff ff       	call   8079010 <runtime.newstack>
 
 
/usr/local/lib/go/src/runtime/asm_386.s:410
	MOVL	$0, 0x1003	// crash if newstack returns
 8086317:	c7 05 03 10 00 00 00 	movl   $0x0,0x1003
 808631e:	00 00 00 
 
/usr/local/lib/go/src/runtime/asm_386.s:411
	POPL	DX	// keep balance check happy
 8086321:	5a                   	pop    %edx
/usr/local/lib/go/src/runtime/asm_386.s:412
	RET
	
	
	
	

~~~

~~~go
// Called from runtime·morestack when more stack is needed.
// Allocate larger stack and relocate to new stack.
// Stack growth is multiplicative, for constant amortized cost.
//
// g->atomicstatus will be Grunning or Gscanrunning upon entry.
// If the GC is trying to stop this g then it will set preemptscan to true.
//
// ctxt is the value of the context register on morestack. newstack
// will write it to g.sched.ctxt.
func newstack(ctxt unsafe.Pointer) {
	thisg := getg()
	// TODO: double check all gp. shouldn't be getg().
	if thisg.m.morebuf.g.ptr().stackguard0 == stackFork {
		throw("stack growth after fork")
	}
	if thisg.m.morebuf.g.ptr() != thisg.m.curg {
		print("runtime: newstack called from g=", hex(thisg.m.morebuf.g), "\n"+"\tm=", thisg.m, " m->curg=", thisg.m.curg, " m->g0=", thisg.m.g0, " m->gsignal=", thisg.m.gsignal, "\n")
		morebuf := thisg.m.morebuf
		traceback(morebuf.pc, morebuf.sp, morebuf.lr, morebuf.g.ptr())
		throw("runtime: wrong goroutine in newstack")
	}

	gp := thisg.m.curg
	// Write ctxt to gp.sched. We do this here instead of in
	// morestack so it has the necessary write barrier.
	gp.sched.ctxt = ctxt

	if thisg.m.curg.throwsplit {
		// Update syscallsp, syscallpc in case traceback uses them.
		morebuf := thisg.m.morebuf
		gp.syscallsp = morebuf.sp
		gp.syscallpc = morebuf.pc
		print("runtime: newstack sp=", hex(gp.sched.sp), " stack=[", hex(gp.stack.lo), ", ", hex(gp.stack.hi), "]\n",
			"\tmorebuf={pc:", hex(morebuf.pc), " sp:", hex(morebuf.sp), " lr:", hex(morebuf.lr), "}\n",
			"\tsched={pc:", hex(gp.sched.pc), " sp:", hex(gp.sched.sp), " lr:", hex(gp.sched.lr), " ctxt:", gp.sched.ctxt, "}\n")

		traceback(morebuf.pc, morebuf.sp, morebuf.lr, gp)
		throw("runtime: stack split at bad time")
	}

	morebuf := thisg.m.morebuf
	thisg.m.morebuf.pc = 0
	thisg.m.morebuf.lr = 0
	thisg.m.morebuf.sp = 0
	thisg.m.morebuf.g = 0

	// NOTE: stackguard0 may change underfoot, if another thread
	// is about to try to preempt gp. Read it just once and use that same
	// value now and below.
	preempt := atomic.Loaduintptr(&gp.stackguard0) == stackPreempt

	// Be conservative about where we preempt.
	// We are interested in preempting user Go code, not runtime code.
	// If we're holding locks, mallocing, or preemption is disabled, don't
	// preempt.
	// This check is very early in newstack so that even the status change
	// from Grunning to Gwaiting and back doesn't happen in this case.
	// That status change by itself can be viewed as a small preemption,
	// because the GC might change Gwaiting to Gscanwaiting, and then
	// this goroutine has to wait for the GC to finish before continuing.
	// If the GC is in some way dependent on this goroutine (for example,
	// it needs a lock held by the goroutine), that small preemption turns
	// into a real deadlock.
	if preempt {
		if thisg.m.locks != 0 || thisg.m.mallocing != 0 || thisg.m.preemptoff != "" || thisg.m.p.ptr().status != _Prunning {
			// Let the goroutine keep running for now.
			// gp->preempt is set, so it will be preempted next time.
			gp.stackguard0 = gp.stack.lo + _StackGuard
			gogo(&gp.sched) // never return
		}
	}

	if gp.stack.lo == 0 {
		throw("missing stack in newstack")
	}
	sp := gp.sched.sp
	if sys.ArchFamily == sys.AMD64 || sys.ArchFamily == sys.I386 {
		// The call to morestack cost a word.
		sp -= sys.PtrSize
	}
	if stackDebug >= 1 || sp < gp.stack.lo {
		print("runtime: newstack sp=", hex(sp), " stack=[", hex(gp.stack.lo), ", ", hex(gp.stack.hi), "]\n",
			"\tmorebuf={pc:", hex(morebuf.pc), " sp:", hex(morebuf.sp), " lr:", hex(morebuf.lr), "}\n",
			"\tsched={pc:", hex(gp.sched.pc), " sp:", hex(gp.sched.sp), " lr:", hex(gp.sched.lr), " ctxt:", gp.sched.ctxt, "}\n")
	}
	if sp < gp.stack.lo {
		print("runtime: gp=", gp, ", gp->status=", hex(readgstatus(gp)), "\n ")
		print("runtime: split stack overflow: ", hex(sp), " < ", hex(gp.stack.lo), "\n")
		throw("runtime: split stack overflow")
	}

	if preempt {
		if gp == thisg.m.g0 {
			throw("runtime: preempt g0")
		}
		if thisg.m.p == 0 && thisg.m.locks == 0 {
			throw("runtime: g is running but p is not")
		}
		// Synchronize with scang.
		casgstatus(gp, _Grunning, _Gwaiting)
		if gp.preemptscan {
			for !castogscanstatus(gp, _Gwaiting, _Gscanwaiting) {
				// Likely to be racing with the GC as
				// it sees a _Gwaiting and does the
				// stack scan. If so, gcworkdone will
				// be set and gcphasework will simply
				// return.
			}
			if !gp.gcscandone {
				// gcw is safe because we're on the
				// system stack.
				gcw := &gp.m.p.ptr().gcw
				scanstack(gp, gcw)
				if gcBlackenPromptly {
					gcw.dispose()
				}
				gp.gcscandone = true
			}
			gp.preemptscan = false
			gp.preempt = false
			casfrom_Gscanstatus(gp, _Gscanwaiting, _Gwaiting)
			// This clears gcscanvalid.
			casgstatus(gp, _Gwaiting, _Grunning)
			gp.stackguard0 = gp.stack.lo + _StackGuard
			gogo(&gp.sched) // never return
		}

		// Act like goroutine called runtime.Gosched.
		casgstatus(gp, _Gwaiting, _Grunning)
		gopreempt_m(gp) // never return
	}

	// Allocate a bigger segment and move the stack.
	oldsize := int(gp.stackAlloc)
	newsize := oldsize * 2
	if uintptr(newsize) > maxstacksize {
		print("runtime: goroutine stack exceeds ", maxstacksize, "-byte limit\n")
		throw("stack overflow")
	}

	// The goroutine must be executing in order to call newstack,
	// so it must be Grunning (or Gscanrunning).
	casgstatus(gp, _Grunning, _Gcopystack)

	// The concurrent GC will not scan the stack while we are doing the copy since
	// the gp is in a Gcopystack status.
	copystack(gp, uintptr(newsize), true)
	if stackDebug >= 1 {
		print("stack grow done\n")
	}
	casgstatus(gp, _Gcopystack, _Grunning)
	gogo(&gp.sched)
}

~~~

b