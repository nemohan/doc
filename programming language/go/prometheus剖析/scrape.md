# scape

[TOC]

scrape 根据服务发现机制获取的数据采集代理，以pull的方式从这些代理获取数据

## Manager



##### Manager的定义

~~~go
// Manager maintains a set of scrape pools and manages start/stop cycles
// when receiving new target groups form the discovery manager.
type Manager struct {
	logger    log.Logger
	append    storage.Appendable
	graceShut chan struct{}

	jitterSeed    uint64     // Global jitterSeed seed is used to spread scrape workload across HA setup.
	mtxScrape     sync.Mutex // Guards the fields below.
	scrapeConfigs map[string]*config.ScrapeConfig
	scrapePools   map[string]*scrapePool
	targetSets    map[string][]*targetgroup.Group

	triggerReload chan struct{}
}
~~~



##### NewManager

参数：

* app 被初始化为storage.NewFanout

~~~go
// NewManager is the Manager constructor
func NewManager(logger log.Logger, app storage.Appendable) *Manager {
	if logger == nil {
		logger = log.NewNopLogger()
	}
	m := &Manager{
		append:        app,
		logger:        logger,
		scrapeConfigs: make(map[string]*config.ScrapeConfig),
		scrapePools:   make(map[string]*scrapePool),
		graceShut:     make(chan struct{}),
		triggerReload: make(chan struct{}, 1),
	}
	targetMetadataCache.registerManager(m)

	return m
}
~~~



##### Manager.ApplyConfig 启动时加载配置调用此函数

~~~go
// ApplyConfig resets the manager's target providers and job configurations as defined by the new cfg.
func (m *Manager) ApplyConfig(cfg *config.Config) error {
	m.mtxScrape.Lock()
	defer m.mtxScrape.Unlock()

	c := make(map[string]*config.ScrapeConfig)
	for _, scfg := range cfg.ScrapeConfigs {
		c[scfg.JobName] = scfg
	}
	m.scrapeConfigs = c

	if err := m.setJitterSeed(cfg.GlobalConfig.ExternalLabels); err != nil {
		return err
	}

    //scrapePools 什么时候被设置
	// Cleanup and reload pool if the configuration has changed.
	var failed bool
	for name, sp := range m.scrapePools {
		if cfg, ok := m.scrapeConfigs[name]; !ok {
			sp.stop()
			delete(m.scrapePools, name)
		} else if !reflect.DeepEqual(sp.config, cfg) {
			err := sp.reload(cfg)
			if err != nil {
				level.Error(m.logger).Log("msg", "error reloading scrape pool", "err", err, "scrape_pool", name)
				failed = true
			}
		}
	}

	if failed {
		return errors.New("failed to apply the new configuration")
	}
	return nil
}
~~~



##### Manager.Run 等待服务发现机制的通知

* 启动Manager.reloader

* 每当服务发现机制发现的targes有变动，就通过channel m.triggerReload 触发manager.reloader执行

~~~go
// Run receives and saves target set updates and triggers the scraping loops reloading.
// Reloading happens in the background so that it doesn't block receiving targets updates.
func (m *Manager) Run(tsets <-chan map[string][]*targetgroup.Group) error {
	go m.reloader()
	for {
		select {
            //服务发现机制发过来的配置变更
		case ts := <-tsets:
            //设置 m.targetSets
			m.updateTsets(ts)

            //触发Manager.reloader执行
			select {
			case m.triggerReload <- struct{}{}:
			default:
			}

		case <-m.graceShut:
			return nil
		}
	}
}
~~~



##### Manager.reloader

* 每5秒执行一次
* 若收到关闭信号则退出。若收到定时器信号(ticker.C)则继续等待m.triggerReload信号或关闭信号

~~~go
func (m *Manager) reloader() {
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-m.graceShut:
			return
		case <-ticker.C:
			select {
			case <-m.triggerReload:
				m.reload()
			case <-m.graceShut:
				return
			}
		}
	}
}
~~~



##### Manager.reload 重新加载targets

* 为target 创建scrapePool

~~~go
func (m *Manager) reload() {
	m.mtxScrape.Lock()
	var wg sync.WaitGroup
    //setName的值是啥  jobName
	for setName, groups := range m.targetSets {
		if _, ok := m.scrapePools[setName]; !ok {
			scrapeConfig, ok := m.scrapeConfigs[setName]
			if !ok {
				level.Error(m.logger).Log("msg", "error reloading target set", "err", "invalid config id:"+setName)
				continue
			}
			sp, err := newScrapePool(scrapeConfig, m.append, m.jitterSeed, log.With(m.logger, "scrape_pool", setName))
			if err != nil {
				level.Error(m.logger).Log("msg", "error creating new scrape pool", "err", err, "scrape_pool", setName)
				continue
			}
			m.scrapePools[setName] = sp
		}

		wg.Add(1)
		// Run the sync in parallel as these take a while and at high load can't catch up.
		go func(sp *scrapePool, groups []*targetgroup.Group) {
			sp.Sync(groups)
			wg.Done()
		}(m.scrapePools[setName], groups)

	}
	m.mtxScrape.Unlock()
	wg.Wait()
}
~~~



##### appender

~~~go
// appender returns an appender for ingested samples from the target.
func appender(app storage.Appender, limit int) storage.Appender {
	app = &timeLimitAppender{
		Appender: app,
		maxTime:  timestamp.FromTime(time.Now().Add(maxAheadTime)),
	}

	// The limit is applied after metrics are potentially dropped via relabeling.
	if limit > 0 {
		app = &limitAppender{
			Appender: app,
			limit:    limit,
		}
	}
	return app
}
~~~



## scrapePool

~~~go
// scrapePool manages scrapes for sets of targets.
type scrapePool struct {
	appendable storage.Appendable
	logger     log.Logger
	cancel     context.CancelFunc

	// mtx must not be taken after targetMtx.
	mtx            sync.Mutex
	config         *config.ScrapeConfig
	client         *http.Client
	loops          map[uint64]loop
	targetLimitHit bool // Internal state to speed up the target_limit checks.

	targetMtx sync.Mutex
	// activeTargets and loops must always be synchronized to have the same
	// set of hashes.
	activeTargets  map[uint64]*Target
	droppedTargets []*Target

	// Constructor for new scrape loops. This is settable for testing convenience.
	newLoop func(scrapeLoopOptions) loop
}
~~~



##### newScrapePool

* 调用conifg_util.NewClientFromConfig 创建client

~~~go
func newScrapePool(cfg *config.ScrapeConfig, app storage.Appendable, jitterSeed uint64, logger log.Logger) (*scrapePool, error) {
	targetScrapePools.Inc()
	if logger == nil {
		logger = log.NewNopLogger()
	}

	client, err := config_util.NewClientFromConfig(cfg.HTTPClientConfig, cfg.JobName, false, false)
	if err != nil {
		targetScrapePoolsFailed.Inc()
		return nil, errors.Wrap(err, "error creating HTTP client")
	}

	buffers := pool.New(1e3, 100e6, 3, func(sz int) interface{} { return make([]byte, 0, sz) })

	ctx, cancel := context.WithCancel(context.Background())
	sp := &scrapePool{
		cancel:        cancel,
		appendable:    app,
		config:        cfg,
		client:        client,
		activeTargets: map[uint64]*Target{},
		loops:         map[uint64]loop{},
		logger:        logger,
	}
	sp.newLoop = func(opts scrapeLoopOptions) loop {
		// Update the targets retrieval function for metadata to a new scrape cache.
		cache := opts.cache
		if cache == nil {
			cache = newScrapeCache()
		}
		opts.target.SetMetadataStore(cache)

		return newScrapeLoop(
			ctx,
			opts.scraper,
			log.With(logger, "target", opts.target),
			buffers,
			func(l labels.Labels) labels.Labels {
				return mutateSampleLabels(l, opts.target, opts.honorLabels, opts.mrc)
			},
			func(l labels.Labels) labels.Labels { return mutateReportSampleLabels(l, opts.target) },
			func(ctx context.Context) storage.Appender { return appender(app.Appender(ctx), opts.limit) },
			cache,
			jitterSeed,
			opts.honorTimestamps,
		)
	}

	return sp, nil
}
~~~



##### scrapePool.reload

~~~go
// reload the scrape pool with the given scrape configuration. The target state is preserved
// but all scrape loops are restarted with the new scrape configuration.
// This method returns after all scrape loops that were stopped have stopped scraping.
func (sp *scrapePool) reload(cfg *config.ScrapeConfig) error {
	sp.mtx.Lock()
	defer sp.mtx.Unlock()
	targetScrapePoolReloads.Inc()
	start := time.Now()

	client, err := config_util.NewClientFromConfig(cfg.HTTPClientConfig, cfg.JobName, false, false)
	if err != nil {
		targetScrapePoolReloadsFailed.Inc()
		return errors.Wrap(err, "error creating HTTP client")
	}

	reuseCache := reusableCache(sp.config, cfg)
	sp.config = cfg
	oldClient := sp.client
	sp.client = client

	targetScrapePoolTargetLimit.WithLabelValues(sp.config.JobName).Set(float64(sp.config.TargetLimit))

	var (
		wg              sync.WaitGroup
		interval        = time.Duration(sp.config.ScrapeInterval)
		timeout         = time.Duration(sp.config.ScrapeTimeout)
		limit           = int(sp.config.SampleLimit)
		honorLabels     = sp.config.HonorLabels
		honorTimestamps = sp.config.HonorTimestamps
		mrc             = sp.config.MetricRelabelConfigs
	)

	sp.targetMtx.Lock()

	forcedErr := sp.refreshTargetLimitErr()
	for fp, oldLoop := range sp.loops {
		var cache *scrapeCache
		if oc := oldLoop.getCache(); reuseCache && oc != nil {
			oldLoop.disableEndOfRunStalenessMarkers()
			cache = oc
		} else {
			cache = newScrapeCache()
		}
		var (
			t       = sp.activeTargets[fp]
			s       = &targetScraper{Target: t, client: sp.client, timeout: timeout}
			newLoop = sp.newLoop(scrapeLoopOptions{
				target:          t,
				scraper:         s,
				limit:           limit,
				honorLabels:     honorLabels,
				honorTimestamps: honorTimestamps,
				mrc:             mrc,
				cache:           cache,
			})
		)
		wg.Add(1)

		go func(oldLoop, newLoop loop) {
			oldLoop.stop()
			wg.Done()

			newLoop.setForcedError(forcedErr)
			newLoop.run(interval, timeout, nil)
		}(oldLoop, newLoop)

		sp.loops[fp] = newLoop
	}

	sp.targetMtx.Unlock()

	wg.Wait()
	oldClient.CloseIdleConnections()
	targetReloadIntervalLength.WithLabelValues(interval.String()).Observe(
		time.Since(start).Seconds(),
	)
	return nil
}
~~~



##### scrapePool.Sync

~~~go

// Sync converts target groups into actual scrape targets and synchronizes
// the currently running scraper with the resulting set and returns all scraped and dropped targets.
func (sp *scrapePool) Sync(tgs []*targetgroup.Group) {
	sp.mtx.Lock()
	defer sp.mtx.Unlock()
	start := time.Now()

	sp.targetMtx.Lock()
	var all []*Target
	sp.droppedTargets = []*Target{}
	for _, tg := range tgs {
		targets, err := targetsFromGroup(tg, sp.config)
		if err != nil {
			level.Error(sp.logger).Log("msg", "creating targets failed", "err", err)
			continue
		}
		for _, t := range targets {
			if t.Labels().Len() > 0 {
				all = append(all, t)
			} else if t.DiscoveredLabels().Len() > 0 {
				sp.droppedTargets = append(sp.droppedTargets, t)
			}
		}
	}
	sp.targetMtx.Unlock()
	sp.sync(all)

	targetSyncIntervalLength.WithLabelValues(sp.config.JobName).Observe(
		time.Since(start).Seconds(),
	)
	targetScrapePoolSyncsCounter.WithLabelValues(sp.config.JobName).Inc()
}
~~~



##### scrapePool.sync 开启定时抓取的协程

~~~go
// sync takes a list of potentially duplicated targets, deduplicates them, starts
// scrape loops for new targets, and stops scrape loops for disappeared targets.
// It returns after all stopped scrape loops terminated.
func (sp *scrapePool) sync(targets []*Target) {
	var (
		uniqueLoops     = make(map[uint64]loop)
		interval        = time.Duration(sp.config.ScrapeInterval)
		timeout         = time.Duration(sp.config.ScrapeTimeout)
		limit           = int(sp.config.SampleLimit)
		honorLabels     = sp.config.HonorLabels
		honorTimestamps = sp.config.HonorTimestamps
		mrc             = sp.config.MetricRelabelConfigs
	)

   	//为target创建scrapeLoop
	sp.targetMtx.Lock()
	for _, t := range targets {
		hash := t.hash()

		if _, ok := sp.activeTargets[hash]; !ok {
			s := &targetScraper{Target: t, client: sp.client, timeout: timeout}
			l := sp.newLoop(scrapeLoopOptions{
				target:          t,
				scraper:         s,
				limit:           limit,
				honorLabels:     honorLabels,
				honorTimestamps: honorTimestamps,
				mrc:             mrc,
			})

			sp.activeTargets[hash] = t
			sp.loops[hash] = l

			uniqueLoops[hash] = l
		} else {
			// This might be a duplicated target.
			if _, ok := uniqueLoops[hash]; !ok {
				uniqueLoops[hash] = nil
			}
			// Need to keep the most updated labels information
			// for displaying it in the Service Discovery web page.
			sp.activeTargets[hash].SetDiscoveredLabels(t.DiscoveredLabels())
		}
	}

	var wg sync.WaitGroup

    //停止和移除旧的
	// Stop and remove old targets and scraper loops.
	for hash := range sp.activeTargets {
		if _, ok := uniqueLoops[hash]; !ok {
			wg.Add(1)
			go func(l loop) {
				l.stop()
				wg.Done()
			}(sp.loops[hash])

			delete(sp.loops, hash)
			delete(sp.activeTargets, hash)
		}
	}

	sp.targetMtx.Unlock()

	targetScrapePoolTargetsAdded.WithLabelValues(sp.config.JobName).Set(float64(len(uniqueLoops)))
	forcedErr := sp.refreshTargetLimitErr()
	for _, l := range sp.loops {
		l.setForcedError(forcedErr)
	}
	for _, l := range uniqueLoops {
		if l != nil {
			go l.run(interval, timeout, nil)
		}
	}
	// Wait for all potentially stopped scrapers to terminate.
	// This covers the case of flapping targets. If the server is under high load, a new scraper
	// may be active and tries to insert. The old scraper that didn't terminate yet could still
	// be inserting a previous sample set.
	wg.Wait()
}
~~~



### scrapeLoop

~~~go
type scrapeLoop struct {
	scraper         scraper
	l               log.Logger
	cache           *scrapeCache
	lastScrapeSize  int
	buffers         *pool.Pool
	jitterSeed      uint64
	honorTimestamps bool
	forcedErr       error
	forcedErrMtx    sync.Mutex

	appender            func(ctx context.Context) storage.Appender
	sampleMutator       labelsMutator
	reportSampleMutator labelsMutator

	parentCtx context.Context
	ctx       context.Context
	cancel    func()
	stopped   chan struct{}

	disabledEndOfRunStalenessMarkers bool
}
~~~



##### newScrapeLoop

~~~go
func newScrapeLoop(ctx context.Context,
	sc scraper,
	l log.Logger,
	buffers *pool.Pool,
	sampleMutator labelsMutator,
	reportSampleMutator labelsMutator,
	appender func(ctx context.Context) storage.Appender,
	cache *scrapeCache,
	jitterSeed uint64,
	honorTimestamps bool,
) *scrapeLoop {
	if l == nil {
		l = log.NewNopLogger()
	}
	if buffers == nil {
		buffers = pool.New(1e3, 1e6, 3, func(sz int) interface{} { return make([]byte, 0, sz) })
	}
	if cache == nil {
		cache = newScrapeCache()
	}
	sl := &scrapeLoop{
		scraper:             sc,
		buffers:             buffers,
		cache:               cache,
		appender:            appender,
		sampleMutator:       sampleMutator,
		reportSampleMutator: reportSampleMutator,
		stopped:             make(chan struct{}),
		jitterSeed:          jitterSeed,
		l:                   l,
		parentCtx:           ctx,
		honorTimestamps:     honorTimestamps,
	}
	sl.ctx, sl.cancel = context.WithCancel(ctx)

	return sl
}

~~~



##### scrapeLoop.run  定时抓取数据的协程

* 调用scrapeLoop.scrapeAndReport 抓取数据

~~~go

func (sl *scrapeLoop) run(interval, timeout time.Duration, errc chan<- error) {
    //等待一段时间再开始
	select {
	case <-time.After(sl.scraper.offset(interval, sl.jitterSeed)):
		// Continue after a scraping offset.
	case <-sl.ctx.Done():
		close(sl.stopped)
		return
	}

	var last time.Time

	alignedScrapeTime := time.Now()
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

mainLoop:
	for {
		select {
		case <-sl.parentCtx.Done():
			close(sl.stopped)
			return
		case <-sl.ctx.Done():
			break mainLoop
		default:
		}

		// Temporary workaround for a jitter in go timers that causes disk space
		// increase in TSDB.
		// See https://github.com/prometheus/prometheus/issues/7846
        //总体上不太明白
		scrapeTime := time.Now()
        //scrapeTimestampTolearance 的值是2毫秒, AlignScrapeTimestamps 是true
        //抓取间隔超过200毫秒
		if AlignScrapeTimestamps && interval > 100*scrapeTimestampTolerance {
			// For some reason, a tick might have been skipped, in which case we
			// would call alignedScrapeTime.Add(interval) multiple times.
			for scrapeTime.Sub(alignedScrapeTime) >= interval {
				alignedScrapeTime = alignedScrapeTime.Add(interval)
			}
			// Align the scrape time if we are in the tolerance boundaries.
			if scrapeTime.Sub(alignedScrapeTime) <= scrapeTimestampTolerance {
				scrapeTime = alignedScrapeTime
			}
		}

		last = sl.scrapeAndReport(interval, timeout, last, scrapeTime, errc)

		select {
		case <-sl.parentCtx.Done():
			close(sl.stopped)
			return
		case <-sl.ctx.Done():
			break mainLoop
		case <-ticker.C:
		}
	}

	close(sl.stopped)

	if !sl.disabledEndOfRunStalenessMarkers {
		sl.endOfRunStaleness(last, ticker, interval)
	}
}
~~~



##### scrapeLoop.scrapeAndReport 收集数据并写入存储

~~~go
// scrapeAndReport performs a scrape and then appends the result to the storage
// together with reporting metrics, by using as few appenders as possible.
// In the happy scenario, a single appender is used.
// This function uses sl.parentCtx instead of sl.ctx on purpose. A scrape should
// only be cancelled on shutdown, not on reloads.
func (sl *scrapeLoop) scrapeAndReport(interval, timeout time.Duration, last, appendTime time.Time, errc chan<- error) time.Time {
	start := time.Now()

	// Only record after the first scrape.
	if !last.IsZero() {
		targetIntervalLength.WithLabelValues(interval.String()).Observe(
			time.Since(last).Seconds(),
		)
	}

	b := sl.buffers.Get(sl.lastScrapeSize).([]byte)
	defer sl.buffers.Put(b)
	buf := bytes.NewBuffer(b)

	var total, added, seriesAdded int
	var err, appErr, scrapeErr error

	app := sl.appender(sl.parentCtx)
	defer func() {
		if err != nil {
			app.Rollback()
			return
		}
		err = app.Commit()
		if err != nil {
			level.Error(sl.l).Log("msg", "Scrape commit failed", "err", err)
		}
	}()

	defer func() {
		if err = sl.report(app, appendTime, time.Since(start), total, added, seriesAdded, scrapeErr); err != nil {
			level.Warn(sl.l).Log("msg", "Appending scrape report failed", "err", err)
		}
	}()

	if forcedErr := sl.getForcedError(); forcedErr != nil {
		scrapeErr = forcedErr
		// Add stale markers.
		if _, _, _, err := sl.append(app, []byte{}, "", appendTime); err != nil {
			app.Rollback()
			app = sl.appender(sl.parentCtx)
			level.Warn(sl.l).Log("msg", "Append failed", "err", err)
		}
		if errc != nil {
			errc <- forcedErr
		}

		return start
	}

    //获取数据，数据写入buf
	var contentType string
	scrapeCtx, cancel := context.WithTimeout(sl.parentCtx, timeout)
	contentType, scrapeErr = sl.scraper.scrape(scrapeCtx, buf)
	cancel()

	if scrapeErr == nil {
		b = buf.Bytes()
		// NOTE: There were issues with misbehaving clients in the past
		// that occasionally returned empty results. We don't want those
		// to falsely reset our buffer size.
		if len(b) > 0 {
			sl.lastScrapeSize = len(b)
		}
	} else {
		level.Debug(sl.l).Log("msg", "Scrape failed", "err", scrapeErr)
		if errc != nil {
			errc <- scrapeErr
		}
	}

	// A failed scrape is the same as an empty scrape,
	// we still call sl.append to trigger stale markers.
	total, added, seriesAdded, appErr = sl.append(app, b, contentType, appendTime)
	if appErr != nil {
		app.Rollback()
		app = sl.appender(sl.parentCtx)
		level.Debug(sl.l).Log("msg", "Append failed", "err", appErr)
		// The append failed, probably due to a parse error or sample limit.
		// Call sl.append again with an empty scrape to trigger stale markers.
		if _, _, _, err := sl.append(app, []byte{}, "", appendTime); err != nil {
			app.Rollback()
			app = sl.appender(sl.parentCtx)
			level.Warn(sl.l).Log("msg", "Append failed", "err", err)
		}
	}

	if scrapeErr == nil {
		scrapeErr = appErr
	}

	return start
}
~~~

##### scrapeLoop.report

~~~go
func (sl *scrapeLoop) report(app storage.Appender, start time.Time, duration time.Duration, scraped, added, seriesAdded int, scrapeErr error) (err error) {
	sl.scraper.Report(start, duration, scrapeErr)

	ts := timestamp.FromTime(start)

	var health float64
	if scrapeErr == nil {
		health = 1
	}

	if err = sl.addReportSample(app, scrapeHealthMetricName, ts, health); err != nil {
		return
	}
	if err = sl.addReportSample(app, scrapeDurationMetricName, ts, duration.Seconds()); err != nil {
		return
	}
	if err = sl.addReportSample(app, scrapeSamplesMetricName, ts, float64(scraped)); err != nil {
		return
	}
	if err = sl.addReportSample(app, samplesPostRelabelMetricName, ts, float64(added)); err != nil {
		return
	}
	if err = sl.addReportSample(app, scrapeSeriesAddedMetricName, ts, float64(seriesAdded)); err != nil {
		return
	}
	return
}
~~~



##### scrapeLoop.append 数据写入DB

这里使用的app的实际值是 storage.fanoutAppender

~~~go
func (sl *scrapeLoop) append(app storage.Appender, b []byte, contentType string, ts time.Time) (total, added, seriesAdded int, err error) {
	var (
		p              = textparse.New(b, contentType)
		defTime        = timestamp.FromTime(ts)
		appErrs        = appendErrors{}
		sampleLimitErr error
	)

	defer func() {
		if err != nil {
			return
		}
		// Only perform cache cleaning if the scrape was not empty.
		// An empty scrape (usually) is used to indicate a failed scrape.
		sl.cache.iterDone(len(b) > 0)
	}()

loop:
	for {
		var (
			et          textparse.Entry
			sampleAdded bool
		)
		if et, err = p.Next(); err != nil {
			if err == io.EOF {
				err = nil
			}
			break
		}
		switch et {
		case textparse.EntryType:
			sl.cache.setType(p.Type())
			continue
		case textparse.EntryHelp:
			sl.cache.setHelp(p.Help())
			continue
		case textparse.EntryUnit:
			sl.cache.setUnit(p.Unit())
			continue
		case textparse.EntryComment:
			continue
		default:
		}
		total++

		t := defTime
		met, tp, v := p.Series()
		if !sl.honorTimestamps {
			tp = nil
		}
		if tp != nil {
			t = *tp
		}

        /*
        yoloString的实现，为什么不是string(b)
        func yoloString(b []byte) string {
	return *((*string)(unsafe.Pointer(&b)))
}
        */
		if sl.cache.getDropped(yoloString(met)) {
			continue
		}
        //缓存有数据
		ce, ok := sl.cache.get(yoloString(met))

		if ok {
			err = app.AddFast(ce.ref, t, v)
			_, err = sl.checkAddError(ce, met, tp, err, &sampleLimitErr, &appErrs)
			// In theory this should never happen.
			if err == storage.ErrNotFound {
				ok = false
			}
		}
		if !ok {
			var lset labels.Labels

			mets := p.Metric(&lset)
			hash := lset.Hash()

			// Hash label set as it is seen local to the target. Then add target labels
			// and relabeling and store the final label set.
			lset = sl.sampleMutator(lset)

			// The label set may be set to nil to indicate dropping.
			if lset == nil {
				sl.cache.addDropped(mets)
				continue
			}

			if !lset.Has(labels.MetricName) {
				err = errNameLabelMandatory
				break loop
			}

			var ref uint64
			ref, err = app.Add(lset, t, v)
			sampleAdded, err = sl.checkAddError(nil, met, tp, err, &sampleLimitErr, &appErrs)
			if err != nil {
				if err != storage.ErrNotFound {
					level.Debug(sl.l).Log("msg", "Unexpected error", "series", string(met), "err", err)
				}
				break loop
			}

			if tp == nil {
				// Bypass staleness logic if there is an explicit timestamp.
				sl.cache.trackStaleness(hash, lset)
			}
			sl.cache.addRef(mets, ref, lset, hash)
			if sampleAdded && sampleLimitErr == nil {
				seriesAdded++
			}
		}

		// Increment added even if there's an error so we correctly report the
		// number of samples remaining after relabeling.
		added++

	}
	if sampleLimitErr != nil {
		if err == nil {
			err = sampleLimitErr
		}
		// We only want to increment this once per scrape, so this is Inc'd outside the loop.
		targetScrapeSampleLimit.Inc()
	}
	if appErrs.numOutOfOrder > 0 {
		level.Warn(sl.l).Log("msg", "Error on ingesting out-of-order samples", "num_dropped", appErrs.numOutOfOrder)
	}
	if appErrs.numDuplicates > 0 {
		level.Warn(sl.l).Log("msg", "Error on ingesting samples with different value but same timestamp", "num_dropped", appErrs.numDuplicates)
	}
	if appErrs.numOutOfBounds > 0 {
		level.Warn(sl.l).Log("msg", "Error on ingesting samples that are too old or are too far into the future", "num_dropped", appErrs.numOutOfBounds)
	}
	if err == nil {
		sl.cache.forEachStale(func(lset labels.Labels) bool {
			// Series no longer exposed, mark it stale.
			_, err = app.Add(lset, defTime, math.Float64frombits(value.StaleNaN))
			switch errors.Cause(err) {
			case storage.ErrOutOfOrderSample, storage.ErrDuplicateSampleForTimestamp:
				// Do not count these in logging, as this is expected if a target
				// goes away and comes back again with a new scrape loop.
				err = nil
			}
			return err == nil
		})
	}
	return
}

~~~



### scrapeCache

~~~go
// scrapeCache tracks mappings of exposed metric strings to label sets and
// storage references. Additionally, it tracks staleness of series between
// scrapes.
type scrapeCache struct {
	iter uint64 // Current scrape iteration.

	// How many series and metadata entries there were at the last success.
	successfulCount int

	// Parsed string to an entry with information about the actual label set
	// and its storage reference.
	series map[string]*cacheEntry

	// Cache of dropped metric strings and their iteration. The iteration must
	// be a pointer so we can update it without setting a new entry with an unsafe
	// string in addDropped().
	droppedSeries map[string]*uint64

	// seriesCur and seriesPrev store the labels of series that were seen
	// in the current and previous scrape.
	// We hold two maps and swap them out to save allocations.
	seriesCur  map[uint64]labels.Labels
	seriesPrev map[uint64]labels.Labels

	metaMtx  sync.Mutex
	metadata map[string]*metaEntry
}

~~~



##### scrapeCache.get

~~~go
func (c *scrapeCache) get(met string) (*cacheEntry, bool) {
	e, ok := c.series[met]
	if !ok {
		return nil, false
	}
	e.lastIter = c.iter
	return e, true
}
~~~



##### scrapeCache.iterDone

~~~go
func (c *scrapeCache) iterDone(flushCache bool) {
	c.metaMtx.Lock()
	count := len(c.series) + len(c.droppedSeries) + len(c.metadata)
	c.metaMtx.Unlock()

	if flushCache {
		c.successfulCount = count
	} else if count > c.successfulCount*2+1000 {
		// If a target had varying labels in scrapes that ultimately failed,
		// the caches would grow indefinitely. Force a flush when this happens.
		// We use the heuristic that this is a doubling of the cache size
		// since the last scrape, and allow an additional 1000 in case
		// initial scrapes all fail.
		flushCache = true
		targetScrapeCacheFlushForced.Inc()
	}

	if flushCache {
		// All caches may grow over time through series churn
		// or multiple string representations of the same metric. Clean up entries
		// that haven't appeared in the last scrape.
		for s, e := range c.series {
			if c.iter != e.lastIter {
				delete(c.series, s)
			}
		}
		for s, iter := range c.droppedSeries {
			if c.iter != *iter {
				delete(c.droppedSeries, s)
			}
		}
		c.metaMtx.Lock()
		for m, e := range c.metadata {
			// Keep metadata around for 10 scrapes after its metric disappeared.
			if c.iter-e.lastIter > 10 {
				delete(c.metadata, m)
			}
		}
		c.metaMtx.Unlock()

		c.iter++
	}

	// Swap current and previous series.
	c.seriesPrev, c.seriesCur = c.seriesCur, c.seriesPrev

	// We have to delete every single key in the map.
	for k := range c.seriesCur {
		delete(c.seriesCur, k)
	}
}



func (c *scrapeCache) addRef(met string, ref uint64, lset labels.Labels, hash uint64) {
	if ref == 0 {
		return
	}
	c.series[met] = &cacheEntry{ref: ref, lastIter: c.iter, lset: lset, hash: hash}
}

func (c *scrapeCache) addDropped(met string) {
	iter := c.iter
	c.droppedSeries[met] = &iter
}

func (c *scrapeCache) getDropped(met string) bool {
	iterp, ok := c.droppedSeries[met]
	if ok {
		*iterp = c.iter
	}
	return ok
}

func (c *scrapeCache) trackStaleness(hash uint64, lset labels.Labels) {
	c.seriesCur[hash] = lset
}

func (c *scrapeCache) forEachStale(f func(labels.Labels) bool) {
	for h, lset := range c.seriesPrev {
		if _, ok := c.seriesCur[h]; !ok {
			if !f(lset) {
				break
			}
		}
	}
}

func (c *scrapeCache) setType(metric []byte, t textparse.MetricType) {
	c.metaMtx.Lock()

	e, ok := c.metadata[yoloString(metric)]
	if !ok {
		e = &metaEntry{typ: textparse.MetricTypeUnknown}
		c.metadata[string(metric)] = e
	}
	e.typ = t
	e.lastIter = c.iter

	c.metaMtx.Unlock()
}

func (c *scrapeCache) setHelp(metric, help []byte) {
	c.metaMtx.Lock()

	e, ok := c.metadata[yoloString(metric)]
	if !ok {
		e = &metaEntry{typ: textparse.MetricTypeUnknown}
		c.metadata[string(metric)] = e
	}
	if e.help != yoloString(help) {
		e.help = string(help)
	}
	e.lastIter = c.iter

	c.metaMtx.Unlock()
}

func (c *scrapeCache) setUnit(metric, unit []byte) {
	c.metaMtx.Lock()

	e, ok := c.metadata[yoloString(metric)]
	if !ok {
		e = &metaEntry{typ: textparse.MetricTypeUnknown}
		c.metadata[string(metric)] = e
	}
	if e.unit != yoloString(unit) {
		e.unit = string(unit)
	}
	e.lastIter = c.iter

	c.metaMtx.Unlock()
}

func (c *scrapeCache) GetMetadata(metric string) (MetricMetadata, bool) {
	c.metaMtx.Lock()
	defer c.metaMtx.Unlock()

	m, ok := c.metadata[metric]
	if !ok {
		return MetricMetadata{}, false
	}
	return MetricMetadata{
		Metric: metric,
		Type:   m.typ,
		Help:   m.help,
		Unit:   m.unit,
	}, true
}

func (c *scrapeCache) ListMetadata() []MetricMetadata {
	c.metaMtx.Lock()
	defer c.metaMtx.Unlock()

	res := make([]MetricMetadata, 0, len(c.metadata))

	for m, e := range c.metadata {
		res = append(res, MetricMetadata{
			Metric: m,
			Type:   e.typ,
			Help:   e.help,
			Unit:   e.unit,
		})
	}
	return res
}

// MetadataSize returns the size of the metadata cache.
func (c *scrapeCache) SizeMetadata() (s int) {
	c.metaMtx.Lock()
	defer c.metaMtx.Unlock()
	for _, e := range c.metadata {
		s += e.size()
	}

	return s
}

// MetadataLen returns the number of metadata entries in the cache.
func (c *scrapeCache) LengthMetadata() int {
	c.metaMtx.Lock()
	defer c.metaMtx.Unlock()

	return len(c.metadata)
}
~~~



## scraper targetScraper

~~~go
// A scraper retrieves samples and accepts a status report at the end.
type scraper interface {
	scrape(ctx context.Context, w io.Writer) (string, error)
	Report(start time.Time, dur time.Duration, err error)
	offset(interval time.Duration, jitterSeed uint64) time.Duration
}

// targetScraper implements the scraper interface for a target.
type targetScraper struct {
	*Target

	client  *http.Client
	req     *http.Request
	timeout time.Duration

	gzipr *gzip.Reader
	buf   *bufio.Reader
}
~~~



##### targetScraper.scrape 从数据节点拉取数据

~~~go
func (s *targetScraper) scrape(ctx context.Context, w io.Writer) (string, error) {
	if s.req == nil {
		req, err := http.NewRequest("GET", s.URL().String(), nil)
		if err != nil {
			return "", err
		}
		req.Header.Add("Accept", acceptHeader)
		req.Header.Add("Accept-Encoding", "gzip")
		req.Header.Set("User-Agent", userAgentHeader)
		req.Header.Set("X-Prometheus-Scrape-Timeout-Seconds", fmt.Sprintf("%f", s.timeout.Seconds()))

		s.req = req
	}

	resp, err := s.client.Do(s.req.WithContext(ctx))
	if err != nil {
		return "", err
	}
	defer func() {
		io.Copy(ioutil.Discard, resp.Body)
		resp.Body.Close()
	}()

	if resp.StatusCode != http.StatusOK {
		return "", errors.Errorf("server returned HTTP status %s", resp.Status)
	}

	if resp.Header.Get("Content-Encoding") != "gzip" {
		_, err = io.Copy(w, resp.Body)
		if err != nil {
			return "", err
		}
		return resp.Header.Get("Content-Type"), nil
	}

	if s.gzipr == nil {
		s.buf = bufio.NewReader(resp.Body)
		s.gzipr, err = gzip.NewReader(s.buf)
		if err != nil {
			return "", err
		}
	} else {
		s.buf.Reset(resp.Body)
		if err = s.gzipr.Reset(s.buf); err != nil {
			return "", err
		}
	}

	_, err = io.Copy(w, s.gzipr)
	s.gzipr.Close()
	if err != nil {
		return "", err
	}
	return resp.Header.Get("Content-Type"), nil
}
~~~



## Target

##### Target的定义

~~~go
// Target refers to a singular HTTP or HTTPS endpoint.
type Target struct {
	// Labels before any processing.
	discoveredLabels labels.Labels
	// Any labels that are added to this target and its metrics.
	labels labels.Labels
	// Additional URL parameters that are part of the target URL.
	params url.Values

	mtx                sync.RWMutex
	lastError          error
	lastScrape         time.Time
	lastScrapeDuration time.Duration
	health             TargetHealth
	metadata           MetricMetadataStore
}

// Targets is a sortable list of targets.
type Targets []*Target
~~~



##### Target.Repot

~~~go
// Report sets target data about the last scrape.
func (t *Target) Report(start time.Time, dur time.Duration, err error) {
	t.mtx.Lock()
	defer t.mtx.Unlock()

	if err == nil {
		t.health = HealthGood
	} else {
		t.health = HealthBad
	}

	t.lastError = err
	t.lastScrape = start
	t.lastScrapeDuration = dur
}
~~~



##### targetsFromGroup

~~~go
// targetsFromGroup builds targets based on the given TargetGroup and config.
func targetsFromGroup(tg *targetgroup.Group, cfg *config.ScrapeConfig) ([]*Target, error) {
	targets := make([]*Target, 0, len(tg.Targets))

	for i, tlset := range tg.Targets {
		lbls := make([]labels.Label, 0, len(tlset)+len(tg.Labels))

		for ln, lv := range tlset {
			lbls = append(lbls, labels.Label{Name: string(ln), Value: string(lv)})
		}
		for ln, lv := range tg.Labels {
			if _, ok := tlset[ln]; !ok {
				lbls = append(lbls, labels.Label{Name: string(ln), Value: string(lv)})
			}
		}

		lset := labels.New(lbls...)

		lbls, origLabels, err := populateLabels(lset, cfg)
		if err != nil {
			return nil, errors.Wrapf(err, "instance %d in group %s", i, tg)
		}
		if lbls != nil || origLabels != nil {
			targets = append(targets, NewTarget(lbls, origLabels, cfg.Params))
		}
	}
	return targets, nil
}
~~~



## limitAppender

~~~
// limitAppender limits the number of total appended samples in a batch.
type limitAppender struct {
	storage.Appender

	limit int
	i     int
}

func (app *limitAppender) Add(lset labels.Labels, t int64, v float64) (uint64, error) {
	if !value.IsStaleNaN(v) {
		app.i++
		if app.i > app.limit {
			return 0, errSampleLimit
		}
	}
	ref, err := app.Appender.Add(lset, t, v)
	if err != nil {
		return 0, err
	}
	return ref, nil
}

func (app *limitAppender) AddFast(ref uint64, t int64, v float64) error {
	if !value.IsStaleNaN(v) {
		app.i++
		if app.i > app.limit {
			return errSampleLimit
		}
	}
	err := app.Appender.AddFast(ref, t, v)
	return err
}
~~~

