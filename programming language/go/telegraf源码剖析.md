# telegraf

[TOC]

## telegraf 配置

| 命令行选项              | 描述                                        | 备注                                                         |
| ----------------------- | ------------------------------------------- | ------------------------------------------------------------ |
| --input-filter <filter> | filter the inputs to enable, separator is : | 若指定的input插件在配置文件生效，但input-filter没有(input-filter的长度大于0）。该插件也不会生效 |
|                         |                                             |                                                              |
|                         |                                             |                                                              |



## telegraf 剖析

### 目录结构

| 目录            | 描述                           |
| --------------- | ------------------------------ |
| agent           | 启动所有插件                   |
| config          | 解析配置文件                   |
| metric          | 定义数据表示                   |
| plugins         | 定义输入、处理、聚合、输出插件 |
| plugins/inputs  | 输入插件                       |
| plugins/outputs | 输出插件                       |
| models          |                                |
| cmd             | mian函数                       |



### input 插件实现

* input plugin需要实现Input和PluginDescriber接口
* 在包初始化函数init中，调用inputs.Add将插件注册到inputs包中的全局变量Inputs中
* 需要修改配置文件和plugins/inputs/all.go 来引入新的插件所在的包
* 插件可以通过实现parsers.Input接口，定制配置文件解析

telegraf/plugin.go

~~~go
// PluginDescriber contains the functions all plugins must implement to describe
// themselves to Telegraf. Note that all plugins may define a logger that is
// not part of the interface, but will receive an injected logger if it's set.
// eg: Log telegraf.Logger `toml:"-"`
type PluginDescriber interface {
	// SampleConfig returns the default configuration of the Processor
	SampleConfig() string

	// Description returns a one-sentence description on the Processor
	Description() string
}
~~~

#### Input 接口的定义

telegraf/input.go

~~~go
type Input interface {
	PluginDescriber

	// Gather takes in an accumulator and adds the metrics that the Input
	// gathers. This is called every agent.interval
	Gather(Accumulator) error
}
~~~

#### Inputs全局变量，维护所有注册的插件

plugins/inputs/registry.go

~~~go
type Creator func() telegraf.Input

var Inputs = map[string]Creator{}

//creator在加载配置文件时，会被调用
func Add(name string, creator Creator) {
	Inputs[name] = creator
}
~~~

### output插件



输出插件需要实现telegraf.go/Output接口

#### Output 接口

~~~go
type Output interface {
	PluginDescriber

	// Connect to the Output; connect is only called once when the plugin starts
	Connect() error
	// Close any connections to the Output. Close is called once when the output
	// is shutting down. Close will not be called until all writes have finished,
	// and Write() will not be called once Close() has been, so locking is not
	// necessary.
	Close() error
	// Write takes in group of points to be written to the Output
	Write(metrics []Metric) error
}
~~~



### 运行机制剖析



* 解析命令行参数
* 启动监听信号量的协程
* 加载配置文件
* 依次初始化output插件、processor插件、聚合插件、input插件
* 为output插件、processor插件、聚合插件、input插件启动协程



采集的数据的传输通过channel来实现：

* 初始化输出插件的时候，创建一个channel。所有的输出插件共用一个channel ，共用通过models/RuningOutput实现。从channel接收到的数据为每个输出插件制作一份拷贝
* 所有的输入插件共用初始化输出插件时创建的channel， 共用通过models/RunningInput实现

#### 信号量处理和配置文件热加载

telegraf通过捕获信号量syscall.SIGHUP触发配置文件重新加载。信号量触发时取消其他在执行任务的协程

##### reloadLoop

- 调用context.WithCancel创建ctx, 通过使用这个ctx取消其他协程的执行
- 创建等待处理信号量的协程
- runAgent一直运行直到有信号量触发

~~~go
func reloadLoop(
	inputFilters []string,
	outputFilters []string,
	aggregatorFilters []string,
	processorFilters []string,
) {
	reload := make(chan bool, 1)
	reload <- true
	for <-reload {
		reload <- false

		ctx, cancel := context.WithCancel(context.Background())

		signals := make(chan os.Signal, 1)
		signal.Notify(signals, os.Interrupt, syscall.SIGHUP,
			syscall.SIGTERM, syscall.SIGINT)
		go func() {
			select {
			case sig := <-signals:
				if sig == syscall.SIGHUP {
					log.Printf("I! Reloading Telegraf config")
                    //即使这里<-reload，for <-reload也不会执行。因为cancel尚未执行
					<-reload
                    //使得for <-reload可以读取到值
					reload <- true
				}
                //取消其他协程的执行，会导致runAgent返回
				cancel()
			case <-stop:
				cancel()
			}
		}()

		err := runAgent(ctx, inputFilters, outputFilters)
		if err != nil && err != context.Canceled {
			log.Fatalf("E! [telegraf] Error running agent: %v", err)
		}
	}
}
~~~

#### 启动流程

1. 初始化输出插件
2. 初始化processor插件
3. 初始化聚合(Aggregator)插件
4. 初始化输入插件

####  初始化输出插件

telegraf主要以推送方式将数据传递到目标端，所以初始化输出插件时主要是建立到目标端的链接。

##### Agent.startOutputs 

* 创建传输采集数据用的channel

* 调用RunningOutput.connectOutput为每个输出插件建立到目标端的链接

* 将所有的ouput插件都整合到outputUnit.outputs切片中


~~~go
// startOutputs calls Connect on all outputs and returns the source channel.
// If an error occurs calling Connect all stared plugins have Close called.
func (a *Agent) startOutputs(
	ctx context.Context,
	outputs []*models.RunningOutput,
) (chan<- telegraf.Metric, *outputUnit, error) {
	src := make(chan telegraf.Metric, 100)
	unit := &outputUnit{src: src}
	for _, output := range outputs {
		err := a.connectOutput(ctx, output)
		if err != nil {
			for _, output := range unit.outputs {
				output.Close()
			}
			return nil, nil, fmt.Errorf("connecting output %s: %w", output.LogName(), err)
		}

		unit.outputs = append(unit.outputs, output)
	}

	return src, unit, nil
}
~~~

#### Agent.Run 启动并运行插件

* 调用initPlugins初始化所有插件
* 调用Agent.startOutputs启动输出插件
* 若配置文件定义了聚合插件，则启动所有聚合插件
* 调用Agent.startProcessors启动所有processor插件
* 调用Agent.startInputs启动所有输入插件

~~~go
// Run starts and runs the Agent until the context is done.
func (a *Agent) Run(ctx context.Context) error {
	log.Printf("I! [agent] Config: Interval:%s, Quiet:%#v, Hostname:%#v, "+
		"Flush Interval:%s",
		a.Config.Agent.Interval.Duration, a.Config.Agent.Quiet,
		a.Config.Agent.Hostname, a.Config.Agent.FlushInterval.Duration)

	log.Printf("D! [agent] Initializing plugins")
	err := a.initPlugins()
	if err != nil {
		return err
	}

	startTime := time.Now()

	log.Printf("D! [agent] Connecting outputs")
	next, ou, err := a.startOutputs(ctx, a.Config.Outputs)
	if err != nil {
		return err
	}

	var apu []*processorUnit
	var au *aggregatorUnit
	if len(a.Config.Aggregators) != 0 {
		aggC := next
		if len(a.Config.AggProcessors) != 0 {
			aggC, apu, err = a.startProcessors(next, a.Config.AggProcessors)
			if err != nil {
				return err
			}
		}

		next, au, err = a.startAggregators(aggC, next, a.Config.Aggregators)
		if err != nil {
			return err
		}
	}

	var pu []*processorUnit
	if len(a.Config.Processors) != 0 {
		next, pu, err = a.startProcessors(next, a.Config.Processors)
		if err != nil {
			return err
		}
	}

	iu, err := a.startInputs(next, a.Config.Inputs)
	if err != nil {
		return err
	}

	var wg sync.WaitGroup
	wg.Add(1)
	go func() {
		defer wg.Done()
		err := a.runOutputs(ou)
		if err != nil {
			log.Printf("E! [agent] Error running outputs: %v", err)
		}
	}()

	if au != nil {
		wg.Add(1)
		go func() {
			defer wg.Done()
			err := a.runProcessors(apu)
			if err != nil {
				log.Printf("E! [agent] Error running processors: %v", err)
			}
		}()

		wg.Add(1)
		go func() {
			defer wg.Done()
			err := a.runAggregators(startTime, au)
			if err != nil {
				log.Printf("E! [agent] Error running aggregators: %v", err)
			}
		}()
	}

	if pu != nil {
		wg.Add(1)
		go func() {
			defer wg.Done()
			err := a.runProcessors(pu)
			if err != nil {
				log.Printf("E! [agent] Error running processors: %v", err)
			}
		}()
	}

	wg.Add(1)
	go func() {
		defer wg.Done()
		err := a.runInputs(ctx, startTime, iu)
		if err != nil {
			log.Printf("E! [agent] Error running inputs: %v", err)
		}
	}()

	wg.Wait()

	log.Printf("D! [agent] Stopped Successfully")
	return err
}
~~~



### 输出插件的工作过程

#### Agent.runOutputs

* 创建控制输出的协程，定期将数据从输出插件输出到目标存储

* 从channel unit.src读取采集的数据，调用RunningOutput.AddMetric添加到缓存中
* 调用cancel，取消控制输出的协程
* 等待协程完成

~~~go
// runOutputs begins processing metrics and returns until the source channel is
// closed and all metrics have been written.  On shutdown metrics will be
// written one last time and dropped if unsuccessful.
func (a *Agent) runOutputs(
	unit *outputUnit,
) error {
	var wg sync.WaitGroup

	// Start flush loop
	interval := a.Config.Agent.FlushInterval.Duration
	jitter := a.Config.Agent.FlushJitter.Duration

	ctx, cancel := context.WithCancel(context.Background())

	for _, output := range unit.outputs {
		interval := interval
		// Overwrite agent flush_interval if this plugin has its own.
		if output.Config.FlushInterval != 0 {
			interval = output.Config.FlushInterval
		}

		jitter := jitter
		// Overwrite agent flush_jitter if this plugin has its own.
		if output.Config.FlushJitter != 0 {
			jitter = output.Config.FlushJitter
		}

		wg.Add(1)
		go func(output *models.RunningOutput) {
			defer wg.Done()

			ticker := NewRollingTicker(interval, jitter)
			defer ticker.Stop()

			a.flushLoop(ctx, output, ticker)
		}(output)
	}

    //unit.src是初始化输出插件时创建的channel, 
	for metric := range unit.src {
		for i, output := range unit.outputs {
			if i == len(a.Config.Outputs)-1 {
				output.AddMetric(metric)
			} else {
                //其他插件使用拷贝的数据
				output.AddMetric(metric.Copy())
			}
		}
	}

	log.Println("I! [agent] Hang on, flushing any cached metrics before shutdown")
	cancel()
	wg.Wait()

	return nil
}
~~~



#### Agnet.flushLoop 将buffer中的数据刷到输出插件

* 创建监听信号量SIGUSR1的channel
* 检查context.Done()，若已经被取消则协程退出
* 等待context.Done、ticker、信号量、批处理等条件触发。触发则调用Agent.flushOnce

~~~go
// flushLoop runs an output's flush function periodically until the context is
// done.
func (a *Agent) flushLoop(
	ctx context.Context,
	output *models.RunningOutput,
	ticker Ticker,
) {
	logError := func(err error) {
		if err != nil {
			log.Printf("E! [agent] Error writing to %s: %v", output.LogName(), err)
		}
	}

	// watch for flush requests
	flushRequested := make(chan os.Signal, 1)
	watchForFlushSignal(flushRequested)
	defer stopListeningForFlushSignal(flushRequested)

	for {
		// Favor shutdown over other methods.
		select {
		case <-ctx.Done():
			logError(a.flushOnce(output, ticker, output.Write))
			return
		default:
		}

		select {
		case <-ctx.Done():
			logError(a.flushOnce(output, ticker, output.Write))
			return
		case <-ticker.Elapsed():
			logError(a.flushOnce(output, ticker, output.Write))
		case <-flushRequested:
			logError(a.flushOnce(output, ticker, output.Write))
		case <-output.BatchReady:
			// Favor the ticker over batch ready
			select {
			case <-ticker.Elapsed():
				logError(a.flushOnce(output, ticker, output.Write))
			default:
				logError(a.flushOnce(output, ticker, output.WriteBatch))
			}
		}
	}
}
~~~



#### Agent.flushOnce

* 调用writeFunc(实际是RunningOutput.Write)

~~~go
// flushOnce runs the output's Write function once, logging a warning each
// interval it fails to complete before.
func (a *Agent) flushOnce(
	output *models.RunningOutput,
	ticker Ticker,
	writeFunc func() error,
) error {
	done := make(chan error)
	go func() {
		done <- writeFunc()
	}()

	for {
		select {
		case err := <-done:
			output.LogBufferStatus()
			return err
		case <-ticker.Elapsed():
			log.Printf("W! [agent] [%q] did not complete within its flush interval",
				output.LogName())
			output.LogBufferStatus()
		}
	}
}
~~~

#### RunningOutput

##### RunningOutput.AddMetric

~~~go
// AddMetric adds a metric to the output.
//
// Takes ownership of metric
func (ro *RunningOutput) AddMetric(metric telegraf.Metric) {
	if ok := ro.Config.Filter.Select(metric); !ok {
		ro.metricFiltered(metric)
		return
	}

	ro.Config.Filter.Modify(metric)
	if len(metric.FieldList()) == 0 {
		ro.metricFiltered(metric)
		return
	}

	if output, ok := ro.Output.(telegraf.AggregatingOutput); ok {
		ro.aggMutex.Lock()
		output.Add(metric)
		ro.aggMutex.Unlock()
		return
	}

	if len(ro.Config.NameOverride) > 0 {
		metric.SetName(ro.Config.NameOverride)
	}

	if len(ro.Config.NamePrefix) > 0 {
		metric.AddPrefix(ro.Config.NamePrefix)
	}

	if len(ro.Config.NameSuffix) > 0 {
		metric.AddSuffix(ro.Config.NameSuffix)
	}

	dropped := ro.buffer.Add(metric)
	atomic.AddInt64(&ro.droppedMetrics, int64(dropped))

	count := atomic.AddInt64(&ro.newMetricsCount, 1)
	if count == int64(ro.MetricBatchSize) {
		atomic.StoreInt64(&ro.newMetricsCount, 0)
		select {
		case ro.BatchReady <- time.Now():
		default:
		}
	}
}
~~~

##### RunningOutput.Write

~~~go
// Write writes all metrics to the output, stopping when all have been sent on
// or error.
func (ro *RunningOutput) Write() error {
	if output, ok := ro.Output.(telegraf.AggregatingOutput); ok {
		ro.aggMutex.Lock()
		metrics := output.Push()
		ro.buffer.Add(metrics...)
		output.Reset()
		ro.aggMutex.Unlock()
	}

	atomic.StoreInt64(&ro.newMetricsCount, 0)

	// Only process the metrics in the buffer now.  Metrics added while we are
	// writing will be sent on the next call.
	nBuffer := ro.buffer.Len()
	nBatches := nBuffer/ro.MetricBatchSize + 1
	for i := 0; i < nBatches; i++ {
		batch := ro.buffer.Batch(ro.MetricBatchSize)
		if len(batch) == 0 {
			break
		}

		err := ro.write(batch)
		if err != nil {
			ro.buffer.Reject(batch)
			return err
		}
		ro.buffer.Accept(batch)
	}
	return nil
}
~~~











### 缓存机制 metric buffer 



#### Buffer.Add

~~~go
// Add adds metrics to the buffer and returns number of dropped metrics.
func (b *Buffer) Add(metrics ...telegraf.Metric) int {
	b.Lock()
	defer b.Unlock()

	dropped := 0
	for i := range metrics {
		if n := b.add(metrics[i]); n != 0 {
			dropped += n
		}
	}

	b.BufferSize.Set(int64(b.length()))
	return dropped
}
~~~



##### Buffer.add  发现个bug??

为什么调用b.metricDropped(b.buf[b.last])。感觉像是个bug，应该用b.first才对吧



~~~go
func (b *Buffer) add(m telegraf.Metric) int {
	dropped := 0
	// Check if Buffer is full
	if b.size == b.cap {
        //这是个bug??
		b.metricDropped(b.buf[b.last])
		dropped++

		if b.batchSize > 0 {
			b.batchSize--
			b.batchFirst = b.next(b.batchFirst)
		}
	}

	b.metricAdded()
	//若buf已经满了，b.last则指向最先入队那个
	b.buf[b.last] = m
	b.last = b.next(b.last)

    //最先入队的已经被覆盖了，应该调整b.first指向次最先入队的metric
	if b.size == b.cap {
		b.first = b.next(b.first)
	}

	b.size = min(b.size+1, b.cap)
	return dropped
}
~~~



### 数据采集过程



#### Agent.runInputs 为每一个采集插件启动一个协程，并等待所有采集协程退出

Agent.runInputs为每个采集插件启动一个协程，并等待所有采集协程退出。当触发信号量时，调用ctx.cancel才会通知采集协程退出。

* 为每个插件启动协程
* 等待采集协程完成
* 关闭channel unit.dst, 即输出通道

~~~go
// runInputs starts and triggers the periodic gather for Inputs.
//
// When the context is done the timers are stopped and this function returns
// after all ongoing Gather calls complete.
func (a *Agent) runInputs(
	ctx context.Context,
	startTime time.Time,
	unit *inputUnit,
) error {
	var wg sync.WaitGroup
	for _, input := range unit.inputs {
		// Overwrite agent interval if this plugin has its own.
		interval := a.Config.Agent.Interval.Duration
		if input.Config.Interval != 0 {
			interval = input.Config.Interval
		}

		// Overwrite agent precision if this plugin has its own.
		precision := a.Config.Agent.Precision.Duration
		if input.Config.Precision != 0 {
			precision = input.Config.Precision
		}

		// Overwrite agent collection_jitter if this plugin has its own.
		jitter := a.Config.Agent.CollectionJitter.Duration
		if input.Config.CollectionJitter != 0 {
			jitter = input.Config.CollectionJitter
		}

		var ticker Ticker
		if a.Config.Agent.RoundInterval {
			ticker = NewAlignedTicker(startTime, interval, jitter)
		} else {
			ticker = NewUnalignedTicker(interval, jitter)
		}
		defer ticker.Stop()

		acc := NewAccumulator(input, unit.dst)
		acc.SetPrecision(getPrecision(precision, interval))

		wg.Add(1)
		go func(input *models.RunningInput) {
			defer wg.Done()
			a.gatherLoop(ctx, acc, input, ticker, interval)
		}(input)
	}

	wg.Wait()

	log.Printf("D! [agent] Stopping service inputs")
	stopServiceInputs(unit.inputs)

	close(unit.dst)
	log.Printf("D! [agent] Input channel closed")

	return nil
}
~~~

#### Agetn.gatherLoop 负责采集任务的协程

参数ticker控制采集周期

~~~go
// gather runs an input's gather function periodically until the context is
// done.
func (a *Agent) gatherLoop(
	ctx context.Context,
	acc telegraf.Accumulator,
	input *models.RunningInput,
	ticker Ticker,
	interval time.Duration,
) {
	defer panicRecover(input)

	for {
		select {
		case <-ticker.Elapsed():
			err := a.gatherOnce(acc, input, ticker, interval)
			if err != nil {
				acc.AddError(err)
			}
		case <-ctx.Done():
			return
		}
	}
}
~~~



#### Agent.gatherOnce 调用采集插件

采集的数据通过accumulator.metrics channel 将数据送的输出插件, 这一步是在input.Gather函数内完成的

~~~go
// gatherOnce runs the input's Gather function once, logging a warning each
// interval it fails to complete before.
func (a *Agent) gatherOnce(
	acc telegraf.Accumulator,
	input *models.RunningInput,
	ticker Ticker,
	interval time.Duration,
) error {
	done := make(chan error)
	go func() {
		done <- input.Gather(acc)
	}()

	// Only warn after interval seconds, even if the interval is started late.
	// Intervals can start late if the previous interval went over or due to
	// clock changes.
	slowWarning := time.NewTicker(interval)
	defer slowWarning.Stop()
	
    //即便超时也会等待采集完成,所以上面的采集函数使用的goroutine不会泄露
	for {
		select {
		case err := <-done:
			return err
		case <-slowWarning.C:
			log.Printf("W! [%s] Collection took longer than expected; not complete after interval of %s",
				input.LogName(), interval)
		case <-ticker.Elapsed():
			log.Printf("D! [%s] Previous collection has not completed; scheduled collection skipped",
				input.LogName())
		}
	}
}
~~~



#### RunningInput

##### RunningInput.MakeMetric

* r.Config.Filter.Select 根据插件的配置进一步过滤不需要的tag或field

* 调用makemetric添加配置文件定义的前缀、后缀、标签(tag)和全局tag
* r.Config.Filter.Modify

~~~go
func (r *RunningInput) MakeMetric(metric telegraf.Metric) telegraf.Metric {
	if ok := r.Config.Filter.Select(metric); !ok {
		r.metricFiltered(metric)
		return nil
	}

	m := makemetric(
		metric,
		r.Config.NameOverride,
		r.Config.MeasurementPrefix,
		r.Config.MeasurementSuffix,
		r.Config.Tags,
		r.defaultTags)

	r.Config.Filter.Modify(metric)
	if len(metric.FieldList()) == 0 {
		r.metricFiltered(metric)
		return nil
	}

	r.MetricsGathered.Incr(1)
	GlobalMetricsGathered.Incr(1)
	return m
}
~~~



### 采集的数据的表示及转换

#### accumulator

~~~go
type accumulator struct {
	maker     MetricMaker
	metrics   chan<- telegraf.Metric
	precision time.Duration
}

func NewAccumulator(
	maker MetricMaker,
	metrics chan<- telegraf.Metric,
) telegraf.Accumulator {
	acc := accumulator{
		maker:     maker,
		metrics:   metrics,
		precision: time.Nanosecond,
	}
	return &acc
}
~~~

##### accumulator.AddFields

~~~go
func (ac *accumulator) AddFields(
	measurement string,
	fields map[string]interface{},
	tags map[string]string,
	t ...time.Time,
) {
	ac.addFields(measurement, tags, fields, telegraf.Untyped, t...)
}

~~~

##### accumulator.addFields

* 先调用metrirc.New将采集数据放到metric结构中
* 再调用RunningInput.MakeMetric

~~~go
func (ac *accumulator) addFields(
	measurement string,
	tags map[string]string,
	fields map[string]interface{},
	tp telegraf.ValueType,
	t ...time.Time,
) {
	m, err := metric.New(measurement, tags, fields, ac.getTime(t), tp)
	if err != nil {
		return
	}
	if m := ac.maker.MakeMetric(m); m != nil {
		ac.metrics <- m
	}
}
~~~

#### metric的定义

~~~go
type metric struct {
	name   string
	tags   []*telegraf.Tag
	fields []*telegraf.Field
	tm     time.Time

	tp        telegraf.ValueType
	aggregate bool
}
~~~



##### metric.AddFieild

~~~go
func (m *metric) AddField(key string, value interface{}) {
	for i, field := range m.fields {
		if key == field.Key {
			m.fields[i] = &telegraf.Field{Key: key, Value: convertField(value)}
			return
		}
	}
	m.fields = append(m.fields, &telegraf.Field{Key: key, Value: convertField(value)})

~~~

### 指标的维度

telegraf中使用tag作为采集的指标数据的维度。对应prometheus中的label

以下是telegraf采集五元组(源ip、源端口、目标ip、目标端口、协议)插件的代码片段。tags指定了相关的维度，如local_ip、local_port等

~~~go
	srcIP := tuples[3]
				dstIP := tuples[4]
				index := strings.LastIndex(tuples[3], ":")
				rIndex := strings.LastIndex(tuples[4], ":")

				tags := map[string]string{
					"local_ip":    srcIP[:index],
					"local_port":  srcIP[index+1:],
					"remote_ip":   dstIP[:rIndex],
					"remote_port": dstIP[rIndex+1:],
					"proto":       tuples[0],
				}
				acc.AddFields("netfivetuple", map[string]interface{}{"tuples": 1}, tags)
~~~



在prometheus中，按指定local_port为22的过滤条件得到的结果：

![image-20201111110957349](C:\Users\monster\AppData\Roaming\Typora\typora-user-images\image-20201111110957349.png)

## 总结

