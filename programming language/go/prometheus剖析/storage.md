# Storage

[TOC]

存储抽象层，适配多种不同的存储

## fanout storage



##### NewFanout

~~~go
// NewFanout returns a new fanout Storage, which proxies reads and writes
// through to multiple underlying storages.
//
// The difference between primary and secondary Storage is only for read (Querier) path and it goes as follows:
// * If the primary querier returns an error, then any of the Querier operations will fail.
// * If any secondary querier returns an error the result from that queries is discarded. The overall operation will succeed,
// and the error from the secondary querier will be returned as a warning.
//
// NOTE: In the case of Prometheus, it treats all remote storages as secondary / best effort.
func NewFanout(logger log.Logger, primary Storage, secondaries ...Storage) Storage {
	return &fanout{
		logger:      logger,
		primary:     primary,
		secondaries: secondaries,
	}
}
~~~



##### fanout.Appender 获取fanoutAppender示例

~~~go
func (f *fanout) Appender(ctx context.Context) Appender {
	primary := f.primary.Appender(ctx)
	secondaries := make([]Appender, 0, len(f.secondaries))
	for _, storage := range f.secondaries {
		secondaries = append(secondaries, storage.Appender(ctx))
	}
	return &fanoutAppender{
		logger:      f.logger,
		primary:     primary,
		secondaries: secondaries,
	}
}
~~~



## readyStorage

定义在prometheus/cmd/prometheus/man.go 中

~~~go
// readyStorage implements the Storage interface while allowing to set the actual
// storage at a later point in time.
type readyStorage struct {
	mtx             sync.RWMutex
	db              *tsdb.DB
	startTimeMargin int64
}

// Set the storage.
func (s *readyStorage) Set(db *tsdb.DB, startTimeMargin int64) {
	s.mtx.Lock()
	defer s.mtx.Unlock()

	s.db = db
	s.startTimeMargin = startTimeMargin
}

// get is internal, you should use readyStorage as the front implementation layer.
func (s *readyStorage) get() *tsdb.DB {
	s.mtx.RLock()
	x := s.db
	s.mtx.RUnlock()
	return x
}

// StartTime implements the Storage interface.
func (s *readyStorage) StartTime() (int64, error) {
	if x := s.get(); x != nil {
		var startTime int64

		if len(x.Blocks()) > 0 {
			startTime = x.Blocks()[0].Meta().MinTime
		} else {
			startTime = time.Now().Unix() * 1000
		}
		// Add a safety margin as it may take a few minutes for everything to spin up.
		return startTime + s.startTimeMargin, nil
	}

	return math.MaxInt64, tsdb.ErrNotReady
}

// Querier implements the Storage interface.
func (s *readyStorage) Querier(ctx context.Context, mint, maxt int64) (storage.Querier, error) {
	if x := s.get(); x != nil {
		return x.Querier(ctx, mint, maxt)
	}
	return nil, tsdb.ErrNotReady
}

// ChunkQuerier implements the Storage interface.
func (s *readyStorage) ChunkQuerier(ctx context.Context, mint, maxt int64) (storage.ChunkQuerier, error) {
	if x := s.get(); x != nil {
		return x.ChunkQuerier(ctx, mint, maxt)
	}
	return nil, tsdb.ErrNotReady
}

// Appender implements the Storage interface.
func (s *readyStorage) Appender(ctx context.Context) storage.Appender {
	if x := s.get(); x != nil {
		return x.Appender(ctx)
	}
	return notReadyAppender{}
}

type notReadyAppender struct{}

func (n notReadyAppender) Add(l labels.Labels, t int64, v float64) (uint64, error) {
	return 0, tsdb.ErrNotReady
}

func (n notReadyAppender) AddFast(ref uint64, t int64, v float64) error { return tsdb.ErrNotReady }

func (n notReadyAppender) Commit() error { return tsdb.ErrNotReady }

func (n notReadyAppender) Rollback() error { return tsdb.ErrNotReady }

// Close implements the Storage interface.
func (s *readyStorage) Close() error {
	if x := s.get(); x != nil {
		return x.Close()
	}
	return nil
}

// CleanTombstones implements the api_v1.TSDBAdminStats and api_v2.TSDBAdmin interfaces.
func (s *readyStorage) CleanTombstones() error {
	if x := s.get(); x != nil {
		return x.CleanTombstones()
	}
	return tsdb.ErrNotReady
}

// Delete implements the api_v1.TSDBAdminStats and api_v2.TSDBAdmin interfaces.
func (s *readyStorage) Delete(mint, maxt int64, ms ...*labels.Matcher) error {
	if x := s.get(); x != nil {
		return x.Delete(mint, maxt, ms...)
	}
	return tsdb.ErrNotReady
}

// Snapshot implements the api_v1.TSDBAdminStats and api_v2.TSDBAdmin interfaces.
func (s *readyStorage) Snapshot(dir string, withHead bool) error {
	if x := s.get(); x != nil {
		return x.Snapshot(dir, withHead)
	}
	return tsdb.ErrNotReady
}

// Stats implements the api_v1.TSDBAdminStats interface.
func (s *readyStorage) Stats(statsByLabelName string) (*tsdb.Stats, error) {
	if x := s.get(); x != nil {
		return x.Head().Stats(statsByLabelName), nil
	}
	return nil, tsdb.ErrNotReady
}
~~~



## fanoutAppender

fanoutAppender 实现了Appender接口。作为scrape和db层的中间层，负责将scrape提供的数据写入多个存储(若配置了多个存储)

##### fanoutAppender的定义

~~~go
// fanoutAppender implements Appender.
type fanoutAppender struct {
	logger log.Logger

	primary     Appender //主存储
	secondaries []Appender//其他存储
}
~~~

##### fanoutAppender.AddFast

~~~go

func (f *fanoutAppender) AddFast(ref uint64, t int64, v float64) error {
	if err := f.primary.AddFast(ref, t, v); err != nil {
		return err
	}

	for _, appender := range f.secondaries {
		if err := appender.AddFast(ref, t, v); err != nil {
			return err
		}
	}
	return nil
}
~~~



##### fanoutAppender.Commit 和fanoutAppender.Rollback

~~~go

func (f *fanoutAppender) Commit() (err error) {
	err = f.primary.Commit()

	for _, appender := range f.secondaries {
		if err == nil {
			err = appender.Commit()
		} else {
			if rollbackErr := appender.Rollback(); rollbackErr != nil {
				level.Error(f.logger).Log("msg", "Squashed rollback error on commit", "err", rollbackErr)
			}
		}
	}
	return
}

func (f *fanoutAppender) Rollback() (err error) {
	err = f.primary.Rollback()

	for _, appender := range f.secondaries {
		rollbackErr := appender.Rollback()
		if err == nil {
			err = rollbackErr
		} else if rollbackErr != nil {
			level.Error(f.logger).Log("msg", "Squashed rollback error on rollback", "err", rollbackErr)
		}
	}
	return nil
}

~~~



#####  fanoutAppender.Add

~~~go
func (f *fanoutAppender) Add(l labels.Labels, t int64, v float64) (uint64, error) {
	ref, err := f.primary.Add(l, t, v)
	if err != nil {
		return ref, err
	}

	for _, appender := range f.secondaries {
		if _, err := appender.Add(l, t, v); err != nil {
			return 0, err
		}
	}
	return ref, nil
}
~~~

## ChunkSeriesSet

### 写索引

##### seriesSetAdapter

storeage/generic.go

~~~
type seriesSetAdapter struct {
	genericSeriesSet
}
~~~



##### chunkSeriesSetAdapter

~~~go
type chunkSeriesSetAdapter struct {
	genericSeriesSet
}
func (a *chunkSeriesSetAdapter) At() ChunkSeries {
	return a.genericSeriesSet.At().(ChunkSeries)
}

func (q *chunkQuerierAdapter) Select(sortSeries bool, hints *SelectHints, matchers ...*labels.Matcher) ChunkSeriesSet {
	return &chunkSeriesSetAdapter{q.genericQuerier.Select(sortSeries, hints, matchers...)}
}
~~~



#####  newGenericMergeSeriesSet

storage/merge.go

~~~go
// newGenericMergeSeriesSet returns a new genericSeriesSet that merges (and deduplicates)
// series returned by the series sets when iterating.
// Each series set must return its series in labels order, otherwise
// merged series set will be incorrect.
// Overlapped situations are merged using provided mergeFunc.
func newGenericMergeSeriesSet(sets []genericSeriesSet, mergeFunc genericSeriesMergeFunc) genericSeriesSet {
	if len(sets) == 1 {
		return sets[0]
	}

	// We are pre-advancing sets, so we can introspect the label of the
	// series under the cursor.
	var h genericSeriesSetHeap
	for _, set := range sets {
		if set == nil {
			continue
		}
		if set.Next() {
			heap.Push(&h, set)
		}
		if err := set.Err(); err != nil {
			return errorOnlySeriesSet{err}
		}
	}
	return &genericMergeSeriesSet{
		mergeFunc: mergeFunc,
		sets:      sets,
		heap:      h,
	}
}
~~~



##### NewMergeChunkSeriesSet

~~~go
// NewMergeChunkSeriesSet returns a new ChunkSeriesSet that merges many SeriesSet together.
func NewMergeChunkSeriesSet(sets []ChunkSeriesSet, mergeFunc VerticalChunkSeriesMergeFunc) ChunkSeriesSet {
	genericSets := make([]genericSeriesSet, 0, len(sets))
	for _, s := range sets {
		genericSets = append(genericSets, &genericChunkSeriesSetAdapter{s})

	}
	return &chunkSeriesSetAdapter{newGenericMergeSeriesSet(genericSets, (&chunkSeriesMergerAdapter{VerticalChunkSeriesMergeFunc: mergeFunc}).Merge)}
}
~~~

#### genericMergeSeriesSet

storage/merge.go

~~~go
// genericMergeSeriesSet implements genericSeriesSet.
type genericMergeSeriesSet struct {
	currentLabels labels.Labels
	mergeFunc     genericSeriesMergeFunc

	heap        genericSeriesSetHeap
	sets        []genericSeriesSet
	currentSets []genericSeriesSet
}

func (c *genericMergeSeriesSet) Next() bool {
	// Run in a loop because the "next" series sets may not be valid anymore.
	// If, for the current label set, all the next series sets come from
	// failed remote storage sources, we want to keep trying with the next label set.
	for {
		// Firstly advance all the current series sets. If any of them have run out,
		// we can drop them, otherwise they should be inserted back into the heap.
		for _, set := range c.currentSets {
			if set.Next() {
				heap.Push(&c.heap, set)
			}
		}

		if len(c.heap) == 0 {
			return false
		}

		// Now, pop items of the heap that have equal label sets.
		c.currentSets = nil
		c.currentLabels = c.heap[0].At().Labels()
		for len(c.heap) > 0 && labels.Equal(c.currentLabels, c.heap[0].At().Labels()) {
			set := heap.Pop(&c.heap).(genericSeriesSet)
			c.currentSets = append(c.currentSets, set)
		}

		// As long as the current set contains at least 1 set,
		// then it should return true.
		if len(c.currentSets) != 0 {
			break
		}
	}
	return true
}

func (c *genericMergeSeriesSet) At() Labels {
	if len(c.currentSets) == 1 {
		return c.currentSets[0].At()
	}
	series := make([]Labels, 0, len(c.currentSets))
	for _, seriesSet := range c.currentSets {
		series = append(series, seriesSet.At())
	}
	return c.mergeFunc(series...)
}

func (c *genericMergeSeriesSet) Err() error {
	for _, set := range c.sets {
		if err := set.Err(); err != nil {
			return err
		}
	}
	return nil
}

func (c *genericMergeSeriesSet) Warnings() Warnings {
	var ws Warnings
	for _, set := range c.sets {
		ws = append(ws, set.Warnings()...)
	}
	return ws
}
~~~



##### genericSeriesSetAdapter

storage/generic.go中

genericSeriesSetAdapter实现了SeriesSet接口

~~~go
type genericSeriesSetAdapter struct {
	SeriesSet
}
~~~



##### chunkSeriesMergerAdapter

storage/generic.go

~~~go
/storage/merge.go
// VerticalSeriesMergeFunc returns merged series implementation that merges series with same labels together.
// It has to handle time-overlapped series as well.
type VerticalSeriesMergeFunc func(...Series) Series

//==========================

type chunkSeriesMergerAdapter struct {
	VerticalChunkSeriesMergeFunc
}

func (a *chunkSeriesMergerAdapter) Merge(s ...Labels) Labels {
	buf := make([]ChunkSeries, 0, len(s))
    //ChunkSeries实现了Lables接口
	for _, ser := range s {
		buf = append(buf, ser.(ChunkSeries))
	}
	return a.VerticalChunkSeriesMergeFunc(buf...)
}
~~~



##### NewCompactingChunkSeriesMerger

~~~go
// NewCompactingChunkSeriesMerger returns VerticalChunkSeriesMergeFunc that merges the same chunk series into single chunk series.
// In case of the chunk overlaps, it compacts those into one or more time-ordered non-overlapping chunks with merged data.
// Samples from overlapped chunks are merged using series vertical merge func.
// It expects the same labels for each given series.
//
// NOTE: Use the returned merge function only when you see potentially overlapping series, as this introduces small a overhead
// to handle overlaps between series.
func NewCompactingChunkSeriesMerger(mergeFunc VerticalSeriesMergeFunc) VerticalChunkSeriesMergeFunc {
	return func(series ...ChunkSeries) ChunkSeries {
		if len(series) == 0 {
			return nil
		}
		return &ChunkSeriesEntry{
			Lset: series[0].Labels(),
			ChunkIteratorFn: func() chunks.Iterator {
				iterators := make([]chunks.Iterator, 0, len(series))
				for _, s := range series {
					iterators = append(iterators, s.Iterator())
				}
				return &compactChunkIterator{
					mergeFunc: mergeFunc,
					iterators: iterators,
				}
			},
		}
	}
}
~~~



##### ChainedSeriesMerge

~~~go
// ChainedSeriesMerge returns single series from many same, potentially overlapping series by chaining samples together.
// If one or more samples overlap, one sample from random overlapped ones is kept and all others with the same
// timestamp are dropped.
//
// This works the best with replicated series, where data from two series are exactly the same. This does not work well
// with "almost" the same data, e.g. from 2 Prometheus HA replicas. This is fine, since from the Prometheus perspective
// this never happens.
//
// It's optimized for non-overlap cases as well.
func ChainedSeriesMerge(series ...Series) Series {
	if len(series) == 0 {
		return nil
	}
	return &SeriesEntry{
		Lset: series[0].Labels(),
		SampleIteratorFn: func() chunkenc.Iterator {
			iterators := make([]chunkenc.Iterator, 0, len(series))
			for _, s := range series {
				iterators = append(iterators, s.Iterator())
			}
			return newChainSampleIterator(iterators)
		},
	}
}
~~~



### ChunkSeriesEntry

~~~go
type ChunkSeriesEntry struct {
	Lset            labels.Labels
	ChunkIteratorFn func() chunks.Iterator
}

func (s *ChunkSeriesEntry) Labels() labels.Labels     { return s.Lset }
func (s *ChunkSeriesEntry) Iterator() chunks.Iterator { return s.ChunkIteratorFn() }

~~~



## 接口



##### Storage 接口

~~~go
// Storage ingests and manages samples, along with various indexes. All methods
// are goroutine-safe. Storage implements storage.SampleAppender.
type Storage interface {
	SampleAndChunkQueryable
	Appendable

	// StartTime returns the oldest timestamp stored in the storage.
	StartTime() (int64, error)

	// Close closes the storage and all its underlying resources.
	Close() error
}
~~~



##### Appendable 接口

~~~go
// Appendable allows creating appenders.
type Appendable interface {
	// Appender returns a new appender for the storage. The implementation
	// can choose whether or not to use the context, for deadlines or to check
	// for errors.
	Appender(ctx context.Context) Appender
}

// SampleAndChunkQueryable allows retrieving samples as well as encoded samples in form of chunks.
type SampleAndChunkQueryable interface {
	Queryable
	ChunkQueryable
}
~~~



##### Appender 接口

~~~go
// Appender provides batched appends against a storage.
// It must be completed with a call to Commit or Rollback and must not be reused afterwards.
//
// Operations on the Appender interface are not goroutine-safe.
type Appender interface {
	// Add adds a sample pair for the given series. A reference number is
	// returned which can be used to add further samples in the same or later
	// transactions.
	// Returned reference numbers are ephemeral and may be rejected in calls
	// to AddFast() at any point. Adding the sample via Add() returns a new
	// reference number.
	// If the reference is 0 it must not be used for caching.
	Add(l labels.Labels, t int64, v float64) (uint64, error)

	// AddFast adds a sample pair for the referenced series. It is generally
	// faster than adding a sample by providing its full label set.
	AddFast(ref uint64, t int64, v float64) error

	// Commit submits the collected samples and purges the batch. If Commit
	// returns a non-nil error, it also rolls back all modifications made in
	// the appender so far, as Rollback would do. In any case, an Appender
	// must not be used anymore after Commit has been called.
	Commit() error

	// Rollback rolls back all modifications made in the appender so far.
	// Appender has to be discarded after rollback.
	Rollback() error
}
~~~



##### ChunkSeries接口

~~~go
// ChunkSeries exposes a single time series and allows iterating over chunks.
type ChunkSeries interface {
	Labels
	ChunkIteratable
}

// Series exposes a single time series and allows iterating over samples.
type Series interface {
	Labels
	SampleIteratable
}
~~~



##### SeriesSet 

~~~go
// SeriesSet contains a set of series.
type SeriesSet interface {
	Next() bool
	// At returns full series. Returned series should be iteratable even after Next is called.
	At() Series
	// The error that iteration as failed with.
	// When an error occurs, set cannot continue to iterate.
	Err() error
	// A collection of warnings for the whole set.
	// Warnings could be return even iteration has not failed with error.
	Warnings() Warnings
}

var emptySeriesSet = errSeriesSet{}

// EmptySeriesSet returns a series set that's always empty.
func EmptySeriesSet() SeriesSet {
	return emptySeriesSet
}

type errSeriesSet struct {
	err error
}

func (s errSeriesSet) Next() bool         { return false }
func (s errSeriesSet) At() Series         { return nil }
func (s errSeriesSet) Err() error         { return s.err }
func (s errSeriesSet) Warnings() Warnings { return nil }

// ErrSeriesSet returns a series set that wraps an error.
func ErrSeriesSet(err error) SeriesSet {
	return errSeriesSet{err: err}
}

var emptyChunkSeriesSet = errChunkSeriesSet{}

// EmptyChunkSeriesSet returns a chunk series set that's always empty.
func EmptyChunkSeriesSet() ChunkSeriesSet {
	return emptyChunkSeriesSet
}

type errChunkSeriesSet struct {
	err error
}

func (s errChunkSeriesSet) Next() bool         { return false }
func (s errChunkSeriesSet) At() ChunkSeries    { return nil }
func (s errChunkSeriesSet) Err() error         { return s.err }
func (s errChunkSeriesSet) Warnings() Warnings { return nil }

// ErrChunkSeriesSet returns a chunk series set that wraps an error.
func ErrChunkSeriesSet(err error) ChunkSeriesSet {
	return errChunkSeriesSet{err: err}
}



// ChunkSeriesSet contains a set of chunked series.
type ChunkSeriesSet interface {
	Next() bool
	// At returns full chunk series. Returned series should be iteratable even after Next is called.
	At() ChunkSeries
	// The error that iteration has failed with.
	// When an error occurs, set cannot continue to iterate.
	Err() error
	// A collection of warnings for the whole set.
	// Warnings could be return even iteration has not failed with error.
	Warnings() Warnings
}



var emptySeriesSet = errSeriesSet{}

// EmptySeriesSet returns a series set that's always empty.
func EmptySeriesSet() SeriesSet {
	return emptySeriesSet
}

type errSeriesSet struct {
	err error
}

func (s errSeriesSet) Next() bool         { return false }
func (s errSeriesSet) At() Series         { return nil }
func (s errSeriesSet) Err() error         { return s.err }
func (s errSeriesSet) Warnings() Warnings { return nil }

// ErrSeriesSet returns a series set that wraps an error.
func ErrSeriesSet(err error) SeriesSet {
	return errSeriesSet{err: err}
}

var emptyChunkSeriesSet = errChunkSeriesSet{}

// EmptyChunkSeriesSet returns a chunk series set that's always empty.
func EmptyChunkSeriesSet() ChunkSeriesSet {
	return emptyChunkSeriesSet
}

type errChunkSeriesSet struct {
	err error
}

func (s errChunkSeriesSet) Next() bool         { return false }
func (s errChunkSeriesSet) At() ChunkSeries    { return nil }
func (s errChunkSeriesSet) Err() error         { return s.err }
func (s errChunkSeriesSet) Warnings() Warnings { return nil }

// ErrChunkSeriesSet returns a chunk series set that wraps an error.
func ErrChunkSeriesSet(err error) ChunkSeriesSet {
	return errChunkSeriesSet{err: err}
}


// ChunkSeriesSet contains a set of chunked series.
type ChunkSeriesSet interface {
	Next() bool
	// At returns full chunk series. Returned series should be iteratable even after Next is called.
	At() ChunkSeries
	// The error that iteration has failed with.
	// When an error occurs, set cannot continue to iterate.
	Err() error
	// A collection of warnings for the whole set.
	// Warnings could be return even iteration has not failed with error.
	Warnings() Warnings
}


~~~



##### 查询相关接口

~~~go



// The errors exposed.
var (
	ErrNotFound                    = errors.New("not found")
	ErrOutOfOrderSample            = errors.New("out of order sample")
	ErrDuplicateSampleForTimestamp = errors.New("duplicate sample for timestamp")
	ErrOutOfBounds                 = errors.New("out of bounds")
)

// A Queryable handles queries against a storage.
// Use it when you need to have access to all samples without chunk encoding abstraction e.g promQL.
type Queryable interface {
	// Querier returns a new Querier on the storage.
	Querier(ctx context.Context, mint, maxt int64) (Querier, error)
}

// Querier provides querying access over time series data of a fixed time range.
type Querier interface {
	LabelQuerier

	// Select returns a set of series that matches the given label matchers.
	// Caller can specify if it requires returned series to be sorted. Prefer not requiring sorting for better performance.
	// It allows passing hints that can help in optimising select, but it's up to implementation how this is used if used at all.
	Select(sortSeries bool, hints *SelectHints, matchers ...*labels.Matcher) SeriesSet
}

// A ChunkQueryable handles queries against a storage.
// Use it when you need to have access to samples in encoded format.
type ChunkQueryable interface {
	// ChunkQuerier returns a new ChunkQuerier on the storage.
	ChunkQuerier(ctx context.Context, mint, maxt int64) (ChunkQuerier, error)
}

// ChunkQuerier provides querying access over time series data of a fixed time range.
type ChunkQuerier interface {
	LabelQuerier

	// Select returns a set of series that matches the given label matchers.
	// Caller can specify if it requires returned series to be sorted. Prefer not requiring sorting for better performance.
	// It allows passing hints that can help in optimising select, but it's up to implementation how this is used if used at all.
	Select(sortSeries bool, hints *SelectHints, matchers ...*labels.Matcher) ChunkSeriesSet
}

// LabelQuerier provides querying access over labels.
type LabelQuerier interface {
	// LabelValues returns all potential values for a label name.
	// It is not safe to use the strings beyond the lifefime of the querier.
	// TODO(yeya24): support matchers or hints.
	LabelValues(name string) ([]string, Warnings, error)

	// LabelNames returns all the unique label names present in the block in sorted order.
	// TODO(yeya24): support matchers or hints.
	LabelNames() ([]string, Warnings, error)

	// Close releases the resources of the Querier.
	Close() error
}

// SelectHints specifies hints passed for data selections.
// This is used only as an option for implementation to use.
type SelectHints struct {
	Start int64 // Start time in milliseconds for this select.
	End   int64 // End time in milliseconds for this select.

	Step int64  // Query step size in milliseconds.
	Func string // String representation of surrounding function or aggregation.

	Grouping []string // List of label names used in aggregation.
	By       bool     // Indicate whether it is without or by.
	Range    int64    // Range vector selector range in milliseconds.
}

// TODO(bwplotka): Move to promql/engine_test.go?
// QueryableFunc is an adapter to allow the use of ordinary functions as
// Queryables. It follows the idea of http.HandlerFunc.
type QueryableFunc func(ctx context.Context, mint, maxt int64) (Querier, error)

// Querier calls f() with the given parameters.
func (f QueryableFunc) Querier(ctx context.Context, mint, maxt int64) (Querier, error) {
	return f(ctx, mint, maxt)
}

// Labels represents an item that has labels e.g. time series.
type Labels interface {
	// Labels returns the complete set of labels. For series it means all labels identifying the series.
	Labels() labels.Labels
}

type SampleIteratable interface {
	// Iterator returns a new, independent iterator of the data of the series.
	Iterator() chunkenc.Iterator
}

type ChunkIteratable interface {
	// Iterator returns a new, independent iterator that iterates over potentially overlapping
	// chunks of the series, sorted by min time.
	Iterator() chunks.Iterator
}

type Warnings []error
~~~

