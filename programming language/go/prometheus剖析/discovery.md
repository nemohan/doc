# discovery

[TOC]

discovery模块负则管理各种服务发现机制。并且监视配置发现的变更，变更后及时通知scrape做出调整

##### init

~~~go
var（	
configNames      = make(map[string]Config)
	configFieldNames = make(map[reflect.Type]string)
	configFields     []reflect.StructField

	configTypesMu sync.Mutex
	configTypes   = make(map[reflect.Type]reflect.Type)

	emptyStructType = reflect.TypeOf(struct{}{})
	configsType     = reflect.TypeOf(Configs{})
)

func init() {
	// N.B.: static_configs is the only Config type implemented by default.
	// All other types are registered at init by their implementing packages.
	elemTyp := reflect.TypeOf(&targetgroup.Group{})
    //staticConfigsKey 是字符串常量 static_configs
	registerConfig(staticConfigsKey, elemTyp, StaticConfig{})
}
~~~



##### registerConfig

~~~go
func registerConfig(yamlKey string, elemType reflect.Type, config Config) {
	name := config.Name()
    //configNames 哈希表
	if _, ok := configNames[name]; ok {
		panic(fmt.Sprintf("discovery: Config named %q is already registered", name))
	}
	configNames[name] = config

    //类型到fieldName的映射
    //configFieldPrefix是字符串常量 AUTO_DISCOVERY_
    //filedName 就是类似于AUTO_DISCOVERY_file 或 AUTO_DISCOVERY_static的值
	fieldName := configFieldPrefix + yamlKey // Field must be exported.
	configFieldNames[elemType] = fieldName

    //插入排序
    //configFields是 []reflect.StructField类型的切片
	// Insert fields in sorted order.
	i := sort.Search(len(configFields), func(k int) bool {
		return fieldName < configFields[k].Name
	})
	configFields = append(configFields, reflect.StructField{}) // Add empty field at end.
	copy(configFields[i+1:], configFields[i:])                 // Shift fields to the right.
	configFields[i] = reflect.StructField{                     // Write new field in place.
		Name: fieldName,
		Type: reflect.SliceOf(elemType),
		Tag:  reflect.StructTag(`yaml:"` + yamlKey + `,omitempty"`),
	}
}
~~~



##### RegisterConfig

每种不同的服务发现机制模块在初始化时都会调用RegisterConfig 来注册，比如kubernetes、file等

~~~go
// RegisterConfig registers the given Config type for YAML marshaling and unmarshaling.
func RegisterConfig(config Config) {
	registerConfig(config.Name()+"_sd_configs", reflect.TypeOf(config), config)
}
~~~



## file 基于文件的服务发现

~~~go
var (
	patFileSDName = regexp.MustCompile(`^[^*]*(\*[^/]*)?\.(json|yml|yaml|JSON|YML|YAML)$`)

	// DefaultSDConfig is the default file SD configuration.
	DefaultSDConfig = SDConfig{
		RefreshInterval: model.Duration(5 * time.Minute),
	}
)

func init() {
	discovery.RegisterConfig(&SDConfig{})
}

// SDConfig is the configuration for file based discovery.
type SDConfig struct {
	Files           []string       `yaml:"files"`
	RefreshInterval model.Duration `yaml:"refresh_interval,omitempty"`
}

// Name returns the name of the Config.
func (*SDConfig) Name() string { return "file" }

// NewDiscoverer returns a Discoverer for the Config.
func (c *SDConfig) NewDiscoverer(opts discovery.DiscovererOptions) (discovery.Discoverer, error) {
	return NewDiscovery(c, opts.Logger), nil
}

// SetDirectory joins any relative file paths with dir.
func (c *SDConfig) SetDirectory(dir string) {
	for i, file := range c.Files {
		c.Files[i] = config.JoinDir(dir, file)
	}
}

// UnmarshalYAML implements the yaml.Unmarshaler interface.
func (c *SDConfig) UnmarshalYAML(unmarshal func(interface{}) error) error {
	*c = DefaultSDConfig
	type plain SDConfig
	err := unmarshal((*plain)(c))
	if err != nil {
		return err
	}
	if len(c.Files) == 0 {
		return errors.New("file service discovery config must contain at least one path name")
	}
	for _, name := range c.Files {
		if !patFileSDName.MatchString(name) {
			return errors.Errorf("path name %q is not valid for file discovery", name)
		}
	}
	return nil
}

const fileSDFilepathLabel = model.MetaLabelPrefix + "filepath"

// TimestampCollector is a Custom Collector for Timestamps of the files.
type TimestampCollector struct {
	Description *prometheus.Desc
	discoverers map[*Discovery]struct{}
	lock        sync.RWMutex
}

// Describe method sends the description to the channel.
func (t *TimestampCollector) Describe(ch chan<- *prometheus.Desc) {
	ch <- t.Description
}

// Collect creates constant metrics for each file with last modified time of the file.
func (t *TimestampCollector) Collect(ch chan<- prometheus.Metric) {
	// New map to dedup filenames.
	uniqueFiles := make(map[string]float64)
	t.lock.RLock()
	for fileSD := range t.discoverers {
		fileSD.lock.RLock()
		for filename, timestamp := range fileSD.timestamps {
			uniqueFiles[filename] = timestamp
		}
		fileSD.lock.RUnlock()
	}
	t.lock.RUnlock()
	for filename, timestamp := range uniqueFiles {
		ch <- prometheus.MustNewConstMetric(
			t.Description,
			prometheus.GaugeValue,
			timestamp,
			filename,
		)
	}
}

func (t *TimestampCollector) addDiscoverer(disc *Discovery) {
	t.lock.Lock()
	t.discoverers[disc] = struct{}{}
	t.lock.Unlock()
}

func (t *TimestampCollector) removeDiscoverer(disc *Discovery) {
	t.lock.Lock()
	delete(t.discoverers, disc)
	t.lock.Unlock()
}

// NewTimestampCollector creates a TimestampCollector.
func NewTimestampCollector() *TimestampCollector {
	return &TimestampCollector{
		Description: prometheus.NewDesc(
			"prometheus_sd_file_mtime_seconds",
			"Timestamp (mtime) of files read by FileSD. Timestamp is set at read time.",
			[]string{"filename"},
			nil,
		),
		discoverers: make(map[*Discovery]struct{}),
	}
}

var (
	fileSDScanDuration = prometheus.NewSummary(
		prometheus.SummaryOpts{
			Name:       "prometheus_sd_file_scan_duration_seconds",
			Help:       "The duration of the File-SD scan in seconds.",
			Objectives: map[float64]float64{0.5: 0.05, 0.9: 0.01, 0.99: 0.001},
		})
	fileSDReadErrorsCount = prometheus.NewCounter(
		prometheus.CounterOpts{
			Name: "prometheus_sd_file_read_errors_total",
			Help: "The number of File-SD read errors.",
		})
	fileSDTimeStamp = NewTimestampCollector()
)

func init() {
	prometheus.MustRegister(fileSDScanDuration)
	prometheus.MustRegister(fileSDReadErrorsCount)
	prometheus.MustRegister(fileSDTimeStamp)
}

// Discovery provides service discovery functionality based
// on files that contain target groups in JSON or YAML format. Refreshing
// happens using file watches and periodic refreshes.
type Discovery struct {
	paths      []string
	watcher    *fsnotify.Watcher
	interval   time.Duration
	timestamps map[string]float64
	lock       sync.RWMutex

	// lastRefresh stores which files were found during the last refresh
	// and how many target groups they contained.
	// This is used to detect deleted target groups.
	lastRefresh map[string]int
	logger      log.Logger
}

// NewDiscovery returns a new file discovery for the given paths.
func NewDiscovery(conf *SDConfig, logger log.Logger) *Discovery {
	if logger == nil {
		logger = log.NewNopLogger()
	}

	disc := &Discovery{
		paths:      conf.Files,
		interval:   time.Duration(conf.RefreshInterval),
		timestamps: make(map[string]float64),
		logger:     logger,
	}
	fileSDTimeStamp.addDiscoverer(disc)
	return disc
}

// listFiles returns a list of all files that match the configured patterns.
func (d *Discovery) listFiles() []string {
	var paths []string
	for _, p := range d.paths {
		files, err := filepath.Glob(p)
		if err != nil {
			level.Error(d.logger).Log("msg", "Error expanding glob", "glob", p, "err", err)
			continue
		}
		paths = append(paths, files...)
	}
	return paths
}

// watchFiles sets watches on all full paths or directories that were configured for
// this file discovery.
func (d *Discovery) watchFiles() {
	if d.watcher == nil {
		panic("no watcher configured")
	}
	for _, p := range d.paths {
		if idx := strings.LastIndex(p, "/"); idx > -1 {
			p = p[:idx]
		} else {
			p = "./"
		}
		if err := d.watcher.Add(p); err != nil {
			level.Error(d.logger).Log("msg", "Error adding file watch", "path", p, "err", err)
		}
	}
}

// Run implements the Discoverer interface.
func (d *Discovery) Run(ctx context.Context, ch chan<- []*targetgroup.Group) {
	watcher, err := fsnotify.NewWatcher()
	if err != nil {
		level.Error(d.logger).Log("msg", "Error adding file watcher", "err", err)
		return
	}
	d.watcher = watcher
	defer d.stop()

	d.refresh(ctx, ch)

	ticker := time.NewTicker(d.interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return

		case event := <-d.watcher.Events:
			// fsnotify sometimes sends a bunch of events without name or operation.
			// It's unclear what they are and why they are sent - filter them out.
			if len(event.Name) == 0 {
				break
			}
			// Everything but a chmod requires rereading.
			if event.Op^fsnotify.Chmod == 0 {
				break
			}
			// Changes to a file can spawn various sequences of events with
			// different combinations of operations. For all practical purposes
			// this is inaccurate.
			// The most reliable solution is to reload everything if anything happens.
			d.refresh(ctx, ch)

		case <-ticker.C:
			// Setting a new watch after an update might fail. Make sure we don't lose
			// those files forever.
			d.refresh(ctx, ch)

		case err := <-d.watcher.Errors:
			if err != nil {
				level.Error(d.logger).Log("msg", "Error watching file", "err", err)
			}
		}
	}
}

func (d *Discovery) writeTimestamp(filename string, timestamp float64) {
	d.lock.Lock()
	d.timestamps[filename] = timestamp
	d.lock.Unlock()
}

func (d *Discovery) deleteTimestamp(filename string) {
	d.lock.Lock()
	delete(d.timestamps, filename)
	d.lock.Unlock()
}

// stop shuts down the file watcher.
func (d *Discovery) stop() {
	level.Debug(d.logger).Log("msg", "Stopping file discovery...", "paths", fmt.Sprintf("%v", d.paths))

	done := make(chan struct{})
	defer close(done)

	fileSDTimeStamp.removeDiscoverer(d)

	// Closing the watcher will deadlock unless all events and errors are drained.
	go func() {
		for {
			select {
			case <-d.watcher.Errors:
			case <-d.watcher.Events:
				// Drain all events and errors.
			case <-done:
				return
			}
		}
	}()
	if err := d.watcher.Close(); err != nil {
		level.Error(d.logger).Log("msg", "Error closing file watcher", "paths", fmt.Sprintf("%v", d.paths), "err", err)
	}

	level.Debug(d.logger).Log("msg", "File discovery stopped")
}

// refresh reads all files matching the discovery's patterns and sends the respective
// updated target groups through the channel.
func (d *Discovery) refresh(ctx context.Context, ch chan<- []*targetgroup.Group) {
	t0 := time.Now()
	defer func() {
		fileSDScanDuration.Observe(time.Since(t0).Seconds())
	}()
	ref := map[string]int{}
	for _, p := range d.listFiles() {
		tgroups, err := d.readFile(p)
		if err != nil {
			fileSDReadErrorsCount.Inc()

			level.Error(d.logger).Log("msg", "Error reading file", "path", p, "err", err)
			// Prevent deletion down below.
			ref[p] = d.lastRefresh[p]
			continue
		}
		select {
		case ch <- tgroups:
		case <-ctx.Done():
			return
		}

		ref[p] = len(tgroups)
	}
	// Send empty updates for sources that disappeared.
	for f, n := range d.lastRefresh {
		m, ok := ref[f]
		if !ok || n > m {
			level.Debug(d.logger).Log("msg", "file_sd refresh found file that should be removed", "file", f)
			d.deleteTimestamp(f)
			for i := m; i < n; i++ {
				select {
				case ch <- []*targetgroup.Group{{Source: fileSource(f, i)}}:
				case <-ctx.Done():
					return
				}
			}
		}
	}
	d.lastRefresh = ref

	d.watchFiles()
}

// readFile reads a JSON or YAML list of targets groups from the file, depending on its
// file extension. It returns full configuration target groups.
func (d *Discovery) readFile(filename string) ([]*targetgroup.Group, error) {
	fd, err := os.Open(filename)
	if err != nil {
		return nil, err
	}
	defer fd.Close()

	content, err := ioutil.ReadAll(fd)
	if err != nil {
		return nil, err
	}

	info, err := fd.Stat()
	if err != nil {
		return nil, err
	}

	var targetGroups []*targetgroup.Group

	switch ext := filepath.Ext(filename); strings.ToLower(ext) {
	case ".json":
		if err := json.Unmarshal(content, &targetGroups); err != nil {
			return nil, err
		}
	case ".yml", ".yaml":
		if err := yaml.UnmarshalStrict(content, &targetGroups); err != nil {
			return nil, err
		}
	default:
		panic(errors.Errorf("discovery.File.readFile: unhandled file extension %q", ext))
	}

	for i, tg := range targetGroups {
		if tg == nil {
			err = errors.New("nil target group item found")
			return nil, err
		}

		tg.Source = fileSource(filename, i)
		if tg.Labels == nil {
			tg.Labels = model.LabelSet{}
		}
		tg.Labels[fileSDFilepathLabel] = model.LabelValue(filename)
	}

	d.writeTimestamp(filename, float64(info.ModTime().Unix()))

	return targetGroups, nil
}

// fileSource returns a source ID for the i-th target group in the file.
func fileSource(filename string, i int) string {
	return fmt.Sprintf("%s:%d", filename, i)
}
~~~



## static config 基于静态配置的服务发现



~~~go
// A StaticConfig is a Config that provides a static list of targets.
type StaticConfig []*targetgroup.Group

// Name returns the name of the service discovery mechanism.
func (StaticConfig) Name() string { return "static" }

// NewDiscoverer returns a Discoverer for the Config.
func (c StaticConfig) NewDiscoverer(DiscovererOptions) (Discoverer, error) {
	return staticDiscoverer(c), nil
}

type staticDiscoverer []*targetgroup.Group

func (c staticDiscoverer) Run(ctx context.Context, up chan<- []*targetgroup.Group) {
	// TODO: existing implementation closes up chan, but documentation explicitly forbids it...?
	defer close(up)
	select {
	case <-ctx.Done():
	case up <- c:
	}
}
~~~



## Config 接口

~~~go
// A Config provides the configuration and constructor for a Discoverer.
type Config interface {
	// Name returns the name of the discovery mechanism.
	Name() string

	// NewDiscoverer returns a Discoverer for the Config
	// with the given DiscovererOptions.
	NewDiscoverer(DiscovererOptions) (Discoverer, error)
}

// Configs is a slice of Config values that uses custom YAML marshaling and unmarshaling
// to represent itself as a mapping of the Config values grouped by their types.
type Configs []Config
~~~



## Manager



##### Manager的定义

~~~go
// Manager maintains a set of discovery providers and sends each update to a map channel.
// Targets are grouped by the target set name.
type Manager struct {
	logger         log.Logger
	name           string
	mtx            sync.RWMutex
	ctx            context.Context
	discoverCancel []context.CancelFunc

	// Some Discoverers(eg. k8s) send only the updates for a given target group
	// so we use map[tg.Source]*targetgroup.Group to know which group to update.
	targets map[poolKey]map[string]*targetgroup.Group
	// providers keeps track of SD providers.
	providers []*provider
	// The sync channel sends the updates as a map where the key is the job value from the scrape config.
	syncCh chan map[string][]*targetgroup.Group

	// How long to wait before sending updates to the channel. The variable
	// should only be modified in unit tests.
	updatert time.Duration

	// The triggerSend channel signals to the manager that new updates have been received from providers.
	triggerSend chan struct{}
}

// provider holds a Discoverer instance, its configuration and its subscribers.
type provider struct {
	name   string
	d      Discoverer //接口类型 定义Run方法
	subs   []string
	config interface{}
}
~~~



##### NewManager

~~~go
// NewManager is the Discovery Manager constructor.
func NewManager(ctx context.Context, logger log.Logger, options ...func(*Manager)) *Manager {
	if logger == nil {
		logger = log.NewNopLogger()
	}
	mgr := &Manager{
		logger:         logger,
		syncCh:         make(chan map[string][]*targetgroup.Group),
		targets:        make(map[poolKey]map[string]*targetgroup.Group),
		discoverCancel: []context.CancelFunc{},
		ctx:            ctx,
		updatert:       5 * time.Second,
		triggerSend:    make(chan struct{}, 1),
	}
	for _, option := range options {
		option(mgr)
	}
	return mgr
}
~~~





##### Manager.Run

~~~go
// Run starts the background processing
func (m *Manager) Run() error {
	go m.sender()
	for range m.ctx.Done() {
		m.cancelDiscoverers()
		return m.ctx.Err()
	}
	return nil
}
~~~



##### Manager.sender 通知scrape manager

~~~go
func (m *Manager) sender() {
    //每5秒触发一次
	ticker := time.NewTicker(m.updatert)
	defer ticker.Stop()

	for {
		select {
		case <-m.ctx.Done():
			return
		case <-ticker.C: // Some discoverers send updates too often so we throttle these with the ticker.
			select {
                //接收到服务发现机制有更新
			case <-m.triggerSend:
				sentUpdates.WithLabelValues(m.name).Inc()
				select {
				case m.syncCh <- m.allGroups():
				default:
					delayedUpdates.WithLabelValues(m.name).Inc()
					level.Debug(m.logger).Log("msg", "Discovery receiver's channel was full so will retry the next cycle")
					select {
					case m.triggerSend <- struct{}{}:
					default:
					}
				}
			default:
			}
		}
	}
}
~~~



##### Manager.ApplyConfig 启动加载配置时调用此函数

参数: 

* cfg map[string]Configs, key 是配置文件指定的job name，value 是Configs，对应服务发现的配置

~~~go
// ApplyConfig removes all running discovery providers and starts new ones using the provided config.
func (m *Manager) ApplyConfig(cfg map[string]Configs) error {
	m.mtx.Lock()
	defer m.mtx.Unlock()

	for pk := range m.targets {
		if _, ok := cfg[pk.setName]; !ok {
			discoveredTargets.DeleteLabelValues(m.name, pk.setName)
		}
	}
    /*
    poolKey的定义
type poolKey struct {
	setName  string
	provider string
}
    */
	m.cancelDiscoverers()
	m.targets = make(map[poolKey]map[string]*targetgroup.Group)
	m.providers = nil
	m.discoverCancel = nil

    //name 是jobName
	failedCount := 0
	for name, scfg := range cfg {
		failedCount += m.registerProviders(scfg, name)
		discoveredTargets.WithLabelValues(m.name, name).Set(0)
	}
	failedConfigs.WithLabelValues(m.name).Set(float64(failedCount))

	for _, prov := range m.providers {
		m.startProvider(m.ctx, prov)
	}

	return nil
}

~~~



##### Manager.startProvider  启动各个服务发现机制

* 调用p.d.Run启动服务发现机制
* 调用m.updater监视服务发现机制的变更

~~~go
func (m *Manager) startProvider(ctx context.Context, p *provider) {
	level.Debug(m.logger).Log("msg", "Starting provider", "provider", p.name, "subs", fmt.Sprintf("%v", p.subs))
	ctx, cancel := context.WithCancel(ctx)
	updates := make(chan []*targetgroup.Group)

	m.discoverCancel = append(m.discoverCancel, cancel)

	go p.d.Run(ctx, updates)
	go m.updater(ctx, p, updates)
}
~~~



##### Manager.updater 监视服务发现机制的变更

* 等待updates channel 的消息
* m.triggerSend 通知Manager.Run

~~~go
func (m *Manager) updater(ctx context.Context, p *provider, updates chan []*targetgroup.Group) {
	for {
		select {
		case <-ctx.Done():
			return
            //收到变更通知
		case tgs, ok := <-updates:
			receivedUpdates.WithLabelValues(m.name).Inc()
			if !ok {
				level.Debug(m.logger).Log("msg", "Discoverer channel closed", "provider", p.name)
				return
			}

			for _, s := range p.subs {
				m.updateGroup(poolKey{setName: s, provider: p.name}, tgs)
			}

			select {
			case m.triggerSend <- struct{}{}:
			default:
			}
		}
	}
}
~~~



##### Manager.updateGroup

~~~go
func (m *Manager) updateGroup(poolKey poolKey, tgs []*targetgroup.Group) {
	m.mtx.Lock()
	defer m.mtx.Unlock()

	if _, ok := m.targets[poolKey]; !ok {
		m.targets[poolKey] = make(map[string]*targetgroup.Group)
	}
	for _, tg := range tgs {
		if tg != nil { // Some Discoverers send nil target group so need to check for it to avoid panics.
			m.targets[poolKey][tg.Source] = tg
		}
	}
}
~~~



##### Manager.registerProviders 注册服务发现机制

参数:

* setName 是job name
* 

~~~go
// registerProviders returns a number of failed SD config.
func (m *Manager) registerProviders(cfgs Configs, setName string) int {
	var (
		failed int
		added  bool
	)
	add := func(cfg Config) {
		for _, p := range m.providers {
			if reflect.DeepEqual(cfg, p.config) {
				p.subs = append(p.subs, setName)
				added = true
				return
			}
		}
		typ := cfg.Name()
		d, err := cfg.NewDiscoverer(DiscovererOptions{
			Logger: log.With(m.logger, "discovery", typ),
		})
		if err != nil {
			level.Error(m.logger).Log("msg", "Cannot create service discovery", "err", err, "type", typ)
			failed++
			return
		}
        //static/0
        //
		m.providers = append(m.providers, &provider{
			name:   fmt.Sprintf("%s/%d", typ, len(m.providers)),
			d:      d,
			config: cfg,
			subs:   []string{setName},
		})
		added = true
	}//end func
    
	for _, cfg := range cfgs {
		add(cfg)
	}
	if !added {
		// Add an empty target group to force the refresh of the corresponding
		// scrape pool and to notify the receiver that this target set has no
		// current targets.
		// It can happen because the combined set of SD configurations is empty
		// or because we fail to instantiate all the SD configurations.
		add(StaticConfig{{}})
	}
	return failed
}
~~~

