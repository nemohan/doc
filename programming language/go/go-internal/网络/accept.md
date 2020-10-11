# 等待链接

[TOC]



##### TCPListener.Accept

net/tcpsock.go

~~~go
// Accept implements the Accept method in the Listener interface; it
// waits for the next call and returns a generic Conn.
func (l *TCPListener) Accept() (Conn, error) {
	if !l.ok() {
		return nil, syscall.EINVAL
	}
	c, err := l.accept()
	if err != nil {
		return nil, &OpError{Op: "accept", Net: l.fd.net, Source: nil, Addr: l.fd.laddr, Err: err}
	}
	return c, nil
}
~~~



##### TCPListener.accept 等待新链接并创建TCPConn

net/tcpsock_posix.go

~~~go
func (ln *TCPListener) accept() (*TCPConn, error) {
	fd, err := ln.fd.accept()
	if err != nil {
		return nil, err
	}
	return newTCPConn(fd), nil
}
~~~



##### netFD.accept

net/fd_unix.go

* 加读锁fd.readLock

* 为什么调用pd.prepareRead, 做一些检查

* 监听的套接字已被设置为非阻塞，调用accept会返回syscall.EAGAIN错误，转而调用fd.pd.waitRead使得当前协程进入等待状态
* 调用newFD为新链接创建netFD, 然后调用netfd.init添加`文件描述符`到epoll中
* 

~~~go
func (fd *netFD) accept() (netfd *netFD, err error) {
	if err := fd.readLock(); err != nil {
		return nil, err
	}
	defer fd.readUnlock()

	var s int
	var rsa syscall.Sockaddr
	if err = fd.pd.prepareRead(); err != nil {
		return nil, err
	}
	for {
		s, rsa, err = accept(fd.sysfd)
		if err != nil {
			nerr, ok := err.(*os.SyscallError)
			if !ok {
				return nil, err
			}
			switch nerr.Err {
			case syscall.EAGAIN:
				if err = fd.pd.waitRead(); err == nil {
					continue
				}
			case syscall.ECONNABORTED:
				// This means that a socket on the
				// listen queue was closed before we
				// Accept()ed it; it's a silly error,
				// so try again.
				continue
			}//end switch
			return nil, err
		}//end if
		break
	}//end for

	if netfd, err = newFD(s, fd.family, fd.sotype, fd.net); err != nil {
		closeFunc(s)
		return nil, err
	}
	if err = netfd.init(); err != nil {
		fd.Close()
		return nil, err
	}
	lsa, _ := syscall.Getsockname(netfd.sysfd)
	netfd.setAddr(netfd.addrFunc()(lsa), netfd.addrFunc()(rsa))
	return netfd, nil
}

~~~



##### accept

net/sock_cloexec.go

* 调用syscall.Accept
* 设置描述符非阻塞

~~~go
// Wrapper around the accept system call that marks the returned file
// descriptor as nonblocking and close-on-exec.
func accept(s int) (int, syscall.Sockaddr, error) {
	ns, sa, err := accept4Func(s, syscall.SOCK_NONBLOCK|syscall.SOCK_CLOEXEC)
	// On Linux the accept4 system call was introduced in 2.6.28
	// kernel and on FreeBSD it was introduced in 10 kernel. If we
	// get an ENOSYS error on both Linux and FreeBSD, or EINVAL
	// error on Linux, fall back to using accept.
	switch err {
	case nil:
		return ns, sa, nil
	default: // errors other than the ones listed
		return -1, sa, os.NewSyscallError("accept4", err)
	case syscall.ENOSYS: // syscall missing
	case syscall.EINVAL: // some Linux use this instead of ENOSYS
	case syscall.EACCES: // some Linux use this instead of ENOSYS
	case syscall.EFAULT: // some Linux use this instead of ENOSYS
	}

	// See ../syscall/exec_unix.go for description of ForkLock.
	// It is probably okay to hold the lock across syscall.Accept
	// because we have put fd.sysfd into non-blocking mode.
	// However, a call to the File method will put it back into
	// blocking mode. We can't take that risk, so no use of ForkLock here.
	ns, sa, err = acceptFunc(s)
	if err == nil {
		syscall.CloseOnExec(ns)
	}
	if err != nil {
		return -1, nil, os.NewSyscallError("accept", err)
	}
	if err = syscall.SetNonblock(ns, true); err != nil {
		closeFunc(ns)
		return -1, nil, os.NewSyscallError("setnonblock", err)
	}
	return ns, sa, nil
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

