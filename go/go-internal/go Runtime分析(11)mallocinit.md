# schedinit 续 mallocinit

~~~assembly
//======================== mallocinit
08050a70 <runtime.mallocinit>:
runtime.mallocinit():
/usr/local/lib/go/src/runtime/malloc.go:215
// reserved, not merely checked.
//
// SysFault marks a (already sysAlloc'd) region to fault
// if accessed. Used only for debugging the runtime.

func mallocinit() {
 8050a70:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
 8050a77:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx
 8050a7d:	3b 61 08             	cmp    0x8(%ecx),%esp
 8050a80:	0f 86 fc 03 00 00    	jbe    8050e82 <runtime.mallocinit+0x412>
 // ################3 检查栈空间
 
 
 8050a86:	83 ec 48             	sub    $0x48,%esp
/usr/local/lib/go/src/runtime/malloc.go:216
	if class_to_size[_TinySizeClass] != _TinySize {
 8050a89:	0f b7 05 84 82 0c 08 	movzwl 0x80c8284,%eax
 8050a90:	66 83 f8 10          	cmp    $0x10,%ax
 8050a94:	0f 85 d0 03 00 00    	jne    8050e6a <runtime.mallocinit+0x3fa>
/usr/local/lib/go/src/runtime/malloc.go:220
		throw("bad TinySizeClass")
	}

	testdefersizes()
 8050a9a:	e8 d1 5c 01 00       	call   8066770 <runtime.testdefersizes>
/usr/local/lib/go/src/runtime/malloc.go:223

	// Copy class sizes out for statistics table.
	for i := range class_to_size {
 8050a9f:	31 c0                	xor    %eax,%eax
 8050aa1:	83 f8 43             	cmp    $0x43,%eax
 8050aa4:	7d 26                	jge    8050acc <runtime.mallocinit+0x5c>
 //############## 0x43 正好是数组 class_to_size的大小, 是否要跳出循环
 
/usr/local/lib/go/src/runtime/malloc.go:224
		memstats.by_size[i].size = uint32(class_to_size[i])
 8050aa6:	0f 83 b7 03 00 00    	jae    8050e63 <runtime.mallocinit+0x3f3>
/usr/local/lib/go/src/runtime/malloc.go:216
	if class_to_size[_TinySizeClass] != _TinySize {
 8050aac:	8d 0d 80 82 0c 08    	lea    0x80c8280,%ecx
 //##########  0x80c8280 为 class_to_size的地址
 
 
/usr/local/lib/go/src/runtime/malloc.go:224
		memstats.by_size[i].size = uint32(class_to_size[i])
 8050ab2:	0f b7 14 41          	movzwl (%ecx,%eax,2),%edx
 //########## edx = ecx + (2 * eax) eax为索引
 8050ab6:	8d 1c 80             	lea    (%eax,%eax,4),%ebx
 //############ ebx= eax + (eax * 4)  
 8050ab9:	8d 2d 20 97 0d 08    	lea    0x80d9720,%ebp
 8050abf:	89 94 9d d4 10 00 00 	mov    %edx,0x10d4(%ebp,%ebx,4)
 //############ 0x80d9720 为memstats的地址  ebp + (ebx * 4) = edx
 //############# 0x10d4 为 by_size的偏移量
 
/usr/local/lib/go/src/runtime/malloc.go:223
	for i := range class_to_size {
 8050ac6:	40                   	inc    %eax
 8050ac7:	83 f8 43             	cmp    $0x43,%eax
 8050aca:	7c da                	jl     8050aa6 <runtime.mallocinit+0x36>
 // ############ i 小于数组 class_to_size大小 跳转回去
/usr/local/lib/go/src/runtime/malloc.go:228
	}

	// Check physPageSize.
	if physPageSize == 0 {
 8050acc:	8b 05 e8 8d 0d 08    	mov    0x80d8de8,%eax
 8050ad2:	85 c0                	test   %eax,%eax
 8050ad4:	0f 84 71 03 00 00    	je     8050e4b <runtime.mallocinit+0x3db>
/usr/local/lib/go/src/runtime/malloc.go:232
		// The OS init code failed to fetch the physical page size.
		throw("failed to get system page size")
	}
	if physPageSize < minPhysPageSize {
 8050ada:	3d 00 10 00 00       	cmp    $0x1000,%eax
 8050adf:	0f 82 d8 02 00 00    	jb     8050dbd <runtime.mallocinit+0x34d>
/usr/local/lib/go/src/runtime/malloc.go:236
		print("system page size (", physPageSize, ") is smaller than minimum page size (", minPhysPageSize, ")\n")
		throw("bad system page size")
	}
	if physPageSize&(physPageSize-1) != 0 {
 8050ae5:	8d 48 ff             	lea    -0x1(%eax),%ecx
 8050ae8:	85 c1                	test   %eax,%ecx
 8050aea:	0f 85 69 02 00 00    	jne    8050d59 <runtime.mallocinit+0x2e9>
/usr/local/lib/go/src/runtime/malloc.go:242
		print("system page size (", physPageSize, ") must be a power of 2\n")
		throw("bad system page size")
	}





	var p, bitmapSize, spansSize, pSize, limit uintptr
	var reserved bool
 8050af0:	c6 44 24 13 00       	movb   $0x0,0x13(%esp)
/usr/local/lib/go/src/runtime/malloc.go:322
		// in the hope that subsequent reservations will succeed.
		arenaSizes := []uintptr{
			512 << 20,
			256 << 20,
			128 << 20,
			0,
 8050af5:	8d 7c 24 30          	lea    0x30(%esp),%edi
 8050af9:	8d 35 90 4f 0a 08    	lea    0x80a4f90,%esi
 8050aff:	e8 e4 78 03 00       	call   80883e8 <runtime.duffcopy+0x4d8>
 //########## 0x80a4f90 为statictmp的地址
/usr/local/lib/go/src/runtime/malloc.go:223
	for i := range class_to_size {
 8050b04:	31 c0                	xor    %eax,%eax
/usr/local/lib/go/src/runtime/malloc.go:325
		}

// ###################### 
		for _, arenaSize := range arenaSizes {
 8050b06:	8d 4c 24 30          	lea    0x30(%esp),%ecx
/usr/local/lib/go/src/runtime/malloc.go:228
	if physPageSize == 0 {
 8050b0a:	31 d2                	xor    %edx,%edx
 8050b0c:	31 db                	xor    %ebx,%ebx
 8050b0e:	31 ed                	xor    %ebp,%ebp
 8050b10:	31 f6                	xor    %esi,%esi
/usr/local/lib/go/src/runtime/malloc.go:325
		for _, arenaSize := range arenaSizes {
 8050b12:	89 44 24 2c          	mov    %eax,0x2c(%esp)
 8050b16:	89 4c 24 44          	mov    %ecx,0x44(%esp)
 8050b1a:	83 f8 04             	cmp    $0x4,%eax
 8050b1d:	7d 6f                	jge    8050b8e <runtime.mallocinit+0x11e>
 8050b1f:	8b 11                	mov    (%ecx),%edx
 // ############### 0x4 是arenaSizes 的大小
 
/usr/local/lib/go/src/runtime/malloc.go:344
			// give out a slightly higher pointer. Except QEMU, which
			// is buggy, as usual: it won't adjust the pointer upward.
			// So adjust it upward a little bit ourselves: 1/4 MB to get
			// away from the running binary image and then round up
			// to a MB boundary.
			p = round(firstmoduledata.end+(1<<18), 1<<20)
 8050b21:	8b 1d 78 83 0c 08    	mov    0x80c8378,%ebx
 8050b27:	81 c3 ff ff 13 00    	add    $0x13ffff,%ebx
 8050b2d:	81 e3 00 00 f0 ff    	and    $0xfff00000,%ebx
 
 
/usr/local/lib/go/src/runtime/malloc.go:346
			pSize = bitmapSize + spansSize + arenaSize + _PageSize
			p = uintptr(sysReserve(unsafe.Pointer(p), pSize, &reserved))
 8050b33:	89 1c 24             	mov    %ebx,(%esp)
/usr/local/lib/go/src/runtime/malloc.go:333
			spansSize = round(spansSize, _PageSize)
 8050b36:	bb 00 00 20 00       	mov    $0x200000,%ebx
/usr/local/lib/go/src/runtime/malloc.go:345
			pSize = bitmapSize + spansSize + arenaSize + _PageSize
 8050b3b:	8d 94 1a 00 20 00 10 	lea    0x10002000(%edx,%ebx,1),%edx
 8050b42:	89 54 24 1c          	mov    %edx,0x1c(%esp)
/usr/local/lib/go/src/runtime/malloc.go:346
			p = uintptr(sysReserve(unsafe.Pointer(p), pSize, &reserved))
 8050b46:	89 54 24 04          	mov    %edx,0x4(%esp)
/usr/local/lib/go/src/runtime/malloc.go:242
	var reserved bool
 8050b4a:	8d 5c 24 13          	lea    0x13(%esp),%ebx
/usr/local/lib/go/src/runtime/malloc.go:346
			p = uintptr(sysReserve(unsafe.Pointer(p), pSize, &reserved))
 8050b4e:	89 5c 24 08          	mov    %ebx,0x8(%esp)
 8050b52:	e8 b9 52 00 00       	call   8055e10 <runtime.sysReserve>
 8050b57:	8b 44 24 0c          	mov    0xc(%esp),%eax
/usr/local/lib/go/src/runtime/malloc.go:347
			if p != 0 {
 8050b5b:	85 c0                	test   %eax,%eax
 8050b5d:	0f 85 e3 01 00 00    	jne    8050d46 <runtime.mallocinit+0x2d6>
/usr/local/lib/go/src/runtime/malloc.go:325
		for _, arenaSize := range arenaSizes {
 8050b63:	8b 7c 24 44          	mov    0x44(%esp),%edi
 8050b67:	8d 4f 04             	lea    0x4(%edi),%ecx
 8050b6a:	8b 7c 24 2c          	mov    0x2c(%esp),%edi
 8050b6e:	47                   	inc    %edi
/usr/local/lib/go/src/runtime/malloc.go:351
				break
			}
		}
		if p == 0 {
 8050b6f:	89 c2                	mov    %eax,%edx
/usr/local/lib/go/src/runtime/malloc.go:326
			bitmapSize = (_MaxArena32 + 1) / (sys.PtrSize * 8 / 2)
 8050b71:	bb 00 00 00 10       	mov    $0x10000000,%ebx
/usr/local/lib/go/src/runtime/malloc.go:333
			spansSize = round(spansSize, _PageSize)
 8050b76:	bd 00 00 20 00       	mov    $0x200000,%ebp
/usr/local/lib/go/src/runtime/malloc.go:370
		// reservations located anywhere in the 4GB virtual space.
		mheap_.arena_start = 0
	} else {
		mheap_.arena_start = p1 + (spansSize + bitmapSize)
	}
	mheap_.arena_end = p + pSize
 8050b7b:	8b 74 24 1c          	mov    0x1c(%esp),%esi
/usr/local/lib/go/src/runtime/malloc.go:325
		for _, arenaSize := range arenaSizes {
 8050b7f:	89 f8                	mov    %edi,%eax
 8050b81:	89 44 24 2c          	mov    %eax,0x2c(%esp)
 8050b85:	89 4c 24 44          	mov    %ecx,0x44(%esp)
 8050b89:	83 f8 04             	cmp    $0x4,%eax
 8050b8c:	7c 91                	jl     8050b1f <runtime.mallocinit+0xaf>
/usr/local/lib/go/src/runtime/malloc.go:351
		if p == 0 {
 8050b8e:	89 d0                	mov    %edx,%eax
 
 
 
 
/usr/local/lib/go/src/runtime/malloc.go:362
	mheap_.bitmap = p1 + spansSize + bitmapSize
 8050b90:	89 d9                	mov    %ebx,%ecx
 8050b92:	89 ea                	mov    %ebp,%edx
/usr/local/lib/go/src/runtime/malloc.go:370
	mheap_.arena_end = p + pSize
 8050b94:	89 f3                	mov    %esi,%ebx
/usr/local/lib/go/src/runtime/malloc.go:351
		if p == 0 {
 8050b96:	89 44 24 20          	mov    %eax,0x20(%esp)
/usr/local/lib/go/src/runtime/malloc.go:362
	mheap_.bitmap = p1 + spansSize + bitmapSize
 8050b9a:	89 4c 24 24          	mov    %ecx,0x24(%esp)
 8050b9e:	89 54 24 18          	mov    %edx,0x18(%esp)
/usr/local/lib/go/src/runtime/malloc.go:351
		if p == 0 {
 8050ba2:	85 c0                	test   %eax,%eax
 8050ba4:	0f 84 84 01 00 00    	je     8050d2e <runtime.mallocinit+0x2be>
/usr/local/lib/go/src/runtime/malloc.go:359
	p1 := round(p, _PageSize)
 8050baa:	8d a8 ff 1f 00 00    	lea    0x1fff(%eax),%ebp
 8050bb0:	81 e5 00 e0 ff ff    	and    $0xffffe000,%ebp
 8050bb6:	89 6c 24 14          	mov    %ebp,0x14(%esp)
/usr/local/lib/go/src/runtime/malloc.go:362
	mheap_.bitmap = p1 + spansSize + bitmapSize
 8050bba:	8d 74 15 00          	lea    0x0(%ebp,%edx,1),%esi
 8050bbe:	01 ce                	add    %ecx,%esi
 8050bc0:	89 35 28 b6 0c 08    	mov    %esi,0x80cb628
/usr/local/lib/go/src/runtime/malloc.go:366
		mheap_.arena_start = 0
 8050bc6:	c7 05 30 b6 0c 08 00 	movl   $0x0,0x80cb630
 8050bcd:	00 00 00 
/usr/local/lib/go/src/runtime/malloc.go:370
	mheap_.arena_end = p + pSize
 8050bd0:	01 c3                	add    %eax,%ebx
 8050bd2:	89 1d 38 b6 0c 08    	mov    %ebx,0x80cb638
/usr/local/lib/go/src/runtime/malloc.go:371
	mheap_.arena_used = p1 + (spansSize + bitmapSize)
 8050bd8:	8d 1c 11             	lea    (%ecx,%edx,1),%ebx
 8050bdb:	01 eb                	add    %ebp,%ebx
 8050bdd:	89 1d 34 b6 0c 08    	mov    %ebx,0x80cb634
/usr/local/lib/go/src/runtime/malloc.go:372
	mheap_.arena_reserved = reserved
 8050be3:	0f b6 5c 24 13       	movzbl 0x13(%esp),%ebx
 8050be8:	88 1d 3c b6 0c 08    	mov    %bl,0x80cb63c
/usr/local/lib/go/src/runtime/malloc.go:374

	if mheap_.arena_start&(_PageSize-1) != 0 {
 8050bee:	8b 1d 30 b6 0c 08    	mov    0x80cb630,%ebx
 8050bf4:	89 5c 24 28          	mov    %ebx,0x28(%esp)
 8050bf8:	f7 c3 ff 1f 00 00    	test   $0x1fff,%ebx
 8050bfe:	75 40                	jne    8050c40 <runtime.mallocinit+0x1d0>
/usr/local/lib/go/src/runtime/malloc.go:362
	mheap_.bitmap = p1 + spansSize + bitmapSize
 8050c00:	8d 05 80 ab 0c 08    	lea    0x80cab80,%eax
/usr/local/lib/go/src/runtime/malloc.go:380
		println("bad pagesize", hex(p), hex(p1), hex(spansSize), hex(bitmapSize), hex(_PageSize), "start", hex(mheap_.arena_start))
		throw("misrounded allocation in mallocinit")
	}

	// Initialize the rest of the allocator.
	mheap_.init(spansStart, spansSize)
 8050c06:	89 04 24             	mov    %eax,(%esp)
 8050c09:	89 6c 24 04          	mov    %ebp,0x4(%esp)
 8050c0d:	89 54 24 08          	mov    %edx,0x8(%esp)
 8050c11:	e8 3a 00 01 00       	call   8060c50 <runtime.(*mheap).init>
/usr/local/lib/go/src/runtime/malloc.go:381
	_g_ := getg()
 8050c16:	65 8b 05 00 00 00 00 	mov    %gs:0x0,%eax
 8050c1d:	8b 80 fc ff ff ff    	mov    -0x4(%eax),%eax
 8050c23:	89 44 24 40          	mov    %eax,0x40(%esp)
/usr/local/lib/go/src/runtime/malloc.go:382
	_g_.m.mcache = allocmcache()
 8050c27:	e8 f4 41 00 00       	call   8054e20 <runtime.allocmcache>
 8050c2c:	8b 44 24 40          	mov    0x40(%esp),%eax
 8050c30:	8b 40 18             	mov    0x18(%eax),%eax
 8050c33:	8b 0c 24             	mov    (%esp),%ecx
 8050c36:	89 88 b8 00 00 00    	mov    %ecx,0xb8(%eax)
/usr/local/lib/go/src/runtime/malloc.go:383
}
 8050c3c:	83 c4 48             	add    $0x48,%esp
 8050c3f:	c3                   	ret    
/usr/local/lib/go/src/runtime/malloc.go:375
		println("bad pagesize", hex(p), hex(p1), hex(spansSize), hex(bitmapSize), hex(_PageSize), "start", hex(mheap_.arena_start))
 8050c40:	e8 0b 76 01 00       	call   8068250 <runtime.printlock>
 8050c45:	8d 05 79 ec 09 08    	lea    0x809ec79,%eax
 8050c4b:	89 04 24             	mov    %eax,(%esp)
 8050c4e:	c7 44 24 04 0c 00 00 	movl   $0xc,0x4(%esp)
 8050c55:	00 
 8050c56:	e8 65 7e 01 00       	call   8068ac0 <runtime.printstring>
 8050c5b:	e8 c0 77 01 00       	call   8068420 <runtime.printsp>
 8050c60:	8b 44 24 20          	mov    0x20(%esp),%eax
 8050c64:	89 04 24             	mov    %eax,(%esp)
 8050c67:	c7 44 24 04 00 00 00 	movl   $0x0,0x4(%esp)
 8050c6e:	00 
 8050c6f:	e8 1c 7d 01 00       	call   8068990 <runtime.printhex>
 8050c74:	e8 a7 77 01 00       	call   8068420 <runtime.printsp>
 8050c79:	8b 44 24 14          	mov    0x14(%esp),%eax
 8050c7d:	89 04 24             	mov    %eax,(%esp)
 8050c80:	c7 44 24 04 00 00 00 	movl   $0x0,0x4(%esp)
 8050c87:	00 
 8050c88:	e8 03 7d 01 00       	call   8068990 <runtime.printhex>
 8050c8d:	e8 8e 77 01 00       	call   8068420 <runtime.printsp>
 8050c92:	8b 44 24 18          	mov    0x18(%esp),%eax
 8050c96:	89 04 24             	mov    %eax,(%esp)
 8050c99:	c7 44 24 04 00 00 00 	movl   $0x0,0x4(%esp)
 8050ca0:	00 
 8050ca1:	e8 ea 7c 01 00       	call   8068990 <runtime.printhex>
 8050ca6:	e8 75 77 01 00       	call   8068420 <runtime.printsp>
 8050cab:	8b 44 24 24          	mov    0x24(%esp),%eax
 8050caf:	89 04 24             	mov    %eax,(%esp)
 8050cb2:	c7 44 24 04 00 00 00 	movl   $0x0,0x4(%esp)
 8050cb9:	00 
 8050cba:	e8 d1 7c 01 00       	call   8068990 <runtime.printhex>
 8050cbf:	e8 5c 77 01 00       	call   8068420 <runtime.printsp>
 8050cc4:	c7 04 24 00 20 00 00 	movl   $0x2000,(%esp)
 8050ccb:	c7 44 24 04 00 00 00 	movl   $0x0,0x4(%esp)
 8050cd2:	00 
 8050cd3:	e8 b8 7c 01 00       	call   8068990 <runtime.printhex>
 8050cd8:	e8 43 77 01 00       	call   8068420 <runtime.printsp>
 8050cdd:	8d 05 5c e4 09 08    	lea    0x809e45c,%eax
 8050ce3:	89 04 24             	mov    %eax,(%esp)
 8050ce6:	c7 44 24 04 05 00 00 	movl   $0x5,0x4(%esp)
 8050ced:	00 
 8050cee:	e8 cd 7d 01 00       	call   8068ac0 <runtime.printstring>
 8050cf3:	e8 28 77 01 00       	call   8068420 <runtime.printsp>
 8050cf8:	8b 44 24 28          	mov    0x28(%esp),%eax
 8050cfc:	89 04 24             	mov    %eax,(%esp)
 8050cff:	c7 44 24 04 00 00 00 	movl   $0x0,0x4(%esp)
 8050d06:	00 
 8050d07:	e8 84 7c 01 00       	call   8068990 <runtime.printhex>
 8050d0c:	e8 4f 77 01 00       	call   8068460 <runtime.printnl>
 8050d11:	e8 aa 75 01 00       	call   80682c0 <runtime.printunlock>
/usr/local/lib/go/src/runtime/malloc.go:376
		throw("misrounded allocation in mallocinit")
 8050d16:	8d 05 ea 13 0a 08    	lea    0x80a13ea,%eax
 8050d1c:	89 04 24             	mov    %eax,(%esp)
 8050d1f:	c7 44 24 04 23 00 00 	movl   $0x23,0x4(%esp)
 8050d26:	00 
 8050d27:	e8 64 6c 01 00       	call   8067990 <runtime.throw>
 8050d2c:	0f 0b                	ud2    
/usr/local/lib/go/src/runtime/malloc.go:352
			throw("runtime: cannot reserve arena virtual address space")
 8050d2e:	8d 05 58 20 0a 08    	lea    0x80a2058,%eax
 8050d34:	89 04 24             	mov    %eax,(%esp)
 8050d37:	c7 44 24 04 33 00 00 	movl   $0x33,0x4(%esp)
 8050d3e:	00 
 8050d3f:	e8 4c 6c 01 00       	call   8067990 <runtime.throw>
 8050d44:	0f 0b                	ud2    
/usr/local/lib/go/src/runtime/malloc.go:326
			bitmapSize = (_MaxArena32 + 1) / (sys.PtrSize * 8 / 2)
 8050d46:	b9 00 00 00 10       	mov    $0x10000000,%ecx
/usr/local/lib/go/src/runtime/malloc.go:333
			spansSize = round(spansSize, _PageSize)
 8050d4b:	ba 00 00 20 00       	mov    $0x200000,%edx
/usr/local/lib/go/src/runtime/malloc.go:370
	mheap_.arena_end = p + pSize
 8050d50:	8b 5c 24 1c          	mov    0x1c(%esp),%ebx
/usr/local/lib/go/src/runtime/malloc.go:351
		if p == 0 {
 8050d54:	e9 3d fe ff ff       	jmp    8050b96 <runtime.mallocinit+0x126>
/usr/local/lib/go/src/runtime/malloc.go:237
		print("system page size (", physPageSize, ") must be a power of 2\n")
 8050d59:	e8 f2 74 01 00       	call   8068250 <runtime.printlock>
 8050d5e:	8d 05 80 f4 09 08    	lea    0x809f480,%eax
 8050d64:	89 04 24             	mov    %eax,(%esp)
 8050d67:	c7 44 24 04 12 00 00 	movl   $0x12,0x4(%esp)
 8050d6e:	00 
 8050d6f:	e8 4c 7d 01 00       	call   8068ac0 <runtime.printstring>
 8050d74:	8b 05 e8 8d 0d 08    	mov    0x80d8de8,%eax
 8050d7a:	89 04 24             	mov    %eax,(%esp)
 8050d7d:	c7 44 24 04 00 00 00 	movl   $0x0,0x4(%esp)
 8050d84:	00 
 8050d85:	e8 76 7b 01 00       	call   8068900 <runtime.printint>
 8050d8a:	8d 05 63 fc 09 08    	lea    0x809fc63,%eax
 8050d90:	89 04 24             	mov    %eax,(%esp)
 8050d93:	c7 44 24 04 17 00 00 	movl   $0x17,0x4(%esp)
 8050d9a:	00 
 8050d9b:	e8 20 7d 01 00       	call   8068ac0 <runtime.printstring>
 8050da0:	e8 1b 75 01 00       	call   80682c0 <runtime.printunlock>
/usr/local/lib/go/src/runtime/malloc.go:238
		throw("bad system page size")
 8050da5:	8d 05 f9 f6 09 08    	lea    0x809f6f9,%eax
 8050dab:	89 04 24             	mov    %eax,(%esp)
 8050dae:	c7 44 24 04 14 00 00 	movl   $0x14,0x4(%esp)
 8050db5:	00 
 8050db6:	e8 d5 6b 01 00       	call   8067990 <runtime.throw>
 8050dbb:	0f 0b                	ud2    
/usr/local/lib/go/src/runtime/malloc.go:233
		print("system page size (", physPageSize, ") is smaller than minimum page size (", minPhysPageSize, ")\n")
 8050dbd:	e8 8e 74 01 00       	call   8068250 <runtime.printlock>
 8050dc2:	8d 05 80 f4 09 08    	lea    0x809f480,%eax
 8050dc8:	89 04 24             	mov    %eax,(%esp)
 8050dcb:	c7 44 24 04 12 00 00 	movl   $0x12,0x4(%esp)
 8050dd2:	00 
 8050dd3:	e8 e8 7c 01 00       	call   8068ac0 <runtime.printstring>
 8050dd8:	8b 05 e8 8d 0d 08    	mov    0x80d8de8,%eax
 8050dde:	89 04 24             	mov    %eax,(%esp)
 8050de1:	c7 44 24 04 00 00 00 	movl   $0x0,0x4(%esp)
 8050de8:	00 
 8050de9:	e8 12 7b 01 00       	call   8068900 <runtime.printint>
 8050dee:	8d 05 02 16 0a 08    	lea    0x80a1602,%eax
 8050df4:	89 04 24             	mov    %eax,(%esp)
 8050df7:	c7 44 24 04 25 00 00 	movl   $0x25,0x4(%esp)
 8050dfe:	00 
 8050dff:	e8 bc 7c 01 00       	call   8068ac0 <runtime.printstring>
 8050e04:	c7 04 24 00 10 00 00 	movl   $0x1000,(%esp)
 8050e0b:	c7 44 24 04 00 00 00 	movl   $0x0,0x4(%esp)
 8050e12:	00 
 8050e13:	e8 e8 7a 01 00       	call   8068900 <runtime.printint>
 8050e18:	8d 05 eb e2 09 08    	lea    0x809e2eb,%eax
 8050e1e:	89 04 24             	mov    %eax,(%esp)
 8050e21:	c7 44 24 04 02 00 00 	movl   $0x2,0x4(%esp)
 8050e28:	00 
 8050e29:	e8 92 7c 01 00       	call   8068ac0 <runtime.printstring>
 8050e2e:	e8 8d 74 01 00       	call   80682c0 <runtime.printunlock>
/usr/local/lib/go/src/runtime/malloc.go:234
		throw("bad system page size")
 8050e33:	8d 05 f9 f6 09 08    	lea    0x809f6f9,%eax
 8050e39:	89 04 24             	mov    %eax,(%esp)
 8050e3c:	c7 44 24 04 14 00 00 	movl   $0x14,0x4(%esp)
 8050e43:	00 
 8050e44:	e8 47 6b 01 00       	call   8067990 <runtime.throw>
 8050e49:	0f 0b                	ud2    
/usr/local/lib/go/src/runtime/malloc.go:230
		throw("failed to get system page size")
 8050e4b:	8d 05 7a 0b 0a 08    	lea    0x80a0b7a,%eax
 8050e51:	89 04 24             	mov    %eax,(%esp)
 8050e54:	c7 44 24 04 1e 00 00 	movl   $0x1e,0x4(%esp)
 8050e5b:	00 
 8050e5c:	e8 2f 6b 01 00       	call   8067990 <runtime.throw>
 8050e61:	0f 0b                	ud2    
 
 
 
/usr/local/lib/go/src/runtime/malloc.go:224
		memstats.by_size[i].size = uint32(class_to_size[i])
 8050e63:	e8 58 55 01 00       	call   80663c0 <runtime.panicindex>
 8050e68:	0f 0b                	ud2    
/usr/local/lib/go/src/runtime/malloc.go:217
		throw("bad TinySizeClass")
 8050e6a:	8d 05 03 f3 09 08    	lea    0x809f303,%eax
 8050e70:	89 04 24             	mov    %eax,(%esp)
 8050e73:	c7 44 24 04 11 00 00 	movl   $0x11,0x4(%esp)
 8050e7a:	00 
 8050e7b:	e8 10 6b 01 00       	call   8067990 <runtime.throw>
 8050e80:	0f 0b                	ud2    
/usr/local/lib/go/src/runtime/malloc.go:215
func mallocinit() {
 8050e82:	e8 a9 54 03 00       	call   8086330 <runtime.morestack_noctxt>
 8050e87:	e9 e4 fb ff ff       	jmp    8050a70 <runtime.mallocinit>
 8050e8c:	cc                   	int3   
 8050e8d:	cc                   	int3   
 8050e8e:	cc                   	int3   
 8050e8f:	cc                   	int3   

~~~





~~~go

func mallocinit() {
	if class_to_size[_TinySizeClass] != _TinySize {
		throw("bad TinySizeClass")
	}

	testdefersizes()

	// Copy class sizes out for statistics table.
	for i := range class_to_size {
		memstats.by_size[i].size = uint32(class_to_size[i])
	}

	// Check physPageSize.
	if physPageSize == 0 {
		// The OS init code failed to fetch the physical page size.
		throw("failed to get system page size")
	}
	if physPageSize < minPhysPageSize {
		print("system page size (", physPageSize, ") is smaller than minimum page size (", minPhysPageSize, ")\n")
		throw("bad system page size")
	}
	if physPageSize&(physPageSize-1) != 0 {
		print("system page size (", physPageSize, ") must be a power of 2\n")
		throw("bad system page size")
	}

	var p, bitmapSize, spansSize, pSize, limit uintptr
	var reserved bool

	// limit = runtime.memlimit();
	// See https://golang.org/issue/5049
	// TODO(rsc): Fix after 1.1.
	limit = 0

	// Set up the allocation arena, a contiguous area of memory where
	// allocated data will be found. The arena begins with a bitmap large
	// enough to hold 2 bits per allocated word.
	if sys.PtrSize == 8 && (limit == 0 || limit > 1<<30) {
		// On a 64-bit machine, allocate from a single contiguous reservation.
		// 512 GB (MaxMem) should be big enough for now.
		//
		// The code will work with the reservation at any address, but ask
		// SysReserve to use 0x0000XXc000000000 if possible (XX=00...7f).
		// Allocating a 512 GB region takes away 39 bits, and the amd64
		// doesn't let us choose the top 17 bits, so that leaves the 9 bits
		// in the middle of 0x00c0 for us to choose. Choosing 0x00c0 means
		// that the valid memory addresses will begin 0x00c0, 0x00c1, ..., 0x00df.
		// In little-endian, that's c0 00, c1 00, ..., df 00. None of those are valid
		// UTF-8 sequences, and they are otherwise as far away from
		// ff (likely a common byte) as possible. If that fails, we try other 0xXXc0
		// addresses. An earlier attempt to use 0x11f8 caused out of memory errors
		// on OS X during thread allocations.  0x00c0 causes conflicts with
		// AddressSanitizer which reserves all memory up to 0x0100.
		// These choices are both for debuggability and to reduce the
		// odds of a conservative garbage collector (as is still used in gccgo)
		// not collecting memory because some non-pointer block of memory
		// had a bit pattern that matched a memory address.
		//
		// Actually we reserve 544 GB (because the bitmap ends up being 32 GB)
		// but it hardly matters: e0 00 is not valid UTF-8 either.
		//
		// If this fails we fall back to the 32 bit memory mechanism
		//
		// However, on arm64, we ignore all this advice above and slam the
		// allocation at 0x40 << 32 because when using 4k pages with 3-level
		// translation buffers, the user address space is limited to 39 bits
		// On darwin/arm64, the address space is even smaller.
		arenaSize := round(_MaxMem, _PageSize)
		bitmapSize = arenaSize / (sys.PtrSize * 8 / 2)
		spansSize = arenaSize / _PageSize * sys.PtrSize
		spansSize = round(spansSize, _PageSize)
		for i := 0; i <= 0x7f; i++ {
			switch {
			case GOARCH == "arm64" && GOOS == "darwin":
				p = uintptr(i)<<40 | uintptrMask&(0x0013<<28)
			case GOARCH == "arm64":
				p = uintptr(i)<<40 | uintptrMask&(0x0040<<32)
			default:
				p = uintptr(i)<<40 | uintptrMask&(0x00c0<<32)
			}
			pSize = bitmapSize + spansSize + arenaSize + _PageSize
			p = uintptr(sysReserve(unsafe.Pointer(p), pSize, &reserved))
			if p != 0 {
				break
			}
		}
	}

	if p == 0 {
		// On a 32-bit machine, we can't typically get away
		// with a giant virtual address space reservation.
		// Instead we map the memory information bitmap
		// immediately after the data segment, large enough
		// to handle the entire 4GB address space (256 MB),
		// along with a reservation for an initial arena.
		// When that gets used up, we'll start asking the kernel
		// for any memory anywhere.

		// If we fail to allocate, try again with a smaller arena.
		// This is necessary on Android L where we share a process
		// with ART, which reserves virtual memory aggressively.
		// In the worst case, fall back to a 0-sized initial arena,
		// in the hope that subsequent reservations will succeed.
		arenaSizes := []uintptr{
			512 << 20,
			256 << 20,
			128 << 20,
			0,
		}

		for _, arenaSize := range arenaSizes {
            // 计算位图大小 32位  4GB /16  假设sys.PtrSize 为4KB
			bitmapSize = (_MaxArena32 + 1) / (sys.PtrSize * 8 / 2)
            // 4GB/ (4k * 4)
			spansSize = (_MaxArena32 + 1) / _PageSize * sys.PtrSize
			if limit > 0 && arenaSize+bitmapSize+spansSize > limit {
				bitmapSize = (limit / 9) &^ ((1 << _PageShift) - 1)
				arenaSize = bitmapSize * 8
				spansSize = arenaSize / _PageSize * sys.PtrSize
			}
            //页面大小对齐
			spansSize = round(spansSize, _PageSize)

			// SysReserve treats the address we ask for, end, as a hint,
			// not as an absolute requirement. If we ask for the end
			// of the data segment but the operating system requires
			// a little more space before we can start allocating, it will
			// give out a slightly higher pointer. Except QEMU, which
			// is buggy, as usual: it won't adjust the pointer upward.
			// So adjust it upward a little bit ourselves: 1/4 MB to get
			// away from the running binary image and then round up
			// to a MB boundary.
            
            
            // firstmodeldata.end + 256k ，
			p = round(firstmoduledata.end+(1<<18), 1<<20)
			pSize = bitmapSize + spansSize + arenaSize + _PageSize
            
            //映射一块虚拟地址空间
			p = uintptr(sysReserve(unsafe.Pointer(p), pSize, &reserved))
			if p != 0 {
				break
			}
		}
		if p == 0 {
			throw("runtime: cannot reserve arena virtual address space")
		}
	}

	// PageSize can be larger than OS definition of page size,
	// so SysReserve can give us a PageSize-unaligned pointer.
	// To overcome this we ask for PageSize more and round up the pointer.
	p1 := round(p, _PageSize)

	spansStart := p1
    // mheap_.bitmap 应该是指向结束的地方
	mheap_.bitmap = p1 + spansSize + bitmapSize
	if sys.PtrSize == 4 {
		// Set arena_start such that we can accept memory
		// reservations located anywhere in the 4GB virtual space.
		mheap_.arena_start = 0
	} else {
		mheap_.arena_start = p1 + (spansSize + bitmapSize)
	}
	mheap_.arena_end = p + pSize
	mheap_.arena_used = p1 + (spansSize + bitmapSize)
	mheap_.arena_reserved = reserved

	if mheap_.arena_start&(_PageSize-1) != 0 {
		println("bad pagesize", hex(p), hex(p1), hex(spansSize), hex(bitmapSize), hex(_PageSize), "start", hex(mheap_.arena_start))
		throw("misrounded allocation in mallocinit")
	}

	// Initialize the rest of the allocator.
	mheap_.init(spansStart, spansSize)
	_g_ := getg()
	_g_.m.mcache = allocmcache()
}
~~~

