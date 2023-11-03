# compaction

[TOC]



## memTable 压缩

整体流程

![image-20230630173742749](D:\个人笔记\doc\db\leveldb\compaction.assets\image-20230630173742749.png)

rotateMem

<font color = 'gree'> rotateMem调度memTable后台写入level-0 的SSTable。并调用newMem创建新的memTable。在调度后台写入过程中，会等待写入完成，若调度三次都未写入完成会以panic报告</font>

~~~go
func (db *DB) rotateMem(n int, wait bool) (mem *memDB, err error) {
	retryLimit := 3
retry:
	// Wait for pending memdb compaction.
	err = db.compTriggerWait(db.mcompCmdC)
	if err != nil {
		return
	}
	retryLimit--

	// Create new memdb and journal.
	mem, err = db.newMem(n)
	if err != nil {
		if err == errHasFrozenMem {
			if retryLimit <= 0 {
				panic("BUG: still has frozen memdb")
			}
			goto retry
		}
		return
	}

	// Schedule memdb compaction.
	if wait {
		err = db.compTriggerWait(db.mcompCmdC)
	} else {
		db.compTrigger(db.mcompCmdC)
	}
	return
}
~~~



newMem创建新的memTable和.log文件。newMem创建新的memTable时，会检查之前的memTable是否已经被释放，若没有释放则会报错

~~~go
// Create new memdb and froze the old one; need external synchronization.
// newMem only called synchronously by the writer.
func (db *DB) newMem(n int) (mem *memDB, err error) {
	fd := storage.FileDesc{Type: storage.TypeJournal, Num: db.s.allocFileNum()}
	w, err := db.s.stor.Create(fd)
	if err != nil {
		db.s.reuseFileNum(fd.Num)
		return
	}

	db.memMu.Lock()
	defer db.memMu.Unlock()

	if db.frozenMem != nil {
		return nil, errHasFrozenMem
	}

	if db.journal == nil {
		db.journal = journal.NewWriter(w)
	} else {
		if err := db.journal.Reset(w); err != nil {
			return nil, err
		}
		if err := db.journalWriter.Close(); err != nil {
			return nil, err
		}
		db.frozenJournalFd = db.journalFd
	}
	db.journalWriter = w
	db.journalFd = fd
	db.frozenMem = db.mem
	mem = db.mpoolGet(n)
	mem.incref() // for self
	mem.incref() // for caller
	db.mem = mem
	// The seq only incremented by the writer. And whoever called newMem
	// should hold write lock, so no need additional synchronization here.
	db.frozenSeq = db.seq
	return
}
~~~



~~~go
// Send range compaction request.
func (db *DB) compTriggerRange(compC chan<- cCmd, level int, min, max []byte) (err error) {
	ch := make(chan error)
	defer close(ch)
	// Send cmd.
	select {
	case compC <- cRange{level, min, max, ch}:
	case err := <-db.compErrC:
		return err
	case <-db.closeC:
		return ErrClosed
	}
	// Wait cmd.
	select {
	case err = <-ch:
	case err = <-db.compErrC:
	case <-db.closeC:
		return ErrClosed
	}
	return err
}
~~~



~~~go
func (db *DB) mCompaction() {
	var x cCmd

	defer func() {
		if x := recover(); x != nil {
			if x != errCompactionTransactExiting {
				panic(x)
			}
		}
		if x != nil {
			x.ack(ErrClosed)
		}
		db.closeW.Done()
	}()

	for {
		select {
		//等待触发compaction的命令
		case x = <-db.mcompCmdC:
			switch x.(type) {
			case cAuto:
				//为什么等待compaction完成
				db.memCompaction()
				//回复触发compaction的
				x.ack(nil)
				x = nil
			default:
				panic("leveldb: unknown command")
			}
		case <-db.closeC:
			return
		}
	}
}
~~~



### memCompaction

* 检查memTable是否为空，为空则退出
* 暂停table compaction ????
* 调用compactionTransactFunc以类似于事务的方式创建SSTable并写入数据。实际写入工作由flushMemdb完成
* 调用db.compactionCommit将元信息写入MANIFEST文件。元信息包括: 新创建的SSTable的level、SSTable大小、最小的key、最大的key、文件名称使用的序号、已经使用的最大的key-value的序列号。db.compactionCommit会调用session.commit完成以下任务:1) 创建新的version

~~~go
func (db *DB) memCompaction() {
	mdb := db.getFrozenMem()
	if mdb == nil {
		return
	}
	defer mdb.decref()
	//记录mdb长度(key-value)个数及大小
	db.logf("memdb@flush N·%d S·%s", mdb.Len(), shortenb(int64(mdb.Size())))

	// Don't compact empty memdb.
	if mdb.Len() == 0 {
		db.logf("memdb@flush skipping")
		// drop frozen memdb
		db.dropFrozenMem()
		return
	}

	//为啥pause table compaction
	// Pause table compaction.
	resumeC := make(chan struct{})
	select {
	case db.tcompPauseC <- (chan<- struct{})(resumeC):
	case <-db.compPerErrC:
		close(resumeC)
		resumeC = nil
	case <-db.closeC:
		db.compactionExitTransact()
	}

	var (
		rec        = &sessionRecord{}
		stats      = &cStatStaging{}
		flushLevel int
	)

	// Generate tables.
	db.compactionTransactFunc("memdb@flush", func(cnt *compactionTransactCounter) (err error) {
		stats.startTimer()
		flushLevel, err = db.s.flushMemdb(rec, mdb.DB, db.memdbMaxLevel)
		stats.stopTimer()
		return
	}, func() error {
		for _, r := range rec.addedTables {
			db.logf("memdb@flush revert @%d", r.num)
			if err := db.s.stor.Remove(storage.FileDesc{Type: storage.TypeTable, Num: r.num}); err != nil {
				return err
			}
		}
		return nil
	})

	rec.setJournalNum(db.journalFd.Num)
	rec.setSeqNum(db.frozenSeq)

	// Commit.
	stats.startTimer()
	db.compactionCommit("memdb", rec)
	stats.stopTimer()

	db.logf("memdb@flush committed F·%d T·%v", len(rec.addedTables), stats.duration)

	// Save compaction stats
	for _, r := range rec.addedTables {
		stats.write += r.size
	}
	db.compStats.addStat(flushLevel, stats)
	atomic.AddUint32(&db.memComp, 1)

	// Drop frozen memdb.
	db.dropFrozenMem()

	// Resume table compaction.
	if resumeC != nil {
		select {
		case <-resumeC:
			close(resumeC)
		case <-db.closeC:
			db.compactionExitTransact()
		}
	}

	// Trigger table compaction.
	db.compTrigger(db.tcompCmdC)
}
~~~



### flushMemdb

* memTable创建迭代器
* level-0 的SSTable使用上一步创建的迭代器读取key-value并写入文件
* 将新创建SSTable的信息：SSTable归属的level、SSTable名称包含的序列号、文件大小、最小key、最大key记录到sessionRecord.addedTables中

~~~go
func (s *session) flushMemdb(rec *sessionRecord, mdb *memdb.DB, maxLevel int) (int, error) {
	// Create sorted table.
	iter := mdb.NewIterator(nil)
	defer iter.Release()
	t, n, err := s.tops.createFrom(iter)
	if err != nil {
		return 0, err
	}

	// Pick level other than zero can cause compaction issue with large
	// bulk insert and delete on strictly incrementing key-space. The
	// problem is that the small deletion markers trapped at lower level,
	// while key/value entries keep growing at higher level. Since the
	// key-space is strictly incrementing it will not overlaps with
	// higher level, thus maximum possible level is always picked, while
	// overlapping deletion marker pushed into lower level.
	// See: https://github.com/syndtr/goleveldb/issues/127.
	flushLevel := s.pickMemdbLevel(t.imin.ukey(), t.imax.ukey(), maxLevel)
	rec.addTableFile(flushLevel, t)

	s.logf("memdb@flush created L%d@%d N·%d S·%s %q:%q", flushLevel, t.fd.Num, n, shortenb(t.size), t.imin, t.imax)
	return flushLevel, nil
}
~~~



## SSTable 压缩



### SSTable 压缩触发条件

* level-0，SSTable数目超过DefaultCompactionL0Trigger（默认4）时，可以开始压缩
* 非level-0，所有SSTable总的大小超过某个阈值（默认10的level次方MB）的1倍时，可以开始压缩



computeCompaction会计算每个level适于压缩的分数，分数超过1时，表示对应的level可以压缩。计算规则如下:

* level-0，SSTable数目超过DefaultCompactionL0Trigger（默认4）时，可以开始压缩
* 非level-0，SSTable总的大小超过某个阈值（默认10的level次方MB）的1倍时，可以开始压缩

~~~go
func (v *version) needCompaction() bool {
	return v.cScore >= 1 || atomic.LoadPointer(&v.cSeek) != nil
}
func (v *version) computeCompaction() {
	// Precomputed best level for next compaction
	bestLevel := int(-1)
	bestScore := float64(-1)

	statFiles := make([]int, len(v.levels))
	statSizes := make([]string, len(v.levels))
	statScore := make([]string, len(v.levels))
	statTotSize := int64(0)

	for level, tables := range v.levels {
		var score float64
		size := tables.size()
		if level == 0 {
			// We treat level-0 specially by bounding the number of files
			// instead of number of bytes for two reasons:
			//
			// (1) With larger write-buffer sizes, it is nice not to do too
			// many level-0 compaction.
			//
			// (2) The files in level-0 are merged on every read and
			// therefore we wish to avoid too many files when the individual
			// file size is small (perhaps because of a small write-buffer
			// setting, or very high compression ratios, or lots of
			// overwrites/deletions).
			score = float64(len(tables)) / float64(v.s.o.GetCompactionL0Trigger())
		} else {
			score = float64(size) / float64(v.s.o.GetCompactionTotalSize(level))
		}

		if score > bestScore {
			bestLevel = level
			bestScore = score
		}

		statFiles[level] = len(tables)
		statSizes[level] = shortenb(size)
		statScore[level] = fmt.Sprintf("%.2f", score)
		statTotSize += size
	}

	v.cLevel = bestLevel
	v.cScore = bestScore

	v.s.logf("version@stat F·%v S·%s%v Sc·%v", statFiles, shortenb(statTotSize), statSizes, statScore)
}
~~~





### compaction 记录当前压缩状态信息

compaction代表压缩状态，主要包含以下信息:

* compaction.v 当前压缩对应的版本（即当前数据块的状态快照)
* compaction.typ 压缩类型，可取level0Compaction、nonLevel0Compaction、seekCompaction三个值
* sourceLevel 被压缩的level
* levels 被压缩的level对应的SSTable和level+1对应的SSTable
* gp level+2重叠的SSTable
* imin 参与压缩的最小的key
* imax 参与压缩的最大的key

~~~go
// compaction represent a compaction state.
type compaction struct {
	s *session
	v *version

	typ           int
	sourceLevel   int
	levels        [2]tFiles
	maxGPOverlaps int64

	gp                tFiles
	gpi               int
	seenKey           bool
	gpOverlappedBytes int64
	imin, imax        internalKey
	tPtrs             []int
	released          bool

	snapGPI               int
	snapSeenKey           bool
	snapGPOverlappedBytes int64
	snapTPtrs             []int
}
~~~



#### expand 确定level和level+1涉及到的需要压缩的表

~~~go
// Expand compacted tables; need external synchronization.
func (c *compaction) expand() {
	limit := int64(c.s.o.GetCompactionExpandLimit(c.sourceLevel))

	//被压缩的level包含的所有SSTaable
	vt0 := c.v.levels[c.sourceLevel]
	vt1 := tFiles{}

	//level +1 包含的所有SSTable
	if level := c.sourceLevel + 1; level < len(c.v.levels) {
		vt1 = c.v.levels[level]
	}

	//被压缩level的第一个文件, c.levels[1]此时为空, 即t1为空
	//++++++++++++++++++t0 可能只包含一个SSTable
	t0, t1 := c.levels[0], c.levels[1]
	imin, imax := t0.getRange(c.s.icmp)

	// For non-zero levels, the ukey can't hop across tables at all.
	if c.sourceLevel == 0 {
		//++++++++++++++++++找到和t0的key重叠的表
		// We expand t0 here just incase ukey hop across tables.
		t0 = vt0.getOverlaps(t0, c.s.icmp, imin.ukey(), imax.ukey(), c.sourceLevel == 0)
		//++++++++++++++++找到了重叠的表
		if len(t0) != len(c.levels[0]) {
			imin, imax = t0.getRange(c.s.icmp)
		}
	}
    
    //在level+1对应的全部SSTable中找到和level存在重叠的SSTable
	t1 = vt1.getOverlaps(t1, c.s.icmp, imin.ukey(), imax.ukey(), false)
    
    
	// Get entire range covered by compaction.
	amin, amax := append(t0, t1...).getRange(c.s.icmp)

	// See if we can grow the number of inputs in "sourceLevel" without
	// changing the number of "sourceLevel+1" files we pick up.
	if len(t1) > 0 {
		exp0 := vt0.getOverlaps(nil, c.s.icmp, amin.ukey(), amax.ukey(), c.sourceLevel == 0)
		if len(exp0) > len(t0) && t1.size()+exp0.size() < limit {
			xmin, xmax := exp0.getRange(c.s.icmp)
			exp1 := vt1.getOverlaps(nil, c.s.icmp, xmin.ukey(), xmax.ukey(), false)
			if len(exp1) == len(t1) {
				c.s.logf("table@compaction expanding L%d+L%d (F·%d S·%s)+(F·%d S·%s) -> (F·%d S·%s)+(F·%d S·%s)",
					c.sourceLevel, c.sourceLevel+1, len(t0), shortenb(t0.size()), len(t1), shortenb(t1.size()),
					len(exp0), shortenb(exp0.size()), len(exp1), shortenb(exp1.size()))
				imin, imax = xmin, xmax
				t0, t1 = exp0, exp1
				amin, amax = append(t0, t1...).getRange(c.s.icmp)
			}
		}
	}

	// Compute the set of grandparent files that overlap this compaction
	// (parent == sourceLevel+1; grandparent == sourceLevel+2)
	if level := c.sourceLevel + 2; level < len(c.v.levels) {
		c.gp = c.v.levels[level].getOverlaps(c.gp, c.s.icmp, amin.ukey(), amax.ukey(), false)
	}

	c.levels[0], c.levels[1] = t0, t1
	c.imin, c.imax = imin, imax
}
~~~



### SSTable压缩调度

tCompaction负责调度SSTable的压缩，大体流程如下：

* 调用db.tableNeedCompaction检查SSTable是否需要压缩，判断压缩的标准是1) level-0：SSTable数目超过DefaultCompactionL0Trigger（默认4）时，可以开始压缩。2）非level-0：SSTable总的大小超过某个阈值（默认10的level次方MB）的1倍时，可以开始压缩
* 若可以压缩，1)尝试从db.tcompCmdC读取命令，“写入”操作执行时通过写入db.tcompCmd来查询写入是否可以继续。level-0 SSTable文件数目超过某个阈值(默认12)时，需要暂停写入。2）尝试从db.tcompPauseC读取命令，是否需要暂停此次压缩。3）若等待"写入"的队列waitQ不为空，且level-0 SSTable数目小于阈值，则恢复等待"写入"的任务，并清空等待队列
* 若不可以压缩。1）恢复等待”写入“的任务，并清空等待队列。2）尝试从db.tcompCmdC读取命令，“写入”操作执行时通过写入db.tcompCmd来查询写入是否可以继续 3）尝试从db.tcompPauseC读取命令，是否需要暂停此次压缩

~~~go
func (db *DB) tCompaction() {
	var (
		x     cCmd
		waitQ []cCmd
	)

	defer func() {
		if x := recover(); x != nil {
			if x != errCompactionTransactExiting {
				panic(x)
			}
		}
		for i := range waitQ {
			waitQ[i].ack(ErrClosed)
			waitQ[i] = nil
		}
		if x != nil {
			x.ack(ErrClosed)
		}
		db.closeW.Done()
	}()

	for {
		//如果SSTable需要压缩
		if db.tableNeedCompaction() {
			select {
			//等待
			case x = <-db.tcompCmdC:

			//等待
			case ch := <-db.tcompPauseC:
				//等待可写入ch
				db.pauseCompaction(ch)
				continue
			case <-db.closeC:
				return
			default:
			}
			//等待队列不为空，且level-0文件数目小于 DefaultWriteL0PauseTrigger(默认值12)
			//通知"写"操作可继续
			// Resume write operation as soon as possible.
			if len(waitQ) > 0 && db.resumeWrite() {
				for i := range waitQ {
					waitQ[i].ack(nil)
					waitQ[i] = nil
				}
				waitQ = waitQ[:0]
			}
		} else { //没有SSTable需要压缩

			for i := range waitQ {
				waitQ[i].ack(nil)
				waitQ[i] = nil
			}
			waitQ = waitQ[:0]
			select {
			case x = <-db.tcompCmdC:
			case ch := <-db.tcompPauseC:
				db.pauseCompaction(ch)
				continue
			case <-db.closeC:
				return
			}
		}
		if x != nil {
			switch cmd := x.(type) {
			case cAuto:
				if cmd.ackC != nil {
					// Check the write pause state before caching it.
					if db.resumeWrite() {
						x.ack(nil)
					} else {
						waitQ = append(waitQ, x)
					}
				}
			case cRange:
				x.ack(db.tableRangeCompaction(cmd.level, cmd.min, cmd.max))
			default:
				panic("leveldb: unknown command")
			}
			x = nil
		}
		db.tableAutoCompaction()
	}
}

~~~



### SSTable压缩

tableCompaction的工作流程:

* 调用sessionRecord.addCompPtr记录被压缩的level，以及level、level+1中涉及到的被压缩的SSTable中最大的key

~~~go
func (db *DB) tableAutoCompaction() {
	if c := db.s.pickCompaction(); c != nil {
		db.tableCompaction(c, false)
	}
}

func (db *DB) tableCompaction(c *compaction, noTrivial bool) {
	defer c.release()

	rec := &sessionRecord{}
    //c.sourceLevel 为被压缩的文件所属的level
	rec.addCompPtr(c.sourceLevel, c.imax)

    //noTrivial
    //trivial在这的概念：被压缩的SSTable只有一个，且level+2 的大小
	if !noTrivial && c.trivial() {
		t := c.levels[0][0]
		db.logf("table@move L%d@%d -> L%d", c.sourceLevel, t.fd.Num, c.sourceLevel+1)
		rec.delTable(c.sourceLevel, t.fd.Num)
		rec.addTableFile(c.sourceLevel+1, t)
		db.compactionCommit("table-move", rec)
		return
	}

    //将被压缩的表，记录到sessionRecord.deletedTables字段中
    //记录被删除的表的信息，包括被删除的表所在的level、SSTable序列号
	var stats [2]cStatStaging
	for i, tables := range c.levels {
		for _, t := range tables {
			stats[i].read += t.size
			// Insert deleted tables into record
			rec.delTable(c.sourceLevel+i, t.fd.Num)
		}
	}
	sourceSize := stats[0].read + stats[1].read
	minSeq := db.minSeq()
	db.logf("table@compaction L%d·%d -> L%d·%d S·%s Q·%d", c.sourceLevel, len(c.levels[0]), c.sourceLevel+1, len(c.levels[1]), shortenb(sourceSize), minSeq)

	b := &tableCompactionBuilder{
		db:        db,
		s:         db.s,
		c:         c,
		rec:       rec,
		stat1:     &stats[1],
		minSeq:    minSeq,
		strict:    db.s.o.GetStrict(opt.StrictCompaction),
		tableSize: db.s.o.GetCompactionTableSize(c.sourceLevel + 1),
	}
	db.compactionTransact("table@build", b)

	// Commit.
	stats[1].startTimer()
	db.compactionCommit("table", rec)
	stats[1].stopTimer()

	resultSize := stats[1].write
	db.logf("table@compaction committed F%s S%s Ke·%d D·%d T·%v", sint(len(rec.addedTables)-len(rec.deletedTables)), sshortenb(resultSize-sourceSize), b.kerrCnt, b.dropCnt, stats[1].duration)

	// Save compaction stats
	for i := range stats {
		db.compStats.addStat(c.sourceLevel+1, &stats[i])
	}
	switch c.typ {
	case level0Compaction:
		atomic.AddUint32(&db.level0Comp, 1)
	case nonLevel0Compaction:
		atomic.AddUint32(&db.nonLevel0Comp, 1)
	case seekCompaction:
		atomic.AddUint32(&db.seekComp, 1)
	}
}
~~~



### 被压缩LEVEL 对应的文件选择策略

#### pickCompaction

* 若level 适于压缩的分数大于等于1时，1）若可压缩的是level-0，选择level中的第一个SSTable进行压缩
* 若v.cSeek不为空，？？？
* 否则没有满足压缩条件的表，退出

~~~go
func (s *session) pickCompaction() *compaction {
	v := s.version()

	var sourceLevel int
	var t0 tFiles
	var typ int
    
    //此时t0只包含一个文件
	if v.cScore >= 1 {
		sourceLevel = v.cLevel
		cptr := s.getCompPtr(sourceLevel)
		tables := v.levels[sourceLevel]
		if cptr != nil && sourceLevel > 0 {
			n := len(tables)
			//搜索第一个大于cptr的SSTable
			if i := sort.Search(n, func(i int) bool {
				return s.icmp.Compare(tables[i].imax, cptr) > 0
			}); i < n {
				t0 = append(t0, tables[i])
			}
		}
        //level 为 level-0或cptr为nil, 或没有找到大于cptr的SSTable
		if len(t0) == 0 {
			t0 = append(t0, tables[0])
		}
		if sourceLevel == 0 {
			typ = level0Compaction
		} else {
			typ = nonLevel0Compaction
		}
	} else {
        //t0 会有几个文件?????????????????
		if p := atomic.LoadPointer(&v.cSeek); p != nil {
			ts := (*tSet)(p)
			sourceLevel = ts.level
			t0 = append(t0, ts.table)
			typ = seekCompaction
		} else {
			v.release()
			return nil
		}
	}

	return newCompaction(s, v, sourceLevel, t0, typ)
}
~~~



## 影响压缩的参数

GetCompactionTableSize 压缩时生成对应的level的单个文件大小

* 默认2MB
* Options.CompactionTableSizeMultiplierPerLevel[level] * Options.CompactionTableSize
* (Options.CompactionTableSizeMultiplier ^ level) * Options.CompactionTableSize

~~~go
func (o *Options) GetCompactionTableSize(level int) int {
	var (
		base = DefaultCompactionTableSize //默认2MB
		mult float64
	)
	if o != nil {
		if o.CompactionTableSize > 0 {
			base = o.CompactionTableSize
		}
		if level < len(o.CompactionTableSizeMultiplierPerLevel) && o.CompactionTableSizeMultiplierPerLevel[level] > 0 {
			mult = o.CompactionTableSizeMultiplierPerLevel[level]
		} else if o.CompactionTableSizeMultiplier > 0 {
			mult = math.Pow(o.CompactionTableSizeMultiplier, float64(level))
		}
	}
	if mult == 0 {
        //DefaultCompactionTableSizeMultiplier 默认1.0
		mult = math.Pow(DefaultCompactionTableSizeMultiplier, float64(level))
	}
	return int(float64(base) * mult)
}
~~~

Options.GetCompactionExpandLimit 确定压缩过程中参与压缩的level+1文件总大小

~~~go
func (o *Options) GetCompactionExpandLimit(level int) int {
	factor := DefaultCompactionExpandLimitFactor
	if o != nil && o.CompactionExpandLimitFactor > 0 {
		factor = o.CompactionExpandLimitFactor
	}
	return o.GetCompactionTableSize(level+1) * factor
}

~~~

Options.GetCompactionSourceLimit 参与压缩的文件大小(被压缩的文件)

~~~
func (o *Options) GetCompactionSourceLimit(level int) int {
	factor := DefaultCompactionSourceLimitFactor
	if o != nil && o.CompactionSourceLimitFactor > 0 {
		factor = o.CompactionSourceLimitFactor
	}
	return o.GetCompactionTableSize(level+1) * factor
}
~~~



GetCompactionGPOverlaps  获取被压缩的level对应level+2的可能涉及到的SSTable的总大小

~~~go
func (o *Options) GetCompactionGPOverlaps(level int) int {
	factor := DefaultCompactionGPOverlapsFactor
	if o != nil && o.CompactionGPOverlapsFactor > 0 {
		factor = o.CompactionGPOverlapsFactor
	}
	return o.GetCompactionTableSize(level+2) * factor
}
~~~

### level包含的所有SSTable总大小阈值

~~~go
func (o *Options) GetCompactionTotalSize(level int) int64 {
	var (
		//10 MB
		base = DefaultCompactionTotalSize
		mult float64
	)
	if o != nil {
		if o.CompactionTotalSize > 0 {
			base = o.CompactionTotalSize
		}
		if level < len(o.CompactionTotalSizeMultiplierPerLevel) && o.CompactionTotalSizeMultiplierPerLevel[level] > 0 {
			mult = o.CompactionTotalSizeMultiplierPerLevel[level]
		} else if o.CompactionTotalSizeMultiplier > 0 {
			mult = math.Pow(o.CompactionTotalSizeMultiplier, float64(level))
		}
	}
	if mult == 0 {
        //DefaultCompactionTotalSizeMultiplier 默认10
		mult = math.Pow(DefaultCompactionTotalSizeMultiplier, float64(level))
	}
	return int64(float64(base) * mult)
}
~~~

