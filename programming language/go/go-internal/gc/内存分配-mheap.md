# gmheap

[TOC]





mheap的内存布局:

~~~
spans | bitmap|                                      free |
			  ^											  ^
			  |											  |
			  used										  end
~~~



##### mheap的定义

mheap维护了哪些东西:

* 空闲的span（内存页面数目不超过128的span) 队列 mheap.free 和mheap.freelarge(页面数目超过128)

* mheap.spans 页面-span映射表，即这个页面属于哪个span


~~~go
// Main malloc heap.
// The heap itself is the "free[]" and "large" arrays,
// but all the other global data is here too.
//
// mheap must not be heap-allocated because it contains mSpanLists,
// which must not be heap-allocated.
//
//go:notinheap
type mheap struct {
	lock      mutex
    /*
    _MaxMHeapList   = 1 << (20 - _PageShift) // Maximum page length for fixed-size list in MHeap.
    free 是个固定大小（128）的链表，
    每个span管理若干个页面，
    管理相同数目页面的span形成一个mSpanList。
    这样span管理的页面数目就是空闲队列free的索引
    free是一个由管理的内存页面数目小于_MaxMHeapList的mSpanList空闲队列
    */
	free      [_MaxMHeapList]mSpanList // free lists of given length
	freelarge mSpanList                // free lists length >= _MaxMHeapList
	busy      [_MaxMHeapList]mSpanList // busy lists of large objects of given length
	busylarge mSpanList                // busy lists of large objects length >= _MaxMHeapList
    
    //sweep分代
	sweepgen  uint32                   // sweep generation, see comment in mspan
	sweepdone uint32                   // all spans are swept

	// allspans is a slice of all mspans ever created. Each mspan
	// appears exactly once.
	//
	// The memory for allspans is manually managed and can be
	// reallocated and move as the heap grows.
	//
	// In general, allspans is protected by mheap_.lock, which
	// prevents concurrent access as well as freeing the backing
	// store. Accesses during STW might not hold the lock, but
	// must ensure that allocation cannot happen around the
	// access (since that may free the backing store).
	allspans []*mspan // all spans out there

	//页面-span映射表    
	// spans is a lookup table to map virtual address page IDs to *mspan.
	// For allocated spans, their pages map to the span itself.
	// For free spans, only the lowest and highest pages map to the span itself.
	// Internal pages map to an arbitrary span.
	// For pages that have never been allocated, spans entries are nil.
	//
	// This is backed by a reserved region of the address space so
	// it can grow without moving. The memory up to len(spans) is
	// mapped. cap(spans) indicates the total reserved memory.
	spans []*mspan

	// sweepSpans contains two mspan stacks: one of swept in-use
	// spans, and one of unswept in-use spans. These two trade
	// roles on each GC cycle. Since the sweepgen increases by 2
	// on each cycle, this means the swept spans are in
	// sweepSpans[sweepgen/2%2] and the unswept spans are in
	// sweepSpans[1-sweepgen/2%2]. Sweeping pops spans from the
	// unswept stack and pushes spans that are still in-use on the
	// swept stack. Likewise, allocating an in-use span pushes it
	// on the swept stack.
	sweepSpans [2]gcSweepBuf

	_ uint32 // align uint64 fields on 32-bit for atomics

	// Proportional sweep
	pagesInUse        uint64  // pages of spans in stats _MSpanInUse; R/W with mheap.lock
	spanBytesAlloc    uint64  // bytes of spans allocated this cycle; updated atomically
	pagesSwept        uint64  // pages swept this cycle; updated atomically
	sweepPagesPerByte float64 // proportional sweep ratio; written with lock, read without
	// TODO(austin): pagesInUse should be a uintptr, but the 386
	// compiler can't 8-byte align fields.

	// Malloc stats.
	largefree  uint64                  // bytes freed for large objects (>maxsmallsize)
	nlargefree uint64                  // number of frees for large objects (>maxsmallsize)
	nsmallfree [_NumSizeClasses]uint64 // number of frees for small objects (<=maxsmallsize)

	// range of addresses we might see in the heap
	bitmap         uintptr // Points to one byte past the end of the bitmap
	bitmap_mapped  uintptr
	arena_start    uintptr
	arena_used     uintptr // always mHeap_Map{Bits,Spans} before updating
	arena_end      uintptr
	arena_reserved bool

	// central free lists for small size classes.
	// the padding makes sure that the MCentrals are
	// spaced CacheLineSize bytes apart, so that each MCentral.lock
	// gets its own cache line.
	central [_NumSizeClasses]struct {
		mcentral mcentral
		pad      [sys.CacheLineSize]byte
	}

	spanalloc             fixalloc // allocator for span*
	cachealloc            fixalloc // allocator for mcache*
	specialfinalizeralloc fixalloc // allocator for specialfinalizer*
	specialprofilealloc   fixalloc // allocator for specialprofile*
	speciallock           mutex    // lock for special record allocators.
}
~~~



##### mSpanList 的定义

mSpanList 是一个由管理页面数相同的span形成的链表.

例如span_a 管理4个页面，span_b同样管理四个页面。那么span_a 和span_b就是mSpanList维护的链表的元素

~~~go
// mSpanList heads a linked list of spans.
//
//go:notinheap
type mSpanList struct {
	first *mspan // first span in list, or nil if none
	last  *mspan // last span in list, or nil if none
}
~~~



##### mheap.init 

runtime/mheap.go

- 初始化mheap.spanalloc、mheap.cachealloc、mheap.specialfinalizeralloc、mheap.specialprofilealloc, 这些结构使用的内存都是通过fixalloc分配器分配而来

~~~go
// Initialize the heap.
func (h *mheap) init(spansStart, spansBytes uintptr) {
	h.spanalloc.init(unsafe.Sizeof(mspan{}), recordspan, unsafe.Pointer(h), &memstats.mspan_sys)
    
	h.cachealloc.init(unsafe.Sizeof(mcache{}), nil, nil, &memstats.mcache_sys)
    
	h.specialfinalizeralloc.init(unsafe.Sizeof(specialfinalizer{}), nil, nil, &memstats.other_sys)
    
	h.specialprofilealloc.init(unsafe.Sizeof(specialprofile{}), nil, nil, &memstats.other_sys)

	// Don't zero mspan allocations. Background sweeping can
	// inspect a span concurrently with allocating it, so it's
	// important that the span's sweepgen survive across freeing
	// and re-allocating a span to prevent background sweeping
	// from improperly cas'ing it from 0.
	//
	// This is safe because mspan contains no heap pointers.
	h.spanalloc.zero = false

	// h->mapcache needs no init
	for i := range h.free {
		h.free[i].init()
		h.busy[i].init()
	}

	h.freelarge.init()
	h.busylarge.init()
	for i := range h.central {
		h.central[i].mcentral.init(int32(i))
	}

	sp := (*slice)(unsafe.Pointer(&h.spans))
	sp.array = unsafe.Pointer(spansStart)
	sp.len = 0
	sp.cap = int(spansBytes / sys.PtrSize)
}

~~~





### mheap的内存分配

全局变量mheap_的初始化见《内存分配-初始化》



##### 内存分配的过程

* 调用alloc_m 创建一个管理若干内存页面的span
* alloc_m 首先尝试释放一些已经被gc清扫过的内存
* alloc_m调用mheap.allocSpanLocked
* mheap.allocSpanLocked 首先尝试从空闲队列mheap.free获取内存



内存分配四部曲:

1) mheap.alloc_m

2) mheap.allocSpanLocked

3) mheap.allocLarge 

4) mheap.grow 

5) mheap.sysAlloc



##### 0) mheap.alloc 从mheap获取新的或空闲的mspan

~~~go
func (h *mheap) alloc(npage uintptr, sizeclass int32, large bool, needzero bool) *mspan {
	// Don't do any operations that lock the heap on the G stack.
	// It might trigger stack growth, and the stack growth code needs
	// to be able to allocate heap.
	var s *mspan
	systemstack(func() {
		s = h.alloc_m(npage, sizeclass, large)
	})

	if s != nil {
		if needzero && s.needzero != 0 {
			memclrNoHeapPointers(unsafe.Pointer(s.base()), s.npages<<_PageShift)
		}
		s.needzero = 0
	}
	return s
}
~~~



##### 1）mheap.alloc_m

* 上锁

* 尝试释放部分已经被GC清扫的内存
* 调用mheap.allocSpanLocked获取管理若干内存页面的span(从空闲队列获取或新创建)
* 初始化新获取的msapn ,并将其放入mheap.sweepSpans管理的队列
* 若large参数为true, 则将其放入mheap.busy或mheap.busyLarge队列

~~~go
// Allocate a new span of npage pages from the heap for GC'd memory
// and record its size class in the HeapMap and HeapMapCache.
func (h *mheap) alloc_m(npage uintptr, sizeclass int32, large bool) *mspan {
	_g_ := getg()
	if _g_ != _g_.m.g0 {
		throw("_mheap_alloc not on g0 stack")
	}
	lock(&h.lock)

    //调用gc释放内存
	// To prevent excessive heap growth, before allocating n pages
	// we need to sweep and reclaim at least n pages.
	if h.sweepdone == 0 {
		// TODO(austin): This tends to sweep a large number of
		// spans in order to find a few completely free spans
		// (for example, in the garbage benchmark, this sweeps
		// ~30x the number of pages its trying to allocate).
		// If GC kept a bit for whether there were any marks
		// in a span, we could release these free spans
		// at the end of GC and eliminate this entirely.
		h.reclaim(npage)
	}

	// transfer stats from cache to global
	memstats.heap_scan += uint64(_g_.m.mcache.local_scan)
	_g_.m.mcache.local_scan = 0
	memstats.tinyallocs += uint64(_g_.m.mcache.local_tinyallocs)
	_g_.m.mcache.local_tinyallocs = 0

	s := h.allocSpanLocked(npage)
    //下面这一段不是很明白
	if s != nil {
		// Record span info, because gc needs to be
		// able to map interior pointer to containing span.
		atomic.Store(&s.sweepgen, h.sweepgen)
		h.sweepSpans[h.sweepgen/2%2].push(s) // Add to swept in-use list.
		s.state = _MSpanInUse
		s.allocCount = 0
		s.sizeclass = uint8(sizeclass)
		if sizeclass == 0 {
			s.elemsize = s.npages << _PageShift
			s.divShift = 0
			s.divMul = 0
			s.divShift2 = 0
			s.baseMask = 0
		} else {
			s.elemsize = uintptr(class_to_size[sizeclass])
			m := &class_to_divmagic[sizeclass]
			s.divShift = m.shift
			s.divMul = m.mul
			s.divShift2 = m.shift2
			s.baseMask = m.baseMask
		}

		// update stats, sweep lists
		h.pagesInUse += uint64(npage)
		if large {
			memstats.heap_objects++
			atomic.Xadd64(&memstats.heap_live, int64(npage<<_PageShift))
			// Swept spans are at the end of lists.
			if s.npages < uintptr(len(h.free)) {
				h.busy[s.npages].insertBack(s)
			} else {
				h.busylarge.insertBack(s)
			}
		}
	}
	// heap_scan and heap_live were updated.
	if gcBlackenEnabled != 0 {
		gcController.revise()
	}

	if trace.enabled {
		traceHeapAlloc()
	}

	// h.spans is accessed concurrently without synchronization
	// from other threads. Hence, there must be a store/store
	// barrier here to ensure the writes to h.spans above happen
	// before the caller can publish a pointer p to an object
	// allocated from s. As soon as this happens, the garbage
	// collector running on another processor could read p and
	// look up s in h.spans. The unlock acts as the barrier to
	// order these writes. On the read side, the data dependency
	// between p and the index in h.spans orders the reads.
	unlock(&h.lock)
	return s
}
~~~



##### 2）mheap.allocSpanLocked

* 根据页面大小（数目)从空闲队列mheap.free找到合适的空闲span链表
* 若没有找到，则调用mheap.allocLarge创建一个span。若创建失败则调用mheap.grow 从mheap分配页面
* 若找到合适的span, 检查是否满足条件。若满足条件则将其从空闲队列移除
* 若新的span的页面数超过要求分配的数目(使用bestFit策略从mheap.freelarge空闲队列获取span时会出现此种情况), 则一分为二再创建一个新的span管理多出的内存页面，并调用mheap.freeSpanLocked将其放入空闲队列(free 或mheap.freelarge)



疑问: s.npreleased

~~~go
// Allocates a span of the given size.  h must be locked.
// The returned span has been removed from the
// free list, but its state is still MSpanFree.
func (h *mheap) allocSpanLocked(npage uintptr) *mspan {
	var list *mSpanList
	var s *mspan

    //固定大小(内存页面数目)的span空闲队列中查找合适span
	// Try in fixed-size lists up to max.
	for i := int(npage); i < len(h.free); i++ {
		list = &h.free[i]
		if !list.isEmpty() {
			s = list.first
			goto HaveSpan
		}
	}

    //最佳匹配策略从mheap.freelarge查找合适span
	// Best fit in list of large spans.
	list = &h.freelarge
	s = h.allocLarge(npage)
	if s == nil {
        //调整mheap管理的内存
		if !h.grow(npage) {
			return nil
		}
		s = h.allocLarge(npage)
		if s == nil {
			return nil
		}
	}

HaveSpan:
	// Mark span in use.
	if s.state != _MSpanFree {
		throw("MHeap_AllocLocked - MSpan not free")
	}
	if s.npages < npage {
		throw("MHeap_AllocLocked - bad npages")
	}
	list.remove(s)
	if s.inList() {
		throw("still in list")
	}
    
    //s.npreleased
	if s.npreleased > 0 {
		sysUsed(unsafe.Pointer(s.base()), s.npages<<_PageShift)
		memstats.heap_released -= uint64(s.npreleased << _PageShift)
		s.npreleased = 0
	}

    //一分为二
	if s.npages > npage {
		// Trim extra and put it back in the heap.
		t := (*mspan)(h.spanalloc.alloc())
		t.init(s.base()+npage<<_PageShift, s.npages-npage)
		s.npages = npage
		p := (t.base() - h.arena_start) >> _PageShift
		if p > 0 {
			h.spans[p-1] = s
		}
		h.spans[p] = t
		h.spans[p+t.npages-1] = t
		t.needzero = s.needzero
		s.state = _MSpanStack // prevent coalescing with s
		t.state = _MSpanStack
		h.freeSpanLocked(t, false, false, s.unusedsince)
		s.state = _MSpanFree
	}
	s.unusedsince = 0

	p := (s.base() - h.arena_start) >> _PageShift
	for n := uintptr(0); n < npage; n++ {
		h.spans[p+n] = s
	}

	memstats.heap_inuse += uint64(npage << _PageShift)
	memstats.heap_idle -= uint64(npage << _PageShift)

	//println("spanalloc", hex(s.start<<_PageShift))
	if s.inList() {
		throw("still in list")
	}
	return s
}
~~~



#####  3) mheap.allocLarge 使用BetsFit策略找从mspan空闲队列到大小合适的span

* 从空闲span队列mheap.freelarge使用BestFit(最优，页面数目最接近分配页面数的span) 策略找到合适的span

~~~go
// Allocate a span of exactly npage pages from the list of large spans.
func (h *mheap) allocLarge(npage uintptr) *mspan {
	return bestFit(&h.freelarge, npage, nil)
}

// Search list for smallest span with >= npage pages.
// If there are multiple smallest spans, take the one
// with the earliest starting address.
func bestFit(list *mSpanList, npage uintptr, best *mspan) *mspan {
	for s := list.first; s != nil; s = s.next {
		if s.npages < npage {
			continue
		}
		if best == nil || s.npages < best.npages || (s.npages == best.npages && s.base() < best.base()) {
			best = s
		}
	}
	return best
}
~~~



##### 4) mheap.grow

runtime/mheap.go

* 调用sysAlloc 从heap为span分配内存页面
* 调用mheap.freeSpanLocked将新创建的span加入空闲队列

~~~go
// Try to add at least npage pages of memory to the heap,
// returning whether it worked.
//
// h must be locked.
func (h *mheap) grow(npage uintptr) bool {
	// Ask for a big chunk, to reduce the number of mappings
	// the operating system needs to track; also amortizes
	// the overhead of an operating system mapping.
	// Allocate a multiple of 64kB.
    //_HeapAllocChunk的大小是1M`
    //_PageSize 是8K
	npage = round(npage, (64<<10)/_PageSize)
	ask := npage << _PageShift
	if ask < _HeapAllocChunk {
		ask = _HeapAllocChunk
	}
	
    //调用sysAlloc 从heap预留的内存分配ask
	v := h.sysAlloc(ask)
	if v == nil {
		if ask > npage<<_PageShift {
			ask = npage << _PageShift
			v = h.sysAlloc(ask)
		}
		if v == nil {
			print("runtime: out of memory: cannot allocate ", ask, "-byte block (", memstats.heap_sys, " in use)\n")
			return false
		}
	}

	// Create a fake "in use" span and free it, so that the
	// right coalescing happens.
	s := (*mspan)(h.spanalloc.alloc())
	s.init(uintptr(v), ask>>_PageShift)
	p := (s.base() - h.arena_start) >> _PageShift
	for i := p; i < p+s.npages; i++ {
		h.spans[i] = s
	}
	atomic.Store(&s.sweepgen, h.sweepgen)
	s.state = _MSpanInUse
	h.pagesInUse += uint64(s.npages)
	h.freeSpanLocked(s, false, true, 0)
	return true
}
~~~



##### mheap.freeSpanLocked

创建新的span时，会调用freeSanLocked

* 设置span的一些状态
* 尝试合并内存地址连续的span
* 将span放入空闲队列

~~~go
// s must be on a busy list (h.busy or h.busylarge) or unlinked.
func (h *mheap) freeSpanLocked(s *mspan, acctinuse, acctidle bool, unusedsince int64) {
	switch s.state {
	case _MSpanStack:
		if s.allocCount != 0 {
			throw("MHeap_FreeSpanLocked - invalid stack free")
		}
	case _MSpanInUse:
		if s.allocCount != 0 || s.sweepgen != h.sweepgen {
			print("MHeap_FreeSpanLocked - span ", s, " ptr ", hex(s.base()), " allocCount ", s.allocCount, " sweepgen ", s.sweepgen, "/", h.sweepgen, "\n")
			throw("MHeap_FreeSpanLocked - invalid free")
		}
		h.pagesInUse -= uint64(s.npages)
	default:
		throw("MHeap_FreeSpanLocked - invalid span state")
	}

	if acctinuse {
		memstats.heap_inuse -= uint64(s.npages << _PageShift)
	}
	if acctidle {
		memstats.heap_idle += uint64(s.npages << _PageShift)
	}
	s.state = _MSpanFree
	if s.inList() {
		h.busyList(s.npages).remove(s)
	}

	// Stamp newly unused spans. The scavenger will use that
	// info to potentially give back some pages to the OS.
	s.unusedsince = unusedsince
	if unusedsince == 0 {
		s.unusedsince = nanotime()
	}
	s.npreleased = 0

	// Coalesce with earlier, later spans.
	p := (s.base() - h.arena_start) >> _PageShift
	if p > 0 {
        //向前合并
		t := h.spans[p-1]
		if t != nil && t.state == _MSpanFree {
			s.startAddr = t.startAddr
			s.npages += t.npages
			s.npreleased = t.npreleased // absorb released pages
			s.needzero |= t.needzero
			p -= t.npages
			h.spans[p] = s
			h.freeList(t.npages).remove(t)
			t.state = _MSpanDead
			h.spanalloc.free(unsafe.Pointer(t))
		}
	}
    //向后合并
	if (p + s.npages) < uintptr(len(h.spans)) {
		t := h.spans[p+s.npages]
		if t != nil && t.state == _MSpanFree {
			s.npages += t.npages
			s.npreleased += t.npreleased
			s.needzero |= t.needzero
			h.spans[p+s.npages-1] = s
			h.freeList(t.npages).remove(t)
			t.state = _MSpanDead
			h.spanalloc.free(unsafe.Pointer(t))
		}
	}

	// Insert s into appropriate list.
	h.freeList(s.npages).insert(s)
}
~~~





##### 5) mheap.sysAlloc

* 从初始化时预留的内存块分配内存
* 预留的内存剩余的空闲内存足够
* 剩余的空闲内存不足

~~~go
// sysAlloc allocates the next n bytes from the heap arena. The
// returned pointer is always _PageSize aligned and between
// h.arena_start and h.arena_end. sysAlloc returns nil on failure.
// There is no corresponding free function.
func (h *mheap) sysAlloc(n uintptr) unsafe.Pointer {
	if n > h.arena_end-h.arena_used {
		// We are in 32-bit mode, maybe we didn't use all possible address space yet.
		// Reserve some more space.
		p_size := round(n+_PageSize, 256<<20)
		new_end := h.arena_end + p_size // Careful: can overflow
		if h.arena_end <= new_end && new_end-h.arena_start-1 <= _MaxArena32 {
			// TODO: It would be bad if part of the arena
			// is reserved and part is not.
			var reserved bool
			p := uintptr(sysReserve(unsafe.Pointer(h.arena_end), p_size, &reserved))
			if p == 0 {
				return nil
			}
			// p can be just about anywhere in the address
			// space, including before arena_end.
			if p == h.arena_end {
				h.arena_end = new_end
				h.arena_reserved = reserved
			} else if h.arena_end < p && p+p_size-h.arena_start-1 <= _MaxArena32 {
				// Keep everything page-aligned.
				// Our pages are bigger than hardware pages.
				h.arena_end = p + p_size
				used := p + (-p & (_PageSize - 1))
				h.mapBits(used)
				h.mapSpans(used)
				h.arena_used = used
				h.arena_reserved = reserved
			} else {
				// We got a mapping, but it's not
				// linear with our current arena, so
				// we can't use it.
				//
				// TODO: Make it possible to allocate
				// from this. We can't decrease
				// arena_used, but we could introduce
				// a new variable for the current
				// allocation position.

				// We haven't added this allocation to
				// the stats, so subtract it from a
				// fake stat (but avoid underflow).
				stat := uint64(p_size)
				sysFree(unsafe.Pointer(p), p_size, &stat)
			}
		}
	}//n > h.arena_end -h.arena_used

    //预留内存足够
	if n <= h.arena_end-h.arena_used {
		// Keep taking from our reservation.
		p := h.arena_used
		sysMap(unsafe.Pointer(p), n, h.arena_reserved, &memstats.heap_sys)
		h.mapBits(p + n)
		h.mapSpans(p + n)
		h.arena_used = p + n
		if raceenabled {
			racemapshadow(unsafe.Pointer(p), n)
		}

		if p&(_PageSize-1) != 0 {
			throw("misrounded allocation in MHeap_SysAlloc")
		}
		return unsafe.Pointer(p)
	}

	// If using 64-bit, our reservation is all we have.
	if h.arena_end-h.arena_start > _MaxArena32 {
		return nil
	}

	// On 32-bit, once the reservation is gone we can
	// try to get memory at a location chosen by the OS.
	p_size := round(n, _PageSize) + _PageSize
	p := uintptr(sysAlloc(p_size, &memstats.heap_sys))
	if p == 0 {
		return nil
	}

	if p < h.arena_start || p+p_size-h.arena_start > _MaxArena32 {
		top := ^uintptr(0)
		if top-h.arena_start-1 > _MaxArena32 {
			top = h.arena_start + _MaxArena32 + 1
		}
		print("runtime: memory allocated by OS (", hex(p), ") not in usable range [", hex(h.arena_start), ",", hex(top), ")\n")
		sysFree(unsafe.Pointer(p), p_size, &memstats.heap_sys)
		return nil
	}

	p_end := p + p_size
	p += -p & (_PageSize - 1)
	if p+n > h.arena_used {
		h.mapBits(p + n)
		h.mapSpans(p + n)
		h.arena_used = p + n
		if p_end > h.arena_end {
			h.arena_end = p_end
		}
		if raceenabled {
			racemapshadow(unsafe.Pointer(p), n)
		}
	}

	if p&(_PageSize-1) != 0 {
		throw("misrounded allocation in MHeap_SysAlloc")
	}
	return unsafe.Pointer(p)
}
~~~







##### mheap.mapBits

* 需要为位图保留多大空间来管理已经分配的内存
* 如果是32位系统, mheap_.bitmap 被初始化为管理4GB空间的位图的末端

~~~go
// mHeap_MapBits is called each time arena_used is extended.
// It maps any additional bitmap memory needed for the new arena memory.
// It must be called with the expected new value of arena_used,
// *before* h.arena_used has been updated.
// Waiting to update arena_used until after the memory has been mapped
// avoids faults when other threads try access the bitmap immediately
// after observing the change to arena_used.
//
//go:nowritebarrier
func (h *mheap) mapBits(arena_used uintptr) {
	// Caller has added extra mappings to the arena.
	// Add extra mappings of bitmap words as needed.
	// We allocate extra bitmap pieces in chunks of bitmapChunk.
	const bitmapChunk = 8192
    //heapBitmapScal 定义为 sys.Ptrsize *(8/2)
	n := (arena_used - mheap_.arena_start) / heapBitmapScale
	n = round(n, bitmapChunk)
	n = round(n, physPageSize)
	if h.bitmap_mapped >= n {
		return
	}

	sysMap(unsafe.Pointer(h.bitmap-n), n-h.bitmap_mapped, h.arena_reserved, &memstats.gc_sys)
	h.bitmap_mapped = n
}
~~~



##### mheap.mapSpans

~~~go
// mHeap_MapSpans makes sure that the spans are mapped
// up to the new value of arena_used.
//
// It must be called with the expected new value of arena_used,
// *before* h.arena_used has been updated.
// Waiting to update arena_used until after the memory has been mapped
// avoids faults when other threads try access the bitmap immediately
// after observing the change to arena_used.
func (h *mheap) mapSpans(arena_used uintptr) {
	// Map spans array, PageSize at a time.
	n := arena_used
    //sys.PtrSize 是4，则h.arena_start 为0
    //sys.PtrSize 是8,则
	n -= h.arena_start
	n = n / _PageSize * sys.PtrSize
	n = round(n, physPageSize)
	need := n / unsafe.Sizeof(h.spans[0])
	have := uintptr(len(h.spans))
	if have >= need {
		return
	}
	h.spans = h.spans[:need]
	sysMap(unsafe.Pointer(&h.spans[have]), (need-have)*unsafe.Sizeof(h.spans[0]), h.arena_reserved, &memstats.other_sys)
}
~~~



### mheap 维护的管理mspan的空闲队列

##### mheap.freeList

获取span归属的mSpanList, 若span管理的页面数目不超过_MaxMHeapList(128),则在h.free中查找。否则归属h.freelage

~~~go
func (h *mheap) freeList(npages uintptr) *mSpanList {
	if npages < uintptr(len(h.free)) {
		return &h.free[npages]
	}
	return &h.freelarge
}

~~~



##### mheap.busyList

~~~go
func (h *mheap) busyList(npages uintptr) *mSpanList {
	if npages < uintptr(len(h.free)) {
		return &h.busy[npages]
	}
	return &h.busylarge
}
~~~



### 内存释放

##### mheap.reclaim

~~~go
// Sweeps and reclaims at least npage pages into heap.
// Called before allocating npage pages.
func (h *mheap) reclaim(npage uintptr) {
	// First try to sweep busy spans with large objects of size >= npage,
	// this has good chances of reclaiming the necessary space.
	for i := int(npage); i < len(h.busy); i++ {
		if h.reclaimList(&h.busy[i], npage) != 0 {
			return // Bingo!
		}
	}

	// Then -- even larger objects.
	if h.reclaimList(&h.busylarge, npage) != 0 {
		return // Bingo!
	}

	// Now try smaller objects.
	// One such object is not enough, so we need to reclaim several of them.
	reclaimed := uintptr(0)
	for i := 0; i < int(npage) && i < len(h.busy); i++ {
		reclaimed += h.reclaimList(&h.busy[i], npage-reclaimed)
		if reclaimed >= npage {
			return
		}
	}

	// Now sweep everything that is not yet swept.
	unlock(&h.lock)
	for {
		n := sweepone()
		if n == ^uintptr(0) { // all spans are swept
			break
		}
		reclaimed += n
		if reclaimed >= npage {
			break
		}
	}
	lock(&h.lock)
}
~~~



##### mheap.reclaimList

~~~go
// Sweeps spans in list until reclaims at least npages into heap.
// Returns the actual number of pages reclaimed.
func (h *mheap) reclaimList(list *mSpanList, npages uintptr) uintptr {
	n := uintptr(0)
	sg := mheap_.sweepgen
retry:
	for s := list.first; s != nil; s = s.next {
		if s.sweepgen == sg-2 && atomic.Cas(&s.sweepgen, sg-2, sg-1) {
			list.remove(s)
			// swept spans are at the end of the list
			list.insertBack(s)
			unlock(&h.lock)
			snpages := s.npages
			if s.sweep(false) {
				n += snpages
			}
			lock(&h.lock)
			if n >= npages {
				return n
			}
			// the span could have been moved elsewhere
			goto retry
		}
		if s.sweepgen == sg-1 {
			// the span is being sweept by background sweeper, skip
			continue
		}
		// already swept empty span,
		// all subsequent ones must also be either swept or in process of sweeping
		break
	}
	return n
}
~~~



### gcSweepBuf

##### gcSweepBuf 和gcSeepBlock的关系



![1588257560415](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1588257560415.png)

##### gcSweepBuf的定义

~~~go
// A gcSweepBuf is a set of *mspans.
//
// gcSweepBuf is safe for concurrent push operations *or* concurrent
// pop operations, but not both simultaneously.
type gcSweepBuf struct {
	// A gcSweepBuf is a two-level data structure consisting of a
	// growable spine that points to fixed-sized blocks. The spine
	// can be accessed without locks, but adding a block or
	// growing it requires taking the spine lock.
	//
	// Because each mspan covers at least 8K of heap and takes at
	// most 8 bytes in the gcSweepBuf, the growth of the spine is
	// quite limited.
	//
	// The spine and all blocks are allocated off-heap, which
	// allows this to be used in the memory manager and avoids the
	// need for write barriers on all of these. We never release
	// this memory because there could be concurrent lock-free
	// access and we're likely to reuse it anyway. (In principle,
	// we could do this during STW.)

	spineLock mutex
	spine     unsafe.Pointer // *[N]*gcSweepBlock, accessed atomically
	spineLen  uintptr        // Spine array length, accessed atomically
	spineCap  uintptr        // Spine array cap, accessed under lock

	// index is the first unused slot in the logical concatenation
	// of all blocks. It is accessed atomically.
	index uint32
}

const (
	gcSweepBlockEntries    = 512 // 4KB on 64-bit
	gcSweepBufInitSpineCap = 256 // Enough for 1GB heap on 64-bit
)

//管理512个mspan
type gcSweepBlock struct {
	spans [gcSweepBlockEntries]*mspan

}
~~~



##### gcSweepBuf.push

~~~go
// push adds span s to buffer b. push is safe to call concurrently
// with other push operations, but NOT to call concurrently with pop.
func (b *gcSweepBuf) push(s *mspan) {
	// Obtain our slot.
	cursor := uintptr(atomic.Xadd(&b.index, +1) - 1)
    //gcSweepBlockEntries 值为512, top 是确定mspan应该放在哪个gcSweepBlock,
    //bottom则是在gcSweepBlock.spans数组中的索引位置
	top, bottom := cursor/gcSweepBlockEntries, cursor%gcSweepBlockEntries

	// Do we need to add a block?
	spineLen := atomic.Loaduintptr(&b.spineLen)
	var block *gcSweepBlock
retry:
	if top < spineLen {
		spine := atomic.Loadp(unsafe.Pointer(&b.spine))
		blockp := add(spine, sys.PtrSize*top)
		block = (*gcSweepBlock)(atomic.Loadp(blockp))
	} else {
		// Add a new block to the spine, potentially growing
		// the spine.
		lock(&b.spineLock)
		// spineLen cannot change until we release the lock,
		// but may have changed while we were waiting.
		spineLen = atomic.Loaduintptr(&b.spineLen)
		if top < spineLen {
			unlock(&b.spineLock)
			goto retry
		}

		if spineLen == b.spineCap {
			// Grow the spine.
			newCap := b.spineCap * 2
			if newCap == 0 {
				newCap = gcSweepBufInitSpineCap //256
			}
			newSpine := persistentalloc(newCap*sys.PtrSize, sys.CacheLineSize, &memstats.gc_sys)
			if b.spineCap != 0 {
				// Blocks are allocated off-heap, so
				// no write barriers.
				memmove(newSpine, b.spine, b.spineCap*sys.PtrSize)
			}
			// Spine is allocated off-heap, so no write barrier.
			atomic.StorepNoWB(unsafe.Pointer(&b.spine), newSpine)
			b.spineCap = newCap
			// We can't immediately free the old spine
			// since a concurrent push with a lower index
			// could still be reading from it. We let it
			// leak because even a 1TB heap would waste
			// less than 2MB of memory on old spines. If
			// this is a problem, we could free old spines
			// during STW.
		}

		// Allocate a new block and add it to the spine.
		block = (*gcSweepBlock)(persistentalloc(unsafe.Sizeof(gcSweepBlock{}), sys.CacheLineSize, &memstats.gc_sys))
		blockp := add(b.spine, sys.PtrSize*top)
		// Blocks are allocated off-heap, so no write barrier.
		atomic.StorepNoWB(blockp, unsafe.Pointer(block))
		atomic.Storeuintptr(&b.spineLen, spineLen+1)
		unlock(&b.spineLock)
	}

	// We have a block. Insert the span.
	block.spans[bottom] = s
}

~~~

