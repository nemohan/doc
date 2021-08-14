# fileStore

[TOC]



##### NewFileStore

~~~go
// NewFileStore returns a new instance of FileStore based on the given directory.
func NewFileStore(dir string) *FileStore {
	logger := zap.NewNop()
	fs := &FileStore{
		dir:          dir,
		lastModified: time.Time{},
		logger:       logger,
		traceLogger:  logger,
		openLimiter:  limiter.NewFixed(runtime.GOMAXPROCS(0)),
		stats:        &FileStoreStatistics{},
		purger: &purger{
			files:  map[string]TSMFile{},
			logger: logger,
		},
		obs:           noFileStoreObserver{},
		parseFileName: DefaultParseFileName,
	}
	fs.purger.fileStore = fs
	return fs
}

~~~



##### FileStore.Open



~~~
// Open loads all the TSM files in the configured directory.
func (f *FileStore) Open() error {
	f.mu.Lock()
	defer f.mu.Unlock()

	// Not loading files from disk so nothing to do
	if f.dir == "" {
		return nil
	}

	if f.openLimiter == nil {
		return errors.New("cannot open FileStore without an OpenLimiter (is EngineOptions.OpenLimiter set?)")
	}

	// find the current max ID for temp directories
	tmpfiles, err := ioutil.ReadDir(f.dir)
	if err != nil {
		return err
	}
	ext := fmt.Sprintf(".%s", TmpTSMFileExtension)
	for _, fi := range tmpfiles {
		if fi.IsDir() && strings.HasSuffix(fi.Name(), ext) {
			ss := strings.Split(filepath.Base(fi.Name()), ".")
			if len(ss) == 2 {
				if i, err := strconv.Atoi(ss[0]); err != nil {
					if i > f.currentTempDirID {
						f.currentTempDirID = i
					}
				}
			}
		}
	}

	files, err := filepath.Glob(filepath.Join(f.dir, fmt.Sprintf("*.%s", TSMFileExtension)))
	if err != nil {
		return err
	}

	// struct to hold the result of opening each reader in a goroutine
	type res struct {
		r   *TSMReader
		err error
	}

	readerC := make(chan *res)
	for i, fn := range files {
		// Keep track of the latest ID
		generation, _, err := f.parseFileName(fn)
		if err != nil {
			return err
		}

		if generation >= f.currentGeneration {
			f.currentGeneration = generation + 1
		}

		file, err := os.OpenFile(fn, os.O_RDONLY, 0666)
		if err != nil {
			return fmt.Errorf("error opening file %s: %v", fn, err)
		}

		go func(idx int, file *os.File) {
			// Ensure a limited number of TSM files are loaded at once.
			// Systems which have very large datasets (1TB+) can have thousands
			// of TSM files which can cause extremely long load times.
			f.openLimiter.Take()
			defer f.openLimiter.Release()

			start := time.Now()
			df, err := NewTSMReader(file, WithMadviseWillNeed(f.tsmMMAPWillNeed))
			f.logger.Info("Opened file",
				zap.String("path", file.Name()),
				zap.Int("id", idx),
				zap.Duration("duration", time.Since(start)))

			// If we are unable to read a TSM file then log the error, rename
			// the file, and continue loading the shard without it.
			if err != nil {
				f.logger.Error("Cannot read corrupt tsm file, renaming", zap.String("path", file.Name()), zap.Int("id", idx), zap.Error(err))
				file.Close()
				if e := os.Rename(file.Name(), file.Name()+"."+BadTSMFileExtension); e != nil {
					f.logger.Error("Cannot rename corrupt tsm file", zap.String("path", file.Name()), zap.Int("id", idx), zap.Error(e))
					readerC <- &res{r: df, err: fmt.Errorf("cannot rename corrupt file %s: %v", file.Name(), e)}
					return
				}
				readerC <- &res{r: df, err: fmt.Errorf("cannot read corrupt file %s: %v", file.Name(), err)}
				return
			}

			df.WithObserver(f.obs)
			readerC <- &res{r: df}
		}(i, file)
	}

	var lm int64
	for range files {
		res := <-readerC
		if res.err != nil {
			return res.err
		} else if res.r == nil {
			continue
		}
		f.files = append(f.files, res.r)

		// Accumulate file store size stats
		atomic.AddInt64(&f.stats.DiskBytes, int64(res.r.Size()))
		for _, ts := range res.r.TombstoneFiles() {
			atomic.AddInt64(&f.stats.DiskBytes, int64(ts.Size))
		}

		// Re-initialize the lastModified time for the file store
		if res.r.LastModified() > lm {
			lm = res.r.LastModified()
		}

	}
	f.lastModified = time.Unix(0, lm).UTC()
	close(readerC)

	sort.Sort(tsmReaders(f.files))
	atomic.StoreInt64(&f.stats.FileCount, int64(len(f.files)))
	return nil
}
~~~

