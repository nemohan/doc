 # meta

[TOC]



## measurement

先看看measurement 实现了一个怎样的索引结构

measurement 相当于实现了一个倒排索引(invert index) 。哈希表measurement.seriesByID，可以通过series的哈希值，快速确定series对象。而哈希表measurement.seriesByTagKeyValue(key 是tag的key, value是tagKeyValue类型的指针)，则可以通过tag的key找到其对应的所有值(tagKeyValue)。而tagKeyValue又维护了哈希表tagKeyValue.entries (类型map[string]*tagKeyValueEntry , key 是tag的某个key对应的value, 值是\*tagKeyValue类型的指针），tagKeyValueEntry则维护了该value所在的所有series的ID

成员:  

* seriesByID map[suint64]*series 哈希表。key是series的哈希值。value 是\*series类型的指针
* seriesByTagKeyValue map[string]*tagKeyValue。key是tag的key， value是\*tagKeyValue类型的指针。

measurement 定义了表包含的tag的索引

~~~go
// Measurement represents a collection of time series in a database. It also
// contains in memory structures for indexing tags. Exported functions are
// goroutine safe while un-exported functions assume the caller will use the
// appropriate locks.
type measurement struct {
	Database  string
	Name      string `json:"name,omitempty"`
	NameBytes []byte // cached version as []byte

	mu         sync.RWMutex
	fieldNames map[string]struct{}

	// in-memory index fields
	seriesByID          map[uint64]*series      // lookup table for series by their id
    //定义了该measurement包含的所有tag，tag由“键值对”组成。“键”对应map的key,值的集合对应tagKeyValue
	seriesByTagKeyValue map[string]*tagKeyValue // map from tag key to value to sorted set of series ids

	// lazyily created sorted series IDs
	sortedSeriesIDs seriesIDs // sorted list of series IDs in this measurement

	// Indicates whether the seriesByTagKeyValueMap needs to be rebuilt as it contains deleted series
	// that waste memory.
	dirty bool
}

// newMeasurement allocates and initializes a new Measurement.
func newMeasurement(database, name string) *measurement {
	return &measurement{
		Database:  database,
		Name:      name,
		NameBytes: []byte(name),

		fieldNames:          make(map[string]struct{}),
		seriesByID:          make(map[uint64]*series),
		seriesByTagKeyValue: make(map[string]*tagKeyValue),
	}
}
~~~



##### measurement.HasTagKey 检查含有key的tag是否存在

~~~go

// HasTagKey returns true if at least one series in this measurement has written a value for the passed in tag key
func (m *measurement) HasTagKey(k string) bool {
	m.mu.RLock()
	defer m.mu.RUnlock()
	_, hasTag := m.seriesByTagKeyValue[k]
	return hasTag
}

~~~



##### measurement.HasTagKeyValue 是否包含指定的 tag

tag由 key和value组成

~~~go

func (m *measurement) HasTagKeyValue(k, v []byte) bool {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.seriesByTagKeyValue[string(k)].Contains(string(v))
}
~~~



##### measurement.CardinalityBytes 某个key的唯一值个数

~~~go
// CardinalityBytes returns the number of values associated with the given tag key.
func (m *measurement) CardinalityBytes(key []byte) int {
	m.mu.RLock()
	defer m.mu.RUnlock()
    //实际是返回的len(tagKeyVlaue.entries)
	return m.seriesByTagKeyValue[string(key)].Cardinality()
}
~~~



##### measurement.AddSeries 添加series，创建映射关系

~~~go
// AddSeries adds a series to the measurement's index.
// It returns true if the series was added successfully or false if the series was already present.
func (m *measurement) AddSeries(s *series) bool {
	if s == nil {
		return false
	}

	m.mu.RLock()
	if m.seriesByID[s.ID] != nil {
		m.mu.RUnlock()
		return false
	}
	m.mu.RUnlock()

	m.mu.Lock()
	defer m.mu.Unlock()

	if m.seriesByID[s.ID] != nil {
		return false
	}

	m.seriesByID[s.ID] = s

	if len(m.seriesByID) == 1 || (len(m.sortedSeriesIDs) == len(m.seriesByID)-1 && s.ID > m.sortedSeriesIDs[len(m.sortedSeriesIDs)-1]) {
		m.sortedSeriesIDs = append(m.sortedSeriesIDs, s.ID)
	}

	// add this series id to the tag index on the measurement
	for _, t := range s.Tags {
		valueMap := m.seriesByTagKeyValue[string(t.Key)]
		if valueMap == nil {
			valueMap = newTagKeyValue()
			m.seriesByTagKeyValue[string(t.Key)] = valueMap
		}
		valueMap.InsertSeriesIDByte(t.Value, s.ID)
	}

	return true
}

~~~

### 数据查询

##### measurement.TagSets

~~~go
// TagSets returns the unique tag sets that exist for the given tag keys. This is used to determine
// what composite series will be created by a group by. i.e. "group by region" should return:
// {"region":"uswest"}, {"region":"useast"}
// or region, service returns
// {"region": "uswest", "service": "redis"}, {"region": "uswest", "service": "mysql"}, etc...
// This will also populate the TagSet objects with the series IDs that match each tagset and any
// influx filter expression that goes with the series
// TODO: this shouldn't be exported. However, until tx.go and the engine get refactored into tsdb, we need it.
func (m *measurement) TagSets(shardSeriesIDs *tsdb.SeriesIDSet, opt query.IteratorOptions) ([]*query.TagSet, error) {
	// get the unique set of series ids and the filters that should be applied to each
	ids, filters, err := m.filters(opt.Condition)
	if err != nil {
		return nil, err
	}

	var dims []string
	if len(opt.Dimensions) > 0 {
		dims = make([]string, len(opt.Dimensions))
		copy(dims, opt.Dimensions)
		sort.Strings(dims)
	}

	m.mu.RLock()
	// For every series, get the tag values for the requested tag keys i.e. dimensions. This is the
	// TagSet for that series. Series with the same TagSet are then grouped together, because for the
	// purpose of GROUP BY they are part of the same composite series.
	tagSets := make(map[string]*query.TagSet, 64)
	var seriesN int
	for _, id := range ids {
		// Abort if the query was killed
		select {
		case <-opt.InterruptCh:
			m.mu.RUnlock()
			return nil, query.ErrQueryInterrupted
		default:
		}

		if opt.MaxSeriesN > 0 && seriesN > opt.MaxSeriesN {
			m.mu.RUnlock()
			return nil, fmt.Errorf("max-select-series limit exceeded: (%d/%d)", seriesN, opt.MaxSeriesN)
		}

		s := m.seriesByID[id]
		if s == nil || s.Deleted() || !shardSeriesIDs.Contains(id) {
			continue
		}

		if opt.Authorizer != nil && !opt.Authorizer.AuthorizeSeriesRead(m.Database, m.NameBytes, s.Tags) {
			continue
		}

		var tagsAsKey []byte
		if len(dims) > 0 {
			tagsAsKey = tsdb.MakeTagsKey(dims, s.Tags)
		}

		tagSet := tagSets[string(tagsAsKey)]
		if tagSet == nil {
			// This TagSet is new, create a new entry for it.
			tagSet = &query.TagSet{
				Tags: nil,
				Key:  tagsAsKey,
			}
			tagSets[string(tagsAsKey)] = tagSet
		}
		// Associate the series and filter with the Tagset.
		tagSet.AddFilter(s.Key, filters[id])
		seriesN++
	}
	// Release the lock while we sort all the tags
	m.mu.RUnlock()

	// Sort the series in each tag set.
	for _, t := range tagSets {
		// Abort if the query was killed
		select {
		case <-opt.InterruptCh:
			return nil, query.ErrQueryInterrupted
		default:
		}

		sort.Sort(t)
	}

	// The TagSets have been created, as a map of TagSets. Just send
	// the values back as a slice, sorting for consistency.
	sortedTagsSets := make([]*query.TagSet, 0, len(tagSets))
	for _, v := range tagSets {
		sortedTagsSets = append(sortedTagsSets, v)
	}
	sort.Sort(byTagKey(sortedTagsSets))

	return sortedTagsSets, nil
}
~~~



##### measurement.filters

~~~go
// filters walks the where clause of a select statement and returns a map with all series ids
// matching the where clause and any filter expression that should be applied to each
func (m *measurement) filters(condition influxql.Expr) ([]uint64, map[uint64]influxql.Expr, error) {
	if condition == nil {
		return m.SeriesIDs(), nil, nil
	}
	return m.WalkWhereForSeriesIds(condition)
}
~~~



### tagKeyValue

tagKeyValue 定义了某个tag 的key所对应的所有value

~~~go

// TagKeyValue provides goroutine-safe concurrent access to the set of series
// ids mapping to a set of tag values.
type tagKeyValue struct {
	mu      sync.RWMutex
	entries map[string]*tagKeyValueEntry
}
~~~



##### tagKeyValue.Contains 

检查在某个tag的所有值中是否包含值value

~~~go
// Contains returns true if the TagKeyValue contains value.
func (t *tagKeyValue) Contains(value string) bool {
	if t == nil {
		return false
	}

	t.mu.RLock()
	defer t.mu.RUnlock()
	_, ok := t.entries[value]
	return ok
}
~~~



##### tagKeyValue.InsertSeriesIDByte

~~~go
// InsertSeriesIDByte adds a series id to the tag key value.
func (t *tagKeyValue) InsertSeriesIDByte(value []byte, id uint64) {
	t.mu.Lock()
    //entries 包含了某个tag key对应的所有value
	entry := t.entries[string(value)]
	if entry == nil {
		entry = newTagKeyValueEntry()
		t.entries[string(value)] = entry
	}
    //tag key-value对应的serries id
	entry.m[id] = struct{}{}
	t.mu.Unlock()
}
~~~



#### tagKeyValueEntry

~~~go
type tagKeyValueEntry struct {
	m map[uint64]struct{} // series id set
	a seriesIDs           // lazily sorted list of series.
}
~~~



### seriesIDs

~~~go
// SeriesIDs is a convenience type for sorting, checking equality, and doing
// union and intersection of collections of series ids.
type seriesIDs []uint6
~~~



## series

series定义了其所在的measurement、key(由measurement name和tags组成)、Tags

~~~go
// series belong to a Measurement and represent unique time series in a database.
type series struct {
	mu      sync.RWMutex
	deleted bool

	// immutable
	ID          uint64
	Measurement *measurement
	Key         string
	Tags        models.Tags //Tags 其实是一个 []model.Tag类型的切片
}
~~~

