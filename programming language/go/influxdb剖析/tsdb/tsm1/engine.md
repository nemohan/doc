# engine

[TOC]



## 总结



### 写数据的过程

* 数据先写入缓存，然后再异步刷缓存到磁盘（根据缓存大小或刷缓存的周期)



## Engine



~~~go
// Engine represents a storage engine with compressed blocks.
type Engine struct {
	mu sync.RWMutex

	index tsdb.Index

	// The following group of fields is used to track the state of level compactions within the
	// Engine. The WaitGroup is used to monitor the compaction goroutines, the 'done' channel is
	// used to signal those goroutines to shutdown. Every request to disable level compactions will
	// call 'Wait' on 'wg', with the first goroutine to arrive (levelWorkers == 0 while holding the
	// lock) will close the done channel and re-assign 'nil' to the variable. Re-enabling will
	// decrease 'levelWorkers', and when it decreases to zero, level compactions will be started
	// back up again.

	wg           *sync.WaitGroup // waitgroup for active level compaction goroutines
	done         chan struct{}   // channel to signal level compactions to stop
	levelWorkers int             // Number of "workers" that expect compactions to be in a disabled state

	snapDone chan struct{}   // channel to signal snapshot compactions to stop
	snapWG   *sync.WaitGroup // waitgroup for running snapshot compactions

	id           uint64
	path         string
	sfile        *tsdb.SeriesFile
	logger       *zap.Logger // Logger to be used for important messages
	traceLogger  *zap.Logger // Logger to be used when trace-logging is on.
	traceLogging bool

	fieldset *tsdb.MeasurementFieldSet

	WAL            *WAL
	Cache          *Cache
	Compactor      *Compactor
	CompactionPlan CompactionPlanner
	FileStore      *FileStore

	MaxPointsPerBlock int

	// CacheFlushMemorySizeThreshold specifies the minimum size threshold for
	// the cache when the engine should write a snapshot to a TSM file
	CacheFlushMemorySizeThreshold uint64

	// CacheFlushWriteColdDuration specifies the length of time after which if
	// no writes have been committed to the WAL, the engine will write
	// a snapshot of the cache to a TSM file
	CacheFlushWriteColdDuration time.Duration

	// WALEnabled determines whether writes to the WAL are enabled.  If this is false,
	// writes will only exist in the cache and can be lost if a snapshot has not occurred.
	WALEnabled bool

	// Invoked when creating a backup file "as new".
	formatFileName FormatFileNameFunc

	// Controls whether to enabled compactions when the engine is open
	enableCompactionsOnOpen bool

	stats *EngineStatistics

	// Limiter for concurrent compactions.
	compactionLimiter limiter.Fixed

	scheduler *scheduler

	// provides access to the total set of series IDs
	seriesIDSets tsdb.SeriesIDSets

	// seriesTypeMap maps a series key to field type
	seriesTypeMap *radix.Tree

	// muDigest ensures only one goroutine can generate a digest at a time.
	muDigest sync.RWMutex
}
~~~



##### NewEngine

path 参数的值是: .influxdb/data/数据库名称/policy/shard_id

~~~go
// NewEngine returns a new instance of Engine.
func NewEngine(id uint64, idx tsdb.Index, path string, walPath string, sfile *tsdb.SeriesFile, opt tsdb.EngineOptions) tsdb.Engine {
	var wal *WAL
	if opt.WALEnabled {
		wal = NewWAL(walPath)
		wal.syncDelay = time.Duration(opt.Config.WALFsyncDelay)
	}

	fs := NewFileStore(path)
	fs.openLimiter = opt.OpenLimiter
	if opt.FileStoreObserver != nil {
		fs.WithObserver(opt.FileStoreObserver)
	}
	fs.tsmMMAPWillNeed = opt.Config.TSMWillNeed

	cache := NewCache(uint64(opt.Config.CacheMaxMemorySize))

	c := NewCompactor()
	c.Dir = path
	c.FileStore = fs
	c.RateLimit = opt.CompactionThroughputLimiter

	var planner CompactionPlanner = NewDefaultPlanner(fs, time.Duration(opt.Config.CompactFullWriteColdDuration))
	if opt.CompactionPlannerCreator != nil {
		planner = opt.CompactionPlannerCreator(opt.Config).(CompactionPlanner)
		planner.SetFileStore(fs)
	}

	logger := zap.NewNop()
	stats := &EngineStatistics{}
	e := &Engine{
		id:           id,
		path:         path,
		index:        idx,
		sfile:        sfile,
		logger:       logger,
		traceLogger:  logger,
		traceLogging: opt.Config.TraceLoggingEnabled,

		WAL:   wal,
		Cache: cache,

		FileStore:      fs,
		Compactor:      c,
		CompactionPlan: planner,

		CacheFlushMemorySizeThreshold: uint64(opt.Config.CacheSnapshotMemorySize),
		CacheFlushWriteColdDuration:   time.Duration(opt.Config.CacheSnapshotWriteColdDuration),
		enableCompactionsOnOpen:       true,
		WALEnabled:                    opt.WALEnabled,
		formatFileName:                DefaultFormatFileName,
		stats:                         stats,
		compactionLimiter:             opt.CompactionLimiter,
		scheduler:                     newScheduler(stats, opt.CompactionLimiter.Capacity()),
		seriesIDSets:                  opt.SeriesIDSets,
	}

	// Feature flag to enable per-series type checking, by default this is off and
	// e.seriesTypeMap will be nil.
	if os.Getenv("INFLUXDB_SERIES_TYPE_CHECK_ENABLED") != "" {
		e.seriesTypeMap = radix.New()
	}

	if e.traceLogging {
		fs.enableTraceLogging(true)
		if e.WALEnabled {
			e.WAL.enableTraceLogging(true)
		}
	}

	return e
}
~~~



##### Engine.Open

* 创建存储分片的目录 .influxdb/data/数据库名称/policy名称/shard_id

~~~go
// Open opens and initializes the engine.
func (e *Engine) Open() error {
	if err := os.MkdirAll(e.path, 0777); err != nil {
		return err
	}

	if err := e.cleanup(); err != nil {
		return err
	}

    //.influxdb/data/数据库名称/policy/shard_id/fields.idx
	fields, err := tsdb.NewMeasurementFieldSet(filepath.Join(e.path, "fields.idx"))
	if err != nil {
		e.logger.Warn(fmt.Sprintf("error opening fields.idx: %v.  Rebuilding.", err))
	}

	e.mu.Lock()
	e.fieldset = fields
	e.mu.Unlock()

	e.index.SetFieldSet(fields)

	if e.WALEnabled {
		if err := e.WAL.Open(); err != nil {
			return err
		}
	}

	if err := e.FileStore.Open(); err != nil {
		return err
	}

	if e.WALEnabled {
		if err := e.reloadCache(); err != nil {
			return err
		}
	}

	e.Compactor.Open()

	if e.enableCompactionsOnOpen {
		e.SetCompactionsEnabled(true)
	}

	return nil
}
~~~

### 数据查询

##### Engine.createVarRefIterator

~~~go
// createVarRefIterator creates an iterator for a variable reference.
func (e *Engine) createVarRefIterator(ctx context.Context, measurement string, opt query.IteratorOptions) ([]query.Iterator, error) {
	ref, _ := opt.Expr.(*influxql.VarRef)

	if exists, err := e.index.MeasurementExists([]byte(measurement)); err != nil {
		return nil, err
	} else if !exists {
		return nil, nil
	}

	var (
		tagSets []*query.TagSet
		err     error
	)
	if e.index.Type() == tsdb.InmemIndexName {
		ts := e.index.(indexTagSets)
		tagSets, err = ts.TagSets([]byte(measurement), opt)
	} else {
		indexSet := tsdb.IndexSet{Indexes: []tsdb.Index{e.index}, SeriesFile: e.sfile}
		tagSets, err = indexSet.TagSets(e.sfile, []byte(measurement), opt)
	}

	if err != nil {
		return nil, err
	}

	// Reverse the tag sets if we are ordering by descending.
	if !opt.Ascending {
		for _, t := range tagSets {
			t.Reverse()
		}
	}

	// Calculate tag sets and apply SLIMIT/SOFFSET.
	tagSets = query.LimitTagSets(tagSets, opt.SLimit, opt.SOffset)
	itrs := make([]query.Iterator, 0, len(tagSets))
	if err := func() error {
		for _, t := range tagSets {
			inputs, err := e.createTagSetIterators(ctx, ref, measurement, t, opt)
			if err != nil {
				return err
			} else if len(inputs) == 0 {
				continue
			}

			// If we have a LIMIT or OFFSET and the grouping of the outer query
			// is different than the current grouping, we need to perform the
			// limit on each of the individual series keys instead to improve
			// performance.
			if (opt.Limit > 0 || opt.Offset > 0) && len(opt.Dimensions) != len(opt.GroupBy) {
				for i, input := range inputs {
					inputs[i] = newLimitIterator(input, opt)
				}
			}

			itr, err := query.Iterators(inputs).Merge(opt)
			if err != nil {
				query.Iterators(inputs).Close()
				return err
			}

			// Apply a limit on the merged iterator.
			if opt.Limit > 0 || opt.Offset > 0 {
				if len(opt.Dimensions) == len(opt.GroupBy) {
					// When the final dimensions and the current grouping are
					// the same, we will only produce one series so we can use
					// the faster limit iterator.
					itr = newLimitIterator(itr, opt)
				} else {
					// When the dimensions are different than the current
					// grouping, we need to account for the possibility there
					// will be multiple series. The limit iterator in the
					// influxql package handles that scenario.
					itr = query.NewLimitIterator(itr, opt)
				}
			}
			itrs = append(itrs, itr)
		}
		return nil
	}(); err != nil {
		query.Iterators(itrs).Close()
		return nil, err
	}

	return itrs, nil
}

~~~



~~~
// createTagSetIterators creates a set of iterators for a tagset.
func (e *Engine) createTagSetIterators(ctx context.Context, ref *influxql.VarRef, name string, t *query.TagSet, opt query.IteratorOptions) ([]query.Iterator, error) {
	// Set parallelism by number of logical cpus.
	parallelism := runtime.GOMAXPROCS(0)
	if parallelism > len(t.SeriesKeys) {
		parallelism = len(t.SeriesKeys)
	}

	// Create series key groupings w/ return error.
	groups := make([]struct {
		keys    []string
		filters []influxql.Expr
		itrs    []query.Iterator
		err     error
	}, parallelism)

	// Group series keys.
	n := len(t.SeriesKeys) / parallelism
	for i := 0; i < parallelism; i++ {
		group := &groups[i]

		if i < parallelism-1 {
			group.keys = t.SeriesKeys[i*n : (i+1)*n]
			group.filters = t.Filters[i*n : (i+1)*n]
		} else {
			group.keys = t.SeriesKeys[i*n:]
			group.filters = t.Filters[i*n:]
		}
	}

	// Read series groups in parallel.
	var wg sync.WaitGroup
	for i := range groups {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			groups[i].itrs, groups[i].err = e.createTagSetGroupIterators(ctx, ref, name, groups[i].keys, t, groups[i].filters, opt)
		}(i)
	}
	wg.Wait()

	// Determine total number of iterators so we can allocate only once.
	var itrN int
	for _, group := range groups {
		itrN += len(group.itrs)
	}

	// Combine all iterators together and check for errors.
	var err error
	itrs := make([]query.Iterator, 0, itrN)
	for _, group := range groups {
		if group.err != nil {
			err = group.err
		}
		itrs = append(itrs, group.itrs...)
	}

	// If an error occurred, make sure we close all created iterators.
	if err != nil {
		query.Iterators(itrs).Close()
		return nil, err
	}

	return itrs, nil
}

// createTagSetGroupIterators creates a set of iterators for a subset of a tagset's series.
func (e *Engine) createTagSetGroupIterators(ctx context.Context, ref *influxql.VarRef, name string, seriesKeys []string, t *query.TagSet, filters []influxql.Expr, opt query.IteratorOptions) ([]query.Iterator, error) {
	itrs := make([]query.Iterator, 0, len(seriesKeys))
	for i, seriesKey := range seriesKeys {
		var conditionFields []influxql.VarRef
		if filters[i] != nil {
			// Retrieve non-time fields from this series filter and filter out tags.
			conditionFields = influxql.ExprNames(filters[i])
		}

		itr, err := e.createVarRefSeriesIterator(ctx, ref, name, seriesKey, t, filters[i], conditionFields, opt)
		if err != nil {
			return itrs, err
		} else if itr == nil {
			continue
		}
		itrs = append(itrs, itr)

		// Abort if the query was killed
		select {
		case <-opt.InterruptCh:
			query.Iterators(itrs).Close()
			return nil, query.ErrQueryInterrupted
		default:
		}

		// Enforce series limit at creation time.
		if opt.MaxSeriesN > 0 && len(itrs) > opt.MaxSeriesN {
			query.Iterators(itrs).Close()
			return nil, fmt.Errorf("max-select-series limit exceeded: (%d/%d)", len(itrs), opt.MaxSeriesN)
		}

	}
	return itrs, nil
}

// createVarRefSeriesIterator creates an iterator for a variable reference for a series.
func (e *Engine) createVarRefSeriesIterator(ctx context.Context, ref *influxql.VarRef, name string, seriesKey string, t *query.TagSet, filter influxql.Expr, conditionFields []influxql.VarRef, opt query.IteratorOptions) (query.Iterator, error) {
	_, tfs := models.ParseKey([]byte(seriesKey))
	tags := query.NewTags(tfs.Map())

	// Create options specific for this series.
	itrOpt := opt
	itrOpt.Condition = filter

	var curCounter, auxCounter, condCounter *metrics.Counter
	if col := metrics.GroupFromContext(ctx); col != nil {
		curCounter = col.GetCounter(numberOfRefCursorsCounter)
		auxCounter = col.GetCounter(numberOfAuxCursorsCounter)
		condCounter = col.GetCounter(numberOfCondCursorsCounter)
	}

	// Build main cursor.
	var cur cursor
	if ref != nil {
		cur = e.buildCursor(ctx, name, seriesKey, tfs, ref, opt)
		// If the field doesn't exist then don't build an iterator.
		if cur == nil {
			return nil, nil
		}
		if curCounter != nil {
			curCounter.Add(1)
		}
	}

	// Build auxiliary cursors.
	// Tag values should be returned if the field doesn't exist.
	var aux []cursorAt
	if len(opt.Aux) > 0 {
		aux = make([]cursorAt, len(opt.Aux))
		for i, ref := range opt.Aux {
			// Create cursor from field if a tag wasn't requested.
			if ref.Type != influxql.Tag {
				cur := e.buildCursor(ctx, name, seriesKey, tfs, &ref, opt)
				if cur != nil {
					if auxCounter != nil {
						auxCounter.Add(1)
					}
					aux[i] = newBufCursor(cur, opt.Ascending)
					continue
				}

				// If a field was requested, use a nil cursor of the requested type.
				switch ref.Type {
				case influxql.Float, influxql.AnyField:
					aux[i] = nilFloatLiteralValueCursor
					continue
				case influxql.Integer:
					aux[i] = nilIntegerLiteralValueCursor
					continue
				case influxql.Unsigned:
					aux[i] = nilUnsignedLiteralValueCursor
					continue
				case influxql.String:
					aux[i] = nilStringLiteralValueCursor
					continue
				case influxql.Boolean:
					aux[i] = nilBooleanLiteralValueCursor
					continue
				}
			}

			// If field doesn't exist, use the tag value.
			if v := tags.Value(ref.Val); v == "" {
				// However, if the tag value is blank then return a null.
				aux[i] = nilStringLiteralValueCursor
			} else {
				aux[i] = &literalValueCursor{value: v}
			}
		}
	}

	// Remove _tagKey condition field.
	// We can't seach on it because we can't join it to _tagValue based on time.
	if varRefSliceContains(conditionFields, "_tagKey") {
		conditionFields = varRefSliceRemove(conditionFields, "_tagKey")

		// Remove _tagKey conditional references from iterator.
		itrOpt.Condition = influxql.RewriteExpr(influxql.CloneExpr(itrOpt.Condition), func(expr influxql.Expr) influxql.Expr {
			switch expr := expr.(type) {
			case *influxql.BinaryExpr:
				if ref, ok := expr.LHS.(*influxql.VarRef); ok && ref.Val == "_tagKey" {
					return &influxql.BooleanLiteral{Val: true}
				}
				if ref, ok := expr.RHS.(*influxql.VarRef); ok && ref.Val == "_tagKey" {
					return &influxql.BooleanLiteral{Val: true}
				}
			}
			return expr
		})
	}

	// Build conditional field cursors.
	// If a conditional field doesn't exist then ignore the series.
	var conds []cursorAt
	if len(conditionFields) > 0 {
		conds = make([]cursorAt, len(conditionFields))
		for i, ref := range conditionFields {
			// Create cursor from field if a tag wasn't requested.
			if ref.Type != influxql.Tag {
				cur := e.buildCursor(ctx, name, seriesKey, tfs, &ref, opt)
				if cur != nil {
					if condCounter != nil {
						condCounter.Add(1)
					}
					conds[i] = newBufCursor(cur, opt.Ascending)
					continue
				}

				// If a field was requested, use a nil cursor of the requested type.
				switch ref.Type {
				case influxql.Float, influxql.AnyField:
					conds[i] = nilFloatLiteralValueCursor
					continue
				case influxql.Integer:
					conds[i] = nilIntegerLiteralValueCursor
					continue
				case influxql.Unsigned:
					conds[i] = nilUnsignedLiteralValueCursor
					continue
				case influxql.String:
					conds[i] = nilStringLiteralValueCursor
					continue
				case influxql.Boolean:
					conds[i] = nilBooleanLiteralValueCursor
					continue
				}
			}

			// If field doesn't exist, use the tag value.
			if v := tags.Value(ref.Val); v == "" {
				// However, if the tag value is blank then return a null.
				conds[i] = nilStringLiteralValueCursor
			} else {
				conds[i] = &literalValueCursor{value: v}
			}
		}
	}
	condNames := influxql.VarRefs(conditionFields).Strings()

	// Limit tags to only the dimensions selected.
	dimensions := opt.GetDimensions()
	tags = tags.Subset(dimensions)

	// If it's only auxiliary fields then it doesn't matter what type of iterator we use.
	if ref == nil {
		if opt.StripName {
			name = ""
		}
		return newFloatIterator(name, tags, itrOpt, nil, aux, conds, condNames), nil
	}

	// Remove name if requested.
	if opt.StripName {
		name = ""
	}

	switch cur := cur.(type) {
	case floatCursor:
		return newFloatIterator(name, tags, itrOpt, cur, aux, conds, condNames), nil
	case integerCursor:
		return newIntegerIterator(name, tags, itrOpt, cur, aux, conds, condNames), nil
	case unsignedCursor:
		return newUnsignedIterator(name, tags, itrOpt, cur, aux, conds, condNames), nil
	case stringCursor:
		return newStringIterator(name, tags, itrOpt, cur, aux, conds, condNames), nil
	case booleanCursor:
		return newBooleanIterator(name, tags, itrOpt, cur, aux, conds, condNames), nil
	default:
		panic("unreachable")
	}
}

~~~



### 写数据到缓存

疑问数据何时写入磁盘？刷盘异步执行，由Engine.WriteSnapshot执行

Engine.WritePointsWithContext会先将数据写入缓存和WAL日志

##### Engine.WritePointsWithContext

influxdb/tsdb/engine/tsm1/engine.go

~~~go
// WritePointsWithContext() writes metadata and point data into the engine.  It
// returns an error if new points are added to an existing key.
//
// In addition, it accepts a context.Context value. It stores write statstics
// to context values passed in of type tsdb.ContextKey. The metrics it stores
// are points written and values (fields) written.
//
// It expects int64 pointers to be stored in the tsdb.StatPointsWritten and
// tsdb.StatValuesWritten keys and will store the proper values if requested.
//
func (e *Engine) WritePointsWithContext(ctx context.Context, points []models.Point) error {
    //Value 是个接口类型
	values := make(map[string][]Value, len(points))
	var (
		keyBuf    []byte
		baseLen   int
		seriesErr error
		npoints   int64 // total points processed
		nvalues   int64 // total values (fields) processed
	)

	for _, p := range points {
		// TODO: In the future we'd like to check ctx.Err() for cancellation here.
		// Beforehand we should measure the performance impact.

        //keyBuf的内容是: key#!~#field_key
        //
		keyBuf = append(keyBuf[:0], p.Key()...)
        // keyFieldSeprator的值  #!~#
		keyBuf = append(keyBuf, keyFieldSeparator...)
		baseLen = len(keyBuf)
		iter := p.FieldIterator()
		t := p.Time().UnixNano()

		npoints++
		for iter.Next() {
			// Skip fields name "time", they are illegal
			if bytes.Equal(iter.FieldKey(), timeBytes) {
				continue
			}

            // key#!~#field_key1
            //key#!~#field_key2
			keyBuf = append(keyBuf[:baseLen], iter.FieldKey()...)

            //e.seriesTypeMap 是一个radix tree
            //由环境变量 INFLUXDB_SERIES_TYPE_CHECK_ENABLED决定是否开启
			if e.seriesTypeMap != nil {
				// Fast-path check to see if the field for the series already exists.
				if v, ok := e.seriesTypeMap.Get(keyBuf); !ok {
					if typ, err := e.Type(keyBuf); err != nil {
						// Field type is unknown, we can try to add it.
					} else if typ != iter.Type() {
						// Existing type is different from what was passed in, we need to drop
						// this write and refresh the series type map.
						seriesErr = tsdb.ErrFieldTypeConflict
						e.seriesTypeMap.Insert(keyBuf, int(typ))
						continue
					}

					// Doesn't exist, so try to insert
					vv, ok := e.seriesTypeMap.Insert(keyBuf, int(iter.Type()))

					// We didn't insert and the type that exists isn't what we tried to insert, so
					// we have a conflict and must drop this field/series.
					if !ok || vv != int(iter.Type()) {
						seriesErr = tsdb.ErrFieldTypeConflict
						continue
					}
				} else if v != int(iter.Type()) {
					// The series already exists, but with a different type.  This is also a type conflict
					// and we need to drop this field/series.
					seriesErr = tsdb.ErrFieldTypeConflict
					continue
				}
			}//end if

			var v Value
			switch iter.Type() {
			case models.Float:
				fv, err := iter.FloatValue()
				if err != nil {
					return err
				}
				v = NewFloatValue(t, fv)
			case models.Integer:
				iv, err := iter.IntegerValue()
				if err != nil {
					return err
				}
				v = NewIntegerValue(t, iv)
			case models.Unsigned:
				iv, err := iter.UnsignedValue()
				if err != nil {
					return err
				}
				v = NewUnsignedValue(t, iv)
			case models.String:
				v = NewStringValue(t, iter.StringValue())
			case models.Boolean:
				bv, err := iter.BooleanValue()
				if err != nil {
					return err
				}
				v = NewBooleanValue(t, bv)
			default:
				return fmt.Errorf("unknown field type for %s: %s", string(iter.FieldKey()), p.String())
			}

			nvalues++
			values[string(keyBuf)] = append(values[string(keyBuf)], v)
		}
	}

	e.mu.RLock()
	defer e.mu.RUnlock()

    //数据何时写磁盘
	// first try to write to the cache
	if err := e.Cache.WriteMulti(values); err != nil {
		return err
	}

    //写入WAL日志
	if e.WALEnabled {
		if _, err := e.WAL.WriteMulti(values); err != nil {
			return err
		}
	}

	// if requested, store points written stats
	if pointsWritten, ok := ctx.Value(tsdb.StatPointsWritten).(*int64); ok {
		*pointsWritten = npoints
	}

	// if requested, store values written stats
	if valuesWritten, ok := ctx.Value(tsdb.StatValuesWritten).(*int64); ok {
		*valuesWritten = nvalues
	}

	return seriesErr
}
~~~



### 数据落盘



##### Engine.SetEnabled 开启数据刷盘后台协程

~~~go
// SetEnabled sets whether the engine is enabled.
func (e *Engine) SetEnabled(enabled bool) {
	e.enableCompactionsOnOpen = enabled
	e.SetCompactionsEnabled(enabled)
}

// SetCompactionsEnabled enables compactions on the engine.  When disabled
// all running compactions are aborted and new compactions stop running.
func (e *Engine) SetCompactionsEnabled(enabled bool) {
	if enabled {
		e.enableSnapshotCompactions()
		e.enableLevelCompactions(false)
	} else {
		e.disableSnapshotCompactions()
		e.disableLevelCompactions(false)
	}
}
~~~



##### Engine.enableSnapshotCompactions 开启刷缓存协程

* 若snapDone 上次刷缓存尚未完成，直接返回
* 调用Engine.Compactor.EnableSnapshots
* 开启刷缓存的协程，调用Engine.compactCache

~~~go
func (e *Engine) enableSnapshotCompactions() {
    //已经开启缓存
	// Check if already enabled under read lock
	e.mu.RLock()
	if e.snapDone != nil {
		e.mu.RUnlock()
		return
	}
	e.mu.RUnlock()

	// Check again under write lock
	e.mu.Lock()
	if e.snapDone != nil {
		e.mu.Unlock()
		return
	}

	e.Compactor.EnableSnapshots()
	e.snapDone = make(chan struct{})
	wg := new(sync.WaitGroup)
	wg.Add(1)
	e.snapWG = wg
	e.mu.Unlock()

	go func() { defer wg.Done(); e.compactCache() }()
}
~~~



##### Engine.compactCache 定期检查WAL 和cache是否需要写入磁盘

* 设置一个每秒执行一次的ticker
* 调用Engine.ShouldCompactCache检查是否需要刷缓存，若缓存大小超过指定的值Engine.CacheFlushMemorySizeThreshold(DefaultCacheSnapshotMemorySize 25MB)。或者距上次刷盘时间超过Engine.CacheFlushWriteColdDuration(默认值: 10分钟）则执行Engine.WriteSnapshot
* 记录刷缓存的统计信息，刷缓存出错次数、刷缓存次数、刷缓存耗时



​        CacheFlushMemorySizeThreshold: uint64(opt.Config.CacheSnapshotMemorySize),

​        CacheFlushWriteColdDuration:   time.Duration(opt.Config.CacheSnapshotWriteColdDuration)

~~~go
// compactCache continually checks if the WAL cache should be written to disk.
func (e *Engine) compactCache() {
	t := time.NewTicker(time.Second)
	defer t.Stop()
	for {
		e.mu.RLock()
		quit := e.snapDone
		e.mu.RUnlock()

		select {
		case <-quit:
			return

		case <-t.C:
            //更新缓存的年龄
			e.Cache.UpdateAge()
            //超过25MB或超过10分钟,则刷缓存
			if e.ShouldCompactCache(time.Now()) {
				start := time.Now()
				e.traceLogger.Info("Compacting cache", zap.String("path", e.path))
				err := e.WriteSnapshot()
				if err != nil && err != errCompactionsDisabled {
					e.logger.Info("Error writing snapshot", zap.Error(err))
					atomic.AddInt64(&e.stats.CacheCompactionErrors, 1)
				} else {
					atomic.AddInt64(&e.stats.CacheCompactions, 1)
				}
				atomic.AddInt64(&e.stats.CacheCompactionDuration, time.Since(start).Nanoseconds())
			}
		}
	}
}
~~~





##### Engine.WriteSnapshot 写快照

* 统计写快照耗费时间
* 若开启了WAL，调用Engine.WAL.CloseSegment
* 调用Engine.Cache.Snapshot 创建快照

~~~go
// WriteSnapshot will snapshot the cache and write a new TSM file with its contents, releasing the snapshot when done.
func (e *Engine) WriteSnapshot() (err error) {
	// Lock and grab the cache snapshot along with all the closed WAL
	// filenames associated with the snapshot

	started := time.Now()
	log, logEnd := logger.NewOperation(e.logger, "Cache snapshot", "tsm1_cache_snapshot")
	defer func() {
		elapsed := time.Since(started)
		e.Cache.UpdateCompactTime(elapsed)

		if err == nil {
			log.Info("Snapshot for path written", zap.String("path", e.path), zap.Duration("duration", elapsed))
		}
		logEnd()
	}()

    //匿名函数
	closedFiles, snapshot, err := func() (segments []string, snapshot *Cache, err error) {
		e.mu.Lock()
		defer e.mu.Unlock()

		if e.WALEnabled {
			if err = e.WAL.CloseSegment(); err != nil {
				return
			}

			segments, err = e.WAL.ClosedSegments()
			if err != nil {
				return
			}
		}

		snapshot, err = e.Cache.Snapshot()
		if err != nil {
			return
		}

		return
	}()

	if err != nil {
		return err
	}

	if snapshot.Size() == 0 {
		e.Cache.ClearSnapshot(true)
		return nil
	}

	// The snapshotted cache may have duplicate points and unsorted data.  We need to deduplicate
	// it before writing the snapshot.  This can be very expensive so it's done while we are not
	// holding the engine write lock.
	dedup := time.Now()
	snapshot.Deduplicate()
	e.traceLogger.Info("Snapshot for path deduplicated",
		zap.String("path", e.path),
		zap.Duration("duration", time.Since(dedup)))

	return e.writeSnapshotAndCommit(log, closedFiles, snapshot)
}
~~~



##### Engine.writeSnapshotAndCommit

* 调用Engine.Compactor.WriteSnapshot写快照

~~~go
// writeSnapshotAndCommit will write the passed cache to a new TSM file and remove the closed WAL segments.
func (e *Engine) writeSnapshotAndCommit(log *zap.Logger, closedFiles []string, snapshot *Cache) (err error) {
	defer func() {
		if err != nil {
			e.Cache.ClearSnapshot(false)
		}
	}()

    //e.Compactor在NewEngine中调用NewCompactor初始化
	// write the new snapshot files
	newFiles, err := e.Compactor.WriteSnapshot(snapshot)
	if err != nil {
		log.Info("Error writing snapshot from compactor", zap.Error(err))
		return err
	}

	e.mu.RLock()
	defer e.mu.RUnlock()

	// update the file store with these new files
	if err := e.FileStore.Replace(nil, newFiles); err != nil {
		log.Info("Error adding new TSM files from snapshot. Removing temp files.", zap.Error(err))

		// Remove the new snapshot files. We will try again.
		for _, file := range newFiles {
			if err := os.Remove(file); err != nil {
				log.Info("Unable to remove file", zap.String("path", file), zap.Error(err))
			}
		}
		return err
	}

	// clear the snapshot from the in-memory cache, then the old WAL files
	e.Cache.ClearSnapshot(true)

	if e.WALEnabled {
		if err := e.WAL.Remove(closedFiles); err != nil {
			log.Info("Error removing closed WAL segments", zap.Error(err))
		}
	}

	return nil
}
~~~



### 索引



### 创建表

##### Engine.MeasurementFields 创建表

CreateFieldsIfNotExists定义在tsdb/shard.go中

~~~go
// MeasurementFields returns the measurement fields for a measurement.
func (e *Engine) MeasurementFields(measurement []byte) *tsdb.MeasurementFields {
	return e.fieldset.CreateFieldsIfNotExists(measurement)
}
~~~



