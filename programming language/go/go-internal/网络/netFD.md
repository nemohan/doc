# netFD

[TOC]



### netFD

net/fd_unix.go

~~~go
// Network file descriptor.
type netFD struct {
	// locking/lifetime of sysfd + serialize access to Read and Write methods
	fdmu fdMutex

	// immutable until Close
	sysfd       int
	family      int
	sotype      int
	isStream    bool
	isConnected bool
	net         string
	laddr       Addr
	raddr       Addr

	// writev cache.
	iovecs *[]syscall.Iovec

	// wait server
	pd pollDesc
}
~~~



##### newFD 套接字转换

net/fd_unix.go

~~~go
func newFD(sysfd, family, sotype int, net string) (*netFD, error) {
	return &netFD{sysfd: sysfd, 
                  family: family, 
                  sotype: sotype, net: net, 
                  isStream: sotype == syscall.SOCK_STREAM}, nil
}

~~~



##### netFD.listenStream

net/sock_posix.go

* 调用setDefaultListenerSockopts 设置REUSEADDR
* 调用fd.init初始化轮询器

~~~go
func (fd *netFD) listenStream(laddr sockaddr, backlog int) error {
	if err := setDefaultListenerSockopts(fd.sysfd); err != nil {
		return err
	}
	if lsa, err := laddr.sockaddr(fd.family); err != nil {
		return err
	} else if lsa != nil {
		if err := syscall.Bind(fd.sysfd, lsa); err != nil {
			return os.NewSyscallError("bind", err)
		}
	}
	if err := listenFunc(fd.sysfd, backlog); err != nil {
		return os.NewSyscallError("listen", err)
	}
	if err := fd.init(); err != nil {
		return err
	}
	lsa, _ := syscall.Getsockname(fd.sysfd)
	fd.setAddr(fd.addrFunc()(lsa), nil)
	return nil
}
~~~



##### netFD.init 初始化poller

net/fd_unix.go

* 调用pllDesc.init 初始化轮询器

~~~go
func (fd *netFD) init() error {
	if err := fd.pd.init(fd); err != nil {
		return err
	}
	return nil
}
~~~



##### netFD.Close

net/fd_unix.go

~~~go
func (fd *netFD) Close() error {
	if !fd.fdmu.increfAndClose() {
		return errClosing
	}
	// Unblock any I/O.  Once it all unblocks and returns,
	// so that it cannot be referring to fd.sysfd anymore,
	// the final decref will close fd.sysfd. This should happen
	// fairly quickly, since all the I/O is non-blocking, and any
	// attempts to block in the pollDesc will return errClosing.
	fd.pd.evict()
	fd.decref()
	return nil
}
~~~



##### netFD.destroy

net/fd_unix.go

~~~go
func (fd *netFD) destroy() {
	// Poller may want to unregister fd in readiness notification mechanism,
	// so this must be executed before closeFunc.
	fd.pd.close()
	closeFunc(fd.sysfd)
	fd.sysfd = -1
	runtime.SetFinalizer(fd, nil)
}
~~~



##### netFD.readLock 读锁

net/fdMutex.go

* 

~~~go
// readLock adds a reference to fd and locks fd for reading.
// It returns an error when fd cannot be used for reading.
func (fd *netFD) readLock() error {
	if !fd.fdmu.rwlock(true) {
		return errClosing
	}
	return nil
}
~~~