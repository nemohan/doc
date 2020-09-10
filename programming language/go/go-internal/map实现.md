# map 的实现

[TOC]



代码中的注解：

~~~go
// This file contains the implementation of Go's map type.
//
// A map is just a hash table. The data is arranged
// into an array of buckets. Each bucket contains up to
// 8 key/value pairs. The low-order bits of the hash are
// used to select a bucket. Each bucket contains a few
// high-order bits of each hash to distinguish the entries
// within a single bucket.
//
// If more than 8 keys hash to a bucket, we chain on
// extra buckets.
//
// When the hashtable grows, we allocate a new array
// of buckets twice as big. Buckets are incrementally
// copied from the old bucket array to the new bucket array.
//
// Map iterators walk through the array of buckets and
// return the keys in walk order (bucket #, then overflow
// chain order, then bucket index).  To maintain iteration
// semantics, we never move keys within their bucket (if
// we did, keys might be returned 0 or 2 times).  When
// growing the table, iterators remain iterating through the
// old table and must check the new table if the bucket
// they are iterating through has been moved ("evacuated")
// to the new table.

// Picking loadFactor: too large and we have lots of overflow
// buckets, too small and we waste a lot of space. I wrote
// a simple program to check some stats for different loads:
// (64-bit, 8 byte keys and values)
//  loadFactor    %overflow  bytes/entry     hitprobe    missprobe
//        4.00         2.13        20.77         3.00         4.00
//        4.50         4.05        17.30         3.25         4.50
//        5.00         6.85        14.77         3.50         5.00
//        5.50        10.55        12.94         3.75         5.50
//        6.00        15.27        11.67         4.00         6.00
//        6.50        20.90        10.79         4.25         6.50
//        7.00        27.14        10.15         4.50         7.00
//        7.50        34.03         9.73         4.75         7.50
//        8.00        41.10         9.40         5.00         8.00
//
// %overflow   = percentage of buckets which have an overflow bucket
// bytes/entry = overhead bytes used per key/value pair
// hitprobe    = # of entries to check when looking up a present key
// missprobe   = # of entries to check when looking up an absent key
//
// Keep in mind this data is for maximally loaded tables, i.e. just
// before the table grows. Typical tables will be somewhat less loaded.
~~~

一些常量定义:

~~~go
	// Possible tophash values. We reserve a few possibilities for special marks.
	// Each bucket (including its overflow buckets, if any) will have either all or none of its
	// entries in the evacuated* states (except during the evacuate() method, which only happens
	// during map writes and thus no one else can observe the map during that time).
	empty          = 0 // cell is empty
	evacuatedEmpty = 1 // cell is empty, bucket is evacuated.
	evacuatedX     = 2 // key/value is valid.  Entry has been evacuated to first half of larger table.
	evacuatedY     = 3 // same as above, but evacuated to second half of larger table.
	minTopHash     = 4 // minimum tophash for a normal filled cell.
~~~



#### 基本操作

map的大致结构

![image-20200910163112807](${img}/image-20200910163112807.png)

有意思的两点:

* bucket的存储方式
* rehash。rehash是通过增量rehash完成的， 插入时根据当前bucket是否完成迁移确定在新哈希表还是旧哈希表中查找`key`。添加时则总在新哈希表中添加。插入过程会不断的推进bucket的迁移



##### 创建map

~~~go
// makemap implements a Go map creation make(map[k]v, hint)
// If the compiler has determined that the map or the first bucket
// can be created on the stack, h and/or bucket may be non-nil.
// If h != nil, the map can be created directly in h.
// If bucket != nil, bucket can be used as the first bucket.
func makemap(t *maptype, hint int64, h *hmap, bucket unsafe.Pointer) *hmap {
	if sz := unsafe.Sizeof(hmap{}); sz > 48 || sz != t.hmap.size {
		println("runtime: sizeof(hmap) =", sz, ", t.hmap.size =", t.hmap.size)
		throw("bad hmap size")
	}

	if hint < 0 || int64(int32(hint)) != hint {
		panic(plainError("makemap: size out of range"))
		// TODO: make hint an int, then none of this nonsense
	}

	if !ismapkey(t.key) {
		throw("runtime.makemap: unsupported map key type")
	}

	// check compiler's and reflect's math
	if t.key.size > maxKeySize && (!t.indirectkey || t.keysize != uint8(sys.PtrSize)) ||
		t.key.size <= maxKeySize && (t.indirectkey || t.keysize != uint8(t.key.size)) {
		throw("key size wrong")
	}
	if t.elem.size > maxValueSize && (!t.indirectvalue || t.valuesize != uint8(sys.PtrSize)) ||
		t.elem.size <= maxValueSize && (t.indirectvalue || t.valuesize != uint8(t.elem.size)) {
		throw("value size wrong")
	}

	// invariants we depend on. We should probably check these at compile time
	// somewhere, but for now we'll do it here.
	if t.key.align > bucketCnt {
		throw("key align too big")
	}
	if t.elem.align > bucketCnt {
		throw("value align too big")
	}
	if t.key.size%uintptr(t.key.align) != 0 {
		throw("key size not a multiple of key align")
	}
	if t.elem.size%uintptr(t.elem.align) != 0 {
		throw("value size not a multiple of value align")
	}
	if bucketCnt < 8 {
		throw("bucketsize too small for proper alignment")
	}
	if dataOffset%uintptr(t.key.align) != 0 {
		throw("need padding in bucket (key)")
	}
	if dataOffset%uintptr(t.elem.align) != 0 {
		throw("need padding in bucket (value)")
	}

	// find size parameter which will hold the requested # of elements
	B := uint8(0)
	for ; overLoadFactor(hint, B); B++ {
	}

	// allocate initial hash table
	// if B == 0, the buckets field is allocated lazily later (in mapassign)
	// If hint is large zeroing this memory could take a while.
	buckets := bucket
	if B != 0 {
		buckets = newarray(t.bucket, 1<<B)
	}

	// initialize Hmap
	if h == nil {
		h = (*hmap)(newobject(t.hmap))
	}
	h.count = 0
	h.B = B
	h.flags = 0
	h.hash0 = fastrand()
	h.buckets = buckets
	h.oldbuckets = nil
	h.nevacuate = 0
	h.noverflow = 0

	return h
}
~~~



##### mapassign 插入元素

mapassign 会返回待插入value的内存位置

bucket 的结构： hash(key)| hash(key2) | key| key2 | value| value2

* 设置hashWriting标志位
* 2 检查是否正在重新哈希
* 3 查找空闲槽位。找到后仍然需要遍历所有的bmap，以确当是否有重复的key
* 4 若当前未正在调整哈希表， 且根据当前的loadFactor确定是否需要调整哈希表的大小
* 若需要进行rehash,则跳到步骤2

~~~go
// Like mapaccess, but allocates a slot for the key if it is not present in the map.
func mapassign(t *maptype, h *hmap, key unsafe.Pointer) unsafe.Pointer {
	if h == nil {
		panic(plainError("assignment to entry in nil map"))
	}
	if raceenabled {
		callerpc := getcallerpc(unsafe.Pointer(&t))
		pc := funcPC(mapassign)
		racewritepc(unsafe.Pointer(h), callerpc, pc)
		raceReadObjectPC(t.key, key, callerpc, pc)
	}
	if msanenabled {
		msanread(key, t.key.size)
	}
	if h.flags&hashWriting != 0 {
		throw("concurrent map writes")
	}
	h.flags |= hashWriting

	alg := t.key.alg
	hash := alg.hash(key, uintptr(h.hash0))

	if h.buckets == nil {
		h.buckets = newarray(t.bucket, 1)
	}

again:
	bucket := hash & (uintptr(1)<<h.B - 1)
    //这分两种情况
    //正在rehash, 迁移bucket
	if h.growing() {
		growWork(t, h, bucket)
	}
	b := (*bmap)(unsafe.Pointer(uintptr(h.buckets) + bucket*uintptr(t.bucketsize)))
	top := uint8(hash >> (sys.PtrSize*8 - 8))
    //minTopHash的值是常量4
	if top < minTopHash {
		top += minTopHash
	}

	var inserti *uint8
	var insertk unsafe.Pointer
	var val unsafe.Pointer
	for {
        //bucketCnt的值是常量8
		for i := uintptr(0); i < bucketCnt; i++ {
			if b.tophash[i] != top {
                //找到空闲位置, 若找到了为啥还continue
				if b.tophash[i] == empty && inserti == nil {
					inserti = &b.tophash[i]
					insertk = add(unsafe.Pointer(b), dataOffset+i*uintptr(t.keysize))
                    //待插入value的内存位置
					val = add(unsafe.Pointer(b), dataOffset+bucketCnt*uintptr(t.keysize)+i*uintptr(t.valuesize))
				}
				continue
			}
            //k 应该是key
			k := add(unsafe.Pointer(b), dataOffset+i*uintptr(t.keysize))
			if t.indirectkey {
				k = *((*unsafe.Pointer)(k))
			}
            //键是否相等, 不相等。哈希值相同但key不同
            //若找到了一个空闲插槽，岂不是key 和k也不相同, inserti 也不为nil
            //要继续遍历其他的bmap, 之所以这样。是因为有可能有相同的key在其他bmap中
			if !alg.equal(key, k) {
				continue
			}
			// already have a mapping for key. Update it.
			if t.needkeyupdate {
				typedmemmove(t.key, k, key)
			}
			val = add(unsafe.Pointer(b), dataOffset+bucketCnt*uintptr(t.keysize)+i*uintptr(t.valuesize))
			goto done
		}
		ovf := b.overflow(t)
		if ovf == nil {
			break
		}
		b = ovf
	}

	// Did not find mapping for key. Allocate new cell & add entry.

	// If we hit the max load factor or we have too many overflow buckets,
	// and we're not already in the middle of growing, start growing.
    //没有在调整哈希表大小， 且满足以下两个条件之一
    //1 
    //overflow bucket没超过一定数量
	if !h.growing() && (overLoadFactor(int64(h.count), h.B) || tooManyOverflowBuckets(h.noverflow, h.B)) {
		hashGrow(t, h)
		goto again // Growing the table invalidates everything, so try again
	}

	if inserti == nil {
		// all current buckets are full, allocate a new one.
		newb := (*bmap)(newobject(t.bucket))
		h.setoverflow(t, b, newb)
		inserti = &newb.tophash[0]
		insertk = add(unsafe.Pointer(newb), dataOffset)
		val = add(insertk, bucketCnt*uintptr(t.keysize))
	}

	// store new key/value at insert position
	if t.indirectkey {
		kmem := newobject(t.key)
		*(*unsafe.Pointer)(insertk) = kmem
		insertk = kmem
	}
	if t.indirectvalue {
		vmem := newobject(t.elem)
		*(*unsafe.Pointer)(val) = vmem
	}
	typedmemmove(t.key, insertk, key)
	*inserti = top
	h.count++

done:
	if h.flags&hashWriting == 0 {
		throw("concurrent map writes")
	}
	h.flags &^= hashWriting
	if t.indirectvalue {
		val = *((*unsafe.Pointer)(val))
	}
	return val
}
~~~



##### mapaccess1 查找

* 首先计算key的哈希值，然后根据哈希值确定bucket
* 根据当前是否正在rehash, 以及确定的bucket迁移是否完成确定在新哈希表还是旧哈希表中查找

~~~go
// mapaccess1 returns a pointer to h[key].  Never returns nil, instead
// it will return a reference to the zero object for the value type if
// the key is not in the map.
// NOTE: The returned pointer may keep the whole map live, so don't
// hold onto it for very long.
func mapaccess1(t *maptype, h *hmap, key unsafe.Pointer) unsafe.Pointer {
	if raceenabled && h != nil {
		callerpc := getcallerpc(unsafe.Pointer(&t))
		pc := funcPC(mapaccess1)
		racereadpc(unsafe.Pointer(h), callerpc, pc)
		raceReadObjectPC(t.key, key, callerpc, pc)
	}
	if msanenabled && h != nil {
		msanread(key, t.key.size)
	}
	if h == nil || h.count == 0 {
		return unsafe.Pointer(&zeroVal[0])
	}
	if h.flags&hashWriting != 0 {
		throw("concurrent map read and map write")
	}
	alg := t.key.alg
	hash := alg.hash(key, uintptr(h.hash0))
	m := uintptr(1)<<h.B - 1
	b := (*bmap)(add(h.buckets, (hash&m)*uintptr(t.bucketsize)))
    
    //正在进行rehash
	if c := h.oldbuckets; c != nil {
		if !h.sameSizeGrow() {
			// There used to be half as many buckets; mask down one more power of two.
			m >>= 1
		}
		oldb := (*bmap)(add(c, (hash&m)*uintptr(t.bucketsize)))
        
        //检查当前旧哈希表bucket是否迁移完成, 若完成则从新哈希表中的bucket中查找， 否则总旧哈希表中查找
         //若b.tophash[0] > empty && b.tophash[0] < minTopHash, 则evacuated返回true
    //反之就是empty, minTopHash, 正常的key就会执行if 逻辑
        //迁移完成会将b.tophash[0]设置成 evacuatedX, evacuated(oldb)就会返回true.从而不执行if
        
        
		if !evacuated(oldb) {
			b = oldb
		}
	}
	top := uint8(hash >> (sys.PtrSize*8 - 8))
    //加4 因为前0， 1， 2， 3都作为状态值使用了
	if top < minTopHash {
		top += minTopHash
	}
	for {
		for i := uintptr(0); i < bucketCnt; i++ {
			if b.tophash[i] != top {
				continue
			}
			k := add(unsafe.Pointer(b), dataOffset+i*uintptr(t.keysize))
			if t.indirectkey {
				k = *((*unsafe.Pointer)(k))
			}
            //键是否相等
			if alg.equal(key, k) {
				v := add(unsafe.Pointer(b), dataOffset+bucketCnt*uintptr(t.keysize)+i*uintptr(t.valuesize))
				if t.indirectvalue {
					v = *((*unsafe.Pointer)(v))
				}
				return v
			}
		}
		b = b.overflow(t)
		if b == nil {
			return unsafe.Pointer(&zeroVal[0])
		}
	}
}
~~~



#### 调整哈希表大小

#####  hashGrow 增大哈希表

~~~go
func hashGrow(t *maptype, h *hmap) {
	// If we've hit the load factor, get bigger.
	// Otherwise, there are too many overflow buckets,
	// so keep the same number of buckets and "grow" laterally.
	bigger := uint8(1)
	if !overLoadFactor(int64(h.count), h.B) {
		bigger = 0
		h.flags |= sameSizeGrow
	}
	oldbuckets := h.buckets
	newbuckets := newarray(t.bucket, 1<<(h.B+bigger))
	flags := h.flags &^ (iterator | oldIterator)
	if h.flags&iterator != 0 {
		flags |= oldIterator
	}
	// commit the grow (atomic wrt gc)
	h.B += bigger
	h.flags = flags
	h.oldbuckets = oldbuckets
	h.buckets = newbuckets
	h.nevacuate = 0
	h.noverflow = 0

	if h.overflow != nil {
		// Promote current overflow buckets to the old generation.
		if h.overflow[1] != nil {
			throw("overflow is not nil")
		}
		h.overflow[1] = h.overflow[0]
		h.overflow[0] = nil
	}

	// the actual copying of the hash table data is done incrementally
	// by growWork() and evacuate().
}
~~~



##### growwork迁移策略

* 插入过程会调用此函数，推进bucket的迁移

~~~go
func growWork(t *maptype, h *hmap, bucket uintptr) {
	// make sure we evacuate the oldbucket corresponding
	// to the bucket we're about to use
	evacuate(t, h, bucket&h.oldbucketmask())

	// evacuate one more oldbucket to make progress on growing
	if h.growing() {
		evacuate(t, h, h.nevacuate)
	}
}
~~~



##### evacuate 在新旧哈希表之间迁移键值对

迁移分两种情况处理：

* case 1: 哈希表大小不变，将旧哈希表的`键值对`拷贝到新哈希表
* case 2: 哈希表大小增加



疑问: **哈希表增大的情况下，应该是通过key 的哈希值确定新的bucket，evacuate怎么是用 `y = (*bmap)(add(h.buckets, (oldbucket+newbit)*uintptr(t.bucketsize)))`；oldbucket+newbit 确定新bucket**

~~~go
func evacuate(t *maptype, h *hmap, oldbucket uintptr) {
	b := (*bmap)(add(h.oldbuckets, oldbucket*uintptr(t.bucketsize)))
	newbit := h.noldbuckets()
	alg := t.key.alg
    
    //检查bucket是否已经迁移
    //若b.tophash[0] > empty && b.tophash[0] < minTopHash, 则evacuated返回true。表示这个bucket已经迁移完成
    //反之就是empty, minTopHash, 正常的key就会执行if 逻辑
	if !evacuated(b) {
		// TODO: reuse overflow buckets instead of using new ones, if there
		// is no iterator using the old buckets.  (If !oldIterator.)

		var (
			x, y   *bmap          // current low/high buckets in new map
			xi, yi int            // key/val indices into x and y
			xk, yk unsafe.Pointer // pointers to current x and y key storage
			xv, yv unsafe.Pointer // pointers to current x and y value storage
		)
        
        //新哈希表管理的所有bitmap
		x = (*bmap)(add(h.buckets, oldbucket*uintptr(t.bucketsize)))
		xi = 0
		xk = add(unsafe.Pointer(x), dataOffset)
		xv = add(xk, bucketCnt*uintptr(t.keysize))
        
        //哈希表增大
        //??????????????????????????, 确定新bucket的原因没搞明白
		if !h.sameSizeGrow() {
			// Only calculate y pointers if we're growing bigger.
			// Otherwise GC can see bad pointers.
            //为什么是oldbucket + newbit
			y = (*bmap)(add(h.buckets, (oldbucket+newbit)*uintptr(t.bucketsize)))
			yi = 0
			yk = add(unsafe.Pointer(y), dataOffset)
			yv = add(yk, bucketCnt*uintptr(t.keysize))
		}
        //针对b 是旧哈希表的bucket管理的所有bmap
		for ; b != nil; b = b.overflow(t) {
			k := add(unsafe.Pointer(b), dataOffset)
			v := add(k, bucketCnt*uintptr(t.keysize))
			for i := 0; i < bucketCnt; i, k, v = i+1, add(k, uintptr(t.keysize)), add(v, uintptr(t.valuesize)) {
				top := b.tophash[i]
				if top == empty {
					b.tophash[i] = evacuatedEmpty
					continue
				}
				if top < minTopHash {
					throw("bad map state")
				}
				k2 := k
				if t.indirectkey {
					k2 = *((*unsafe.Pointer)(k2))
				}
				useX := true
                //新表比旧表大
				if !h.sameSizeGrow() {
					// Compute hash to make our evacuation decision (whether we need
					// to send this key/value to bucket x or bucket y).
					hash := alg.hash(k2, uintptr(h.hash0))
                    
                    //map 正在被迭代
					if h.flags&iterator != 0 {
						if !t.reflexivekey && !alg.equal(k2, k2) {
							// If key != key (NaNs), then the hash could be (and probably
							// will be) entirely different from the old hash. Moreover,
							// it isn't reproducible. Reproducibility is required in the
							// presence of iterators, as our evacuation decision must
							// match whatever decision the iterator made.
							// Fortunately, we have the freedom to send these keys either
							// way. Also, tophash is meaningless for these kinds of keys.
							// We let the low bit of tophash drive the evacuation decision.
							// We recompute a new random tophash for the next level so
							// these keys will get evenly distributed across all buckets
							// after multiple grows.
							if top&1 != 0 {
								hash |= newbit
							} else {
								hash &^= newbit
							}
							top = uint8(hash >> (sys.PtrSize*8 - 8))
							if top < minTopHash {
								top += minTopHash
							}
						}
					}//end if h.flags & iterator != 0
                    
                    //那种情况hash & newbit 是0
                    //哪种情况hash & newbit 是1
					useX = hash&newbit == 0
                }//end if !h.sameSizeGrow()
                
                
                //从旧哈希表迁移到新哈希表
				if useX {
                    //将旧哈希表的bmap管理的tophash的值设为evacuatedX
					b.tophash[i] = evacuatedX
					if xi == bucketCnt {
						newx := (*bmap)(newobject(t.bucket))
						h.setoverflow(t, x, newx)
						x = newx
						xi = 0
						xk = add(unsafe.Pointer(x), dataOffset)
						xv = add(xk, bucketCnt*uintptr(t.keysize))
					}
					x.tophash[xi] = top
					if t.indirectkey {
						*(*unsafe.Pointer)(xk) = k2 // copy pointer
					} else {
						typedmemmove(t.key, xk, k) // copy value
					}
					if t.indirectvalue {
						*(*unsafe.Pointer)(xv) = *(*unsafe.Pointer)(v)
					} else {
						typedmemmove(t.elem, xv, v)
					}
					xi++
					xk = add(xk, uintptr(t.keysize))
					xv = add(xv, uintptr(t.valuesize))
				} else {
					b.tophash[i] = evacuatedY
					if yi == bucketCnt {
						newy := (*bmap)(newobject(t.bucket))
						h.setoverflow(t, y, newy)
						y = newy
						yi = 0
						yk = add(unsafe.Pointer(y), dataOffset)
						yv = add(yk, bucketCnt*uintptr(t.keysize))
					}
					y.tophash[yi] = top
					if t.indirectkey {
						*(*unsafe.Pointer)(yk) = k2
					} else {
						typedmemmove(t.key, yk, k)
					}
					if t.indirectvalue {
						*(*unsafe.Pointer)(yv) = *(*unsafe.Pointer)(v)
					} else {
						typedmemmove(t.elem, yv, v)
					}
					yi++
					yk = add(yk, uintptr(t.keysize))
					yv = add(yv, uintptr(t.valuesize))
				}//end else
			}
		}//end for
        
        
		// Unlink the overflow buckets & clear key/value to help GC.
		if h.flags&oldIterator == 0 {
			b = (*bmap)(add(h.oldbuckets, oldbucket*uintptr(t.bucketsize)))
			// Preserve b.tophash because the evacuation
			// state is maintained there.
			if t.bucket.kind&kindNoPointers == 0 {
				memclrHasPointers(add(unsafe.Pointer(b), dataOffset), uintptr(t.bucketsize)-dataOffset)
			} else {
				memclrNoHeapPointers(add(unsafe.Pointer(b), dataOffset), uintptr(t.bucketsize)-dataOffset)
			}
		}
	}

	// Advance evacuation mark
    //h.nevacuate 的初始值是0
    //清理完毕
    //growWork 函数会调用evacuate(t, h, h.nevacuate),逐个清理
	if oldbucket == h.nevacuate {
		h.nevacuate = oldbucket + 1
		if oldbucket+1 == newbit { // newbit == # of oldbuckets
			// Growing is all done. Free old main bucket array.
			h.oldbuckets = nil
			// Can discard old overflow buckets as well.
			// If they are still referenced by an iterator,
			// then the iterator holds a pointers to the slice.
			if h.overflow != nil {
				h.overflow[1] = nil
			}
			h.flags &^= sameSizeGrow
		}
	}
}
~~~



##### overLoadFactor 确定哈希表是否过载

若哈希表当前的元素数超过bucketCnt(8)并且 元素数是哈希表大小的loadFactor(6.5)倍。

~~~go
// overLoadFactor reports whether count items placed in 1<<B buckets is over loadFactor.
func overLoadFactor(count int64, B uint8) bool {
	// TODO: rewrite to use integer math and comparison?
	return count >= bucketCnt && float32(count) >= loadFactor*float32((uintptr(1)<<B))
}
~~~

