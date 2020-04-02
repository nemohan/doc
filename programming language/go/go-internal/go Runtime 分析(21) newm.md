# newm 启动一个新线程





问题: fork, vfork, clone, pthread 这三者之间有何什么异同

~~~go
// runtime/proc.go

// Create a new m. It will start off with a call to fn, or else the scheduler.
// fn needs to be static and not a heap allocated closure.
// May run with m.p==nil, so write barriers are not allowed.
//go:nowritebarrierrec
func newm(fn func(), _p_ *p) {
	mp := allocm(_p_, fn)
	mp.nextp.set(_p_)
	mp.sigmask = initSigmask
	if iscgo {
		var ts cgothreadstart
		if _cgo_thread_start == nil {
			throw("_cgo_thread_start missing")
		}
		ts.g.set(mp.g0)
		ts.tls = (*uint64)(unsafe.Pointer(&mp.tls[0]))
		ts.fn = unsafe.Pointer(funcPC(mstart))
		if msanenabled {
			msanwrite(unsafe.Pointer(&ts), unsafe.Sizeof(ts))
		}
		asmcgocall(_cgo_thread_start, unsafe.Pointer(&ts))
		return
	}
	newosproc(mp, unsafe.Pointer(mp.g0.stack.hi))
}

~~~





~~~go
// runtime/os_linux.go

// May run with m.p==nil, so write barriers are not allowed.
//go:nowritebarrier
func newosproc(mp *m, stk unsafe.Pointer) {
	/*
	 * note: strace gets confused if we use CLONE_PTRACE here.
	 */
	if false {
		print("newosproc stk=", stk, " m=", mp, " g=", mp.g0, " clone=", funcPC(clone), " id=", mp.id, " ostk=", &mp, "\n")
	}

	// Disable signals during clone, so that the new thread starts
	// with signals disabled. It will enable them in minit.
	var oset sigset
	sigprocmask(_SIG_SETMASK, &sigset_all, &oset)
	ret := clone(cloneFlags, stk, unsafe.Pointer(mp), unsafe.Pointer(mp.g0), unsafe.Pointer(funcPC(mstart)))
	sigprocmask(_SIG_SETMASK, &oset, nil)

	if ret < 0 {
		print("runtime: failed to create new OS thread (have ", mcount(), " already; errno=", -ret, ")\n")
		if ret == -_EAGAIN {
			println("runtime: may need to increase max user processes (ulimit -u)")
		}
		throw("newosproc")
	}
}

~~~





~~~go
// runtime/os_windows.go

// May run with m.p==nil, so write barriers are not allowed. This
// function is called by newosproc0, so it is also required to
// operate without stack guards.
//go:nowritebarrierrec
//go:nosplit
func newosproc(mp *m, stk unsafe.Pointer) {
	const _STACK_SIZE_PARAM_IS_A_RESERVATION = 0x00010000
	thandle := stdcall6(_CreateThread, 0, 0x20000,
		funcPC(tstart_stdcall), uintptr(unsafe.Pointer(mp)),
		_STACK_SIZE_PARAM_IS_A_RESERVATION, 0)

	if thandle == 0 {
		if atomic.Load(&exiting) != 0 {
			// CreateThread may fail if called
			// concurrently with ExitProcess. If this
			// happens, just freeze this thread and let
			// the process exit. See issue #18253.
			lock(&deadlock)
			lock(&deadlock)
		}
		print("runtime: failed to create new OS thread (have ", mcount(), " already; errno=", getlasterror(), ")\n")
		throw("runtime.newosproc")
	}
}

~~~







~~~assembly

// int32 clone(int32 flags, void *stack, M *mp, G *gp, void (*fn)(void));
TEXT runtime·clone(SB),NOSPLIT,$0
	MOVL	$120, AX	// clone
	MOVL	flags+0(FP), BX
	MOVL	stk+4(FP), CX
	MOVL	$0, DX	// parent tid ptr
	MOVL	$0, DI	// child tid ptr

	// Copy mp, gp, fn off parent stack for use by child.
	SUBL	$16, CX
	MOVL	mp+8(FP), SI
	MOVL	SI, 0(CX)
	MOVL	gp+12(FP), SI
	MOVL	SI, 4(CX)
	MOVL	fn+16(FP), SI
	MOVL	SI, 8(CX)
	MOVL	$1234, 12(CX)

	// cannot use CALL 0x10(GS) here, because the stack changes during the
	// system call (after CALL 0x10(GS), the child is still using the
	// parent's stack when executing its RET instruction).
	INT	$0x80

	// In parent, return.
	CMPL	AX, $0
	JEQ	3(PC)
	MOVL	AX, ret+20(FP)
	RET

	// Paranoia: check that SP is as we expect.
	MOVL	12(SP), BP
	CMPL	BP, $1234
	JEQ	2(PC)
	INT	$3

	// Initialize AX to Linux tid
	MOVL	$224, AX
	INVOKE_SYSCALL

	MOVL	0(SP), BX	    // m
	MOVL	4(SP), DX	    // g
	MOVL	8(SP), SI	    // fn

	CMPL	BX, $0
	JEQ	nog
	CMPL	DX, $0
	JEQ	nog

	MOVL	AX, m_procid(BX)	// save tid as m->procid

	// set up ldt 7+id to point at m->tls.
	LEAL	m_tls(BX), BP
	MOVL	m_id(BX), DI
	ADDL	$7, DI	// m0 is LDT#7. count up.
	// setldt(tls#, &tls, sizeof tls)
	PUSHAL	// save registers
	PUSHL	$32	// sizeof tls
	PUSHL	BP	// &tls
	PUSHL	DI	// tls #
	CALL	runtime·setldt(SB)
	POPL	AX
	POPL	AX
	POPL	AX
	POPAL

	// Now segment is established. Initialize m, g.
	get_tls(AX)
	MOVL	DX, g(AX)
	MOVL	BX, g_m(DX)

	CALL	runtime·stackcheck(SB)	// smashes AX, CX
	MOVL	0(DX), DX	// paranoia; check they are not nil
	MOVL	0(BX), BX

	// more paranoia; check that stack splitting code works
	PUSHAL
	CALL	runtime·emptyfunc(SB)
	POPAL

nog:
	CALL	SI	// fn()
	CALL	runtime·exit1(SB)
	MOVL	$0x1234, 0x1005
~~~

