# newproc1 续 gfget





### p的定义

~~~go
type p struct {
	lock mutex

	id          int32
	status      uint32 // one of pidle/prunning/...
	link        puintptr
	schedtick   uint32     // incremented on every scheduler call
	syscalltick uint32     // incremented on every system call
	sysmontick  sysmontick // last tick observed by sysmon
	m           muintptr   // back-link to associated m (nil if idle)
	mcache      *mcache
	racectx     uintptr

	deferpool    [5][]*_defer // pool of available defer structs of different sizes (see panic.go)
	deferpoolbuf [5][32]*_defer

	// Cache of goroutine ids, amortizes accesses to runtime·sched.goidgen.
	goidcache    uint64
	goidcacheend uint64

	// Queue of runnable goroutines. Accessed without lock.
	runqhead uint32
	runqtail uint32
	runq     [256]guintptr
	// runnext, if non-nil, is a runnable G that was ready'd by
	// the current G and should be run next instead of what's in
	// runq if there's time remaining in the running G's time
	// slice. It will inherit the time left in the current time
	// slice. If a set of goroutines is locked in a
	// communicate-and-wait pattern, this schedules that set as a
	// unit and eliminates the (potentially large) scheduling
	// latency that otherwise arises from adding the ready'd
	// goroutines to the end of the run queue.
	runnext guintptr

	// Available G's (status == Gdead)
	gfree    *g
	gfreecnt int32

	sudogcache []*sudog
	sudogbuf   [128]*sudog

	tracebuf traceBufPtr

	// traceSweep indicates the sweep events should be traced.
	// This is used to defer the sweep start event until a span
	// has actually been swept.
	traceSweep bool
	// traceSwept and traceReclaimed track the number of bytes
	// swept and reclaimed by sweeping in the current sweep loop.
	traceSwept, traceReclaimed uintptr

	palloc persistentAlloc // per-P to avoid mutex

	// Per-P GC state
	gcAssistTime         int64 // Nanoseconds in assistAlloc
	gcFractionalMarkTime int64 // Nanoseconds in fractional mark worker
	gcBgMarkWorker       guintptr
	gcMarkWorkerMode     gcMarkWorkerMode

	// gcMarkWorkerStartTime is the nanotime() at which this mark
	// worker started.
	gcMarkWorkerStartTime int64

	// gcw is this P's GC work buffer cache. The work buffer is
	// filled by write barriers, drained by mutator assists, and
	// disposed on certain GC state transitions.
	gcw gcWork

	// wbBuf is this P's GC write barrier buffer.
	//
	// TODO: Consider caching this in the running G.
	wbBuf wbBuf

	runSafePointFn uint32 // if 1, run sched.safePointFn at next safe point

	pad [sys.CacheLineSize]byte
}
~~~



### gfget

runtime/proc.go



~~~go
/ Get from gfree list.
// If local list is empty, grab a batch from global list.
func gfget(_p_ *p) *g {
retry:
	gp := _p_.gfree
	if gp == nil && (sched.gfreeStack != nil || sched.gfreeNoStack != nil) {
		lock(&sched.gflock)
		for _p_.gfreecnt < 32 {
			if sched.gfreeStack != nil {
				// Prefer Gs with stacks.
				gp = sched.gfreeStack
				sched.gfreeStack = gp.schedlink.ptr()
			} else if sched.gfreeNoStack != nil {
				gp = sched.gfreeNoStack
				sched.gfreeNoStack = gp.schedlink.ptr()
			} else {
				break
			}
			_p_.gfreecnt++
			sched.ngfree--
			gp.schedlink.set(_p_.gfree)
			_p_.gfree = gp
		}
		unlock(&sched.gflock)
		goto retry
	}
	if gp != nil {
		_p_.gfree = gp.schedlink.ptr()
		_p_.gfreecnt--
		if gp.stack.lo == 0 {
			// Stack was deallocated in gfput. Allocate a new one.
			systemstack(func() {
				gp.stack = stackalloc(_FixedStack)
			})
			gp.stackguard0 = gp.stack.lo + _StackGuard
		} else {
			if raceenabled {
				racemalloc(unsafe.Pointer(gp.stack.lo), gp.stack.hi-gp.stack.lo)
			}
			if msanenabled {
				msanmalloc(unsafe.Pointer(gp.stack.lo), gp.stack.hi-gp.stack.lo)
			}
		}
	}
	return gp
}

~~~



/ Get from gfree list.

// If local list is empty, grab a batch from global list.

func gfget(_p_ *p) *g {

retry:

​    gp := _p_.gfree

​    if gp == nil && (sched.gfreeStack != nil || sched.gfreeNoStack != nil) {

​        lock(&sched.gflock)

​        for _p_.gfreecnt < 32 {

​            if sched.gfreeStack != nil {

​                // Prefer Gs with stacks.

​                gp = sched.gfreeStack

​                sched.gfreeStack = gp.schedlink.ptr()

​            } else if sched.gfreeNoStack != nil {

​                gp = sched.gfreeNoStack

​                sched.gfreeNoStack = gp.schedlink.ptr()

​            } else {

​                break

​            }

​            _p_.gfreecnt++

​            sched.ngfree--

​            gp.schedlink.set(_p_.gfree)

​            _p_.gfree = gp

​        }

​        unlock(&sched.gflock)

​        goto retry

​    }

​    if gp != nil {

​        _p_.gfree = gp.schedlink.ptr()

​        _p_.gfreecnt--

​        if gp.stack.lo == 0 {

​            // Stack was deallocated in gfput. Allocate a new one.

​            systemstack(func() {

​                gp.stack = stackalloc(_FixedStack)

​            })

​            gp.stackguard0 = gp.stack.lo + _StackGuard

​        } else {

​            if raceenabled {

​                racemalloc(unsafe.Pointer(gp.stack.lo), gp.stack.hi-gp.stack.lo)

​            }

​            if msanenabled {

​                msanmalloc(unsafe.Pointer(gp.stack.lo), gp.stack.hi-gp.stack.lo)

​            }

​        }

​    }

​    return gp

}





~~~assembly

0806fa00 <runtime.gfget>:
runtime.gfget():
/usr/local/lib/go/src/runtime/proc.go:3014

// Get from gfree list.
// If local list is empty, grab a batch from global list.
func gfget(_p_ *p) *g {
 806fa00:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
 806fa07:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx
 806fa0d:	3b 61 08             	cmp    0x8(%ecx),%esp
 806fa10:	0f 86 d8 01 00 00    	jbe    806fbee <runtime.gfget+0x1ee>
 806fa16:	83 ec 18             	sub    $0x18,%esp
/usr/local/lib/go/src/runtime/proc.go:3016
retry:
	gp := _p_.gfree
 806fa19:	8b 44 24 1c          	mov    0x1c(%esp),%eax
 //############# eax = _p_ ，参数_p_
 
 806fa1d:	8b 88 fc 06 00 00    	mov    0x6fc(%eax),%ecx
 // ######### ecx= _p_.gfree
 
 806fa23:	89 4c 24 08          	mov    %ecx,0x8(%esp)
 
 
/usr/local/lib/go/src/runtime/proc.go:3017
	if gp == nil && (sched.gfreeStack != nil || sched.gfreeNoStack != nil) {
 806fa27:	85 c9                	test   %ecx,%ecx
 806fa29:	0f 85 3a 01 00 00    	jne    806fb69 <runtime.gfget+0x169>
 //############## gp != nil 跳转  sched 地址0x80c9220 
 // ####  sched.greeStack的偏移为 0x48  sched.gfreeNoStack的偏移为0x4c 
 
 806fa2f:	8b 15 68 92 0c 08    	mov    0x80c9268,%edx
 806fa35:	85 d2                	test   %edx,%edx
 806fa37:	0f 84 1b 01 00 00    	je     806fb58 <runtime.gfget+0x158>
/usr/local/lib/go/src/runtime/proc.go:3018
​		lock(&sched.gflock)
 806fa3d:	8d 0d 64 92 0c 08    	lea    0x80c9264,%ecx
 806fa43:	89 0c 24             	mov    %ecx,(%esp)
 806fa46:	e8 35 09 fe ff       	call   8050380 <runtime.lock>
/usr/local/lib/go/src/runtime/proc.go:3019
​		for _p_.gfreecnt < 32 {
 806fa4b:	8b 44 24 1c          	mov    0x1c(%esp),%eax
 806fa4f:	8b 88 00 07 00 00    	mov    0x700(%eax),%ecx
 806fa55:	83 f9 20             	cmp    $0x20,%ecx
 806fa58:	7d 72                	jge    806facc <runtime.gfget+0xcc>
/usr/local/lib/go/src/runtime/proc.go:3020
​			if sched.gfreeStack != nil {
 806fa5a:	8b 0d 68 92 0c 08    	mov    0x80c9268,%ecx
 806fa60:	89 4c 24 0c          	mov    %ecx,0xc(%esp)
 806fa64:	85 c9                	test   %ecx,%ecx
 806fa66:	0f 84 a7 00 00 00    	je     806fb13 <runtime.gfget+0x113>
/usr/local/lib/go/src/runtime/proc.go:3023
​				// Prefer Gs with stacks.
​				gp = sched.gfreeStack
​				sched.gfreeStack = gp.schedlink.ptr()
 806fa6c:	8b 51 7c             	mov    0x7c(%ecx),%edx
 806fa6f:	8b 1d 80 8e 0d 08    	mov    0x80d8e80,%ebx
 806fa75:	85 db                	test   %ebx,%ebx
 806fa77:	75 7b                	jne    806faf4 <runtime.gfget+0xf4>
 806fa79:	89 15 68 92 0c 08    	mov    %edx,0x80c9268
/usr/local/lib/go/src/runtime/proc.go:3030
​				gp = sched.gfreeNoStack
​				sched.gfreeNoStack = gp.schedlink.ptr()
​			} else {
​				break
​			}
​			_p_.gfreecnt++
 806fa7f:	8b 90 00 07 00 00    	mov    0x700(%eax),%edx
 806fa85:	42                   	inc    %edx
 806fa86:	89 90 00 07 00 00    	mov    %edx,0x700(%eax)
/usr/local/lib/go/src/runtime/proc.go:3031
​			sched.ngfree--
 806fa8c:	8b 15 70 92 0c 08    	mov    0x80c9270,%edx
 806fa92:	4a                   	dec    %edx
 806fa93:	89 15 70 92 0c 08    	mov    %edx,0x80c9270
/usr/local/lib/go/src/runtime/proc.go:3032
​			gp.schedlink.set(_p_.gfree)
 806fa99:	8d 51 7c             	lea    0x7c(%ecx),%edx
 806fa9c:	84 02                	test   %al,(%edx)
 806fa9e:	8b 90 fc 06 00 00    	mov    0x6fc(%eax),%edx
 806faa4:	89 51 7c             	mov    %edx,0x7c(%ecx)
/usr/local/lib/go/src/runtime/proc.go:3033
​			_p_.gfree = gp
 806faa7:	8b 15 80 8e 0d 08    	mov    0x80d8e80,%edx
 806faad:	8d 98 fc 06 00 00    	lea    0x6fc(%eax),%ebx
 806fab3:	85 d2                	test   %edx,%edx
 806fab5:	75 28                	jne    806fadf <runtime.gfget+0xdf>
 806fab7:	89 88 fc 06 00 00    	mov    %ecx,0x6fc(%eax)
/usr/local/lib/go/src/runtime/proc.go:3019
​		for _p_.gfreecnt < 32 {
 806fabd:	8b 44 24 1c          	mov    0x1c(%esp),%eax
 806fac1:	8b 88 00 07 00 00    	mov    0x700(%eax),%ecx
 806fac7:	83 f9 20             	cmp    $0x20,%ecx
 806faca:	7c 8e                	jl     806fa5a <runtime.gfget+0x5a>
/usr/local/lib/go/src/runtime/proc.go:3018
​		lock(&sched.gflock)
 806facc:	8d 0d 64 92 0c 08    	lea    0x80c9264,%ecx
/usr/local/lib/go/src/runtime/proc.go:3035
​		}
​		unlock(&sched.gflock)
 806fad2:	89 0c 24             	mov    %ecx,(%esp)
 806fad5:	e8 86 0a fe ff       	call   8050560 <runtime.unlock>
/usr/local/lib/go/src/runtime/proc.go:3016
​	gp := _p_.gfree
 806fada:	e9 3a ff ff ff       	jmp    806fa19 <runtime.gfget+0x19>
/usr/local/lib/go/src/runtime/proc.go:3033
​			_p_.gfree = gp
 806fadf:	89 1c 24             	mov    %ebx,(%esp)
 806fae2:	89 4c 24 04          	mov    %ecx,0x4(%esp)
 806fae6:	e8 b5 2b fe ff       	call   80526a0 <runtime.writebarrierptr>
/usr/local/lib/go/src/runtime/proc.go:3019
​		for _p_.gfreecnt < 32 {
 806faeb:	8b 44 24 1c          	mov    0x1c(%esp),%eax
 806faef:	e9 57 ff ff ff       	jmp    806fa4b <runtime.gfget+0x4b>
/usr/local/lib/go/src/runtime/proc.go:3017
​	if gp == nil && (sched.gfreeStack != nil || sched.gfreeNoStack != nil) {
 806faf4:	8d 1d 68 92 0c 08    	lea    0x80c9268,%ebx
/usr/local/lib/go/src/runtime/proc.go:3023
​				sched.gfreeStack = gp.schedlink.ptr()
 806fafa:	89 1c 24             	mov    %ebx,(%esp)
 806fafd:	89 54 24 04          	mov    %edx,0x4(%esp)
 806fb01:	e8 9a 2b fe ff       	call   80526a0 <runtime.writebarrierptr>
/usr/local/lib/go/src/runtime/proc.go:3030
​			_p_.gfreecnt++
 806fb06:	8b 44 24 1c          	mov    0x1c(%esp),%eax
/usr/local/lib/go/src/runtime/proc.go:3032
​			gp.schedlink.set(_p_.gfree)
 806fb0a:	8b 4c 24 0c          	mov    0xc(%esp),%ecx
/usr/local/lib/go/src/runtime/proc.go:3030
​			_p_.gfreecnt++
 806fb0e:	e9 6c ff ff ff       	jmp    806fa7f <runtime.gfget+0x7f>
/usr/local/lib/go/src/runtime/proc.go:3024
​			} else if sched.gfreeNoStack != nil {
 806fb13:	8b 0d 6c 92 0c 08    	mov    0x80c926c,%ecx
 806fb19:	89 4c 24 0c          	mov    %ecx,0xc(%esp)
 806fb1d:	85 c9                	test   %ecx,%ecx
 806fb1f:	74 ab                	je     806facc <runtime.gfget+0xcc>
/usr/local/lib/go/src/runtime/proc.go:3026
​				sched.gfreeNoStack = gp.schedlink.ptr()
 806fb21:	8b 15 80 8e 0d 08    	mov    0x80d8e80,%edx
 806fb27:	8b 59 7c             	mov    0x7c(%ecx),%ebx
 806fb2a:	85 d2                	test   %edx,%edx
 806fb2c:	75 0b                	jne    806fb39 <runtime.gfget+0x139>
 806fb2e:	89 1d 6c 92 0c 08    	mov    %ebx,0x80c926c
/usr/local/lib/go/src/runtime/proc.go:3030
​			_p_.gfreecnt++
 806fb34:	e9 46 ff ff ff       	jmp    806fa7f <runtime.gfget+0x7f>
/usr/local/lib/go/src/runtime/proc.go:3024
​			} else if sched.gfreeNoStack != nil {
 806fb39:	8d 15 6c 92 0c 08    	lea    0x80c926c,%edx
/usr/local/lib/go/src/runtime/proc.go:3026
​				sched.gfreeNoStack = gp.schedlink.ptr()
 806fb3f:	89 14 24             	mov    %edx,(%esp)
 806fb42:	89 5c 24 04          	mov    %ebx,0x4(%esp)
 806fb46:	e8 55 2b fe ff       	call   80526a0 <runtime.writebarrierptr>
/usr/local/lib/go/src/runtime/proc.go:3030
​			_p_.gfreecnt++
 806fb4b:	8b 44 24 1c          	mov    0x1c(%esp),%eax
/usr/local/lib/go/src/runtime/proc.go:3032
​			gp.schedlink.set(_p_.gfree)
 806fb4f:	8b 4c 24 0c          	mov    0xc(%esp),%ecx
/usr/local/lib/go/src/runtime/proc.go:3030
​			_p_.gfreecnt++
 806fb53:	e9 27 ff ff ff       	jmp    806fa7f <runtime.gfget+0x7f>
 
 
 //################### 
/usr/local/lib/go/src/runtime/proc.go:3017
​	if gp == nil && (sched.gfreeStack != nil || sched.gfreeNoStack != nil) {
 806fb58:	8b 15 6c 92 0c 08    	mov    0x80c926c,%edx
 806fb5e:	85 d2                	test   %edx,%edx
 806fb60:	74 05                	je     806fb67 <runtime.gfget+0x167>
 // ########### sched.gfreeNoStack 是否为空
 
/usr/local/lib/go/src/runtime/proc.go:3018
​		lock(&sched.gflock)
 806fb62:	e9 d6 fe ff ff       	jmp    806fa3d <runtime.gfget+0x3d>
/usr/local/lib/go/src/runtime/proc.go:3017
​	if gp == nil && (sched.gfreeStack != nil || sched.gfreeNoStack != nil) {
 806fb67:	85 c9                	test   %ecx,%ecx
/usr/local/lib/go/src/runtime/proc.go:3038
​		goto retry
​	}



//###########################
​	if gp != nil {
 806fb69:	74 2c                	je     806fb97 <runtime.gfget+0x197>
/usr/local/lib/go/src/runtime/proc.go:3039
​		_p_.gfree = gp.schedlink.ptr()
 806fb6b:	8b 15 80 8e 0d 08    	mov    0x80d8e80,%edx
 806fb71:	8b 59 7c             	mov    0x7c(%ecx),%ebx
 806fb74:	8d a8 fc 06 00 00    	lea    0x6fc(%eax),%ebp
 806fb7a:	85 d2                	test   %edx,%edx
 806fb7c:	75 5a                	jne    806fbd8 <runtime.gfget+0x1d8>
 806fb7e:	89 98 fc 06 00 00    	mov    %ebx,0x6fc(%eax)
/usr/local/lib/go/src/runtime/proc.go:3040
​		_p_.gfreecnt--
 806fb84:	8b 90 00 07 00 00    	mov    0x700(%eax),%edx
 806fb8a:	4a                   	dec    %edx
 806fb8b:	89 90 00 07 00 00    	mov    %edx,0x700(%eax)
/usr/local/lib/go/src/runtime/proc.go:3041
​		if gp.stack.lo == 0 {
 806fb91:	8b 01                	mov    (%ecx),%eax
 806fb93:	85 c0                	test   %eax,%eax
 806fb95:	74 08                	je     806fb9f <runtime.gfget+0x19f>
/usr/local/lib/go/src/runtime/proc.go:3057
​			if msanenabled {
​				msanmalloc(unsafe.Pointer(gp.stack.lo), gp.stackAlloc)
​			}
​		}
​	}
​	return gp
 806fb97:	89 4c 24 20          	mov    %ecx,0x20(%esp)
 806fb9b:	83 c4 18             	add    $0x18,%esp
 806fb9e:	c3                   	ret    
/usr/local/lib/go/src/runtime/proc.go:3043
​			systemstack(func() {
 806fb9f:	c7 44 24 10 00 00 00 	movl   $0x0,0x10(%esp)
 806fba6:	00 
 806fba7:	8d 05 20 5c 08 08    	lea    0x8085c20,%eax
 806fbad:	89 44 24 10          	mov    %eax,0x10(%esp)
 806fbb1:	89 4c 24 14          	mov    %ecx,0x14(%esp)
 806fbb5:	8d 44 24 10          	lea    0x10(%esp),%eax
/usr/local/lib/go/src/runtime/proc.go:3045
​			})
 806fbb9:	89 04 24             	mov    %eax,(%esp)
 806fbbc:	e8 4f 66 01 00       	call   8086210 <runtime.systemstack>
/usr/local/lib/go/src/runtime/proc.go:3046
​			gp.stackguard0 = gp.stack.lo + _StackGuard
 806fbc1:	8b 4c 24 08          	mov    0x8(%esp),%ecx
 806fbc5:	8b 01                	mov    (%ecx),%eax
 806fbc7:	05 70 03 00 00       	add    $0x370,%eax
 806fbcc:	89 41 08             	mov    %eax,0x8(%ecx)
/usr/local/lib/go/src/runtime/proc.go:3047
​			gp.stackAlloc = _FixedStack
 806fbcf:	c7 41 1c 00 08 00 00 	movl   $0x800,0x1c(%ecx)
/usr/local/lib/go/src/runtime/proc.go:3057
​	return gp
 806fbd6:	eb bf                	jmp    806fb97 <runtime.gfget+0x197>
/usr/local/lib/go/src/runtime/proc.go:3039
​		_p_.gfree = gp.schedlink.ptr()
 806fbd8:	89 2c 24             	mov    %ebp,(%esp)
 806fbdb:	89 5c 24 04          	mov    %ebx,0x4(%esp)
 806fbdf:	e8 bc 2a fe ff       	call   80526a0 <runtime.writebarrierptr>
/usr/local/lib/go/src/runtime/proc.go:3040
​		_p_.gfreecnt--
 806fbe4:	8b 44 24 1c          	mov    0x1c(%esp),%eax
/usr/local/lib/go/src/runtime/proc.go:3041
​		if gp.stack.lo == 0 {
 806fbe8:	8b 4c 24 08          	mov    0x8(%esp),%ecx
/usr/local/lib/go/src/runtime/proc.go:3040
​		_p_.gfreecnt--
 806fbec:	eb 96                	jmp    806fb84 <runtime.gfget+0x184>
/usr/local/lib/go/src/runtime/proc.go:3014
func gfget(_p_ *p) *g {
 806fbee:	e8 3d 67 01 00       	call   8086330 <runtime.morestack_noctxt>
 806fbf3:	e9 08 fe ff ff       	jmp    806fa00 <runtime.gfget>
 806fbf8:	cc                   	int3   
 806fbf9:	cc                   	int3   
 806fbfa:	cc                   	int3   
 806fbfb:	cc                   	int3   
 806fbfc:	cc                   	int3   
 806fbfd:	cc                   	int3   
 806fbfe:	cc                   	int3   
 806fbff:	cc                   	int3   
~~~

