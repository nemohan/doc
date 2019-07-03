# map



### runtime/hashmap.go 文件前面的注释

~~~
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


// A bucket for a Go map.
type bmap struct {
	// tophash generally contains the top byte of the hash value
	// for each key in this bucket. If tophash[0] < minTopHash,
	// tophash[0] is a bucket evacuation state instead.
	tophash [bucketCnt]uint8
	// Followed by bucketCnt keys and then bucketCnt values.
	// NOTE: packing all the keys together and then all the values together makes the
	// code a bit more complicated than alternating key/value/key/value/... but it allows
	// us to eliminate padding which would be needed for, e.g., map[int64]int8.
	// Followed by an overflow pointer.
}

go 的哈希表由bucket数组构成，每个bucket中的key的位置由key的哈希值的高位第一个字节确定。bucket中所有key连续放在一起。后面紧跟key对应的value
bucket 布局:
 tophash[8]uint8] [key1,key2,key3...] [value1, value2,value3...s]
~~~





### 总结

* 写空map会导致panic
* 并发的读写冲突检测是通过 hmap的flags中的标志位来确定的
* 

### 源码

~~~go
package main

import ()

func main() {
	m := make(map[string]int, 1)
	m1 := make(map[int]int, 4)
	m["nihao"] = 1
	m1[1] = 2

}
~~~





###  反汇编



~~~assembly
0808aae0 <main.main> (File Offset: 0x42ae0):
main.main():
/home/hanzhao/workspace/go_runtime/main_map.go:5
package main

import ()

func main() {
 808aae0:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
 808aae7:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx
 808aaed:	8d 84 24 64 ff ff ff 	lea    -0x9c(%esp),%eax
 808aaf4:	3b 41 08             	cmp    0x8(%ecx),%eax
 808aaf7:	0f 86 17 01 00 00    	jbe    808ac14 <main.main+0x134> (File Offset: 0x42c14)
 808aafd:	81 ec 1c 01 00 00    	sub    $0x11c,%esp
/home/hanzhao/workspace/go_runtime/main_map.go:6
	m := make(map[string]int, 1)
 808ab03:	8d bc 24 94 00 00 00 	lea    0x94(%esp),%edi
/home/hanzhao/workspace/go_runtime/main_map.go:7
	m1 := make(map[int]int, 4)
 808ab0a:	31 c0                	xor    %eax,%eax
/home/hanzhao/workspace/go_runtime/main_map.go:6
package main

import ()

func main() {
	m := make(map[string]int, 1)
 808ab0c:	e8 e8 d3 ff ff       	call   8087ef9 <runtime.duffzero+0x79> (File Offset: 0x3fef9)
 808ab11:	8d bc 24 b0 00 00 00 	lea    0xb0(%esp),%edi
 808ab18:	e8 c8 d3 ff ff       	call   8087ee5 <runtime.duffzero+0x65> (File Offset: 0x3fee5)
 808ab1d:	8d 0d 80 52 09 08    	lea    0x8095280,%ecx
 808ab23:	89 0c 24             	mov    %ecx,(%esp)
 //################## hmap
 
 808ab26:	c7 44 24 04 01 00 00 	movl   $0x1,0x4(%esp)
 808ab2d:	00 
//############## map 大小
 
 808ab2e:	c7 44 24 08 00 00 00 	movl   $0x0,0x8(%esp)
 808ab35:	00 
 
 808ab36:	8d 94 24 94 00 00 00 	lea    0x94(%esp),%edx
 808ab3d:	89 54 24 0c          	mov    %edx,0xc(%esp)
 
 808ab41:	8d 94 24 b0 00 00 00 	lea    0xb0(%esp),%edx
 808ab48:	89 54 24 10          	mov    %edx,0x10(%esp)
 808ab4c:	e8 cf 2d fc ff       	call   804d920 <runtime.makemap> (File Offset: 0x5920)
 
 808ab51:	8b 4c 24 14          	mov    0x14(%esp),%ecx
 808ab55:	89 4c 24 6c          	mov    %ecx,0x6c(%esp)
/home/hanzhao/workspace/go_runtime/main_map.go:7
	m1 := make(map[int]int, 4)
 808ab59:	8d 7c 24 78          	lea    0x78(%esp),%edi
 808ab5d:	31 c0                	xor    %eax,%eax
 808ab5f:	e8 95 d3 ff ff       	call   8087ef9 <runtime.duffzero+0x79> (File Offset: 0x3fef9)
 808ab64:	8d 7c 24 1c          	lea    0x1c(%esp),%edi
 808ab68:	e8 80 d3 ff ff       	call   8087eed <runtime.duffzero+0x6d> (File Offset: 0x3feed)
 808ab6d:	8d 0d 00 52 09 08    	lea    0x8095200,%ecx
 808ab73:	89 0c 24             	mov    %ecx,(%esp)
 808ab76:	c7 44 24 04 04 00 00 	movl   $0x4,0x4(%esp)
 808ab7d:	00 
 808ab7e:	c7 44 24 08 00 00 00 	movl   $0x0,0x8(%esp)
 808ab85:	00 
 808ab86:	8d 54 24 78          	lea    0x78(%esp),%edx
 808ab8a:	89 54 24 0c          	mov    %edx,0xc(%esp)
 808ab8e:	8d 54 24 1c          	lea    0x1c(%esp),%edx
 808ab92:	89 54 24 10          	mov    %edx,0x10(%esp)
 808ab96:	e8 85 2d fc ff       	call   804d920 <runtime.makemap> (File Offset: 0x5920)
 808ab9b:	8b 4c 24 14          	mov    0x14(%esp),%ecx
 808ab9f:	89 4c 24 68          	mov    %ecx,0x68(%esp)
/home/hanzhao/workspace/go_runtime/main_map.go:8
	m["nihao"] = 1
 808aba3:	8d 15 77 e8 09 08    	lea    0x809e877,%edx
 808aba9:	89 54 24 70          	mov    %edx,0x70(%esp)
 808abad:	c7 44 24 74 05 00 00 	movl   $0x5,0x74(%esp)
 808abb4:	00 
/home/hanzhao/workspace/go_runtime/main_map.go:6
package main

import ()

func main() {
	m := make(map[string]int, 1)
 808abb5:	8d 15 80 52 09 08    	lea    0x8095280,%edx
/home/hanzhao/workspace/go_runtime/main_map.go:8
	m1 := make(map[int]int, 4)
	m["nihao"] = 1
 808abbb:	89 14 24             	mov    %edx,(%esp)
 808abbe:	8b 54 24 6c          	mov    0x6c(%esp),%edx
 808abc2:	89 54 24 04          	mov    %edx,0x4(%esp)
 808abc6:	8d 54 24 70          	lea    0x70(%esp),%edx
 808abca:	89 54 24 08          	mov    %edx,0x8(%esp)
 808abce:	e8 4d 32 fc ff       	call   804de20 <runtime.mapassign> (File Offset: 0x5e20)
 808abd3:	8b 4c 24 0c          	mov    0xc(%esp),%ecx
 808abd7:	c7 01 01 00 00 00    	movl   $0x1,(%ecx)
/home/hanzhao/workspace/go_runtime/main_map.go:9
	m1[1] = 2
 808abdd:	c7 44 24 18 01 00 00 	movl   $0x1,0x18(%esp)
 808abe4:	00 
/home/hanzhao/workspace/go_runtime/main_map.go:7

import ()

func main() {
	m := make(map[string]int, 1)
	m1 := make(map[int]int, 4)
 808abe5:	8d 0d 00 52 09 08    	lea    0x8095200,%ecx
/home/hanzhao/workspace/go_runtime/main_map.go:9
	m["nihao"] = 1
	m1[1] = 2
 808abeb:	89 0c 24             	mov    %ecx,(%esp)
 808abee:	8b 4c 24 68          	mov    0x68(%esp),%ecx
 808abf2:	89 4c 24 04          	mov    %ecx,0x4(%esp)
 808abf6:	8d 4c 24 18          	lea    0x18(%esp),%ecx
 808abfa:	89 4c 24 08          	mov    %ecx,0x8(%esp)
 808abfe:	e8 1d 32 fc ff       	call   804de20 <runtime.mapassign> (File Offset: 0x5e20)
 808ac03:	8b 4c 24 0c          	mov    0xc(%esp),%ecx
 808ac07:	c7 01 02 00 00 00    	movl   $0x2,(%ecx)
/home/hanzhao/workspace/go_runtime/main_map.go:11

}
 808ac0d:	81 c4 1c 01 00 00    	add    $0x11c,%esp
 808ac13:	c3                   	ret    
/home/hanzhao/workspace/go_runtime/main_map.go:5
package main

import ()

func main() {
 808ac14:	e8 17 b7 ff ff       	call   8086330 <runtime.morestack_noctxt> (File Offset: 0x3e330)
 808ac19:	e9 c2 fe ff ff       	jmp    808aae0 <main.main> (File Offset: 0x42ae0)
 808ac1e:	cc                   	int3   
 808ac1f:	cc                   	int3   

0808ac20 <main.init> (File Offset: 0x42c20):
main.init():
 808ac20:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
 808ac27:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx
 808ac2d:	3b 61 08             	cmp    0x8(%ecx),%esp
 808ac30:	76 1e                	jbe    808ac50 <main.init+0x30> (File Offset: 0x42c50)
 808ac32:	0f b6 05 40 8d 0d 08 	movzbl 0x80d8d40,%eax
 808ac39:	80 f8 01             	cmp    $0x1,%al
 808ac3c:	76 01                	jbe    808ac3f <main.init+0x1f> (File Offset: 0x42c3f)
 808ac3e:	c3                   	ret    
 808ac3f:	75 07                	jne    808ac48 <main.init+0x28> (File Offset: 0x42c48)
 808ac41:	e8 ba b9 fd ff       	call   8066600 <runtime.throwinit> (File Offset: 0x1e600)
 808ac46:	0f 0b                	ud2    
 808ac48:	c6 05 40 8d 0d 08 02 	movb   $0x2,0x80d8d40
 808ac4f:	c3                   	ret    
 808ac50:	e8 db b6 ff ff       	call   8086330 <runtime.morestack_noctxt> (File Offset: 0x3e330)
 808ac55:	eb c9                	jmp    808ac20 <main.init> (File Offset: 0x42c20)
 
 
 size = 04 00 00 00
 ptrdata = 04 00 00 00
 hash =e5 db c8 4a
 tfag=02
 align = 04
 fieldalign = 04
 kind = 35
 
809527f:	00 
04 00             	add    %al,(%eax,%eax,1)
 8095282:	00 00                	add    %al,(%eax)
 8095284:	04 00                	add    $0x0,%al
 8095286:	00 00                	add    %al,(%eax)
 8095288:	e5 db                	in     $0xdb,%eax
 809528a:	c8 4a 02 04          	enter  $0x24a,$0x4
 809528e:	04 35                	add    $0x35,%al
 8095290:	20 8b 0c 08 5f 41    	and    %cl,0x415f080c(%ebx)
 8095296:	0a 08                	or     (%eax),%cl
 8095298:	ec                   	in     (%dx),%al
 8095299:	2e 00 00             	add    %al,%cs:(%eax)
 809529c:	00 00                	add    %al,(%eax)
 809529e:	00 00                	add    %al,(%eax)
 
 
 80952a0:	20 4b 09             	and    %cl,0x9(%ebx)
 80952a3:	08 20                	or     %ah,(%eax)
 80952a5:	47                   	inc    %edi
 80952a6:	09 08                	or     %ecx,(%eax)
 80952a8:	e0 83                	loopne 809522d <type.*+0xa22d> (File Offset: 0x4d22d)
 80952aa:	09 08                	or     %ecx,(%eax)
 80952ac:	e0 b1                	loopne 809525f <type.*+0xa25f> (File Offset: 0x4d25f)
 80952ae:	09 08                	or     %ecx,(%eax)
 80952b0:	08 00                	or     %al,(%eax)
 80952b2:	04 00                	add    $0x0,%al
 80952b4:	6c                   	insb   (%dx),%es:(%edi)
 80952b5:	00 01                	add    %al,(%ecx)
 80952b7:	01 00                	add    %eax,(%eax)
 80952b9:	00 00                	add    %al,(%eax)
 80952bb:	00 00                	add    %al,(%eax)
 80952bd:	00 00                	add    %al,(%eax)
 80952bf:	00 04 00             	add    %al,(%eax,%eax,1)
 80952c2:	00 00                	add    %al,(%eax)
 80952c4:	04 00                	add    $0x0,%al
 80952c6:	00 00                	add    %al,(%eax)
 80952c8:	a0 0a 27 7d 02       	mov    0x27d270a,%al
 80952cd:	04 04                	add    $0x4,%al
 80952cf:	35 20 8b 0c 08       	xor    $0x80c8b20,%eax
 80952d4:	5f                   	pop    %edi
 80952d5:	41                   	inc    %ecx
 80952d6:	0a 08                	or     (%eax),%cl
 80952d8:	4c                   	dec    %esp
 80952d9:	37                   	aaa    
 80952da:	00 00                	add    %al,(%eax)
 80952dc:	00 00                	add    %al,(%eax)
 80952de:	00 00                	add    %al,(%eax)
 80952e0:	20 4b 09             	and    %cl,0x9(%ebx)
 80952e3:	08 20                	or     %ah,(%eax)
 80952e5:	4c                   	dec    %esp
 80952e6:	09 08                	or     %ecx,(%eax)
 80952e8:	40                   	inc    %eax
 80952e9:	84 09                	test   %cl,(%ecx)
 80952eb:	08 80 b2 09 08 08    	or     %al,0x80809b2(%eax)
 80952f1:	00 08                	add    %cl,(%eax)
 80952f3:	00 8c 00 01 01 00 00 	add    %cl,0x101(%eax,%eax,1)
 80952fa:	00 00                	add    %al,(%eax)
 80952fc:	00 00                	add    %al,(%eax)
 80952fe:	00 00                	add    %al,(%eax)
 8095300:	04 00                	add    $0x0,%al
 8095302:	00 00                	add    %al,(%eax)
 8095304:	04 00                	add    $0x0,%al
 8095306:	00 00                	add    %al,(%eax)
 8095308:	f8                   	clc    
 8095309:	bd 21 f7 02 04       	mov    $0x402f721,%ebp
 809530e:	04 35                	add    $0x35,%al
 8095310:	20 8b 0c 08 5f 41    	and    %cl,0x415f080c(%ebx)
 8095316:	0a 08                	or     (%eax),%cl
 8095318:	ac                   	lods   %ds:(%esi),%al
 8095319:	42                   	inc    %edx
 809531a:	00 00                	add    %al,(%eax)

//==================================
8095200 *maptype
size = 04 00 00 00
ptrdata = 04 00 00 00
hash = 50 1b 58 23
tflag = 02
align =04
fieldalign= 04
kind=35
alg = 20 8b 0c 08  80c8b20
gcdata = 5f 41 0a 08
str = 92 27 00 00
ptrToThis = 00 00 00 00 

key =  20 47 09 08
elem=  20 47 09 08
bucket = 20 83 09 08 
hmap =  a0 b0 09 08
keysize = 04
indirectKey = 00
valuesize = 04
indirectvalue=00
bucketsize = 4c
80951ff:	00 04 00             	add    %al,(%eax,%eax,1)
 8095202:	00 00                	add    %al,(%eax)
 8095204:	04 00                	add    $0x0,%al
 8095206:	00 00                	add    %al,(%eax)
 8095208:	50                   	push   %eax
 8095209:	1b 58 23             	sbb    0x23(%eax),%ebx
 809520c:	02 04 04             	add    (%esp,%eax,1),%al
 809520f:	35 20 8b 0c 08       	xor    $0x80c8b20,%eax
 
 
 
 8095214:	5f                   	pop    %edi
 8095215:	41                   	inc    %ecx
 8095216:	0a 08                	or     (%eax),%cl
 8095218:	92                   	xchg   %eax,%edx
 8095219:	27                   	daa    
 809521a:	00 00                	add    %al,(%eax)
 809521c:	00 00                	add    %al,(%eax)
 809521e:	00 00                	add    %al,(%eax)
 
 
 
 8095220:	20 47 09             	and    %al,0x9(%edi)
 8095223:	08 20                	or     %ah,(%eax)
 8095225:	47    
 
 inc    %edi
 8095226:	09 08                	or     %ecx,(%eax)
 8095228:	20 83 09 08 a0 b0    	and    %al,-0x4f5ff7f7(%ebx)
 809522e:	09 08                	or     %ecx,(%eax)
 8095230:	04 00                	add    $0x0,%al
 8095232:	04 00                	add    $0x0,%al
 8095234:	4c                   	dec    %esp
 8095235:	00 01                	add    %al,(%ecx)
~~~





~~~go
const (
	// Maximum number of key/value pairs a bucket can hold.
	bucketCntBits = 3
	bucketCnt     = 1 << bucketCntBits

	// Maximum average load of a bucket that triggers growth.
	loadFactor = 6.5

	// Maximum key or value size to keep inline (instead of mallocing per element).
	// Must fit in a uint8.
	// Fast versions cannot handle big values - the cutoff size for
	// fast versions in ../../cmd/internal/gc/walk.go must be at most this value.
	maxKeySize   = 128
	maxValueSize = 128

	// data offset should be the size of the bmap struct, but needs to be
	// aligned correctly. For amd64p32 this means 64-bit alignment
	// even though pointers are 32 bit.
	dataOffset = unsafe.Offsetof(struct {
		b bmap
		v int64
	}{}.v)

	// Possible tophash values. We reserve a few possibilities for special marks.
	// Each bucket (including its overflow buckets, if any) will have either all or none of its
	// entries in the evacuated* states (except during the evacuate() method, which only happens
	// during map writes and thus no one else can observe the map during that time).
	empty          = 0 // cell is empty
	evacuatedEmpty = 1 // cell is empty, bucket is evacuated.
	evacuatedX     = 2 // key/value is valid.  Entry has been evacuated to first half of larger table.
	evacuatedY     = 3 // same as above, but evacuated to second half of larger table.
	minTopHash     = 4 // minimum tophash for a normal filled cell.

	// flags
	iterator     = 1 // there may be an iterator using buckets
	oldIterator  = 2 // there may be an iterator using oldbuckets
	hashWriting  = 4 // a goroutine is writing to the map
	sameSizeGrow = 8 // the current map growth is to a new map of the same size

	// sentinel bucket ID for iterator checks
	noCheck = 1<<(8*sys.PtrSize) - 1
)



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
    //指定的hint至少为8，B才大于0
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

// 如果map的大小超过 bucketCnt即8，并且 超过预期大小的loadFactor倍数

// overLoadFactor reports whether count items placed in 1<<B buckets is over loadFactor.
func overLoadFactor(count int64, B uint8) bool {
	// TODO: rewrite to use integer math and comparison?
	return count >= bucketCnt && float32(count) >= loadFactor*float32((uintptr(1)<<B))
}

func (h *hmap) setoverflow(t *maptype, b, ovf *bmap) {
	h.incrnoverflow()
	if t.bucket.kind&kindNoPointers != 0 {
		h.createOverflow()
		*h.overflow[0] = append(*h.overflow[0], ovf)
	}
	*(**bmap)(add(unsafe.Pointer(b), uintptr(t.bucketsize)-sys.PtrSize)) = ovf
}

func (h *hmap) createOverflow() {
	if h.overflow == nil {
		h.overflow = new([2]*[]*bmap)
	}
	if h.overflow[0] == nil {
		h.overflow[0] = new([]*bmap)
	}
}


//注释写的很清楚了

// incrnoverflow increments h.noverflow.
// noverflow counts the number of overflow buckets.
// This is used to trigger same-size map growth.
// See also tooManyOverflowBuckets.
// To keep hmap small, noverflow is a uint16.
// When there are few buckets, noverflow is an exact count.
// When there are many buckets, noverflow is an approximate count.
func (h *hmap) incrnoverflow() {
	// We trigger same-size map growth if there are
	// as many overflow buckets as buckets.
	// We need to be able to count to 1<<h.B.
	if h.B < 16 {
		h.noverflow++
		return
	}
	// Increment with probability 1/(1<<(h.B-15)).
	// When we reach 1<<15 - 1, we will have approximately
	// as many overflow buckets as buckets.
	mask := uint32(1)<<(h.B-15) - 1
	// Example: if h.B == 18, then mask == 7,
	// and fastrand & 7 == 0 with probability 1/8.
	if fastrand()&mask == 0 {
		h.noverflow++
	}
}

~~~





### 写



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
    
    //并发写的冲突检测
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
    //hash的低位 确定bucket
	bucket := hash & (uintptr(1)<<h.B - 1)
	if h.growing() {
		growWork(t, h, bucket)
	}
    
    // 所有的bucket，都是放在一块连续的内存中，
    // 创建buckets时候，并没有用t.bucketsize?????. 又如何确保内存足够呢
	b := (*bmap)(unsafe.Pointer(uintptr(h.buckets) + bucket*uintptr(t.bucketsize)))
	top := uint8(hash >> (sys.PtrSize*8 - 8))
	if top < minTopHash {
		top += minTopHash
	}

	var inserti *uint8
	var insertk unsafe.Pointer
	var val unsafe.Pointer
	for {
		for i := uintptr(0); i < bucketCnt; i++ {
			if b.tophash[i] != top {
                //######### 找到第一个为空的
				if b.tophash[i] == empty && inserti == nil {
					inserti = &b.tophash[i]
                    // key 的存放位置
					insertk = add(unsafe.Pointer(b), dataOffset+i*uintptr(t.keysize))
                    
                    // value的存放位置
					val = add(unsafe.Pointer(b),
                       dataOffset+bucketCnt*uintptr(t.keysize)+i*uintptr(t.valuesize))
				}
                //没有为空的
				continue
			}
            
            // 1 b.tophash[i] == top，相同的散列高位
            // 2 
            
			k := add(unsafe.Pointer(b), dataOffset+i*uintptr(t.keysize))
			if t.indirectkey {
				k = *((*unsafe.Pointer)(k))
			}
            
            //键值是否已经存在, top高位相同，key不同
			if !alg.equal(key, k) {
				continue
			}
			// already have a mapping for key. Update it.
			if t.needkeyupdate {
				typedmemmove(t.key, k, key)
			}
			val = add(unsafe.Pointer(b), dataOffset+bucketCnt*uintptr(t.keysize)+i*uintptr(t.valuesize))
			goto done
		}// end for

        // 是否有链接在一起的bucket，当bucket满时。用额外的bucket存放
		ovf := b.overflow(t)
		if ovf == nil {
			break
		}
		b = ovf
	}

	// Did not find mapping for key. Allocate new cell & add entry.

	// If we hit the max load factor or we have too many overflow buckets,
	// and we're not already in the middle of growing, start growing.
	if !h.growing() && (overLoadFactor(int64(h.count), h.B) || tooManyOverflowBuckets(h.noverflow, h.B)) {
		hashGrow(t, h)
		goto again // Growing the table invalidates everything, so try again
	}

    //当前bucket满，分配新的bucket
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

