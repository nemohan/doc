# shard

[TOC]

shard的实现在tsdb/shard.go中



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

