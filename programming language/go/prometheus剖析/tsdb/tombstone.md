# tombstone



##### NewMemTombstones

~~~go
// NewMemTombstones creates new in memory Tombstone Reader
// that allows adding new intervals.
func NewMemTombstones() *MemTombstones {
	return &MemTombstones{intvlGroups: make(map[uint64]Intervals)}
}
~~~

