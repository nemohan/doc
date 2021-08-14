# TSMWriter

[TOC]



##### tsmWriter.WriteBlock

~~~go
// WriteBlock writes block for the given key and time range to the TSM file.  If the write
// exceeds max entries for a given key, ErrMaxBlocksExceeded is returned.  This indicates
// that the index is now full for this key and no future writes to this key will succeed.
func (t *tsmWriter) WriteBlock(key []byte, minTime, maxTime int64, block []byte) error {
	if len(key) > maxKeyLength {
		return ErrMaxKeyLengthExceeded
	}

	// Nothing to write
	if len(block) == 0 {
		return nil
	}

	blockType, err := BlockType(block)
	if err != nil {
		return err
	}

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

	// fsync the file periodically to avoid long pauses with very big files.
	if t.n-t.lastSync > fsyncEvery {
		if err := t.sync(); err != nil {
			return err
		}
		t.lastSync = t.n
	}

	if len(t.index.Entries(key)) >= maxIndexEntries {
		return ErrMaxBlocksExceeded
	}

	return nil
}
~~~



##### tsmWriter.WriteIndex

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



## IndexWriter



### directIndex

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



##### directIndex.Add

~~~go
func (d *directIndex) Add(key []byte, blockType byte, minTime, maxTime int64, offset int64, size uint32) {
	// Is this the first block being added?
	if len(d.key) == 0 {
		// size of the key stored in the index
		d.size += uint32(2 + len(key))
        //indexCountSize 常量2
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

		// size of the encoded index entry
		d.size += indexEntrySize

	} else if cmp < 0 {
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

