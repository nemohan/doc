# Handler

[TOC]

### 总结



### Throttler 并发写限制器

定义在handler.go

##### Throttler的定义

Throttler主要的成员变量：

* current 控制并发写的带缓冲的channel
* 

~~~go
// Throttler represents an HTTP throttler that limits the number of concurrent
// requests being processed as well as the number of enqueued requests.
type Throttler struct {
	current  chan struct{} //
	enqueued chan struct{}

	// Maximum amount of time requests can wait in queue.
	// Must be set before adding middleware.
	EnqueueTimeout time.Duration

	Logger *zap.Logger
}

// NewThrottler returns a new instance of Throttler that limits to concurrentN.
// requests processed at a time and maxEnqueueN requests waiting to be processed.
func NewThrottler(concurrentN, maxEnqueueN int) *Throttler {
	return &Throttler{
		current:  make(chan struct{}, concurrentN),
		enqueued: make(chan struct{}, concurrentN+maxEnqueueN),
		Logger:   zap.NewNop(),
	}
}
~~~



##### Throttler.Handler 限制写并发

存在以下两种情况：

1 t.enqueued未满，t.current未满。占用t.enqueued中的一个token，也占用t.current中的一个token。请求处理完毕后，先释放t.current的token，再释放t.enqueued的token

2 t.enqueued未满，t.current满。等待其他请求处理完毕，释放t.current中的token；或者等待超时丢弃本次写请求，然后释放t.enqueued中的token

3 t.enqueued满(t.curent必满，t.current满后才会导致t.enqueued满)。丢弃本次写请求



~~~go


// Handler wraps h in a middleware handler that throttles requests.
func (t *Throttler) Handler(h http.Handler) http.Handler {
	timeout := t.EnqueueTimeout

	// Return original handler if concurrent requests is zero.
	if cap(t.current) == 0 {
		return h
	}

	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Start a timer to limit enqueued request times.
		var timerCh <-chan time.Time
		if timeout > 0 {
			timer := time.NewTimer(timeout)
			defer timer.Stop()
			timerCh = timer.C
		}

        //若enqueued未满，则写入成功。
		// Wait for a spot in the queue.
		if cap(t.enqueued) > cap(t.current) {
			select {
                //未满，写入成功
			case t.enqueued <- struct{}{}:
				defer func() { <-t.enqueued }()
			default:
				t.Logger.Warn("request throttled, queue full", zap.Duration("d", timeout))
				http.Error(w, "request throttled, queue full", http.StatusServiceUnavailable)
				return
			}
		}

		// First check if we can immediately send in to current because there is
		// available capacity. This helps reduce racyness in tests.
		select {
		case t.current <- struct{}{}:
		default:
			// Wait for a spot in the list of concurrent requests, but allow checking the timeout.
			select {
			case t.current <- struct{}{}:
			case <-timerCh:
				t.Logger.Warn("request throttled, exceeds timeout", zap.Duration("d", timeout))
				http.Error(w, "request throttled, exceeds timeout", http.StatusServiceUnavailable)
				return
			}
		}
        //请求处理完毕，释放一个token
		defer func() { <-t.current }()

		// Execute request.
		h.ServeHTTP(w, r)
	})
}

~~~



### Handler



#### Handler的定义

Handler的部分成员由cmd/influxd/run/Server.appendHTTPDService 初始化

~~~go
// Handler represents an HTTP handler for the InfluxDB server.
type Handler struct {
	mux       *pat.PatternServeMux
	Version   string
	BuildType string

	MetaClient interface {
		Database(name string) *meta.DatabaseInfo
		Databases() []meta.DatabaseInfo
		Authenticate(username, password string) (ui meta.User, err error)
		User(username string) (meta.User, error)
		AdminUserExists() bool
	}

	QueryAuthorizer interface {
		AuthorizeQuery(u meta.User, query *influxql.Query, database string) error
	}

	WriteAuthorizer interface {
		AuthorizeWrite(username, database string) error
	}

	QueryExecutor *query.Executor

	Monitor interface {
		Statistics(tags map[string]string) ([]*monitor.Statistic, error)
		Diagnostics() (map[string]*diagnostics.Diagnostics, error)
	}

	PointsWriter interface {
		WritePoints(database, retentionPolicy string, consistencyLevel models.ConsistencyLevel, user meta.User, points []models.Point) error
	}

	Store Store

	// Flux services
	Controller       Controller
	CompilerMappings flux.CompilerMappings
	registered       bool

	Config           *Config
	Logger           *zap.Logger
	CLFLogger        *log.Logger
	accessLog        *os.File		//访问日志
	accessLogFilters StatusFilters
	stats            *Statistics  //维护统计信息

	requestTracker *RequestTracker
	writeThrottler *Throttler   //限制写并发
}
~~~



##### NewHandler

~~~go
// NewHandler returns a new instance of handler with routes.
func NewHandler(c Config) *Handler {
	h := &Handler{
		mux:            pat.New(),
		Config:         &c,
		Logger:         zap.NewNop(),
		CLFLogger:      log.New(os.Stderr, "[httpd] ", 0),
		stats:          &Statistics{},
		requestTracker: NewRequestTracker(),
	}

	// Limit the number of concurrent & enqueued write requests.
	h.writeThrottler = NewThrottler(c.MaxConcurrentWriteLimit, c.MaxEnqueuedWriteLimit)
	h.writeThrottler.EnqueueTimeout = c.EnqueuedWriteTimeout

	// Disable the write log if they have been suppressed.
	writeLogEnabled := c.LogEnabled
	if c.SuppressWriteLog {
		writeLogEnabled = false
	}

	var authWrapper func(handler func(http.ResponseWriter, *http.Request)) interface{}
	if h.Config.AuthEnabled && h.Config.PingAuthEnabled {
		authWrapper = func(handler func(http.ResponseWriter, *http.Request)) interface{} {
			return func(w http.ResponseWriter, r *http.Request, user meta.User) {
				handler(w, r)
			}
		}
	} else {
		authWrapper = func(handler func(http.ResponseWriter, *http.Request)) interface{} {
			return handler
		}
	}

	h.AddRoutes([]Route{
		Route{
			"query-options", // Satisfy CORS checks.
			"OPTIONS", "/query", false, true, h.serveOptions,
		},
		Route{
			"query", // Query serving route.
			"GET", "/query", true, true, h.serveQuery,
		},
		Route{
			"query", // Query serving route.
			"POST", "/query", true, true, h.serveQuery,
		},
		Route{
			"write-options", // Satisfy CORS checks.
			"OPTIONS", "/write", false, true, h.serveOptions,
		},
		Route{
			"write", // Data-ingest route.
			"POST", "/write", true, writeLogEnabled, h.serveWriteV1,
		},
		Route{
			"write", // Data-ingest route.
			"POST", "/api/v2/write", true, writeLogEnabled, h.serveWriteV2,
		},
		Route{
			"prometheus-write", // Prometheus remote write
			"POST", "/api/v1/prom/write", false, true, h.servePromWrite,
		},
		Route{
			"prometheus-read", // Prometheus remote read
			"POST", "/api/v1/prom/read", true, true, h.servePromRead,
		},
		Route{ // Ping
			"ping",
			"GET", "/ping", false, true, authWrapper(h.servePing),
		},
		Route{ // Ping
			"ping-head",
			"HEAD", "/ping", false, true, authWrapper(h.servePing),
		},
		Route{ // Ping w/ status
			"status",
			"GET", "/status", false, true, authWrapper(h.serveStatus),
		},
		Route{ // Ping w/ status
			"status-head",
			"HEAD", "/status", false, true, authWrapper(h.serveStatus),
		},
		Route{ // Ping
			"ping",
			"GET", "/health", false, true, authWrapper(h.serveHealth),
		},
		Route{
			"prometheus-metrics",
			"GET", "/metrics", false, true, authWrapper(promhttp.Handler().ServeHTTP),
		},
	}...)

	// When PprofAuthEnabled is enabled, create debug/pprof endpoints with the
	// same authentication handlers as other endpoints.
	if h.Config.AuthEnabled && h.Config.PprofEnabled && h.Config.PprofAuthEnabled {
		authWrapper = func(handler func(http.ResponseWriter, *http.Request)) interface{} {
			return func(w http.ResponseWriter, r *http.Request, user meta.User) {
				if user == nil || !user.AuthorizeUnrestricted() {
					h.Logger.Info("Unauthorized request", zap.String("user", user.ID()), zap.String("path", r.URL.Path))
					h.httpError(w, "error authorizing admin access", http.StatusForbidden)
					return
				}
				handler(w, r)
			}
		}
		h.AddRoutes([]Route{
			Route{
				"pprof-cmdline",
				"GET", "/debug/pprof/cmdline", true, true, authWrapper(httppprof.Cmdline),
			},
			Route{
				"pprof-profile",
				"GET", "/debug/pprof/profile", true, true, authWrapper(httppprof.Profile),
			},
			Route{
				"pprof-symbol",
				"GET", "/debug/pprof/symbol", true, true, authWrapper(httppprof.Symbol),
			},
			Route{
				"pprof-all",
				"GET", "/debug/pprof/all", true, true, authWrapper(h.archiveProfilesAndQueries),
			},
			Route{
				"debug-expvar",
				"GET", "/debug/vars", true, true, authWrapper(h.serveExpvar),
			},
			Route{
				"debug-requests",
				"GET", "/debug/requests", true, true, authWrapper(h.serveDebugRequests),
			},
		}...)
	}

	fluxRoute := Route{
		"flux-read",
		"POST", "/api/v2/query", true, true, nil,
	}

	if !c.FluxEnabled {
		fluxRoute.HandlerFunc = func(w http.ResponseWriter, r *http.Request) {
			http.Error(w, "Flux query service disabled. Verify flux-enabled=true in the [http] section of the InfluxDB config.", http.StatusForbidden)
		}
	} else {
		fluxRoute.HandlerFunc = h.serveFluxQuery
	}
	h.AddRoutes(fluxRoute)

	return h
}

~~~



##### Handler.Open

* 若开启了访问日志选项，则打开日志文件

~~~go
func (h *Handler) Open() {
	if h.Config.LogEnabled {
		path := "stderr"

		if h.Config.AccessLogPath != "" {
			f, err := os.OpenFile(h.Config.AccessLogPath, os.O_WRONLY|os.O_APPEND|os.O_CREATE, 0666)
			if err != nil {
				h.Logger.Error("unable to open access log, falling back to stderr", zap.Error(err), zap.String("path", h.Config.AccessLogPath))
				return
			}
			h.CLFLogger = log.New(f, "", 0) // [httpd] prefix stripped when logging to a file
			h.accessLog = f
			path = h.Config.AccessLogPath
		}
		h.Logger.Info("opened HTTP access log", zap.String("path", path))
	}
	h.accessLogFilters = StatusFilters(h.Config.AccessLogStatusFilters)

	if h.Config.AuthEnabled && h.Config.SharedSecret == "" {
		h.Logger.Info("Auth is enabled but shared-secret is blank. BearerAuthentication is disabled.")
	}

	if h.Config.FluxEnabled {
		h.registered = true
		prom.MustRegister(h.Controller.PrometheusCollectors()...)
	}
}
~~~



##### Handler.ServeHTTP 处理http请求

* 增加统计信息

~~~go
// ServeHTTP responds to HTTP request to the handler.
func (h *Handler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	atomic.AddInt64(&h.stats.Requests, 1)
	atomic.AddInt64(&h.stats.ActiveRequests, 1)
	defer atomic.AddInt64(&h.stats.ActiveRequests, -1)
	start := time.Now()

	// Add version and build header to all InfluxDB requests.
	w.Header().Add("X-Influxdb-Version", h.Version)
	w.Header().Add("X-Influxdb-Build", h.BuildType)

	// Maintain backwards compatibility by using unwrapped pprof/debug handlers
	// when PprofAuthEnabled is false.
	if h.Config.AuthEnabled && h.Config.PprofEnabled && h.Config.PprofAuthEnabled {
		h.mux.ServeHTTP(w, r)
	} else if strings.HasPrefix(r.URL.Path, "/debug/pprof") && h.Config.PprofEnabled {
		h.handleProfiles(w, r)
	} else if strings.HasPrefix(r.URL.Path, "/debug/vars") {
		h.serveExpvar(w, r)
	} else if strings.HasPrefix(r.URL.Path, "/debug/requests") {
		h.serveDebugRequests(w, r)
	} else {
		h.mux.ServeHTTP(w, r)
	}

	atomic.AddInt64(&h.stats.RequestDuration, time.Since(start).Nanoseconds())
}
~~~



##### Handler.AddRoutes 添加路由

对每个路由添加一些封装层(wrapper)

需要认证的情况，请求需要经过的封装层（由内到外）：

* authenticate
* 若是写数据的请求，需要经过Throttler.Handler
* Handler.responseWriter
* gzipFilter(可选) 实现响应内容压缩
* Handler.SetHeaderHandler
* cors  跨域检查
* requestID 生成请求id
* Handler.Logging 记录日志
* Handler.recovery

不需要认证的情况：

- 若是写数据的请求，需要经过Throttler.Handler
- Handler.responseWriter
- gzipFilter(可选)
- Handler.SetHeaderHandler
- cors
- requestID
- Handler.Logging
- Handler.recovery

~~~go
// AddRoutes sets the provided routes on the handler.
func (h *Handler) AddRoutes(routes ...Route) {
	for _, r := range routes {
		var handler http.Handler

		// If it's a handler func that requires authorization, wrap it in authentication
		if hf, ok := r.HandlerFunc.(func(http.ResponseWriter, *http.Request, meta.User)); ok {
			handler = authenticate(hf, h, h.Config.AuthEnabled)
		}

		// This is a normal handler signature and does not require authentication
		if hf, ok := r.HandlerFunc.(func(http.ResponseWriter, *http.Request)); ok {
            //类型转换
			handler = http.HandlerFunc(hf)
		}

		// Throttle route if this is a write endpoint.
		if r.Method == http.MethodPost {
			switch r.Pattern {
			case "/write", "/api/v1/prom/write":
				handler = h.writeThrottler.Handler(handler)
			default:
			}
		}

		handler = h.responseWriter(handler)
		if r.Gzipped {
			handler = gzipFilter(handler)
		}

		handler = h.SetHeadersHandler(handler)
		handler = cors(handler)
		handler = requestID(handler)
		if h.Config.LogEnabled && r.LoggingEnabled {
			handler = h.logging(handler, r.Name)
		}
		handler = h.recovery(handler, r.Name) // make sure recovery is always last

		h.mux.Add(r.Method, r.Pattern, handler)
	}
}
~~~



##### authenticate 检查用户认证

* 根据参数requireAuthentication检查是否需要认证，若不需要直接调用innter
* 若需要认证，则调用parseCredentials。获取用户名密码或bearer token

~~~go
// authenticate wraps a handler and ensures that if user credentials are passed in
// an attempt is made to authenticate that user. If authentication fails, an error is returned.
//
// There is one exception: if there are no users in the system, authentication is not required. This
// is to facilitate bootstrapping of a system with authentication enabled.
func authenticate(inner func(http.ResponseWriter, *http.Request, meta.User), h *Handler, requireAuthentication bool) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Return early if we are not authenticating
		if !requireAuthentication {
			inner(w, r, nil)
			return
		}
		var user meta.User

		// TODO corylanou: never allow this in the future without users
		if requireAuthentication && h.MetaClient.AdminUserExists() {
			creds, err := parseCredentials(r)
			if err != nil {
				atomic.AddInt64(&h.stats.AuthenticationFailures, 1)
				h.httpError(w, err.Error(), http.StatusUnauthorized)
				return
			}

			switch creds.Method {
			case UserAuthentication:
				if creds.Username == "" {
					atomic.AddInt64(&h.stats.AuthenticationFailures, 1)
					h.httpError(w, "username required", http.StatusUnauthorized)
					return
				}

				user, err = h.MetaClient.Authenticate(creds.Username, creds.Password)
				if err != nil {
					atomic.AddInt64(&h.stats.AuthenticationFailures, 1)
					h.httpError(w, "authorization failed", http.StatusUnauthorized)
					return
				}
			case BearerAuthentication:
				if h.Config.SharedSecret == "" {
					atomic.AddInt64(&h.stats.AuthenticationFailures, 1)
					h.httpError(w, "bearer auth disabled", http.StatusUnauthorized)
					return
				}
				keyLookupFn := func(token *jwt.Token) (interface{}, error) {
					// Check for expected signing method.
					if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
						return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
					}
					return []byte(h.Config.SharedSecret), nil
				}

				// Parse and validate the token.
				token, err := jwt.Parse(creds.Token, keyLookupFn)
				if err != nil {
					h.httpError(w, err.Error(), http.StatusUnauthorized)
					return
				} else if !token.Valid {
					h.httpError(w, "invalid token", http.StatusUnauthorized)
					return
				}

				claims, ok := token.Claims.(jwt.MapClaims)
				if !ok {
					h.httpError(w, "problem authenticating token", http.StatusInternalServerError)
					h.Logger.Info("Could not assert JWT token claims as jwt.MapClaims")
					return
				}

				// Make sure an expiration was set on the token.
				if exp, ok := claims["exp"].(float64); !ok || exp <= 0.0 {
					h.httpError(w, "token expiration required", http.StatusUnauthorized)
					return
				}

				// Get the username from the token.
				username, ok := claims["username"].(string)
				if !ok {
					h.httpError(w, "username in token must be a string", http.StatusUnauthorized)
					return
				} else if username == "" {
					h.httpError(w, "token must contain a username", http.StatusUnauthorized)
					return
				}

				// Lookup user in the metastore.
				if user, err = h.MetaClient.User(username); err != nil {
					h.httpError(w, err.Error(), http.StatusUnauthorized)
					return
				} else if user == nil {
					h.httpError(w, meta.ErrUserNotFound.Error(), http.StatusUnauthorized)
					return
				}
			default:
				h.httpError(w, "unsupported authentication", http.StatusUnauthorized)
			}

		}
		inner(w, r, user)
	})
}
~~~



##### 2 Handler.responseWriter 处理ResponseWriter

~~~go
func (h *Handler) responseWriter(inner http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w = NewResponseWriter(w, r)
		inner.ServeHTTP(w, r)
	})
}
~~~

##### 3 Handler.SetHeadersHandler 添加从配置文件获取的额外的http头部

~~~go
func (h *Handler) SetHeadersHandler(handler http.Handler) http.Handler {
	return http.HandlerFunc(h.SetHeadersWrapper(handler.ServeHTTP))
}

// wrapper that adds user supplied headers to the response.
func (h *Handler) SetHeadersWrapper(f func(http.ResponseWriter, *http.Request)) func(http.ResponseWriter, *http.Request) {
	if len(h.Config.HTTPHeaders) == 0 {
		return f
	}

	return func(w http.ResponseWriter, r *http.Request) {
		for header, value := range h.Config.HTTPHeaders {
			w.Header().Add(header, value)
		}
		f(w, r)
	}
}
~~~



##### 4 cors 跨域请求

~~~go
// cors responds to incoming requests and adds the appropriate cors headers
// TODO: corylanou: add the ability to configure this in our config
func cors(inner http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if origin := r.Header.Get("Origin"); origin != "" {
			w.Header().Set(`Access-Control-Allow-Origin`, origin)
			w.Header().Set(`Access-Control-Allow-Methods`, strings.Join([]string{
				`DELETE`,
				`GET`,
				`OPTIONS`,
				`POST`,
				`PUT`,
			}, ", "))

			w.Header().Set(`Access-Control-Allow-Headers`, strings.Join([]string{
				`Accept`,
				`Accept-Encoding`,
				`Authorization`,
				`Content-Length`,
				`Content-Type`,
				`X-CSRF-Token`,
				`X-HTTP-Method-Override`,
			}, ", "))

			w.Header().Set(`Access-Control-Expose-Headers`, strings.Join([]string{
				`Date`,
				`X-InfluxDB-Version`,
				`X-InfluxDB-Build`,
			}, ", "))
		}

		if r.Method == "OPTIONS" {
			return
		}

		inner.ServeHTTP(w, r)
	})
}
~~~



##### 3 requestID 生成标识请求的uuid

在请求和响应都加上Request-Id头部

~~~go
func requestID(inner http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// X-Request-Id takes priority.
		rid := r.Header.Get("X-Request-Id")

		// If X-Request-Id is empty, then check Request-Id
		if rid == "" {
			rid = r.Header.Get("Request-Id")
		}

		// If Request-Id is empty then generate a v1 UUID.
		if rid == "" {
			rid = uuid.TimeUUID().String()
		}

		// We read Request-Id in other handler code so we'll use that naming
		// convention from this point in the request cycle.
		r.Header.Set("Request-Id", rid)

		// Set the request ID on the response headers.
		// X-Request-Id is the most common name for a request ID header.
		w.Header().Set("X-Request-Id", rid)

		// We will also set Request-Id for backwards compatibility with previous
		// versions of InfluxDB.
		w.Header().Set("Request-Id", rid)

		inner.ServeHTTP(w, r)
	})
}
~~~



##### 2 Handler.logging 输出日志

* 根据状态码输出日志

~~~go
func (h *Handler) logging(inner http.Handler, name string) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		l := &responseLogger{w: w}
		inner.ServeHTTP(l, r)

        //accessLogFilters.Match检查状态码是否匹配，若匹配则记录日志
		if h.accessLogFilters.Match(l.Status()) {
			h.CLFLogger.Println(buildLogLine(l, r, start))
		}

		// Log server errors.
		if l.Status()/100 == 5 {
			errStr := l.Header().Get("X-InfluxDB-Error")
			if errStr != "" {
				h.Logger.Error(fmt.Sprintf("[%d] - %q", l.Status(), errStr))
			}
		}
	})
}
~~~



##### 1 Handler.recovery 最外层, 捕获panic

~~~go
func (h *Handler) recovery(inner http.Handler, name string) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		l := &responseLogger{w: w}

		defer func() {
			if err := recover(); err != nil {
				logLine := buildLogLine(l, r, start)
				logLine = fmt.Sprintf("%s [panic:%s] %s", logLine, err, debug.Stack())
				h.CLFLogger.Println(logLine)
				http.Error(w, http.StatusText(http.StatusInternalServerError), 500)
				atomic.AddInt64(&h.stats.RecoveredPanics, 1) // Capture the panic in _internal stats.

				if willCrash {
					h.CLFLogger.Println("\n\n=====\nAll goroutines now follow:")
					buf := debug.Stack()
					h.CLFLogger.Printf("%s\n", buf)
					os.Exit(1) // If we panic then the Go server will recover.
				}
			}
		}()

		inner.ServeHTTP(l, r)
	})
}
~~~



#### 

~~~go
// serveDebugRequests will track requests for a period of time.
func (h *Handler) serveDebugRequests(w http.ResponseWriter, r *http.Request) {
	var d time.Duration
	if s := r.URL.Query().Get("seconds"); s == "" {
		d = DefaultDebugRequestsInterval
	} else if seconds, err := strconv.ParseInt(s, 10, 64); err != nil {
		h.httpError(w, err.Error(), http.StatusBadRequest)
		return
	} else {
		d = time.Duration(seconds) * time.Second
		if d > MaxDebugRequestsInterval {
			h.httpError(w, fmt.Sprintf("exceeded maximum interval time: %s > %s",
				influxql.FormatDuration(d),
				influxql.FormatDuration(MaxDebugRequestsInterval)),
				http.StatusBadRequest)
			return
		}
	}

	var closing <-chan bool
	if notifier, ok := w.(http.CloseNotifier); ok {
		closing = notifier.CloseNotify()
	}

	profile := h.requestTracker.TrackRequests()

	timer := time.NewTimer(d)
	select {
	case <-timer.C:
		profile.Stop()
	case <-closing:
		// Connection was closed early.
		profile.Stop()
		timer.Stop()
		return
	}

	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Header().Add("Connection", "close")

	fmt.Fprintln(w, "{")
	first := true
	for req, st := range profile.Requests {
		val, err := json.Marshal(st)
		if err != nil {
			continue
		}

		if !first {	
			fmt.Fprintln(w, ",")
		}
		first = false
		fmt.Fprintf(w, "%q: ", req.String())
		w.Write(bytes.TrimSpace(val))
	}
	fmt.Fprintln(w, "\n}")
}
~~~



##### Handler.serveDebugRequests 跟踪一段时间内的请求

注意http.CloseNotifier的使用，新版本的go已经抛弃http.CloseNotifier，转而使用http.Request.Context

~~~go
// serveDebugRequests will track requests for a period of time.
func (h *Handler) serveDebugRequests(w http.ResponseWriter, r *http.Request) {
	var d time.Duration
	if s := r.URL.Query().Get("seconds"); s == "" {
		d = DefaultDebugRequestsInterval
	} else if seconds, err := strconv.ParseInt(s, 10, 64); err != nil {
		h.httpError(w, err.Error(), http.StatusBadRequest)
		return
	} else {
		d = time.Duration(seconds) * time.Second
		if d > MaxDebugRequestsInterval {
			h.httpError(w, fmt.Sprintf("exceeded maximum interval time: %s > %s",
				influxql.FormatDuration(d),
				influxql.FormatDuration(MaxDebugRequestsInterval)),
				http.StatusBadRequest)
			return
		}
	}

	var closing <-chan bool
	if notifier, ok := w.(http.CloseNotifier); ok {
		closing = notifier.CloseNotify()
	}

	profile := h.requestTracker.TrackRequests()

	timer := time.NewTimer(d)
	select {
	case <-timer.C:
		profile.Stop()
	case <-closing:
		// Connection was closed early.
		profile.Stop()
		timer.Stop()
		return
	}

	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Header().Add("Connection", "close")

	fmt.Fprintln(w, "{")
	first := true
	for req, st := range profile.Requests {
		val, err := json.Marshal(st)
		if err != nil {
			continue
		}

		if !first {
			fmt.Fprintln(w, ",")
		}
		first = false
		fmt.Fprintf(w, "%q: ", req.String())
		w.Write(bytes.TrimSpace(val))
	}
	fmt.Fprintln(w, "\n}")
}

~~~



### 查询

##### Handler.serveQuery

~~~go
// serveQuery parses an incoming query and, if valid, executes the query.
func (h *Handler) serveQuery(w http.ResponseWriter, r *http.Request, user meta.User) {
	atomic.AddInt64(&h.stats.QueryRequests, 1)
	defer func(start time.Time) {
		atomic.AddInt64(&h.stats.QueryRequestDuration, time.Since(start).Nanoseconds())
	}(time.Now())
	h.requestTracker.Add(r, user)

	// Retrieve the underlying ResponseWriter or initialize our own.
	rw, ok := w.(ResponseWriter)
	if !ok {
		rw = NewResponseWriter(w, r)
	}

	// Retrieve the node id the query should be executed on.
	nodeID, _ := strconv.ParseUint(r.FormValue("node_id"), 10, 64)

	var qr io.Reader
	// Attempt to read the form value from the "q" form value.
	if qp := strings.TrimSpace(r.FormValue("q")); qp != "" {
		qr = strings.NewReader(qp)
	} else if r.MultipartForm != nil && r.MultipartForm.File != nil {
		// If we have a multipart/form-data, try to retrieve a file from 'q'.
		if fhs := r.MultipartForm.File["q"]; len(fhs) > 0 {
			f, err := fhs[0].Open()
			if err != nil {
				h.httpError(rw, err.Error(), http.StatusBadRequest)
				return
			}
			defer f.Close()
			qr = f
		}
	}

	if qr == nil {
		h.httpError(rw, `missing required parameter "q"`, http.StatusBadRequest)
		return
	}

	epoch := strings.TrimSpace(r.FormValue("epoch"))

	p := influxql.NewParser(qr)
	db := r.FormValue("db")

	// Sanitize the request query params so it doesn't show up in the response logger.
	// Do this before anything else so a parsing error doesn't leak passwords.
	sanitize(r)

	// Parse the parameters
	rawParams := r.FormValue("params")
	if rawParams != "" {
		var params map[string]interface{}
		decoder := json.NewDecoder(strings.NewReader(rawParams))
		decoder.UseNumber()
		if err := decoder.Decode(&params); err != nil {
			h.httpError(rw, "error parsing query parameters: "+err.Error(), http.StatusBadRequest)
			return
		}

		// Convert json.Number into int64 and float64 values
		for k, v := range params {
			if v, ok := v.(json.Number); ok {
				var err error
				if strings.Contains(string(v), ".") {
					params[k], err = v.Float64()
				} else {
					params[k], err = v.Int64()
				}

				if err != nil {
					h.httpError(rw, "error parsing json value: "+err.Error(), http.StatusBadRequest)
					return
				}
			}
		}
		p.SetParams(params)
	}

	// Parse query from query string.
	q, err := p.ParseQuery()
	if err != nil {
		h.httpError(rw, "error parsing query: "+err.Error(), http.StatusBadRequest)
		return
	}

	// Check authorization.
	if h.Config.AuthEnabled {
		if err := h.QueryAuthorizer.AuthorizeQuery(user, q, db); err != nil {
			if err, ok := err.(meta.ErrAuthorize); ok {
				h.Logger.Info("Unauthorized request",
					zap.String("user", err.User),
					zap.Stringer("query", err.Query),
					logger.Database(err.Database))
			}
			h.httpError(rw, "error authorizing query: "+err.Error(), http.StatusForbidden)
			return
		}
	}

	// Parse chunk size. Use default if not provided or unparsable.
	chunked := r.FormValue("chunked") == "true"
	chunkSize := DefaultChunkSize
	if chunked {
		if n, err := strconv.ParseInt(r.FormValue("chunk_size"), 10, 64); err == nil && int(n) > 0 {
			chunkSize = int(n)
		}
	}

	// Parse whether this is an async command.
	async := r.FormValue("async") == "true"

	opts := query.ExecutionOptions{
		Database:        db,
		RetentionPolicy: r.FormValue("rp"),
		ChunkSize:       chunkSize,
		ReadOnly:        r.Method == "GET",
		NodeID:          nodeID,
	}

	if h.Config.AuthEnabled {
		// The current user determines the authorized actions.
		opts.Authorizer = user
	} else {
		// Auth is disabled, so allow everything.
		opts.Authorizer = query.OpenAuthorizer
	}

	// Make sure if the client disconnects we signal the query to abort
	var closing chan struct{}
	if !async {
		closing = make(chan struct{})
		if notifier, ok := w.(http.CloseNotifier); ok {
			// CloseNotify() is not guaranteed to send a notification when the query
			// is closed. Use this channel to signal that the query is finished to
			// prevent lingering goroutines that may be stuck.
			done := make(chan struct{})
			defer close(done)

			notify := notifier.CloseNotify()
			go func() {
				// Wait for either the request to finish
				// or for the client to disconnect
				select {
				case <-done:
				case <-notify:
					close(closing)
				}
			}()
			opts.AbortCh = done
		} else {
			defer close(closing)
		}
	}

	// Execute query.
	results := h.QueryExecutor.ExecuteQuery(q, opts, closing)

	// If we are running in async mode, open a goroutine to drain the results
	// and return with a StatusNoContent.
	if async {
		go h.async(q, results)
		h.writeHeader(w, http.StatusNoContent)
		return
	}

	// if we're not chunking, this will be the in memory buffer for all results before sending to client
	resp := Response{Results: make([]*query.Result, 0)}

	// Status header is OK once this point is reached.
	// Attempt to flush the header immediately so the client gets the header information
	// and knows the query was accepted.
	h.writeHeader(rw, http.StatusOK)
	if w, ok := w.(http.Flusher); ok {
		w.Flush()
	}

	// pull all results from the channel
	rows := 0
	for r := range results {
		// Ignore nil results.
		if r == nil {
			continue
		}

		// if requested, convert result timestamps to epoch
		if epoch != "" {
			convertToEpoch(r, epoch)
		}

		// Write out result immediately if chunked.
		if chunked {
			n, _ := rw.WriteResponse(Response{
				Results: []*query.Result{r},
			})
			atomic.AddInt64(&h.stats.QueryRequestBytesTransmitted, int64(n))
			w.(http.Flusher).Flush()
			continue
		}

		// Limit the number of rows that can be returned in a non-chunked
		// response.  This is to prevent the server from going OOM when
		// returning a large response.  If you want to return more than the
		// default chunk size, then use chunking to process multiple blobs.
		// Iterate through the series in this result to count the rows and
		// truncate any rows we shouldn't return.
		if h.Config.MaxRowLimit > 0 {
			for i, series := range r.Series {
				n := h.Config.MaxRowLimit - rows
				if n < len(series.Values) {
					// We have reached the maximum number of values. Truncate
					// the values within this row.
					series.Values = series.Values[:n]
					// Since this was truncated, it will always be a partial return.
					// Add this so the client knows we truncated the response.
					series.Partial = true
				}
				rows += len(series.Values)

				if rows >= h.Config.MaxRowLimit {
					// Drop any remaining series since we have already reached the row limit.
					if i < len(r.Series) {
						r.Series = r.Series[:i+1]
					}
					break
				}
			}
		}

		// It's not chunked so buffer results in memory.
		// Results for statements need to be combined together.
		// We need to check if this new result is for the same statement as
		// the last result, or for the next statement
		l := len(resp.Results)
		if l == 0 {
			resp.Results = append(resp.Results, r)
		} else if resp.Results[l-1].StatementID == r.StatementID {
			if r.Err != nil {
				resp.Results[l-1] = r
				continue
			}

			cr := resp.Results[l-1]
			rowsMerged := 0
			if len(cr.Series) > 0 {
				lastSeries := cr.Series[len(cr.Series)-1]

				for _, row := range r.Series {
					if !lastSeries.SameSeries(row) {
						// Next row is for a different series than last.
						break
					}
					// Values are for the same series, so append them.
					lastSeries.Values = append(lastSeries.Values, row.Values...)
					lastSeries.Partial = row.Partial
					rowsMerged++
				}
			}

			// Append remaining rows as new rows.
			r.Series = r.Series[rowsMerged:]
			cr.Series = append(cr.Series, r.Series...)
			cr.Messages = append(cr.Messages, r.Messages...)
			cr.Partial = r.Partial
		} else {
			resp.Results = append(resp.Results, r)
		}

		// Drop out of this loop and do not process further results when we hit the row limit.
		if h.Config.MaxRowLimit > 0 && rows >= h.Config.MaxRowLimit {
			// If the result is marked as partial, remove that partial marking
			// here. While the series is partial and we would normally have
			// tried to return the rest in the next chunk, we are not using
			// chunking and are truncating the series so we don't want to
			// signal to the client that we plan on sending another JSON blob
			// with another result.  The series, on the other hand, still
			// returns partial true if it was truncated or had more data to
			// send in a future chunk.
			r.Partial = false
			break
		}
	}

	// If it's not chunked we buffered everything in memory, so write it out
	if !chunked {
		n, _ := rw.WriteResponse(resp)
		atomic.AddInt64(&h.stats.QueryRequestBytesTransmitted, int64(n))
	}
}
~~~



#### 写数据

##### Handler.serveWriteV2

* 确定时间精度
* 

~~~go
// serveWriteV2 maps v2 write parameters to a v1 style handler.  the concepts
// of an "org" and "bucket" are mapped to v1 "database" and "retention
// policies".
func (h *Handler) serveWriteV2(w http.ResponseWriter, r *http.Request, user meta.User) {
	precision := r.URL.Query().Get("precision")
	switch precision {
	case "ns":
		precision = "n"
	case "us":
		precision = "u"
	case "ms", "s", "":
		// same as v1 so do nothing
	default:
		err := fmt.Sprintf("invalid precision %q (use ns, us, ms or s)", precision)
		h.httpError(w, err, http.StatusBadRequest)
	}

	db, rp, err := bucket2dbrp(r.URL.Query().Get("bucket"))
	if err != nil {
		h.httpError(w, err.Error(), http.StatusNotFound)
		return
	}
	h.serveWrite(db, rp, precision, w, r, user)
}

// serveWriteV1 handles v1 style writes.
func (h *Handler) serveWriteV1(w http.ResponseWriter, r *http.Request, user meta.User) {
	precision := r.URL.Query().Get("precision")
	switch precision {
	case "", "n", "ns", "u", "ms", "s", "m", "h":
		// it's valid
	default:
		err := fmt.Sprintf("invalid precision %q (use n, u, ms, s, m or h)", precision)
		h.httpError(w, err, http.StatusBadRequest)
	}

	db := r.URL.Query().Get("db")
	rp := r.URL.Query().Get("rp")

	h.serveWrite(db, rp, precision, w, r, user)
}


~~~



##### Handler.serveWrite

PointsWriter 被初始化为coordinator.PointsWriter

* 调整统计信息， 写次数、当前正在写次数(stats.ActiveWriteRequests)
* 检查数据库
* 检查认证信息
* 调用model.ParsePointsWithPrecision解析数据

~~~go
// serveWrite receives incoming series data in line protocol format and writes
// it to the database.
func (h *Handler) serveWrite(database, retentionPolicy, precision string, w http.ResponseWriter, r *http.Request, user meta.User) {
    
    //调整统计信息
	atomic.AddInt64(&h.stats.WriteRequests, 1)
	atomic.AddInt64(&h.stats.ActiveWriteRequests, 1)
	defer func(start time.Time) {
		atomic.AddInt64(&h.stats.ActiveWriteRequests, -1)
		atomic.AddInt64(&h.stats.WriteRequestDuration, time.Since(start).Nanoseconds())
	}(time.Now())
    
    //
	h.requestTracker.Add(r, user)

    //未指定数据库
	if database == "" {
		h.httpError(w, "database is required", http.StatusBadRequest)
		return
	}

    //从元数据获取数据库信息
	if di := h.MetaClient.Database(database); di == nil {
		h.httpError(w, fmt.Sprintf("database not found: %q", database), http.StatusNotFound)
		return
	}

    //认证
	if h.Config.AuthEnabled {
		if user == nil {
			h.httpError(w, fmt.Sprintf("user is required to write to database %q", database), http.StatusForbidden)
			return
		}

		if err := h.WriteAuthorizer.AuthorizeWrite(user.ID(), database); err != nil {
			h.httpError(w, fmt.Sprintf("%q user is not authorized to write to database %q", user.ID(), database), http.StatusForbidden)
			return
		}
	}

    //设置每次读取的大小
	body := r.Body
	if h.Config.MaxBodySize > 0 {
		body = truncateReader(body, int64(h.Config.MaxBodySize))
	}

	// Handle gzip decoding of the body
	if r.Header.Get("Content-Encoding") == "gzip" {
		b, err := gzip.NewReader(r.Body)
		if err != nil {
			h.httpError(w, err.Error(), http.StatusBadRequest)
			return
		}
		defer b.Close()
		body = b
	}

	var bs []byte
	if r.ContentLength > 0 {
        //消息体长度超过配置文件指定的限制
		if h.Config.MaxBodySize > 0 && r.ContentLength > int64(h.Config.MaxBodySize) {
			h.httpError(w, http.StatusText(http.StatusRequestEntityTooLarge), http.StatusRequestEntityTooLarge)
			return
		}

		// This will just be an initial hint for the gzip reader, as the
		// bytes.Buffer will grow as needed when ReadFrom is called
		bs = make([]byte, 0, r.ContentLength)
	}
    
    
	buf := bytes.NewBuffer(bs)

	_, err := buf.ReadFrom(body)
	if err != nil {
		if err == errTruncated {
			h.httpError(w, http.StatusText(http.StatusRequestEntityTooLarge), http.StatusRequestEntityTooLarge)
			return
		}

		if h.Config.WriteTracing {
			h.Logger.Info("Write handler unable to read bytes from request body")
		}
		h.httpError(w, err.Error(), http.StatusBadRequest)
		return
	}
	atomic.AddInt64(&h.stats.WriteRequestBytesReceived, int64(buf.Len()))

	if h.Config.WriteTracing {
		h.Logger.Info("Write body received by handler", zap.ByteString("body", buf.Bytes()))
	}

    //解析数据
	points, parseError := models.ParsePointsWithPrecision(buf.Bytes(), time.Now().UTC(), precision)
	// Not points parsed correctly so return the error now
	if parseError != nil && len(points) == 0 {
		if parseError.Error() == "EOF" {
			h.writeHeader(w, http.StatusOK)
			return
		}
		h.httpError(w, parseError.Error(), http.StatusBadRequest)
		return
	}

	// Determine required consistency level.
	level := r.URL.Query().Get("consistency")
	consistency := models.ConsistencyLevelOne
	if level != "" {
		var err error
		consistency, err = models.ParseConsistencyLevel(level)
		if err != nil {
			h.httpError(w, err.Error(), http.StatusBadRequest)
			return
		}
	}

	type pointsWriterWithContext interface {
		WritePointsWithContext(context.Context, string, string, models.ConsistencyLevel, meta.User, []models.Point) error
	}

    //PointsWriter 被初始化为coordinator.PointsWriter
	writePoints := func() error {
		switch pw := h.PointsWriter.(type) {
		case pointsWriterWithContext:
			var npoints, nvalues int64
			ctx := context.WithValue(context.Background(), coordinator.StatPointsWritten, &npoints)
			ctx = context.WithValue(ctx, coordinator.StatValuesWritten, &nvalues)

			// for now, just store the number of values used.
			err := pw.WritePointsWithContext(ctx, database, retentionPolicy, consistency, user, points)
			atomic.AddInt64(&h.stats.ValuesWrittenOK, nvalues)
			if err != nil {
				return err
			}
			return nil
		default:
			return h.PointsWriter.WritePoints(database, retentionPolicy, consistency, user, points)
		}
	}

	// Write points.
	if err := writePoints(); influxdb.IsClientError(err) {
		atomic.AddInt64(&h.stats.PointsWrittenFail, int64(len(points)))
		h.httpError(w, err.Error(), http.StatusBadRequest)
		return
	} else if influxdb.IsAuthorizationError(err) {
		atomic.AddInt64(&h.stats.PointsWrittenFail, int64(len(points)))
		h.httpError(w, err.Error(), http.StatusForbidden)
		return
	} else if werr, ok := err.(tsdb.PartialWriteError); ok {
		atomic.AddInt64(&h.stats.PointsWrittenOK, int64(len(points)-werr.Dropped))
		atomic.AddInt64(&h.stats.PointsWrittenDropped, int64(werr.Dropped))
		h.httpError(w, werr.Error(), http.StatusBadRequest)
		return
	} else if err != nil {
		atomic.AddInt64(&h.stats.PointsWrittenFail, int64(len(points)))
		h.httpError(w, err.Error(), http.StatusInternalServerError)
		return
	} else if parseError != nil {
		// We wrote some of the points
		atomic.AddInt64(&h.stats.PointsWrittenOK, int64(len(points)))
		// The other points failed to parse which means the client sent invalid line protocol.  We return a 400
		// response code as well as the lines that failed to parse.
		h.httpError(w, tsdb.PartialWriteError{Reason: parseError.Error()}.Error(), http.StatusBadRequest)
		return
	}

	atomic.AddInt64(&h.stats.PointsWrittenOK, int64(len(points)))
	h.writeHeader(w, http.StatusNoContent)
}
~~~



### ResponseWriter

##### NewResponseWriter

~~~go
// NewResponseWriter creates a new ResponseWriter based on the Accept header
// in the request that wraps the ResponseWriter.
func NewResponseWriter(w http.ResponseWriter, r *http.Request) ResponseWriter {
	pretty := r.URL.Query().Get("pretty") == "true"
	rw := &responseWriter{ResponseWriter: w}

	acceptHeaders := parseAccept(r.Header["Accept"])
	for _, accept := range acceptHeaders {
		for _, ct := range contentTypes {
			if match(accept, ct) {
				w.Header().Add("Content-Type", ct.full)
				rw.formatter = ct.formatter(pretty)
				return rw
			}
		}
	}
	w.Header().Add("Content-Type", defaultContentType.full)
	rw.formatter = defaultContentType.formatter(pretty)
	return rw
}
~~~



### truncateReader

~~~go
var (
	errTruncated = errors.New("Read: truncated")
)

// truncateReader returns a Reader that reads from r
// but stops with ErrTruncated after n bytes.
func truncateReader(r io.Reader, n int64) io.ReadCloser {
	tr := &truncatedReader{r: &io.LimitedReader{R: r, N: n + 1}}

	if rc, ok := r.(io.Closer); ok {
		tr.Closer = rc
	}

	return tr
}

// A truncatedReader limits the amount of data returned to a maximum of r.N bytes.
type truncatedReader struct {
	r *io.LimitedReader
	io.Closer
}
//若消息体超过N, 则r.r.N 就满足 r.r.N <= 0
func (r *truncatedReader) Read(p []byte) (n int, err error) {
	n, err = r.r.Read(p)
	if r.r.N <= 0 {
		return n, errTruncated
	}

	return n, err
}

func (r *truncatedReader) Close() error {
	if r.Closer != nil {
		return r.Closer.Close()
	}
	return nil
}
~~~

