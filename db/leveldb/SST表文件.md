# SSTable

[TOC]

table模块提供了对SST文件的读写功能。下面就结合代码分析一下SSTable的读写流程及文件格式

## 写入

table/writer.go 中Wrier封装了对SST文件的写入功能。包含数据块、索引块、filter块的写入，下面是Writer的定义

~~~go
// Writer is a table writer.
type Writer struct {
	writer io.Writer
	err    error
	// Options
	cmp         comparer.Comparer
	filter      filter.Filter
	compression opt.Compression
	blockSize   int

	bpool       *util.BufferPool
	dataBlock   blockWriter
	indexBlock  blockWriter
	filterBlock filterWriter
	pendingBH   blockHandle
	offset      uint64
	nEntries    int
	// Scratch allocated enough for 5 uvarint. Block writer should not use
	// first 20-bytes since it will be used to encode block handle, which
	// then passed to the block writer itself.
	scratch            [50]byte
	comparerScratch    []byte
	compressionScratch []byte
}
~~~

Writer对外提供了两个方法Append和Close。

* Append负责将key-value组织到数据块内，并将数据块写入到文件
* Close 负责将数据块索引、元信息写入文件

Append方法

Append方法做了以下工作:

* 检查key是否严格递增
* 调用flushPendingBH，将前一个数据块的元信息：块内的最大的key的successor(没有successor时，使用最大的key)、块在文件内的位置、长度信息编码到索引块中。此时索引块只是在内存中，等待Writer.Close方法被调用时会写入文件
* 调用blockWriter.append将key-value写入到数据块内
* 调用filterWriter.add将key加入到过滤器内，对bloomfilter的分析见其他部分
* 若块大小超过块的阈值，调用Writer.finishBlock。finishBlock则执行以下步骤：1）调用blockWriter.finish将restartPoint写入块内。2）调用Writer.writeBlock，若设置了压缩算法则将数据块压缩，然后写入文件。并记录数据块在文件内的位置和大小信息 3) 调用filterWriter.flush生成数据块对应的filter块(filter块此时仍在内存中)。并记录位置信息

~~~go
// Append appends key/value pair to the table. The keys passed must
// be in increasing order.
//
// It is safe to modify the contents of the arguments after Append returns.
func (w *Writer) Append(key, value []byte) error {
	if w.err != nil {
		return w.err
	}
	if w.nEntries > 0 && w.cmp.Compare(w.dataBlock.prevKey, key) >= 0 {
		w.err = fmt.Errorf("leveldb/table: Writer: keys are not in increasing order: %q, %q", w.dataBlock.prevKey, key)
		return w.err
	}

	if err := w.flushPendingBH(key); err != nil {
		return err
	}
	// Append key/value pair to the data block.
	if err := w.dataBlock.append(key, value); err != nil {
		return err
	}
	// Add key to the filter block.
	w.filterBlock.add(key)

	// Finish the data block if block size target reached.
	if w.dataBlock.bytesLen() >= w.blockSize {
		if err := w.finishBlock(); err != nil {
			w.err = err
			return w.err
		}
	}
	w.nEntries++
	return nil
}
~~~



Close

* 若最后一个块有数据，则调用Writer.finishBlock将块写入文件。若表文件没有任何数据则写入一个空块
* 调用Writer.flushPendingBH将数据块的元信息放入到索引块中
* 调用filterWriter.finish并将filter数据块写入文件，filter只有一个大块，包含多个小块，每个小块对应一个数据块
* 将filter的元信息metaindex块写入文件， metaindex块包含filter的名称，以及filter块的blockHandle
* 将索引块写入文件
* 写入table footer，table foolter总共48字节。table footer依次由metaIndex块的blockHandle、index块的blockHandle、8字节的magic组成

~~~go
// Close will finalize the table. Calling Append is not possible
// after Close, but calling BlocksLen, EntriesLen and BytesLen
// is still possible.
func (w *Writer) Close() error {
	defer func() {
		if w.bpool != nil {
			// Buffer.Bytes() returns [offset:] of the buffer.
			// We need to Reset() so that the offset = 0, resulting
			// in buf.Bytes() returning the whole allocated bytes.
			w.dataBlock.buf.Reset()
			w.bpool.Put(w.dataBlock.buf.Bytes())
		}
	}()

	if w.err != nil {
		return w.err
	}

	// Write the last data block. Or empty data block if there
	// aren't any data blocks at all.
	if w.dataBlock.nEntries > 0 || w.nEntries == 0 {
		if err := w.finishBlock(); err != nil {
			w.err = err
			return w.err
		}
	}
	if err := w.flushPendingBH(nil); err != nil {
		return err
	}

	// Write the filter block.
	var filterBH blockHandle
	if err := w.filterBlock.finish(); err != nil {
		return err
	}
	if buf := &w.filterBlock.buf; buf.Len() > 0 {
		filterBH, w.err = w.writeBlock(buf, opt.NoCompression)
		if w.err != nil {
			return w.err
		}
	}

	// Write the metaindex block.
	if filterBH.length > 0 {
		key := []byte("filter." + w.filter.Name())
		n := encodeBlockHandle(w.scratch[:20], filterBH)
		if err := w.dataBlock.append(key, w.scratch[:n]); err != nil {
			return err
		}
	}
	if err := w.dataBlock.finish(); err != nil {
		return err
	}
	metaindexBH, err := w.writeBlock(&w.dataBlock.buf, w.compression)
	if err != nil {
		w.err = err
		return w.err
	}

	// Write the index block.
	if err := w.indexBlock.finish(); err != nil {
		return err
	}
	indexBH, err := w.writeBlock(&w.indexBlock.buf, w.compression)
	if err != nil {
		w.err = err
		return w.err
	}

	// Write the table footer.
	footer := w.scratch[:footerLen]
	for i := range footer {
		footer[i] = 0
	}
	n := encodeBlockHandle(footer, metaindexBH)
	encodeBlockHandle(footer[n:], indexBH)
	copy(footer[footerLen-len(magic):], magic)
	if _, err := w.writer.Write(footer); err != nil {
		w.err = err
		return w.err
	}
	w.offset += footerLen

	w.err = errors.New("leveldb/table: writer is closed")
	return nil
}
~~~



### filterWriter

fukterWruter.flush方法没有搞清楚

~~~
type filterWriter struct {
	generator filter.FilterGenerator
	buf       util.Buffer
	nKeys     int
	offsets   []uint32
	baseLg    uint
}

func (w *filterWriter) add(key []byte) {
	if w.generator == nil {
		return
	}
	w.generator.Add(key)
	w.nKeys++
}

func (w *filterWriter) flush(offset uint64) {
	if w.generator == nil {
		return
	}
	//???? w.baseLg的值默认为  DefaultFilterBaseLg 11. 2KB
	//offset  4 / 2 = 2
	for x := int(offset / uint64(1<<w.baseLg)); x > len(w.offsets); {
		w.generate()
	}
}

func (w *filterWriter) finish() error {
	if w.generator == nil {
		return nil
	}
	// Generate last keys.

	if w.nKeys > 0 {
		w.generate()
	}
	w.offsets = append(w.offsets, uint32(w.buf.Len()))
	for _, x := range w.offsets {
		buf4 := w.buf.Alloc(4)
		binary.LittleEndian.PutUint32(buf4, x)
	}
	return w.buf.WriteByte(byte(w.baseLg))
}

func (w *filterWriter) generate() {
	// Record offset.
	w.offsets = append(w.offsets, uint32(w.buf.Len()))
	// Generate filters.
	if w.nKeys > 0 {
		w.generator.Generate(&w.buf)
		w.nKeys = 0
	}
}
~~~



## 读取



## 格式

数据块、索引块、filter块、metaIndex块、index块的格式如下：

filter块不包含restart point数据

![image-20230629143422312](D:\个人笔记\doc\db\leveldb\SST表文件.assets\image-20230629143422312.png)

### 数据块的格式

数据块内存储的是key-value。按key升序存储。默认的块大小是4KB

BlockRestartInterval是做什么用的，默认值16。块内key-value个数每到达BlockRestartInterval的倍数时，当前的key和前一个key的共享字节数被重置为0(即使有共享)。估计是key一般不会都存在共享的前缀

![image-20230629095530180](D:\个人笔记\doc\db\leveldb\SST表文件.assets\image-20230629095530180.png)





### filter块

filter块的格式如下

![image-20230629110118054](D:\个人笔记\doc\db\leveldb\SST表文件.assets\image-20230629110118054.png)

filter块和数据块的对应关系有点绕：

![image-20230629161111315](D:\个人笔记\doc\db\leveldb\SST表文件.assets\image-20230629161111315.png)

flush和generate两个方法确定datab lock和filter block的对应关系。

~~~go
//offset是数据块在文件中的位置
func (w *filterWriter) flush(offset uint64) {
	if w.generator == nil {
		return
	}
	//???? w.baseLg的值默认为  DefaultFilterBaseLg 11. 2KB
	//offset  4 / 2 = 2
	//假设baseLg 11, 就是2KB数据对应一个filter块。

	//16 / 2 = 8 . 8 > 4
	for x := int(offset / uint64(1<<w.baseLg)); x > len(w.offsets); {
		w.generate()
	}
}

func (w *filterWriter) generate() {
	// Record offset.
	w.offsets = append(w.offsets, uint32(w.buf.Len()))
	// Generate filters.
	if w.nKeys > 0 {
		w.generator.Generate(&w.buf)
		w.nKeys = 0
	}
}
~~~



索引块

索引块内存储的也是key-value。只是key是对应的数据块包含的最大的key或其sucessor，value是blockHandle由块在文件中的位置、块的大小两部分组成

索引块和数据块的编码格式一致。其他块的编码参考leveldb 的文档



下面的图更清晰的展示了SSTable文件格式

![image-20230629113742600](D:\个人笔记\doc\db\leveldb\SST表文件.assets\image-20230629113742600.png)

~~~

~~~



table/table.go 中的对SST文件格式的详细描述

~~~
/*
Table:

Table is consist of one or more data blocks, an optional filter block
a metaindex block, an index block and a table footer. Metaindex block
is a special block used to keep parameters of the table, such as filter
block name and its block handle. Index block is a special block used to
keep record of data blocks offset and length, index block use one as
restart interval. The key used by index block are the last key of preceding
block, shorter separator of adjacent blocks or shorter successor of the
last key of the last block. Filter block is an optional block contains
sequence of filter data generated by a filter generator.

Table data structure:
                                                         + optional
                                                        /
    +--------------+--------------+--------------+------+-------+-----------------+-------------+--------+
    | data block 1 |      ...     | data block n | filter block | metaindex block | index block | footer |
    +--------------+--------------+--------------+--------------+-----------------+-------------+--------+

    Each block followed by a 5-bytes trailer contains compression type and checksum.

Table block trailer:

    +---------------------------+-------------------+
    | compression type (1-byte) | checksum (4-byte) |
    +---------------------------+-------------------+

    The checksum is a CRC-32 computed using Castagnoli's polynomial. Compression
    type also included in the checksum.

Table footer:

      +------------------- 40-bytes -------------------+
     /                                                  \
    +------------------------+--------------------+------+-----------------+
    | metaindex block handle / index block handle / ---- | magic (8-bytes) |
    +------------------------+--------------------+------+-----------------+

    The magic are first 64-bit of SHA-1 sum of "http://code.google.com/p/leveldb/".

NOTE: All fixed-length integer are little-endian.
*/

/*
Block:

Block is consist of one or more key/value entries and a block trailer.
Block entry shares key prefix with its preceding key until a restart
point reached. A block should contains at least one restart point.
First restart point are always zero.

Block data structure:

      + restart point                 + restart point (depends on restart interval)
     /                               /
    +---------------+---------------+---------------+---------------+---------+
    | block entry 1 | block entry 2 |      ...      | block entry n | trailer |
    +---------------+---------------+---------------+---------------+---------+

Key/value entry:

              +---- key len ----+
             /                   \
    +-------+---------+-----------+---------+--------------------+--------------+----------------+
    | shared (varint) | not shared (varint) | value len (varint) | key (varlen) | value (varlen) |
    +-----------------+---------------------+--------------------+--------------+----------------+

    Block entry shares key prefix with its preceding key:
    Conditions:
        restart_interval=2
        entry one  : key=deck,value=v1
        entry two  : key=dock,value=v2
        entry three: key=duck,value=v3
    The entries will be encoded as follow:

      + restart point (offset=0)                                                 + restart point (offset=16)
     /                                                                          /
    +-----+-----+-----+----------+--------+-----+-----+-----+---------+--------+-----+-----+-----+----------+--------+
    |  0  |  4  |  2  |  "deck"  |  "v1"  |  1  |  3  |  2  |  "ock"  |  "v2"  |  0  |  4  |  2  |  "duck"  |  "v3"  |
    +-----+-----+-----+----------+--------+-----+-----+-----+---------+--------+-----+-----+-----+----------+--------+
     \                                   / \                                  / \                                   /
      +----------- entry one -----------+   +----------- entry two ----------+   +---------- entry three ----------+

    The block trailer will contains two restart points:

    +------------+-----------+--------+
    |     0      |    16     |   2    |
    +------------+-----------+---+----+
     \                      /     \
      +-- restart points --+       + restart points length

Block trailer:

      +-- 4-bytes --+
     /               \
    +-----------------+-----------------+-----------------+------------------------------+
    | restart point 1 |       ....      | restart point n | restart points len (4-bytes) |
    +-----------------+-----------------+-----------------+------------------------------+


NOTE: All fixed-length integer are little-endian.
*/

/*
Filter block:

Filter block consist of one or more filter data and a filter block trailer.
The trailer contains filter data offsets, a trailer offset and a 1-byte base Lg.

Filter block data structure:

      + offset 1      + offset 2      + offset n      + trailer offset
     /               /               /               /
    +---------------+---------------+---------------+---------+
    | filter data 1 |      ...      | filter data n | trailer |
    +---------------+---------------+---------------+---------+

Filter block trailer:

      +- 4-bytes -+
     /             \
    +---------------+---------------+---------------+-------------------------------+------------------+
    | data 1 offset |      ....     | data n offset | data-offsets offset (4-bytes) | base Lg (1-byte) |
    +-------------- +---------------+---------------+-------------------------------+------------------+


NOTE: All fixed-length integer are little-endian.
*/

~~~

## Thinking

* 索引块存储数据块的最大的key时，为什么没用块内最大的key而是用了一个比紧跟在key后面的successor



## 参考

leveldb 官方给出的SST文件格式描述：https://github.com/google/leveldb/blob/main/doc/table_format.md

~~~
<beginning_of_file>
[data block 1]
[data block 2]
...
[data block N]
[meta block 1]
...
[meta block K]
[metaindex block]
[index block]
[Footer]        (fixed size; starts at file_size - sizeof(Footer))
<end_of_file>
The file contains internal pointers. Each such pointer is called a BlockHandle and contains the following information:

offset:   varint64
size:     varint64
See varints for an explanation of varint64 format.

The sequence of key/value pairs in the file are stored in sorted order and partitioned into a sequence of data blocks. These blocks come one after another at the beginning of the file. Each data block is formatted according to the code in block_builder.cc, and then optionally compressed.

After the data blocks we store a bunch of meta blocks. The supported meta block types are described below. More meta block types may be added in the future. Each meta block is again formatted using block_builder.cc and then optionally compressed.

A "metaindex" block. It contains one entry for every other meta block where the key is the name of the meta block and the value is a BlockHandle pointing to that meta block.

An "index" block. This block contains one entry per data block, where the key is a string >= last key in that data block and before the first key in the successive data block. The value is the BlockHandle for the data block.

At the very end of the file is a fixed length footer that contains the BlockHandle of the metaindex and index blocks as well as a magic number.

 metaindex_handle: char[p];     // Block handle for metaindex
 index_handle:     char[q];     // Block handle for index
 padding:          char[40-p-q];// zeroed bytes to make fixed length
                                // (40==2*BlockHandle::kMaxEncodedLength)
 magic:            fixed64;     // == 0xdb4775248b80fb57 (little-endian)
"filter" Meta Block
If a FilterPolicy was specified when the database was opened, a filter block is stored in each table. The "metaindex" block contains an entry that maps from filter.<N> to the BlockHandle for the filter block where <N> is the string returned by the filter policy's Name() method.

The filter block stores a sequence of filters, where filter i contains the output of FilterPolicy::CreateFilter() on all keys that are stored in a block whose file offset falls within the range

[ i*base ... (i+1)*base-1 ]
Currently, "base" is 2KB. So for example, if blocks X and Y start in the range [ 0KB .. 2KB-1 ], all of the keys in X and Y will be converted to a filter by calling FilterPolicy::CreateFilter(), and the resulting filter will be stored as the first filter in the filter block.

The filter block is formatted as follows:

[filter 0]
[filter 1]
[filter 2]
...
[filter N-1]

[offset of filter 0]                  : 4 bytes
[offset of filter 1]                  : 4 bytes
[offset of filter 2]                  : 4 bytes
...
[offset of filter N-1]                : 4 bytes

[offset of beginning of offset array] : 4 bytes
lg(base)                              : 1 byte
The offset array at the end of the filter block allows efficient mapping from a data block offset to the corresponding filter.

"stats" Meta Block
This meta block contains a bunch of stats. The key is the name of the statistic. The value contains the statistic.

TODO(postrelease): record following stats.

data size
index size
key size (uncompressed)
value size (uncompressed)
number of entries
number of data blocks
~~~

