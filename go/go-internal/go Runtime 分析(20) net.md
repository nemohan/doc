

# net

以Accept 为例:

~~~go
// net/Dial.go
// Listen announces on the local network address laddr.
// The network net must be a stream-oriented network: "tcp", "tcp4",
// "tcp6", "unix" or "unixpacket".
// For TCP and UDP, the syntax of laddr is "host:port", like "127.0.0.1:8080".
// If host is omitted, as in ":8080", Listen listens on all available interfaces
// instead of just the interface with the given host address.
// See Dial for more details about address syntax.
//
// Listening on a hostname is not recommended because this creates a socket
// for at most one of its IP addresses.


// 从Listen开始入手
func Listen(net, laddr string) (Listener, error) {
	addrs, err := DefaultResolver.resolveAddrList(context.Background(), "listen", net, laddr, nil)
	if err != nil {
		return nil, &OpError{Op: "listen", Net: net, Source: nil, Addr: nil, Err: err}
	}
	var l Listener
	switch la := addrs.first(isIPv4).(type) {
	case *TCPAddr:
		l, err = ListenTCP(net, la)
	case *UnixAddr:
		l, err = ListenUnix(net, la)
	default:
		return nil, &OpError{Op: "listen", Net: net, Source: nil, Addr: la, Err: &AddrError{Err: "unexpected address type", Addr: laddr}}
	}
	if err != nil {
		return nil, err // l is non-nil interface containing nil pointer
	}
	return l, nil
}

~~~



~~~go

// ListenTCP announces on the TCP address laddr and returns a TCP
// listener. Net must be "tcp", "tcp4", or "tcp6".  If laddr has a
// port of 0, ListenTCP will choose an available port. The caller can
// use the Addr method of TCPListener to retrieve the chosen address.
func ListenTCP(net string, laddr *TCPAddr) (*TCPListener, error) {
	switch net {
	case "tcp", "tcp4", "tcp6":
	default:
		return nil, &OpError{Op: "listen", Net: net, Source: nil, Addr: laddr.opAddr(), Err: UnknownNetworkError(net)}
	}
	if laddr == nil {
		laddr = &TCPAddr{}
	}
	ln, err := listenTCP(context.Background(), net, laddr)
	if err != nil {
		return nil, &OpError{Op: "listen", Net: net, Source: nil, Addr: laddr.opAddr(), Err: err}
	}
	return ln, nil
}
~~~



~~~go
// tcpsock_posix.go
func listenTCP(ctx context.Context, network string, laddr *TCPAddr) (*TCPListener, error) {
	fd, err := internetSocket(ctx, network, laddr, nil, syscall.SOCK_STREAM, 0, "listen")
	if err != nil {
		return nil, err
	}
	return &TCPListener{fd}, nil
}
~~~





~~~go
// net/ipsock_posix.go
// Internet sockets (TCP, UDP, IP)
func internetSocket(ctx context.Context, net string, laddr, raddr sockaddr, sotype, proto int, mode string) (fd *netFD, err error) {
	if (runtime.GOOS == "windows" || runtime.GOOS == "openbsd" || runtime.GOOS == "nacl") && mode == "dial" && raddr.isWildcard() {
		raddr = raddr.toLocal(net)
	}
	family, ipv6only := favoriteAddrFamily(net, laddr, raddr, mode)
	return socket(ctx, net, family, sotype, proto, ipv6only, laddr, raddr)
}

~~~



~~~go
//net/sock_posix.go

// socket returns a network file descriptor that is ready for
// asynchronous I/O using the network poller.
func socket(ctx context.Context, net string, family, sotype, proto int, ipv6only bool, laddr, raddr sockaddr) (fd *netFD, err error) {
    
    // 此socket 会将文件描述符设置为NONBLOCK
	s, err := sysSocket(family, sotype, proto)
	if err != nil {
		return nil, err
	}
	if err = setDefaultSockopts(s, family, sotype, ipv6only); err != nil {
		closeFunc(s)
		return nil, err
	}
	if fd, err = newFD(s, family, sotype, net); err != nil {
		closeFunc(s)
		return nil, err
	}

	// This function makes a network file descriptor for the
	// following applications:
	//
	// - An endpoint holder that opens a passive stream
	//   connection, known as a stream listener
	//
	// - An endpoint holder that opens a destination-unspecific
	//   datagram connection, known as a datagram listener
	//
	// - An endpoint holder that opens an active stream or a
	//   destination-specific datagram connection, known as a
	//   dialer
	//
	// - An endpoint holder that opens the other connection, such
	//   as talking to the protocol stack inside the kernel
	//
	// For stream and datagram listeners, they will only require
	// named sockets, so we can assume that it's just a request
	// from stream or datagram listeners when laddr is not nil but
	// raddr is nil. Otherwise we assume it's just for dialers or
	// the other connection holders.

	if laddr != nil && raddr == nil {
		switch sotype {
		case syscall.SOCK_STREAM, syscall.SOCK_SEQPACKET:
            //此处的listenerBacklog， 如果是linux平台，会从/proc/sys/net/core/somaxconn获取
			if err := fd.listenStream(laddr, listenerBacklog); err != nil {
				fd.Close()
				return nil, err
			}
			return fd, nil
		case syscall.SOCK_DGRAM:
			if err := fd.listenDatagram(laddr); err != nil {
				fd.Close()
				return nil, err
			}
			return fd, nil
		}
	}
	if err := fd.dial(ctx, laddr, raddr); err != nil {
		fd.Close()
		return nil, err
	}
	return fd, nil
}


~~~





~~~go
// net/sock_posix.go

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









~~~go
// Wrapper around the socket system call that marks the returned file
// descriptor as nonblocking and close-on-exec.
func sysSocket(family, sotype, proto int) (int, error) {
	s, err := socketFunc(family, sotype|syscall.SOCK_NONBLOCK|syscall.SOCK_CLOEXEC, proto)
	// On Linux the SOCK_NONBLOCK and SOCK_CLOEXEC flags were
	// introduced in 2.6.27 kernel and on FreeBSD both flags were
	// introduced in 10 kernel. If we get an EINVAL error on Linux
	// or EPROTONOSUPPORT error on FreeBSD, fall back to using
	// socket without them.
	switch err {
	case nil:
		return s, nil
	default:
		return -1, os.NewSyscallError("socket", err)
	case syscall.EPROTONOSUPPORT, syscall.EINVAL:
	}

	// See ../syscall/exec_unix.go for description of ForkLock.
	syscall.ForkLock.RLock()
	s, err = socketFunc(family, sotype, proto)
	if err == nil {
		syscall.CloseOnExec(s)
	}
	syscall.ForkLock.RUnlock()
	if err != nil {
		return -1, os.NewSyscallError("socket", err)
	}
	if err = syscall.SetNonblock(s, true); err != nil {
		closeFunc(s)
		return -1, os.NewSyscallError("setnonblock", err)
	}
	return s, nil
}
~~~





~~~go

// net/fd_unix.go
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

func newFD(sysfd, family, sotype int, net string) (*netFD, error) {
	return &netFD{sysfd: sysfd, family: family, sotype: sotype, net: net, isStream: sotype == syscall.SOCK_STREAM}, nil
}

func (fd *netFD) init() error {
	if err := fd.pd.init(fd); err != nil {
		return err
	}
	return nil
}
~~~





~~~go
//net/fd_poll_runtime.go
// runtime_poolServerInit只会调用一次
func (pd *pollDesc) init(fd *netFD) error {
	serverInit.Do(runtime_pollServerInit)
	ctx, errno := runtime_pollOpen(uintptr(fd.sysfd))
	runtime.KeepAlive(fd)
	if errno != 0 {
		return syscall.Errno(errno)
	}
	pd.runtimeCtx = ctx
	return nil
}
~~~







~~~go
// runtime/netpoll.go
//go:linkname net_runtime_pollServerInit net.runtime_pollServerInit
func net_runtime_pollServerInit() {
	netpollinit()
    
    //调度模块会用到netpollInited
	atomic.Store(&netpollInited, 1)
}

func netpollinited() bool {
	return atomic.Load(&netpollInited) != 0
}

//go:linkname net_runtime_pollOpen net.runtime_pollOpen
func net_runtime_pollOpen(fd uintptr) (*pollDesc, int) {
	pd := pollcache.alloc()
	lock(&pd.lock)
	if pd.wg != 0 && pd.wg != pdReady {
		throw("netpollOpen: blocked write on free descriptor")
	}
	if pd.rg != 0 && pd.rg != pdReady {
		throw("netpollOpen: blocked read on free descriptor")
	}
	pd.fd = fd
	pd.closing = false
	pd.seq++
	pd.rg = 0
	pd.rd = 0
	pd.wg = 0
	pd.wd = 0
	unlock(&pd.lock)

	var errno int32
	errno = netpollopen(fd, pd)
	return pd, int(errno)
}

~~~





~~~go
// runtime/netpoll_epoll.go
// epfd是个全局变量。netpollinit 只会调用一次
func netpollinit() {
	epfd = epollcreate1(_EPOLL_CLOEXEC)
	if epfd >= 0 {
		return
	}
	epfd = epollcreate(1024)
	if epfd >= 0 {
		closeonexec(epfd)
		return
	}
	println("netpollinit: failed to create epoll descriptor", -epfd)
	throw("netpollinit: failed to create descriptor")
}

func netpollopen(fd uintptr, pd *pollDesc) int32 {
	var ev epollevent
	ev.events = _EPOLLIN | _EPOLLOUT | _EPOLLRDHUP | _EPOLLET
	*(**pollDesc)(unsafe.Pointer(&ev.data)) = pd
	return -epollctl(epfd, _EPOLL_CTL_ADD, int32(fd), &ev)
}
~~~







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
        //在创建socket时，已经设置为NONBLOCK， 所以会走到syscall.EAGAIN
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
			}
			return nil, err
		}
		break
	}

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





~~~go
//net/fd_poll_runtime.go

func (pd *pollDesc) wait(mode int) error {
	res := runtime_pollWait(pd.runtimeCtx, mode)
	return convertErr(res)
}

func (pd *pollDesc) waitRead() error {
	return pd.wait('r')
}

~~~





~~~go
// runtime/netpoll.go
//go:linkname net_runtime_pollWait net.runtime_pollWait
func net_runtime_pollWait(pd *pollDesc, mode int) int {
	err := netpollcheckerr(pd, int32(mode))
	if err != 0 {
		return err
	}
	// As for now only Solaris uses level-triggered IO.
	if GOOS == "solaris" {
		netpollarm(pd, mode)
	}
	for !netpollblock(pd, int32(mode), false) {
		err = netpollcheckerr(pd, int32(mode))
		if err != 0 {
			return err
		}
		// Can happen if timeout has fired and unblocked us,
		// but before we had a chance to run, timeout has been reset.
		// Pretend it has not happened and retry.
	}
	return 0
}
~~~





~~~go
// returns true if IO is ready, or false if timedout or closed
// waitio - wait only for completed IO, ignore errors
func netpollblock(pd *pollDesc, mode int32, waitio bool) bool {
	gpp := &pd.rg
	if mode == 'w' {
		gpp = &pd.wg
	}

	// set the gpp semaphore to WAIT
	for {
		old := *gpp
		if old == pdReady {
			*gpp = 0
			return true
		}
		if old != 0 {
			throw("netpollblock: double wait")
		}
		if atomic.Casuintptr(gpp, 0, pdWait) {
			break
		}
	}

	// need to recheck error states after setting gpp to WAIT
	// this is necessary because runtime_pollUnblock/runtime_pollSetDeadline/deadlineimpl
	// do the opposite: store to closing/rd/wd, membarrier, load of rg/wg
    //gopark 会切换当前运行的goruine到其他的gorutine
    // gopark 见 第19篇 mcall
	if waitio || netpollcheckerr(pd, mode) == 0 {
		gopark(netpollblockcommit, unsafe.Pointer(gpp), "IO wait", traceEvGoBlockNet, 5)
	}
    // gorutine 挂起后的恢复点
    
	// be careful to not lose concurrent READY notification
	old := atomic.Xchguintptr(gpp, 0)
	if old > pdWait {
		throw("netpollblock: corrupted state")
	}
	return old == pdReady
}



~~~





~~~go
//这一段比较重要========================
func netpollblockcommit(gp *g, gpp unsafe.Pointer) bool {
	return atomic.Casuintptr((*uintptr)(gpp), pdWait, uintptr(unsafe.Pointer(gp)))
}

~~~





~~~go
func netpollunblock(pd *pollDesc, mode int32, ioready bool) *g {
	gpp := &pd.rg
	if mode == 'w' {
		gpp = &pd.wg
	}

	for {
		old := *gpp
		if old == pdReady {
			return nil
		}
		if old == 0 && !ioready {
			// Only set READY for ioready. runtime_pollWait
			// will check for timeout/cancel before waiting.
			return nil
		}
		var new uintptr
		if ioready {
			new = pdReady
		}
		if atomic.Casuintptr(gpp, old, new) {
			if old == pdReady || old == pdWait {
				old = 0
			}
			return (*g)(unsafe.Pointer(old))
		}
	}
}
~~~





~~~go
/ make pd ready, newly runnable goroutines (if any) are returned in rg/wg
// May run during STW, so write barriers are not allowed.
//go:nowritebarrier
func netpollready(gpp *guintptr, pd *pollDesc, mode int32) {
	var rg, wg guintptr
	if mode == 'r' || mode == 'r'+'w' {
		rg.set(netpollunblock(pd, 'r', true))
	}
	if mode == 'w' || mode == 'r'+'w' {
		wg.set(netpollunblock(pd, 'w', true))
	}
	if rg != 0 {
		rg.ptr().schedlink = *gpp
		*gpp = rg
	}
	if wg != 0 {
		wg.ptr().schedlink = *gpp
		*gpp = wg
	}
}

~~~





~~~go
// polls for ready network connections
// returns list of goroutines that become runnable
func netpoll(block bool) *g {
	if epfd == -1 {
		return nil
	}
	waitms := int32(-1)
	if !block {
		waitms = 0
	}
	var events [128]epollevent
retry:
	n := epollwait(epfd, &events[0], int32(len(events)), waitms)
	if n < 0 {
		if n != -_EINTR {
			println("runtime: epollwait on fd", epfd, "failed with", -n)
			throw("epollwait failed")
		}
		goto retry
	}
	var gp guintptr
	for i := int32(0); i < n; i++ {
		ev := &events[i]
		if ev.events == 0 {
			continue
		}
		var mode int32
		if ev.events&(_EPOLLIN|_EPOLLRDHUP|_EPOLLHUP|_EPOLLERR) != 0 {
			mode += 'r'
		}
		if ev.events&(_EPOLLOUT|_EPOLLHUP|_EPOLLERR) != 0 {
			mode += 'w'
		}
		if mode != 0 {
			pd := *(**s)(unsafe.Pointer(&ev.data))

			netpollready(&gp, pd, mode)
		}
	}
	if block && gp == 0 {
		goto retry
	}
	return gp.ptr()
}
~~~

