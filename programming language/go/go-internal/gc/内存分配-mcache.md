# mcache 缓存

[TOC]



##### mcache的定义

* mcache.tiny 指向当前分配的小内存块， mcache.tinyoffset 在tiny指向的内存块中，下一个可用位置

~~~go
// Per-thread (in Go, per-P) cache for small objects.
// No locking needed because it is per-thread (per-P).
//
// mcaches are allocated from non-GC'd memory, so any heap pointers
// must be specially handled.
//
//go:notinheap
type mcache struct {
	// The following members are accessed on every malloc,
	// so they are grouped here for better caching.
	next_sample int32   // trigger heap sample after allocating this many bytes
	local_scan  uintptr // bytes of scannable heap allocated

	// Allocator cache for tiny objects w/o pointers.
	// See "Tiny allocator" comment in malloc.go.

	// tiny points to the beginning of the current tiny block, or
	// nil if there is no current tiny block.
	//
	// tiny is a heap pointer. Since mcache is in non-GC'd memory,
	// we handle it by clearing it in releaseAll during mark
	// termination.
	tiny             uintptr
	tinyoffset       uintptr
	local_tinyallocs uintptr // number of tiny allocs not counted in other stats

	// The rest is not accessed on every malloc.
	alloc [_NumSizeClasses]*mspan // spans to allocate from

	stackcache [_NumStackOrders]stackfreelist

	// Local allocator stats, flushed during GC.
	local_nlookup    uintptr                  // number of pointer lookups
	local_largefree  uintptr                  // bytes freed for large objects (>maxsmallsize)
	local_nlargefree uintptr                  // number of frees for large objects (>maxsmallsize)
	local_nsmallfree [_NumSizeClasses]uintptr // number of frees for small objects (<=maxsmallsize)
}
~~~



##### allocmcache 创建mcache

初始化内存分配模块时，会调用allocmcache为当前的g.m分配mcache

runtime/mcache.go

~~~go
// dummy MSpan that contains no free objects.
var emptymspan mspan //全局变量
func allocmcache() *mcache {
	lock(&mheap_.lock)
	c := (*mcache)(mheap_.cachealloc.alloc())
	unlock(&mheap_.lock)
	for i := 0; i < _NumSizeClasses; i++ {
		c.alloc[i] = &emptymspan
	}
	c.next_sample = nextSample()
	return c
}
~~~



##### nextFreeFast

runtime/malloc.go

<font color="red">mspan.allocCache的每一位对应一个对象大小的内存?? </font>,

位图跟内存位置的对应关系: 位图的第n位所对应的内存位置

* 根据mspan.allocCache管理的位图，确定是否有空闲内存。若有空闲内存则返回该空闲内存的地址



两个疑问：

~~~go
// nextFreeFast returns the next free object if one is quickly available.
// Otherwise it returns 0.
func nextFreeFast(s *mspan) gclinkptr {
    //theBit 是小于等于64的整数，等于64时表明没有空闲内存
	theBit := sys.Ctz64(s.allocCache) // Is there a free object in the allocCache?
	if theBit < 64 {
		result := s.freeindex + uintptr(theBit)
        //s.nelems 是span能容纳对象个数
		if result < s.nelems {
			freeidx := result + 1
            //为什么freeidx 满足下面条件时返回0
			if freeidx%64 == 0 && freeidx != s.nelems {
				return 0
			}
            //为什么allocCache 向右移动(theBit + 1)
			s.allocCache >>= (theBit + 1)
			s.freeindex = freeidx
			v := gclinkptr(result*s.elemsize + s.base())//强制转换
			s.allocCount++
			return v
		}
	}
	return 0
}
~~~



##### mcache.nextFree

* 检查从mspan分配的对象个数是否达到容量上限mspan.nelems,若达到上限调用c.refill 获取新的mspan,

  <font color="red">并设置shouldhelpgc = true</font>

* 已分配对象个数未达到上限,

~~~go
/ nextFree returns the next free object from the cached span if one is available.
// Otherwise it refills the cache with a span with an available object and
// returns that object along with a flag indicating that this was a heavy
// weight allocation. If it is a heavy weight allocation the caller must
// determine whether a new GC cycle needs to be started or if the GC is active
// whether this goroutine needs to assist the GC.
func (c *mcache) nextFree(sizeclass uint8) (v gclinkptr, s *mspan, shouldhelpgc bool) {
	s = c.alloc[sizeclass]
	shouldhelpgc = false
	freeIndex := s.nextFreeIndex()
    //一开始
    //freeIndex == s.nelems== 0
	if freeIndex == s.nelems {
		// The span is full.
		if uintptr(s.allocCount) != s.nelems {
			println("runtime: s.allocCount=", s.allocCount, "s.nelems=", s.nelems)
			throw("s.allocCount != s.nelems && freeIndex == s.nelems")
		}
		systemstack(func() {
			c.refill(int32(sizeclass))
		})
		shouldhelpgc = true
		s = c.alloc[sizeclass]

		freeIndex = s.nextFreeIndex()
	}

	if freeIndex >= s.nelems {
		throw("freeIndex is not valid")
	}

	v = gclinkptr(freeIndex*s.elemsize + s.base())
	s.allocCount++
	if uintptr(s.allocCount) > s.nelems {
		println("s.allocCount=", s.allocCount, "s.nelems=", s.nelems)
		throw("s.allocCount > s.nelems")
	}
	return
}
~~~



##### mcache.refill

* 调用mcental.cacheSpan获取mspan, 新获取的span会替换掉已经没有空闲空间的span

~~~go
// Gets a span that has a free object in it and assigns it
// to be the cached span for the given sizeclass. Returns this span.
func (c *mcache) refill(sizeclass int32) *mspan {
	_g_ := getg()

	_g_.m.locks++
	// Return the current cached span to the central lists.
	s := c.alloc[sizeclass]

	if uintptr(s.allocCount) != s.nelems {
		throw("refill of span with free space remaining")
	}

	if s != &emptymspan {
		s.incache = false
	}

	// Get a new cached span from the central lists.
	s = mheap_.central[sizeclass].mcentral.cacheSpan()
	if s == nil {
		throw("out of memory")
	}

	if uintptr(s.allocCount) == s.nelems {
		throw("span has no free space")
	}

	c.alloc[sizeclass] = s
	_g_.m.locks--
	return s
}
~~~



##### Ctz64 不明白

runtime/intrinsics.go

Ctz64 即确定64位中哪一位是1。有点类似下面的算法



见这篇http://supertech.csail.mit.edu/papers/debruijn.pdf

~~~go
const deBruijn64ctz = 0x0218a392cd3d5dbf

var deBruijnIdx64ctz = [64]byte{
	0, 1, 2, 7, 3, 13, 8, 19,
	4, 25, 14, 28, 9, 34, 20, 40,
	5, 17, 26, 38, 15, 46, 29, 48,
	10, 31, 35, 54, 21, 50, 41, 57,
	63, 6, 12, 18, 24, 27, 33, 39,
	16, 37, 45, 47, 30, 53, 49, 56,
	62, 11, 23, 32, 36, 44, 52, 55,
	61, 22, 43, 51, 60, 42, 59, 58,
}

const deBruijn32ctz = 0x04653adf

var deBruijnIdx32ctz = [32]byte{
	0, 1, 2, 6, 3, 11, 7, 16,
	4, 14, 12, 21, 8, 23, 17, 26,
	31, 5, 10, 15, 13, 20, 22, 25,
	30, 9, 19, 24, 29, 18, 28, 27,
}


// Ctz64 counts trailing (low-order) zeroes,
// and if all are zero, then 64. 
// n- lgn = 58  2的6次方=64
func Ctz64(x uint64) int {
    //只保留了第一个位为1的
	x &= -x                       // isolate low-order bit
    
    //计算哈希值
	y := x * deBruijn64ctz >> 58  // extract part of deBruijn sequence
    
    //哈希表的内容是，这个64位的的整数中哪一位为1
	i := int(deBruijnIdx64ctz[y]) // convert to bit index
    
    //为何先左移57位， 64 的位模式是: 0100 0000
    //x 只有在63位为1， z = 1
	z := int((x - 1) >> 57 & 64)  // adjustment if zero
	return i + z
}
~~~

