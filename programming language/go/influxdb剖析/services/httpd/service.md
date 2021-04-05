# service

[TOC]

httpd提供http API接口读写influxdb。httpd的亮点在于使用了基于令牌桶机制限制并发链接数、并发写，值得借鉴。并发链接限制通过自定义limitListener实现、并发写限制通过Throttler实现。



### Service

##### Service的定义

~~~go
// Service manages the listener and handler for an HTTP endpoint.
type Service struct {
	ln        net.Listener
	addr      string
	https     bool
	cert      string
	key       string
	limit     int
	tlsConfig *tls.Config
	err       chan error

	unixSocket         bool
	unixSocketPerm     uint32
	unixSocketGroup    int
	bindSocket         string
	unixSocketListener net.Listener

	Handler *Handler

	Logger *zap.Logger
}
~~~



##### NewService

~~~go
// NewService returns a new instance of Service.
func NewService(c Config) *Service {
	s := &Service{
		addr:           c.BindAddress,
		https:          c.HTTPSEnabled,
		cert:           c.HTTPSCertificate,
		key:            c.HTTPSPrivateKey,
		limit:          c.MaxConnectionLimit,
		tlsConfig:      c.TLS,
		err:            make(chan error),
		unixSocket:     c.UnixSocketEnabled,
		unixSocketPerm: uint32(c.UnixSocketPermissions),
		bindSocket:     c.BindSocket,
		Handler:        NewHandler(c),
		Logger:         zap.NewNop(),
	}
	if s.tlsConfig == nil {
		s.tlsConfig = new(tls.Config)
	}
	if s.key == "" {
		s.key = s.cert
	}
	if c.UnixSocketGroup != nil {
		s.unixSocketGroup = int(*c.UnixSocketGroup)
	}
	s.Handler.Logger = s.Logger
	return s
}
~~~



##### Service.Open

~~~go
// Open starts the service.
func (s *Service) Open() error {
	s.Logger.Info("Starting HTTP service", zap.Bool("authentication", s.Handler.Config.AuthEnabled))

	s.Handler.Open()

	// Open listener.
	if s.https {
		cert, err := tls.LoadX509KeyPair(s.cert, s.key)
		if err != nil {
			return err
		}

		tlsConfig := s.tlsConfig.Clone()
		tlsConfig.Certificates = []tls.Certificate{cert}

		listener, err := tls.Listen("tcp", s.addr, tlsConfig)
		if err != nil {
			return err
		}

		s.ln = listener
	} else {
		listener, err := net.Listen("tcp", s.addr)
		if err != nil {
			return err
		}

		s.ln = listener
	}
	s.Logger.Info("Listening on HTTP",
		zap.Stringer("addr", s.ln.Addr()),
		zap.Bool("https", s.https))

	// Open unix socket listener.
	if s.unixSocket {
		if runtime.GOOS == "windows" {
			return fmt.Errorf("unable to use unix socket on windows")
		}
		if err := os.MkdirAll(path.Dir(s.bindSocket), 0777); err != nil {
			return err
		}
		if err := syscall.Unlink(s.bindSocket); err != nil && !os.IsNotExist(err) {
			return err
		}

		listener, err := net.Listen("unix", s.bindSocket)
		if err != nil {
			return err
		}
		if s.unixSocketPerm != 0 {
			if err := os.Chmod(s.bindSocket, os.FileMode(s.unixSocketPerm)); err != nil {
				return err
			}
		}
		if s.unixSocketGroup != 0 {
			if err := os.Chown(s.bindSocket, -1, s.unixSocketGroup); err != nil {
				return err
			}
		}

		s.Logger.Info("Listening on unix socket",
			zap.Stringer("addr", listener.Addr()))
		s.unixSocketListener = listener

		go s.serveUnixSocket()
	}

	// Enforce a connection limit if one has been given.
	if s.limit > 0 {
		s.ln = LimitListener(s.ln, s.limit)
	}

	// wait for the listeners to start
	timeout := time.Now().Add(time.Second)
	for {
		if s.ln.Addr() != nil {
			break
		}

		if time.Now().After(timeout) {
			return fmt.Errorf("unable to open without http listener running")
		}
		time.Sleep(10 * time.Millisecond)
	}

	// Begin listening for requests in a separate goroutine.
	go s.serveTCP()
	return nil
}
~~~



##### Service.serveTCP 服务http请求

~~~~go
// serveTCP serves the handler from the TCP listener.
func (s *Service) serveTCP() {
	s.serve(s.ln)
}

// serveUnixSocket serves the handler from the unix socket listener.
func (s *Service) serveUnixSocket() {
	s.serve(s.unixSocketListener)
}

// serve serves the handler from the listener.
func (s *Service) serve(listener net.Listener) {
	// The listener was closed so exit
	// See https://github.com/golang/go/issues/4373
	err := http.Serve(listener, s.Handler)
	if err != nil && !strings.Contains(err.Error(), "closed") {
		s.err <- fmt.Errorf("listener failed: addr=%s, err=%s", s.Addr(), err)
	}
}
~~~~

