# bolt db

[TOC]



## 文件存储格式

### 非叶子节点存储格式

~~~go
type page struct {
	id       pgid //页面id
	flags    uint16 //
	count    uint16 //key 的个数
	overflow uint32
	ptr      uintptr //指向存储key的元信息的数组
}
~~~

页面中每个记录的存储格式

~~~go
type branchPageElement struct {
	pos   uint32 //存储key的位置
	ksize uint32 //key的大小
	pgid  pgid //key 所在的页面
}
~~~



非叶子节点存储格式如下图所示:

![image-20240426104619034](D:\个人笔记\doc\db\boltdb.assets\image-20240426104619034.png)



### 叶子节点存储格式

叶子节点中每个记录的格式:

~~~go
type leafPageElement struct {
	flags uint32
	pos   uint32
	ksize uint32
	vsize uint32
}
~~~



叶子节点存储格式如下图所示:

![image-20240426105825277](D:\个人笔记\doc\db\boltdb.assets\image-20240426105825277.png)



## bucket

bucket 实际也是以key-value形式存储在b+树中。bucket和bucket包含的key-value是怎么关联起来的呢？怎么确定key1 属于bucket_a 而不是bucket_b

~~~go
// bucket represents the on-file representation of a bucket.
// This is stored as the "value" of a bucket key. If the bucket is small enough,
// then its root page can be stored inline in the "value", after the bucket
// header. In the case of inline buckets, the "root" will be 0.
type bucket struct {
	root     pgid   // page id of the bucket's root-level page
	sequence uint64 // monotonically incrementing, used by NextSequence()
}
~~~



## cursor

cursor从bucket的root开始遍历，事务的第一个bucket的root则指向b+树的根页面。

## Transaction

~~~go
// Tx represents a read-only or read/write transaction on the database.
// Read-only transactions can be used for retrieving values for keys and creating cursors.
// Read/write transactions can create and remove buckets and create and remove keys.
//
// IMPORTANT: You must commit or rollback transactions when you are done with
// them. Pages can not be reclaimed by the writer until no more transactions
// are using them. A long running read transaction can cause the database to
// quickly grow.
type Tx struct {
	writable       bool
	managed        bool
	db             *DB
	meta           *meta
	root           Bucket
	pages          map[pgid]*page
	stats          TxStats
	commitHandlers []func()

	// WriteFlag specifies the flag for write-related methods like WriteTo().
	// Tx opens the database file with the specified flag to copy the data.
	//
	// By default, the flag is unset, which works well for mostly in-memory
	// workloads. For databases that are much larger than available RAM,
	// set the flag to syscall.O_DIRECT to avoid trashing the page cache.
	WriteFlag int
}
~~~

