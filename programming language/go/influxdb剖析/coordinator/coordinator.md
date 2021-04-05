# coordinator

[TOC]



coordinator 负责将时间点的数据对应到数据库的指定分片上，然后调用存储层(tsdb)提供的接口将数据写入磁盘

### PointsWriter

定义在coordinator/points_writer.go中



##### PointsWriter的定义

PointsWriter比较重要的几部分：

* MetaClient 接口，负责获取数据库的元数据。在
* TSDBStore接口，负责创建、写入分片

~~~go
// PointsWriter handles writes across multiple local and remote data nodes.
type PointsWriter struct {
	mu           sync.RWMutex
	closing      chan struct{}
	WriteTimeout time.Duration
	Logger       *zap.Logger

	Node *influxdb.Node

    //在 cmd/influxd/run/server.go中被Server.Open初始化为 meta.NewClient
    //MetaClient被初始化为
	MetaClient interface {
		Database(name string) (di *meta.DatabaseInfo)
		RetentionPolicy(database, policy string) (*meta.RetentionPolicyInfo, error)
		CreateShardGroup(database, policy string, timestamp time.Time) (*meta.ShardGroupInfo, error)
	}

    //cmd/influxd/run/server.go
    //被初始化为tsdb.NewStore()初始化
	TSDBStore interface {
		CreateShard(database, retentionPolicy string, shardID uint64, enabled bool) error
		WriteToShard(shardID uint64, points []models.Point) error
	}

	subPoints []chan<- *WritePointsRequest

	stats *WriteStatistics
}
~~~



##### NewPointsWriter

~~~go
/ NewPointsWriter returns a new instance of PointsWriter for a node.
func NewPointsWriter() *PointsWriter {
	return &PointsWriter{
		closing:      make(chan struct{}),
		WriteTimeout: DefaultWriteTimeout,
		Logger:       zap.NewNop(),
		stats:        &WriteStatistics{},
	}
}
~~~



##### PointsWriter.WritePoints 数据写入指定数据库的指定持久化策略(retention policy)

~~~go
// A wrapper for WritePointsWithContext()
func (w *PointsWriter) WritePoints(database, retentionPolicy string, consistencyLevel models.ConsistencyLevel, user meta.User, points []models.Point) error {
	return w.WritePointsWithContext(context.Background(), database, retentionPolicy, consistencyLevel, user, points)

}
~~~



##### PointsWriter.WritePointsWithContext

~~~go
// WritePointsWithContext writes data to the underlying storage. consitencyLevel and user are only used for clustered scenarios.
//
func (w *PointsWriter) WritePointsWithContext(ctx context.Context, database, retentionPolicy string, consistencyLevel models.ConsistencyLevel, user meta.User, points []models.Point) error {
	return w.WritePointsPrivilegedWithContext(ctx, database, retentionPolicy, consistencyLevel, points)
}
~~~



##### WritePointsPrivilegedWithContext

* 调整stats.WriteReq和stats.PointWriteReq统计信息

* 根据数据库名称调用PointsWriter.MetaClient.Database 获取准备写入的数据库
* 调用PointsWriter.MapShards确定样本点对应的分片，若分片不存在则创建分片

~~~go
// WritePointsPrivilegedWithContext writes the data to the underlying storage,
// consitencyLevel is only used for clustered scenarios
//
// If a request for StatPointsWritten or StatValuesWritten of type ContextKey is
// sent via context values, this stores the total points and fields written in
// the memory pointed to by the associated wth the int64 pointers.
//
func (w *PointsWriter) WritePointsPrivilegedWithContext(ctx context.Context, database, retentionPolicy string, consistencyLevel models.ConsistencyLevel, points []models.Point) error {
	atomic.AddInt64(&w.stats.WriteReq, 1)
	atomic.AddInt64(&w.stats.PointWriteReq, int64(len(points)))

    //若持久化策略为空，则使用默认的
	if retentionPolicy == "" {
		db := w.MetaClient.Database(database)
		if db == nil {
			return influxdb.ErrDatabaseNotFound(database)
		}
		retentionPolicy = db.DefaultRetentionPolicy
	}

    //确定样本点对应的分片
	shardMappings, err := w.MapShards(&WritePointsRequest{Database: database, RetentionPolicy: retentionPolicy, Points: points})
	if err != nil {
		return err
	}

	// Write each shard in it's own goroutine and return as soon as one fails.
	ch := make(chan error, len(shardMappings.Points))
	for shardID, points := range shardMappings.Points {
		go func(ctx context.Context, shard *meta.ShardInfo, database, retentionPolicy string, points []models.Point) {
			var numPoints, numValues int64
			ctx = context.WithValue(ctx, tsdb.StatPointsWritten, &numPoints)
			ctx = context.WithValue(ctx, tsdb.StatValuesWritten, &numValues)

			err := w.writeToShardWithContext(ctx, shard, database, retentionPolicy, points)
			if err == tsdb.ErrShardDeletion {
				err = tsdb.PartialWriteError{Reason: fmt.Sprintf("shard %d is pending deletion", shard.ID), Dropped: len(points)}
			}

			if v, ok := ctx.Value(StatPointsWritten).(*int64); ok {
				atomic.AddInt64(v, numPoints)
			}

			if v, ok := ctx.Value(StatValuesWritten).(*int64); ok {
				atomic.AddInt64(v, numValues)
			}

			ch <- err
		}(ctx, shardMappings.Shards[shardID], database, retentionPolicy, points)
	}

	// Send points to subscriptions if possible.
	var ok, dropped int64
	pts := &WritePointsRequest{Database: database, RetentionPolicy: retentionPolicy, Points: points}
	// We need to lock just in case the channel is about to be nil'ed
	w.mu.RLock()
	for _, ch := range w.subPoints {
		select {
		case ch <- pts:
			ok++
		default:
			dropped++
		}
	}
	w.mu.RUnlock()

	if ok > 0 {
		atomic.AddInt64(&w.stats.SubWriteOK, ok)
	}

	if dropped > 0 {
		atomic.AddInt64(&w.stats.SubWriteDrop, dropped)
	}

	if err == nil && len(shardMappings.Dropped) > 0 {
		err = tsdb.PartialWriteError{Reason: "points beyond retention policy", Dropped: len(shardMappings.Dropped)}

	}
	timeout := time.NewTimer(w.WriteTimeout)
	defer timeout.Stop()
	for range shardMappings.Points {
		select {
		case <-w.closing:
			return ErrWriteFailed
		case <-timeout.C:
			atomic.AddInt64(&w.stats.WriteTimeout, 1)
			// return timeout error to caller
			return ErrTimeout
		case err := <-ch:
			if err != nil {
				return err
			}
		}
	}
	return err
}
~~~



##### PointsWriter.MapShards 将每个时间点的数据映射到对应的分片

* 调用PointsWriter.MetaClient.RetentionPolicy获取 数据库的指定持久化策略，若持久化策略不存在则返回错误
* 根据样本点的时间和分片组的起止时间，确定样本落在哪个分片组。若没有分片满足，则创建分片组
* 

~~~go
// MapShards maps the points contained in wp to a ShardMapping.  If a point
// maps to a shard group or shard that does not currently exist, it will be
// created before returning th e mapping.
func (w *PointsWriter) MapShards(wp *WritePointsRequest) (*ShardMapping, error) {
	rp, err := w.MetaClient.RetentionPolicy(wp.Database, wp.RetentionPolicy)
	if err != nil {
		return nil, err
	} else if rp == nil {
		return nil, influxdb.ErrRetentionPolicyNotFound(wp.RetentionPolicy)
	}

	// Holds all the shard groups and shards that are required for writes.
	list := make(sgList, 0, 8)
	min := time.Unix(0, models.MinNanoTime)
    //持久化策略的时间大于0
	if rp.Duration > 0 {
		min = time.Now().Add(-rp.Duration)
	}

	for _, p := range wp.Points {
		// Either the point is outside the scope of the RP, or we already have
		// a suitable shard group for the point.
        //检查样本点时间是否超出rp覆盖的时间
        //样本点的时间小于分片的持久化时间, 落在这个分片之外
		if p.Time().Before(min) || list.Covers(p.Time()) {
			continue
		}

        //CreateShardGroup 会查找已有或创建新的
		// No shard groups overlap with the point's time, so we will create
		// a new shard group for this point.
		sg, err := w.MetaClient.CreateShardGroup(wp.Database, wp.RetentionPolicy, p.Time())
		if err != nil {
			return nil, err
		}

		if sg == nil {
			return nil, errors.New("nil shard group")
		}
		list = list.Append(*sg)
	}

    //创建新的ShardMapping
	mapping := NewShardMapping(len(wp.Points))
	for _, p := range wp.Points {
		sg := list.ShardGroupAt(p.Time())
		if sg == nil {
			// We didn't create a shard group because the point was outside the
			// scope of the RP.
			mapping.Dropped = append(mapping.Dropped, p)
			atomic.AddInt64(&w.stats.WriteDropped, 1)
			continue
		}
        //P.HashID 根据key(由measurement name 和tags(排好序))计算哈希值
		sh := sg.ShardFor(p.HashID())
		mapping.MapPoint(&sh, p)
	}
	return mapping, nil
}
~~~



##### PointsWriter.writeToShardWithContext 调用TSDBStore.WriteToShardWithContext 写数据到分片

* 封装匿名函数writeToShard
* 若分片不存在，则调用PointsWriter.TSDBStore.CreateShard创建存储数据的文件

TSDBStore

~~~go
func (w *PointsWriter) writeToShardWithContext(ctx context.Context, shard *meta.ShardInfo, database, retentionPolicy string, points []models.Point) error {
	atomic.AddInt64(&w.stats.PointWriteReqLocal, int64(len(points)))

	// This is a small wrapper to make type-switching over w.TSDBStore a little
	// less verbose.
	writeToShard := func() error {
		type shardWriterWithContext interface {
			WriteToShardWithContext(context.Context, uint64, []models.Point) error
		}
		switch sw := w.TSDBStore.(type) {
		case shardWriterWithContext:
			if err := sw.WriteToShardWithContext(ctx, shard.ID, points); err != nil {
				return err
			}
		default:
			if err := w.TSDBStore.WriteToShard(shard.ID, points); err != nil {
				return err
			}
		}
		return nil
	}

	// Except tsdb.ErrShardNotFound no error can be handled here
	if err := writeToShard(); err == tsdb.ErrShardNotFound {
		// Shard doesn't exist -- lets create it and try again..

		// If we've written to shard that should exist on the current node, but the
		// store has not actually created this shard, tell it to create it and
		// retry the write
		if err = w.TSDBStore.CreateShard(database, retentionPolicy, shard.ID, true); err != nil {
			w.Logger.Info("Write failed", zap.Uint64("shard", shard.ID), zap.Error(err))
			atomic.AddInt64(&w.stats.WriteErr, 1)
			return err
		}

		// Now that we've created the shard, try to write to it again.
		if err := writeToShard(); err != nil {
			w.Logger.Info("Write failed", zap.Uint64("shard", shard.ID), zap.Error(err))
			atomic.AddInt64(&w.stats.WriteErr, 1)
			return err
		}
	} else {
		atomic.AddInt64(&w.stats.WriteErr, 1)
		return err
	}

	atomic.AddInt64(&w.stats.WriteOK, 1)
	return nil
}
~~~



### sgList

##### sgList.Covers

~~~go
func (l sgList) Covers(t time.Time) bool {
	if len(l) == 0 {
		return false
	}
	return l.ShardGroupAt(t) != nil
}
~~~



##### sgList.ShardGroupAt

~~~go
// sgList is a wrapper around a meta.ShardGroupInfos where we can also check
// if a given time is covered by any of the shard groups in the list.
type sgList meta.ShardGroupInfos


// ShardGroupAt attempts to find a shard group that could contain a point
// at the given time.
//
// Shard groups are sorted first according to end time, and then according
// to start time. Therefore, if there are multiple shard groups that match
// this point's time they will be preferred in this order:
//
//  - a shard group with the earliest end time;
//  - (assuming identical end times) the shard group with the earliest start time.
func (l sgList) ShardGroupAt(t time.Time) *meta.ShardGroupInfo {
	idx := sort.Search(len(l), func(i int) bool { return l[i].EndTime.After(t) })

	// We couldn't find a shard group the point falls into.
	if idx == len(l) || t.Before(l[idx].StartTime) {
		return nil
	}
	return &l[idx]
}

// Append appends a shard group to the list, and returns a sorted list.
func (l sgList) Append(sgi meta.ShardGroupInfo) sgList {
	next := append(l, sgi)
	sort.Sort(meta.ShardGroupInfos(next))
	return next
}
~~~



### ShardMapping 建立point和shard之间的映射关系

~~~go
// ShardMapping contains a mapping of shards to points.
type ShardMapping struct {
	n       int
    //shard id 关联的所有point
	Points  map[uint64][]models.Point  // The points associated with a shard ID
	Shards  map[uint64]*meta.ShardInfo // The shards that have been mapped, keyed by shard ID
	Dropped []models.Point             // Points that were dropped
}

// NewShardMapping creates an empty ShardMapping.
func NewShardMapping(n int) *ShardMapping {
	return &ShardMapping{
		n:      n,
		Points: map[uint64][]models.Point{},
		Shards: map[uint64]*meta.ShardInfo{},
	}
}

~~~



##### ShardMapping.MapPoint 关联meta.ShardInfo 和 models.Point

~~~go

// MapPoint adds the point to the ShardMapping, associated with the given shardInfo.
func (s *ShardMapping) MapPoint(shardInfo *meta.ShardInfo, p models.Point) {
    //s.Points[shardInfo.ID]初始为空
	if cap(s.Points[shardInfo.ID]) < s.n {
		s.Points[shardInfo.ID] = make([]models.Point, 0, s.n)
	}
	s.Points[shardInfo.ID] = append(s.Points[shardInfo.ID], p)
	s.Shards[shardInfo.ID] = shardInfo
}
~~~



## LocalShardMapper

查询数据时使用LocalShardMapper确定对应的shard


##### LocalShardMapper.MapShards 根据数据库确定分片

~~~go
// MapShards maps the sources to the appropriate shards into an IteratorCreator.
func (e *LocalShardMapper) MapShards(sources influxql.Sources, t influxql.TimeRange, opt query.SelectOptions) (query.ShardGroup, error) {
	a := &LocalShardMapping{
		ShardMap: make(map[Source]tsdb.ShardGroup),
	}

	tmin := time.Unix(0, t.MinTimeNano())
	tmax := time.Unix(0, t.MaxTimeNano())
	if err := e.mapShards(a, sources, tmin, tmax); err != nil {
		return nil, err
	}
	a.MinTime, a.MaxTime = tmin, tmax
	return a, nil
}

func (e *LocalShardMapper) mapShards(a *LocalShardMapping, sources influxql.Sources, tmin, tmax time.Time) error {
	for _, s := range sources {
		switch s := s.(type) {
		case *influxql.Measurement:
			source := Source{
				Database:        s.Database,
				RetentionPolicy: s.RetentionPolicy,
			}
			// Retrieve the list of shards for this database. This list of
			// shards is always the same regardless of which measurement we are
			// using.
			if _, ok := a.ShardMap[source]; !ok {
				groups, err := e.MetaClient.ShardGroupsByTimeRange(s.Database, s.RetentionPolicy, tmin, tmax)
				if err != nil {
					return err
				}

				if len(groups) == 0 {
					a.ShardMap[source] = nil
					continue
				}

				shardIDs := make([]uint64, 0, len(groups[0].Shards)*len(groups))
				for _, g := range groups {
					for _, si := range g.Shards {
						shardIDs = append(shardIDs, si.ID)
					}
				}
				a.ShardMap[source] = e.TSDBStore.ShardGroup(shardIDs)
			}
		case *influxql.SubQuery:
			if err := e.mapShards(a, s.Statement.Sources, tmin, tmax); err != nil {
				return err
			}
		}
	}
	return nil
}
~~~



