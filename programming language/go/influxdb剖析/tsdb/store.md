# store

[TOC]

| 目录                                                 | 用途                                                         | 类型                |
| ---------------------------------------------------- | ------------------------------------------------------------ | ------------------- |
| .influxdb/data目录结构                               |                                                              |                     |
| ./influxdb/data                                      | 数据存放路径                                                 |                     |
| ./influxdb/data/数据库名称/policy                    | 每个持久化策略一个目录                                       |                     |
| .influxdb/data/数据库名称/policy/shard_id            | 每个分片一个目录                                             | tsdb/engine模块创建 |
| .influxdb/data/数据库名称/policy名称/shard_id/index  | 分片对应的索引文件                                           | 文件                |
| .influxdb/data/数据库名称/policy/shard_id/fields.idx | 存放表结构的文件                                             | 文件                |
|                                                      |                                                              |                     |
| .influxdb/data/数据库名称/_series                    | 未知                                                         |                     |
| .influxdb/data/数据库名称/_series/partition_id       | 分片目录对应SeriesPartion                                    | 目录                |
| .influxdb/data/数据库名称/_series/partition_id/0000  | 对应SeriesSegmenet,存放序列化后的series                      | 文件                |
| .influxdb/data/数据库名称/_series/partition_id/index | 索引文件, index和SeriesSegment的关系是啥。这个index文件记录的是series在SeriesSegment管理的文件中的位置 | 文件                |
|                                                      |                                                              |                     |
| WAL 目录结构                                         |                                                              |                     |
| .influxdb/wal/数据库名称/policy/shardid              | wal存放目录                                                  |                     |





![1611586566042](${img}/1611586566042.png)





大致的存储结构：



Store实现了TSDBStore接口，提供CreateShard和WriteToShard接口。coordinator包会使用Store提供的接口



## 总结

索引和SeriesFile的关系



#### .influxdb/data/数据库名称/_series/partition_id/index series 的索引文件格式

一个index文件索引整个partition。series的索引是以hash map形式实现。写入文件的内容也是两个哈希表

第一个哈希表: key_id_map   key: series(由叫做key，由measurement name 和tags组成) value: key的id,这个id仅是一个序列号并非哈希值

第二个哈希表: if_offset_map key: series的哈希值(id)  value: series 在文件中的位置

~~~
magic(4字节 SIDX)		   | version (1字节)
________________________________________________________
max_series_id 			| max offset
________________________________________
count 					| capacity
____________________________________________________________________
key_id_map.offset 		| key_id_map.size
_____________________________________________
id_offset_map.offset	| id_offset_map.size

~~~



#### .influxdb/data/数据库名称/_series/partition_id/0000 存放series的文件格式

#### series的格式

~~~
flag(1字节)|id(8字节)|size|measurement name长度(2字节)|name|tag数量|key长度(2字节)|key| value长度(2字节)|value|key2长度|key2...
~~~



~~~
magic(4字节 SSGE)		|	version(1字节)
____________________________________
series
___________________________________
series
~~~



### 索引

在写入数据的过程中，会为series（由measurement 名称和tags)建立索引。并将每个series写入路径.influxdb/data/数据库/\_series/partition_id/0000的文件，同时每个series在上述文件中的位置及id会写入另一个文件.influxdb/data/数据库/_series/partition_id/index文件





## Store

##### Store的定义

~~~go
// Store manages shards and indexes for databases.
type Store struct {
	mu                sync.RWMutex
	shards            map[uint64]*Shard
	databases         map[string]*databaseState
	sfiles            map[string]*SeriesFile
	SeriesFileMaxSize int64 // Determines size of series file mmap. Can be altered in tests.
	path              string //默认路径是 ~/.influxdb/data

	// shared per-database indexes, only if using "inmem".
	indexes map[string]interface{}

	// Maintains a set of shards that are in the process of deletion.
	// This prevents new shards from being created while old ones are being deleted.
	pendingShardDeletes map[uint64]struct{}

	// Epoch tracker helps serialize writes and deletes that may conflict. It
	// is stored by shard.
	epochs map[uint64]*epochTracker

	EngineOptions EngineOptions

	baseLogger *zap.Logger
	Logger     *zap.Logger

	closing chan struct{}
	wg      sync.WaitGroup
	opened  bool
}
~~~



### 写数据

##### Store.WriteToShard

~~~go
// WriteToShard writes a list of points to a shard identified by its ID.
func (s *Store) WriteToShard(shardID uint64, points []models.Point) error {
	return s.WriteToShardWithContext(context.Background(), shardID, points)
}
~~~



##### Store.WriteToShardWithContext 写数据到分片

~~~go
func (s *Store) WriteToShardWithContext(ctx context.Context, shardID uint64, points []models.Point) error {
	s.mu.RLock()

	select {
	case <-s.closing:
		s.mu.RUnlock()
		return ErrStoreClosed
	default:
	}

    //shards是什么时候创建的, coordinator在遇到此错误后，会调用Store.CreateShard创建
	sh := s.shards[shardID]
	if sh == nil {
		s.mu.RUnlock()
		return ErrShardNotFound
	}

	epoch := s.epochs[shardID]

	s.mu.RUnlock()

	// enter the epoch tracker
	guards, gen := epoch.StartWrite()
	defer epoch.EndWrite(gen)

	// wait for any guards before writing the points.
	for _, guard := range guards {
		if guard.Matches(points) {
			guard.Wait()
		}
	}

	// Ensure snapshot compactions are enabled since the shard might have been cold
	// and disabled by the monitor.
	if sh.IsIdle() {
		sh.SetCompactionsEnabled(true)
	}

	return sh.WritePointsWithContext(ctx, points)
}
~~~



### 创建存储分片数据的相关文件



分片的存储结构是什么样的？



##### Store.CreateShard 创建分片

注意opt.InmemIndex的赋值

写数据时，若没有分片，则会创建分片

* 检查分片是否已经存在，若存在则返回。不存在，则继续
* 检查分片是否处于正在删除状态
* 创建存放分片数据的目录，目录名称 s.path/数据库名称/policy名称。默认(~/.influxdb/data/数据库名称/policy名称)
* 创建分片使用的WAL目录, .influxdb/wal/数据库名称/rention policy名称/shard_id
* 调用Store.openSeriesFile建立SeriesFile和Shard的关联

~~~go
// CreateShard creates a shard with the given id and retention policy on a database.
func (s *Store) CreateShard(database, retentionPolicy string, shardID uint64, enabled bool) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	select {
	case <-s.closing:
		return ErrStoreClosed
	default:
	}

	// Shard already exists.
	if _, ok := s.shards[shardID]; ok {
		return nil
	}

	// Shard may be undergoing a pending deletion. While the shard can be
	// recreated, it must wait for the pending delete to finish.
	if _, ok := s.pendingShardDeletes[shardID]; ok {
		return ErrShardDeletion
	}

    //创建存放分片的目录 s.path的值是: .influxdb/data/
    //完整路径就是: .influxdb/data/数据库名称/rententionPolicy 名称
	// Create the db and retention policy directories if they don't exist.
	if err := os.MkdirAll(filepath.Join(s.path, database, retentionPolicy), 0700); err != nil {
		return err
	}

    //WAL目录 .influxdb/wal/数据库名称/policy名称/shard_id
	// Create the WAL directory.
	walPath := filepath.Join(s.EngineOptions.Config.WALDir, database, retentionPolicy, fmt.Sprintf("%d", shardID))
	if err := os.MkdirAll(walPath, 0700); err != nil {
		return err
	}

    
    //series file的用途还没搞清楚????????????????????????????????
    //搞清楚了: series file 存储的是series(又被称作key),由measurement name和tags组成
	// Retrieve database series file.
	sfile, err := s.openSeriesFile(database)
	if err != nil {
		return err
	}

    //创建索引
	// Retrieve shared index, if needed.
	idx, err := s.createIndexIfNotExists(database)
	if err != nil {
		return err
	}

	// Copy index options and pass in shared index.
	opt := s.EngineOptions
    //===================================
	opt.InmemIndex = idx
	opt.SeriesIDSets = shardSet{store: s, db: database}

    
    //创建分片 path: .influxdb/data/数据库名称/retentionPolicy/shard_id
	path := filepath.Join(s.path, database, retentionPolicy, strconv.FormatUint(shardID, 10))
    //关联shard 和SeriesFile
	shard := NewShard(shardID, path, walPath, sfile, opt)
	shard.WithLogger(s.baseLogger)
	shard.EnableOnOpen = enabled

	if err := shard.Open(); err != nil {
		return err
	}

	s.shards[shardID] = shard
	s.epochs[shardID] = newEpochTracker()
	if _, ok := s.databases[database]; !ok {
		s.databases[database] = new(databaseState)
	}
	s.databases[database].addIndexType(shard.IndexType())
	if state := s.databases[database]; state.hasMultipleIndexTypes() {
		var fields []zapcore.Field
		for idx, cnt := range state.indexTypes {
			fields = append(fields, zap.Int(fmt.Sprintf("%s_count", idx), cnt))
		}
		s.Logger.Warn("Mixed shard index types", append(fields, logger.Database(database))...)
	}

	return nil
}
~~~





##### Store.openSeriesFile 打开或创建series文件

创建分片Store.CreateShard会调用此函数

<font color="red">SeriesFile 是用来存放什么数据的, 用来存放series</font>

~~~go
// openSeriesFile either returns or creates a series file for the provided
// database. It must be called under a full lock.
func (s *Store) openSeriesFile(database string) (*SeriesFile, error) {
	if sfile := s.sfiles[database]; sfile != nil {
		return sfile, nil
	}

    //SeriesFileDirectory是一个字符串常量，字面值是_series
    //.influxdb/data/数据库名称/_series
	sfile := NewSeriesFile(filepath.Join(s.path, database, SeriesFileDirectory))
	sfile.WithMaxCompactionConcurrency(s.EngineOptions.Config.SeriesFileMaxConcurrentSnapshotCompactions)
	sfile.Logger = s.baseLogger
	if err := sfile.Open(); err != nil {
		return nil, err
	}
	s.sfiles[database] = sfile
	return sfile, nil
}
~~~





##### Store.createIndexIfNotExists 创建存放series 的索引文件

参数name 是数据库名称

~~~go
// createIndexIfNotExists returns a shared index for a database, if the inmem
// index is being used. If the TSI index is being used, then this method is
// basically a no-op.
//NewInmemIndex明确指明的是inmem index, 为啥注释说 if the TSI index is being used,
func (s *Store) createIndexIfNotExists(name string) (interface{}, error) {
	if idx := s.indexes[name]; idx != nil {
		return idx, nil
	}

	sfile, err := s.openSeriesFile(name)
	if err != nil {
		return nil, err
	}

    //NewInmemIndex 定义在tsdb/engine.go中
    //在tsdb/index/inmem/inmem.go中被初始化
	idx, err := NewInmemIndex(name, sfile)
	if err != nil {
		return nil, err
	}

	s.indexes[name] = idx
	return idx, nil
}
~~~



