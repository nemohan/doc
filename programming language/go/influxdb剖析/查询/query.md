# query

[TOC]



influxdb/query包



## Executor

##### Executor的定义

~~~go
// Executor executes every statement in an Query.
type Executor struct {
	// Used for executing a statement in the query.
    //StatementExecutor 被初始化为coordinator.StatementExecutor
	StatementExecutor StatementExecutor

	// Used for tracking running queries.
	TaskManager *TaskManager

	// Logger to use for all logging.
	// Defaults to discarding all log output.
	Logger *zap.Logger

	// expvar-based stats.
	stats *Statistics
}

// NewExecutor returns a new instance of Executor.
func NewExecutor() *Executor {
	return &Executor{
		TaskManager: NewTaskManager(),
		Logger:      zap.NewNop(),
		stats:       &Statistics{},
	}
}
~~~



##### ExecuteQuery

influxdb/query/executor.go

~~~go
// ExecuteQuery executes each statement within a query.
func (e *Executor) ExecuteQuery(query *influxql.Query, opt ExecutionOptions, closing chan struct{}) <-chan *Result {
	results := make(chan *Result)
	go e.executeQuery(query, opt, closing, results)
	return results
}

func (e *Executor) executeQuery(query *influxql.Query, opt ExecutionOptions, closing <-chan struct{}, results chan *Result) {
	defer close(results)
	defer e.recover(query, results)

	atomic.AddInt64(&e.stats.ActiveQueries, 1)
	atomic.AddInt64(&e.stats.ExecutedQueries, 1)
	defer func(start time.Time) {
		atomic.AddInt64(&e.stats.ActiveQueries, -1)
		atomic.AddInt64(&e.stats.FinishedQueries, 1)
		atomic.AddInt64(&e.stats.QueryExecutionDuration, time.Since(start).Nanoseconds())
	}(time.Now())

	ctx, detach, err := e.TaskManager.AttachQuery(query, opt, closing)
	if err != nil {
		select {
		case results <- &Result{Err: err}:
		case <-opt.AbortCh:
		}
		return
	}
	defer detach()

	// Setup the execution context that will be used when executing statements.
	ctx.Results = results

	var i int
LOOP:
	for ; i < len(query.Statements); i++ {
		ctx.statementID = i
		stmt := query.Statements[i]

		// If a default database wasn't passed in by the caller, check the statement.
		defaultDB := opt.Database
		if defaultDB == "" {
			if s, ok := stmt.(influxql.HasDefaultDatabase); ok {
				defaultDB = s.DefaultDatabase()
			}
		}

		// Do not let queries manually use the system measurements. If we find
		// one, return an error. This prevents a person from using the
		// measurement incorrectly and causing a panic.
		if stmt, ok := stmt.(*influxql.SelectStatement); ok {
			for _, s := range stmt.Sources {
				switch s := s.(type) {
				case *influxql.Measurement:
					if influxql.IsSystemName(s.Name) {
						command := "the appropriate meta command"
						switch s.Name {
						case "_fieldKeys":
							command = "SHOW FIELD KEYS"
						case "_measurements":
							command = "SHOW MEASUREMENTS"
						case "_series":
							command = "SHOW SERIES"
						case "_tagKeys":
							command = "SHOW TAG KEYS"
						case "_tags":
							command = "SHOW TAG VALUES"
						}
						results <- &Result{
							Err: fmt.Errorf("unable to use system source '%s': use %s instead", s.Name, command),
						}
						break LOOP
					}
				}
			}
		}

		// Rewrite statements, if necessary.
		// This can occur on meta read statements which convert to SELECT statements.
		newStmt, err := RewriteStatement(stmt)
		if err != nil {
			results <- &Result{Err: err}
			break
		}
		stmt = newStmt

		// Normalize each statement if possible.
		if normalizer, ok := e.StatementExecutor.(StatementNormalizer); ok {
			if err := normalizer.NormalizeStatement(stmt, defaultDB, opt.RetentionPolicy); err != nil {
				if err := ctx.send(&Result{Err: err}); err == ErrQueryAborted {
					return
				}
				break
			}
		}

		// Log each normalized statement.
		if !ctx.Quiet {
			e.Logger.Info("Executing query", zap.Stringer("query", stmt))
		}

        //StatementExecutor 被初始化为coordinator.StatementExecutor
		// Send any other statements to the underlying statement executor.
		err = e.StatementExecutor.ExecuteStatement(stmt, ctx)
		if err == ErrQueryInterrupted {
			// Query was interrupted so retrieve the real interrupt error from
			// the query task if there is one.
			if qerr := ctx.Err(); qerr != nil {
				err = qerr
			}
		}

		// Send an error for this result if it failed for some reason.
		if err != nil {
			if err := ctx.send(&Result{
				StatementID: i,
				Err:         err,
			}); err == ErrQueryAborted {
				return
			}
			// Stop after the first error.
			break
		}

		// Check if the query was interrupted during an uninterruptible statement.
		interrupted := false
		select {
		case <-ctx.Done():
			interrupted = true
		default:
			// Query has not been interrupted.
		}

		if interrupted {
			break
		}
	}

	// Send error results for any statements which were not executed.
	for ; i < len(query.Statements)-1; i++ {
		if err := ctx.send(&Result{
			StatementID: i,
			Err:         ErrNotExecuted,
		}); err == ErrQueryAborted {
			return
		}
	}
}
~~~



##### RewriteStatement 重写部分语句

~~~go
// RewriteStatement rewrites stmt into a new statement, if applicable.
func RewriteStatement(stmt influxql.Statement) (influxql.Statement, error) {
	switch stmt := stmt.(type) {
	case *influxql.ShowFieldKeysStatement:
		return rewriteShowFieldKeysStatement(stmt)
	case *influxql.ShowFieldKeyCardinalityStatement:
		return rewriteShowFieldKeyCardinalityStatement(stmt)
	case *influxql.ShowMeasurementsStatement:
		return rewriteShowMeasurementsStatement(stmt)
	case *influxql.ShowMeasurementCardinalityStatement:
		return rewriteShowMeasurementCardinalityStatement(stmt)
	case *influxql.ShowSeriesStatement:
		return rewriteShowSeriesStatement(stmt)
	case *influxql.ShowSeriesCardinalityStatement:
		return rewriteShowSeriesCardinalityStatement(stmt)
	case *influxql.ShowTagKeysStatement:
		return rewriteShowTagKeysStatement(stmt)
	case *influxql.ShowTagKeyCardinalityStatement:
		return rewriteShowTagKeyCardinalityStatement(stmt)
	case *influxql.ShowTagValuesStatement:
		return rewriteShowTagValuesStatement(stmt)
	case *influxql.ShowTagValuesCardinalityStatement:
		return rewriteShowTagValuesCardinalityStatement(stmt)
	default:
		return stmt, nil
	}
}
~~~



##### rewriteShowFieldKeysStatement 重写查询 field的语句

~~~go
func rewriteShowFieldKeysStatement(stmt *influxql.ShowFieldKeysStatement) (influxql.Statement, error) {
	return &influxql.SelectStatement{
		Fields: influxql.Fields([]*influxql.Field{
			{Expr: &influxql.VarRef{Val: "fieldKey"}},
			{Expr: &influxql.VarRef{Val: "fieldType"}},
		}),
		Sources:    rewriteSources(stmt.Sources, "_fieldKeys", stmt.Database),
		Condition:  rewriteSourcesCondition(stmt.Sources, nil),
		Offset:     stmt.Offset,
		Limit:      stmt.Limit,
		SortFields: stmt.SortFields,
		OmitTime:   true,
		Dedupe:     true,
		IsRawQuery: true,
	}, nil
}
~~~



##### Select

query/select.go

coordinator/statement_executor.go 中StatementExecutor.createIterators会调用此函数

参数:

* ShardMapper 实际是coordinator.LocalShardMapper

~~~go
// Select compiles, prepares, and then initiates execution of the query using the
// default compile options.
func Select(ctx context.Context, stmt *influxql.SelectStatement, shardMapper ShardMapper, opt SelectOptions) (Cursor, error) {
	s, err := Prepare(stmt, shardMapper, opt)
	if err != nil {
		return nil, err
	}
	// Must be deferred so it runs after Select.
	defer s.Close()
	return s.Select(ctx)
}
~~~



##### Prepare

query/select.go

~~~go
// Prepare will compile the statement with the default compile options and
// then prepare the query.
func Prepare(stmt *influxql.SelectStatement, shardMapper ShardMapper, opt SelectOptions) (PreparedStatement, error) {
    //返回compiledStatement
	c, err := Compile(stmt, CompileOptions{})
	if err != nil {
		return nil, err
	}
	return c.Prepare(shardMapper, opt)
}
~~~



### Compile



##### compiledStatement的定义

~~~go
// compiledStatement represents a select statement that has undergone some initial processing to
// determine if it is valid and to have some initial modifications done on the AST.
type compiledStatement struct {
	// Condition is the condition used for accessing data.
	Condition influxql.Expr

	// TimeRange is the TimeRange for selecting data.
	TimeRange influxql.TimeRange

	// Interval holds the time grouping interval.
	Interval Interval

	// InheritedInterval marks if the interval was inherited by a parent.
	// If this is set, then an interval that was inherited will not cause
	// a query that shouldn't have an interval to fail.
	InheritedInterval bool

	// ExtraIntervals is the number of extra intervals that will be read in addition
	// to the TimeRange. It is a multiple of Interval and only applies to queries that
	// have an Interval. It is used to extend the TimeRange of the mapped shards to
	// include additional non-emitted intervals used by derivative and other functions.
	// It will be set to the highest number of extra intervals that need to be read even
	// if it doesn't apply to all functions. The number will always be positive.
	// This value may be set to a non-zero value even if there is no interval for the
	// compiled query.
	ExtraIntervals int

	// Ascending is true if the time ordering is ascending.
	Ascending bool

	// FunctionCalls holds a reference to the call expression of every function
	// call that has been encountered.
	FunctionCalls []*influxql.Call

	// OnlySelectors is set to true when there are no aggregate functions.
	OnlySelectors bool

	// HasDistinct is set when the distinct() function is encountered.
	HasDistinct bool

	// FillOption contains the fill option for aggregates.
	FillOption influxql.FillOption

	// TopBottomFunction is set to top or bottom when one of those functions are
	// used in the statement.
	TopBottomFunction string

	// HasAuxiliaryFields is true when the function requires auxiliary fields.
	HasAuxiliaryFields bool

	// Fields holds all of the fields that will be used.
	Fields []*compiledField

	// TimeFieldName stores the name of the time field's column.
	// The column names generated by the compiler will not conflict with
	// this name.
	TimeFieldName string

	// Limit is the number of rows per series this query should be limited to.
	Limit int

	// HasTarget is true if this query is being written into a target.
	HasTarget bool

	// Options holds the configured compiler options.
	Options CompileOptions

	stmt *influxql.SelectStatement
}

~~~



##### Compile

query/compile.go

~~~go
func Compile(stmt *influxql.SelectStatement, opt CompileOptions) (Statement, error) {
	c := newCompiler(opt)
	c.stmt = stmt.Clone()
	if err := c.preprocess(c.stmt); err != nil {
		return nil, err
	}
	if err := c.compile(c.stmt); err != nil {
		return nil, err
	}
	c.stmt.TimeAlias = c.TimeFieldName
	c.stmt.Condition = c.Condition

	// Convert DISTINCT into a call.
	c.stmt.RewriteDistinct()

	// Remove "time" from fields list.
	c.stmt.RewriteTimeFields()

	// Rewrite any regex conditions that could make use of the index.
	c.stmt.RewriteRegexConditions()
	return c, nil
}
~~~



##### newCompiler

~~~go
func newCompiler(opt CompileOptions) *compiledStatement {
	if opt.Now.IsZero() {
		opt.Now = time.Now().UTC()
	}
	return &compiledStatement{
		OnlySelectors: true,
		TimeFieldName: "time",
		Options:       opt,
	}
}
~~~



##### compiledStatement.preprocess

~~~go
// preprocess retrieves and records the global attributes of the current statement.
func (c *compiledStatement) preprocess(stmt *influxql.SelectStatement) error {
	c.Ascending = stmt.TimeAscending()
	c.Limit = stmt.Limit
	c.HasTarget = stmt.Target != nil

	valuer := influxql.NowValuer{Now: c.Options.Now, Location: stmt.Location}
	cond, t, err := influxql.ConditionExpr(stmt.Condition, &valuer)
	if err != nil {
		return err
	}
	// Verify that the condition is actually ok to use.
	if err := c.validateCondition(cond); err != nil {
		return err
	}
	c.Condition = cond
	c.TimeRange = t

	// Read the dimensions of the query, validate them, and retrieve the interval
	// if it exists.
	if err := c.compileDimensions(stmt); err != nil {
		return err
	}

	// Retrieve the fill option for the statement.
	c.FillOption = stmt.Fill

	// Resolve the min and max times now that we know if there is an interval or not.
	if c.TimeRange.Min.IsZero() {
		c.TimeRange.Min = time.Unix(0, influxql.MinTime).UTC()
	}
	if c.TimeRange.Max.IsZero() {
		// If the interval is non-zero, then we have an aggregate query and
		// need to limit the maximum time to now() for backwards compatibility
		// and usability.
		if !c.Interval.IsZero() {
			c.TimeRange.Max = c.Options.Now
		} else {
			c.TimeRange.Max = time.Unix(0, influxql.MaxTime).UTC()
		}
	}
	return nil
}
~~~



##### compiledStatement.Prepare

* shardMapper.MapShards 映射到分片

~~~go
func (c *compiledStatement) Prepare(shardMapper ShardMapper, sopt SelectOptions) (PreparedStatement, error) {
	// If this is a query with a grouping, there is a bucket limit, and the minimum time has not been specified,
	// we need to limit the possible time range that can be used when mapping shards but not when actually executing
	// the select statement. Determine the shard time range here.
	timeRange := c.TimeRange
	if sopt.MaxBucketsN > 0 && !c.stmt.IsRawQuery && timeRange.MinTimeNano() == influxql.MinTime {
		interval, err := c.stmt.GroupByInterval()
		if err != nil {
			return nil, err
		}

		offset, err := c.stmt.GroupByOffset()
		if err != nil {
			return nil, err
		}

		if interval > 0 {
			// Determine the last bucket using the end time.
			opt := IteratorOptions{
				Interval: Interval{
					Duration: interval,
					Offset:   offset,
				},
			}
			last, _ := opt.Window(c.TimeRange.MaxTimeNano() - 1)

			// Determine the time difference using the number of buckets.
			// Determine the maximum difference between the buckets based on the end time.
			maxDiff := last - models.MinNanoTime
			if maxDiff/int64(interval) > int64(sopt.MaxBucketsN) {
				timeRange.Min = time.Unix(0, models.MinNanoTime)
			} else {
				timeRange.Min = time.Unix(0, last-int64(interval)*int64(sopt.MaxBucketsN-1))
			}
		}
	}

	// Modify the time range if there are extra intervals and an interval.
	if !c.Interval.IsZero() && c.ExtraIntervals > 0 {
		if c.Ascending {
			newTime := timeRange.Min.Add(time.Duration(-c.ExtraIntervals) * c.Interval.Duration)
			if !newTime.Before(time.Unix(0, influxql.MinTime).UTC()) {
				timeRange.Min = newTime
			} else {
				timeRange.Min = time.Unix(0, influxql.MinTime).UTC()
			}
		} else {
			newTime := timeRange.Max.Add(time.Duration(c.ExtraIntervals) * c.Interval.Duration)
			if !newTime.After(time.Unix(0, influxql.MaxTime).UTC()) {
				timeRange.Max = newTime
			} else {
				timeRange.Max = time.Unix(0, influxql.MaxTime).UTC()
			}
		}
	}

	// Create an iterator creator based on the shards in the cluster.
	shards, err := shardMapper.MapShards(c.stmt.Sources, timeRange, sopt)
	if err != nil {
		return nil, err
	}

	// Rewrite wildcards, if any exist.
	mapper := FieldMapper{FieldMapper: shards}
	stmt, err := c.stmt.RewriteFields(mapper)
	if err != nil {
		shards.Close()
		return nil, err
	}

	// Validate if the types are correct now that they have been assigned.
	if err := validateTypes(stmt); err != nil {
		shards.Close()
		return nil, err
	}

	// Determine base options for iterators.
	opt, err := newIteratorOptionsStmt(stmt, sopt)
	if err != nil {
		shards.Close()
		return nil, err
	}
	opt.StartTime, opt.EndTime = c.TimeRange.MinTimeNano(), c.TimeRange.MaxTimeNano()
	opt.Ascending = c.Ascending

	if sopt.MaxBucketsN > 0 && !stmt.IsRawQuery && c.TimeRange.MinTimeNano() > influxql.MinTime {
		interval, err := stmt.GroupByInterval()
		if err != nil {
			shards.Close()
			return nil, err
		}

		if interval > 0 {
			// Determine the start and end time matched to the interval (may not match the actual times).
			first, _ := opt.Window(opt.StartTime)
			last, _ := opt.Window(opt.EndTime - 1)

			// Determine the number of buckets by finding the time span and dividing by the interval.
			buckets := (last - first + int64(interval)) / int64(interval)
			if int(buckets) > sopt.MaxBucketsN {
				shards.Close()
				return nil, fmt.Errorf("max-select-buckets limit exceeded: (%d/%d)", buckets, sopt.MaxBucketsN)
			}
		}
	}

	columns := stmt.ColumnNames()
	return &preparedStatement{
		stmt:      stmt,
		opt:       opt,
		ic:        shards,
		columns:   columns,
		maxPointN: sopt.MaxPointN,
		now:       c.Options.Now,
	}, nil
}
~~~



## PreparedStatement

query/Select.go

~~~go
// Select is a prepared statement that is ready to be executed.
type PreparedStatement interface {
	// Select creates the Iterators that will be used to read the query.
	Select(ctx context.Context) (Cursor, error)

	// Explain outputs the explain plan for this statement.
	Explain() (string, error)

	// Close closes the resources associated with this prepared statement.
	// This must be called as the mapped shards may hold open resources such
	// as network connections.
	Close() error
}v
~~~



### preparedStatement

query/select.go

~~~go
type preparedStatement struct {
	stmt *influxql.SelectStatement
	opt  IteratorOptions
	ic   interface {
		IteratorCreator
		io.Closer
	}
	columns   []string
	maxPointN int
	now       time.Time
}


~~~



##### preparedStatement.Select

~~~go
func (p *preparedStatement) Select(ctx context.Context) (Cursor, error) {
	// TODO(jsternberg): Remove this hacky method of propagating now.
	// Each level of the query should use a time range discovered during
	// compilation, but that requires too large of a refactor at the moment.
	ctx = context.WithValue(ctx, "now", p.now)

	opt := p.opt
	opt.InterruptCh = ctx.Done()
	cur, err := buildCursor(ctx, p.stmt, p.ic, opt)
	if err != nil {
		return nil, err
	}

	// If a monitor exists and we are told there is a maximum number of points,
	// register the monitor function.
	if m := MonitorFromContext(ctx); m != nil {
		if p.maxPointN > 0 {
			monitor := PointLimitMonitor(cur, DefaultStatsInterval, p.maxPointN)
			m.Monitor(monitor)
		}
	}
	return cur, nil
}
~~~



##### buildCursor

~~~go
func buildCursor(ctx context.Context, stmt *influxql.SelectStatement, ic IteratorCreator, opt IteratorOptions) (Cursor, error) {
	span := tracing.SpanFromContext(ctx)
	if span != nil {
		span = span.StartSpan("build_cursor")
		defer span.Finish()

		span.SetLabels("statement", stmt.String())
		ctx = tracing.NewContextWithSpan(ctx, span)
	}

	switch opt.Fill {
	case influxql.NumberFill:
		if v, ok := opt.FillValue.(int); ok {
			opt.FillValue = int64(v)
		}
	case influxql.PreviousFill:
		opt.FillValue = SkipDefault
	}

	fields := make([]*influxql.Field, 0, len(stmt.Fields)+1)
	if !stmt.OmitTime {
		// Add a field with the variable "time" if we have not omitted time.
		fields = append(fields, &influxql.Field{
			Expr: &influxql.VarRef{
				Val:  "time",
				Type: influxql.Time,
			},
		})
	}

	// Iterate through each of the fields to add them to the value mapper.
	valueMapper := newValueMapper()
	for _, f := range stmt.Fields {
		fields = append(fields, valueMapper.Map(f))

		// If the field is a top() or bottom() call, we need to also add
		// the extra variables if we are not writing into a target.
		if stmt.Target != nil {
			continue
		}

		switch expr := f.Expr.(type) {
		case *influxql.Call:
			if expr.Name == "top" || expr.Name == "bottom" {
				for i := 1; i < len(expr.Args)-1; i++ {
					nf := influxql.Field{Expr: expr.Args[i]}
					fields = append(fields, valueMapper.Map(&nf))
				}
			}
		}
	}

	// Set the aliases on each of the columns to what the final name should be.
	columns := stmt.ColumnNames()
	for i, f := range fields {
		f.Alias = columns[i]
	}

	// Retrieve the refs to retrieve the auxiliary fields.
	var auxKeys []influxql.VarRef
	if len(valueMapper.refs) > 0 {
		opt.Aux = make([]influxql.VarRef, 0, len(valueMapper.refs))
		for ref := range valueMapper.refs {
			opt.Aux = append(opt.Aux, *ref)
		}
		sort.Sort(influxql.VarRefs(opt.Aux))

		auxKeys = make([]influxql.VarRef, len(opt.Aux))
		for i, ref := range opt.Aux {
			auxKeys[i] = valueMapper.symbols[ref.String()]
		}
	}

	// If there are no calls, then produce an auxiliary cursor.
	if len(valueMapper.calls) == 0 {
		// If all of the auxiliary keys are of an unknown type,
		// do not construct the iterator and return a null cursor.
		if !hasValidType(auxKeys) {
			return newNullCursor(fields), nil
		}

		itr, err := buildAuxIterator(ctx, ic, stmt.Sources, opt)
		if err != nil {
			return nil, err
		}

		// Create a slice with an empty first element.
		keys := []influxql.VarRef{{}}
		keys = append(keys, auxKeys...)

		scanner := NewIteratorScanner(itr, keys, opt.FillValue)
		return newScannerCursor(scanner, fields, opt), nil
	}

	// Check to see if this is a selector statement.
	// It is a selector if it is the only selector call and the call itself
	// is a selector.
	selector := len(valueMapper.calls) == 1
	if selector {
		for call := range valueMapper.calls {
			if !influxql.IsSelector(call) {
				selector = false
			}
		}
	}

	// Produce an iterator for every single call and create an iterator scanner
	// associated with it.
	var g errgroup.Group
	var mu sync.Mutex
	scanners := make([]IteratorScanner, 0, len(valueMapper.calls))
	for call := range valueMapper.calls {
		call := call

		driver := valueMapper.table[call]
		if driver.Type == influxql.Unknown {
			// The primary driver of this call is of unknown type, so skip this.
			continue
		}

		g.Go(func() error {
			itr, err := buildFieldIterator(ctx, call, ic, stmt.Sources, opt, selector, stmt.Target != nil)
			if err != nil {
				return err
			}

			keys := make([]influxql.VarRef, 0, len(auxKeys)+1)
			keys = append(keys, driver)
			keys = append(keys, auxKeys...)

			scanner := NewIteratorScanner(itr, keys, opt.FillValue)

			mu.Lock()
			scanners = append(scanners, scanner)
			mu.Unlock()

			return nil
		})
	}

	// Close all scanners if any iterator fails.
	if err := g.Wait(); err != nil {
		for _, s := range scanners {
			s.Close()
		}
		return nil, err
	}

	if len(scanners) == 0 {
		return newNullCursor(fields), nil
	} else if len(scanners) == 1 {
		return newScannerCursor(scanners[0], fields, opt), nil
	}
	return newMultiScannerCursor(scanners, fields, opt), nil
}


~~~



## TaskManager



##### TaskManager.AttachQuery

~~~go
// AttachQuery attaches a running query to be managed by the TaskManager.
// Returns the query id of the newly attached query or an error if it was
// unable to assign a query id or attach the query to the TaskManager.
// This function also returns a channel that will be closed when this
// query finishes running.
//
// After a query finishes running, the system is free to reuse a query id.
func (t *TaskManager) AttachQuery(q *influxql.Query, opt ExecutionOptions, interrupt <-chan struct{}) (*ExecutionContext, func(), error) {
	t.mu.Lock()
	defer t.mu.Unlock()

	if t.shutdown {
		return nil, nil, ErrQueryEngineShutdown
	}

    //最大并发查询数
	if t.MaxConcurrentQueries > 0 && len(t.queries) >= t.MaxConcurrentQueries {
		return nil, nil, ErrMaxConcurrentQueriesLimitExceeded(len(t.queries), t.MaxConcurrentQueries)
	}

	qid := t.nextID
	query := &Task{
		query:     q.String(),
		database:  opt.Database,
		status:    RunningTask,
		startTime: time.Now(),
		closing:   make(chan struct{}),
		monitorCh: make(chan error),
	}
	t.queries[qid] = query

	go t.waitForQuery(qid, query.closing, interrupt, query.monitorCh)
	if t.LogQueriesAfter != 0 {
		go query.monitor(func(closing <-chan struct{}) error {
			timer := time.NewTimer(t.LogQueriesAfter)
			defer timer.Stop()

			select {
			case <-timer.C:
				t.Logger.Warn(fmt.Sprintf("Detected slow query: %s (qid: %d, database: %s, threshold: %s)",
					query.query, qid, query.database, t.LogQueriesAfter))
			case <-closing:
			}
			return nil
		})
	}
	t.nextID++

	ctx := &ExecutionContext{
		Context:          context.Background(),
		QueryID:          qid,
		task:             query,
		ExecutionOptions: opt,
	}
	ctx.watch()
	return ctx, func() { t.DetachQuery(qid) }, nil
}
~~~



## Emitter

##### Emitter.Emit

~~~go
// Emit returns the next row from the iterators.
func (e *Emitter) Emit() (*models.Row, bool, error) {
	// Continually read from the cursor until it is exhausted.
	for {
		// Scan the next row. If there are no rows left, return the current row.
		var row Row
		if !e.cur.Scan(&row) {
			if err := e.cur.Err(); err != nil {
				return nil, false, err
			}
			r := e.row
			e.row = nil
			return r, false, nil
		}

		// If there's no row yet then create one.
		// If the name and tags match the existing row, append to that row if
		// the number of values doesn't exceed the chunk size.
		// Otherwise return existing row and add values to next emitted row.
		if e.row == nil {
			e.createRow(row.Series, row.Values)
		} else if e.series.SameSeries(row.Series) {
			if e.chunkSize > 0 && len(e.row.Values) >= e.chunkSize {
				r := e.row
				r.Partial = true
				e.createRow(row.Series, row.Values)
				return r, true, nil
			}
			e.row.Values = append(e.row.Values, row.Values)
		} else {
			r := e.row
			e.createRow(row.Series, row.Values)
			return r, true, nil
		}
	}
}

~~~

