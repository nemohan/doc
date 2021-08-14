# logFile



## LogFile



~~~
// LogFile represents an on-disk write-ahead log file.
type LogFile struct {
	mu         sync.RWMutex
	wg         sync.WaitGroup // ref count
	id         int            // file sequence identifier
	data       []byte         // mmap
	file       *os.File       // writer
	w          *bufio.Writer  // buffered writer
	bufferSize int            // The size of the buffer used by the buffered writer
	nosync     bool           // Disables buffer flushing and file syncing. Useful for offline tooling.
	buf        []byte         // marshaling buffer
	keyBuf     []byte

	sfile   *tsdb.SeriesFile // series lookup
	size    int64            // tracks current file size
	modTime time.Time        // tracks last time write occurred

	// In-memory series existence/tombstone sets.
	seriesIDSet, tombstoneSeriesIDSet *tsdb.SeriesIDSet

	// In-memory index.
	mms logMeasurements

	// Filepath to the log file.
	path string
}

// NewLogFile returns a new instance of LogFile.
func NewLogFile(sfile *tsdb.SeriesFile, path string) *LogFile {
	return &LogFile{
		sfile: sfile,
		path:  path,
		mms:   make(logMeasurements),

		seriesIDSet:          tsdb.NewSeriesIDSet(),
		tombstoneSeriesIDSet: tsdb.NewSeriesIDSet(),
	}
}
~~~

