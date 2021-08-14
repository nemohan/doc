# inmem index

[TOC]

## 总结

* 每个分片一个索引
* series由 "measurment 名称“ 和tags组成的字符串表示
* inmem 索引实际上是一种倒排索引



series :

~~~
————————————————————————————————————————————————————————————————————————
measurement		|tag=value		|	tag=value	|		|
————————————————————————————————————————————————————————————————————————
~~~



整体结构:

![1611462152254](${img}/1611462152254.png)

来自官方的介绍

~~~
/*
Package inmem implements a shared, in-memory index for each database.

The in-memory index is the original index implementation and provides fast
access to index data. However, it also forces high memory usage for large
datasets and can cause OOM errors.

Index is the shared index structure that provides most of the functionality.
However, ShardIndex is a light per-shard wrapper that adapts this original
shared index format to the new per-shard format.
*/
~~~



##### init 索引注册

~~~go
// IndexName is the name of this index.
const IndexName = tsdb.InmemIndexName

func init() {
	tsdb.NewInmemIndex = func(name string, sfile *tsdb.SeriesFile) (interface{}, error) { return NewIndex(name, sfile), nil }

	tsdb.RegisterIndex(IndexName, func(id uint64, database, path string, seriesIDSet *tsdb.SeriesIDSet, sfile *tsdb.SeriesFile, opt tsdb.EngineOptions) tsdb.Index {
		return NewShardIndex(id, seriesIDSet, opt)
	})
}
~~~



就先看看inmem index是如何工作的

Index 通过维护一个measurements 哈希表(map[string]*measurement)

##### Index的定义

成员:

* series map[string]*series类型的哈希表。key是series(由measurement name 和tags组成)，value是\*series类型的指针。该成员维护该数据库的所有的measurement的所有series
* measurements map[string]*measurement。key是measurement 的名称，value 是\*measurement类型的指针

~~~go
// Index is the in memory index of a collection of measurements, time
// series, and their tags. Exported functions are goroutine safe while
// un-exported functions assume the caller will use the appropriate locks.
type Index struct {
	mu sync.RWMutex

	database string
	sfile    *tsdb.SeriesFile
	fieldset *tsdb.MeasurementFieldSet

	// In-memory metadata index, built on load and updated when new series come in
	measurements map[string]*measurement // measurement name to object and index
	series       map[string]*series      // map series key to the Series object

	seriesSketch, seriesTSSketch             estimator.Sketch
	measurementsSketch, measurementsTSSketch estimator.Sketch

	// Mutex to control rebuilds of the index
	rebuildQueue sync.Mutex
}


~~~



##### NewIndex

~~~go
// NewIndex returns a new initialized Index.
func NewIndex(database string, sfile *tsdb.SeriesFile) *Index {
	index := &Index{
		database:     database,
		sfile:        sfile,
		measurements: make(map[string]*measurement),
		series:       make(map[string]*series),
	}

	index.seriesSketch = hll.NewDefaultPlus()
	index.seriesTSSketch = hll.NewDefaultPlus()
	index.measurementsSketch = hll.NewDefaultPlus()
	index.measurementsTSSketch = hll.NewDefaultPlus()

	return index
}
~~~



### 创建series

##### Index.CreateMeasurementIndexIfNotExists 根据名称获取或创建measurement

~~~go
/ CreateMeasurementIndexIfNotExists creates or retrieves an in memory index
// object for the measurement
func (i *Index) CreateMeasurementIndexIfNotExists(name []byte) *measurement {
	name = escape.Unescape(name)

	// See if the measurement exists using a read-lock
	i.mu.RLock()
	m := i.measurements[string(name)]
	if m != nil {
		i.mu.RUnlock()
		return m
	}
	i.mu.RUnlock()

	// Doesn't exist, so lock the index to create it
	i.mu.Lock()
	defer i.mu.Unlock()

	// Make sure it was created in between the time we released our read-lock
	// and acquire the write lock
	m = i.measurements[string(name)]
	if m == nil {
		m = newMeasurement(i.database, string(name))
		i.measurements[string(name)] = m

		// Add the measurement to the measurements sketch.
		i.measurementsSketch.Add([]byte(name))
	}
	return m
}
~~~



##### Index.CreateSeriesListIfNotExists   创建series

写数据时, 被ShardIndex.CreateSeriesListIfNotExists调用

* 检查series数量是否超过MaxSeriesPerDatabase 默认值是100万
* 调用CreateSeriesListIfNotExists

~~~go
// CreateSeriesListIfNotExists adds the series for the given measurement to the
// index and sets its ID or returns the existing series object
func (i *Index) CreateSeriesListIfNotExists(seriesIDSet *tsdb.SeriesIDSet, measurements map[string]int,
	keys, names [][]byte,
         tagsSlice []models.Tags, opt *tsdb.EngineOptions, ignoreLimits bool) error {

	// Verify that the series will not exceed limit.
	if !ignoreLimits {
		i.mu.RLock()
		if max := opt.Config.MaxSeriesPerDatabase; max > 0 && len(i.series)+len(keys) > max {
			i.mu.RUnlock()
			return errMaxSeriesPerDatabaseExceeded{limit: opt.Config.MaxSeriesPerDatabase}
		}
		i.mu.RUnlock()
	}

	seriesIDs, err := i.sfile.CreateSeriesListIfNotExists(names, tagsSlice)
	if err != nil {
		return err
	}

	i.mu.RLock()
    //？？？？？？？？？？？？？？？？？？？？？？？？？？？？？
    //所有的measurment的key共用一个series, 这样难道不会有问题么？？？
    //没有问题，每个series由 measurement名称和所有tag组成
	// If there is a series for this ID, it's already been added.
	seriesList := make([]*series, len(seriesIDs))
	for j, key := range keys {
		seriesList[j] = i.series[string(key)]
	}
	i.mu.RUnlock()

    //检查是否存在新的 series, key
	var hasNewSeries bool
	for _, ss := range seriesList {
		if ss == nil {
			hasNewSeries = true
			continue
		}

		// This series might need to be added to the local bitset, if the series
		// was created on another shard.
		seriesIDSet.Lock()
		if !seriesIDSet.ContainsNoLock(ss.ID) {
			seriesIDSet.AddNoLock(ss.ID)
			measurements[ss.Measurement.Name]++
		}
		seriesIDSet.Unlock()
	}
	if !hasNewSeries {
		return nil
	}

    //创建measurement
	// get or create the measurement index
	mms := make([]*measurement, len(names))
	for j, name := range names {
		mms[j] = i.CreateMeasurementIndexIfNotExists(name)
	}

	i.mu.Lock()
	defer i.mu.Unlock()

	// Check for the series again under a write lock
	var newSeriesN int
	for j, key := range keys {
		if seriesList[j] != nil {
			continue
		}

		ss := i.series[string(key)]
		if ss == nil {
			newSeriesN++
			continue
		}
		seriesList[j] = ss

		// This series might need to be added to the local bitset, if the series
		// was created on another shard.
        //每个分片索引，一个seriesIDSet
		seriesIDSet.Lock()
		if !seriesIDSet.ContainsNoLock(ss.ID) {
			seriesIDSet.AddNoLock(ss.ID)
			measurements[ss.Measurement.Name]++
		}
		seriesIDSet.Unlock()
	}
	if newSeriesN == 0 {
		return nil
	}
    
    //
	for j, key := range keys {
		// Note, keys may contain duplicates (e.g., because of points for the same series
		// in the same batch). If the duplicate series are new, the index must
		// be rechecked on each iteration.
        //seriesList存放已经存在的series
		if seriesList[j] != nil || i.series[string(key)] != nil {
			continue
		}

        //创建新的series
		// set the in memory ID for query processing on this shard
		// The series key and tags are clone to prevent a memory leak
		skey := string(key)
		ss := newSeries(seriesIDs[j], mms[j], skey, tagsSlice[j].Clone())
		i.series[skey] = ss

		mms[j].AddSeries(ss)

		// Add the series to the series sketch.
		i.seriesSketch.Add(key)

		// This series needs to be added to the bitset tracking undeleted series IDs.
		seriesIDSet.Lock()
		seriesIDSet.AddNoLock(seriesIDs[j])
		measurements[mms[j].Name]++
		seriesIDSet.Unlock()
	}

	return nil
}
~~~



##### Index.assignExistingSeries 过滤掉已经存在的series

参数: key 应该是包含measurement 和 tags的 字节数组

* 过滤掉已经存在的key

~~~go
// assignExistingSeries assigns the existing series to shardID and returns the series, names and tags that
// do not exists yet.
func (i *Index) assignExistingSeries(shardID uint64, seriesIDSet *tsdb.SeriesIDSet, measurements map[string]int,
	keys, names [][]byte,
    tagsSlice []models.Tags)
([][]byte, [][]byte, []models.Tags) {

	i.mu.RLock()
	var n int
	for j, key := range keys {
        //添加不存在的, key 对应series是否已经存在
		if ss := i.series[string(key)]; ss == nil {
			keys[n] = keys[j]
			names[n] = names[j]
			tagsSlice[n] = tagsSlice[j]
			n++
		} else {
			// Add the existing series to this shard's bitset, since this may
			// be the first time the series is added to this shard.
			if !seriesIDSet.Contains(ss.ID) {
				seriesIDSet.Lock()
				if !seriesIDSet.ContainsNoLock(ss.ID) {
					seriesIDSet.AddNoLock(ss.ID)
					measurements[string(names[j])]++
				}
				seriesIDSet.Unlock()
			}
		}
	}
	i.mu.RUnlock()
	return keys[:n], names[:n], tagsSlice[:n]
}
~~~



##### Index.HasTagKey 确定tag key是否存在于指定的measurement

~~~go

// HasTagKey returns true if tag key exists.
func (i *Index) HasTagKey(name, key []byte) (bool, error) {
	i.mu.RLock()
	mm := i.measurements[string(name)]
	i.mu.RUnlock()

	if mm == nil {
		return false, nil
	}
	return mm.HasTagKey(string(key)), nil
}
~~~



##### Index.HasTagValue

~~~go
// HasTagValue returns true if tag value exists.
func (i *Index) HasTagValue(name, key, value []byte) (bool, error) {
	i.mu.RLock()
	mm := i.measurements[string(name)]
	i.mu.RUnlock()

	if mm == nil {
		return false, nil
	}
	return mm.HasTagKeyValue(key, value), nil
}
~~~



## 数据查询

##### Index.TagSets

~~~go
// TagSets returns a list of tag sets.
func (i *Index) TagSets(shardSeriesIDs *tsdb.SeriesIDSet, name []byte, opt query.IteratorOptions) ([]*query.TagSet, error) {
	i.mu.RLock()
	defer i.mu.RUnlock()

	mm := i.measurements[string(name)]
	if mm == nil {
		return nil, nil
	}

	tagSets, err := mm.TagSets(shardSeriesIDs, opt)
	if err != nil {
		return nil, err
	}

	return tagSets, nil
}
~~~



## ShardIndex

##### ShardIndex的定义

~~~go
// Ensure index implements interface.
var _ tsdb.Index = &ShardIndex{}

// ShardIndex represents a shim between the TSDB index interface and the shared
// in-memory index. This is required because per-shard in-memory indexes will
// grow the heap size too large.
type ShardIndex struct {
	id uint64 // shard id

	*Index // Shared reference to global database-wide index.

	// Bitset storing all undeleted series IDs associated with this shard.
	seriesIDSet *tsdb.SeriesIDSet

	// mapping of measurements to the count of series ids in the set. protected
	// by the seriesIDSet lock.
	measurements map[string]int

	opt tsdb.EngineOptions
}
~~~



##### NewShardIndex

~~~go
// NewShardIndex returns a new index for a shard.
func NewShardIndex(id uint64, seriesIDSet *tsdb.SeriesIDSet, opt tsdb.EngineOptions) tsdb.Index {
	return &ShardIndex{
		Index:        opt.InmemIndex.(*Index),
		id:           id,
		seriesIDSet:  seriesIDSet,
		measurements: make(map[string]int),
		opt:          opt,
	}
}
~~~



### 为series添加索引

##### ShardIndex.CreateSeriesListIfNotExists 为tag添加索引

参数:

* keys 包含measurement 和tag
* names measurement 名称数组
* tagsSlice



* 调用 Index.assignExistingSeries , 过滤掉已经存在的 series，一个key就是一个series
* 确保tag的cardinality不超过MaxValuesPerTag(默认值10万)，若超过则丢弃
* 调用Index.CreateSeriesListIfNotExists 添加keys

~~~go
// CreateSeriesListIfNotExists creates a list of series if they doesn't exist in bulk.
func (idx *ShardIndex) CreateSeriesListIfNotExists(keys, names [][]byte, tagsSlice []models.Tags) error {
    //idx.assignExistingSeries实际调用的是Index.assignExistingSeries
	keys, names, tagsSlice = idx.assignExistingSeries(idx.id, idx.seriesIDSet, idx.measurements, keys, names, tagsSlice)
	if len(keys) == 0 {
		return nil
	}

	var (
		reason      string
		droppedKeys [][]byte
	)

    //确保tag的value的唯一值数目不超过MaxValusePerTag
    //MaxValuesPerTag的默认值是10万，在tsdb/config.go中定义
	// Ensure that no tags go over the maximum cardinality.
	if maxValuesPerTag := idx.opt.Config.MaxValuesPerTag; maxValuesPerTag > 0 {
		var n int

	outer:
		for i, name := range names {
			tags := tagsSlice[i]
			for _, tag := range tags {
                //跳过已经存在的tag
				// Skip if the tag value already exists.
				if ok, _ := idx.HasTagValue(name, tag.Key, tag.Value); ok {
					continue
				}

				// Read cardinality. Skip if we're below the threshold.
				n := idx.TagValueN(name, tag.Key)
				if n < maxValuesPerTag {
					continue
				}

				if reason == "" {
					reason = fmt.Sprintf("max-values-per-tag limit exceeded (%d/%d): measurement=%q tag=%q value=%q",
						n, maxValuesPerTag, name, string(tag.Key), string(tag.Value))
				}

				droppedKeys = append(droppedKeys, keys[i])
				continue outer
			}

			// Increment success count if all checks complete.
			if n != i {
				keys[n], names[n], tagsSlice[n] = keys[i], names[i], tagsSlice[i]
			}
			n++
		}

		// Slice to only include successful points.
		keys, names, tagsSlice = keys[:n], names[:n], tagsSlice[:n]
	}

    //MaxSeriesPerDatabase 只应用于inmem 索引,默认值是100万。定义在tsdb/config.go中
	if err := idx.Index.CreateSeriesListIfNotExists(idx.seriesIDSet, idx.measurements, keys, names, tagsSlice, &idx.opt, idx.opt.Config.MaxSeriesPerDatabase == 0); err != nil {
		reason = err.Error()
		droppedKeys = append(droppedKeys, keys...)
	}

	// Report partial writes back to shard.
	if len(droppedKeys) > 0 {
		dropped := len(droppedKeys) // number dropped before deduping
		bytesutil.SortDedup(droppedKeys)
		return tsdb.PartialWriteError{
			Reason:      reason,
			Dropped:     dropped,
			DroppedKeys: droppedKeys,
		}
	}

	return nil
}
~~~



##### Index.TagValueN 获得某个tag的键对应所有值的集合的大小

~~~go
// TagValueN returns the cardinality of a tag value.
func (i *Index) TagValueN(name, key []byte) int {
	i.mu.RLock()
	mm := i.measurements[string(name)]
	i.mu.RUnlock()

	if mm == nil {
		return 0
	}
	return mm.CardinalityBytes(key)
}
~~~



