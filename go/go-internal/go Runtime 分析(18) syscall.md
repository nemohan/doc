# syscall

分析系统调用以读取文件为例

objdump -DgSlF main_goroutine > main_goroutine_objdump

产生带行号的dump

~~~go

package main

import (
	"os"
)

func main() {
	go onxh()
}

func onxh() {
	file, _ := os.Open("niho")
	data := make([]byte, 100)
	file.Read(data)
}
~~~







~~~assembly

func onxh() {
 808fb60:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
 808fb67:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx
 808fb6d:	8d 44 24 fc          	lea    -0x4(%esp),%eax
 808fb71:	3b 41 08             	cmp    0x8(%ecx),%eax
 808fb74:	76 60                	jbe    808fbd6 <main.onxh+0x76> (File Offset: 0x47bd6)
 808fb76:	81 ec 84 00 00 00    	sub    $0x84,%esp
/home/hanzhao/workspace/go_runtime/main.go:12
	file, _ := os.Open("niho")
 808fb7c:	8d 05 54 53 0a 08    	lea    0x80a5354,%eax
 808fb82:	89 04 24             	mov    %eax,(%esp)
 808fb85:	c7 44 24 04 04 00 00 	movl   $0x4,0x4(%esp)
 //################### 0x80a5354 应该是字符串地址， 0x4是字符串"niho"的长度
 808fb8c:	00 
 808fb8d:	e8 5e ef ff ff       	call   808eaf0 <os.Open> (File Offset: 0x46af0)
 808fb92:	8b 44 24 08          	mov    0x8(%esp),%eax
 808fb96:	89 84 24 80 00 00 00 	mov    %eax,0x80(%esp)
/home/hanzhao/workspace/go_runtime/main.go:13
	data := make([]byte, 100)
 808fb9d:	8d 7c 24 1c          	lea    0x1c(%esp),%edi
 808fba1:	31 c0                	xor    %eax,%eax
 808fba3:	e8 ef 9c ff ff       	call   8089897 <runtime.duffzero+0x67> (File Offset: 0x41897)
/home/hanzhao/workspace/go_runtime/main.go:14
	file.Read(data)
 808fba8:	8b 84 24 80 00 00 00 	mov    0x80(%esp),%eax
 808fbaf:	89 04 24             	mov    %eax,(%esp)
/home/hanzhao/workspace/go_runtime/main.go:13
	go onxh()
}

func onxh() {
	file, _ := os.Open("niho")
	data := make([]byte, 100)
 808fbb2:	8d 44 24 1c          	lea    0x1c(%esp),%eax
/home/hanzhao/workspace/go_runtime/main.go:14
	file.Read(data)
 808fbb6:	89 44 24 04          	mov    %eax,0x4(%esp)
 808fbba:	c7 44 24 08 64 00 00 	movl   $0x64,0x8(%esp)
 808fbc1:	00 
 808fbc2:	c7 44 24 0c 64 00 00 	movl   $0x64,0xc(%esp)
 808fbc9:	00 
 808fbca:	e8 a1 ec ff ff       	call   808e870 <os.(*File).Read> (File Offset: 0x46870)
/home/hanzhao/workspace/go_runtime/main.go:15
}
 808fbcf:	81 c4 84 00 00 00    	add    $0x84,%esp
 808fbd5:	c3                   	ret    
/home/hanzhao/workspace/go_runtime/main.go:11

func main() {
	go onxh()
}

func onxh() {
 808fbd6:	e8 05 81 ff ff       	call   8087ce0 <runtime.morestack_noctxt> (File Offset: 0x3fce0)
 808fbdb:	eb 83                	jmp    808fb60 <main.onxh> (File Offset: 0x47b60)
 808fbdd:	cc                   	int3   
 808fbde:	cc                   	int3   
 808fbdf:	cc                   	int3  
 
 
 
 //======================================2
 
// Open opens the named file for reading. If successful, methods on
// the returned file can be used for reading; the associated file
// descriptor has mode O_RDONLY.
// If there is an error, it will be of type *PathError.
func Open(name string) (*File, error) {
 808eaf0:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
 808eaf7:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx
 808eafd:	3b 61 08             	cmp    0x8(%ecx),%esp
 808eb00:	76 43                	jbe    808eb45 <os.Open+0x55> (File Offset: 0x46b45)
 808eb02:	83 ec 1c             	sub    $0x1c,%esp
/usr/lib/golang/src/os/file.go:247
	return OpenFile(name, O_RDONLY, 0)
 808eb05:	8b 44 24 20          	mov    0x20(%esp),%eax
 //################ 字符串地址
 808eb09:	89 04 24             	mov    %eax,(%esp)
 808eb0c:	8b 44 24 24          	mov    0x24(%esp),%eax
 //############## 文件名长度
 808eb10:	89 44 24 04          	mov    %eax,0x4(%esp)
 808eb14:	c7 44 24 08 00 00 00 	movl   $0x0,0x8(%esp)
 808eb1b:	00 
 //############# O_RDONLY 为0
 808eb1c:	c7 44 24 0c 00 00 00 	movl   $0x0,0xc(%esp)
 808eb23:	00 
 808eb24:	e8 17 03 00 00       	call   808ee40 <os.OpenFile> (File Offset: 0x46e40)
 808eb29:	8b 44 24 14          	mov    0x14(%esp),%eax
 808eb2d:	8b 4c 24 10          	mov    0x10(%esp),%ecx
 808eb31:	8b 54 24 18          	mov    0x18(%esp),%edx
 808eb35:	89 4c 24 28          	mov    %ecx,0x28(%esp)
 808eb39:	89 44 24 2c          	mov    %eax,0x2c(%esp)
 808eb3d:	89 54 24 30          	mov    %edx,0x30(%esp)
 808eb41:	83 c4 1c             	add    $0x1c,%esp
 808eb44:	c3                   	ret    
/usr/lib/golang/src/os/file.go:246

// Open opens the named file for reading. If successful, methods on
// the returned file can be used for reading; the associated file
// descriptor has mode O_RDONLY.
// If there is an error, it will be of type *PathError.
func Open(name string) (*File, error) {
 808eb45:	e8 96 91 ff ff       	call   8087ce0 <runtime.morestack_noctxt> (File Offset: 0x3fce0)
 808eb4a:	eb a4                	jmp    808eaf0 <os.Open> (File Offset: 0x46af0)
 808eb4c:	cc                   	int3   
 808eb4d:	cc                   	int3   
 808eb4e:	cc                   	int3   
 808eb4f:	cc                   	int3 
 
 
 
 
 
 
 
 
 
 //========================== 3

0808ee40 <os.OpenFile> (File Offset: 0x46e40):
os.OpenFile():
/usr/lib/golang/src/os/file_unix.go:86
// OpenFile is the generalized open call; most users will use Open
// or Create instead. It opens the named file with specified flag
// (O_RDONLY etc.) and perm, (0666 etc.) if applicable. If successful,
// methods on the returned File can be used for I/O.
// If there is an error, it will be of type *PathError.

stack:
fileMode
flag
len
name
ret

func OpenFile(name string, flag int, perm FileMode) (*File, error) {
 808ee40:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
 808ee47:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx
 808ee4d:	3b 61 08             	cmp    0x8(%ecx),%esp
 808ee50:	0f 86 75 01 00 00    	jbe    808efcb <os.OpenFile+0x18b> (File Offset: 0x46fcb)
 808ee56:	83 ec 28             	sub    $0x28,%esp
/usr/lib/golang/src/os/file_unix.go:97
	}

	var r int
	for {
		var e error
		r, e = syscall.Open(name, flag|syscall.O_CLOEXEC, syscallMode(perm))
 808ee59:	8b 44 24 38          	mov    0x38(%esp),%eax
 //##################### perm
 808ee5d:	89 c1                	mov    %eax,%ecx
 808ee5f:	25 ff 01 00 00       	and    $0x1ff,%eax
 808ee64:	f7 c1 00 00 80 00    	test   $0x800000,%ecx
 808ee6a:	74 05                	je     808ee71 <os.OpenFile+0x31> (File Offset: 0x46e71)
 808ee6c:	0d 00 08 00 00       	or     $0x800,%eax
 808ee71:	f7 c1 00 00 40 00    	test   $0x400000,%ecx
 808ee77:	74 05                	je     808ee7e <os.OpenFile+0x3e> (File Offset: 0x46e7e)
 808ee79:	0d 00 04 00 00       	or     $0x400,%eax
 808ee7e:	f7 c1 00 00 10 00    	test   $0x100000,%ecx
 808ee84:	74 05                	je     808ee8b <os.OpenFile+0x4b> (File Offset: 0x46e8b)
 808ee86:	0d 00 02 00 00       	or     $0x200,%eax
 
 
 808ee8b:	8b 4c 24 2c          	mov    0x2c(%esp),%ecx
 
 808ee8f:	89 0c 24             	mov    %ecx,(%esp)
 //############## name
 
 808ee92:	8b 54 24 30          	mov    0x30(%esp),%edx
 808ee96:	89 54 24 04          	mov    %edx,0x4(%esp)
 //########## name len
 
 808ee9a:	8b 5c 24 34          	mov    0x34(%esp),%ebx
 808ee9e:	81 cb 00 00 08 00    	or     $0x80000,%ebx
 808eea4:	89 5c 24 08          	mov    %ebx,0x8(%esp)
 //############## flag
 
 808eea8:	89 44 24 0c          	mov    %eax,0xc(%esp)
 808eeac:	e8 3f e9 ff ff       	call   808d7f0 <syscall.Open> (File Offset: 0x457f0)
 808eeb1:	8b 44 24 10          	mov    0x10(%esp),%eax
 808eeb5:	8b 4c 24 18          	mov    0x18(%esp),%ecx
 808eeb9:	89 4c 24 20          	mov    %ecx,0x20(%esp)
 808eebd:	8b 54 24 14          	mov    0x14(%esp),%edx
 808eec1:	89 54 24 1c          	mov    %edx,0x1c(%esp)
/usr/lib/golang/src/os/file_unix.go:98
		if e == nil {
 808eec5:	85 d2                	test   %edx,%edx
 808eec7:	0f 84 ca 00 00 00    	je     808ef97 <os.OpenFile+0x157> (File Offset: 0x46f97)
/usr/lib/golang/src/os/file_unix.go:109
		// fuse file systems (see http://golang.org/issue/11180).
		if runtime.GOOS == "darwin" && e == syscall.EINTR {
			continue
		}

		return nil, &PathError{"open", name, e}
 808eecd:	8d 05 80 ed 09 08    	lea    0x809ed80,%eax
 808eed3:	89 04 24             	mov    %eax,(%esp)
 808eed6:	e8 25 35 fc ff       	call   8052400 <runtime.newobject> (File Offset: 0xa400)
 808eedb:	8b 44 24 04          	mov    0x4(%esp),%eax
 808eedf:	89 44 24 24          	mov    %eax,0x24(%esp)
 808eee3:	c7 40 04 04 00 00 00 	movl   $0x4,0x4(%eax)
 808eeea:	8b 0d 60 54 0e 08    	mov    0x80e5460,%ecx
 808eef0:	85 c9                	test   %ecx,%ecx
 808eef2:	0f 85 84 00 00 00    	jne    808ef7c <os.OpenFile+0x13c> (File Offset: 0x46f7c)
 808eef8:	8d 0d 5c 53 0a 08    	lea    0x80a535c,%ecx
 808eefe:	89 08                	mov    %ecx,(%eax)
 808ef00:	8b 4c 24 30          	mov    0x30(%esp),%ecx
 808ef04:	89 48 0c             	mov    %ecx,0xc(%eax)
 808ef07:	8b 0d 60 54 0e 08    	mov    0x80e5460,%ecx
 808ef0d:	8d 50 08             	lea    0x8(%eax),%edx
 808ef10:	85 c9                	test   %ecx,%ecx
 808ef12:	75 52                	jne    808ef66 <os.OpenFile+0x126> (File Offset: 0x46f66)
 808ef14:	8b 4c 24 2c          	mov    0x2c(%esp),%ecx
 808ef18:	89 48 08             	mov    %ecx,0x8(%eax)
 808ef1b:	8b 4c 24 1c          	mov    0x1c(%esp),%ecx
 808ef1f:	89 48 10             	mov    %ecx,0x10(%eax)
 808ef22:	8b 0d 60 54 0e 08    	mov    0x80e5460,%ecx
 808ef28:	8d 50 14             	lea    0x14(%eax),%edx
 808ef2b:	85 c9                	test   %ecx,%ecx
 808ef2d:	75 21                	jne    808ef50 <os.OpenFile+0x110> (File Offset: 0x46f50)
 808ef2f:	8b 4c 24 20          	mov    0x20(%esp),%ecx
 808ef33:	89 48 14             	mov    %ecx,0x14(%eax)
 808ef36:	c7 44 24 3c 00 00 00 	movl   $0x0,0x3c(%esp)
 808ef3d:	00 
 808ef3e:	8d 0d b0 40 0d 08    	lea    0x80d40b0,%ecx
 808ef44:	89 4c 24 40          	mov    %ecx,0x40(%esp)
 808ef48:	89 44 24 44          	mov    %eax,0x44(%esp)
 808ef4c:	83 c4 28             	add    $0x28,%esp
 808ef4f:	c3                   	ret    
 808ef50:	89 14 24             	mov    %edx,(%esp)
 808ef53:	8b 4c 24 20          	mov    0x20(%esp),%ecx
 808ef57:	89 4c 24 04          	mov    %ecx,0x4(%esp)
 808ef5b:	e8 50 3c fc ff       	call   8052bb0 <runtime.writebarrierptr> (File Offset: 0xabb0)
 808ef60:	8b 44 24 24          	mov    0x24(%esp),%eax
 808ef64:	eb d0                	jmp    808ef36 <os.OpenFile+0xf6> (File Offset: 0x46f36)
 808ef66:	89 14 24             	mov    %edx,(%esp)
 808ef69:	8b 4c 24 2c          	mov    0x2c(%esp),%ecx
 808ef6d:	89 4c 24 04          	mov    %ecx,0x4(%esp)
 808ef71:	e8 3a 3c fc ff       	call   8052bb0 <runtime.writebarrierptr> (File Offset: 0xabb0)
 808ef76:	8b 44 24 24          	mov    0x24(%esp),%eax
 808ef7a:	eb 9f                	jmp    808ef1b <os.OpenFile+0xdb> (File Offset: 0x46f1b)
 808ef7c:	89 04 24             	mov    %eax,(%esp)
 808ef7f:	8d 0d 5c 53 0a 08    	lea    0x80a535c,%ecx
 808ef85:	89 4c 24 04          	mov    %ecx,0x4(%esp)
 808ef89:	e8 22 3c fc ff       	call   8052bb0 <runtime.writebarrierptr> (File Offset: 0xabb0)
 808ef8e:	8b 44 24 24          	mov    0x24(%esp),%eax
 808ef92:	e9 69 ff ff ff       	jmp    808ef00 <os.OpenFile+0xc0> (File Offset: 0x46f00)
/usr/lib/golang/src/os/file_unix.go:123
	// content to live with. See ../syscall/exec_unix.go.
	if !supportsCloseOnExec {
		syscall.CloseOnExec(r)
	}

	return NewFile(uintptr(r), name), nil
 808ef97:	89 04 24             	mov    %eax,(%esp)
 808ef9a:	8b 44 24 2c          	mov    0x2c(%esp),%eax
 808ef9e:	89 44 24 04          	mov    %eax,0x4(%esp)
 808efa2:	8b 44 24 30          	mov    0x30(%esp),%eax
 808efa6:	89 44 24 08          	mov    %eax,0x8(%esp)
 808efaa:	e8 71 fd ff ff       	call   808ed20 <os.NewFile> (File Offset: 0x46d20)
 808efaf:	8b 44 24 0c          	mov    0xc(%esp),%eax
 808efb3:	89 44 24 3c          	mov    %eax,0x3c(%esp)
 808efb7:	c7 44 24 40 00 00 00 	movl   $0x0,0x40(%esp)
 808efbe:	00 
 808efbf:	c7 44 24 44 00 00 00 	movl   $0x0,0x44(%esp)
 808efc6:	00 
 808efc7:	83 c4 28             	add    $0x28,%esp
 808efca:	c3                   	ret    
/usr/lib/golang/src/os/file_unix.go:86
// OpenFile is the generalized open call; most users will use Open
// or Create instead. It opens the named file with specified flag
// (O_RDONLY etc.) and perm, (0666 etc.) if applicable. If successful,
// methods on the returned File can be used for I/O.
// If there is an error, it will be of type *PathError.
func OpenFile(name string, flag int, perm FileMode) (*File, error) {
 808efcb:	e8 10 8d ff ff       	call   8087ce0 <runtime.morestack_noctxt> (File Offset: 0x3fce0)
 808efd0:	e9 6b fe ff ff       	jmp    808ee40 <os.OpenFile> (File Offset: 0x46e40)
 808efd5:	cc                   	int3   
 808efd6:	cc                   	int3   
 808efd7:	cc                   	int3   
 808efd8:	cc                   	int3   
 808efd9:	cc                   	int3   
 808efda:	cc                   	int3   
 808efdb:	cc                   	int3   
 808efdc:	cc                   	int3   
 808efdd:	cc                   	int3   
 808efde:	cc                   	int3   
 808efdf:	cc                   	int3   
 
 
 
 // ============================ 

func Open(path string, mode int, perm uint32) (fd int, err error) {
 808d7f0:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
 808d7f7:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx
 808d7fd:	3b 61 08             	cmp    0x8(%ecx),%esp
 808d800:	76 50                	jbe    808d852 <syscall.Open+0x62> (File Offset: 0x45852)
 808d802:	83 ec 20             	sub    $0x20,%esp
/usr/lib/golang/src/syscall/syscall_linux.go:51
	return openat(_AT_FDCWD, path, mode|O_LARGEFILE, perm)
 808d805:	c7 04 24 9c ff ff ff 	movl   $0xffffff9c,(%esp)
 808d80c:	8b 44 24 24          	mov    0x24(%esp),%eax
 //############### name
 808d810:	89 44 24 04          	mov    %eax,0x4(%esp)
 808d814:	8b 44 24 28          	mov    0x28(%esp),%eax

 808d818:	89 44 24 08          	mov    %eax,0x8(%esp)
  //############ 长度
  
 808d81c:	8b 44 24 2c          	mov    0x2c(%esp),%eax
 808d820:	0d 00 80 00 00       	or     $0x8000,%eax
 808d825:	89 44 24 0c          	mov    %eax,0xc(%esp)
 //############## mode
 
 808d829:	8b 44 24 30          	mov    0x30(%esp),%eax
 808d82d:	89 44 24 10          	mov    %eax,0x10(%esp)
 808d831:	e8 8a 02 00 00       	call   808dac0 <syscall.openat> (File Offset: 0x45ac0)
 808d836:	8b 44 24 1c          	mov    0x1c(%esp),%eax
 808d83a:	8b 4c 24 18          	mov    0x18(%esp),%ecx
 808d83e:	8b 54 24 14          	mov    0x14(%esp),%edx
 808d842:	89 54 24 34          	mov    %edx,0x34(%esp)
 808d846:	89 4c 24 38          	mov    %ecx,0x38(%esp)
 808d84a:	89 44 24 3c          	mov    %eax,0x3c(%esp)
 808d84e:	83 c4 20             	add    $0x20,%esp
 808d851:	c3                   	ret    
/usr/lib/golang/src/syscall/syscall_linux.go:50
 
 
 
 //================================
 
0808dac0 <syscall.openat> (File Offset: 0x45ac0):
syscall.openat():
/usr/lib/golang/src/syscall/zsyscall_linux_386.go:34
	return
}

// THIS FILE IS GENERATED BY THE COMMAND AT THE TOP; DO NOT EDIT

func openat(dirfd int, path string, flags int, mode uint32) (fd int, err error) {
 808dac0:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
 808dac7:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx
 808dacd:	3b 61 08             	cmp    0x8(%ecx),%esp
 808dad0:	0f 86 2a 01 00 00    	jbe    808dc00 <syscall.openat+0x140> (File Offset: 0x45c00)
 808dad6:	83 ec 44             	sub    $0x44,%esp
/usr/lib/golang/src/syscall/zsyscall_linux_386.go:36
	var _p0 *byte
	_p0, err = BytePtrFromString(path)
 808dad9:	8b 44 24 4c          	mov    0x4c(%esp),%eax
 808dadd:	89 04 24             	mov    %eax,(%esp)
 808dae0:	8b 44 24 50          	mov    0x50(%esp),%eax
 808dae4:	89 44 24 04          	mov    %eax,0x4(%esp)
 808dae8:	e8 83 fc ff ff       	call   808d770 <syscall.BytePtrFromString> (File Offset: 0x45770)
 808daed:	8b 44 24 08          	mov    0x8(%esp),%eax
 808daf1:	89 44 24 34          	mov    %eax,0x34(%esp)
 808daf5:	8b 4c 24 10          	mov    0x10(%esp),%ecx
 808daf9:	89 4c 24 3c          	mov    %ecx,0x3c(%esp)
 808dafd:	8b 54 24 0c          	mov    0xc(%esp),%edx
 808db01:	89 54 24 38          	mov    %edx,0x38(%esp)
/usr/lib/golang/src/syscall/zsyscall_linux_386.go:37
	if err != nil {
 808db05:	85 d2                	test   %edx,%edx
 808db07:	0f 85 df 00 00 00    	jne    808dbec <syscall.openat+0x12c> (File Offset: 0x45bec)
/usr/lib/golang/src/syscall/zsyscall_linux_386.go:40
		return
	}
	r0, _, e1 := Syscall6(SYS_OPENAT, uintptr(dirfd), uintptr(unsafe.Pointer(_p0)), uintptr(flags), uintptr(mode), 0, 0)
 808db0d:	89 44 24 40          	mov    %eax,0x40(%esp)
 808db11:	c7 04 24 27 01 00 00 	movl   $0x127,(%esp)
 808db18:	8b 5c 24 48          	mov    0x48(%esp),%ebx
 808db1c:	89 5c 24 04          	mov    %ebx,0x4(%esp)
 808db20:	8b 5c 24 40          	mov    0x40(%esp),%ebx
 808db24:	89 5c 24 08          	mov    %ebx,0x8(%esp)
 808db28:	8b 5c 24 54          	mov    0x54(%esp),%ebx
 808db2c:	89 5c 24 0c          	mov    %ebx,0xc(%esp)
 808db30:	8b 5c 24 58          	mov    0x58(%esp),%ebx
 808db34:	89 5c 24 10          	mov    %ebx,0x10(%esp)
 808db38:	c7 44 24 14 00 00 00 	movl   $0x0,0x14(%esp)
 808db3f:	00 
 808db40:	c7 44 24 18 00 00 00 	movl   $0x0,0x18(%esp)
 808db47:	00 
 808db48:	e8 93 07 00 00       	call   808e2e0 <syscall.Syscall6> (File Offset: 0x462e0)
 808db4d:	8b 44 24 1c          	mov    0x1c(%esp),%eax
 808db51:	89 44 24 28          	mov    %eax,0x28(%esp)
 808db55:	8b 4c 24 24          	mov    0x24(%esp),%ecx
 808db59:	89 4c 24 2c          	mov    %ecx,0x2c(%esp)
/usr/lib/golang/src/syscall/zsyscall_linux_386.go:41
	use(unsafe.Pointer(_p0))
 808db5d:	8b 54 24 34          	mov    0x34(%esp),%edx
 808db61:	89 14 24             	mov    %edx,(%esp)
 808db64:	e8 07 07 00 00       	call   808e270 <syscall.use> (File Offset: 0x46270)
/usr/lib/golang/src/syscall/zsyscall_linux_386.go:43
	fd = int(r0)
	if e1 != 0 {
 808db69:	8b 44 24 2c          	mov    0x2c(%esp),%eax
 808db6d:	85 c0                	test   %eax,%eax
 808db6f:	74 71                	je     808dbe2 <syscall.openat+0x122> (File Offset: 0x45be2)
/usr/lib/golang/src/syscall/zsyscall_linux_386.go:44
		err = errnoErr(e1)
 808db71:	83 f8 02             	cmp    $0x2,%eax
 808db74:	77 46                	ja     808dbbc <syscall.openat+0xfc> (File Offset: 0x45bbc)
 808db76:	75 20                	jne    808db98 <syscall.openat+0xd8> (File Offset: 0x45b98)
 808db78:	8b 05 cc 4a 0d 08    	mov    0x80d4acc,%eax
 808db7e:	8b 0d c8 4a 0d 08    	mov    0x80d4ac8,%ecx
/usr/lib/golang/src/syscall/zsyscall_linux_386.go:46
	}
	return
 808db84:	8b 54 24 28          	mov    0x28(%esp),%edx
 808db88:	89 54 24 5c          	mov    %edx,0x5c(%esp)
 808db8c:	89 4c 24 60          	mov    %ecx,0x60(%esp)
 808db90:	89 44 24 64          	mov    %eax,0x64(%esp)
 808db94:	83 c4 44             	add    $0x44,%esp
 808db97:	c3                   	ret    
/usr/lib/golang/src/syscall/zsyscall_linux_386.go:44
	}
	r0, _, e1 := Syscall6(SYS_OPENAT, uintptr(dirfd), uintptr(unsafe.Pointer(_p0)), uintptr(flags), uintptr(mode), 0, 0)
	use(unsafe.Pointer(_p0))
	fd = int(r0)
	if e1 != 0 {
		err = errnoErr(e1)
 808db98:	89 44 24 30          	mov    %eax,0x30(%esp)
 808db9c:	8d 05 f0 40 0d 08    	lea    0x80d40f0,%eax
 808dba2:	89 04 24             	mov    %eax,(%esp)
 808dba5:	8d 44 24 30          	lea    0x30(%esp),%eax
 808dba9:	89 44 24 04          	mov    %eax,0x4(%esp)
 808dbad:	e8 2e 28 fc ff       	call   80503e0 <runtime.convT2I> (File Offset: 0x83e0)
 808dbb2:	8b 44 24 0c          	mov    0xc(%esp),%eax
 808dbb6:	8b 4c 24 08          	mov    0x8(%esp),%ecx
/usr/lib/golang/src/syscall/zsyscall_linux_386.go:46
	}
	return
 808dbba:	eb c8                	jmp    808db84 <syscall.openat+0xc4> (File Offset: 0x45b84)
/usr/lib/golang/src/syscall/zsyscall_linux_386.go:44
	}
	r0, _, e1 := Syscall6(SYS_OPENAT, uintptr(dirfd), uintptr(unsafe.Pointer(_p0)), uintptr(flags), uintptr(mode), 0, 0)
	use(unsafe.Pointer(_p0))
	fd = int(r0)
	if e1 != 0 {
		err = errnoErr(e1)
 808dbbc:	83 f8 0b             	cmp    $0xb,%eax
 808dbbf:	75 0e                	jne    808dbcf <syscall.openat+0x10f> (File Offset: 0x45bcf)
 808dbc1:	8b 05 bc 4a 0d 08    	mov    0x80d4abc,%eax
 808dbc7:	8b 0d b8 4a 0d 08    	mov    0x80d4ab8,%ecx
/usr/lib/golang/src/syscall/zsyscall_linux_386.go:46
	}
	return
 808dbcd:	eb b5                	jmp    808db84 <syscall.openat+0xc4> (File Offset: 0x45b84)
/usr/lib/golang/src/syscall/zsyscall_linux_386.go:44
	}
	r0, _, e1 := Syscall6(SYS_OPENAT, uintptr(dirfd), uintptr(unsafe.Pointer(_p0)), uintptr(flags), uintptr(mode), 0, 0)
	use(unsafe.Pointer(_p0))
	fd = int(r0)
	if e1 != 0 {
		err = errnoErr(e1)
 808dbcf:	83 f8 16             	cmp    $0x16,%eax
 808dbd2:	75 c4                	jne    808db98 <syscall.openat+0xd8> (File Offset: 0x45b98)
 808dbd4:	8b 05 c4 4a 0d 08    	mov    0x80d4ac4,%eax
 808dbda:	8b 0d c0 4a 0d 08    	mov    0x80d4ac0,%ecx
/usr/lib/golang/src/syscall/zsyscall_linux_386.go:46
	}
	return
 808dbe0:	eb a2                	jmp    808db84 <syscall.openat+0xc4> (File Offset: 0x45b84)
 808dbe2:	8b 4c 24 38          	mov    0x38(%esp),%ecx
 808dbe6:	8b 44 24 3c          	mov    0x3c(%esp),%eax
 808dbea:	eb 98                	jmp    808db84 <syscall.openat+0xc4> (File Offset: 0x45b84)
/usr/lib/golang/src/syscall/zsyscall_linux_386.go:38

func openat(dirfd int, path string, flags int, mode uint32) (fd int, err error) {
	var _p0 *byte
	_p0, err = BytePtrFromString(path)
	if err != nil {
		return
 808dbec:	c7 44 24 5c 00 00 00 	movl   $0x0,0x5c(%esp)
 808dbf3:	00 
 808dbf4:	89 54 24 60          	mov    %edx,0x60(%esp)
 808dbf8:	89 4c 24 64          	mov    %ecx,0x64(%esp)
 808dbfc:	83 c4 44             	add    $0x44,%esp
 808dbff:	c3                   	ret    
/usr/lib/golang/src/syscall/zsyscall_linux_386.go:34
	return
}

// THIS FILE IS GENERATED BY THE COMMAND AT THE TOP; DO NOT EDIT

func openat(dirfd int, path string, flags int, mode uint32) (fd int, err error) {
 808dc00:	e8 db a0 ff ff       	call   8087ce0 <runtime.morestack_noctxt> (File Offset: 0x3fce0)
 808dc05:	e9 b6 fe ff ff       	jmp    808dac0 <syscall.openat> (File Offset: 0x45ac0)
 808dc0a:	cc                   	int3   
 808dc0b:	cc                   	int3   
 808dc0c:	cc                   	int3   
 808dc0d:	cc                   	int3   
 808dc0e:	cc                   	int3   
 808dc0f:	cc                   	int3  
 
 
 
 
 //================================
0808e2e0 <syscall.Syscall6> (File Offset: 0x462e0):
syscall.Syscall6():
/usr/lib/golang/src/syscall/asm_linux_386.s:45

// func Syscall6(trap uintptr, a1, a2, a3, a4, a5, a6 uintptr) (r1, r2, err uintptr);
TEXT	·Syscall6(SB),NOSPLIT,$0-40
	CALL	runtime·entersyscall(SB)
 808e2e0:	e8 bb 17 fe ff       	call   806faa0 <runtime.entersyscall> (File Offset: 0x27aa0)
/usr/lib/golang/src/syscall/asm_linux_386.s:46
	MOVL	trap+0(FP), AX	// syscall entry
 808e2e5:	8b 44 24 04          	mov    0x4(%esp),%eax
/usr/lib/golang/src/syscall/asm_linux_386.s:47
	MOVL	a1+4(FP), BX
 808e2e9:	8b 5c 24 08          	mov    0x8(%esp),%ebx
/usr/lib/golang/src/syscall/asm_linux_386.s:48
	MOVL	a2+8(FP), CX
 808e2ed:	8b 4c 24 0c          	mov    0xc(%esp),%ecx
/usr/lib/golang/src/syscall/asm_linux_386.s:49
	MOVL	a3+12(FP), DX
 808e2f1:	8b 54 24 10          	mov    0x10(%esp),%edx
/usr/lib/golang/src/syscall/asm_linux_386.s:50
	MOVL	a4+16(FP), SI
 808e2f5:	8b 74 24 14          	mov    0x14(%esp),%esi
/usr/lib/golang/src/syscall/asm_linux_386.s:51
	MOVL	a5+20(FP), DI
 808e2f9:	8b 7c 24 18          	mov    0x18(%esp),%edi
/usr/lib/golang/src/syscall/asm_linux_386.s:52
	MOVL	a6+24(FP), BP
 808e2fd:	8b 6c 24 1c          	mov    0x1c(%esp),%ebp
 
 
 
/usr/lib/golang/src/syscall/asm_linux_386.s:53
	INVOKE_SYSCALL
 808e301:	cd 80                	int    $0x80
/usr/lib/golang/src/syscall/asm_linux_386.s:54
	CMPL	AX, $0xfffff001
 808e303:	3d 01 f0 ff ff       	cmp    $0xfffff001,%eax
/usr/lib/golang/src/syscall/asm_linux_386.s:55
	JLS	ok6
 808e308:	76 1c                	jbe    808e326 <syscall.Syscall6+0x46> (File Offset: 0x46326)
/usr/lib/golang/src/syscall/asm_linux_386.s:56
	MOVL	$-1, r1+28(FP)
 808e30a:	c7 44 24 20 ff ff ff 	movl   $0xffffffff,0x20(%esp)
 808e311:	ff 
/usr/lib/golang/src/syscall/asm_linux_386.s:57
	MOVL	$0, r2+32(FP)
 808e312:	c7 44 24 24 00 00 00 	movl   $0x0,0x24(%esp)
 808e319:	00 
/usr/lib/golang/src/syscall/asm_linux_386.s:58
	NEGL	AX
 808e31a:	f7 d8                	neg    %eax
/usr/lib/golang/src/syscall/asm_linux_386.s:59
	MOVL	AX, err+36(FP)
 808e31c:	89 44 24 28          	mov    %eax,0x28(%esp)
/usr/lib/golang/src/syscall/asm_linux_386.s:60
	CALL	runtime·exitsyscall(SB)
 808e320:	e8 fb 1a fe ff       	call   806fe20 <runtime.exitsyscall> (File Offset: 0x27e20)
/usr/lib/golang/src/syscall/asm_linux_386.s:61
	RET
 808e325:	c3                   	ret    
 
 
 
 
 
/usr/lib/golang/src/syscall/asm_linux_386.s:63
ok6:
	MOVL	AX, r1+28(FP)
 808e326:	89 44 24 20          	mov    %eax,0x20(%esp)
/usr/lib/golang/src/syscall/asm_linux_386.s:64
	MOVL	DX, r2+32(FP)
 808e32a:	89 54 24 24          	mov    %edx,0x24(%esp)
/usr/lib/golang/src/syscall/asm_linux_386.s:65
	MOVL	$0, err+36(FP)
 808e32e:	c7 44 24 28 00 00 00 	movl   $0x0,0x28(%esp)
 808e335:	00 
/usr/lib/golang/src/syscall/asm_linux_386.s:66
	CALL	runtime·exitsyscall(SB)
 808e336:	e8 e5 1a fe ff       	call   806fe20 <runtime.exitsyscall> (File Offset: 0x27e20)
/usr/lib/golang/src/syscall/asm_linux_386.s:67
	RET
 808e33b:	c3                   	ret    
 808e33c:	cc                   	int3   
 808e33d:	cc                   	int3   
 808e33e:	cc                   	int3   
 808e33f:	cc                   	int3   
 
 
 
 
 
 //========================================
// Standard syscall entry used by the go syscall library and normal cgo calls.
//go:nosplit
func entersyscall(dummy int32) {
 806faa0:	83 ec 08             	sub    $0x8,%esp
 806faa3:	8d 44 24 0c          	lea    0xc(%esp),%eax
/usr/lib/golang/src/runtime/proc.go:2488
	reentersyscall(getcallerpc(unsafe.Pointer(&dummy)), getcallersp(unsafe.Pointer(&dummy)))
 806faa7:	89 04 24             	mov    %eax,(%esp)
 806faaa:	e8 31 96 01 00       	call   80890e0 <runtime.getcallerpc> (File Offset: 0x410e0)
 806faaf:	8b 44 24 04          	mov    0x4(%esp),%eax
/usr/lib/golang/src/runtime/proc.go:2487
	_g_.m.locks--
}

// Standard syscall entry used by the go syscall library and normal cgo calls.
//go:nosplit
func entersyscall(dummy int32) {
 806fab3:	8d 4c 24 0c          	lea    0xc(%esp),%ecx
/usr/lib/golang/src/runtime/proc.go:2488
	reentersyscall(getcallerpc(unsafe.Pointer(&dummy)), getcallersp(unsafe.Pointer(&dummy)))
 806fab7:	89 04 24             	mov    %eax,(%esp)
 806faba:	89 4c 24 04          	mov    %ecx,0x4(%esp)
 806fabe:	e8 dd fd ff ff       	call   806f8a0 <runtime.reentersyscall> (File Offset: 0x278a0)
/usr/lib/golang/src/runtime/proc.go:2489
}
 806fac3:	83 c4 08             	add    $0x8,%esp
 806fac6:	c3                   	ret    
 806fac7:	cc                   	int3   
 806fac8:	cc                   	int3   
 806fac9:	cc                   	int3   
 806faca:	cc                   	int3   
 806facb:	cc                   	int3   
 806facc:	cc                   	int3   
 806facd:	cc                   	int3   
 806face:	cc                   	int3   
 806facf:	cc                   	int3   
~~~

