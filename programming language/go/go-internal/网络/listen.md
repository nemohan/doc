# tcp 监听

[TOC]



##### Listener的定义

~~~go
// A Listener is a generic network listener for stream-oriented protocols.
//
// Multiple goroutines may invoke methods on a Listener simultaneously.
type Listener interface {
	// Accept waits for and returns the next connection to the listener.
	Accept() (Conn, error)

	// Close closes the listener.
	// Any blocked Accept operations will be unblocked and return errors.
	Close() error

	// Addr returns the listener's network address.
	Addr() Addr
}
~~~



##### Listen

net/dial.go

* 解析地址
* 根据地址类型确定监听TCP还是UNIX套接字

~~~go
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



##### ListenTCP 

net/tcpsock.go

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



##### listenTCP

net/tcpsock_posix.go

~~~go
func listenTCP(ctx context.Context, network string, laddr *TCPAddr) (*TCPListener, error) {
	fd, err := internetSocket(ctx, network, laddr, nil, syscall.SOCK_STREAM, 0, "listen")
	if err != nil {
		return nil, err
	}
	return &TCPListener{fd}, nil
}
~~~



##### internetSocket

ipsock_posix.go

~~~go
// Internet sockets (TCP, UDP, IP)
func internetSocket(ctx context.Context, net string, laddr, raddr sockaddr, sotype, proto int, mode string) (fd *netFD, err error) {
	if (runtime.GOOS == "windows" || runtime.GOOS == "openbsd" || runtime.GOOS == "nacl") && mode == "dial" && raddr.isWildcard() {
		raddr = raddr.toLocal(net)
	}
	family, ipv6only := favoriteAddrFamily(net, laddr, raddr, mode)
	return socket(ctx, net, family, sotype, proto, ipv6only, laddr, raddr)
}
~~~



##### socket

net/sock_posix.go

* 创建套接字
* 设置套接字选项
* 开始监听

~~~go
// socket returns a network file descriptor that is ready for
// asynchronous I/O using the network poller.
func socket(ctx context.Context, net string, family, sotype, proto int, ipv6only bool, laddr, raddr sockaddr) (fd *netFD, err error) {
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



##### sysSocket 创建套接字

net/sock_cloexec.go

* 调用系统调用创建套接字， 新创建的套接字为非阻塞模式
* 

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



##### 钩子

net/hook_unix.go

~~~go
var (
	testHookDialChannel  = func() {} // for golang.org/issue/5349
	testHookCanceledDial = func() {} // for golang.org/issue/16523

	// Placeholders for socket system calls.
	socketFunc        func(int, int, int) (int, error)         = syscall.Socket
	closeFunc         func(int) error                          = syscall.Close
	connectFunc       func(int, syscall.Sockaddr) error        = syscall.Connect
	listenFunc        func(int, int) error                     = syscall.Listen
	acceptFunc        func(int) (int, syscall.Sockaddr, error) = syscall.Accept
	getsockoptIntFunc func(int, int, int) (int, error)         = syscall.GetsockoptInt
)
~~~



##### maxListenerBacklog 设置全局变量listenerBacklog

sock_linux.go

* listenerBacklog 要么从/proc/sys/net/core/somaxconn获取，要么返回默认值syscall.SOMAXCONN
* syscall.SOMACONN 定义在syscall/zerrors_linux_386.go文件中，即128
* listenerBacklog最大是65535

~~~go
func maxListenerBacklog() int {
	fd, err := open("/proc/sys/net/core/somaxconn")
	if err != nil {
		return syscall.SOMAXCONN
	}
	defer fd.close()
	l, ok := fd.readLine()
	if !ok {
		return syscall.SOMAXCONN
	}
	f := getFields(l)
	n, _, ok := dtoi(f[0])
	if n == 0 || !ok {
		return syscall.SOMAXCONN
	}
	// Linux stores the backlog in a uint16.
	// Truncate number to avoid wrapping.
	// See issue 5030.
	if n > 1<<16-1 {
		n = 1<<16 - 1
	}
	return n
}
~~~



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



### pollDesc

net/fd_poll_runtime.go

pollDesc只是对runtime/netpoll.go 中定义的pollDesc的简单封装

~~~go
type pollDesc struct {
	runtimeCtx uintptr
}
~~~



##### pollDesc.init

net/fd_poll_runtime.go

* <font color="red">调用runtime_pollServerInit(runtime/netpoll.go )初始化轮询器,该初始化只会执行一次。也意味着全局只有一个epoll文件描述符</font>
* 调用runtime_pollOpen会将`文件描述符`添加到epoll中, runtime_pollOpen返回的ctx实际是一个指向runtime.pollDesc结构的指针

~~~go
var serverInit sync.Once

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



##### pollDesc.prepareRead

~~~go
func (pd *pollDesc) prepareRead() error {
	return pd.prepare('r')
}
~~~



##### pollDesc.prepare

~~~go
func (pd *pollDesc) prepare(mode int) error {
	res := runtime_pollReset(pd.runtimeCtx, mode)
	return convertErr(res)
}
~~~

