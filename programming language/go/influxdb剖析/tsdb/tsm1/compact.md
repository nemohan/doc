# Compactor

[TOC]

定义在tsdb/engine/compact.go



## 总结

每个缓存快照写入一个单独tsm文件。然后定期合并小的tsm文件

数据文件格式

~~~

/*
A TSM file is composed for four sections: header, blocks, index and the footer.

┌────────┬────────────────────────────────────┬─────────────┬──────────────┐
│ Header │               Blocks               │    Index    │    Footer    │
│5 bytes │              N bytes               │   N bytes   │   4 bytes    │
└────────┴────────────────────────────────────┴─────────────┴──────────────┘

Header is composed of a magic number to identify the file type and a version
number.

┌───────────────────┐
│      Header       │
├─────────┬─────────┤
│  Magic  │ Version │
│ 4 bytes │ 1 byte  │
└─────────┴─────────┘

Blocks are sequences of pairs of CRC32 and data.  The block data is opaque to the
file.  The CRC32 is used for block level error detection.  The length of the blocks
is stored in the index.

┌───────────────────────────────────────────────────────────┐
│                          Blocks                           │
├───────────────────┬───────────────────┬───────────────────┤
│      Block 1      │      Block 2      │      Block N      │
├─────────┬─────────┼─────────┬─────────┼─────────┬─────────┤
│  CRC    │  Data   │  CRC    │  Data   │  CRC    │  Data   │
│ 4 bytes │ N bytes │ 4 bytes │ N bytes │ 4 bytes │ N bytes │
└─────────┴─────────┴─────────┴─────────┴─────────┴─────────┘

Following the blocks is the index for the blocks in the file.  The index is
composed of a sequence of index entries ordered lexicographically by key and
then by time.  Each index entry starts with a key length and key followed by a
count of the number of blocks in the file.  Each block entry is composed of
the min and max time for the block, the offset into the file where the block
is located and the the size of the block.

The index structure can provide efficient access to all blocks as well as the
ability to determine the cost associated with acessing a given key.  Given a key
and timestamp, we can determine whether a file contains the block for that
timestamp as well as where that block resides and how much data to read to
retrieve the block.  If we know we need to read all or multiple blocks in a
file, we can use the size to determine how much to read in a given IO.

┌────────────────────────────────────────────────────────────────────────────┐
│                                   Index                                    │
├─────────┬─────────┬──────┬───────┬─────────┬─────────┬────────┬────────┬───┤
│ Key Len │   Key   │ Type │ Count │Min Time │Max Time │ Offset │  Size  │...│
│ 2 bytes │ N bytes │1 byte│2 bytes│ 8 bytes │ 8 bytes │8 bytes │4 bytes │   │
└─────────┴─────────┴──────┴───────┴─────────┴─────────┴────────┴────────┴───┘

The last section is the footer that stores the offset of the start of the index.

┌─────────┐
│ Footer  │
├─────────┤
│Index Ofs│
│ 8 bytes │
└─────────┘
*/
~~~



##### Compactor的定义

~~~go
// Compactor merges multiple TSM files into new files or
// writes a Cache into 1 or more TSM files.
type Compactor struct {
	Dir  string
	Size int

	FileStore interface {
		NextGeneration() int
		TSMReader(path string) *TSMReader
	}

	// RateLimit is the limit for disk writes for all concurrent compactions.
	RateLimit limiter.Rate

	formatFileName FormatFileNameFunc
	parseFileName  ParseFileNameFunc

	mu                 sync.RWMutex
	snapshotsEnabled   bool
	compactionsEnabled bool

	// lastSnapshotDuration is the amount of time the last snapshot took to complete.
	lastSnapshotDuration time.Duration

	snapshotLatencies *latencies

	// The channel to signal that any in progress snapshots should be aborted.
	snapshotsInterrupt chan struct{}
	// The channel to signal that any in progress level compactions should be aborted.
	compactionsInterrupt chan struct{}

	files map[string]struct{}
}
~~~



##### NewCompactor

~~~go
// NewCompactor returns a new instance of Compactor.
func NewCompactor() *Compactor {
	return &Compactor{
        //DefaultFormatFileName 定义在file_store.go中
		formatFileName: DefaultFormatFileName,
		parseFileName:  DefaultParseFileName,
	}
}
~~~



##### NewDefaultPlanner

~~~go
func NewDefaultPlanner(fs fileStore, writeColdDuration time.Duration) *DefaultPlanner {
	return &DefaultPlanner{
		FileStore:                    fs,
		compactFullWriteColdDuration: writeColdDuration,
		filesInUse:                   make(map[string]struct{}),
	}
}
~~~



### 写缓存到磁盘

<font color="red">每个快照都会写到一个新文件么？</font>

##### Compactor.WriteSnapshot 写缓存快照



Engine.writeSnapshotAndCommit 调用此函数

* 检查是否允许写快照
* 调用cache.Count函数，获取field的值的数目。若值的数目超过30万，则采用并发写
* 

~~~go
// WriteSnapshot writes a Cache snapshot to one or more new TSM files.
func (c *Compactor) WriteSnapshot(cache *Cache) ([]string, error) {
	c.mu.RLock()
	enabled := c.snapshotsEnabled
	intC := c.snapshotsInterrupt
	c.mu.RUnlock()

	if !enabled {
		return nil, errSnapshotsDisabled
	}

    //获取值的数目
	start := time.Now()
	card := cache.Count()

    //值的数目小于30万 并且快照延迟小于15秒
	// Enable throttling if we have lower cardinality or snapshots are going fast.
	throttle := card < 3e6 && c.snapshotLatencies.avg() < 15*time.Second

    //2e6 就是20万
	// Write snapshost concurrently if cardinality is relatively high.
	concurrency := card / 2e6
	if concurrency < 1 {
		concurrency = 1
	}

    //大于30万,提高写的并发数
	// Special case very high cardinality, use max concurrency and don't throttle writes.
	if card >= 3e6 {
		concurrency = 4
		throttle = false
	}

	splits := cache.Split(concurrency)

	type res struct {
		files []string
		err   error
	}

	resC := make(chan res, concurrency)
	for i := 0; i < concurrency; i++ {
		go func(sp *Cache) {
			iter := NewCacheKeyIterator(sp, tsdb.DefaultMaxPointsPerBlock, intC)
			files, err := c.writeNewFiles(c.FileStore.NextGeneration(), 0, nil, iter, throttle)
			resC <- res{files: files, err: err}

		}(splits[i])
	}

	var err error
	files := make([]string, 0, concurrency)
	for i := 0; i < concurrency; i++ {
		result := <-resC
		if result.err != nil {
			err = result.err
		}
		files = append(files, result.files...)
	}

	dur := time.Since(start).Truncate(time.Second)

	c.mu.Lock()

	// See if we were disabled while writing a snapshot
	enabled = c.snapshotsEnabled
	c.lastSnapshotDuration = dur
	c.snapshotLatencies.add(time.Since(start))
	c.mu.Unlock()

	if !enabled {
		return nil, errSnapshotsDisabled
	}

	return files, err
}
~~~



##### Compactor.writeNewFiles

Compactor.WriteSnapshot调用此函数

~~~go
// writeNewFiles writes from the iterator into new TSM files, rotating
// to a new file once it has reached the max TSM file size.
func (c *Compactor) writeNewFiles(generation, sequence int, src []string, iter KeyIterator, throttle bool) ([]string, error) {
	// These are the new TSM files written
	var files []string

	for {
		sequence++

        //gen-seq 9位宽度的数字
        //.influxdb/data/数据库名称/policy/shard_id/generation-sequence.tsm.tmp
        //TSMFileExtension的值是tsm
        //TmpTSMFileExtension的值是tmp
		// New TSM files are written to a temp file and renamed when fully completed.
		fileName := filepath.Join(c.Dir, c.formatFileName(generation, sequence)+"."+TSMFileExtension+"."+TmpTSMFileExtension)

		// Write as much as possible to this file
		err := c.write(fileName, iter, throttle)

        //若TSM文件大小超过2G，则返回errMaxFileExceeded, 单个key的块数超过65535则返回ErrMaxBlocksExceeded
		// We've hit the max file limit and there is more to write.  Create a new file
		// and continue.
		if err == errMaxFileExceeded || err == ErrMaxBlocksExceeded {
			files = append(files, fileName)
			continue
		} else if err == ErrNoValues {
			// If the file only contained tombstoned entries, then it would be a 0 length
			// file that we can drop.
			if err := os.RemoveAll(fileName); err != nil {
				return nil, err
			}
			break
		} else if _, ok := err.(errCompactionInProgress); ok {
			// Don't clean up the file as another compaction is using it.  This should not happen as the
			// planner keeps track of which files are assigned to compaction plans now.
			return nil, err
		} else if err != nil {
			// Remove any tmp files we already completed
			for _, f := range files {
				if err := os.RemoveAll(f); err != nil {
					return nil, err
				}
			}
			// We hit an error and didn't finish the compaction.  Remove the temp file and abort.
			if err := os.RemoveAll(fileName); err != nil {
				return nil, err
			}
			return nil, err
		}

		files = append(files, fileName)
		break
	}

	return files, nil
}
~~~



##### Compactor.write 写.tsm文件

* 创建TSM文件
* 若KeyIterator索引超过64M则创建基于文件的索引缓存

~~~go
func (c *Compactor) write(path string, iter KeyIterator, throttle bool) (err error) {
	fd, err := os.OpenFile(path, os.O_CREATE|os.O_RDWR|os.O_EXCL, 0666)
	if err != nil {
		return errCompactionInProgress{err: err}
	}

	// syncingWriter ensures that whatever we wrap the above file descriptor in
	// it will always be able to be synced by the tsm writer, since it does
	// type assertions to attempt to sync.
	type syncingWriter interface {
		io.Writer
		Sync() error
	}

	// Create the write for the new TSM file.
	var (
		w           TSMWriter
		limitWriter syncingWriter = fd
	)

	if c.RateLimit != nil && throttle {
		limitWriter = limiter.NewWriterWithRate(fd, c.RateLimit)
	}

	// Use a disk based TSM buffer if it looks like we might create a big index
	// in memory.
    //所有key的大小超过64M
	if iter.EstimatedIndexSize() > 64*1024*1024 {
		w, err = NewTSMWriterWithDiskBuffer(limitWriter)
		if err != nil {
			return err
		}
	} else {
		w, err = NewTSMWriter(limitWriter)
		if err != nil {
			return err
		}
	}

	defer func() {
		closeErr := w.Close()
		if err == nil {
			err = closeErr
		}

		// Check for errors where we should not remove the file
		_, inProgress := err.(errCompactionInProgress)
		maxBlocks := err == ErrMaxBlocksExceeded
		maxFileSize := err == errMaxFileExceeded
		if inProgress || maxBlocks || maxFileSize {
			return
		}

		if err != nil {
			w.Remove()
		}
	}()

	for iter.Next() {
		c.mu.RLock()
		enabled := c.snapshotsEnabled || c.compactionsEnabled
		c.mu.RUnlock()

		if !enabled {
			return errCompactionAborted{}
		}
		// Each call to read returns the next sorted key (or the prior one if there are
		// more values to write).  The size of values will be less than or equal to our
		// chunk size (1000)
		key, minTime, maxTime, block, err := iter.Read()
		if err != nil {
			return err
		}

		if minTime > maxTime {
			return fmt.Errorf("invalid index entry for block. min=%d, max=%d", minTime, maxTime)
		}

        //单个key的块数超过65535
		// Write the key and value
		if err := w.WriteBlock(key, minTime, maxTime, block); err == ErrMaxBlocksExceeded {
			if err := w.WriteIndex(); err != nil {
				return err
			}
			return err
		} else if err != nil {
			return err
		}

        //maxTSMFileSize 的默认值是2G
		// If we have a max file size configured and we're over it, close out the file
        
		// and return the error.
		if w.Size() > maxTSMFileSize {
			if err := w.WriteIndex(); err != nil {
				return err
			}

			return errMaxFileExceeded
		}
	}//END FOR

	// Were there any errors encountered during iteration?
	if err := iter.Err(); err != nil {
		return err
	}

	// We're all done.  Close out the file.
	if err := w.WriteIndex(); err != nil {
		return err
	}
	return nil
}
~~~



### tsmWriter

influxdb/tsdb/engine/tsm1/writer.go

##### tsmWriter的定义

~~~go
// tsmWriter writes keys and values in the TSM format
type tsmWriter struct {
	wrapped io.Writer
	w       *bufio.Writer
	index   IndexWriter
	n       int64

	// The bytes written count of when we last fsync'd
	lastSync int64
}
~~~



##### NewTSMWriter

~~~go

// NewTSMWriter returns a new TSMWriter writing to w.
func NewTSMWriter(w io.Writer) (TSMWriter, error) {
	index := NewIndexWriter()
	return &tsmWriter{wrapped: w, w: bufio.NewWriterSize(w, 1024*1024), index: index}, nil
}
~~~



##### tsmWriter.WriteBlock 写入数据块

* 检查key的长度是否超过maxKeyLength(65535)
* 调用BlockType 确定块的类型
* 是否首次写入，若是首次写入，写入头部信息(magic number 和 version)
* 写入数据块的校验和和数据块
* 调用index.Add为新写的块添加索引

~~~go
// WriteBlock writes block for the given key and time range to the TSM file.  If the write
// exceeds max entries for a given key, ErrMaxBlocksExceeded is returned.  This indicates
// that the index is now full for this key and no future writes to this key will succeed.
func (t *tsmWriter) WriteBlock(key []byte, minTime, maxTime int64, block []byte) error {
    //65535
	if len(key) > maxKeyLength {
		return ErrMaxKeyLengthExceeded
	}

	// Nothing to write
	if len(block) == 0 {
		return nil
	}

    //根据block的第一个字节，确定类型
    //
	blockType, err := BlockType(block)
	if err != nil {
		return err
	}

    //写入魔数和版本号0x16D116D1
	// Write header only after we have some data to write.
	if t.n == 0 {
		if err := t.writeHeader(); err != nil {
			return err
		}
	}

	var checksum [crc32.Size]byte
	binary.BigEndian.PutUint32(checksum[:], crc32.ChecksumIEEE(block))

	_, err = t.w.Write(checksum[:])
	if err != nil {
		return err
	}

	n, err := t.w.Write(block)
	if err != nil {
		return err
	}
	n += len(checksum)

	// Record this block in index
	t.index.Add(key, blockType, minTime, maxTime, t.n, uint32(n))

	// Increment file position pointer (checksum + block len)
	t.n += int64(n)

    //fsyncEvery的值是25M
	// fsync the file periodically to avoid long pauses with very big files.
	if t.n-t.lastSync > fsyncEvery {
		if err := t.sync(); err != nil {
			return err
		}
		t.lastSync = t.n
	}

    //maxIndexEntries的值是65535
	if len(t.index.Entries(key)) >= maxIndexEntries {
		return ErrMaxBlocksExceeded
	}

	return nil
}
~~~



##### tsmWriter.WriteIndex  写索引

~~~go
// WriteIndex writes the index section of the file.  If there are no index entries to write,
// this returns ErrNoValues.
func (t *tsmWriter) WriteIndex() error {
	indexPos := t.n

	if t.index.KeyCount() == 0 {
		return ErrNoValues
	}

	// Set the destination file on the index so we can periodically
	// fsync while writing the index.
	if f, ok := t.wrapped.(syncer); ok {
		t.index.(*directIndex).f = f
	}

	// Write the index
	if _, err := t.index.WriteTo(t.w); err != nil {
		return err
	}

	var buf [8]byte
	binary.BigEndian.PutUint64(buf[:], uint64(indexPos))

	// Write the index index position
	_, err := t.w.Write(buf[:])
	return err
}
~~~



### IndexEntry

~~~go
// IndexEntry is the index information for a given block in a TSM file.
type IndexEntry struct {
	// The min and max time of all points stored in the block.
	MinTime, MaxTime int64

	// The absolute position in the file where this block is located.
	Offset int64

	// The size in bytes of the block in the file.
	Size uint32
}
~~~



##### IndexEntry.AppendTo

~~~~

// AppendTo writes a binary-encoded version of IndexEntry to b, allocating
// and returning a new slice, if necessary.
func (e *IndexEntry) AppendTo(b []byte) []byte {
	if len(b) < indexEntrySize {
		if cap(b) < indexEntrySize {
			b = make([]byte, indexEntrySize)
		} else {
			b = b[:indexEntrySize]
		}
	}

	binary.BigEndian.PutUint64(b[:8], uint64(e.MinTime))
	binary.BigEndian.PutUint64(b[8:16], uint64(e.MaxTime))
	binary.BigEndian.PutUint64(b[16:24], uint64(e.Offset))
	binary.BigEndian.PutUint32(b[24:28], uint32(e.Size))

	return b
}
~~~~



###  indexEntries

influxdb/tsdb/engine/tsm1/reader.go



~~~go
type indexEntries struct {
	Type    byte
	entries []IndexEntry
}
~~~



##### indexEntries.WriteTo

~~~go
func (a *indexEntries) WriteTo(w io.Writer) (total int64, err error) {
	var buf [indexEntrySize]byte
	var n int

	for _, entry := range a.entries {
		entry.AppendTo(buf[:])
		n, err = w.Write(buf[:])
		total += int64(n)
		if err != nil {
			return total, err
		}
	}

	return total, nil
}
~~~



### IndexWriter



##### directIndex的定义

~~~go
// directIndex is a simple in-memory index implementation for a TSM file.  The full index
// must fit in memory.
type directIndex struct {
	keyCount int
	size     uint32

	// The bytes written count of when we last fsync'd
	lastSync uint32
	fd       *os.File
	buf      *bytes.Buffer

	f syncer

	w *bufio.Writer

	key          []byte
	indexEntries *indexEntries
}
~~~



##### NewIndexWriter

~~~go
// NewIndexWriter returns a new IndexWriter.
func NewIndexWriter() IndexWriter {
	buf := bytes.NewBuffer(make([]byte, 0, 1024*1024))
	return &directIndex{buf: buf, w: bufio.NewWriter(buf)}
}
~~~



##### directIndex.Add 为数据块添加索引

参数：

* offset 数据块在磁盘上的位置

* 若是首次写入，写入头部信息key_len|key|type|count。

~~~go
/*
┌────────────────────────────────────────────────────────────────────────────┐
│                                   Index                                    │
├─────────┬─────────┬──────┬───────┬─────────┬─────────┬────────┬────────┬───┤
│ Key Len │   Key   │ Type │ Count │Min Time │Max Time │ Offset │  Size  │...│
│ 2 bytes │ N bytes │1 byte│2  │ 8 bytes │ 8 bytes │8 bytes │4 bytes │   │
└─────────┴─────────┴──────┴───────┴─────────┴─────────┴────────┴────────┴───┘
*/

func (d *directIndex) Add(key []byte, blockType byte, minTime, maxTime int64, offset int64, size uint32) {
	// Is this the first block being added?
	if len(d.key) == 0 {
		// size of the key stored in the index
		d.size += uint32(2 + len(key))
        
        //indexCountSize的值是2 索引数目占用2字节
		// size of the count of entries stored in the index
		d.size += indexCountSize

		d.key = key
		if d.indexEntries == nil {
			d.indexEntries = &indexEntries{}
		}
		d.indexEntries.Type = blockType
		d.indexEntries.entries = append(d.indexEntries.entries, IndexEntry{
			MinTime: minTime,
			MaxTime: maxTime,
			Offset:  offset,
			Size:    size,
		})

        //indexEntrySize 的值是常量28
		// size of the encoded index entry
		d.size += indexEntrySize
		d.keyCount++
		return
	}

	// See if were still adding to the same series key.
	cmp := bytes.Compare(d.key, key)
	if cmp == 0 {
		// The last block is still this key
		d.indexEntries.entries = append(d.indexEntries.entries, IndexEntry{
			MinTime: minTime,
			MaxTime: maxTime,
			Offset:  offset,
			Size:    size,
		})

        //indexEntryS/.lkjher645zXC VBNM./
\
		// size of the encoded index entry
		d.size += indexEntrySize

        //d.key < key
	} else if cmp < 0 {
        //d.flush 写入buffer
		d.flush(d.w)
		// We have a new key that is greater than the last one so we need to add
		// a new index block section.

		// size of the key stored in the index
		d.size += uint32(2 + len(key))
		// size of the count of entries stored in the index
		d.size += indexCountSize

		d.key = key
		d.indexEntries.Type = blockType
		d.indexEntries.entries = append(d.indexEntries.entries, IndexEntry{
			MinTime: minTime,
			MaxTime: maxTime,
			Offset:  offset,
			Size:    size,
		})

		// size of the encoded index entry
		d.size += indexEntrySize
		d.keyCount++
	} else {
		// Keys can't be added out of order.
		panic(fmt.Sprintf("keys must be added in sorted order: %s < %s", string(key), string(d.key)))
	}
}
~~~



##### directIndex.WriteTo

~~~go
func (d *directIndex) WriteTo(w io.Writer) (int64, error) {
	if _, err := d.flush(d.w); err != nil {
		return 0, err
	}

	if err := d.w.Flush(); err != nil {
		return 0, err
	}

	if d.fd == nil {
		return copyBuffer(d.f, w, d.buf, nil)
	}

	if _, err := d.fd.Seek(0, io.SeekStart); err != nil {
		return 0, err
	}

	return io.Copy(w, bufio.NewReaderSize(d.fd, 1024*1024))
}
~~~





##### directIndex.flush

~~~go
func (d *directIndex) flush(w io.Writer) (int64, error) {
	var (
		n   int
		err error
		buf [5]byte
		N   int64
	)

	if len(d.key) == 0 {
		return 0, nil
	}
	// For each key, individual entries are sorted by time
	key := d.key
	entries := d.indexEntries

    /*
    // Max number of blocks for a given key that can exist in a single file
	maxIndexEntries = (1 << (indexCountSize * 8)) - 1
	maxIndexEntries的值是65535
    */
	if entries.Len() > maxIndexEntries {
		return N, fmt.Errorf("key '%s' exceeds max index entries: %d > %d", key, entries.Len(), maxIndexEntries)
	}

	if !sort.IsSorted(entries) {
		sort.Sort(entries)
	}

    
	binary.BigEndian.PutUint16(buf[0:2], uint16(len(key)))
	buf[2] = entries.Type
	binary.BigEndian.PutUint16(buf[3:5], uint16(entries.Len()))

    //写入内容: len(key) | key
	// Append the key length and key
	if n, err = w.Write(buf[0:2]); err != nil {
		return int64(n) + N, fmt.Errorf("write: writer key length error: %v", err)
	}
	N += int64(n)

    
	if n, err = w.Write(key); err != nil {
		return int64(n) + N, fmt.Errorf("write: writer key error: %v", err)
	}
	N += int64(n)

    //写入内容: block type | count
	// Append the block type and count
	if n, err = w.Write(buf[2:5]); err != nil {
		return int64(n) + N, fmt.Errorf("write: writer block type and count error: %v", err)
	}
	N += int64(n)

    //写入内容:
	// Append each index entry for all blocks for this key
	var n64 int64
	if n64, err = entries.WriteTo(w); err != nil {
		return n64 + N, fmt.Errorf("write: writer entries error: %v", err)
	}
	N += n64

	d.key = nil
	d.indexEntries.Type = 0
	d.indexEntries.entries = d.indexEntries.entries[:0]

	// If this is a disk based index and we've written more than the fsync threshold,
	// fsync the data to avoid long pauses later on.
	if d.fd != nil && d.size-d.lastSync > fsyncEvery {
		if err := d.fd.Sync(); err != nil {
			return N, err
		}
		d.lastSync = d.size
	}

	return N, nil

}
~~~



### cacheKeyIterator

cacheKeyIterator 是以chan为基础的迭代器，负责将数据序列化

##### NewCacheKeyIterator

参数：

* size 指定每个块的最大point数目，默认1000





* 调用cache.Keys()返回所有的key

~~~go
// NewCacheKeyIterator returns a new KeyIterator from a Cache.
func NewCacheKeyIterator(cache *Cache, size int, interrupt chan struct{}) KeyIterator {
	keys := cache.Keys()

	chans := make([]chan struct{}, len(keys))
	for i := 0; i < len(keys); i++ {
		chans[i] = make(chan struct{}, 1)
	}

	cki := &cacheKeyIterator{
		i:         -1,
		size:      size,
		cache:     cache,
		order:     keys,
		ready:     chans,
		blocks:    make([][]cacheBlock, len(keys)),
		interrupt: interrupt,
	}
	go cki.encode()
	return cki
}
~~~



##### cacheKeyIterator.encode 数据编码

~~~go
func (c *cacheKeyIterator) encode() {
	concurrency := runtime.GOMAXPROCS(0)
	n := len(c.ready)

	// Divide the keyset across each CPU
	chunkSize := 1
	idx := uint64(0)

	for i := 0; i < concurrency; i++ {
		// Run one goroutine per CPU and encode a section of the key space concurrently
		go func() {
            //tsdb.DefaultMaxPointsPerBlock的值是1000，定义在influxdb/tsdb/config.go中
			tenc := getTimeEncoder(tsdb.DefaultMaxPointsPerBlock)
			fenc := getFloatEncoder(tsdb.DefaultMaxPointsPerBlock)
			benc := getBooleanEncoder(tsdb.DefaultMaxPointsPerBlock)
			uenc := getUnsignedEncoder(tsdb.DefaultMaxPointsPerBlock)
			senc := getStringEncoder(tsdb.DefaultMaxPointsPerBlock)
			ienc := getIntegerEncoder(tsdb.DefaultMaxPointsPerBlock)

			defer putTimeEncoder(tenc)
			defer putFloatEncoder(fenc)
			defer putBooleanEncoder(benc)
			defer putUnsignedEncoder(uenc)
			defer putStringEncoder(senc)
			defer putIntegerEncoder(ienc)

			for {
                //为啥不是直接atomic.AddUint64(&idx, 1)
				i := int(atomic.AddUint64(&idx, uint64(chunkSize))) - chunkSize

				if i >= n {
					break
				}

				key := c.order[i]
				values := c.cache.values(key)

				for len(values) > 0 {

					end := len(values)
					if end > c.size {
						end = c.size
					}

					minTime, maxTime := values[0].UnixNano(), values[end-1].UnixNano()
					var b []byte
					var err error

					switch values[0].(type) {
					case FloatValue:
						b, err = encodeFloatBlockUsing(nil, values[:end], tenc, fenc)
					case IntegerValue:
						b, err = encodeIntegerBlockUsing(nil, values[:end], tenc, ienc)
					case UnsignedValue:
						b, err = encodeUnsignedBlockUsing(nil, values[:end], tenc, uenc)
					case BooleanValue:
						b, err = encodeBooleanBlockUsing(nil, values[:end], tenc, benc)
					case StringValue:
						b, err = encodeStringBlockUsing(nil, values[:end], tenc, senc)
					default:
						b, err = Values(values[:end]).Encode(nil)
					}

					values = values[end:]

					c.blocks[i] = append(c.blocks[i], cacheBlock{
						k:       key,
						minTime: minTime,
						maxTime: maxTime,
						b:       b,
						err:     err,
					})

					if err != nil {
						c.err = err
					}
				}
				// Notify this key is fully encoded
				c.ready[i] <- struct{}{}
			}//end for
		}()//end go
	}
}
~~~



##### cacheKeyIterator.Next

读完一个blocks，再读取下一个

~~~go
func (c *cacheKeyIterator) Next() bool {
    //对c.blocks的使用，不会有并发问题么
	if c.i >= 0 && c.i < len(c.ready) && len(c.blocks[c.i]) > 0 {
		c.blocks[c.i] = c.blocks[c.i][1:]
		if len(c.blocks[c.i]) > 0 {
			return true
		}
	}
    //c.i的初始值是-1
	c.i++

    //读完
	if c.i >= len(c.ready) {
		return false
	}

	<-c.ready[c.i]
	return true
}
~~~



##### cacheKeyIterator.Read

~~~go
func (c *cacheKeyIterator) Read() ([]byte, int64, int64, []byte, error) {
	// See if snapshot compactions were disabled while we were running.
	select {
	case <-c.interrupt:
		c.err = errCompactionAborted{}
		return nil, 0, 0, nil, c.err
	default:
	}

	blk := c.blocks[c.i][0]
	return blk.k, blk.minTime, blk.maxTime, blk.b, blk.err
}
~~~



















