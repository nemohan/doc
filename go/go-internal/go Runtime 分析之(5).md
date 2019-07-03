#  go runtime1.go

~~~assembly
08073560 <runtime.args>:
runtime.args():
/usr/local/lib/go/src/runtime/runtime1.go:61
//go:nosplit
func argv_index(argv **byte, i int32) *byte {
	return *(**byte)(add(unsafe.Pointer(argv), uintptr(i)*sys.PtrSize))
}

func args(c int32, v **byte) {
 8073560:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
 8073567:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx
 //######## 获取g0
 807356d:	3b 61 08             	cmp    0x8(%ecx),%esp
 //######## 栈空间是否足够 g0.stackguard0 < esp 说明栈空间够用
 8073570:	76 51                	jbe    80735c3 <runtime.args+0x63>
 8073572:	83 ec 08             	sub    $0x8,%esp
 
 
/usr/local/lib/go/src/runtime/runtime1.go:62
	argc = c
 8073575:	8b 44 24 0c          	mov    0xc(%esp),%eax
 8073579:	89 05 5c 8d 0d 08    	mov    %eax,0x80d8d5c
 // ########## eax = argc
 
/usr/local/lib/go/src/runtime/runtime1.go:63
	argv = v
 807357f:	8b 0d 80 8e 0d 08    	mov    0x80d8e80,%ecx
 8073585:	85 c9                	test   %ecx,%ecx
 8073587:	75 1a                	jne    80735a3 <runtime.args+0x43>
 //################# 上面是 runtime.writeBarrier
 8073589:	8b 4c 24 10          	mov    0x10(%esp),%ecx
 807358d:	89 0d bc 8f 0c 08    	mov    %ecx,0x80c8fbc
 // #############  ecx=argv  保存argv
 
/usr/local/lib/go/src/runtime/runtime1.go:64
	sysargs(c, v)
 8073593:	89 04 24             	mov    %eax,(%esp)
 8073596:	89 4c 24 04          	mov    %ecx,0x4(%esp)
 807359a:	e8 31 26 ff ff       	call   8065bd0 <runtime.sysargs>
/usr/local/lib/go/src/runtime/runtime1.go:65
}
 807359f:	83 c4 08             	add    $0x8,%esp
 80735a2:	c3                   	ret    

~~~

~~~go
os_linux.go

//################## 不是十分清除这块是做什么的???????????????????????????


// Should be a built-in for unsafe.Pointer?
//go:nosplit
func add(p unsafe.Pointer, x uintptr) unsafe.Pointer {
	return unsafe.Pointer(uintptr(p) + x)
}

// nosplit for use in linux startup sysargs
//go:nosplit
func argv_index(argv **byte, i int32) *byte {
	return *(**byte)(add(unsafe.Pointer(argv), uintptr(i)*sys.PtrSize))
}

func sysargs(argc int32, argv **byte) {
	n := argc + 1

	// skip over argv, envp to get to auxv
	for argv_index(argv, n) != nil {
		n++
	}

	// skip NULL separator
	n++

	// now argv+n is auxv
	auxv := (*[1 << 28]uintptr)(add(unsafe.Pointer(argv), uintptr(n)*sys.PtrSize))
	if sysauxv(auxv[:]) == 0 {
		// In some situations we don't get a loader-provided
		// auxv, such as when loaded as a library on Android.
		// Fall back to /proc/self/auxv.
		fd := open(&procAuxv[0], 0 /* O_RDONLY */, 0)
		if fd < 0 {
			// On Android, /proc/self/auxv might be unreadable (issue 9229), so we fallback to
			// try using mincore to detect the physical page size.
			// mincore should return EINVAL when address is not a multiple of system page size.
			const size = 256 << 10 // size of memory region to allocate
			p := mmap(nil, size, _PROT_READ|_PROT_WRITE, _MAP_ANON|_MAP_PRIVATE, -1, 0)
			if uintptr(p) < 4096 {
				return
			}
			var n uintptr
			for n = 4 << 10; n < size; n <<= 1 {
				err := mincore(unsafe.Pointer(uintptr(p)+n), 1, &addrspace_vec[0])
				if err == 0 {
					physPageSize = n
					break
				}
			}
			if physPageSize == 0 {
				physPageSize = size
			}
			munmap(p, size)
			return
		}
		var buf [128]uintptr
		n := read(fd, noescape(unsafe.Pointer(&buf[0])), int32(unsafe.Sizeof(buf)))
		closefd(fd)
		if n < 0 {
			return
		}
		// Make sure buf is terminated, even if we didn't read
		// the whole file.
		buf[len(buf)-2] = _AT_NULL
		sysauxv(buf[:])
	}
}


~~~

~~~assembly
//带反编译的版本

func sysargs(argc int32, argv **byte) {
 8065bd0:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
 8065bd7:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx
 8065bdd:	8d 84 24 54 fe ff ff 	lea    -0x1ac(%esp),%eax
 8065be4:	3b 41 08             	cmp    0x8(%ecx),%eax
 //############ 检查栈空间
 
 8065be7:	0f 86 f4 01 00 00    	jbe    8065de1 <runtime.sysargs+0x211>
 8065bed:	81 ec 2c 02 00 00    	sub    $0x22c,%esp
/usr/local/lib/go/src/runtime/os_linux.go:196
	n := argc + 1
 8065bf3:	8b 84 24 30 02 00 00 	mov    0x230(%esp),%eax
 8065bfa:	40                   	inc    %eax
/usr/local/lib/go/src/runtime/os_linux.go:199

	// skip over argv, envp to get to auxv
	for argv_index(argv, n) != nil {
 8065bfb:	8b 8c 24 34 02 00 00 	mov    0x234(%esp),%ecx
 8065c02:	89 ca                	mov    %ecx,%edx
 8065c04:	89 c3                	mov    %eax,%ebx
 8065c06:	c1 e0 02             	shl    $0x2,%eax
 8065c09:	01 d0                	add    %edx,%eax
 8065c0b:	8b 00                	mov    (%eax),%eax
 8065c0d:	85 c0                	test   %eax,%eax
 8065c0f:	74 05                	je     8065c16 <runtime.sysargs+0x46>
/usr/local/lib/go/src/runtime/os_linux.go:200
		n++
 8065c11:	8d 43 01             	lea    0x1(%ebx),%eax
/usr/local/lib/go/src/runtime/os_linux.go:199
	for argv_index(argv, n) != nil {
 8065c14:	eb ec                	jmp    8065c02 <runtime.sysargs+0x32>
/usr/local/lib/go/src/runtime/os_linux.go:204
	}

	// skip NULL separator
	n++
 8065c16:	8d 43 01             	lea    0x1(%ebx),%eax
/usr/local/lib/go/src/runtime/os_linux.go:207

	// now argv+n is auxv
	auxv := (*[1 << 28]uintptr)(add(unsafe.Pointer(argv), uintptr(n)*sys.PtrSize))
 8065c19:	c1 e0 02             	shl    $0x2,%eax
 8065c1c:	01 d0                	add    %edx,%eax
/usr/local/lib/go/src/runtime/os_linux.go:208
	if sysauxv(auxv[:]) == 0 {
 8065c1e:	84 00                	test   %al,(%eax)
 8065c20:	89 04 24             	mov    %eax,(%esp)
 8065c23:	c7 44 24 04 00 00 00 	movl   $0x10000000,0x4(%esp)
 8065c2a:	10 
 8065c2b:	c7 44 24 08 00 00 00 	movl   $0x10000000,0x8(%esp)
 8065c32:	10 
 8065c33:	e8 b8 01 00 00       	call   8065df0 <runtime.sysauxv>
 8065c38:	8b 44 24 0c          	mov    0xc(%esp),%eax
 8065c3c:	85 c0                	test   %eax,%eax
 8065c3e:	0f 85 88 01 00 00    	jne    8065dcc <runtime.sysargs+0x1fc>
/usr/local/lib/go/src/runtime/os_linux.go:212
		// In some situations we don't get a loader-provided
		// auxv, such as when loaded as a library on Android.
		// Fall back to /proc/self/auxv.
		fd := open(&procAuxv[0], 0 /* O_RDONLY */, 0)
 8065c44:	8b 05 68 8a 0c 08    	mov    0x80c8a68,%eax
 8065c4a:	8b 0d 6c 8a 0c 08    	mov    0x80c8a6c,%ecx
 8065c50:	85 c9                	test   %ecx,%ecx
 8065c52:	0f 86 82 01 00 00    	jbe    8065dda <runtime.sysargs+0x20a>
 8065c58:	89 04 24             	mov    %eax,(%esp)
 8065c5b:	c7 44 24 04 00 00 00 	movl   $0x0,0x4(%esp)
 8065c62:	00 
 8065c63:	c7 44 24 08 00 00 00 	movl   $0x0,0x8(%esp)
 8065c6a:	00 
 8065c6b:	e8 90 2b 02 00       	call   8088800 <runtime.open>
 8065c70:	8b 44 24 0c          	mov    0xc(%esp),%eax
 8065c74:	89 44 24 24          	mov    %eax,0x24(%esp)
/usr/local/lib/go/src/runtime/os_linux.go:213
		if fd < 0 {
 8065c78:	85 c0                	test   %eax,%eax
 8065c7a:	0f 8d e2 00 00 00    	jge    8065d62 <runtime.sysargs+0x192>
/usr/local/lib/go/src/runtime/os_linux.go:218
			// On Android, /proc/self/auxv might be unreadable (issue 9229), so we fallback to
			// try using mincore to detect the physical page size.
			// mincore should return EINVAL when address is not a multiple of system page size.
			const size = 256 << 10 // size of memory region to allocate
			p := mmap(nil, size, _PROT_READ|_PROT_WRITE, _MAP_ANON|_MAP_PRIVATE, -1, 0)
 8065c80:	c7 04 24 00 00 00 00 	movl   $0x0,(%esp)
 8065c87:	c7 44 24 04 00 00 04 	movl   $0x40000,0x4(%esp)
 8065c8e:	00 
 8065c8f:	c7 44 24 08 03 00 00 	movl   $0x3,0x8(%esp)
 8065c96:	00 
 8065c97:	c7 44 24 0c 22 00 00 	movl   $0x22,0xc(%esp)
 8065c9e:	00 
 8065c9f:	c7 44 24 10 ff ff ff 	movl   $0xffffffff,0x10(%esp)
 8065ca6:	ff 
 8065ca7:	c7 44 24 14 00 00 00 	movl   $0x0,0x14(%esp)
 8065cae:	00 
 8065caf:	e8 3c 2e 02 00       	call   8088af0 <runtime.mmap>
 8065cb4:	8b 44 24 18          	mov    0x18(%esp),%eax
 8065cb8:	89 84 24 28 02 00 00 	mov    %eax,0x228(%esp)
/usr/local/lib/go/src/runtime/os_linux.go:219
			if uintptr(p) < 4096 {
 8065cbf:	89 c1                	mov    %eax,%ecx
 8065cc1:	81 f9 00 10 00 00    	cmp    $0x1000,%ecx
 8065cc7:	0f 82 8e 00 00 00    	jb     8065d5b <runtime.sysargs+0x18b>
 8065ccd:	b9 00 10 00 00       	mov    $0x1000,%ecx
/usr/local/lib/go/src/runtime/os_linux.go:223
				return
			}
			var n uintptr
			for n = 4 << 10; n < size; n <<= 1 {
 8065cd2:	89 4c 24 1c          	mov    %ecx,0x1c(%esp)
 8065cd6:	81 f9 00 00 04 00    	cmp    $0x40000,%ecx
 8065cdc:	73 3f                	jae    8065d1d <runtime.sysargs+0x14d>
/usr/local/lib/go/src/runtime/os_linux.go:224
				err := mincore(unsafe.Pointer(uintptr(p)+n), 1, &addrspace_vec[0])
 8065cde:	8d 15 41 8d 0d 08    	lea    0x80d8d41,%edx
 8065ce4:	89 54 24 08          	mov    %edx,0x8(%esp)
 8065ce8:	89 c2                	mov    %eax,%edx
 8065cea:	01 ca                	add    %ecx,%edx
 8065cec:	89 14 24             	mov    %edx,(%esp)
 8065cef:	c7 44 24 04 01 00 00 	movl   $0x1,0x4(%esp)
 8065cf6:	00 
 8065cf7:	e8 64 2c 02 00       	call   8088960 <runtime.mincore>
 8065cfc:	8b 44 24 0c          	mov    0xc(%esp),%eax
/usr/local/lib/go/src/runtime/os_linux.go:225
				if err == 0 {
 8065d00:	85 c0                	test   %eax,%eax
 8065d02:	74 4b                	je     8065d4f <runtime.sysargs+0x17f>
/usr/local/lib/go/src/runtime/os_linux.go:223
			for n = 4 << 10; n < size; n <<= 1 {
 8065d04:	8b 4c 24 1c          	mov    0x1c(%esp),%ecx
 8065d08:	d1 e1                	shl    %ecx
/usr/local/lib/go/src/runtime/os_linux.go:224
				err := mincore(unsafe.Pointer(uintptr(p)+n), 1, &addrspace_vec[0])
 8065d0a:	8b 84 24 28 02 00 00 	mov    0x228(%esp),%eax
/usr/local/lib/go/src/runtime/os_linux.go:223
			for n = 4 << 10; n < size; n <<= 1 {
 8065d11:	89 4c 24 1c          	mov    %ecx,0x1c(%esp)
 8065d15:	81 f9 00 00 04 00    	cmp    $0x40000,%ecx
 8065d1b:	72 c1                	jb     8065cde <runtime.sysargs+0x10e>
/usr/local/lib/go/src/runtime/os_linux.go:230
					physPageSize = n
					break
				}
			}
			if physPageSize == 0 {
 8065d1d:	8b 05 e8 8d 0d 08    	mov    0x80d8de8,%eax
 8065d23:	85 c0                	test   %eax,%eax
 8065d25:	75 0a                	jne    8065d31 <runtime.sysargs+0x161>
/usr/local/lib/go/src/runtime/os_linux.go:231
				physPageSize = size
 8065d27:	c7 05 e8 8d 0d 08 00 	movl   $0x40000,0x80d8de8
 8065d2e:	00 04 00 
/usr/local/lib/go/src/runtime/os_linux.go:233
			}
			munmap(p, size)
 8065d31:	8b 84 24 28 02 00 00 	mov    0x228(%esp),%eax
 8065d38:	89 04 24             	mov    %eax,(%esp)
 8065d3b:	c7 44 24 04 00 00 04 	movl   $0x40000,0x4(%esp)
 8065d42:	00 
 8065d43:	e8 e8 2d 02 00       	call   8088b30 <runtime.munmap>
/usr/local/lib/go/src/runtime/os_linux.go:234
			return
 8065d48:	81 c4 2c 02 00 00    	add    $0x22c,%esp
 8065d4e:	c3                   	ret    
/usr/local/lib/go/src/runtime/os_linux.go:226
					physPageSize = n
 8065d4f:	8b 44 24 1c          	mov    0x1c(%esp),%eax
 8065d53:	89 05 e8 8d 0d 08    	mov    %eax,0x80d8de8
/usr/local/lib/go/src/runtime/os_linux.go:230
			if physPageSize == 0 {
 8065d59:	eb c2                	jmp    8065d1d <runtime.sysargs+0x14d>
/usr/local/lib/go/src/runtime/os_linux.go:220
				return
 8065d5b:	81 c4 2c 02 00 00    	add    $0x22c,%esp
 8065d61:	c3                   	ret    
/usr/local/lib/go/src/runtime/os_linux.go:236
		}
		var buf [128]uintptr
 8065d62:	8d 7c 24 28          	lea    0x28(%esp),%edi
 8065d66:	31 c0                	xor    %eax,%eax
 8065d68:	e8 13 21 02 00       	call   8087e80 <runtime.duffzero>
/usr/local/lib/go/src/runtime/os_linux.go:237
		n := read(fd, noescape(unsafe.Pointer(&buf[0])), int32(unsafe.Sizeof(buf)))
 8065d6d:	8b 4c 24 24          	mov    0x24(%esp),%ecx
 8065d71:	89 0c 24             	mov    %ecx,(%esp)
 8065d74:	8d 54 24 28          	lea    0x28(%esp),%edx
 8065d78:	89 54 24 04          	mov    %edx,0x4(%esp)
 8065d7c:	c7 44 24 08 00 02 00 	movl   $0x200,0x8(%esp)
 8065d83:	00 
 8065d84:	e8 f7 2a 02 00       	call   8088880 <runtime.read>
 8065d89:	8b 4c 24 0c          	mov    0xc(%esp),%ecx
 8065d8d:	89 4c 24 20          	mov    %ecx,0x20(%esp)
/usr/local/lib/go/src/runtime/os_linux.go:238
		closefd(fd)
 8065d91:	8b 54 24 24          	mov    0x24(%esp),%edx
 8065d95:	89 14 24             	mov    %edx,(%esp)
 8065d98:	e8 93 2a 02 00       	call   8088830 <runtime.closefd>
/usr/local/lib/go/src/runtime/os_linux.go:239
		if n < 0 {
 8065d9d:	8b 4c 24 20          	mov    0x20(%esp),%ecx
 8065da1:	85 c9                	test   %ecx,%ecx
 8065da3:	7c 2e                	jl     8065dd3 <runtime.sysargs+0x203>
/usr/local/lib/go/src/runtime/os_linux.go:244
			return
		}
		// Make sure buf is terminated, even if we didn't read
		// the whole file.
		buf[len(buf)-2] = _AT_NULL
 8065da5:	c7 84 24 20 02 00 00 	movl   $0x0,0x220(%esp)
 8065dac:	00 00 00 00 
/usr/local/lib/go/src/runtime/os_linux.go:236
		var buf [128]uintptr
 8065db0:	8d 44 24 28          	lea    0x28(%esp),%eax
/usr/local/lib/go/src/runtime/os_linux.go:245
		sysauxv(buf[:])
 8065db4:	89 04 24             	mov    %eax,(%esp)
 8065db7:	c7 44 24 04 80 00 00 	movl   $0x80,0x4(%esp)
 8065dbe:	00 
 8065dbf:	c7 44 24 08 80 00 00 	movl   $0x80,0x8(%esp)
 8065dc6:	00 
 8065dc7:	e8 24 00 00 00       	call   8065df0 <runtime.sysauxv>
/usr/local/lib/go/src/runtime/os_linux.go:247
	}
}

~~~

