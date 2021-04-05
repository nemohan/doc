# index

[TOC]

tsi1 类型索引



##### 索引注册

~~~go

func init() {
	if os.Getenv("INFLUXDB_EXP_TSI_PARTITIONS") != "" {
		i, err := strconv.Atoi(os.Getenv("INFLUXDB_EXP_TSI_PARTITIONS"))
		if err != nil {
			panic(err)
		}
		DefaultPartitionN = uint64(i)
	}

	tsdb.RegisterIndex(IndexName, func(_ uint64, db, path string, _ *tsdb.SeriesIDSet, sfile *tsdb.SeriesFile, opt tsdb.EngineOptions) tsdb.Index {
		idx := NewIndex(sfile, db,
			WithPath(path),
			WithMaximumLogFileSize(int64(opt.Config.MaxIndexLogFileSize)),
			WithSeriesIDCacheSize(opt.Config.SeriesIDSetCacheSize),
		)
		return idx
	})
}
~~~



##### Index的定义

path: .influxdb/data/数据库/policy/shard_id/index

~~~go
// Index represents a collection of layered index files and WAL.
type Index struct {
	mu         sync.RWMutex
	partitions []*Partition
	opened     bool

	tagValueCache     *TagValueSeriesIDCache
	tagValueCacheSize int

	// The following may be set when initializing an Index.
	path               string      // Root directory of the index partitions.
	disableCompactions bool        // Initially disables compactions on the index.
	maxLogFileSize     int64       // Maximum size of a LogFile before it's compacted.
	logfileBufferSize  int         // The size of the buffer used by the LogFile.
	disableFsync       bool        // Disables flushing buffers and fsyning files. Used when working with indexes offline.
	logger             *zap.Logger // Index's logger.

	// The following must be set when initializing an Index.
	sfile    *tsdb.SeriesFile // series lookup file
	database string           // Name of database.

	// Cached sketches.
	mSketch, mTSketch estimator.Sketch // Measurement sketches
	sSketch, sTSketch estimator.Sketch // Series sketches

	// Index's version.
	version int

	// Number of partitions used by the index.
	PartitionN uint64
}
~~~



##### Index.CreateSeriesListIfNotExists

~~~go
// CreateSeriesListIfNotExists creates a list of series if they doesn't exist in bulk.
func (i *Index) CreateSeriesListIfNotExists(keys [][]byte, names [][]byte, tagsSlice []models.Tags) error {
	// All slices must be of equal length.
	if len(names) != len(tagsSlice) {
		return errors.New("names/tags length mismatch in index")
	}

	// We need to move different series into collections for each partition
	// to process.
	pNames := make([][][]byte, i.PartitionN)
	pTags := make([][]models.Tags, i.PartitionN)

	// Determine partition for series using each series key.
	for ki, key := range keys {
		pidx := i.partitionIdx(key)
		pNames[pidx] = append(pNames[pidx], names[ki])
		pTags[pidx] = append(pTags[pidx], tagsSlice[ki])
	}

	// Process each subset of series on each partition.
	n := i.availableThreads()

	// Store errors.
	errC := make(chan error, i.PartitionN)

	var pidx uint32 // Index of maximum Partition being worked on.
	for k := 0; k < n; k++ {
		go func() {
			for {
				idx := int(atomic.AddUint32(&pidx, 1) - 1) // Get next partition to work on.
				if idx >= len(i.partitions) {
					return // No more work.
				}

				ids, err := i.partitions[idx].createSeriesListIfNotExists(pNames[idx], pTags[idx])

				var updateCache bool
				for _, id := range ids {
					if id != 0 {
						updateCache = true
						break
					}
				}

				if !updateCache {
					errC <- err
					continue
				}

				// Some cached bitset results may need to be updated.
				i.tagValueCache.RLock()
				for j, id := range ids {
					if id == 0 {
						continue
					}

					name := pNames[idx][j]
					tags := pTags[idx][j]
					if i.tagValueCache.measurementContainsSets(name) {
						for _, pair := range tags {
							// TODO(edd): It's not clear to me yet whether it will be better to take a lock
							// on every series id set, or whether to gather them all up under the cache rlock
							// and then take the cache lock and update them all at once (without invoking a lock
							// on each series id set).
							//
							// Taking the cache lock will block all queries, but is one lock. Taking each series set
							// lock might be many lock/unlocks but will only block a query that needs that particular set.
							//
							// Need to think on it, but I think taking a lock on each series id set is the way to go.
							//
							// One other option here is to take a lock on the series id set when we first encounter it
							// and then keep it locked until we're done with all the ids.
							//
							// Note: this will only add `id` to the set if it exists.
							i.tagValueCache.addToSet(name, pair.Key, pair.Value, id) // Takes a lock on the series id set
						}
					}
				}
				i.tagValueCache.RUnlock()

				errC <- err
			}
		}()
	}

	// Check for error
	for i := 0; i < cap(errC); i++ {
		if err := <-errC; err != nil {
			return err
		}
	}

	// Update sketches under lock.
	i.mu.Lock()
	defer i.mu.Unlock()

	for _, key := range keys {
		i.sSketch.Add(key)
	}
	for _, name := range names {
		i.mSketch.Add(name)
	}

	return nil
}
~~~



##### Index.CreateSeriesIfNotExists



~~~~go
// CreateSeriesIfNotExists creates a series if it doesn't exist or is deleted.
func (i *Index) CreateSeriesIfNotExists(key, name []byte, tags models.Tags) error {
    //i.partition根据key的哈希值，确定其对应的Partition
	ids, err := i.partition(key).createSeriesListIfNotExists([][]byte{name}, []models.Tags{tags})
	if err != nil {
		return err
	}

	i.mu.Lock()
	i.sSketch.Add(key)
	i.mSketch.Add(name)
	i.mu.Unlock()

	if ids[0] == 0 {
		return nil // No new series, nothing further to update.
	}

	// If there are cached sets for any of the tag pairs, they will need to be
	// updated with the series id.
	i.tagValueCache.RLock()
	if i.tagValueCache.measurementContainsSets(name) {
		for _, pair := range tags {
			// TODO(edd): It's not clear to me yet whether it will be better to take a lock
			// on every series id set, or whether to gather them all up under the cache rlock
			// and then take the cache lock and update them all at once (without invoking a lock
			// on each series id set).
			//
			// Taking the cache lock will block all queries, but is one lock. Taking each series set
			// lock might be many lock/unlocks but will only block a query that needs that particular set.
			//
			// Need to think on it, but I think taking a lock on each series id set is the way to go.
			//
			// Note this will only add `id` to the set if it exists.
			i.tagValueCache.addToSet(name, pair.Key, pair.Value, ids[0]) // Takes a lock on the series id set
		}
	}
	i.tagValueCache.RUnlock()
	return nil
}
~~~~



##### Index.Open

~~~go
// Open opens the index.
func (i *Index) Open() error {
	i.mu.Lock()
	defer i.mu.Unlock()

	if i.opened {
		return errors.New("index already open")
	}

	// Ensure root exists.
	if err := os.MkdirAll(i.path, 0777); err != nil {
		return err
	}

	// Initialize index partitions.
	i.partitions = make([]*Partition, i.PartitionN)
	for j := 0; j < len(i.partitions); j++ {
		p := NewPartition(i.sfile, filepath.Join(i.path, fmt.Sprint(j)))
		p.MaxLogFileSize = i.maxLogFileSize
		p.nosync = i.disableFsync
		p.logbufferSize = i.logfileBufferSize
		p.logger = i.logger.With(zap.String("tsi1_partition", fmt.Sprint(j+1)))
		i.partitions[j] = p
	}

	// Open all the Partitions in parallel.
	partitionN := len(i.partitions)
	n := i.availableThreads()

	// Store results.
	errC := make(chan error, partitionN)

	// Run fn on each partition using a fixed number of goroutines.
	var pidx uint32 // Index of maximum Partition being worked on.
	for k := 0; k < n; k++ {
		go func(k int) {
			for {
				idx := int(atomic.AddUint32(&pidx, 1) - 1) // Get next partition to work on.
				if idx >= partitionN {
					return // No more work.
				}
				err := i.partitions[idx].Open()
				errC <- err
			}
		}(k)
	}

	// Check for error
	for i := 0; i < partitionN; i++ {
		if err := <-errC; err != nil {
			return err
		}
	}

	// Refresh cached sketches.
	if err := i.updateSeriesSketches(); err != nil {
		return err
	} else if err := i.updateMeasurementSketches(); err != nil {
		return err
	}

	// Mark opened.
	i.opened = true
	i.logger.Info(fmt.Sprintf("index opened with %d partitions", partitionN))
	return nil
}
~~~



## Partition

path: .influxdb/data/数据库名称/policy/shard_id/index/0-7



~~~go
// Partition represents a collection of layered index files and WAL.
type Partition struct {
	mu     sync.RWMutex
	opened bool

	sfile         *tsdb.SeriesFile // series lookup file
	activeLogFile *LogFile         // current log file
	fileSet       *FileSet         // current file set
	seq           int              // file id sequence

	// Fast series lookup of series IDs in the series file that have been present
	// in this partition. This set tracks both insertions and deletions of a series.
	seriesIDSet *tsdb.SeriesIDSet

	// Compaction management
	levels          []CompactionLevel // compaction levels
	levelCompacting []bool            // level compaction status

	// Close management.
	once    sync.Once
	closing chan struct{} // closing is used to inform iterators the partition is closing.

	// Fieldset shared with engine.
	fieldset *tsdb.MeasurementFieldSet

	currentCompactionN int // counter of in-progress compactions

	// Directory of the Partition's index files.
	path string
	id   string // id portion of path.

	// Log file compaction thresholds.
	MaxLogFileSize int64
	nosync         bool // when true, flushing and syncing of LogFile will be disabled.
	logbufferSize  int  // the LogFile's buffer is set to this value.

	// Frequency of compaction checks.
	compactionInterrupt chan struct{}
	compactionsDisabled int

	logger *zap.Logger

	// Current size of MANIFEST. Used to determine partition size.
	manifestSize int64

	// Index's version.
	version int
}

~~~



##### Partition.Open

~~~go
// Open opens the partition.
func (p *Partition) Open() error {
	p.mu.Lock()
	defer p.mu.Unlock()

	p.closing = make(chan struct{})

	if p.opened {
		return errors.New("index partition already open")
	}

	// Validate path is correct.
	p.id = filepath.Base(p.path)
	_, err := strconv.Atoi(p.id)
	if err != nil {
		return err
	}

	// Create directory if it doesn't exist.
	if err := os.MkdirAll(p.path, 0777); err != nil {
		return err
	}

    //ManifestFileName 是常量字符串 MANIFEST
	// Read manifest file.
	m, manifestSize, err := ReadManifestFile(filepath.Join(p.path, ManifestFileName))
	if os.IsNotExist(err) {
        //名称: .influxdb/data/数据库/policy/shard_id/0-7/MANIFEST
		m = NewManifest(p.ManifestPath())
	} else if err != nil {
		return err
	}
	// Set manifest size on the partition
	p.manifestSize = manifestSize

	// Check to see if the MANIFEST file is compatible with the current Index.
	if err := m.Validate(); err != nil {
		return err
	}

	// Copy compaction levels to the index.
	p.levels = make([]CompactionLevel, len(m.Levels))
	copy(p.levels, m.Levels)

	// Set up flags to track whether a level is compacting.
	p.levelCompacting = make([]bool, len(p.levels))

	// Open each file in the manifest.
	var files []File
	for _, filename := range m.Files {
		switch filepath.Ext(filename) {
		case LogFileExt:
			f, err := p.openLogFile(filepath.Join(p.path, filename))
			if err != nil {
				return err
			}
			files = append(files, f)

			// Make first log file active, if within threshold.
			sz, _ := f.Stat()
			if p.activeLogFile == nil && sz < p.MaxLogFileSize {
				p.activeLogFile = f
			}

		case IndexFileExt:
			f, err := p.openIndexFile(filepath.Join(p.path, filename))
			if err != nil {
				return err
			}
			files = append(files, f)
		}
	}
	fs, err := NewFileSet(p.levels, p.sfile, files)
	if err != nil {
		return err
	}
	p.fileSet = fs

	// Set initial sequence number.
	p.seq = p.fileSet.MaxID()

	// Delete any files not in the manifest.
	if err := p.deleteNonManifestFiles(m); err != nil {
		return err
	}

	// Ensure a log file exists.
	if p.activeLogFile == nil {
		if err := p.prependActiveLogFile(); err != nil {
			return err
		}
	}

	// Build series existance set.
	if err := p.buildSeriesSet(); err != nil {
		return err
	}

	// Mark opened.
	p.opened = true

	// Send a compaction request on start up.
	p.compact()

	return nil
}

~~~



##### Partition.createSeriesListIfNotExists 以tag创建索引



~~~go
// createSeriesListIfNotExists creates a list of series if they doesn't exist in
// bulk.
func (p *Partition) createSeriesListIfNotExists(names [][]byte, tagsSlice []models.Tags) ([]uint64, error) {
	// Is there anything to do? The partition may have been sent an empty batch.
	if len(names) == 0 {
		return nil, nil
	} else if len(names) != len(tagsSlice) {
		return nil, fmt.Errorf("uneven batch, partition %s sent %d names and %d tags", p.id, len(names), len(tagsSlice))
	}

	// Maintain reference count on files in file set.
	fs, err := p.RetainFileSet()
	if err != nil {
		return nil, err
	}
	defer fs.Release()

	// Ensure fileset cannot change during insert.
	p.mu.RLock()
	// Insert series into log file.
	ids, err := p.activeLogFile.AddSeriesList(p.seriesIDSet, names, tagsSlice)
	if err != nil {
		p.mu.RUnlock()
		return nil, err
	}
	p.mu.RUnlock()

	if err := p.CheckLogFile(); err != nil {
		return nil, err
	}
	return ids, nil
}
~~~



### Manifest

~~~go
// Manifest represents the list of log & index files that make up the index.
// The files are listed in time order, not necessarily ID order.
type Manifest struct {
	Levels []CompactionLevel `json:"levels,omitempty"`
	Files  []string          `json:"files,omitempty"`

	// Version should be updated whenever the TSI format has changed.
	Version int `json:"version,omitempty"`

	path string // location on disk of the manifest.
}

// NewManifest returns a new instance of Manifest with default compaction levels.
func NewManifest(path string) *Manifest {
	m := &Manifest{
		Levels:  make([]CompactionLevel, len(DefaultCompactionLevels)),
		Version: Version,
		path:    path,
	}
	copy(m.Levels, DefaultCompactionLevels)
	return m
}
~~~



## FileSet

~~~go

// FileSet represents a collection of files.
type FileSet struct {
	levels       []CompactionLevel
	sfile        *tsdb.SeriesFile
	files        []File
	manifestSize int64 // Size of the manifest file in bytes.
}

// NewFileSet returns a new instance of FileSet.
func NewFileSet(levels []CompactionLevel, sfile *tsdb.SeriesFile, files []File) (*FileSet, error) {
	return &FileSet{
		levels: levels,
		sfile:  sfile,
		files:  files,
	}, nil
}

~~~



