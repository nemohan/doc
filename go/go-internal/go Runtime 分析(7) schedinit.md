# schedinit 调度器初始化



##### schedinit (runtime/proc.go)



~~~go
//############# proc.go

// The bootstrap sequence is:
//
//	call osinit
//	call schedinit
//	make & queue new G
//	call runtime·mstart
//
// The new G calls runtime·main.
func schedinit() {
	// raceinit must be the first call to race detector.
	// In particular, it must be done before mallocinit below calls racemapshadow.
	_g_ := getg()
	if raceenabled {
		_g_.racectx, raceprocctx0 = raceinit()
	}

	sched.maxmcount = 10000

	tracebackinit()
	moduledataverify()
	stackinit()
	mallocinit()
	mcommoninit(_g_.m)
	alginit()       // maps must not be used before this call
	modulesinit()   // provides activeModules
	typelinksinit() // uses maps, activeModules
	itabsinit()     // uses activeModules

	msigsave(_g_.m)
	initSigmask = _g_.m.sigmask

	goargs()
	goenvs()
	parsedebugvars()
	gcinit()

	sched.lastpoll = uint64(nanotime())
	procs := ncpu
	if n, ok := atoi32(gogetenv("GOMAXPROCS")); ok && n > 0 {
		procs = n
	}
	if procs > _MaxGomaxprocs {
		procs = _MaxGomaxprocs
	}
	if procresize(procs) != nil {
		throw("unknown runnable goroutine during bootstrap")
	}

	if buildVersion == "" {
		// Condition should never trigger. This code just serves
		// to ensure runtime·buildVersion is kept in the resulting binary.
		buildVersion = "unknown"
	}
}
~~~



schedinit 对应的汇编代码

~~~assembly

08069e20 <runtime.schedinit>:
runtime.schedinit():
/usr/local/lib/go/src/runtime/proc.go:462
//	call schedinit
//	make & queue new G
//	call runtime·mstart
//
// The new G calls runtime·main.
func schedinit() {
 8069e20:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
 8069e27:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx
 8069e2d:	3b 61 08             	cmp    0x8(%ecx),%esp
 8069e30:	0f 86 77 01 00 00    	jbe    8069fad <runtime.schedinit+0x18d>
 8069e36:	83 ec 18             	sub    $0x18,%esp
 // ############## 检查栈空间
 
/usr/local/lib/go/src/runtime/proc.go:465
	// raceinit must be the first call to race detector.
	// In particular, it must be done before mallocinit below calls racemapshadow.
	_g_ := getg()
 8069e39:	65 8b 05 00 00 00 00 	mov    %gs:0x0,%eax
 8069e40:	8b 80 fc ff ff ff    	mov    -0x4(%eax),%eax
 8069e46:	89 44 24 14          	mov    %eax,0x14(%esp)
/usr/local/lib/go/src/runtime/proc.go:470
	if raceenabled {
		_g_.racectx, raceprocctx0 = raceinit()
	}

	sched.maxmcount = 10000
 8069e4a:	c7 05 44 92 0c 08 10 	movl   $0x2710,0x80c9244
 8069e51:	27 00 00 
 //############080c9220 为seched 地址  maxmcount的偏移量为0x24
/usr/local/lib/go/src/runtime/proc.go:472

	tracebackinit()
 8069e54:	e8 77 43 01 00       	call   807e1d0 <runtime.tracebackinit>
 
/usr/local/lib/go/src/runtime/proc.go:473
	moduledataverify()
 8069e59:	e8 e2 0c 01 00       	call   807ab40 <runtime.moduledataverify>
/usr/local/lib/go/src/runtime/proc.go:474
	stackinit()
 8069e5e:	e8 9d d5 00 00       	call   8077400 <runtime.stackinit>
/usr/local/lib/go/src/runtime/proc.go:475
	mallocinit()
 8069e63:	e8 08 6c fe ff       	call   8050a70 <runtime.mallocinit>
/usr/local/lib/go/src/runtime/proc.go:476
	mcommoninit(_g_.m)
 8069e68:	8b 44 24 14          	mov    0x14(%esp),%eax
 8069e6c:	8b 48 18             	mov    0x18(%eax),%ecx
 8069e6f:	89 0c 24             	mov    %ecx,(%esp)
 8069e72:	e8 99 03 00 00       	call   806a210 <runtime.mcommoninit>
/usr/local/lib/go/src/runtime/proc.go:477
	alginit()       // maps must not be used before this call
 8069e77:	e8 64 00 fe ff       	call   8049ee0 <runtime.alginit>
/usr/local/lib/go/src/runtime/proc.go:478
	modulesinit()   // provides activeModules
 8069e7c:	e8 0f 0a 01 00       	call   807a890 <runtime.modulesinit>
/usr/local/lib/go/src/runtime/proc.go:479
	typelinksinit() // uses maps, activeModules
 8069e81:	e8 9a 81 01 00       	call   8082020 <runtime.typelinksinit>
/usr/local/lib/go/src/runtime/proc.go:480
	itabsinit()     // uses activeModules
 8069e86:	e8 f5 5d fe ff       	call   804fc80 <runtime.itabsinit>
/usr/local/lib/go/src/runtime/proc.go:482

	msigsave(_g_.m)
 8069e8b:	8b 44 24 14          	mov    0x14(%esp),%eax
 8069e8f:	8b 48 18             	mov    0x18(%eax),%ecx
 8069e92:	89 0c 24             	mov    %ecx,(%esp)
 8069e95:	e8 26 ca 00 00       	call   80768c0 <runtime.msigsave>
/usr/local/lib/go/src/runtime/proc.go:483
	initSigmask = _g_.m.sigmask
 8069e9a:	8b 44 24 14          	mov    0x14(%esp),%eax
 8069e9e:	8b 40 18             	mov    0x18(%eax),%eax
 8069ea1:	8b 48 30             	mov    0x30(%eax),%ecx
 8069ea4:	8b 40 34             	mov    0x34(%eax),%eax
 8069ea7:	89 0d 30 8e 0d 08    	mov    %ecx,0x80d8e30
 8069ead:	89 05 34 8e 0d 08    	mov    %eax,0x80d8e34
/usr/local/lib/go/src/runtime/proc.go:485

	goargs()
 8069eb3:	e8 18 97 00 00       	call   80735d0 <runtime.goargs>
/usr/local/lib/go/src/runtime/proc.go:486
	goenvs()
 8069eb8:	e8 63 c1 ff ff       	call   8066020 <runtime.goenvs>
/usr/local/lib/go/src/runtime/proc.go:487
	parsedebugvars()
 8069ebd:	e8 2e a2 00 00       	call   80740f0 <runtime.parsedebugvars>
/usr/local/lib/go/src/runtime/proc.go:488
	gcinit()
 8069ec2:	e8 29 ca fe ff       	call   80568f0 <runtime.gcinit>
/usr/local/lib/go/src/runtime/proc.go:490

	sched.lastpoll = uint64(nanotime())
 8069ec7:	e8 e4 ea 01 00       	call   80889b0 <runtime.nanotime>
 8069ecc:	8b 04 24             	mov    (%esp),%eax
 8069ecf:	8b 4c 24 04          	mov    0x4(%esp),%ecx
 8069ed3:	89 05 28 92 0c 08    	mov    %eax,0x80c9228
 8069ed9:	89 0d 2c 92 0c 08    	mov    %ecx,0x80c922c
/usr/local/lib/go/src/runtime/proc.go:491
	procs := ncpu
 8069edf:	8b 05 d4 8d 0d 08    	mov    0x80d8dd4,%eax
 8069ee5:	89 44 24 10          	mov    %eax,0x10(%esp)
/usr/local/lib/go/src/runtime/proc.go:492
	if n, ok := atoi32(gogetenv("GOMAXPROCS")); ok && n > 0 {
 8069ee9:	8d 0d 4a e9 09 08    	lea    0x809e94a,%ecx
 8069eef:	89 0c 24             	mov    %ecx,(%esp)
 8069ef2:	c7 44 24 04 0a 00 00 	movl   $0xa,0x4(%esp)
 8069ef9:	00 
 8069efa:	e8 81 2e fe ff       	call   804cd80 <runtime.gogetenv>
 8069eff:	8b 44 24 0c          	mov    0xc(%esp),%eax
 8069f03:	8b 4c 24 08          	mov    0x8(%esp),%ecx
 8069f07:	89 0c 24             	mov    %ecx,(%esp)
 8069f0a:	89 44 24 04          	mov    %eax,0x4(%esp)
 8069f0e:	e8 9d 07 01 00       	call   807a6b0 <runtime.atoi32>
 8069f13:	8b 44 24 08          	mov    0x8(%esp),%eax
 8069f17:	0f b6 4c 24 0c       	movzbl 0xc(%esp),%ecx
 8069f1c:	84 c9                	test   %cl,%cl
 8069f1e:	0f 84 80 00 00 00    	je     8069fa4 <runtime.schedinit+0x184>
 8069f24:	85 c0                	test   %eax,%eax
 8069f26:	7e 7c                	jle    8069fa4 <runtime.schedinit+0x184>
/usr/local/lib/go/src/runtime/proc.go:495
		procs = n
	}
	if procs > _MaxGomaxprocs {
 8069f28:	3d 00 01 00 00       	cmp    $0x100,%eax
 8069f2d:	7e 05                	jle    8069f34 <runtime.schedinit+0x114>
 8069f2f:	b8 00 01 00 00       	mov    $0x100,%eax
/usr/local/lib/go/src/runtime/proc.go:498
		procs = _MaxGomaxprocs
	}
	if procresize(procs) != nil {
 8069f34:	89 04 24             	mov    %eax,(%esp)
 8069f37:	e8 f4 65 00 00       	call   8070530 <runtime.procresize>
 8069f3c:	8b 44 24 04          	mov    0x4(%esp),%eax
 8069f40:	85 c0                	test   %eax,%eax
 8069f42:	75 48                	jne    8069f8c <runtime.schedinit+0x16c>
/usr/local/lib/go/src/runtime/proc.go:502
		throw("unknown runnable goroutine during bootstrap")
	}

	if buildVersion == "" {
 8069f44:	8b 05 d4 89 0c 08    	mov    0x80c89d4,%eax
 8069f4a:	85 c0                	test   %eax,%eax
 8069f4c:	75 20                	jne    8069f6e <runtime.schedinit+0x14e>
/usr/local/lib/go/src/runtime/proc.go:505
		// Condition should never trigger. This code just serves
		// to ensure runtime·buildVersion is kept in the resulting binary.
		buildVersion = "unknown"
 8069f4e:	c7 05 d4 89 0c 08 07 	movl   $0x7,0x80c89d4
 8069f55:	00 00 00 
 8069f58:	8b 05 80 8e 0d 08    	mov    0x80d8e80,%eax
 8069f5e:	85 c0                	test   %eax,%eax
 8069f60:	75 10                	jne    8069f72 <runtime.schedinit+0x152>
 8069f62:	8d 05 ae e5 09 08    	lea    0x809e5ae,%eax
 8069f68:	89 05 d0 89 0c 08    	mov    %eax,0x80c89d0
/usr/local/lib/go/src/runtime/proc.go:507
	}
}
~~~



~~~go

//=================================== procresize
func procresize(nprocs int32) *p {
	old := gomaxprocs
	if old < 0 || old > _MaxGomaxprocs || nprocs <= 0 || nprocs > _MaxGomaxprocs {
		throw("procresize: invalid arg")
	}
	if trace.enabled {
		traceGomaxprocs(nprocs)
	}

	// update statistics
	now := nanotime()
	if sched.procresizetime != 0 {
		sched.totaltime += int64(old) * (now - sched.procresizetime)
	}
	sched.procresizetime = now

	// initialize new P's
	for i := int32(0); i < nprocs; i++ {
		pp := allp[i]
		if pp == nil {
			pp = new(p)
			pp.id = i
			pp.status = _Pgcstop
			pp.sudogcache = pp.sudogbuf[:0]
			for i := range pp.deferpool {
				pp.deferpool[i] = pp.deferpoolbuf[i][:0]
			}
			atomicstorep(unsafe.Pointer(&allp[i]), unsafe.Pointer(pp))
		}
		if pp.mcache == nil {
			if old == 0 && i == 0 {
                //############## 在shecdinit 的mallocinit中会初始化getg().m.mcache
				if getg().m.mcache == nil {
					throw("missing mcache?")
				}
				pp.mcache = getg().m.mcache // bootstrap
			} else {
				pp.mcache = allocmcache()
			}
		}
		if raceenabled && pp.racectx == 0 {
			if old == 0 && i == 0 {
				pp.racectx = raceprocctx0
				raceprocctx0 = 0 // bootstrap
			} else {
				pp.racectx = raceproccreate()
			}
		}
	}

	// free unused P's
	for i := nprocs; i < old; i++ {
		p := allp[i]
		if trace.enabled {
			if p == getg().m.p.ptr() {
				// moving to p[0], pretend that we were descheduled
				// and then scheduled again to keep the trace sane.
				traceGoSched()
				traceProcStop(p)
			}
		}
		// move all runnable goroutines to the global queue
		for p.runqhead != p.runqtail {
			// pop from tail of local queue
			p.runqtail--
			gp := p.runq[p.runqtail%uint32(len(p.runq))].ptr()
			// push onto head of global queue
			globrunqputhead(gp)
		}
		if p.runnext != 0 {
			globrunqputhead(p.runnext.ptr())
			p.runnext = 0
		}
		// if there's a background worker, make it runnable and put
		// it on the global queue so it can clean itself up
		if gp := p.gcBgMarkWorker.ptr(); gp != nil {
			casgstatus(gp, _Gwaiting, _Grunnable)
			if trace.enabled {
				traceGoUnpark(gp, 0)
			}
			globrunqput(gp)
			// This assignment doesn't race because the
			// world is stopped.
			p.gcBgMarkWorker.set(nil)
		}
		for i := range p.sudogbuf {
			p.sudogbuf[i] = nil
		}
		p.sudogcache = p.sudogbuf[:0]
		for i := range p.deferpool {
			for j := range p.deferpoolbuf[i] {
				p.deferpoolbuf[i][j] = nil
			}
			p.deferpool[i] = p.deferpoolbuf[i][:0]
		}
		freemcache(p.mcache)
		p.mcache = nil
		gfpurge(p)
		traceProcFree(p)
		if raceenabled {
			raceprocdestroy(p.racectx)
			p.racectx = 0
		}
		p.status = _Pdead
		// can't free P itself because it can be referenced by an M in syscall
	}

	_g_ := getg()
	if _g_.m.p != 0 && _g_.m.p.ptr().id < nprocs {
		// continue to use the current P
		_g_.m.p.ptr().status = _Prunning
	} else {
		// release the current P and acquire allp[0]
		if _g_.m.p != 0 {
			_g_.m.p.ptr().m = 0
		}
		_g_.m.p = 0
		_g_.m.mcache = nil
		p := allp[0]
		p.m = 0
		p.status = _Pidle
		acquirep(p)
		if trace.enabled {
			traceGoStart()
		}
	}
	var runnablePs *p
	for i := nprocs - 1; i >= 0; i-- {
		p := allp[i]
		if _g_.m.p.ptr() == p {
			continue
		}
		p.status = _Pidle
		if runqempty(p) {
			pidleput(p)
		} else {
			p.m.set(mget())
			p.link.set(runnablePs)
			runnablePs = p
		}
	}
	stealOrder.reset(uint32(nprocs))
	var int32p *int32 = &gomaxprocs // make compiler check that gomaxprocs is an int32
	atomic.Store((*uint32)(unsafe.Pointer(int32p)), uint32(nprocs))
	return runnablePs
}
~~~



~~~assembly
08070530 <runtime.procresize>:
runtime.procresize():
/usr/local/lib/go/src/runtime/proc.go:3461

// Change number of processors. The world is stopped, sched is locked.
// gcworkbufs are not being modified by either the GC or
// the write barrier code.
// Returns list of Ps with local work, they need to be scheduled by the caller.
func procresize(nprocs int32) *p {
 8070530:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
 8070537:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx
 807053d:	3b 61 08             	cmp    0x8(%ecx),%esp
 8070540:	0f 86 c5 07 00 00    	jbe    8070d0b <runtime.procresize+0x7db>
 8070546:	83 ec 58             	sub    $0x58,%esp
/usr/local/lib/go/src/runtime/proc.go:3462
	old := gomaxprocs
 8070549:	8b 05 bc 8d 0d 08    	mov    0x80d8dbc,%eax
 807054f:	89 44 24 0c          	mov    %eax,0xc(%esp)
/usr/local/lib/go/src/runtime/proc.go:3463
	if old < 0 || old > _MaxGomaxprocs || nprocs <= 0 || nprocs > _MaxGomaxprocs {
 8070553:	3d 00 01 00 00       	cmp    $0x100,%eax
 8070558:	0f 87 95 07 00 00    	ja     8070cf3 <runtime.procresize+0x7c3>
 807055e:	8b 4c 24 5c          	mov    0x5c(%esp),%ecx
 8070562:	85 c9                	test   %ecx,%ecx
 8070564:	0f 8e 89 07 00 00    	jle    8070cf3 <runtime.procresize+0x7c3>
 807056a:	81 f9 00 01 00 00    	cmp    $0x100,%ecx
 8070570:	0f 8f 7d 07 00 00    	jg     8070cf3 <runtime.procresize+0x7c3>
/usr/local/lib/go/src/runtime/proc.go:3466
		throw("procresize: invalid arg")
	}
	if trace.enabled {
 8070576:	0f b6 15 a8 0c 0d 08 	movzbl 0x80d0ca8,%edx
 807057d:	84 d2                	test   %dl,%dl
 807057f:	0f 85 59 07 00 00    	jne    8070cde <runtime.procresize+0x7ae>
/usr/local/lib/go/src/runtime/proc.go:3471
		traceGomaxprocs(nprocs)
	}

	// update statistics
	now := nanotime()
 8070585:	e8 26 84 01 00       	call   80889b0 <runtime.nanotime>
 807058a:	8b 44 24 04          	mov    0x4(%esp),%eax
 807058e:	89 44 24 10          	mov    %eax,0x10(%esp)
 8070592:	8b 0c 24             	mov    (%esp),%ecx
/usr/local/lib/go/src/runtime/proc.go:3472
	if sched.procresizetime != 0 {
 8070595:	8b 15 bc 92 0c 08    	mov    0x80c92bc,%edx
 807059b:	8b 1d b8 92 0c 08    	mov    0x80c92b8,%ebx
 80705a1:	85 db                	test   %ebx,%ebx
 80705a3:	87 dd                	xchg   %ebx,%ebp
 80705a5:	0f 95 c3             	setne  %bl
 80705a8:	87 dd                	xchg   %ebx,%ebp
 80705aa:	85 d2                	test   %edx,%edx
 80705ac:	87 de                	xchg   %ebx,%esi
 80705ae:	0f 95 c3             	setne  %bl
 80705b1:	87 de                	xchg   %ebx,%esi
 80705b3:	09 f5                	or     %esi,%ebp
 80705b5:	95                   	xchg   %eax,%ebp
 80705b6:	84 c0                	test   %al,%al
 80705b8:	95                   	xchg   %eax,%ebp
 80705b9:	0f 84 14 07 00 00    	je     8070cd3 <runtime.procresize+0x7a3>
/usr/local/lib/go/src/runtime/proc.go:3473
		sched.totaltime += int64(old) * (now - sched.procresizetime)
 80705bf:	89 cd                	mov    %ecx,%ebp
 80705c1:	29 d9                	sub    %ebx,%ecx
 80705c3:	89 4c 24 34          	mov    %ecx,0x34(%esp)
/usr/local/lib/go/src/runtime/proc.go:3471
	now := nanotime()
 80705c7:	89 c6                	mov    %eax,%esi
/usr/local/lib/go/src/runtime/proc.go:3473
		sched.totaltime += int64(old) * (now - sched.procresizetime)
 80705c9:	8b 44 24 0c          	mov    0xc(%esp),%eax
/usr/local/lib/go/src/runtime/proc.go:3472
	if sched.procresizetime != 0 {
 80705cd:	89 d7                	mov    %edx,%edi
/usr/local/lib/go/src/runtime/proc.go:3473
		sched.totaltime += int64(old) * (now - sched.procresizetime)
 80705cf:	f7 e1                	mul    %ecx
 80705d1:	89 54 24 30          	mov    %edx,0x30(%esp)
 80705d5:	8b 15 c0 92 0c 08    	mov    0x80c92c0,%edx
 80705db:	89 54 24 2c          	mov    %edx,0x2c(%esp)
 80705df:	01 c2                	add    %eax,%edx
 80705e1:	8b 0d c4 92 0c 08    	mov    0x80c92c4,%ecx
 80705e7:	89 15 c0 92 0c 08    	mov    %edx,0x80c92c0
 80705ed:	89 ea                	mov    %ebp,%edx
 80705ef:	29 dd                	sub    %ebx,%ebp
 80705f1:	19 fe                	sbb    %edi,%esi
 80705f3:	8b 6c 24 0c          	mov    0xc(%esp),%ebp
 80705f7:	89 ef                	mov    %ebp,%edi
 80705f9:	c1 fd 1f             	sar    $0x1f,%ebp
 80705fc:	8b 5c 24 34          	mov    0x34(%esp),%ebx
 8070600:	0f af dd             	imul   %ebp,%ebx
 8070603:	8b 6c 24 30          	mov    0x30(%esp),%ebp
 8070607:	01 eb                	add    %ebp,%ebx
 8070609:	0f af f7             	imul   %edi,%esi
 807060c:	01 f3                	add    %esi,%ebx
 807060e:	8b 6c 24 2c          	mov    0x2c(%esp),%ebp
 8070612:	01 c5                	add    %eax,%ebp
 8070614:	11 d9                	adc    %ebx,%ecx
 8070616:	89 0d c4 92 0c 08    	mov    %ecx,0x80c92c4
/usr/local/lib/go/src/runtime/proc.go:3475
	}
	sched.procresizetime = now
 807061c:	89 15 b8 92 0c 08    	mov    %edx,0x80c92b8
 8070622:	8b 44 24 10          	mov    0x10(%esp),%eax
 8070626:	89 05 bc 92 0c 08    	mov    %eax,0x80c92bc
/usr/local/lib/go/src/runtime/proc.go:3463
	if old < 0 || old > _MaxGomaxprocs || nprocs <= 0 || nprocs > _MaxGomaxprocs {
 807062c:	31 c0                	xor    %eax,%eax
/usr/local/lib/go/src/runtime/proc.go:3478

	// initialize new P's
	for i := int32(0); i < nprocs; i++ {
 807062e:	89 44 24 20          	mov    %eax,0x20(%esp)
 8070632:	8b 4c 24 5c          	mov    0x5c(%esp),%ecx
 8070636:	39 c8                	cmp    %ecx,%eax
 8070638:	7d 3f                	jge    8070679 <runtime.procresize+0x149>
/usr/local/lib/go/src/runtime/proc.go:3479
		pp := allp[i]
 807063a:	3d 01 01 00 00       	cmp    $0x101,%eax
 807063f:	0f 83 87 06 00 00    	jae    8070ccc <runtime.procresize+0x79c>
 8070645:	8d 15 80 97 0c 08    	lea    0x80c9780,%edx
 807064b:	8b 1c 82             	mov    (%edx,%eax,4),%ebx
 807064e:	8d 2c 82             	lea    (%edx,%eax,4),%ebp
 8070651:	89 6c 24 54          	mov    %ebp,0x54(%esp)
/usr/local/lib/go/src/runtime/proc.go:3480
		if pp == nil {
 8070655:	85 db                	test   %ebx,%ebx
 8070657:	0f 84 69 05 00 00    	je     8070bc6 <runtime.procresize+0x696>
/usr/local/lib/go/src/runtime/proc.go:3490
			for i := range pp.deferpool {
				pp.deferpool[i] = pp.deferpoolbuf[i][:0]
			}
			atomicstorep(unsafe.Pointer(&allp[i]), unsafe.Pointer(pp))
		}
		if pp.mcache == nil {
 807065d:	89 5c 24 38          	mov    %ebx,0x38(%esp)
 8070661:	8b 6b 1c             	mov    0x1c(%ebx),%ebp
 8070664:	85 ed                	test   %ebp,%ebp
 8070666:	0f 84 f2 04 00 00    	je     8070b5e <runtime.procresize+0x62e>
/usr/local/lib/go/src/runtime/proc.go:3478
	for i := int32(0); i < nprocs; i++ {
 807066c:	40                   	inc    %eax
 807066d:	89 44 24 20          	mov    %eax,0x20(%esp)
 8070671:	8b 4c 24 5c          	mov    0x5c(%esp),%ecx
 8070675:	39 c8                	cmp    %ecx,%eax
 8070677:	7c c1                	jl     807063a <runtime.procresize+0x10a>
/usr/local/lib/go/src/runtime/proc.go:3461
func procresize(nprocs int32) *p {
 8070679:	89 c8                	mov    %ecx,%eax
/usr/local/lib/go/src/runtime/proc.go:3511
			}
		}
	}

	// free unused P's
	for i := nprocs; i < old; i++ {
 807067b:	89 4c 24 14          	mov    %ecx,0x14(%esp)
 807067f:	39 f9                	cmp    %edi,%ecx
 8070681:	0f 8d 2c 02 00 00    	jge    80708b3 <runtime.procresize+0x383>
/usr/local/lib/go/src/runtime/proc.go:3512
		p := allp[i]
 8070687:	81 f9 01 01 00 00    	cmp    $0x101,%ecx
 807068d:	0f 83 c4 04 00 00    	jae    8070b57 <runtime.procresize+0x627>
/usr/local/lib/go/src/runtime/proc.go:3479
		pp := allp[i]
 8070693:	8d 15 80 97 0c 08    	lea    0x80c9780,%edx
/usr/local/lib/go/src/runtime/proc.go:3512
		p := allp[i]
 8070699:	8b 1c 8a             	mov    (%edx,%ecx,4),%ebx
 807069c:	89 5c 24 44          	mov    %ebx,0x44(%esp)
/usr/local/lib/go/src/runtime/proc.go:3513
		if trace.enabled {
 80706a0:	0f b6 2d a8 0c 0d 08 	movzbl 0x80d0ca8,%ebp
 80706a7:	95                   	xchg   %eax,%ebp
 80706a8:	84 c0                	test   %al,%al
 80706aa:	95                   	xchg   %eax,%ebp
 80706ab:	74 1b                	je     80706c8 <runtime.procresize+0x198>
/usr/local/lib/go/src/runtime/proc.go:3514
			if p == getg().m.p.ptr() {
 80706ad:	65 8b 2d 00 00 00 00 	mov    %gs:0x0,%ebp
 80706b4:	8b ad fc ff ff ff    	mov    -0x4(%ebp),%ebp
 80706ba:	8b 6d 18             	mov    0x18(%ebp),%ebp
 80706bd:	8b 6d 5c             	mov    0x5c(%ebp),%ebp
 80706c0:	39 eb                	cmp    %ebp,%ebx
 80706c2:	0f 84 63 04 00 00    	je     8070b2b <runtime.procresize+0x5fb>
/usr/local/lib/go/src/runtime/proc.go:3522
				traceGoSched()
				traceProcStop(p)
			}
		}
		// move all runnable goroutines to the global queue
		for p.runqhead != p.runqtail {
 80706c8:	8b ab f0 02 00 00    	mov    0x2f0(%ebx),%ebp
 80706ce:	8b b3 f4 02 00 00    	mov    0x2f4(%ebx),%esi
 80706d4:	39 f5                	cmp    %esi,%ebp
 80706d6:	74 64                	je     807073c <runtime.procresize+0x20c>
/usr/local/lib/go/src/runtime/proc.go:3524
			// pop from tail of local queue
			p.runqtail--
 80706d8:	8d 6e ff             	lea    -0x1(%esi),%ebp
 80706db:	89 ab f4 02 00 00    	mov    %ebp,0x2f4(%ebx)
/usr/local/lib/go/src/runtime/proc.go:3525
			gp := p.runq[p.runqtail%uint32(len(p.runq))].ptr()
 80706e1:	81 e5 ff 00 00 00    	and    $0xff,%ebp
 80706e7:	8b ac ab f8 02 00 00 	mov    0x2f8(%ebx,%ebp,4),%ebp
/usr/local/lib/go/src/runtime/proc.go:3527
			// push onto head of global queue
			globrunqputhead(gp)
 80706ee:	8b 35 58 92 0c 08    	mov    0x80c9258,%esi
 80706f4:	89 75 7c             	mov    %esi,0x7c(%ebp)
 80706f7:	8d 35 58 92 0c 08    	lea    0x80c9258,%esi
 80706fd:	84 06                	test   %al,(%esi)
 80706ff:	89 ee                	mov    %ebp,%esi
 8070701:	89 35 58 92 0c 08    	mov    %esi,0x80c9258
 8070707:	8b 35 5c 92 0c 08    	mov    0x80c925c,%esi
 807070d:	85 f6                	test   %esi,%esi
 807070f:	75 0e                	jne    807071f <runtime.procresize+0x1ef>
 8070711:	8d 35 5c 92 0c 08    	lea    0x80c925c,%esi
 8070717:	84 06                	test   %al,(%esi)
 8070719:	89 2d 5c 92 0c 08    	mov    %ebp,0x80c925c
 807071f:	8b 2d 60 92 0c 08    	mov    0x80c9260,%ebp
 8070725:	45                   	inc    %ebp
 8070726:	89 2d 60 92 0c 08    	mov    %ebp,0x80c9260
/usr/local/lib/go/src/runtime/proc.go:3522
		for p.runqhead != p.runqtail {
 807072c:	8b ab f0 02 00 00    	mov    0x2f0(%ebx),%ebp
 8070732:	8b b3 f4 02 00 00    	mov    0x2f4(%ebx),%esi
 8070738:	39 f5                	cmp    %esi,%ebp
 807073a:	75 9c                	jne    80706d8 <runtime.procresize+0x1a8>
/usr/local/lib/go/src/runtime/proc.go:3529
		}
		if p.runnext != 0 {
 807073c:	8b ab f8 06 00 00    	mov    0x6f8(%ebx),%ebp
 8070742:	85 ed                	test   %ebp,%ebp
 8070744:	74 48                	je     807078e <runtime.procresize+0x25e>
/usr/local/lib/go/src/runtime/proc.go:3530
			globrunqputhead(p.runnext.ptr())
 8070746:	8b 35 58 92 0c 08    	mov    0x80c9258,%esi
 807074c:	89 75 7c             	mov    %esi,0x7c(%ebp)
 807074f:	8d 35 58 92 0c 08    	lea    0x80c9258,%esi
 8070755:	84 06                	test   %al,(%esi)
 8070757:	89 ee                	mov    %ebp,%esi
 8070759:	89 35 58 92 0c 08    	mov    %esi,0x80c9258
 807075f:	8b 35 5c 92 0c 08    	mov    0x80c925c,%esi
 8070765:	85 f6                	test   %esi,%esi
 8070767:	75 0e                	jne    8070777 <runtime.procresize+0x247>
 8070769:	8d 35 5c 92 0c 08    	lea    0x80c925c,%esi
 807076f:	84 06                	test   %al,(%esi)
 8070771:	89 2d 5c 92 0c 08    	mov    %ebp,0x80c925c
 8070777:	8b 2d 60 92 0c 08    	mov    0x80c9260,%ebp
 807077d:	45                   	inc    %ebp
 807077e:	89 2d 60 92 0c 08    	mov    %ebp,0x80c9260
/usr/local/lib/go/src/runtime/proc.go:3531
			p.runnext = 0
 8070784:	c7 83 f8 06 00 00 00 	movl   $0x0,0x6f8(%ebx)
 807078b:	00 00 00 
/usr/local/lib/go/src/runtime/proc.go:3535
		}
		// if there's a background worker, make it runnable and put
		// it on the global queue so it can clean itself up
		if gp := p.gcBgMarkWorker.ptr(); gp != nil {
 807078e:	8b ab 24 09 00 00    	mov    0x924(%ebx),%ebp
 8070794:	89 6c 24 50          	mov    %ebp,0x50(%esp)
 8070798:	85 ed                	test   %ebp,%ebp
 807079a:	0f 85 d2 02 00 00    	jne    8070a72 <runtime.procresize+0x542>
/usr/local/lib/go/src/runtime/proc.go:3545
			globrunqput(gp)
			// This assignment doesn't race because the
			// world is stopped.
			p.gcBgMarkWorker.set(nil)
		}
		for i := range p.sudogbuf {
 80707a0:	8d ab 10 07 00 00    	lea    0x710(%ebx),%ebp
 80707a6:	89 6c 24 4c          	mov    %ebp,0x4c(%esp)
 80707aa:	89 2c 24             	mov    %ebp,(%esp)
 80707ad:	c7 44 24 04 00 02 00 	movl   $0x200,0x4(%esp)
 80707b4:	00 
 80707b5:	e8 76 22 fe ff       	call   8052a30 <runtime.memclrHasPointers>
/usr/local/lib/go/src/runtime/proc.go:3548
			p.sudogbuf[i] = nil
		}
		p.sudogcache = p.sudogbuf[:0]
 80707ba:	8b 44 24 4c          	mov    0x4c(%esp),%eax
 80707be:	84 00                	test   %al,(%eax)
 80707c0:	8b 4c 24 44          	mov    0x44(%esp),%ecx
 80707c4:	c7 81 08 07 00 00 00 	movl   $0x0,0x708(%ecx)
 80707cb:	00 00 00 
 80707ce:	c7 81 0c 07 00 00 80 	movl   $0x80,0x70c(%ecx)
 80707d5:	00 00 00 
 80707d8:	8b 15 80 8e 0d 08    	mov    0x80d8e80,%edx
 80707de:	8d 99 04 07 00 00    	lea    0x704(%ecx),%ebx
 80707e4:	85 d2                	test   %edx,%edx
 80707e6:	0f 85 71 02 00 00    	jne    8070a5d <runtime.procresize+0x52d>
 80707ec:	89 81 04 07 00 00    	mov    %eax,0x704(%ecx)
/usr/local/lib/go/src/runtime/proc.go:3484
			pp.sudogcache = pp.sudogbuf[:0]
 80707f2:	31 c0                	xor    %eax,%eax
/usr/local/lib/go/src/runtime/proc.go:3549
		for i := range p.deferpool {
 80707f4:	89 44 24 24          	mov    %eax,0x24(%esp)
 80707f8:	83 f8 05             	cmp    $0x5,%eax
 80707fb:	7d 66                	jge    8070863 <runtime.procresize+0x333>
/usr/local/lib/go/src/runtime/proc.go:3550
			for j := range p.deferpoolbuf[i] {
 80707fd:	0f 83 53 02 00 00    	jae    8070a56 <runtime.procresize+0x526>
 8070803:	c1 e0 07             	shl    $0x7,%eax
 8070806:	89 44 24 28          	mov    %eax,0x28(%esp)
 807080a:	8d 5c 01 60          	lea    0x60(%ecx,%eax,1),%ebx
 807080e:	89 1c 24             	mov    %ebx,(%esp)
 8070811:	c7 44 24 04 80 00 00 	movl   $0x80,0x4(%esp)
 8070818:	00 
 8070819:	e8 12 22 fe ff       	call   8052a30 <runtime.memclrHasPointers>
/usr/local/lib/go/src/runtime/proc.go:3553
				p.deferpoolbuf[i][j] = nil
			}
			p.deferpool[i] = p.deferpoolbuf[i][:0]
 807081e:	8b 44 24 24          	mov    0x24(%esp),%eax
 8070822:	8d 0c 40             	lea    (%eax,%eax,2),%ecx
 8070825:	8b 54 24 44          	mov    0x44(%esp),%edx
 8070829:	c7 44 8a 28 00 00 00 	movl   $0x0,0x28(%edx,%ecx,4)
 8070830:	00 
 8070831:	c7 44 8a 2c 20 00 00 	movl   $0x20,0x2c(%edx,%ecx,4)
 8070838:	00 
/usr/local/lib/go/src/runtime/proc.go:3550
			for j := range p.deferpoolbuf[i] {
 8070839:	8b 5c 24 28          	mov    0x28(%esp),%ebx
 807083d:	8d 5c 1a 60          	lea    0x60(%edx,%ebx,1),%ebx
/usr/local/lib/go/src/runtime/proc.go:3553
			p.deferpool[i] = p.deferpoolbuf[i][:0]
 8070841:	8b 2d 80 8e 0d 08    	mov    0x80d8e80,%ebp
 8070847:	8d 74 8a 24          	lea    0x24(%edx,%ecx,4),%esi
 807084b:	85 ed                	test   %ebp,%ebp
 807084d:	0f 85 ea 01 00 00    	jne    8070a3d <runtime.procresize+0x50d>
 8070853:	89 5c 8a 24          	mov    %ebx,0x24(%edx,%ecx,4)
/usr/local/lib/go/src/runtime/proc.go:3549
		for i := range p.deferpool {
 8070857:	40                   	inc    %eax
/usr/local/lib/go/src/runtime/proc.go:3550
			for j := range p.deferpoolbuf[i] {
 8070858:	89 d1                	mov    %edx,%ecx
/usr/local/lib/go/src/runtime/proc.go:3549
		for i := range p.deferpool {
 807085a:	89 44 24 24          	mov    %eax,0x24(%esp)
 807085e:	83 f8 05             	cmp    $0x5,%eax
 8070861:	7c 9a                	jl     80707fd <runtime.procresize+0x2cd>
/usr/local/lib/go/src/runtime/proc.go:3555
		}
		freemcache(p.mcache)
 8070863:	8b 41 1c             	mov    0x1c(%ecx),%eax
 8070866:	89 04 24             	mov    %eax,(%esp)
 8070869:	e8 42 46 fe ff       	call   8054eb0 <runtime.freemcache>
/usr/local/lib/go/src/runtime/proc.go:3556
		p.mcache = nil
 807086e:	8b 44 24 44          	mov    0x44(%esp),%eax
 8070872:	c7 40 1c 00 00 00 00 	movl   $0x0,0x1c(%eax)
/usr/local/lib/go/src/runtime/proc.go:3557
		gfpurge(p)
 8070879:	89 04 24             	mov    %eax,(%esp)
 807087c:	e8 7f f3 ff ff       	call   806fc00 <runtime.gfpurge>
/usr/local/lib/go/src/runtime/proc.go:3558
		traceProcFree(p)
 8070881:	8b 44 24 44          	mov    0x44(%esp),%eax
 8070885:	89 04 24             	mov    %eax,(%esp)
 8070888:	e8 83 c0 00 00       	call   807c910 <runtime.traceProcFree>
/usr/local/lib/go/src/runtime/proc.go:3563
		if raceenabled {
			raceprocdestroy(p.racectx)
			p.racectx = 0
		}
		p.status = _Pdead
 807088d:	8b 44 24 44          	mov    0x44(%esp),%eax
 8070891:	c7 40 08 04 00 00 00 	movl   $0x4,0x8(%eax)
/usr/local/lib/go/src/runtime/proc.go:3511
	for i := nprocs; i < old; i++ {
 8070898:	8b 44 24 14          	mov    0x14(%esp),%eax
 807089c:	8d 48 01             	lea    0x1(%eax),%ecx
 
 
/usr/local/lib/go/src/runtime/proc.go:3568
		// can't free P itself because it can be referenced by an M in syscall
	}
	_g_ := getg()
	if _g_.m.p != 0 && _g_.m.p.ptr().id < nprocs {
 807089f:	8b 44 24 5c          	mov    0x5c(%esp),%eax
/usr/local/lib/go/src/runtime/proc.go:3511
	for i := nprocs; i < old; i++ {
 80708a3:	8b 7c 24 0c          	mov    0xc(%esp),%edi
 80708a7:	89 4c 24 14          	mov    %ecx,0x14(%esp)
 80708ab:	39 f9                	cmp    %edi,%ecx
 80708ad:	0f 8c d4 fd ff ff    	jl     8070687 <runtime.procresize+0x157>
 
 
/usr/local/lib/go/src/runtime/proc.go:3567
	_g_ := getg()
 80708b3:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
 80708ba:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx
 80708c0:	89 4c 24 48          	mov    %ecx,0x48(%esp)
 // ################ 获取g
 
/usr/local/lib/go/src/runtime/proc.go:3568
	if _g_.m.p != 0 && _g_.m.p.ptr().id < nprocs {
 80708c4:	8b 51 18             	mov    0x18(%ecx),%edx
 80708c7:	8b 52 5c             	mov    0x5c(%edx),%edx
 80708ca:	85 d2                	test   %edx,%edx
 80708cc:	0f 84 10 01 00 00    	je     80709e2 <runtime.procresize+0x4b2>
 // ################# 检查 _g_.m.p 是否为0 在初始化阶段， _g_.m.p 为0
 
 80708d2:	89 d3                	mov    %edx,%ebx
 80708d4:	8b 6b 04             	mov    0x4(%ebx),%ebp
 80708d7:	39 c5                	cmp    %eax,%ebp
 80708d9:	0f 8d 01 01 00 00    	jge    80709e0 <runtime.procresize+0x4b0>
/usr/local/lib/go/src/runtime/proc.go:3570
		// continue to use the current P
		_g_.m.p.ptr().status = _Prunning
 80708df:	c7 43 08 01 00 00 00 	movl   $0x1,0x8(%ebx)
 
 
 
 // ############################### 这段  begin 
 //===============================
/usr/local/lib/go/src/runtime/proc.go:3587
		if trace.enabled {
			traceGoStart()
		}
	}
	var runnablePs *p
	for i := nprocs - 1; i >= 0; i-- {
 80708e6:	8d 50 ff             	lea    -0x1(%eax),%edx
 //################## eax 的值为nprocs
 
/usr/local/lib/go/src/runtime/proc.go:3461
func procresize(nprocs int32) *p {
 80708e9:	31 db                	xor    %ebx,%ebx
/usr/local/lib/go/src/runtime/proc.go:3587
	for i := nprocs - 1; i >= 0; i-- {
 80708eb:	89 54 24 18          	mov    %edx,0x18(%esp)
/usr/local/lib/go/src/runtime/proc.go:3597
		p.status = _Pidle
		if runqempty(p) {
			pidleput(p)
		} else {
			p.m.set(mget())
			p.link.set(runnablePs)
 80708ef:	89 5c 24 3c          	mov    %ebx,0x3c(%esp)
 
 
/usr/local/lib/go/src/runtime/proc.go:3587
	for i := nprocs - 1; i >= 0; i-- {
 80708f3:	85 d2                	test   %edx,%edx
 80708f5:	7c 30                	jl     8070927 <runtime.procresize+0x3f7>
 //############## i >=0
 
 
/usr/local/lib/go/src/runtime/proc.go:3588
		p := allp[i]
 80708f7:	81 fa 01 01 00 00    	cmp    $0x101,%edx
 // ################# allp[i] 边界检查，是否越界
 80708fd:	0f 83 d6 00 00 00    	jae    80709d9 <runtime.procresize+0x4a9>
 //########### edx= 0
 
/usr/local/lib/go/src/runtime/proc.go:3589
		if _g_.m.p.ptr() == p {
 8070903:	8b 69 18             	mov    0x18(%ecx),%ebp
 //########### ecx 的值 为 _g_
/usr/local/lib/go/src/runtime/proc.go:3479
		pp := allp[i]
 8070906:	8d 35 80 97 0c 08    	lea    0x80c9780,%esi
 //########### 0x80c9780 为allp 的地址
 
/usr/local/lib/go/src/runtime/proc.go:3588
		p := allp[i]
 807090c:	8b 3c 96             	mov    (%esi,%edx,4),%edi
 807090f:	89 7c 24 40          	mov    %edi,0x40(%esp)
 //############## p 的值
 
/usr/local/lib/go/src/runtime/proc.go:3589
		if _g_.m.p.ptr() == p {
 8070913:	8b 6d 5c             	mov    0x5c(%ebp),%ebp
 8070916:	39 ef                	cmp    %ebp,%edi
 8070918:	75 41                	jne    807095b <runtime.procresize+0x42b>
 //#####################  edi的值来自allp[0],  检查_g_.m.p.ptr() == p
 
/usr/local/lib/go/src/runtime/proc.go:3587
	for i := nprocs - 1; i >= 0; i-- {
 807091a:	4a                   	dec    %edx
 807091b:	89 54 24 18          	mov    %edx,0x18(%esp)
 //#################33 i--, edx=i
 
/usr/local/lib/go/src/runtime/proc.go:3597
			p.link.set(runnablePs)
 807091f:	89 5c 24 3c          	mov    %ebx,0x3c(%esp)
 // ############### 此时ebx 的值为0
/usr/local/lib/go/src/runtime/proc.go:3587
	for i := nprocs - 1; i >= 0; i-- {
 8070923:	85 d2                	test   %edx,%edx
 8070925:	7d d0                	jge    80708f7 <runtime.procresize+0x3c7>
 //###################### 跳到循环开头
/usr/local/lib/go/src/runtime/proc.go:3601
			runnablePs = p
		}
	}
	stealOrder.reset(uint32(nprocs))
 8070927:	8d 0d 80 90 0c 08    	lea    0x80c9080,%ecx
 807092d:	89 0c 24             	mov    %ecx,(%esp)
 8070930:	89 44 24 04          	mov    %eax,0x4(%esp)
 8070934:	e8 47 2a 00 00       	call   8073380 <runtime.(*randomOrder).reset>
/usr/local/lib/go/src/runtime/proc.go:3462
	old := gomaxprocs
 8070939:	8d 05 bc 8d 0d 08    	lea    0x80d8dbc,%eax
/usr/local/lib/go/src/runtime/proc.go:3603
	var int32p *int32 = &gomaxprocs // make compiler check that gomaxprocs is an int32
	atomic.Store((*uint32)(unsafe.Pointer(int32p)), uint32(nprocs))
 807093f:	89 04 24             	mov    %eax,(%esp)
 8070942:	8b 44 24 5c          	mov    0x5c(%esp),%eax
 8070946:	89 44 24 04          	mov    %eax,0x4(%esp)
 807094a:	e8 e1 88 fd ff       	call   8049230 <runtime/internal/atomic.Store>
/usr/local/lib/go/src/runtime/proc.go:3604
	return runnablePs
 807094f:	8b 44 24 3c          	mov    0x3c(%esp),%eax
 8070953:	89 44 24 60          	mov    %eax,0x60(%esp)
 8070957:	83 c4 58             	add    $0x58,%esp
 807095a:	c3                   	ret    
 
 
 
 // ##################### 
/usr/local/lib/go/src/runtime/proc.go:3592
		p.status = _Pidle
 807095b:	c7 47 08 00 00 00 00 	movl   $0x0,0x8(%edi)
/usr/local/lib/go/src/runtime/proc.go:3593
		if runqempty(p) {
 8070962:	89 3c 24             	mov    %edi,(%esp)
 8070965:	e8 06 23 00 00       	call   8072c70 <runtime.runqempty>
 807096a:	0f b6 44 24 04       	movzbl 0x4(%esp),%eax
 807096f:	84 c0                	test   %al,%al
 8070971:	75 54                	jne    80709c7 <runtime.procresize+0x497>
/usr/local/lib/go/src/runtime/proc.go:3596
			p.m.set(mget())
 8070973:	8b 05 34 92 0c 08    	mov    0x80c9234,%eax
 8070979:	85 c0                	test   %eax,%eax
 807097b:	74 19                	je     8070996 <runtime.procresize+0x466>
 807097d:	8b 88 b4 00 00 00    	mov    0xb4(%eax),%ecx
 8070983:	89 0d 34 92 0c 08    	mov    %ecx,0x80c9234
 8070989:	8b 0d 38 92 0c 08    	mov    0x80c9238,%ecx
 807098f:	49                   	dec    %ecx
 8070990:	89 0d 38 92 0c 08    	mov    %ecx,0x80c9238
 8070996:	8b 4c 24 40          	mov    0x40(%esp),%ecx
 807099a:	8d 51 18             	lea    0x18(%ecx),%edx
 807099d:	84 02                	test   %al,(%edx)
 807099f:	89 41 18             	mov    %eax,0x18(%ecx)
/usr/local/lib/go/src/runtime/proc.go:3597
			p.link.set(runnablePs)
 80709a2:	8d 41 0c             	lea    0xc(%ecx),%eax
 80709a5:	84 00                	test   %al,(%eax)
 80709a7:	8b 44 24 3c          	mov    0x3c(%esp),%eax
 80709ab:	89 41 0c             	mov    %eax,0xc(%ecx)
/usr/local/lib/go/src/runtime/proc.go:3601
	stealOrder.reset(uint32(nprocs))
 80709ae:	8b 44 24 5c          	mov    0x5c(%esp),%eax
/usr/local/lib/go/src/runtime/proc.go:3587
	for i := nprocs - 1; i >= 0; i-- {
 80709b2:	8b 54 24 18          	mov    0x18(%esp),%edx
/usr/local/lib/go/src/runtime/proc.go:3479
		pp := allp[i]
 80709b6:	8d 35 80 97 0c 08    	lea    0x80c9780,%esi
/usr/local/lib/go/src/runtime/proc.go:3597
			p.link.set(runnablePs)
 80709bc:	89 cb                	mov    %ecx,%ebx
/usr/local/lib/go/src/runtime/proc.go:3589
		if _g_.m.p.ptr() == p {
 80709be:	8b 4c 24 48          	mov    0x48(%esp),%ecx
/usr/local/lib/go/src/runtime/proc.go:3587
	for i := nprocs - 1; i >= 0; i-- {
 80709c2:	e9 53 ff ff ff       	jmp    807091a <runtime.procresize+0x3ea>
/usr/local/lib/go/src/runtime/proc.go:3594
			pidleput(p)
 80709c7:	8b 44 24 40          	mov    0x40(%esp),%eax
 80709cb:	89 04 24             	mov    %eax,(%esp)
 80709ce:	e8 bd 21 00 00       	call   8072b90 <runtime.pidleput>
/usr/local/lib/go/src/runtime/proc.go:3597
			p.link.set(runnablePs)
 80709d3:	8b 4c 24 3c          	mov    0x3c(%esp),%ecx
/usr/local/lib/go/src/runtime/proc.go:3601
	stealOrder.reset(uint32(nprocs))
 80709d7:	eb d5                	jmp    80709ae <runtime.procresize+0x47e>
 
 // ################ 数组边界检查
/usr/local/lib/go/src/runtime/proc.go:3588
		p := allp[i]
 80709d9:	e8 e2 59 ff ff       	call   80663c0 <runtime.panicindex>
 80709de:	0f 0b                	ud2    
/usr/local/lib/go/src/runtime/proc.go:3568
	if _g_.m.p != 0 && _g_.m.p.ptr().id < nprocs {
 80709e0:	85 d2                	test   %edx,%edx
 
 
 // ############# 从遥远的地方跳过来
/usr/local/lib/go/src/runtime/proc.go:3573
		if _g_.m.p != 0 {
 80709e2:	74 07                	je     80709eb <runtime.procresize+0x4bb>
/usr/local/lib/go/src/runtime/proc.go:3574
			_g_.m.p.ptr().m = 0
 80709e4:	c7 42 18 00 00 00 00 	movl   $0x0,0x18(%edx)
/usr/local/lib/go/src/runtime/proc.go:3576
		_g_.m.p = 0
 80709eb:	8b 51 18             	mov    0x18(%ecx),%edx
 80709ee:	c7 42 5c 00 00 00 00 	movl   $0x0,0x5c(%edx)
 //################ _g_.m.p = 0
 
 
/usr/local/lib/go/src/runtime/proc.go:3577
		_g_.m.mcache = nil
 80709f5:	8b 51 18             	mov    0x18(%ecx),%edx
 80709f8:	c7 82 b8 00 00 00 00 	movl   $0x0,0xb8(%edx)
 80709ff:	00 00 00 
/usr/local/lib/go/src/runtime/proc.go:3578
		p := allp[0]
 8070a02:	8b 15 80 97 0c 08    	mov    0x80c9780,%edx
/usr/local/lib/go/src/runtime/proc.go:3579
		p.m = 0
 8070a08:	c7 42 18 00 00 00 00 	movl   $0x0,0x18(%edx)
/usr/local/lib/go/src/runtime/proc.go:3580
		p.status = _Pidle
 8070a0f:	c7 42 08 00 00 00 00 	movl   $0x0,0x8(%edx)
/usr/local/lib/go/src/runtime/proc.go:3581
		acquirep(p)
 8070a16:	89 14 24             	mov    %edx,(%esp)
 8070a19:	e8 02 03 00 00       	call   8070d20 <runtime.acquirep>
/usr/local/lib/go/src/runtime/proc.go:3582
		if trace.enabled {
 8070a1e:	0f b6 05 a8 0c 0d 08 	movzbl 0x80d0ca8,%eax
 8070a25:	84 c0                	test   %al,%al
 8070a27:	75 0d                	jne    8070a36 <runtime.procresize+0x506>
 
 
 
/usr/local/lib/go/src/runtime/proc.go:3587
	for i := nprocs - 1; i >= 0; i-- {
 8070a29:	8b 44 24 5c          	mov    0x5c(%esp),%eax
/usr/local/lib/go/src/runtime/proc.go:3589
		if _g_.m.p.ptr() == p {
 8070a2d:	8b 4c 24 48          	mov    0x48(%esp),%ecx
/usr/local/lib/go/src/runtime/proc.go:3587
	for i := nprocs - 1; i >= 0; i-- {
 8070a31:	e9 b0 fe ff ff       	jmp    80708e6 <runtime.procresize+0x3b6>
 // ########################## 跳到上面 
 //===============================================
 
 
/usr/local/lib/go/src/runtime/proc.go:3583
			traceGoStart()
 8070a36:	e8 45 cf 00 00       	call   807d980 <runtime.traceGoStart>
/usr/local/lib/go/src/runtime/proc.go:3587
	for i := nprocs - 1; i >= 0; i-- {
 8070a3b:	eb ec                	jmp    8070a29 <runtime.procresize+0x4f9>
/usr/local/lib/go/src/runtime/proc.go:3553
			p.deferpool[i] = p.deferpoolbuf[i][:0]
 8070a3d:	89 34 24             	mov    %esi,(%esp)
 8070a40:	89 5c 24 04          	mov    %ebx,0x4(%esp)
 8070a44:	e8 57 1c fe ff       	call   80526a0 <runtime.writebarrierptr>
/usr/local/lib/go/src/runtime/proc.go:3549
		for i := range p.deferpool {
 8070a49:	8b 44 24 24          	mov    0x24(%esp),%eax
/usr/local/lib/go/src/runtime/proc.go:3550
			for j := range p.deferpoolbuf[i] {
 8070a4d:	8b 54 24 44          	mov    0x44(%esp),%edx
/usr/local/lib/go/src/runtime/proc.go:3549
		for i := range p.deferpool {
 8070a51:	e9 01 fe ff ff       	jmp    8070857 <runtime.procresize+0x327>
/usr/local/lib/go/src/runtime/proc.go:3550
			for j := range p.deferpoolbuf[i] {
 8070a56:	e8 65 59 ff ff       	call   80663c0 <runtime.panicindex>
 8070a5b:	0f 0b                	ud2    
/usr/local/lib/go/src/runtime/proc.go:3548
		p.sudogcache = p.sudogbuf[:0]
 8070a5d:	89 1c 24             	mov    %ebx,(%esp)
 8070a60:	89 44 24 04          	mov    %eax,0x4(%esp)
 8070a64:	e8 37 1c fe ff       	call   80526a0 <runtime.writebarrierptr>
/usr/local/lib/go/src/runtime/proc.go:3550
			for j := range p.deferpoolbuf[i] {
 8070a69:	8b 4c 24 44          	mov    0x44(%esp),%ecx
/usr/local/lib/go/src/runtime/proc.go:3484
			pp.sudogcache = pp.sudogbuf[:0]
 8070a6d:	e9 80 fd ff ff       	jmp    80707f2 <runtime.procresize+0x2c2>
/usr/local/lib/go/src/runtime/proc.go:3536
			casgstatus(gp, _Gwaiting, _Grunnable)
 8070a72:	89 2c 24             	mov    %ebp,(%esp)
 8070a75:	c7 44 24 04 04 00 00 	movl   $0x4,0x4(%esp)
 8070a7c:	00 
 8070a7d:	c7 44 24 08 01 00 00 	movl   $0x1,0x8(%esp)
 8070a84:	00 
 8070a85:	e8 76 a0 ff ff       	call   806ab00 <runtime.casgstatus>
/usr/local/lib/go/src/runtime/proc.go:3537
			if trace.enabled {
 8070a8a:	0f b6 05 a8 0c 0d 08 	movzbl 0x80d0ca8,%eax
 8070a91:	84 c0                	test   %al,%al
 8070a93:	75 7d                	jne    8070b12 <runtime.procresize+0x5e2>
/usr/local/lib/go/src/runtime/proc.go:3540
			globrunqput(gp)
 8070a95:	8b 44 24 50          	mov    0x50(%esp),%eax
 8070a99:	c7 40 7c 00 00 00 00 	movl   $0x0,0x7c(%eax)
 8070aa0:	8b 0d 5c 92 0c 08    	mov    0x80c925c,%ecx
 8070aa6:	85 c9                	test   %ecx,%ecx
 8070aa8:	74 56                	je     8070b00 <runtime.procresize+0x5d0>
 8070aaa:	8d 51 7c             	lea    0x7c(%ecx),%edx
 8070aad:	84 02                	test   %al,(%edx)
 8070aaf:	89 c2                	mov    %eax,%edx
 8070ab1:	89 51 7c             	mov    %edx,0x7c(%ecx)
 8070ab4:	8d 2d 5c 92 0c 08    	lea    0x80c925c,%ebp
 8070aba:	84 45 00             	test   %al,0x0(%ebp)
 8070abd:	89 c5                	mov    %eax,%ebp
 8070abf:	89 2d 5c 92 0c 08    	mov    %ebp,0x80c925c
 8070ac5:	8b 2d 60 92 0c 08    	mov    0x80c9260,%ebp
 8070acb:	45                   	inc    %ebp
 8070acc:	89 2d 60 92 0c 08    	mov    %ebp,0x80c9260
/usr/local/lib/go/src/runtime/proc.go:3543
			p.gcBgMarkWorker.set(nil)
 8070ad2:	8b 5c 24 44          	mov    0x44(%esp),%ebx
 8070ad6:	8d ab 24 09 00 00    	lea    0x924(%ebx),%ebp
 8070adc:	84 45 00             	test   %al,0x0(%ebp)
/usr/local/lib/go/src/runtime/proc.go:3525
			gp := p.runq[p.runqtail%uint32(len(p.runq))].ptr()
 8070adf:	31 ed                	xor    %ebp,%ebp
/usr/local/lib/go/src/runtime/proc.go:3543
			p.gcBgMarkWorker.set(nil)
 8070ae1:	89 ee                	mov    %ebp,%esi
 8070ae3:	89 b3 24 09 00 00    	mov    %esi,0x924(%ebx)
/usr/local/lib/go/src/runtime/proc.go:3568
	if _g_.m.p != 0 && _g_.m.p.ptr().id < nprocs {
 8070ae9:	8b 44 24 5c          	mov    0x5c(%esp),%eax
/usr/local/lib/go/src/runtime/proc.go:3511
	for i := nprocs; i < old; i++ {
 8070aed:	8b 4c 24 14          	mov    0x14(%esp),%ecx
/usr/local/lib/go/src/runtime/proc.go:3479
		pp := allp[i]
 8070af1:	8d 15 80 97 0c 08    	lea    0x80c9780,%edx
/usr/local/lib/go/src/runtime/proc.go:3511
	for i := nprocs; i < old; i++ {
 8070af7:	8b 7c 24 0c          	mov    0xc(%esp),%edi
/usr/local/lib/go/src/runtime/proc.go:3545
		for i := range p.sudogbuf {
 8070afb:	e9 a0 fc ff ff       	jmp    80707a0 <runtime.procresize+0x270>
/usr/local/lib/go/src/runtime/proc.go:3540
			globrunqput(gp)
 8070b00:	8d 0d 58 92 0c 08    	lea    0x80c9258,%ecx
 8070b06:	84 01                	test   %al,(%ecx)
 8070b08:	89 c1                	mov    %eax,%ecx
 8070b0a:	89 0d 58 92 0c 08    	mov    %ecx,0x80c9258
 8070b10:	eb a2                	jmp    8070ab4 <runtime.procresize+0x584>
/usr/local/lib/go/src/runtime/proc.go:3538
				traceGoUnpark(gp, 0)
 8070b12:	8b 44 24 50          	mov    0x50(%esp),%eax
 8070b16:	89 04 24             	mov    %eax,(%esp)
 8070b19:	c7 44 24 04 00 00 00 	movl   $0x0,0x4(%esp)
 8070b20:	00 
 8070b21:	e8 ea d1 00 00       	call   807dd10 <runtime.traceGoUnpark>
/usr/local/lib/go/src/runtime/proc.go:3540
			globrunqput(gp)
 8070b26:	e9 6a ff ff ff       	jmp    8070a95 <runtime.procresize+0x565>
/usr/local/lib/go/src/runtime/proc.go:3517
				traceGoSched()
 8070b2b:	e8 70 d0 00 00       	call   807dba0 <runtime.traceGoSched>
/usr/local/lib/go/src/runtime/proc.go:3518
				traceProcStop(p)
 8070b30:	8b 44 24 44          	mov    0x44(%esp),%eax
 8070b34:	89 04 24             	mov    %eax,(%esp)
 8070b37:	e8 64 ca 00 00       	call   807d5a0 <runtime.traceProcStop>
/usr/local/lib/go/src/runtime/proc.go:3568
	if _g_.m.p != 0 && _g_.m.p.ptr().id < nprocs {
 8070b3c:	8b 44 24 5c          	mov    0x5c(%esp),%eax
/usr/local/lib/go/src/runtime/proc.go:3511
	for i := nprocs; i < old; i++ {
 8070b40:	8b 4c 24 14          	mov    0x14(%esp),%ecx
/usr/local/lib/go/src/runtime/proc.go:3479
		pp := allp[i]
 8070b44:	8d 15 80 97 0c 08    	lea    0x80c9780,%edx
/usr/local/lib/go/src/runtime/proc.go:3522
		for p.runqhead != p.runqtail {
 8070b4a:	8b 5c 24 44          	mov    0x44(%esp),%ebx
/usr/local/lib/go/src/runtime/proc.go:3511
	for i := nprocs; i < old; i++ {
 8070b4e:	8b 7c 24 0c          	mov    0xc(%esp),%edi
/usr/local/lib/go/src/runtime/proc.go:3522
		for p.runqhead != p.runqtail {
 8070b52:	e9 71 fb ff ff       	jmp    80706c8 <runtime.procresize+0x198>
/usr/local/lib/go/src/runtime/proc.go:3512
		p := allp[i]
 8070b57:	e8 64 58 ff ff       	call   80663c0 <runtime.panicindex>
 8070b5c:	0f 0b                	ud2    
/usr/local/lib/go/src/runtime/proc.go:3491
			if old == 0 && i == 0 {
 8070b5e:	85 ff                	test   %edi,%edi
 8070b60:	75 3e                	jne    8070ba0 <runtime.procresize+0x670>
 8070b62:	85 c0                	test   %eax,%eax
 8070b64:	75 3a                	jne    8070ba0 <runtime.procresize+0x670>
/usr/local/lib/go/src/runtime/proc.go:3492
				if getg().m.mcache == nil {
 8070b66:	65 8b 2d 00 00 00 00 	mov    %gs:0x0,%ebp
 8070b6d:	8b ad fc ff ff ff    	mov    -0x4(%ebp),%ebp
 8070b73:	8b 6d 18             	mov    0x18(%ebp),%ebp
 8070b76:	8b ad b8 00 00 00    	mov    0xb8(%ebp),%ebp
 8070b7c:	85 ed                	test   %ebp,%ebp
 8070b7e:	74 08                	je     8070b88 <runtime.procresize+0x658>
 // ######################## getg().m.mcache是什么时候初始化的 mallocinit Q1 ??????
 
 
 
/usr/local/lib/go/src/runtime/proc.go:3495
				pp.mcache = getg().m.mcache // bootstrap
 8070b80:	89 6b 1c             	mov    %ebp,0x1c(%ebx)
/usr/local/lib/go/src/runtime/proc.go:3478
	for i := int32(0); i < nprocs; i++ {
 8070b83:	e9 e4 fa ff ff       	jmp    807066c <runtime.procresize+0x13c>
/usr/local/lib/go/src/runtime/proc.go:3493
					throw("missing mcache?")
 8070b88:	8d 05 f6 ef 09 08    	lea    0x809eff6,%eax
 8070b8e:	89 04 24             	mov    %eax,(%esp)
 8070b91:	c7 44 24 04 0f 00 00 	movl   $0xf,0x4(%esp)
 8070b98:	00 
 8070b99:	e8 f2 6d ff ff       	call   8067990 <runtime.throw>
 8070b9e:	0f 0b                	ud2    
/usr/local/lib/go/src/runtime/proc.go:3497
				pp.mcache = allocmcache()
 8070ba0:	e8 7b 42 fe ff       	call   8054e20 <runtime.allocmcache>
 8070ba5:	8b 04 24             	mov    (%esp),%eax
 8070ba8:	8b 4c 24 38          	mov    0x38(%esp),%ecx
 8070bac:	89 41 1c             	mov    %eax,0x1c(%ecx)
/usr/local/lib/go/src/runtime/proc.go:3478
	for i := int32(0); i < nprocs; i++ {
 8070baf:	8b 44 24 20          	mov    0x20(%esp),%eax
 8070bb3:	8b 4c 24 5c          	mov    0x5c(%esp),%ecx
/usr/local/lib/go/src/runtime/proc.go:3479
		pp := allp[i]
 8070bb7:	8d 15 80 97 0c 08    	lea    0x80c9780,%edx
/usr/local/lib/go/src/runtime/proc.go:3491
			if old == 0 && i == 0 {
 8070bbd:	8b 7c 24 0c          	mov    0xc(%esp),%edi
/usr/local/lib/go/src/runtime/proc.go:3478
	for i := int32(0); i < nprocs; i++ {
 8070bc1:	e9 a6 fa ff ff       	jmp    807066c <runtime.procresize+0x13c>
/usr/local/lib/go/src/runtime/proc.go:3481
			pp = new(p)
 8070bc6:	8d 1d 40 c9 09 08    	lea    0x809c940,%ebx
 8070bcc:	89 1c 24             	mov    %ebx,(%esp)
 8070bcf:	e8 1c 13 fe ff       	call   8051ef0 <runtime.newobject>
 8070bd4:	8b 44 24 04          	mov    0x4(%esp),%eax
 8070bd8:	89 44 24 38          	mov    %eax,0x38(%esp)
/usr/local/lib/go/src/runtime/proc.go:3482
			pp.id = i
 8070bdc:	8b 4c 24 20          	mov    0x20(%esp),%ecx
 8070be0:	89 48 04             	mov    %ecx,0x4(%eax)
/usr/local/lib/go/src/runtime/proc.go:3483
			pp.status = _Pgcstop
 8070be3:	c7 40 08 03 00 00 00 	movl   $0x3,0x8(%eax)
/usr/local/lib/go/src/runtime/proc.go:3484
			pp.sudogcache = pp.sudogbuf[:0]
 8070bea:	8d 90 10 07 00 00    	lea    0x710(%eax),%edx
 8070bf0:	84 02                	test   %al,(%edx)
 8070bf2:	c7 80 08 07 00 00 00 	movl   $0x0,0x708(%eax)
 8070bf9:	00 00 00 
 8070bfc:	c7 80 0c 07 00 00 80 	movl   $0x80,0x70c(%eax)
 8070c03:	00 00 00 
 8070c06:	8b 1d 80 8e 0d 08    	mov    0x80d8e80,%ebx
 8070c0c:	8d a8 04 07 00 00    	lea    0x704(%eax),%ebp
 8070c12:	85 db                	test   %ebx,%ebx
 8070c14:	0f 85 99 00 00 00    	jne    8070cb3 <runtime.procresize+0x783>
 8070c1a:	89 90 04 07 00 00    	mov    %edx,0x704(%eax)
 8070c20:	31 d2                	xor    %edx,%edx
/usr/local/lib/go/src/runtime/proc.go:3485
			for i := range pp.deferpool {
 8070c22:	89 54 24 1c          	mov    %edx,0x1c(%esp)
 8070c26:	83 fa 05             	cmp    $0x5,%edx
 8070c29:	7d 3c                	jge    8070c67 <runtime.procresize+0x737>
/usr/local/lib/go/src/runtime/proc.go:3486
				pp.deferpool[i] = pp.deferpoolbuf[i][:0]
 8070c2b:	73 7f                	jae    8070cac <runtime.procresize+0x77c>
 8070c2d:	8d 1c 52             	lea    (%edx,%edx,2),%ebx
 8070c30:	c7 44 98 28 00 00 00 	movl   $0x0,0x28(%eax,%ebx,4)
 8070c37:	00 
 8070c38:	c7 44 98 2c 20 00 00 	movl   $0x20,0x2c(%eax,%ebx,4)
 8070c3f:	00 
 8070c40:	89 d5                	mov    %edx,%ebp
 8070c42:	c1 e2 07             	shl    $0x7,%edx
 8070c45:	8d 54 10 60          	lea    0x60(%eax,%edx,1),%edx
 8070c49:	8d 74 98 24          	lea    0x24(%eax,%ebx,4),%esi
 8070c4d:	8b 3d 80 8e 0d 08    	mov    0x80d8e80,%edi
 8070c53:	85 ff                	test   %edi,%edi
 8070c55:	75 3b                	jne    8070c92 <runtime.procresize+0x762>
 8070c57:	89 54 98 24          	mov    %edx,0x24(%eax,%ebx,4)
/usr/local/lib/go/src/runtime/proc.go:3485
			for i := range pp.deferpool {
 8070c5b:	8d 55 01             	lea    0x1(%ebp),%edx
 8070c5e:	89 54 24 1c          	mov    %edx,0x1c(%esp)
 8070c62:	83 fa 05             	cmp    $0x5,%edx
 8070c65:	7c c4                	jl     8070c2b <runtime.procresize+0x6fb>
/usr/local/lib/go/src/runtime/proc.go:3488
			atomicstorep(unsafe.Pointer(&allp[i]), unsafe.Pointer(pp))
 8070c67:	8b 54 24 54          	mov    0x54(%esp),%edx
 8070c6b:	89 14 24             	mov    %edx,(%esp)
 8070c6e:	89 44 24 04          	mov    %eax,0x4(%esp)
 8070c72:	e8 d9 93 fd ff       	call   804a050 <runtime.atomicstorep>
/usr/local/lib/go/src/runtime/proc.go:3491
			if old == 0 && i == 0 {
 8070c77:	8b 44 24 20          	mov    0x20(%esp),%eax
/usr/local/lib/go/src/runtime/proc.go:3478
	for i := int32(0); i < nprocs; i++ {
 8070c7b:	8b 4c 24 5c          	mov    0x5c(%esp),%ecx
/usr/local/lib/go/src/runtime/proc.go:3479
		pp := allp[i]
 8070c7f:	8d 15 80 97 0c 08    	lea    0x80c9780,%edx
/usr/local/lib/go/src/runtime/proc.go:3491
			if old == 0 && i == 0 {
 8070c85:	8b 7c 24 0c          	mov    0xc(%esp),%edi
/usr/local/lib/go/src/runtime/proc.go:3490
		if pp.mcache == nil {
 8070c89:	8b 5c 24 38          	mov    0x38(%esp),%ebx
 8070c8d:	e9 cb f9 ff ff       	jmp    807065d <runtime.procresize+0x12d>
/usr/local/lib/go/src/runtime/proc.go:3486
				pp.deferpool[i] = pp.deferpoolbuf[i][:0]
 8070c92:	89 34 24             	mov    %esi,(%esp)
 8070c95:	89 54 24 04          	mov    %edx,0x4(%esp)
 8070c99:	e8 02 1a fe ff       	call   80526a0 <runtime.writebarrierptr>
 8070c9e:	8b 44 24 38          	mov    0x38(%esp),%eax
/usr/local/lib/go/src/runtime/proc.go:3491
			if old == 0 && i == 0 {
 8070ca2:	8b 4c 24 20          	mov    0x20(%esp),%ecx
/usr/local/lib/go/src/runtime/proc.go:3485
			for i := range pp.deferpool {
 8070ca6:	8b 6c 24 1c          	mov    0x1c(%esp),%ebp
 8070caa:	eb af                	jmp    8070c5b <runtime.procresize+0x72b>
/usr/local/lib/go/src/runtime/proc.go:3486
				pp.deferpool[i] = pp.deferpoolbuf[i][:0]
 8070cac:	e8 0f 57 ff ff       	call   80663c0 <runtime.panicindex>
 8070cb1:	0f 0b                	ud2    
/usr/local/lib/go/src/runtime/proc.go:3484
			pp.sudogcache = pp.sudogbuf[:0]
 8070cb3:	89 2c 24             	mov    %ebp,(%esp)
 8070cb6:	89 54 24 04          	mov    %edx,0x4(%esp)
 8070cba:	e8 e1 19 fe ff       	call   80526a0 <runtime.writebarrierptr>
/usr/local/lib/go/src/runtime/proc.go:3486
				pp.deferpool[i] = pp.deferpoolbuf[i][:0]
 8070cbf:	8b 44 24 38          	mov    0x38(%esp),%eax
/usr/local/lib/go/src/runtime/proc.go:3491
			if old == 0 && i == 0 {
 8070cc3:	8b 4c 24 20          	mov    0x20(%esp),%ecx
/usr/local/lib/go/src/runtime/proc.go:3484
			pp.sudogcache = pp.sudogbuf[:0]
 8070cc7:	e9 54 ff ff ff       	jmp    8070c20 <runtime.procresize+0x6f0>
/usr/local/lib/go/src/runtime/proc.go:3479
		pp := allp[i]
 8070ccc:	e8 ef 56 ff ff       	call   80663c0 <runtime.panicindex>
 8070cd1:	0f 0b                	ud2    
/usr/local/lib/go/src/runtime/proc.go:3475
	sched.procresizetime = now
 8070cd3:	89 ca                	mov    %ecx,%edx
/usr/local/lib/go/src/runtime/proc.go:3491
			if old == 0 && i == 0 {
 8070cd5:	8b 7c 24 0c          	mov    0xc(%esp),%edi
/usr/local/lib/go/src/runtime/proc.go:3475
	sched.procresizetime = now
 8070cd9:	e9 3e f9 ff ff       	jmp    807061c <runtime.procresize+0xec>
/usr/local/lib/go/src/runtime/proc.go:3467
		traceGomaxprocs(nprocs)
 8070cde:	89 0c 24             	mov    %ecx,(%esp)
 8070ce1:	e8 ca c7 00 00       	call   807d4b0 <runtime.traceGomaxprocs>
/usr/local/lib/go/src/runtime/proc.go:3473
		sched.totaltime += int64(old) * (now - sched.procresizetime)
 8070ce6:	8b 44 24 0c          	mov    0xc(%esp),%eax
/usr/local/lib/go/src/runtime/proc.go:3478
	for i := int32(0); i < nprocs; i++ {
 8070cea:	8b 4c 24 5c          	mov    0x5c(%esp),%ecx
/usr/local/lib/go/src/runtime/proc.go:3471
	now := nanotime()
 8070cee:	e9 92 f8 ff ff       	jmp    8070585 <runtime.procresize+0x55>
/usr/local/lib/go/src/runtime/proc.go:3464
		throw("procresize: invalid arg")
 8070cf3:	8d 05 a5 fd 09 08    	lea    0x809fda5,%eax
 8070cf9:	89 04 24             	mov    %eax,(%esp)
 8070cfc:	c7 44 24 04 17 00 00 	movl   $0x17,0x4(%esp)
 8070d03:	00 
 8070d04:	e8 87 6c ff ff       	call   8067990 <runtime.throw>
 8070d09:	0f 0b                	ud2    
/usr/local/lib/go/src/runtime/proc.go:3461
func procresize(nprocs int32) *p {
 8070d0b:	e8 20 56 01 00       	call   8086330 <runtime.morestack_noctxt>
 8070d10:	e9 1b f8 ff ff       	jmp    8070530 <runtime.procresize>
 8070d15:	cc                   	int3   
 8070d16:	cc                   	int3   
 8070d17:	cc                   	int3   
 8070d18:	cc                   	int3   
 8070d19:	cc                   	int3   
 8070d1a:	cc                   	int3   
 8070d1b:	cc                   	int3   
 8070d1c:	cc                   	int3   
 8070d1d:	cc                   	int3   
 8070d1e:	cc                   	int3   
 8070d1f:	cc                   	int3   

~~~

