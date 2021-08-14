## cache 缓存

[TOC]

tsdb/engine/cache.go中

##### cache的定义

~~~go
// Cache maintains an in-memory store of Values for a set of keys.
type Cache struct {
	// Due to a bug in atomic  size needs to be the first word in the struct, as
	// that's the only place where you're guaranteed to be 64-bit aligned on a
	// 32 bit system. See: https://golang.org/pkg/sync/atomic/#pkg-note-BUG
	size         uint64
	snapshotSize uint64

	mu      sync.RWMutex
	store   storer
	maxSize uint64

	// snapshots are the cache objects that are currently being written to tsm files
	// they're kept in memory while flushing so they can be queried along with the cache.
	// they are read only and should never be modified
	snapshot     *Cache
	snapshotting bool

	// This number is the number of pending or failed WriteSnaphot attempts since the last successful one.
	snapshotAttempts int

	stats         *CacheStatistics
	lastSnapshot  time.Time
	lastWriteTime time.Time

	// A one time synchronization used to initial the cache with a store.  Since the store can allocate a
	// a large amount memory across shards, we lazily create it.
	initialize       atomic.Value
	initializedCount uint32
}
~~~





##### NewCache

NewEngine 会调用此函数

~~~
cache := NewCache(uint64(opt.Config.CacheMaxMemorySize)) //
~~~



~~~go
// NewCache returns an instance of a cache which will use a maximum of maxSize bytes of memory.
// Only used for engine caches, never for snapshots.
func NewCache(maxSize uint64) *Cache {
	c := &Cache{
		maxSize:      maxSize,
		store:        emptyStore{},
		stats:        &CacheStatistics{},
		lastSnapshot: time.Now(),
	}
	c.initialize.Store(&sync.Once{})
	c.UpdateAge()
	c.UpdateCompactTime(0)
	c.updateCachedBytes(0)
	c.updateMemSize(0)
	c.updateSnapshots()
	return c
}
~~~



##### Cache.WriteMulti 数据写入缓存

* 调用c.init 初始化Cache.store 为ring，只初始化一次

* 统计写入缓存的所有值的大小（字节数），若超过缓存上限DefaultCacheMaxMemorySize 1G(influxdb/tsdb/config.go)。则报错
* 

~~~go



// WriteMulti writes the map of keys and associated values to the cache. This
// function is goroutine-safe. It returns an error if the cache will exceeded
// its max size by adding the new values.  The write attempts to write as many
// values as possible.  If one key fails, the others can still succeed and an
// error will be returned.
func (c *Cache) WriteMulti(values map[string][]Value) error {
	c.init()
	var addedSize uint64
	for _, v := range values {
		addedSize += uint64(Values(v).Size())
	}

    //maxSize 1G 的默认值定义在influxdb/tsdb/config.go中
	// Enough room in the cache?
	limit := c.maxSize // maxSize is safe for reading without a lock.
	n := c.Size() + addedSize
	if limit > 0 && n > limit {
		atomic.AddInt64(&c.stats.WriteErr, 1)
		return ErrCacheMemorySizeLimitExceeded(n, limit)
	}

	var werr error
	c.mu.RLock()
	store := c.store
	c.mu.RUnlock()

    //c.init 会初始化store 为ring
    
	// We'll optimistially set size here, and then decrement it for write errors.
	c.increaseSize(addedSize)
	for k, v := range values {
        //实际调用ring.write
		newKey, err := store.write([]byte(k), v)
		if err != nil {
			// The write failed, hold onto the error and adjust the size delta.
			werr = err
			addedSize -= uint64(Values(v).Size())
			c.decreaseSize(uint64(Values(v).Size()))
		}
		if newKey {
			addedSize += uint64(len(k))
			c.increaseSize(uint64(len(k)))
		}
	}

	// Some points in the batch were dropped.  An error is returned so
	// error stat is incremented as well.
	if werr != nil {
		atomic.AddInt64(&c.stats.WriteDropped, 1)
		atomic.AddInt64(&c.stats.WriteErr, 1)
	}

	// Update the memory size stat
	c.updateMemSize(int64(addedSize))
	atomic.AddInt64(&c.stats.WriteOK, 1)

	c.mu.Lock()
	c.lastWriteTime = time.Now()
	c.mu.Unlock()

	return werr
}
~~~



##### Cache.init

~~~go
// init initializes the cache and allocates the underlying store.  Once initialized,
// the store re-used until Freed.
func (c *Cache) init() {
	if !atomic.CompareAndSwapUint32(&c.initializedCount, 0, 1) {
		return
	}

	c.mu.Lock()
    //ringShards 是16
	c.store, _ = newring(ringShards)
	c.mu.Unlock()
}
~~~



##### Cache.Snapshot 创建缓存快照

~~~go
// Snapshot takes a snapshot of the current cache, adds it to the slice of caches that
// are being flushed, and resets the current cache with new values.
func (c *Cache) Snapshot() (*Cache, error) {
	c.init()

	c.mu.Lock()
	defer c.mu.Unlock()

	if c.snapshotting {
		return nil, ErrSnapshotInProgress
	}

	c.snapshotting = true
	c.snapshotAttempts++ // increment the number of times we tried to do this

	// If no snapshot exists, create a new one, otherwise update the existing snapshot
	if c.snapshot == nil {
        //ringShard的值是16
		store, err := newring(ringShards)
		if err != nil {
			return nil, err
		}

		c.snapshot = &Cache{
			store: store,
		}
	}

	// Did a prior snapshot exist that failed?  If so, return the existing
	// snapshot to retry.
	if c.snapshot.Size() > 0 {
		return c.snapshot, nil
	}
	
    //完成快照创建
	c.snapshot.store, c.store = c.store, c.snapshot.store
	snapshotSize := c.Size()

	// Save the size of the snapshot on the snapshot cache
	atomic.StoreUint64(&c.snapshot.size, snapshotSize)
	// Save the size of the snapshot on the live cache
	atomic.StoreUint64(&c.snapshotSize, snapshotSize)

    //重置
	// Reset the cache's store.
	c.store.reset()
	atomic.StoreUint64(&c.size, 0)
	c.lastSnapshot = time.Now()

    //更新 c.stats.CachedBytes
	c.updateCachedBytes(snapshotSize) // increment the number of bytes added to the snapshot
    //更新统计信息
	c.updateSnapshots()

	return c.snapshot, nil
}
~~~



##### ClearSnapshot

~~~go
// ClearSnapshot removes the snapshot cache from the list of flushing caches and // adjusts the size.
func (c *Cache) ClearSnapshot(success bool) {
	c.init()

	c.mu.RLock()
	snapStore := c.snapshot.store
	c.mu.RUnlock()

	// reset the snapshot store outside of the write lock
	if success {
		snapStore.reset()
	}

	c.mu.Lock()
	defer c.mu.Unlock()

	c.snapshotting = false

	if success {
		c.snapshotAttempts = 0
		c.updateMemSize(-int64(atomic.LoadUint64(&c.snapshotSize))) // decrement the number of bytes in cache

        //为啥不置空, c.snapshot = nil
        
		// Reset the snapshot to a fresh Cache.
		c.snapshot = &Cache{
			store: c.snapshot.store,
		}

		atomic.StoreUint64(&c.snapshotSize, 0)
		c.updateSnapshots()
	}
}

~~~



##### 缓存相关统计信息

~~~go
//更新当前缓存的年龄 单位：毫秒
// UpdateAge updates the age statistic based on the current time.
func (c *Cache) UpdateAge() {
	c.mu.RLock()
	defer c.mu.RUnlock()
	ageStat := int64(time.Since(c.lastSnapshot) / time.Millisecond)
	atomic.StoreInt64(&c.stats.CacheAgeMs, ageStat)
}

//统计刷盘耗时 单位：毫秒
// UpdateCompactTime updates WAL compaction time statistic based on d.
func (c *Cache) UpdateCompactTime(d time.Duration) {
	atomic.AddInt64(&c.stats.WALCompactionTimeMs, int64(d/time.Millisecond))
}

//统计缓存的累积大小
// updateCachedBytes increases the cachedBytes counter by b.
func (c *Cache) updateCachedBytes(b uint64) {
	atomic.AddInt64(&c.stats.CachedBytes, int64(b))
}

//统计缓存占内存大小, 和c.stats.CachedBytes有什么区别
// updateMemSize updates the memSize level by b.
func (c *Cache) updateMemSize(b int64) {
	atomic.AddInt64(&c.stats.MemSizeBytes, b)
}



// updateSnapshots updates the snapshotsCount and the diskSize levels.
func (c *Cache) updateSnapshots() {
	// Update disk stats
	atomic.StoreInt64(&c.stats.DiskSizeBytes, int64(atomic.LoadUint64(&c.snapshotSize)))
	atomic.StoreInt64(&c.stats.SnapshotCount, int64(c.snapshotAttempts))
}
~~~



### ring

使用partition的好处是啥

##### ring的定义

~~~go
// partitions is the number of partitions we used in the ring's continuum. It
// basically defines the maximum number of partitions you can have in the ring.
// If a smaller number of partitions are chosen when creating a ring, then
// they're evenly spread across this many partitions in the ring.
const partitions = 16

// ring is a structure that maps series keys to entries.
//
// ring is implemented as a crude hash ring, in so much that you can have
// variable numbers of members in the ring, and the appropriate member for a
// given series key can always consistently be found. Unlike a true hash ring
// though, this ring is not resizeable—there must be at most 256 members in the
// ring, and the number of members must always be a power of 2.
//
// ring works as follows: Each member of the ring contains a single store, which
// contains a map of series keys to entries. A ring always has 256 partitions,
// and a member takes up one or more of these partitions (depending on how many
// members are specified to be in the ring)
//
// To determine the partition that a series key should be added to, the series
// key is hashed and the first 8 bits are used as an index to the ring.
//
type ring struct {
	// Number of keys within the ring. This is used to provide a hint for
	// allocating the return values in keys(). It will not be perfectly accurate
	// since it doesn't consider adding duplicate keys, or trying to remove non-
	// existent keys.
	keysHint int64

	// The unique set of partitions in the ring.
	// len(partitions) <= len(continuum)
	partitions []*partition
}
~~~



##### newring

~~~go

// newring returns a new ring initialised with n partitions. n must always be a
// power of 2, and for performance reasons should be larger than the number of
// cores on the host. The supported set of values for n is:
//
//     {1, 2, 4, 8, 16, 32, 64, 128, 256}.
//
func newring(n int) (*ring, error) {
    //partitions 是常量16
	if n <= 0 || n > partitions {
		return nil, fmt.Errorf("invalid number of paritions: %d", n)
	}

	r := ring{
		partitions: make([]*partition, n), // maximum number of partitions.
	}

	// The trick here is to map N partitions to all points on the continuum,
	// such that the first eight bits of a given hash will map directly to one
	// of the N partitions.
	for i := 0; i < len(r.partitions); i++ {
		r.partitions[i] = &partition{
			store: make(map[string]*entry),
		}
	}
	return &r, nil
}
~~~



##### ring.write 数据写入partition

参数： 

* key 由 Point.Key(由measurement name 和tags组成)、分隔符、field的key组成



假设Point如下:

~~~
cpu,host=localhost usage=1 free=2
~~~

其对应的key则有两个

~~~
cpu,host=localhost#!~#usage 
cpu,host=localhost#!~#free
~~~



~~~go
// write writes values to the entry in the ring's partition associated with key.
// If no entry exists for the key then one will be created.
// write is safe for use by multiple goroutines.
func (r *ring) write(key []byte, values Values) (bool, error) {
	return r.getPartition(key).write(key, values)
}

// getPartition retrieves the hash ring partition associated with the provided
// key.
func (r *ring) getPartition(key []byte) *partition {
	return r.partitions[int(xxhash.Sum64(key)%uint64(len(r.partitions)))]
}
~~~





#### partition

以hash table的形式存储某个由(所有tag+ 单个field)组成的key 对应的所有值(field对应的值)

~~~go
// partition provides safe access to a map of series keys to entries.
type partition struct {
	mu    sync.RWMutex
	store map[string]*entry
}
~~~



##### entry的定义

influxdb/tsdb/engine/tsm1/cache.go

~~~go
// entry is a set of values and some metadata.
type entry struct {
	mu     sync.RWMutex
    //Values 定义在/influxdb/tsdb/engine/tsm1/encoding.gen.go中, 是个[]Value类型
    //Value 定义在 influxdb/tsdb/engine/tsm1/encoding.go中
	values Values // All stored values.

	// The type of values stored. Read only so doesn't need to be protected by
	// mu.
	vtype byte
}
~~~



##### partition.write

~~~go
// write writes the values to the entry in the partition, creating the entry
// if it does not exist.
// write is safe for use by multiple goroutines.
func (p *partition) write(key []byte, values Values) (bool, error) {
	p.mu.RLock()
	e := p.store[string(key)]
	p.mu.RUnlock()
	if e != nil {
		// Hot path.
		return false, e.add(values)
	}

	p.mu.Lock()
	defer p.mu.Unlock()

	// Check again.
	if e = p.store[string(key)]; e != nil {
		return false, e.add(values)
	}

	// Create a new entry using a preallocated size if we have a hint available.
	e, err := newEntryValues(values)
	if err != nil {
		return false, err
	}

	p.store[string(key)] = e
	return true, nil
}
~~~



### entry

~~~go
// entry is a set of values and some metadata.
type entry struct {
	mu     sync.RWMutex
	values Values // All stored values.

	// The type of values stored. Read only so doesn't need to be protected by
	// mu.
	vtype byte
}
~~~



##### newEntryValues

~~~go
// newEntryValues returns a new instance of entry with the given values.  If the
// values are not valid, an error is returned.
func newEntryValues(values []Value) (*entry, error) {
	e := &entry{}
	e.values = make(Values, 0, len(values))
	e.values = append(e.values, values...)

	// No values, don't check types and ordering
	if len(values) == 0 {
		return e, nil
	}
	//检查类型是否一致
	et := valueType(values[0])
	for _, v := range values {
		// Make sure all the values are the same type
		if et != valueType(v) {
			return nil, tsdb.ErrFieldTypeConflict
		}
	}

	// Set the type of values stored.
	e.vtype = et

	return e, nil
}
~~~



##### entry.add 

~~~go
// add adds the given values to the entry.
func (e *entry) add(values []Value) error {
	if len(values) == 0 {
		return nil // Nothing to do.
	}

	// Are any of the new values the wrong type?
	if e.vtype != 0 {
		for _, v := range values {
			if e.vtype != valueType(v) {
				return tsdb.ErrFieldTypeConflict
			}
		}
	}

	// entry currently has no values, so add the new ones and we're done.
	e.mu.Lock()
	if len(e.values) == 0 {
		e.values = values
		e.vtype = valueType(values[0])
		e.mu.Unlock()
		return nil
	}

	// Append the new values to the existing ones...
	e.values = append(e.values, values...)
	e.mu.Unlock()
	return nil
}
~~~



#####  

~~~go

~~~





















