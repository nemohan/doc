# compact

[TOC]



## LeveldCompactor

感觉这部分代码写的不咋滴

##### LeveledCompactor.Compact

~~~go
// Compact creates a new block in the compactor's directory from the blocks in the
// provided directories.
func (c *LeveledCompactor) Compact(dest string, dirs []string, open []*Block) (uid ulid.ULID, err error) {
	var (
		blocks []BlockReader
		bs     []*Block
		metas  []*BlockMeta
		uids   []string
	)
	start := time.Now()

	for _, d := range dirs {
		meta, _, err := readMetaFile(d)
		if err != nil {
			return uid, err
		}

		var b *Block

		// Use already open blocks if we can, to avoid
		// having the index data in memory twice.
		for _, o := range open {
			if meta.ULID == o.Meta().ULID {
				b = o
				break
			}
		}

		if b == nil {
			var err error
			b, err = OpenBlock(c.logger, d, c.chunkPool)
			if err != nil {
				return uid, err
			}
			defer b.Close()
		}

		metas = append(metas, meta)
		blocks = append(blocks, b)
		bs = append(bs, b)
		uids = append(uids, meta.ULID.String())
	}

	uid = ulid.MustNew(ulid.Now(), rand.Reader)

	meta := CompactBlockMetas(uid, metas...)
	err = c.write(dest, meta, blocks...)
	if err == nil {
		if meta.Stats.NumSamples == 0 {
			for _, b := range bs {
				b.meta.Compaction.Deletable = true
				n, err := writeMetaFile(c.logger, b.dir, &b.meta)
				if err != nil {
					level.Error(c.logger).Log(
						"msg", "Failed to write 'Deletable' to meta file after compaction",
						"ulid", b.meta.ULID,
					)
				}
				b.numBytesMeta = n
			}
			uid = ulid.ULID{}
			level.Info(c.logger).Log(
				"msg", "compact blocks resulted in empty block",
				"count", len(blocks),
				"sources", fmt.Sprintf("%v", uids),
				"duration", time.Since(start),
			)
		} else {
			level.Info(c.logger).Log(
				"msg", "compact blocks",
				"count", len(blocks),
				"mint", meta.MinTime,
				"maxt", meta.MaxTime,
				"ulid", meta.ULID,
				"sources", fmt.Sprintf("%v", uids),
				"duration", time.Since(start),
			)
		}
		return uid, nil
	}

	errs := tsdb_errors.NewMulti(err)
	if err != context.Canceled {
		for _, b := range bs {
			if err := b.setCompactionFailed(); err != nil {
				errs.Add(errors.Wrapf(err, "setting compaction failed for block: %s", b.Dir()))
			}
		}
	}

	return uid, errs.Err()
}
~~~



### 缓存数据刷盘

LeveldCompactor负责将缓存数据写入磁盘

##### LeveldCompactor.Write 写缓存数据

参数

* b 实际是RangeHead

~~~go
func (c *LeveledCompactor) Write(dest string, b BlockReader, mint, maxt int64, parent *BlockMeta) (ulid.ULID, error) {
	start := time.Now()

    //生成一个唯一id
	uid := ulid.MustNew(ulid.Now(), rand.Reader)

    //块所覆盖的series的时间范围
	meta := &BlockMeta{
		ULID:    uid,
		MinTime: mint,
		MaxTime: maxt,
	}
	meta.Compaction.Level = 1
	meta.Compaction.Sources = []ulid.ULID{uid}

	if parent != nil {
		meta.Compaction.Parents = []BlockDesc{
			{ULID: parent.ULID, MinTime: parent.MinTime, MaxTime: parent.MaxTime},
		}
	}

	err := c.write(dest, meta, b)
	if err != nil {
		return uid, err
	}

	if meta.Stats.NumSamples == 0 {
		level.Info(c.logger).Log(
			"msg", "write block resulted in empty block",
			"mint", meta.MinTime,
			"maxt", meta.MaxTime,
			"duration", time.Since(start),
		)
		return ulid.ULID{}, nil
	}

	level.Info(c.logger).Log(
		"msg", "write block",
		"mint", meta.MinTime,
		"maxt", meta.MaxTime,
		"ulid", meta.ULID,
		"duration", time.Since(start),
	)
	return uid, nil
}
~~~



#####  LeveledCompactor.write

* 数据写到临时目录./data/ulid.tmp-for-creation
* 创建索引

~~~go
// write creates a new block that is the union of the provided blocks into dir.
func (c *LeveledCompactor) write(dest string, meta *BlockMeta, blocks ...BlockReader) (err error) {
    //.data/ulid
	dir := filepath.Join(dest, meta.ULID.String())
    
    //tmpForCreationBlockDirSuffx 是字符串常量".tmp-for-creation"
	tmp := dir + tmpForCreationBlockDirSuffix
	var closers []io.Closer
	defer func(t time.Time) {
		err = tsdb_errors.NewMulti(err, tsdb_errors.CloseAll(closers)).Err()

		// RemoveAll returns no error when tmp doesn't exist so it is safe to always run it.
		if err := os.RemoveAll(tmp); err != nil {
			level.Error(c.logger).Log("msg", "removed tmp folder after failed compaction", "err", err.Error())
		}
		c.metrics.ran.Inc()
		c.metrics.duration.Observe(time.Since(t).Seconds())
	}(time.Now())

	if err = os.RemoveAll(tmp); err != nil {
		return err
	}

	if err = os.MkdirAll(tmp, 0777); err != nil {
		return err
	}

	// Populate chunk and index files into temporary directory with
	// data of all blocks.
	var chunkw ChunkWriter

    //chunkDir 定义在block.go 中, ./data/ulid.tmp-for-creation/chunks/
	chunkw, err = chunks.NewWriter(chunkDir(tmp))
	if err != nil {
		return errors.Wrap(err, "open chunk writer")
	}
	closers = append(closers, chunkw)
	// Record written chunk sizes on level 1 compactions.
	if meta.Compaction.Level == 1 {
		chunkw = &instrumentedChunkWriter{
			ChunkWriter: chunkw,
			size:        c.metrics.chunkSize,
			samples:     c.metrics.chunkSamples,
			trange:      c.metrics.chunkRange,
		}
	}

    //indexFilename 是字符串常量 "index" 定义在block.go中
    //./data/ulid.tmp-for-creation/index
	indexw, err := index.NewWriter(c.ctx, filepath.Join(tmp, indexFilename))
	if err != nil {
		return errors.Wrap(err, "open index writer")
	}
	closers = append(closers, indexw)

	if err := c.populateBlock(blocks, meta, indexw, chunkw); err != nil {
		return errors.Wrap(err, "populate block")
	}

	select {
	case <-c.ctx.Done():
		return c.ctx.Err()
	default:
	}

	// We are explicitly closing them here to check for error even
	// though these are covered under defer. This is because in Windows,
	// you cannot delete these unless they are closed and the defer is to
	// make sure they are closed if the function exits due to an error above.
	errs := tsdb_errors.NewMulti()
	for _, w := range closers {
		errs.Add(w.Close())
	}
	closers = closers[:0] // Avoid closing the writers twice in the defer.
	if errs.Err() != nil {
		return errs.Err()
	}

	// Populated block is empty, so exit early.
	if meta.Stats.NumSamples == 0 {
		return nil
	}

    //写meta文件
	if _, err = writeMetaFile(c.logger, tmp, meta); err != nil {
		return errors.Wrap(err, "write merged meta")
	}

	// Create an empty tombstones file.
	if _, err := tombstones.WriteFile(c.logger, tmp, tombstones.NewMemTombstones()); err != nil {
		return errors.Wrap(err, "write new tombstones file")
	}

	df, err := fileutil.OpenDir(tmp)
	if err != nil {
		return errors.Wrap(err, "open temporary block dir")
	}
	defer func() {
		if df != nil {
			df.Close()
		}
	}()

	if err := df.Sync(); err != nil {
		return errors.Wrap(err, "sync temporary dir file")
	}

	// Close temp dir before rename block dir (for windows platform).
	if err = df.Close(); err != nil {
		return errors.Wrap(err, "close temporary dir")
	}
	df = nil

	// Block successfully written, make it visible in destination dir by moving it from tmp one.
	if err := fileutil.Replace(tmp, dir); err != nil {
		return errors.Wrap(err, "rename block dir")
	}

	return nil
}
~~~



##### LeveledCompactor.populateBlock 写索引和数据文件

* 调用index.Writer.AddSymbols写符号

~~~go
// populateBlock fills the index and chunk writers with new data gathered as the union
// of the provided blocks. It returns meta information for the new block.
// It expects sorted blocks input by mint.
func (c *LeveledCompactor) populateBlock(blocks []BlockReader, meta *BlockMeta, indexw IndexWriter, chunkw ChunkWriter) (err error) {
	if len(blocks) == 0 {
		return errors.New("cannot populate block from no readers")
	}

	var (
		sets        []storage.ChunkSeriesSet
		symbols     index.StringIter
		closers     []io.Closer
		overlapping bool
	)
	defer func() {
		errs := tsdb_errors.NewMulti(err)
		if cerr := tsdb_errors.CloseAll(closers); cerr != nil {
			errs.Add(errors.Wrap(cerr, "close"))
		}
		err = errs.Err()
		c.metrics.populatingBlocks.Set(0)
	}()
	c.metrics.populatingBlocks.Set(1)

	globalMaxt := blocks[0].Meta().MaxTime
	for i, b := range blocks {
		select {
		case <-c.ctx.Done():
			return c.ctx.Err()
		default:
		}

		if !overlapping {
			if i > 0 && b.Meta().MinTime < globalMaxt {
				c.metrics.overlappingBlocks.Inc()
				overlapping = true
				level.Info(c.logger).Log("msg", "Found overlapping blocks during compaction", "ulid", meta.ULID)
			}
			if b.Meta().MaxTime > globalMaxt {
				globalMaxt = b.Meta().MaxTime
			}
		}

        //返回IndexReader接口类型, 实际是headIndexReader类型
		indexr, err := b.Index()
		if err != nil {
			return errors.Wrapf(err, "open index reader for block %+v", b.Meta())
		}
		closers = append(closers, indexr)

        //chunkr 实际是headChunkReader类型
		chunkr, err := b.Chunks()
		if err != nil {
			return errors.Wrapf(err, "open chunk reader for block %+v", b.Meta())
		}
		closers = append(closers, chunkr)

		tombsr, err := b.Tombstones()
		if err != nil {
			return errors.Wrapf(err, "open tombstone reader for block %+v", b.Meta())
		}
		closers = append(closers, tombsr)

        //k, v 都是空字符串""
		k, v := index.AllPostingsKey()
        
        //返回所有的series 的id
		all, err := indexr.Postings(k, v)
		if err != nil {
			return err
		}
		all = indexr.SortedPostings(all)
        
        //这为啥搞得如此复杂，创建newBlockChunkSeriesSet意义何在
		// Blocks meta is half open: [min, max), so subtract 1 to ensure we don't hold samples with exact meta.MaxTime timestamp.
		sets = append(sets, newBlockChunkSeriesSet(indexr, chunkr, tombsr, all, meta.MinTime, meta.MaxTime-1))
        
        //返回index.StringIter 接口类型
        //但实际是 index.stringListIter类型,遍历symbol数组
        //symbols是所有的lables的键值对
		syms := indexr.Symbols()
        
		if i == 0 {
			symbols = syms
			continue
		}
		symbols = NewMergedStringIter(symbols, syms)
	}//end for=========================================
    
	
    //symbol 写入索引文件, 已经排好顺序
	for symbols.Next() {
		if err := indexw.AddSymbol(symbols.At()); err != nil {
			return errors.Wrap(err, "add symbol")
		}
	}
	if symbols.Err() != nil {
		return errors.Wrap(symbols.Err(), "next symbol")
	}

	var (
		ref  = uint64(0)
		chks []chunks.Meta
	)

	set := sets[0]
    //什么时候sets > 1
	if len(sets) > 1 {
		// Merge series using compacting chunk series merger.
		set = storage.NewMergeChunkSeriesSet(sets, storage.NewCompactingChunkSeriesMerger(storage.ChainedSeriesMerge))
	}

	// Iterate over all sorted chunk series.
	for set.Next() {
		select {
		case <-c.ctx.Done():
			return c.ctx.Err()
		default:
		}
		s := set.At()
        //s.Iterator 实际返回的玩意： populateWithDelChunkSeriesIterator
		chksIter := s.Iterator()
		chks = chks[:0]
		for chksIter.Next() {
			// We are not iterating in streaming way over chunk as it's more efficient to do bulk write for index and
			// chunk file purposes.
			chks = append(chks, chksIter.At())
		}
		if chksIter.Err() != nil {
			return errors.Wrap(chksIter.Err(), "chunk iter")
		}

		// Skip the series with all deleted chunks.
		if len(chks) == 0 {
			continue
		}

        //写chunk
		if err := chunkw.WriteChunks(chks...); err != nil {
			return errors.Wrap(err, "write chunks")
		}
		if err := indexw.AddSeries(ref, s.Labels(), chks...); err != nil {
			return errors.Wrap(err, "add series")
		}

		meta.Stats.NumChunks += uint64(len(chks))
		meta.Stats.NumSeries++
		for _, chk := range chks {
			meta.Stats.NumSamples += uint64(chk.Chunk.NumSamples())
		}

		for _, chk := range chks {
			if err := c.chunkPool.Put(chk.Chunk); err != nil {
				return errors.Wrap(err, "put chunk")
			}
		}
		ref++
	}
	if set.Err() != nil {
		return errors.Wrap(set.Err(), "iterate compaction set")
	}

	return nil
}
~~~

### blockBaseSeriesSet 这是个什么玩意

tsdb/querier.go

~~~go

// blockBaseSeriesSet allows to iterate over all series in the single block.
// Iterated series are trimmed with given min and max time as well as tombstones.
// See newBlockSeriesSet and newBlockChunkSeriesSet to use it for either sample or chunk iterating.
type blockBaseSeriesSet struct {
	p          index.Postings
	index      IndexReader
	chunks     ChunkReader
	tombstones tombstones.Reader
	mint, maxt int64

	currIterFn func() *populateWithDelGenericSeriesIterator
	currLabels labels.Labels

	bufChks []chunks.Meta
	bufLbls labels.Labels
	err     error

~~~





##### newBlockChunkSeriesSet

tsdb/querier.go中

~~~go
//storage.ChunkSeriesSet是接口类型
func newBlockChunkSeriesSet(i IndexReader, c ChunkReader, t tombstones.Reader, p index.Postings, mint, maxt int64) storage.ChunkSeriesSet {
	return &blockChunkSeriesSet{
		blockBaseSeriesSet{
			index:      i,
			chunks:     c,
			tombstones: t,
			p:          p,
			mint:       mint,
			maxt:       maxt,
			bufLbls:    make(labels.Labels, 0, 10),
		},
	}
}

func (b *blockBaseSeriesSet) Next() bool {
    //b.p 是 index.Postings
	for b.p.Next() {
        //b.p.At 获取当前的series id.
        //获取获取series对应的labels 保存到b.bufLbls
        //chunk写入b.bufChks
        //调用的是headIndexReader.Series
		if err := b.index.Series(b.p.At(), &b.bufLbls, &b.bufChks); err != nil {
			// Postings may be stale. Skip if no underlying series exists.
			if errors.Cause(err) == storage.ErrNotFound {
				continue
			}
			b.err = errors.Wrapf(err, "get series %d", b.p.At())
			return false
		}

		if len(b.bufChks) == 0 {
			continue
		}

		intervals, err := b.tombstones.Get(b.p.At())
		if err != nil {
			b.err = errors.Wrap(err, "get tombstones")
			return false
		}

		// NOTE:
		// * block time range is half-open: [meta.MinTime, meta.MaxTime).
		// * chunks are both closed: [chk.MinTime, chk.MaxTime].
		// * requested time ranges are closed: [req.Start, req.End].

		var trimFront, trimBack bool

		// Copy chunks as iteratables are reusable.
		chks := make([]chunks.Meta, 0, len(b.bufChks))

		// Prefilter chunks and pick those which are not entirely deleted or totally outside of the requested range.
		for _, chk := range b.bufChks {
			if chk.MaxTime < b.mint {
				continue
			}
			if chk.MinTime > b.maxt {
				continue
			}

			if !(tombstones.Interval{Mint: chk.MinTime, Maxt: chk.MaxTime}.IsSubrange(intervals)) {
				chks = append(chks, chk)
			}

			// If still not entirely deleted, check if trim is needed based on requested time range.
			if chk.MinTime < b.mint {
				trimFront = true
			}
			if chk.MaxTime > b.maxt {
				trimBack = true
			}
		}

		if len(chks) == 0 {
			continue
		}

		if trimFront {
			intervals = intervals.Add(tombstones.Interval{Mint: math.MinInt64, Maxt: b.mint - 1})
		}
		if trimBack {
			intervals = intervals.Add(tombstones.Interval{Mint: b.maxt + 1, Maxt: math.MaxInt64})
		}

		b.currLabels = make(labels.Labels, len(b.bufLbls))
		copy(b.currLabels, b.bufLbls)

		b.currIterFn = func() *populateWithDelGenericSeriesIterator {
			return newPopulateWithDelGenericSeriesIterator(b.chunks, chks, intervals)
		}
		return true
	}//end for
	return false
}

//ChunkSeries 是接口类型
func (b *blockChunkSeriesSet) At() storage.ChunkSeries {
	// At can be looped over before iterating, so save the current value locally.
	currIterFn := b.currIterFn
	return &storage.ChunkSeriesEntry{
		Lset: b.currLabels,
        //currIterFn的返回结果是: populateWithDelGenericSeriesIterator
		ChunkIteratorFn: func() chunks.Iterator {
			return currIterFn().toChunkSeriesIterator()
		},
	}
}


~~~



### populateWithDelGenericSeriessIterator

这玩意的名字真是又臭又长

~~~go
// populateWithDelGenericSeriesIterator allows to iterate over given chunk metas. In each iteration it ensures
// that chunks are trimmed based on given tombstones interval if any.
//
// populateWithDelGenericSeriesIterator assumes that chunks that would be fully removed by intervals are filtered out in previous phase.
//
// On each iteration currChkMeta is available. If currDelIter is not nil, it means that chunk iterator in currChkMeta
// is invalid and chunk rewrite is needed, currDelIter should be used.
type populateWithDelGenericSeriesIterator struct {
	chunks ChunkReader
	// chks are expected to be sorted by minTime and should be related to the same, single series.
	chks []chunks.Meta

	i         int
	err       error
	bufIter   *DeletedIterator
	intervals tombstones.Intervals

	currDelIter chunkenc.Iterator
	currChkMeta chunks.Meta
}

func newPopulateWithDelGenericSeriesIterator(
	chunks ChunkReader,
	chks []chunks.Meta,
	intervals tombstones.Intervals,
) *populateWithDelGenericSeriesIterator {
	return &populateWithDelGenericSeriesIterator{
		chunks:    chunks,
		chks:      chks,
		i:         -1,
		bufIter:   &DeletedIterator{},
		intervals: intervals,
	}
}

func (p *populateWithDelGenericSeriesIterator) next() bool {
	if p.err != nil || p.i >= len(p.chks)-1 {
		return false
	}

	p.i++
	p.currChkMeta = p.chks[p.i]

    //调用的是headChunkReader.Chunk
	p.currChkMeta.Chunk, p.err = p.chunks.Chunk(p.currChkMeta.Ref)
	if p.err != nil {
		p.err = errors.Wrapf(p.err, "cannot populate chunk %d", p.currChkMeta.Ref)
		return false
	}

	p.bufIter.Intervals = p.bufIter.Intervals[:0]
	for _, interval := range p.intervals {
        //时间段是否有重叠
		if p.currChkMeta.OverlapsClosedInterval(interval.Mint, interval.Maxt) {
			p.bufIter.Intervals = p.bufIter.Intervals.Add(interval)
		}
	}

	// Re-encode head chunks that are still open (being appended to) or
	// outside the compacted MaxTime range.
	// The chunk.Bytes() method is not safe for open chunks hence the re-encoding.
	// This happens when snapshotting the head block or just fetching chunks from TSDB.
	//
	// TODO think how to avoid the typecasting to verify when it is head block.
	_, isSafeChunk := p.currChkMeta.Chunk.(*safeChunk)
	if len(p.bufIter.Intervals) == 0 && !(isSafeChunk && p.currChkMeta.MaxTime == math.MaxInt64) {
		// If there are no overlap with deletion intervals AND it's NOT an "open" head chunk, we can take chunk as it is.
		p.currDelIter = nil
		return true
	}

	// We don't want full chunk or it's potentially still opened, take just part of it.
	p.bufIter.Iter = p.currChkMeta.Chunk.Iterator(nil)
	p.currDelIter = p.bufIter
	return true
}

func (p *populateWithDelGenericSeriesIterator) Err() error { return p.err }

func (p *populateWithDelGenericSeriesIterator) toSeriesIterator() chunkenc.Iterator {
	return &populateWithDelSeriesIterator{populateWithDelGenericSeriesIterator: p}
}

func (p *populateWithDelGenericSeriesIterator) toChunkSeriesIterator() chunks.Iterator {
	return &populateWithDelChunkSeriesIterator{populateWithDelGenericSeriesIterator: p}
}
~~~



##### populateWithDelChunkSeriesIterator

~~~go
type populateWithDelChunkSeriesIterator struct {
	*populateWithDelGenericSeriesIterator

	curr chunks.Meta
}

func (p *populateWithDelChunkSeriesIterator) Next() bool {
    //调用 populateWithDelGenericSeriesIterator.next
	if !p.next() {
		return false
	}

	p.curr = p.currChkMeta
	if p.currDelIter == nil {
		return true
	}

	// Re-encode the chunk if iterator is provider. This means that it has some samples to be deleted or chunk is opened.
	newChunk := chunkenc.NewXORChunk()
	app, err := newChunk.Appender()
	if err != nil {
		p.err = err
		return false
	}

	if !p.currDelIter.Next() {
		if err := p.currDelIter.Err(); err != nil {
			p.err = errors.Wrap(err, "iterate chunk while re-encoding")
			return false
		}

		// Empty chunk, this should not happen, as we assume full deletions being filtered before this iterator.
		p.err = errors.Wrap(err, "populateWithDelChunkSeriesIterator: unexpected empty chunk found while rewriting chunk")
		return false
	}

	t, v := p.currDelIter.At()
	p.curr.MinTime = t
	app.Append(t, v)

	for p.currDelIter.Next() {
		t, v = p.currDelIter.At()
		app.Append(t, v)
	}
	if err := p.currDelIter.Err(); err != nil {
		p.err = errors.Wrap(err, "iterate chunk while re-encoding")
		return false
	}

	p.curr.Chunk = newChunk
	p.curr.MaxTime = t
	return true
}

func (p *populateWithDelChunkSeriesIterator) At() chunks.Meta { return p.curr }

~~~



## mergedStringIter

定义在tsdb/querier.go中

~~~go
// NewMergedStringIter returns string iterator that allows to merge symbols on demand and stream result.
func NewMergedStringIter(a index.StringIter, b index.StringIter) index.StringIter {
	return &mergedStringIter{a: a,
                             b: b, 
                             aok: a.Next(),
                             bok: b.Next()}
}

type mergedStringIter struct {
	a        index.StringIter
	b        index.StringIter
	aok, bok bool
	cur      string
}

func (m *mergedStringIter) Next() bool {
	if (!m.aok && !m.bok) || (m.Err() != nil) {
		return false
	}

	if !m.aok {
		m.cur = m.b.At()
		m.bok = m.b.Next()
	} else if !m.bok {
		m.cur = m.a.At()
		m.aok = m.a.Next()
	} else if m.b.At() > m.a.At() {
		m.cur = m.a.At()
		m.aok = m.a.Next()
	} else if m.a.At() > m.b.At() {
		m.cur = m.b.At()
		m.bok = m.b.Next()
	} else { // Equal.
		m.cur = m.b.At()
		m.aok = m.a.Next()
		m.bok = m.b.Next()
	}

	return true
}
func (m mergedStringIter) At() string { return m.cur }
func (m mergedStringIter) Err() error {
	if m.a.Err() != nil {
		return m.a.Err()
	}
	return m.b.Err()
}
~~~

