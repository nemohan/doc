# shard

[TOC]

shard的实现在tsdb/shard.go中



## 总结

### measurement field 文件格式

以protobuf 序列化后存储

~~~
magic("0613") | 
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
name | fields | 
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


000000  \0 006 001 003  \n   .  \n  \b   d   a   t   a   b   a   s   e
000010 022 023  \n 017   n   u   m   M   e   a   s   u   r   e   m   e
000020   n   t   s 020 002 022  \r  \n  \t   n   u   m   S   e   r   i
000030   e   s 020 002  \n   -  \n 016   t   s   m   1   _   f   i   l
000040   e   s   t   o   r   e 022  \f  \n  \b   n   u   m   F   i   l
000050   e   s 020 002 022  \r  \n  \t   d   i   s   k   B   y   t   e
000060   s 020 002  \n 221 001  \n 005   w   r   i   t   e 022  \r  \n
000070  \t   w   r   i   t   e   D   r   o   p 020 002 022 016  \n  \n
000080   w   r   i   t   e   E   r   r   o   r 020 002 022  \a  \n 003
000090   r   e   q 020 002 022 020  \n  \f   s   u   b   W   r   i   t
0000a0   e   D   r   o   p 020 002 022  \f  \n  \b   p   o   i   n   t
0000b0   R   e   q 020 002 022 020  \n  \f   w   r   i   t   e   T   i
0000c0   m   e   o   u   t 020 002 022  \v  \n  \a   w   r   i   t   e
0000d0   O   k 020 002 022 016  \n  \n   s   u   b   W   r   i   t   e
0000e0   O   k 020 002 022 021  \n  \r   p   o   i   n   t   R   e   q
0000f0   L   o   c   a   l 020 002  \n      \n 002   c   q 022  \r  \n
000100  \t   q   u   e   r   y   F   a   i   l 020 002 022  \v  \n  \a
000110   q   u   e   r   y   O   k 020 002  \n   F  \n  \n   s   u   b
000120   s   c   r   i   b   e   r 022 021  \n  \r   w   r   i   t   e
000130   F   a   i   l   u   r   e   s 020 002 022 022  \n 016   c   r
000140   e   a   t   e   F   a   i   l   u   r   e   s 020 002 022 021
000150  \n  \r   p   o   i   n   t   s   W   r   i   t   t   e   n 020
000160 002  \n 313 001  \n 005   s   h   a   r   d 022 016  \n  \n   w
000170   r   i   t   e   R   e   q   O   k 020 002 022 026  \n 022   w
000180   r   i   t   e   P   o   i   n   t   s   D   r   o   p   p   e
000190   d 020 002 022 020  \n  \f   s   e   r   i   e   s   C   r   e
0001a0   a   t   e 020 002 022 021  \n  \r   w   r   i   t   e   V   a
0001b0   l   u   e   s   O   k 020 002 022  \f  \n  \b   w   r   i   t
0001c0   e   R   e   q 020 002 022 022  \n 016   w   r   i   t   e   P
0001d0   o   i   n   t   s   E   r   r 020 002 022  \r  \n  \t   d   i
0001e0   s   k   B   y   t   e   s 020 002 022 021  \n  \r   w   r   i
0001f0   t   e   P   o   i   n   t   s   O   k 020 002 022 016  \n  \n
000200   w   r   i   t   e   B   y   t   e   s 020 002 022 017  \n  \v
000210   w   r   i   t   e   R   e   q   E   r   r 020 002 022 020  \n
000220  \f   f   i   e   l   d   s   C   r   e   a   t   e 020 002  \n
000230   v  \n  \r   q   u   e   r   y   E   x   e   c   u   t   o   r
000240 022 023  \n 017   r   e   c   o   v   e   r   e   d   P   a   n
000250   i   c   s 020 002 022 023  \n 017   q   u   e   r   y   D   u
000260   r   a   t   i   o   n   N   s 020 002 022 021  \n  \r   q   u
000270   e   r   i   e   s   A   c   t   i   v   e 020 002 022 023  \n
000280 017   q   u   e   r   i   e   s   E   x   e   c   u   t   e   d
000290 020 002 022 023  \n 017   q   u   e   r   i   e   s   F   i   n
0002a0   i   s   h   e   d 020 002  \n   \  \n  \b   t   s   m   1   _
0002b0   w   a   l 022 033  \n 027   c   u   r   r   e   n   t   S   e
0002c0   g   m   e   n   t   D   i   s   k   B   y   t   e   s 020 002
0002d0 022 030  \n 024   o   l   d   S   e   g   m   e   n   t   s   D
0002e0   i   s   k   B   y   t   e   s 020 002 022  \v  \n  \a   w   r
0002f0   i   t   e   O   k 020 002 022  \f  \n  \b   w   r   i   t   e
000300   E   r   r 020 002  \n 335 006  \n  \v   t   s   m   1   _   e
000310   n   g   i   n   e 022 032  \n 026   t   s   m   O   p   t   i
000320   m   i   z   e   C   o   m   p   a   c   t   i   o   n   s 020
000330 002 022 035  \n 031   t   s   m   F   u   l   l   C   o   m   p
000340   a   c   t   i   o   n   D   u   r   a   t   i   o   n 020 002
000350 022 026  \n 022   t   s   m   F   u   l   l   C   o   m   p   a
000360   c   t   i   o   n   s 020 002 022 024  \n 020   c   a   c   h
000370   e   C   o   m   p   a   c   t   i   o   n   s 020 002 022 030
000380  \n 024   t   s   m   L   e   v   e   l   2   C   o   m   p   a
000390   c   t   i   o   n   s 020 002 022 036  \n 032   t   s   m   O
0003a0   p   t   i   m   i   z   e   C   o   m   p   a   c   t   i   o
0003b0   n   Q   u   e   u   e 020 002 022 034  \n 030   t   s   m   L
0003c0   e   v   e   l   2   C   o   m   p   a   c   t   i   o   n   Q
0003d0   u   e   u   e 020 002 022 026  \n 022   c   a   c   h   e   C
0003e0   o   m   p   a   c   t   i   o   n   E   r   r 020 002 022 032
0003f0  \n 026   c   a   c   h   e   C   o   m   p   a   c   t   i   o
000400   n   s   A   c   t   i   v   e 020 002 022 032  \n 026   t   s
000410   m   L   e   v   e   l   2   C   o   m   p   a   c   t   i   o
000420   n   E   r   r 020 002 022 034  \n 030   t   s   m   L   e   v
000430   e   l   3   C   o   m   p   a   c   t   i   o   n   Q   u   e
000440   u   e 020 002 022 030  \n 024   t   s   m   L   e   v   e   l
000450   3   C   o   m   p   a   c   t   i   o   n   s 020 002 022 032
000460  \n 026   t   s   m   L   e   v   e   l   3   C   o   m   p   a
000470   c   t   i   o   n   E   r   r 020 002 022      \n 034   t   s
000480   m   O   p   t   i   m   i   z   e   C   o   m   p   a   c   t
000490   i   o   n   s   A   c   t   i   v   e 020 002 022 036  \n 032
0004a0   t   s   m   L   e   v   e   l   2   C   o   m   p   a   c   t
0004b0   i   o   n   s   A   c   t   i   v   e 020 002 022 030  \n 024
0004c0   t   s   m   F   u   l   l   C   o   m   p   a   c   t   i   o
0004d0   n   E   r   r 020 002 022 037  \n 033   t   s   m   L   e   v
0004e0   e   l   2   C   o   m   p   a   c   t   i   o   n   D   u   r
0004f0   a   t   i   o   n 020 002 022 032  \n 026   t   s   m   L   e
000500   v   e   l   1   C   o   m   p   a   c   t   i   o   n   E   r
000510   r 020 002 022 033  \n 027   c   a   c   h   e   C   o   m   p
000520   a   c   t   i   o   n   D   u   r   a   t   i   o   n 020 002
000530 022 034  \n 030   t   s   m   L   e   v   e   l   1   C   o   m
000540   p   a   c   t   i   o   n   Q   u   e   u   e 020 002 022 034
000550  \n 030   t   s   m   O   p   t   i   m   i   z   e   C   o   m
000560   p   a   c   t   i   o   n   E   r   r 020 002 022 036  \n 032
000570   t   s   m   L   e   v   e   l   3   C   o   m   p   a   c   t
000580   i   o   n   s   A   c   t   i   v   e 020 002 022 037  \n 033
000590   t   s   m   L   e   v   e   l   1   C   o   m   p   a   c   t
0005a0   i   o   n   D   u   r   a   t   i   o   n 020 002 022 034  \n
0005b0 030   t   s   m   F   u   l   l   C   o   m   p   a   c   t   i
0005c0   o   n   s   A   c   t   i   v   e 020 002 022 030  \n 024   t
0005d0   s   m   L   e   v   e   l   1   C   o   m   p   a   c   t   i
0005e0   o   n   s 020 002 022 037  \n 033   t   s   m   L   e   v   e
0005f0   l   3   C   o   m   p   a   c   t   i   o   n   D   u   r   a
000600   t   i   o   n 020 002 022 036  \n 032   t   s   m   L   e   v
000610   e   l   1   C   o   m   p   a   c   t   i   o   n   s   A   c
000620   t   i   v   e 020 002 022 032  \n 026   t   s   m   F   u   l
000630   l   C   o   m   p   a   c   t   i   o   n   Q   u   e   u   e
000640 020 002 022   !  \n 035   t   s   m   O   p   t   i   m   i   z
000650   e   C   o   m   p   a   c   t   i   o   n   D   u   r   a   t
000660   i   o   n 020 002  \n 243 001  \n  \n   t   s   m   1   _   c
000670   a   c   h   e 022 027  \n 023   W   A   L   C   o   m   p   a
000680   c   t   i   o   n   T   i   m   e   M   s 020 002 022  \v  \n
000690  \a   w   r   i   t   e   O   k 020 002 022 016  \n  \n   c   a
0006a0   c   h   e   A   g   e   M   s 020 002 022  \f  \n  \b   m   e
0006b0   m   B   y   t   e   s 020 002 022 021  \n  \r   s   n   a   p
0006c0   s   h   o   t   C   o   u   n   t 020 002 022 017  \n  \v   c
0006d0   a   c   h   e   d   B   y   t   e   s 020 002 022  \f  \n  \b
0006e0   w   r   i   t   e   E   r   r 020 002 022  \r  \n  \t   d   i
0006f0   s   k   B   y   t   e   s 020 002 022 020  \n  \f   w   r   i
000700   t   e   D   r   o   p   p   e   d 020 002  \n 335 001  \n  \a
000710   r   u   n   t   i   m   e 022  \v  \n  \a   H   e   a   p   S
000720   y   s 020 002 022 016  \n  \n   T   o   t   a   l   A   l   l
000730   o   c 020 002 022  \r  \n  \t   H   e   a   p   I   n   U   s
000740   e 020 002 022 020  \n  \f   N   u   m   G   o   r   o   u   t
000750   i   n   e 020 002 022  \t  \n 005   A   l   l   o   c 020 002
000760 022  \f  \n  \b   H   e   a   p   I   d   l   e 020 002 022 017
000770  \n  \v   H   e   a   p   O   b   j   e   c   t   s 020 002 022
000780  \a  \n 003   S   y   s 020 002 022 020  \n  \f   H   e   a   p
000790   R   e   l   e   a   s   e   d 020 002 022  \v  \n  \a   M   a
0007a0   l   l   o   c   s 020 002 022 020  \n  \f   P   a   u   s   e
0007b0   T   o   t   a   l   N   s 020 002 022  \v  \n  \a   L   o   o
0007c0   k   u   p   s 020 002 022  \r  \n  \t   H   e   a   p   A   l
0007d0   l   o   c 020 002 022  \t  \n 005   N   u   m   G   C 020 002
0007e0 022  \t  \n 005   F   r   e   e   s 020 002  \n 306 003  \n 005
0007f0   h   t   t   p   d 022 032  \n 026   f   l   u   x   Q   u   e
000800   r   y   R   e   q   D   u   r   a   t   i   o   n   N   s 020
000810 002 022 022  \n 016   q   u   e   r   y   R   e   s   p   B   y
000820   t   e   s 020 002 022 020  \n  \f   f   l   u   x   Q   u   e
000830   r   y   R   e   q 020 002 022 025  \n 021   p   o   i   n   t
000840   s   W   r   i   t   t   e   n   F   a   i   l 020 002 022  \f
000850  \n  \b   q   u   e   r   y   R   e   q 020 002 022 017  \n  \v
000860   c   l   i   e   n   t   E   r   r   o   r 020 002 022 021  \n
000870  \r   r   e   q   D   u   r   a   t   i   o   n   N   s 020 002
000880 022 023  \n 017   r   e   c   o   v   e   r   e   d   P   a   n
000890   i   c   s 020 002 022  \r  \n  \t   s   t   a   t   u   s   R
0008a0   e   q 020 002 022 022  \n 016   w   r   i   t   e   R   e   q
0008b0   A   c   t   i   v   e 020 002 022 026  \n 022   w   r   i   t
0008c0   e   R   e   q   D   u   r   a   t   i   o   n   N   s 020 002
0008d0 022 020  \n  \f   p   r   o   m   W   r   i   t   e   R   e   q
0008e0 020 002 022 023  \n 017   p   o   i   n   t   s   W   r   i   t
0008f0   t   e   n   O   K 020 002 022  \v  \n  \a   p   i   n   g   R
000900   e   q 020 002 022  \f  \n  \b   a   u   t   h   F   a   i   l
000910 020 002 022 023  \n 017   v   a   l   u   e   s   W   r   i   t
000920   t   e   n   O   K 020 002 022 017  \n  \v   s   e   r   v   e
000930   r   E   r   r   o   r 020 002 022 030  \n 024   p   o   i   n
000940   t   s   W   r   i   t   t   e   n   D   r   o   p   p   e   d
000950 020 002 022  \f  \n  \b   w   r   i   t   e   R   e   q 020 002
000960 022 021  \n  \r   w   r   i   t   e   R   e   q   B   y   t   e
000970   s 020 002 022 017  \n  \v   p   r   o   m   R   e   a   d   R
000980   e   q 020 002 022  \r  \n  \t   r   e   q   A   c   t   i   v
000990   e 020 002 022 026  \n 022   q   u   e   r   y   R   e   q   D
0009a0   u   r   a   t   i   o   n   N   s 020 002 022  \a  \n 003   r
0009b0   e   q 020 002
0009b4
~~~



### field 类型

* Unknown 0
* float 1
* integer 2
* string 3
* boolean 4
* time 5
* duration 6
* tag 7
* any 8
* unsigned 9



## shard

tsdp/shard.go

##### Shard的定义

~~~go
// Shard represents a self-contained time series database. An inverted index of
// the measurement and tag data is kept along with the raw time series data.
// Data can be split across many shards. The query engine in TSDB is responsible
// for combining the output of many shards into a single query result.
type Shard struct {
	path    string //influxdb/data/数据库名称/policy/shard_id
	walPath string
	id      uint64

	database        string
	retentionPolicy string

	sfile   *SeriesFile
	options EngineOptions

	mu      sync.RWMutex
	_engine Engine
	index   Index
	enabled bool

	// expvar-based stats.
	stats       *ShardStatistics
	defaultTags models.StatisticTags

	baseLogger *zap.Logger
	logger     *zap.Logger

	EnableOnOpen bool

	// CompactionDisabled specifies the shard should not schedule compactions.
	// This option is intended for offline tooling.
	CompactionDisabled bool
}
~~~



##### NewShard

参数:

* path influxdb/data/数据库名称/policy/shard_id
* walPath influxdb/wal/数据库名称/policy/shard_id

~~~go
// NewShard returns a new initialized Shard. walPath doesn't apply to the b1 type index
func NewShard(id uint64, path string, walPath string, sfile *SeriesFile, opt EngineOptions) *Shard {
	db, rp := decodeStorePath(path)
	logger := zap.NewNop()
	if opt.FieldValidator == nil {
		opt.FieldValidator = defaultFieldValidator{}
	}

	s := &Shard{
		id:      id,
		path:    path,
		walPath: walPath,
		sfile:   sfile,
		options: opt,

		stats: &ShardStatistics{},
		defaultTags: models.StatisticTags{
			"path":            path,
			"walPath":         walPath,
			"id":              fmt.Sprintf("%d", id),
			"database":        db,
			"retentionPolicy": rp,
			"engine":          opt.EngineVersion,
		},

		database:        db,
		retentionPolicy: rp,

		logger:       logger,
		baseLogger:   logger,
		EnableOnOpen: true,
	}
	return s
}
~~~



##### Shard.Open

tsdb/shard.go

* 调用NewIndex(定义在tsdb/index.go)创建索引
* 调用NewEngine(定义在tsdb/engine.go)初始化存储引擎

~~~go
// Open initializes and opens the shard's store.
func (s *Shard) Open() error {
	if err := func() error {
		s.mu.Lock()
		defer s.mu.Unlock()

		// Return if the shard is already open
		if s._engine != nil {
			return nil
		}

		seriesIDSet := NewSeriesIDSet()

        //.influxdb/data/数据库/policy/shard_id/index 索引文件名称
		// Initialize underlying index.
		ipath := filepath.Join(s.path, "index")
        
        //根据EngineOption.IndexVersion确定是inmem 索引还是tsi1索引
        //对inmem类型的索引来说，实际调用的是NewShardIndex, 实际用到的参数只有 s.id, seriesIDSet、s.options
        //对tsi1类型索引来说，实际用到的参数是 ipath, s.sfile, s.options
		idx, err := NewIndex(s.id, s.database, ipath, seriesIDSet, s.sfile, s.options)
		if err != nil {
			return err
		}

		idx.WithLogger(s.baseLogger)

        //对inmem idx来说，idx.Open实际无操作
		// Open index.
		if err := idx.Open(); err != nil {
			return err
		}
		s.index = idx

        //目前是tsm1 engine
		// Initialize underlying engine.
		e, err := NewEngine(s.id, idx, s.path, s.walPath, s.sfile, s.options)
		if err != nil {
			return err
		}

		// Set log output on the engine.
		e.WithLogger(s.baseLogger)

		// Disable compactions while loading the index
		e.SetEnabled(false)

		// Open engine.
		if err := e.Open(); err != nil {
			return err
		}

        //做了啥还没分析
		// Load metadata index for the inmem index only.
		if err := e.LoadMetadataIndex(s.id, s.index); err != nil {
			return err
		}
		s._engine = e

		return nil
	}(); err != nil {
		s.close()
		return NewShardError(s.id, err)
	}

	if s.EnableOnOpen {
		// enable writes, queries and compactions
		s.SetEnabled(true)
	}

	return nil
}
~~~



### 写数据



##### Shard.WritePointsWithContext

* 调用Shard.validateSeriesAndFields，将series写入磁盘并为其创建索引
* 调用Shard.createFieldsAndMeasurements 创建表或添加列(field)
* 调用engine.WritePointsWithContext写数据

~~~go
// WritePointsWithContext() will write the raw data points and any new metadata
// to the index in the shard.
//
// If a context key of type ConetextKey is passed in, WritePointsWithContext()
// will store points written stats into the int64 pointer associated with
// StatPointsWritten and the number of values written in the int64 pointer
// stored in the StatValuesWritten context values.
//
func (s *Shard) WritePointsWithContext(ctx context.Context, points []models.Point) error {
	s.mu.RLock()
	defer s.mu.RUnlock()

	engine, err := s.engineNoLock()
	if err != nil {
		return err
	}

	var writeError error
	atomic.AddInt64(&s.stats.WriteReq, 1)

	points, fieldsToCreate, err := s.validateSeriesAndFields(points)
	if err != nil {
		if _, ok := err.(PartialWriteError); !ok {
			return err
		}
		// There was a partial write (points dropped), hold onto the error to return
		// to the caller, but continue on writing the remaining points.
		writeError = err
	}
	atomic.AddInt64(&s.stats.FieldsCreated, int64(len(fieldsToCreate)))

	// add any new fields and keep track of what needs to be saved
	if err := s.createFieldsAndMeasurements(fieldsToCreate); err != nil {
		return err
	}

	// see if our engine is capable of WritePointsWithContext
	type contextWriter interface {
		WritePointsWithContext(context.Context, []models.Point) error
	}
	switch eng := engine.(type) {
	case contextWriter:
		if err := eng.WritePointsWithContext(ctx, points); err != nil {
			atomic.AddInt64(&s.stats.WritePointsErr, int64(len(points)))
			atomic.AddInt64(&s.stats.WriteReqErr, 1)
			return fmt.Errorf("engine: %s", err)
		}
	default:
		// Write to the engine.
		if err := engine.WritePoints(points); err != nil {
			atomic.AddInt64(&s.stats.WritePointsErr, int64(len(points)))
			atomic.AddInt64(&s.stats.WriteReqErr, 1)
			return fmt.Errorf("engine: %s", err)
		}
	}

	// increment the number OK write requests
	atomic.AddInt64(&s.stats.WriteReqOK, 1)

	// Increment the number of points written.  If was a StatPointsWritten
	// request is sent to this function via a context, use the value that the
	// engine reported.  otherwise, use the length of our points slice.
	if npoints, ok := ctx.Value(StatPointsWritten).(*int64); ok {
		// use engine counted points
		atomic.AddInt64(&s.stats.WritePointsOK, *npoints)
	} else {
		// fallback to assuming that len(points) is accurate
		atomic.AddInt64(&s.stats.WritePointsOK, int64(len(points)))
	}

	// Increment the number of values stored if available
	if nvalues, ok := ctx.Value(StatValuesWritten).(*int64); ok {
		atomic.AddInt64(&s.stats.WriteValuesOK, *nvalues)
	}

	return writeError
}

~~~



### 创建series及其索引

##### Shard.validateSeriesAndFields 校验tags 并为series创建索引

* 校验tags并为series创建索引
* 校验fields

~~~go
// validateSeriesAndFields checks which series and fields are new and whose metadata should be saved and indexed.
func (s *Shard) validateSeriesAndFields(points []models.Point) ([]models.Point, []*FieldCreate, error) {
	var (
		fieldsToCreate []*FieldCreate
		err            error
		dropped        int
		reason         string // only first error reason is set unless returned from CreateSeriesListIfNotExists
	)

	// Create all series against the index in bulk.
	keys := make([][]byte, len(points))
	names := make([][]byte, len(points))
	tagsSlice := make([]models.Tags, len(points))

	// Check if keys should be unicode validated.
	validateKeys := s.options.Config.ValidateKeys

	var j int
	for i, p := range points {
        //返回
		tags := p.Tags()

        //丢弃含有time tag的point
        //timeBytes 的值是 []byte("time")
		// Drop any series w/ a "time" tag, these are illegal
		if v := tags.Get(timeBytes); v != nil {
			dropped++
			if reason == "" {
				reason = fmt.Sprintf(
					"invalid tag key: input tag \"%s\" on measurement \"%s\" is invalid",
					"time", string(p.Name()))
			}
			continue
		}

		// Drop any series with invalid unicode characters in the key.
		if validateKeys && !models.ValidKeyTokens(string(p.Name()), tags) {
			dropped++
			if reason == "" {
				reason = fmt.Sprintf("key contains invalid unicode: \"%s\"", string(p.Key()))
			}
			continue
		}

		keys[j] = p.Key()
		names[j] = p.Name() //measurement name
		tagsSlice[j] = tags
		points[j] = points[i]
		j++
	}
	points, keys, names, tagsSlice = points[:j], keys[:j], names[:j], tagsSlice[:j]

	engine, err := s.engineNoLock()
	if err != nil {
		return nil, nil, err
	}

	// Add new series. Check for partial writes.
	var droppedKeys [][]byte
    //engine.CreateSeriesListIfNotExists 实际调用的是tsdb.Index.CreateSeriesListIfNotExists
    //而Engine.Index实际在shard.Open时调用NewIndex创建
	if err := engine.CreateSeriesListIfNotExists(keys, names, tagsSlice); err != nil {
		switch err := err.(type) {
		// TODO(jmw): why is this a *PartialWriteError when everything else is not a pointer?
		// Maybe we can just change it to be consistent if we change it also in all
		// the places that construct it.
		case *PartialWriteError:
			reason = err.Reason
			dropped += err.Dropped
			droppedKeys = err.DroppedKeys
			atomic.AddInt64(&s.stats.WritePointsDropped, int64(err.Dropped))
		default:
			return nil, nil, err
		}
	}

	j = 0
	for i, p := range points {
		// Skip any points with only invalid fields.
		iter := p.FieldIterator()
		validField := false
		for iter.Next() {
			if bytes.Equal(iter.FieldKey(), timeBytes) {
				continue
			}
			validField = true
			break
		}
		if !validField {
			if reason == "" {
				reason = fmt.Sprintf(
					"invalid field name: input field \"%s\" on measurement \"%s\" is invalid",
					"time", string(p.Name()))
			}
			dropped++
			continue
		}

		// Skip any points whos keys have been dropped. Dropped has already been incremented for them.
		if len(droppedKeys) > 0 && bytesutil.Contains(droppedKeys, keys[i]) {
			continue
		}

		name := p.Name()
		mf := engine.MeasurementFields(name)

		// Check with the field validator.
		if err := s.options.FieldValidator.Validate(mf, p); err != nil {
			switch err := err.(type) {
			case PartialWriteError:
				if reason == "" {
					reason = err.Reason
				}
				dropped += err.Dropped
				atomic.AddInt64(&s.stats.WritePointsDropped, int64(err.Dropped))
			default:
				return nil, nil, err
			}
			continue
		}

		points[j] = points[i]
		j++

		// Create any fields that are missing.
		iter.Reset()
		for iter.Next() {
			fieldKey := iter.FieldKey()

			// Skip fields named "time". They are illegal.
			if bytes.Equal(fieldKey, timeBytes) {
				continue
			}

            //field 是否存在,存在则跳过
			if mf.FieldBytes(fieldKey) != nil {
				continue
			}

			dataType := dataTypeFromModelsFieldType(iter.Type())
			if dataType == influxql.Unknown {
				continue
			}

			fieldsToCreate = append(fieldsToCreate, &FieldCreate{
				Measurement: name,
				Field: &Field{
					Name: string(fieldKey),
					Type: dataType,
				},
			})
		}
	}

	if dropped > 0 {
		err = PartialWriteError{Reason: reason, Dropped: dropped}
	}

	return points[:j], fieldsToCreate, err
}
~~~



##### Shard.createFieldsAndMeasurements 创建表结构或添加列(field)

写数据时触发

* 检查是否有需要添加的列(field)，若没有则返回
* 调用CreateFiledIfNotExists创建
* 保存新的表结构

~~~go
func (s *Shard) createFieldsAndMeasurements(fieldsToCreate []*FieldCreate) error {
	if len(fieldsToCreate) == 0 {
		return nil
	}

	engine, err := s.engineNoLock()
	if err != nil {
		return err
	}

	// add fields
	for _, f := range fieldsToCreate {
        //MeasurementFields可能会创建表
		mf := engine.MeasurementFields(f.Measurement)
		if err := mf.CreateFieldIfNotExists([]byte(f.Field.Name), f.Field.Type); err != nil {
			return err
		}

		s.index.SetFieldName(f.Measurement, f.Field.Name)
	}

    //保存表结构
	if len(fieldsToCreate) > 0 {
		return engine.MeasurementFieldSet().Save()
	}

	return nil
}
~~~



## MeasurementFields 表结构的内存表示

### Field 列的表示

~~~go
// Field represents a series field. All of the fields must be hashable.
type Field struct {
	ID   uint8             `json:"id,omitempty"`
	Name string            `json:"name,omitempty"`
	Type influxql.DataType `json:"type,omitempty"`
}
~~~



##### MeasurementFields的定义, MeasurementFields对应表的所有列

定义在tsdb/shard.go

~~~go
// MeasurementFields holds the fields of a measurement and their codec.
type MeasurementFields struct {
	mu sync.Mutex

	fields atomic.Value // map[string]*Field
}
~~~



##### MeasurementFields.CreateFieldIfNotExists 创建 Field(表中的列)

~~~go
// CreateFieldIfNotExists creates a new field with an autoincrementing ID.
// Returns an error if 255 fields have already been created on the measurement or
// the fields already exists with a different type.
func (m *MeasurementFields) CreateFieldIfNotExists(name []byte, typ influxql.DataType) error {
	fields := m.fields.Load().(map[string]*Field)

	// Ignore if the field already exists.
	if f := fields[string(name)]; f != nil {
		if f.Type != typ {
			return ErrFieldTypeConflict
		}
		return nil
	}

	m.mu.Lock()
	defer m.mu.Unlock()

	fields = m.fields.Load().(map[string]*Field)
	// Re-check field and type under write lock.
	if f := fields[string(name)]; f != nil {
		if f.Type != typ {
			return ErrFieldTypeConflict
		}
		return nil
	}

    
	fieldsUpdate := make(map[string]*Field, len(fields)+1)
	for k, v := range fields {
		fieldsUpdate[k] = v
	}
	// Create and append a new field.
	f := &Field{
		ID:   uint8(len(fields) + 1),
		Name: string(name),
		Type: typ,
	}
	fieldsUpdate[string(name)] = f
	m.fields.Store(fieldsUpdate)

	return nil
}
~~~



### MeasurementFieldSet 表结构的内存表示

定义在tsdb/shard.go中

~~~go
// MeasurementFieldSet represents a collection of fields by measurement.
// This safe for concurrent use.
type MeasurementFieldSet struct {
	mu     sync.RWMutex
	fields map[string]*MeasurementFields

	// path is the location to persist field sets
	path string
}
~~~



##### NewMeasurementFieldSet 



path: .influxdb/data/数据库/policy/shard_id/fields.idx

~~~go
// NewMeasurementFieldSet returns a new instance of MeasurementFieldSet.
func NewMeasurementFieldSet(path string) (*MeasurementFieldSet, error) {
	fs := &MeasurementFieldSet{
		fields: make(map[string]*MeasurementFields),
		path:   path,
	}

	// If there is a load error, return the error and an empty set so
	// it can be rebuild manually.
	return fs, fs.load()
}
~~~



##### MeasurementFieldSet.load 加载表结构数据

~~~go
func (fs *MeasurementFieldSet) load() error {
	fs.mu.Lock()
	defer fs.mu.Unlock()

	fd, err := os.Open(fs.path)
	if os.IsNotExist(err) {
		return nil
	} else if err != nil {
		return err
	}
	defer fd.Close()

	var magic [4]byte
	if _, err := fd.Read(magic[:]); err != nil {
		return err
	}

	if !bytes.Equal(magic[:], fieldsIndexMagicNumber) {
		return ErrUnknownFieldsFormat
	}

	var pb internal.MeasurementFieldSet
	b, err := ioutil.ReadAll(fd)
	if err != nil {
		return err
	}

	if err := proto.Unmarshal(b, &pb); err != nil {
		return err
	}

	fs.fields = make(map[string]*MeasurementFields, len(pb.GetMeasurements()))
	for _, measurement := range pb.GetMeasurements() {
		fields := make(map[string]*Field, len(measurement.GetFields()))
		for _, field := range measurement.GetFields() {
			fields[string(field.GetName())] = &Field{Name: string(field.GetName()), Type: influxql.DataType(field.GetType())}
		}
		set := &MeasurementFields{}
		set.fields.Store(fields)
		fs.fields[string(measurement.GetName())] = set
	}
	return nil
}
~~~



##### MeasurementFieldSet.CreateFieldsIfNotExists 创建表

~~~go
// CreateFieldsIfNotExists returns fields for a measurement by name.
func (fs *MeasurementFieldSet) CreateFieldsIfNotExists(name []byte) *MeasurementFields {
	fs.mu.RLock()
	mf := fs.fields[string(name)]
	fs.mu.RUnlock()

	if mf != nil {
		return mf
	}

	fs.mu.Lock()
	mf = fs.fields[string(name)]
	if mf == nil {
		mf = NewMeasurementFields()
		fs.fields[string(name)] = mf
	}
	fs.mu.Unlock()
	return mf
}
~~~



##### MeasurementFieldSet.Save 保存表结构



~~~go

func (fs *MeasurementFieldSet) Save() error {
	fs.mu.Lock()
	defer fs.mu.Unlock()

	return fs.saveNoLock()
}

func (fs *MeasurementFieldSet) saveNoLock() error {
	// No fields left, remove the fields index file
	if len(fs.fields) == 0 {
		return os.RemoveAll(fs.path)
	}

	// Write the new index to a temp file and rename when it's sync'd
	path := fs.path + ".tmp"
	fd, err := os.OpenFile(path, os.O_CREATE|os.O_RDWR|os.O_EXCL|os.O_SYNC, 0666)
	if err != nil {
		return err
	}
	defer os.RemoveAll(path)

	if _, err := fd.Write(fieldsIndexMagicNumber); err != nil {
		return err
	}

	pb := internal.MeasurementFieldSet{
		Measurements: make([]*internal.MeasurementFields, 0, len(fs.fields)),
	}
	for name, mf := range fs.fields {
		fs := &internal.MeasurementFields{
			Name:   []byte(name),
			Fields: make([]*internal.Field, 0, mf.FieldN()),
		}

		mf.ForEachField(func(field string, typ influxql.DataType) bool {
			fs.Fields = append(fs.Fields, &internal.Field{Name: []byte(field), Type: int32(typ)})
			return true
		})

		pb.Measurements = append(pb.Measurements, fs)
	}

	b, err := proto.Marshal(&pb)
	if err != nil {
		return err
	}

	if _, err := fd.Write(b); err != nil {
		return err
	}

	if err = fd.Sync(); err != nil {
		return err
	}

	//close file handle before renaming to support Windows
	if err = fd.Close(); err != nil {
		return err
	}

	if err := file.RenameFile(path, fs.path); err != nil {
		return err
	}

	return file.SyncDir(filepath.Dir(fs.path))
}
~~~



## SeriesIDSet

定义在tsdb/series_set.go中

~~~go
// SeriesIDSet represents a lockable bitmap of series ids.
type SeriesIDSet struct {
	sync.RWMutex
	bitmap *roaring.Bitmap
}

// NewSeriesIDSet returns a new instance of SeriesIDSet.
func NewSeriesIDSet(a ...uint64) *SeriesIDSet {
	ss := &SeriesIDSet{bitmap: roaring.NewBitmap()}
	if len(a) > 0 {
		a32 := make([]uint32, len(a))
		for i := range a {
			a32[i] = uint32(a[i])
		}
		ss.bitmap.AddMany(a32)
	}
	return ss
}
~~~

