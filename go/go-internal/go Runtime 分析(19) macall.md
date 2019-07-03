# mcall 







~~~assembly
0808e850 <runtime.mcall>:
runtime.mcall():
/usr/lib/golang/src/runtime/asm_386.s:256
// func mcall(fn func(*g))
// Switch to m->g0's stack, call fn(g).
// Fn must never return. It should gogo(&g->sched)
// to keep running g.
TEXT runtime·mcall(SB), NOSPLIT, $0-4
	MOVL	fn+0(FP), DI
 808e850:	8b 7c 24 04          	mov    0x4(%esp),%edi
 // ############ edi = fn
 
 
/usr/lib/golang/src/runtime/asm_386.s:258

	get_tls(DX)
 808e854:	65 8b 15 00 00 00 00 	mov    %gs:0x0,%edx
/usr/lib/golang/src/runtime/asm_386.s:259
	MOVL	g(DX), AX	// save state in g->sched
 808e85b:	8b 82 fc ff ff ff    	mov    -0x4(%edx),%eax
 //############## eax = g
 
/usr/lib/golang/src/runtime/asm_386.s:260
	MOVL	0(SP), BX	// caller's PC
 808e861:	8b 1c 24             	mov    (%esp),%ebx
 // ############## ebx = 返回地址
 
/usr/lib/golang/src/runtime/asm_386.s:261
	MOVL	BX, (g_sched+gobuf_pc)(AX)
 808e864:	89 58 24             	mov    %ebx,0x24(%eax)
 // ############## g.sched.pc = ebx  gobuf 在g中的偏移为0x20
 
 
/usr/lib/golang/src/runtime/asm_386.s:262
	LEAL	fn+0(FP), BX	// caller's SP
 808e867:	8d 5c 24 04          	lea    0x4(%esp),%ebx
 
/usr/lib/golang/src/runtime/asm_386.s:263
	MOVL	BX, (g_sched+gobuf_sp)(AX)
 808e86b:	89 58 20             	mov    %ebx,0x20(%eax)
 // ############## g.sched.sp = ebx
 
 
/usr/lib/golang/src/runtime/asm_386.s:264
	MOVL	AX, (g_sched+gobuf_g)(AX)
 808e86e:	89 40 28             	mov    %eax,0x28(%eax)
 // ############# g.sched.g = g
 
/usr/lib/golang/src/runtime/asm_386.s:267
	// switch to m->g0 & its stack, call fn
	MOVL	g(DX), BX
 808e871:	8b 9a fc ff ff ff    	mov    -0x4(%edx),%ebx
 // ################ ebx =  tls[0]也即g
 
/usr/lib/golang/src/runtime/asm_386.s:268
	MOVL	g_m(BX), BX
 808e877:	8b 5b 18             	mov    0x18(%ebx),%ebx
 //########### ebx= g.m
 
/usr/lib/golang/src/runtime/asm_386.s:269
	MOVL	m_g0(BX), SI
 808e87a:	8b 33                	mov    (%ebx),%esi
 //########### esi = m.g0
 
/usr/lib/golang/src/runtime/asm_386.s:270
	CMPL	SI, AX	// if g == m->g0 call badmcall
 808e87c:	39 c6                	cmp    %eax,%esi
/usr/lib/golang/src/runtime/asm_386.s:271
	JNE	3(PC)
 808e87e:	75 07                	jne    808e887 <runtime.mcall+0x37>
 // ############# g != m->g0, 如果 tls[0] 里面的g0是正在执行de goroutine.
 // ############# 那么m.g0是代表什么???????????????????????
 //############## 从下面的代码来看，是处于待运行状态的goroutine
 
/usr/lib/golang/src/runtime/asm_386.s:272
	MOVL	$runtime·badmcall(SB), AX
 808e880:	b8 10 e0 06 08       	mov    $0x806e010,%eax
/usr/lib/golang/src/runtime/asm_386.s:273
	JMP	AX
 808e885:	ff e0                	jmp    *%eax
 
 
 
 
 //############# g != m->g0 跳到这
/usr/lib/golang/src/runtime/asm_386.s:274
	MOVL	SI, g(DX)	// g = m->g0
 808e887:	89 b2 fc ff ff ff    	mov    %esi,-0x4(%edx)
 //################ tls[0] = m.g0
 
 
/usr/lib/golang/src/runtime/asm_386.s:275
	MOVL	(g_sched+gobuf_sp)(SI), SP	// sp = m->g0->sched.sp
 808e88d:	8b 66 20             	mov    0x20(%esi),%esp
/usr/lib/golang/src/runtime/asm_386.s:276
	PUSHL	AX
 808e890:	50                   	push   %eax
 //################# 旧的g
 
/usr/lib/golang/src/runtime/asm_386.s:277
	MOVL	DI, DX
 808e891:	89 fa                	mov    %edi,%edx
/usr/lib/golang/src/runtime/asm_386.s:278
	MOVL	0(DI), DI
 808e893:	8b 3f                	mov    (%edi),%edi
/usr/lib/golang/src/runtime/asm_386.s:279
	CALL	DI
 808e895:	ff d7                	call   *%edi
 // ################ 调用fn
 
 
/usr/lib/golang/src/runtime/asm_386.s:280
	POPL	AX
 808e897:	58                   	pop    %eax
/usr/lib/golang/src/runtime/asm_386.s:281
	MOVL	$runtime·badmcall2(SB), AX
 808e898:	b8 50 e0 06 08       	mov    $0x806e050,%eax
/usr/lib/golang/src/runtime/asm_386.s:282
	JMP	AX
 808e89d:	ff e0                	jmp    *%eax
 808e89f:	cc                   	int3   

~~~







~~~go
//################### 当调用mcall(park_m) 时， gp 是之前正在运行的gorutine的结构
func park_m(gp *g) {
	_g_ := getg()

	if trace.enabled {
		traceGoPark(_g_.m.waittraceev, _g_.m.waittraceskip, gp)
	}

	casgstatus(gp, _Grunning, _Gwaiting)
	dropg()

	if _g_.m.waitunlockf != nil {
		fn := *(*func(*g, unsafe.Pointer) bool)(unsafe.Pointer(&_g_.m.waitunlockf))
		ok := fn(gp, _g_.m.waitlock)
		_g_.m.waitunlockf = nil
		_g_.m.waitlock = nil
		if !ok {
			if trace.enabled {
				traceGoUnpark(gp, 2)
			}
			casgstatus(gp, _Gwaiting, _Grunnable)
			execute(gp, true) // Schedule it back, never returns.
		}
	}
	schedule()
}

~~~





~~~go
// Puts the current goroutine into a waiting state and calls unlockf.
// If unlockf returns false, the goroutine is resumed.
// unlockf must not access this G's stack, as it may be moved between
// the call to gopark and the call to unlockf.
func gopark(unlockf func(*g, unsafe.Pointer) bool, lock unsafe.Pointer, reason string, traceEv byte, traceskip int) {
	mp := acquirem()
	gp := mp.curg
	status := readgstatus(gp)
	if status != _Grunning && status != _Gscanrunning {
		throw("gopark: bad g status")
	}
	mp.waitlock = lock
	mp.waitunlockf = *(*unsafe.Pointer)(unsafe.Pointer(&unlockf))
	gp.waitreason = reason
	mp.waittraceev = traceEv
	mp.waittraceskip = traceskip
	releasem(mp)
	// can't do anything that might move the G between Ms here.
	mcall(park_m)
}

~~~

