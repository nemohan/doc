# Head

[TOC]

## 总结

在prometheus tsdb存储中，需要搞清楚的几个概念：

* series 由label（键值对）构成
* sample  series的id、时间戳、时间序列对应的值
* 

时序数据的特点：

* 随时间变化
* series大量重复

整体文件目录布局：

<font color="red">chunks_head目录中的文件的用途是什么</font>

![1615648091862](${img}/1615648091862.png)

### 流程

##### 写WAL文件

headAppender.Commit被调用时，将series、samples写入WAL文件

##### 写入chunks_head/目录下的文件

headAppender.Commit被调用时，将samples先写入chunk。然后再将chunk写入chunks_head目录下的文件




## Head 缓存

Head 缓存写入的数据，然后通过后台协程将缓存的数据写入磁盘



Head的组成部分：

* Head.series 保存了lables的hash、id(Head.lastSeriesID生成)到series的映射
* Head.postings 保存了所有labels的名称、labels的值到 series id的映射
* Head.symbols 是由label名称和值构成的hash table，有何用途

~~~go
// Head handles reads and writes of time series data within a time window.
type Head struct {
	chunkRange            atomic.Int64
	numSeries             atomic.Uint64
	minTime, maxTime      atomic.Int64 // Current min and max of the samples included in the head.
	minValidTime          atomic.Int64 // Mint allowed to be added to the head. It shouldn't be lower than the maxt of the last persisted block.
	lastWALTruncationTime atomic.Int64
	lastSeriesID          atomic.Uint64

	metrics      *headMetrics
	wal          *wal.WAL
	logger       log.Logger
	appendPool   sync.Pool
	seriesPool   sync.Pool
	bytesPool    sync.Pool
	memChunkPool sync.Pool

	// All series addressable by their ID or hash.
	series         *stripeSeries
	seriesCallback SeriesLifecycleCallback

	symMtx  sync.RWMutex
	symbols map[string]struct{}

	deletedMtx sync.Mutex
	deleted    map[uint64]int // Deleted series, and what WAL segment they must be kept until.

	postings *index.MemPostings // Postings lists for terms.

	tombstones *tombstones.MemTombstones

	iso *isolation

	cardinalityMutex      sync.Mutex
	cardinalityCache      *index.PostingsStats // Posting stats cache which will expire after 30sec.
	lastPostingsStatsCall time.Duration        // Last posting stats call (PostingsCardinalityStats()) time for caching.

	// chunkDiskMapper is used to write and read Head chunks to/from disk.
	chunkDiskMapper *chunks.ChunkDiskMapper
	// chunkDirRoot is the parent directory of the chunks directory.
	chunkDirRoot string

	closedMtx sync.Mutex
	closed    bool
}
~~~



##### NewHead	

~~~go
// NewHead opens the head block in dir.
// stripeSize sets the number of entries in the hash map, it must be a power of 2.
// A larger stripeSize will allocate more memory up-front, but will increase performance when handling a large number of series.
// A smaller stripeSize reduces the memory allocated, but can decrease performance with large number of series.
func NewHead(r prometheus.Registerer, l log.Logger, wal *wal.WAL, chunkRange int64, chkDirRoot string, chkPool chunkenc.Pool, chkWriteBufferSize, stripeSize int, seriesCallback SeriesLifecycleCallback) (*Head, error) {
	if l == nil {
		l = log.NewNopLogger()
	}
    //chunkRange 指定了覆盖的时间范围
	if chunkRange < 1 {
		return nil, errors.Errorf("invalid chunk range %d", chunkRange)
	}
	if seriesCallback == nil {
		seriesCallback = &noopSeriesLifecycleCallback{}
	}
	h := &Head{
		wal:        wal,
		logger:     l,
		series:     newStripeSeries(stripeSize, seriesCallback),
		symbols:    map[string]struct{}{},
		postings:   index.NewUnorderedMemPostings(),
		tombstones: tombstones.NewMemTombstones(),
		iso:        newIsolation(),
		deleted:    map[uint64]int{},
		memChunkPool: sync.Pool{
			New: func() interface{} {
				return &memChunk{}
			},
		},
		chunkDirRoot:   chkDirRoot, //./data
		seriesCallback: seriesCallback,
	}
	h.chunkRange.Store(chunkRange)
	h.minTime.Store(math.MaxInt64)
	h.maxTime.Store(math.MinInt64)
	h.lastWALTruncationTime.Store(math.MinInt64)
	h.metrics = newHeadMetrics(h, r)

	if chkPool == nil {
		chkPool = chunkenc.NewPool()
	}

    //chkWriteBufferSize 是4M
    //mmappedChunksDir 获取目录./data/chunks_head
	var err error
	h.chunkDiskMapper, err = chunks.NewChunkDiskMapper(mmappedChunksDir(chkDirRoot), chkPool, chkWriteBufferSize)
	if err != nil {
		return nil, err
	}

	return h, nil
}
~~~



##### initAppender

~~~go
// initAppender is a helper to initialize the time bounds of the head
// upon the first sample it receives.
type initAppender struct {
	app  storage.Appender
	head *Head
}

func (a *initAppender) Add(lset labels.Labels, t int64, v float64) (uint64, error) {
	if a.app != nil {
		return a.app.Add(lset, t, v)
	}
	a.head.initTime(t)
	a.app = a.head.appender()

	return a.app.Add(lset, t, v)
}

func (a *initAppender) AddFast(ref uint64, t int64, v float64) error {
	if a.app == nil {
		return storage.ErrNotFound
	}
	return a.app.AddFast(ref, t, v)
}

func (a *initAppender) Commit() error {
	if a.app == nil {
		return nil
	}
	return a.app.Commit()
}

func (a *initAppender) Rollback() error {
	if a.app == nil {
		return nil
	}
	return a.app.Rollback()
}

~~~



##### Head.initTime

~~~go
// initTime initializes a head with the first timestamp. This only needs to be called
// for a completely fresh head with an empty WAL.
func (h *Head) initTime(t int64) {
	if !h.minTime.CAS(math.MaxInt64, t) {
		return
	}
	// Ensure that max time is initialized to at least the min time we just set.
	// Concurrent appenders may already have set it to a higher value.
	h.maxTime.CAS(math.MinInt64, t)
}
~~~



##### Head.Appender 获取headAppender实例

~~~go
/ Appender returns a new Appender on the database.
func (h *Head) Appender(_ context.Context) storage.Appender {
	h.metrics.activeAppenders.Inc()

	// The head cache might not have a starting point yet. The init appender
	// picks up the first appended timestamp as the base.
	if h.MinTime() == math.MaxInt64 {
		return &initAppender{
			head: h,
		}
	}
	return h.appender()
}

~~~



##### Head.appender

~~~go
func (h *Head) appender() *headAppender {
	appendID := h.iso.newAppendID()
	cleanupAppendIDsBelow := h.iso.lowWatermark()

	return &headAppender{
		head:                  h,
		minValidTime:          h.appendableMinValidTime(),
		mint:                  math.MaxInt64,
		maxt:                  math.MinInt64,
		samples:               h.getAppendBuffer(),
		sampleSeries:          h.getSeriesBuffer(),
		appendID:              appendID,
		cleanupAppendIDsBelow: cleanupAppendIDsBelow,
	}
}
~~~



##### Head.getOrCreate 根据lables的哈希值查找获取创建其所在的memSeries

* 根据lables的哈希值在Head.stripeSeries中查找其所在的memSeries。若找到则直接返回
* 递增Head.lastSeriesID，以其作为新的series的ref id
* 没找到，则创建其memSeries

~~~go

func (h *Head) getOrCreate(hash uint64, lset labels.Labels) (*memSeries, bool, error) {
	// Just using `getOrSet` below would be semantically sufficient, but we'd create
	// a new series on every sample inserted via Add(), which causes allocations
	// and makes our series IDs rather random and harder to compress in postings.
	s := h.series.getByHash(hash, lset)
	if s != nil {
		return s, false, nil
	}

	// Optimistically assume that we are the first one to create the series.
	id := h.lastSeriesID.Inc()

	return h.getOrCreateWithID(id, hash, lset)
}
~~~



##### Head.getOrCreateWithID 创建保存lables的memSeries

* 创建memSeries
* 

~~~go
func (h *Head) getOrCreateWithID(id, hash uint64, lset labels.Labels) (*memSeries, bool, error) {
	s := newMemSeries(lset, id, h.chunkRange.Load(), &h.memChunkPool)

	s, created, err := h.series.getOrSet(hash, s)
	if err != nil {
		return nil, false, err
	}
	if !created {
		return s, false, nil
	}

	h.metrics.seriesCreated.Inc()
	h.numSeries.Inc()

	h.symMtx.Lock()
	defer h.symMtx.Unlock()
	
    //TODO: name 或value的重复有没有影响
    //h.symbols 有何用途??????????
	for _, l := range lset {
		h.symbols[l.Name] = struct{}{}
		h.symbols[l.Value] = struct{}{}
	}

    //
	h.postings.Add(id, lset)
	return s, true, nil
}
~~~



##### Head.indexRange

~~~go
func (h *Head) indexRange(mint, maxt int64) *headIndexReader {
	if hmin := h.MinTime(); hmin > mint {
		mint = hmin
	}
	return &headIndexReader{head: h, mint: mint, maxt: maxt}
}
~~~



##### Head.chunksRange 获取读取缓存数据的接口headChunkReader

~~~go
func (h *Head) chunksRange(mint, maxt int64, is *isolationState) (*headChunkReader, error) {
	h.closedMtx.Lock()
	defer h.closedMtx.Unlock()
	if h.closed {
		return nil, errors.New("can't read from a closed head")
	}
	if hmin := h.MinTime(); hmin > mint {
		mint = hmin
	}
	return &headChunkReader{
		head:     h,
		mint:     mint,
		maxt:     maxt,
		isoState: is,
	}, nil
}
~~~



##### Head.truncateMemory

~~~go
// truncateMemory removes old data before mint from the head.
func (h *Head) truncateMemory(mint int64) (err error) {
	defer func() {
		if err != nil {
			h.metrics.headTruncateFail.Inc()
		}
	}()
	initialize := h.MinTime() == math.MaxInt64

	if h.MinTime() >= mint && !initialize {
		return nil
	}
	h.minTime.Store(mint)
	h.minValidTime.Store(mint)

	// Ensure that max time is at least as high as min time.
	for h.MaxTime() < mint {
		h.maxTime.CAS(h.MaxTime(), mint)
	}

	// This was an initial call to Truncate after loading blocks on startup.
	// We haven't read back the WAL yet, so do not attempt to truncate it.
	if initialize {
		return nil
	}

	h.metrics.headTruncateTotal.Inc()
	start := time.Now()

	actualMint := h.gc()
	level.Info(h.logger).Log("msg", "Head GC completed", "duration", time.Since(start))
	h.metrics.gcDuration.Observe(time.Since(start).Seconds())
	if actualMint > h.minTime.Load() {
		// The actual mint of the Head is higher than the one asked to truncate.
		appendableMinValidTime := h.appendableMinValidTime()
		if actualMint < appendableMinValidTime {
			h.minTime.Store(actualMint)
			h.minValidTime.Store(actualMint)
		} else {
			// The actual min time is in the appendable window.
			// So we set the mint to the appendableMinValidTime.
			h.minTime.Store(appendableMinValidTime)
			h.minValidTime.Store(appendableMinValidTime)
		}
	}

	// Truncate the chunk m-mapper.
	if err := h.chunkDiskMapper.Truncate(mint); err != nil {
		return errors.Wrap(err, "truncate chunks.HeadReadWriter")
	}
	return nil
}
~~~







### wal相关

##### Head.truncateWAL 截断WAL (TODO)

~~~go
// truncateWAL removes old data before mint from the WAL.
func (h *Head) truncateWAL(mint int64) error {
	if h.wal == nil || mint <= h.lastWALTruncationTime.Load() {
		return nil
	}
	start := time.Now()
	h.lastWALTruncationTime.Store(mint)

	first, last, err := wal.Segments(h.wal.Dir())
	if err != nil {
		return errors.Wrap(err, "get segment range")
	}
	// Start a new segment, so low ingestion volume TSDB don't have more WAL than
	// needed.
	if err := h.wal.NextSegment(); err != nil {
		return errors.Wrap(err, "next segment")
	}
	last-- // Never consider last segment for checkpoint.
	if last < 0 {
		return nil // no segments yet.
	}
	// The lower two thirds of segments should contain mostly obsolete samples.
	// If we have less than two segments, it's not worth checkpointing yet.
	// With the default 2h blocks, this will keeping up to around 3h worth
	// of WAL segments.
	last = first + (last-first)*2/3
	if last <= first {
		return nil
	}

	keep := func(id uint64) bool {
		if h.series.getByID(id) != nil {
			return true
		}
		h.deletedMtx.Lock()
		_, ok := h.deleted[id]
		h.deletedMtx.Unlock()
		return ok
	}
	h.metrics.checkpointCreationTotal.Inc()
	if _, err = wal.Checkpoint(h.logger, h.wal, first, last, keep, mint); err != nil {
		h.metrics.checkpointCreationFail.Inc()
		if _, ok := errors.Cause(err).(*wal.CorruptionErr); ok {
			h.metrics.walCorruptionsTotal.Inc()
		}
		return errors.Wrap(err, "create checkpoint")
	}
	if err := h.wal.Truncate(last + 1); err != nil {
		// If truncating fails, we'll just try again at the next checkpoint.
		// Leftover segments will just be ignored in the future if there's a checkpoint
		// that supersedes them.
		level.Error(h.logger).Log("msg", "truncating segments failed", "err", err)
	}

	// The checkpoint is written and segments before it is truncated, so we no
	// longer need to track deleted series that are before it.
	h.deletedMtx.Lock()
	for ref, segment := range h.deleted {
		if segment < first {
			delete(h.deleted, ref)
		}
	}
	h.deletedMtx.Unlock()

	h.metrics.checkpointDeleteTotal.Inc()
	if err := wal.DeleteCheckpoints(h.wal.Dir(), last); err != nil {
		// Leftover old checkpoints do not cause problems down the line beyond
		// occupying disk space.
		// They will just be ignored since a higher checkpoint exists.
		level.Error(h.logger).Log("msg", "delete old checkpoints", "err", err)
		h.metrics.checkpointDeleteFail.Inc()
	}
	h.metrics.walTruncateDuration.Observe(time.Since(start).Seconds())

	level.Info(h.logger).Log("msg", "WAL checkpoint complete",
		"first", first, "last", last, "duration", time.Since(start))

	return nil
}
~~~



### headIndexReader

headIndexReader负责从head读取作为索引的数据

##### headIndexReader.Symbols 返回所有由label_name和label_value组成的symbol

symbol由标签的名称和值组成

~~~go
func (h *headIndexReader) Symbols() index.StringIter {
	h.head.symMtx.RLock()
	res := make([]string, 0, len(h.head.symbols))

	for s := range h.head.symbols {
		res = append(res, s)
	}
	h.head.symMtx.RUnlock()

	sort.Strings(res)
	return index.NewStringListIter(res)
}
~~~



##### headIndexReader.Postings 获取所有的label键值对

~~~go
// Postings returns the postings list iterator for the label pairs.
func (h *headIndexReader) Postings(name string, values ...string) (index.Postings, error) {
	res := make([]index.Postings, 0, len(values))
	for _, value := range values {
        //h.head.postings.Get 实际返回的是ListPostings类型
		res = append(res, h.head.postings.Get(name, value))
	}
	return index.Merge(res...), nil
}
~~~



##### headIndexReader.Series

~~~go

// Series returns the series for the given reference.
func (h *headIndexReader) Series(ref uint64, lbls *labels.Labels, chks *[]chunks.Meta) error {
    //根据series 的id 获取memSeries
	s := h.head.series.getByID(ref)

	if s == nil {
		h.head.metrics.seriesNotFound.Inc()
		return storage.ErrNotFound
	}
	*lbls = append((*lbls)[:0], s.lset...)

	s.Lock()
	defer s.Unlock()

	*chks = (*chks)[:0]

    //mmapedChunks 是已经写入./data/chunks_head/目录下的文件中的chunk
	for i, c := range s.mmappedChunks {
		// Do not expose chunks that are outside of the specified range.
		if !c.OverlapsClosedInterval(h.mint, h.maxt) {
			continue
		}
		*chks = append(*chks, chunks.Meta{
			MinTime: c.minTime,
			MaxTime: c.maxTime,//高40位是s.ref即series id, 低24位是 i
			Ref:     packChunkID(s.ref, uint64(s.chunkID(i))),
		})
	}
	if s.headChunk != nil && s.headChunk.OverlapsClosedInterval(h.mint, h.maxt) {
		*chks = append(*chks, chunks.Meta{
			MinTime: s.headChunk.minTime,
			MaxTime: math.MaxInt64, // Set the head chunks as open (being appended to).
			Ref:     packChunkID(s.ref, uint64(s.chunkID(len(s.mmappedChunks)))),
		})
	}

	return nil
}
~~~



##### headIndexReader.SortedPostings

~~~go

func (h *headIndexReader) SortedPostings(p index.Postings) index.Postings {
	series := make([]*memSeries, 0, 128)

    //p.Next 遍历所有的series id
	// Fetch all the series only once.
	for p.Next() {
		s := h.head.series.getByID(p.At())
		if s == nil {
			level.Debug(h.head.logger).Log("msg", "Looked up series not found")
		} else {
			series = append(series, s)
		}
	}
	if err := p.Err(); err != nil {
		return index.ErrPostings(errors.Wrap(err, "expand postings"))
	}

	sort.Slice(series, func(i, j int) bool {
		return labels.Compare(series[i].lset, series[j].lset) < 0
	})

	// Convert back to list.
	ep := make([]uint64, 0, len(series))
	for _, p := range series {
		ep = append(ep, p.ref)
	}
	return index.NewListPostings(ep)
}
~~~



### 1 headAppender  负责写数据到缓存的接口

headAppender 是Head对外提供的写数据的接口

* Commit 时会将headAppender.series、headAppender.samples写入WAL文件

##### headAppender 的定义

~~~go
type headAppender struct {
	head         *Head
	minValidTime int64 // No samples below this timestamp are allowed.
	mint, maxt   int64

	series       []record.RefSeries
	samples      []record.RefSample
	sampleSeries []*memSeries

	appendID, cleanupAppendIDsBelow uint64
	closed                          bool
}
~~~



##### headAppender.Add 写数据到缓存

参数: 

* lset label
* t 时间戳
* v 数值

返回值：

* 返回Head维护的series id


~~~go
func (a *headAppender) Add(lset labels.Labels, t int64, v float64) (uint64, error) {
	if t < a.minValidTime {
		a.head.metrics.outOfBoundSamples.Inc()
		return 0, storage.ErrOutOfBounds
	}

	// Ensure no empty labels have gotten through.
	lset = lset.WithoutEmpty()

	if len(lset) == 0 {
		return 0, errors.Wrap(ErrInvalidSample, "empty labelset")
	}

	if l, dup := lset.HasDuplicateLabelNames(); dup {
		return 0, errors.Wrap(ErrInvalidSample, fmt.Sprintf(`label name "%s" is not unique`, l))
	}

    //查找或创建lset所在的memSeries
	s, created, err := a.head.getOrCreate(lset.Hash(), lset)
	if err != nil {
		return 0, err
	}

    //新的series, 是不是新的series由labels确定
    //在influxdb中labels就是tags
	if created {
		a.series = append(a.series, record.RefSeries{
			Ref:    s.ref,
			Labels: lset,
		})
	}
	return s.ref, a.AddFast(s.ref, t, v)
}
~~~



##### headAppender.AddFast

~~~go
func (a *headAppender) AddFast(ref uint64, t int64, v float64) error {
	if t < a.minValidTime {
		a.head.metrics.outOfBoundSamples.Inc()
		return storage.ErrOutOfBounds
	}

	s := a.head.series.getByID(ref)
	if s == nil {
		return errors.Wrap(storage.ErrNotFound, "unknown series")
	}
	s.Lock()
    //检查时间范围和 v是否重复
	if err := s.appendable(t, v); err != nil {
		s.Unlock()
		if err == storage.ErrOutOfOrderSample {
			a.head.metrics.outOfOrderSamples.Inc()
		}
		return err
	}
	s.pendingCommit = true
	s.Unlock()

	if t < a.mint {
		a.mint = t
	}
	if t > a.maxt {
		a.maxt = t
	}
	//commit时会将a.samples写入WAL文件
	a.samples = append(a.samples, record.RefSample{
		Ref: ref,
		T:   t,
		V:   v,
	})
	a.sampleSeries = append(a.sampleSeries, s)
	return nil
}
~~~



##### headAppender.Commit 提交

~~~go
func (a *headAppender) Commit() (err error) {
	if a.closed {
		return ErrAppenderClosed
	}
    
	defer func() { a.closed = true }()
    
    //写入WAL
	if err := a.log(); err != nil {
		//nolint: errcheck
		a.Rollback() // Most likely the same error will happen again.
		return errors.Wrap(err, "write to WAL")
	}

	defer a.head.metrics.activeAppenders.Dec()
    //实际是: Head.appendPool.Put(a.samples[:0])
	defer a.head.putAppendBuffer(a.samples)
    //实际是: Head.bytesPool.Put(a.sampleSeries[:0])
	defer a.head.putSeriesBuffer(a.sampleSeries)
	defer a.head.iso.closeAppend(a.appendID)

	total := len(a.samples)
	var series *memSeries
	for i, s := range a.samples {
		series = a.sampleSeries[i]
		series.Lock()
		ok, chunkCreated := series.append(s.T, s.V, a.appendID, a.head.chunkDiskMapper)
		series.cleanupAppendIDsBelow(a.cleanupAppendIDsBelow)
		series.pendingCommit = false
		series.Unlock()

		if !ok {
			total--
			a.head.metrics.outOfOrderSamples.Inc()
		}
		if chunkCreated {
			a.head.metrics.chunks.Inc()
			a.head.metrics.chunksCreated.Inc()
		}
	}

	a.head.metrics.samplesAppended.Add(float64(total))
	a.head.updateMinMaxTime(a.mint, a.maxt)

	return nil
}
~~~

##### headAppender.log 写数据到WAL===============

* series 写入wal
* samples 写入wal

~~~go

func (a *headAppender) log() error {
	if a.head.wal == nil {
		return nil
	}

    //从缓存池获取一个buffer
	buf := a.head.getBytesBuffer()
	defer func() { a.head.putBytesBuffer(buf) }()

	var rec []byte
	var enc record.Encoder

    //series       []record.RefSeries
	
	if len(a.series) > 0 {
		rec = enc.Series(a.series, buf)
        //这是为啥, 将buf长度重新设置为0
		buf = rec[:0]

		if err := a.head.wal.Log(rec); err != nil {
			return errors.Wrap(err, "log series")
		}
	}
    //samples      []record.RefSample
	if len(a.samples) > 0 {
		rec = enc.Samples(a.samples, buf)
		buf = rec[:0]

		if err := a.head.wal.Log(rec); err != nil {
			return errors.Wrap(err, "log samples")
		}
	}
	return nil
}

~~~









### stripeSeries

可根据series id 或hash在stripSeries快速查找series

~~~go
// stripeSeries locks modulo ranges of IDs and hashes to reduce lock contention.
// The locks are padded to not be on the same cache line. Filling the padded space
// with the maps was profiled to be slower – likely due to the additional pointer
// dereferences.
type stripeSeries struct {
	size                    int
    //series 类似一个哈希表，
    //key 是head维护的seriesID。
    //根据ref id确定bucket
	series                  []map[uint64]*memSeries
    
    //通过hash查找
    //seriesHashmap 保存相同哈希值的series
    //type seriesHashmap map[uint64][]*memSeries
	hashes                  []seriesHashmap
    //一个hash bucket一个锁
	locks                   []stripeLock
    
	seriesLifecycleCallback SeriesLifecycleCallback
}
~~~

##### newStripeSeries

~~~go
func newStripeSeries(stripeSize int, seriesCallback SeriesLifecycleCallback) *stripeSeries {
	s := &stripeSeries{
        //stripeSize 默认是16KB，就是65536个
		size:                    stripeSize,
		series:                  make([]map[uint64]*memSeries, stripeSize),
		hashes:                  make([]seriesHashmap, stripeSize),
		locks:                   make([]stripeLock, stripeSize),
		seriesLifecycleCallback: seriesCallback,
	}

	for i := range s.series {
		s.series[i] = map[uint64]*memSeries{}
	}
	for i := range s.hashes {
		s.hashes[i] = seriesHashmap{}
	}
	return s
}
~~~



##### stripeSeries.getOrSet 根据hash查找或设置memSeries

根据lables的hash值，查找或设置memSeries

~~~go
func (s *stripeSeries) getOrSet(hash uint64, series *memSeries) (*memSeries, bool, error) {
	// PreCreation is called here to avoid calling it inside the lock.
	// It is not necessary to call it just before creating a series,
	// rather it gives a 'hint' whether to create a series or not.
	createSeriesErr := s.seriesLifecycleCallback.PreCreation(series.lset)

	i := hash & uint64(s.size-1)
	s.locks[i].Lock()

    //查找lset对应的memSeries, 若没找到则创建
	if prev := s.hashes[i].get(hash, series.lset); prev != nil {
		s.locks[i].Unlock()
		return prev, false, nil
	}
  
	if createSeriesErr == nil {
		s.hashes[i].set(hash, series)
	}
	s.locks[i].Unlock()

	if createSeriesErr != nil {
		// The callback prevented creation of series.
		return nil, false, createSeriesErr
	}
	// Setting the series in the s.hashes marks the creation of series
	// as any further calls to this methods would return that series.
	s.seriesLifecycleCallback.PostCreation(series.lset)

	i = series.ref & uint64(s.size-1)

	s.locks[i].Lock()
	s.series[i][series.ref] = series
	s.locks[i].Unlock()

	return series, true, nil
}
~~~



##### stripeSeries.getByID 根据series的id获取 memSeries

~~~go
func (s *stripeSeries) getByID(id uint64) *memSeries {
	i := id & uint64(s.size-1)

	s.locks[i].RLock()
	series := s.series[i][id]
	s.locks[i].RUnlock()

	return series
}
~~~



##### stripeSeries.getByHash 根据hash值获取lables 所在的memSeries

~~~go
func (s *stripeSeries) getByHash(hash uint64, lset labels.Labels) *memSeries {
	i := hash & uint64(s.size-1)
	//确定bucket
	s.locks[i].RLock()
	series := s.hashes[i].get(hash, lset)
	s.locks[i].RUnlock()

	return series
}
~~~

### seriesHashmap

seriesHashmap 存储series的hash 到memSeries的映射 

#####  seriesHashmap.get    获取labels所在的memSeries

~~~go
// seriesHashmap is a simple hashmap for memSeries by their label set. It is built
// on top of a regular hashmap and holds a slice of series to resolve hash collisions.
// Its methods require the hash to be submitted with it to avoid re-computations throughout
// the code.
type seriesHashmap map[uint64][]*memSeries

func (m seriesHashmap) get(hash uint64, lset labels.Labels) *memSeries {
	for _, s := range m[hash] {
		if labels.Equal(s.lset, lset) {
			return s
		}
	}
	return nil
}
~~~



### memSeries

memSeries 负责存储某个series 对应的一段时间范围内的所有sample，比如有如下series。sample写入memChunk。待memChunk快满时写入文件。

~~~
mem_total=2 2020-11-11 13:01:01
mem_total=3 2020-11-11 13:01:02
~~~

##### memSeries的定义

几个关键的成员:

* ref 对应series的id
* chunkRange 涵盖的时间范围
* memChunk存储sample数据

~~~go
// memSeries is the in-memory representation of a series. None of its methods
// are goroutine safe and it is the caller's responsibility to lock it.
type memSeries struct {
	sync.RWMutex

	ref           uint64 //series 的id
	lset          labels.Labels //series 对应的所有label
	mmappedChunks []*mmappedChunk
	headChunk     *memChunk
	chunkRange    int64 //memSeries 涵盖的时间范围
	firstChunkID  int

	nextAt        int64 // Timestamp at which to cut the next chunk.
	sampleBuf     [4]sample
	pendingCommit bool // Whether there are samples waiting to be committed to this series.

	app chunkenc.Appender // Current appender for the chunk.

	memChunkPool *sync.Pool

	txs *txRing
}
~~~



##### newMemSeries

参数:

* chunkRange 是head.chunkRange 

~~~go
func newMemSeries(lset labels.Labels, id uint64, chunkRange int64, memChunkPool *sync.Pool) *memSeries {
	s := &memSeries{
		lset:         lset,
		ref:          id,
		chunkRange:   chunkRange,
		nextAt:       math.MinInt64,
		txs:          newTxRing(4),
		memChunkPool: memChunkPool, //使用的是Head.chunkPool
	}
	return s
}
~~~



##### memSeries.chunk

headChunkReader.Chunk 会调用此函数

~~~go
// chunk returns the chunk for the chunk id from memory or by m-mapping it from the disk.
// If garbageCollect is true, it means that the returned *memChunk
// (and not the chunkenc.Chunk inside it) can be garbage collected after it's usage.
func (s *memSeries) chunk(id int, chunkDiskMapper *chunks.ChunkDiskMapper) (chunk *memChunk, garbageCollect bool, err error) {
	// ix represents the index of chunk in the s.mmappedChunks slice. The chunk id's are
	// incremented by 1 when new chunk is created, hence (id - firstChunkID) gives the slice index.
	// The max index for the s.mmappedChunks slice can be len(s.mmappedChunks)-1, hence if the ix
	// is len(s.mmappedChunks), it represents the next chunk, which is the head chunk.
    
    //s.firstChunkID 和s.mmappedChunks 是什么时候设置的
	ix := id - s.firstChunkID
	if ix < 0 || ix > len(s.mmappedChunks) {
		return nil, false, storage.ErrNotFound
	}
	if ix == len(s.mmappedChunks) {
		if s.headChunk == nil {
			return nil, false, errors.New("invalid head chunk")
		}
		return s.headChunk, false, nil
	}
	chk, err := chunkDiskMapper.Chunk(s.mmappedChunks[ix].ref)
	if err != nil {
		if _, ok := err.(*chunks.CorruptionErr); ok {
			panic(err)
		}
		return nil, false, err
	}
	mc := s.memChunkPool.Get().(*memChunk)
	mc.chunk = chk
	mc.minTime = s.mmappedChunks[ix].minTime
	mc.maxTime = s.mmappedChunks[ix].maxTime
	return mc, true, nil
}
~~~



##### memSeries.cutNewHeadChunk 创建新的memChunk



~~~go
func (s *memSeries) cutNewHeadChunk(mint int64, chunkDiskMapper *chunks.ChunkDiskMapper) *memChunk {
	s.mmapCurrentHeadChunk(chunkDiskMapper)

    //NewXORChunk 是啥
	s.headChunk = &memChunk{
		chunk:   chunkenc.NewXORChunk(),
		minTime: mint,
		maxTime: math.MinInt64,
	}

    //11 /8 * 8 + 8 = 16
    // (min / s.chunkRange) * s.chunkRange + s.chunkRange
	// Set upper bound on when the next chunk must be started. An earlier timestamp
	// may be chosen dynamically at a later point.
	s.nextAt = rangeForTimestamp(mint, s.chunkRange)

	app, err := s.headChunk.chunk.Appender()
	if err != nil {
		panic(err)
	}
	s.app = app
	return s.headChunk
}
~~~





##### memSeries.mmapCurrentHeadChunk 将当前的headChunk写入文件

~~~go
func (s *memSeries) mmapCurrentHeadChunk(chunkDiskMapper *chunks.ChunkDiskMapper) {
	if s.headChunk == nil {
		// There is no head chunk, so nothing to m-map here.
		return
	}

    
    //将sample数据写入文件, 更准确的说法是写入.data/chunk_head/目录下的文件中
	chunkRef, err := chunkDiskMapper.WriteChunk(s.ref, s.headChunk.minTime, s.headChunk.maxTime, s.headChunk.chunk)
	if err != nil {
		if err != chunks.ErrChunkDiskMapperClosed {
			panic(err)
		}
	}
    //保存已经写入文件的chunk
	s.mmappedChunks = append(s.mmappedChunks, &mmappedChunk{
		ref:        chunkRef,
		numSamples: uint16(s.headChunk.chunk.NumSamples()),
		minTime:    s.headChunk.minTime,
		maxTime:    s.headChunk.maxTime,
	})
}
~~~



##### memSeries.append  将sample写入chunk

headAppender.Commit 调用此函数



~~~go
// append adds the sample (t, v) to the series. The caller also has to provide
// the appendID for isolation. (The appendID can be zero, which results in no
// isolation for this append.)
// It is unsafe to call this concurrently with s.iterator(...) without holding the series lock.
func (s *memSeries) append(t int64, v float64, appendID uint64, chunkDiskMapper *chunks.ChunkDiskMapper) (sampleInOrder, chunkCreated bool) {
	// Based on Gorilla white papers this offers near-optimal compression ratio
	// so anything bigger that this has diminishing returns and increases
	// the time range within which we have to decompress all samples.
	const samplesPerChunk = 120

    //获取s.headChunk, 创建memSeries时s.headChunk是nil
	c := s.head()

	if c == nil {
		if len(s.mmappedChunks) > 0 && s.mmappedChunks[len(s.mmappedChunks)-1].maxTime >= t {
			// Out of order sample. Sample timestamp is already in the mmaped chunks, so ignore it.
			return false, false
		}
        //创建存储series对应的sample的chunk
		// There is no chunk in this series yet, create the first chunk for the sample.
		c = s.cutNewHeadChunk(t, chunkDiskMapper)
		chunkCreated = true
	}
	numSamples := c.chunk.NumSamples()

	// Out of order sample.
	if c.maxTime >= t {
		return false, chunkCreated
	}
    /*
    // computeChunkEndTime estimates the end timestamp based the beginning of a
// chunk, its current timestamp and the upper bound up to which we insert data.
// It assumes that the time range is 1/4 full.
func computeChunkEndTime(start, cur, max int64) int64 {
	a := (max - start) / ((cur - start + 1) * 4)
	if a == 0 {
		return max
	}
	return start + (max-start)/a
}
    
    */
    //为什么这么操作
    // (s.nextAt - c.minTime )/ ((c.maxTime - c.minTime + 1) * 4)
    //若s.nextAt- c.minTime 小于等于(c.maxTime -c.minTime+1)的4倍.则s.nextAt不变
    // c.minTime + (s.nextAt - c.minTime)/a
    //若超过4倍，则减小s.nextAt
	// If we reach 25% of a chunk's desired sample count, set a definitive time
	// at which to start the next chunk.
	// At latest it must happen at the timestamp set when the chunk was cut.
    //超过25% 即30个, 调用cutNewHeadChunk会设置s.nextAt
    //创建s时，s.netxtAt 是最小的64位整数
    //cutNewHeadChunk 会调整s.nextAt 为对齐s.chunkRange的下一个时间
    //c.minTime 是第一个sample的时间戳
	if numSamples == samplesPerChunk/4 {
		s.nextAt = computeChunkEndTime(c.minTime, c.maxTime, s.nextAt)
	}
    
	if t >= s.nextAt {
		c = s.cutNewHeadChunk(t, chunkDiskMapper)
		chunkCreated = true
	}
	s.app.Append(t, v)

	c.maxTime = t
	//这是什么操作
	s.sampleBuf[0] = s.sampleBuf[1]
	s.sampleBuf[1] = s.sampleBuf[2]
	s.sampleBuf[2] = s.sampleBuf[3]
	s.sampleBuf[3] = sample{t: t, v: v}

	if appendID > 0 {
		s.txs.add(appendID)
	}

	return true, chunkCreated
}
~~~

##### memSeries.appendable

headAppender.AddFast调用此函数

~~~go
// appendable checks whether the given sample is valid for appending to the series.
func (s *memSeries) appendable(t int64, v float64) error {
    //s.head 返回headChunk
	c := s.head()
	if c == nil {
		return nil
	}

	if t > c.maxTime {
		return nil
	}
	if t < c.maxTime {
		return storage.ErrOutOfOrderSample
	}
    //去除重复的sample
	// We are allowing exact duplicates as we can encounter them in valid cases
	// like federation and erroring out at that time would be extremely noisy.
	if math.Float64bits(s.sampleBuf[3].v) != math.Float64bits(v) {
		return storage.ErrDuplicateSampleForTimestamp
	}
	return nil
}
~~~



### headChunkReader

写缓存数据到硬盘时，通过headChunkReader读取缓存数据

~~~go
type headChunkReader struct {
	head       *Head
	mint, maxt int64
	isoState   *isolationState
}
~~~



##### headChunkReader.Chunk 获取chunk

~~~go
// Chunk returns the chunk for the reference number.
func (h *headChunkReader) Chunk(ref uint64) (chunkenc.Chunk, error) {
	sid, cid := unpackChunkID(ref)

    //通过series id 获取series, memSeries
	s := h.head.series.getByID(sid)
	// This means that the series has been garbage collected.
	if s == nil {
		return nil, storage.ErrNotFound
	}

	s.Lock()
	c, garbageCollect, err := s.chunk(int(cid), h.head.chunkDiskMapper)
	if err != nil {
		s.Unlock()
		return nil, err
	}
	defer func() {
		if garbageCollect {
			// Set this to nil so that Go GC can collect it after it has been used.
			c.chunk = nil
			s.memChunkPool.Put(c)
		}
	}()

	// This means that the chunk is outside the specified range.
	if !c.OverlapsClosedInterval(h.mint, h.maxt) {
		s.Unlock()
		return nil, storage.ErrNotFound
	}
	s.Unlock()

	return &safeChunk{
		Chunk:           c.chunk,
		s:               s,
		cid:             int(cid),
		isoState:        h.isoState,
		chunkDiskMapper: h.head.chunkDiskMapper,
	}, nil
}
~~~

### RangeHead 实现BlockReader接口

RangeHead实现了BlockReader接口

##### NewRangeHead

~~~go
// NewRangeHead returns a *RangeHead.
func NewRangeHead(head *Head, mint, maxt int64) *RangeHead {
	return &RangeHead{
		head: head,
		mint: mint,
		maxt: maxt,
	}
}
~~~

##### RangeHead.Index 获取作为索引的数据

LeveledCompactor.populateBlock 调用此函数

~~~go
func (h *RangeHead) Index() (IndexReader, error) {
	return h.head.indexRange(h.mint, h.maxt), nil
}
~~~



##### RangeHead.Chunks 或取数据

~~~go
func (h *RangeHead) Chunks() (ChunkReader, error) {
	return h.head.chunksRange(h.mint, h.maxt, h.head.iso.State())
}
~~~





## RefSeries、RefSample

~~~go
/ RefSeries is the series labels with the series ID.
type RefSeries struct {
	Ref    uint64
	Labels labels.Labels
}

// RefSample is a timestamp/value pair associated with a reference to a series.
type RefSample struct {
	Ref uint64
	T   int64
	V   float64
}
~~~



## isolation

isolation 是做什么的

##### isolationState

~~~go
// isolationState holds the isolation information.
type isolationState struct {
	// We will ignore all appends above the max, or that are incomplete.
	maxAppendID       uint64
	incompleteAppends map[uint64]struct{}
	lowWatermark      uint64 // Lowest of incompleteAppends/maxAppendID.
	isolation         *isolation

	// Doubly linked list of active reads.
	next *isolationState
	prev *isolationState
}
//从双链表中摘除
// Close closes the state.
func (i *isolationState) Close() {
	i.isolation.readMtx.Lock()
	defer i.isolation.readMtx.Unlock()
	i.next.prev = i.prev
	i.prev.next = i.next
}
~~~



##### isolationAppender

维护appendID

~~~go
type isolationAppender struct {
	appendID uint64
	prev     *isolationAppender
	next     *isolationAppender
}
~~~



##### isolation

~~~go

// isolation is the global isolation state.
type isolation struct {
	// Mutex for accessing lastAppendID and appendsOpen.
	appendMtx sync.RWMutex
	// Which appends are currently in progress.
	appendsOpen map[uint64]*isolationAppender
	// New appenders with higher appendID are added to the end. First element keeps lastAppendId.
	// appendsOpenList.next points to the first element and appendsOpenList.prev points to the last element.
	// If there are no appenders, both point back to appendsOpenList.
	appendsOpenList *isolationAppender
	// Pool of reusable *isolationAppender to save on allocations.
	appendersPool sync.Pool

	// Mutex for accessing readsOpen.
	// If taking both appendMtx and readMtx, take appendMtx first.
	readMtx sync.RWMutex
	// All current in use isolationStates. This is a doubly-linked list.
	readsOpen *isolationState
}

func newIsolation() *isolation {
	isoState := &isolationState{}
	isoState.next = isoState
	isoState.prev = isoState

	appender := &isolationAppender{}
	appender.next = appender
	appender.prev = appender

	return &isolation{
		appendsOpen:     map[uint64]*isolationAppender{},
		appendsOpenList: appender,
		readsOpen:       isoState,
		appendersPool:   sync.Pool{New: func() interface{} { return &isolationAppender{} }},
	}
}
~~~



##### isolation.newAppendID

~~~go
// newAppendID increments the transaction counter and returns a new transaction
// ID. The first ID returned is 1.
func (i *isolation) newAppendID() uint64 {
	i.appendMtx.Lock()
	defer i.appendMtx.Unlock()

    //appendsOpenList是双向链表的头节点
	// Last used appendID is stored in head element.
	i.appendsOpenList.appendID++

	app := i.appendersPool.Get().(*isolationAppender)
	app.appendID = i.appendsOpenList.appendID
    //双向循环链表，tail.next = head（表尾指向表头）
    //
	app.prev = i.appendsOpenList.prev
	app.next = i.appendsOpenList

	i.appendsOpenList.prev.next = app
	i.appendsOpenList.prev = app

	i.appendsOpen[app.appendID] = app
	return app.appendID
}

~~~



##### isolation.lowWatermark

~~~go
// lowWatermark returns the appendID below which we no longer need to track
// which appends were from which appendID.
func (i *isolation) lowWatermark() uint64 {
	i.appendMtx.RLock() // Take appendMtx first.
	defer i.appendMtx.RUnlock()
	i.readMtx.RLock()
	defer i.readMtx.RUnlock()
	if i.readsOpen.prev != i.readsOpen {
		return i.readsOpen.prev.lowWatermark
	}

	// Lowest appendID from appenders, or lastAppendId.
	return i.appendsOpenList.next.appendID
}
~~~



##### txRing.cleanupAppendIDsBelow

~~~
func (txr *txRing) cleanupAppendIDsBelow(bound uint64) {
	pos := txr.txIDFirst

	for txr.txIDCount > 0 {
		if txr.txIDs[pos] < bound {
			txr.txIDFirst++
			txr.txIDCount--
		} else {
			break
		}

		pos++
		if pos == len(txr.txIDs) {
			pos = 0
		}
	}

	txr.txIDFirst %= len(txr.txIDs)
}
~~~

