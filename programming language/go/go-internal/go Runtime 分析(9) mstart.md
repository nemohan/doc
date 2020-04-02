# mstart

~~~assembly
0806b620 <runtime.mstart>:
runtime.mstart():
/usr/local/lib/go/src/runtime/proc.go:1132

// Called to start an M.
//go:nosplit
func mstart() {
 806b620:	83 ec 04             	sub    $0x4,%esp
/usr/local/lib/go/src/runtime/proc.go:1133
	_g_ := getg()
 806b623:	65 8b 05 00 00 00 00 	mov    %gs:0x0,%eax
 806b62a:	8b 80 fc ff ff ff    	mov    -0x4(%eax),%eax
/usr/local/lib/go/src/runtime/proc.go:1135

	if _g_.stack.lo == 0 {
 806b630:	8b 08                	mov    (%eax),%ecx
 806b632:	85 c9                	test   %ecx,%ecx
 806b634:	75 24                	jne    806b65a <runtime.mstart+0x3a>
/usr/local/lib/go/src/runtime/proc.go:1138
		// Initialize stack bounds from system stack.
		// Cgo may have left stack size in stack.hi.
		size := _g_.stack.hi
 806b636:	8b 48 04             	mov    0x4(%eax),%ecx
 806b639:	89 0c 24             	mov    %ecx,(%esp)
/usr/local/lib/go/src/runtime/proc.go:1139
		if size == 0 {
 806b63c:	85 c9                	test   %ecx,%ecx
 806b63e:	75 07                	jne    806b647 <runtime.mstart+0x27>
/usr/local/lib/go/src/runtime/proc.go:1140
			size = 8192 * sys.StackGuardMultiplier
 806b640:	c7 04 24 00 20 00 00 	movl   $0x2000,(%esp)
/usr/local/lib/go/src/runtime/proc.go:1138
		size := _g_.stack.hi
 806b647:	8d 0c 24             	lea    (%esp),%ecx
/usr/local/lib/go/src/runtime/proc.go:1142
		}
		_g_.stack.hi = uintptr(noescape(unsafe.Pointer(&size)))
 806b64a:	89 48 04             	mov    %ecx,0x4(%eax)
/usr/local/lib/go/src/runtime/proc.go:1143
		_g_.stack.lo = _g_.stack.hi - size + 1024
 806b64d:	8b 14 24             	mov    (%esp),%edx
 806b650:	29 d1                	sub    %edx,%ecx
 806b652:	81 c1 00 04 00 00    	add    $0x400,%ecx
 806b658:	89 08                	mov    %ecx,(%eax)
/usr/local/lib/go/src/runtime/proc.go:1147
	}
	// Initialize stack guards so that we can start calling
	// both Go and C functions with stack growth prologues.
	_g_.stackguard0 = _g_.stack.lo + _StackGuard
 806b65a:	8b 08                	mov    (%eax),%ecx
 806b65c:	81 c1 70 03 00 00    	add    $0x370,%ecx
 806b662:	89 48 08             	mov    %ecx,0x8(%eax)
/usr/local/lib/go/src/runtime/proc.go:1148
	_g_.stackguard1 = _g_.stackguard0
 806b665:	89 48 0c             	mov    %ecx,0xc(%eax)
/usr/local/lib/go/src/runtime/proc.go:1149
	mstart1()
 806b668:	e8 13 00 00 00       	call   806b680 <runtime.mstart1>
/usr/local/lib/go/src/runtime/proc.go:1150
}
 806b66d:	83 c4 04             	add    $0x4,%esp
 806b670:	c3                   	ret    
 806b671:	cc                   	int3   
 806b672:	cc                   	int3   
 806b673:	cc                   	int3   
 806b674:	cc                   	int3   
 806b675:	cc                   	int3   
 806b676:	cc                   	int3   
 806b677:	cc                   	int3   
 806b678:	cc                   	int3   
 806b679:	cc                   	int3   
 806b67a:	cc                   	int3   
 806b67b:	cc                   	int3   
 806b67c:	cc                   	int3   
 806b67d:	cc                   	int3   
 806b67e:	cc                   	int3   
 806b67f:	cc                   	int3   
~~~

~~~go
// Called to start an M.
//go:nosplit
func mstart() {
	_g_ := getg()

	if _g_.stack.lo == 0 {
		// Initialize stack bounds from system stack.
		// Cgo may have left stack size in stack.hi.
		size := _g_.stack.hi
		if size == 0 {
			size = 8192 * sys.StackGuardMultiplier
		}
		_g_.stack.hi = uintptr(noescape(unsafe.Pointer(&size)))
		_g_.stack.lo = _g_.stack.hi - size + 1024
	}
	// Initialize stack guards so that we can start calling
	// both Go and C functions with stack growth prologues.
	_g_.stackguard0 = _g_.stack.lo + _StackGuard
	_g_.stackguard1 = _g_.stackguard0
	mstart1()
}

func mstart1() {
	_g_ := getg()

	if _g_ != _g_.m.g0 {
		throw("bad runtime·mstart")
	}

	// Record top of stack for use by mcall.
	// Once we call schedule we're never coming back,
	// so other calls can reuse this stack space.
	gosave(&_g_.m.g0.sched)
	_g_.m.g0.sched.pc = ^uintptr(0) // make sure it is never used
	asminit()
	minit()

	// Install signal handlers; after minit so that minit can
	// prepare the thread to be able to handle the signals.
	if _g_.m == &m0 {
		// Create an extra M for callbacks on threads not created by Go.
		if iscgo && !cgoHasExtraM {
			cgoHasExtraM = true
			newextram()
		}
		initsig(false)
	}

	if fn := _g_.m.mstartfn; fn != nil {
		fn()
	}

	if _g_.m.helpgc != 0 {
		_g_.m.helpgc = 0
		stopm()
	} else if _g_.m != &m0 {
		acquirep(_g_.m.nextp.ptr())
		_g_.m.nextp = 0
	}
	schedule()
}

~~~





~~~assembly
0806b680 <runtime.mstart1>:
runtime.mstart1():
/usr/local/lib/go/src/runtime/proc.go:1152

func mstart1() {
 806b680:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
 806b687:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx
 806b68d:	3b 61 08             	cmp    0x8(%ecx),%esp
 806b690:	0f 86 0f 01 00 00    	jbe    806b7a5 <runtime.mstart1+0x125>
 806b696:	83 ec 0c             	sub    $0xc,%esp
/usr/local/lib/go/src/runtime/proc.go:1153
	_g_ := getg()
 806b699:	65 8b 05 00 00 00 00 	mov    %gs:0x0,%eax
 806b6a0:	8b 80 fc ff ff ff    	mov    -0x4(%eax),%eax
 806b6a6:	89 44 24 08          	mov    %eax,0x8(%esp)
/usr/local/lib/go/src/runtime/proc.go:1155

	if _g_ != _g_.m.g0 {
 806b6aa:	8b 48 18             	mov    0x18(%eax),%ecx
 806b6ad:	8b 09                	mov    (%ecx),%ecx
 806b6af:	39 c8                	cmp    %ecx,%eax
 806b6b1:	0f 85 d6 00 00 00    	jne    806b78d <runtime.mstart1+0x10d>
/usr/local/lib/go/src/runtime/proc.go:1162
	}

	// Record top of stack for use by mcall.
	// Once we call schedule we're never coming back,
	// so other calls can reuse this stack space.
	gosave(&_g_.m.g0.sched)
 806b6b7:	84 01                	test   %al,(%ecx)
 806b6b9:	83 c1 20             	add    $0x20,%ecx
 806b6bc:	89 0c 24             	mov    %ecx,(%esp)
 806b6bf:	e8 4c aa 01 00       	call   8086110 <runtime.gosave>
/usr/local/lib/go/src/runtime/proc.go:1163
	_g_.m.g0.sched.pc = ^uintptr(0) // make sure it is never used
 806b6c4:	8b 44 24 08          	mov    0x8(%esp),%eax
 806b6c8:	8b 48 18             	mov    0x18(%eax),%ecx
 806b6cb:	8b 09                	mov    (%ecx),%ecx
 806b6cd:	c7 41 24 ff ff ff ff 	movl   $0xffffffff,0x24(%ecx)
/usr/local/lib/go/src/runtime/proc.go:1164
	asminit()
 806b6d4:	e8 27 aa 01 00       	call   8086100 <runtime.asminit>
/usr/local/lib/go/src/runtime/proc.go:1165
	minit()
 806b6d9:	e8 e2 a9 ff ff       	call   80660c0 <runtime.minit>
/usr/local/lib/go/src/runtime/proc.go:1169

	// Install signal handlers; after minit so that minit can
	// prepare the thread to be able to handle the signals.
	if _g_.m == &m0 {
 806b6de:	8b 44 24 08          	mov    0x8(%esp),%eax
 806b6e2:	8b 48 18             	mov    0x18(%eax),%ecx
 806b6e5:	8d 15 20 95 0c 08    	lea    0x80c9520,%edx
 806b6eb:	39 d1                	cmp    %edx,%ecx
 806b6ed:	75 1f                	jne    806b70e <runtime.mstart1+0x8e>
/usr/local/lib/go/src/runtime/proc.go:1171
		// Create an extra M for callbacks on threads not created by Go.
		if iscgo && !cgoHasExtraM {
 806b6ef:	0f b6 0d 4b 8d 0d 08 	movzbl 0x80d8d4b,%ecx
 806b6f6:	84 c9                	test   %cl,%cl
 806b6f8:	74 0b                	je     806b705 <runtime.mstart1+0x85>
 806b6fa:	0f b6 0d 42 8d 0d 08 	movzbl 0x80d8d42,%ecx
 806b701:	84 c9                	test   %cl,%cl
 806b703:	74 6d                	je     806b772 <runtime.mstart1+0xf2>
/usr/local/lib/go/src/runtime/proc.go:1175
			cgoHasExtraM = true
			newextram()
		}
		initsig(false)
 806b705:	c6 04 24 00          	movb   $0x0,(%esp)
 806b709:	e8 d2 a5 00 00       	call   8075ce0 <runtime.initsig>
/usr/local/lib/go/src/runtime/proc.go:1178
	}

	if fn := _g_.m.mstartfn; fn != nil {
 806b70e:	8b 44 24 08          	mov    0x8(%esp),%eax
 806b712:	8b 48 18             	mov    0x18(%eax),%ecx
 806b715:	8b 51 50             	mov    0x50(%ecx),%edx
 806b718:	85 d2                	test   %edx,%edx
 806b71a:	75 4c                	jne    806b768 <runtime.mstart1+0xe8>
/usr/local/lib/go/src/runtime/proc.go:1182
		fn()
	}

	if _g_.m.helpgc != 0 {
 806b71c:	8b 48 18             	mov    0x18(%eax),%ecx
 806b71f:	8b 91 88 00 00 00    	mov    0x88(%ecx),%edx
 806b725:	85 d2                	test   %edx,%edx
 806b727:	75 2e                	jne    806b757 <runtime.mstart1+0xd7>
/usr/local/lib/go/src/runtime/proc.go:1169
	if _g_.m == &m0 {
 806b729:	8d 15 20 95 0c 08    	lea    0x80c9520,%edx
/usr/local/lib/go/src/runtime/proc.go:1185
		_g_.m.helpgc = 0
		stopm()
	} else if _g_.m != &m0 {
 806b72f:	39 d1                	cmp    %edx,%ecx
 806b731:	75 09                	jne    806b73c <runtime.mstart1+0xbc>
/usr/local/lib/go/src/runtime/proc.go:1189
		acquirep(_g_.m.nextp.ptr())
		_g_.m.nextp = 0
	}
	schedule()
 806b733:	e8 f8 23 00 00       	call   806db30 <runtime.schedule>
/usr/local/lib/go/src/runtime/proc.go:1190
}
 806b738:	83 c4 0c             	add    $0xc,%esp
 806b73b:	c3                   	ret    
/usr/local/lib/go/src/runtime/proc.go:1186
		acquirep(_g_.m.nextp.ptr())
 806b73c:	8b 49 60             	mov    0x60(%ecx),%ecx
 806b73f:	89 0c 24             	mov    %ecx,(%esp)
 806b742:	e8 d9 55 00 00       	call   8070d20 <runtime.acquirep>
/usr/local/lib/go/src/runtime/proc.go:1187
		_g_.m.nextp = 0
 806b747:	8b 44 24 08          	mov    0x8(%esp),%eax
 806b74b:	8b 40 18             	mov    0x18(%eax),%eax
 806b74e:	c7 40 60 00 00 00 00 	movl   $0x0,0x60(%eax)
/usr/local/lib/go/src/runtime/proc.go:1189
	schedule()
 806b755:	eb dc                	jmp    806b733 <runtime.mstart1+0xb3>
/usr/local/lib/go/src/runtime/proc.go:1183
		_g_.m.helpgc = 0
 806b757:	c7 81 88 00 00 00 00 	movl   $0x0,0x88(%ecx)
 806b75e:	00 00 00 
/usr/local/lib/go/src/runtime/proc.go:1184
		stopm()
 806b761:	e8 2a 0d 00 00       	call   806c490 <runtime.stopm>
/usr/local/lib/go/src/runtime/proc.go:1189
	schedule()
 806b766:	eb cb                	jmp    806b733 <runtime.mstart1+0xb3>
/usr/local/lib/go/src/runtime/proc.go:1179
		fn()
 806b768:	8b 0a                	mov    (%edx),%ecx
 806b76a:	ff d1                	call   *%ecx
/usr/local/lib/go/src/runtime/proc.go:1182
	if _g_.m.helpgc != 0 {
 806b76c:	8b 44 24 08          	mov    0x8(%esp),%eax
 806b770:	eb aa                	jmp    806b71c <runtime.mstart1+0x9c>
/usr/local/lib/go/src/runtime/proc.go:1172
			cgoHasExtraM = true
 806b772:	c6 05 42 8d 0d 08 01 	movb   $0x1,0x80d8d42
/usr/local/lib/go/src/runtime/proc.go:1173
			newextram()
 806b779:	e8 a2 07 00 00       	call   806bf20 <runtime.newextram>
/usr/local/lib/go/src/runtime/proc.go:1178
	if fn := _g_.m.mstartfn; fn != nil {
 806b77e:	8b 44 24 08          	mov    0x8(%esp),%eax
/usr/local/lib/go/src/runtime/proc.go:1169
	if _g_.m == &m0 {
 806b782:	8d 15 20 95 0c 08    	lea    0x80c9520,%edx
/usr/local/lib/go/src/runtime/proc.go:1175
		initsig(false)
 806b788:	e9 78 ff ff ff       	jmp    806b705 <runtime.mstart1+0x85>
/usr/local/lib/go/src/runtime/proc.go:1156
		throw("bad runtime·mstart")
 806b78d:	8d 05 3d f5 09 08    	lea    0x809f53d,%eax
 806b793:	89 04 24             	mov    %eax,(%esp)
 806b796:	c7 44 24 04 13 00 00 	movl   $0x13,0x4(%esp)
 806b79d:	00 
 806b79e:	e8 ed c1 ff ff       	call   8067990 <runtime.throw>
 806b7a3:	0f 0b                	ud2    
/usr/local/lib/go/src/runtime/proc.go:1152
func mstart1() {
 806b7a5:	e8 86 ab 01 00       	call   8086330 <runtime.morestack_noctxt>
 806b7aa:	e9 d1 fe ff ff       	jmp    806b680 <runtime.mstart1>
 806b7af:	cc                   	int3 

~~~

