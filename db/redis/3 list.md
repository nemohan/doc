# list
[TOC]



双向链表 2.6.17

## 存储结构 

<font color='red'>既然有两种存储结构。那何时选择ziplist作为存储结构，何时选择list(双链表)作为存储结构</font>。

默认选择是ziplist做为存储结构，若待存储的元素长度超过 server.list_max_ziplist_value指定的字节数时，或ziplist中元素个数超过server.list_max_ziplist_entries时，则会将ziplist转换为list

插入元素可能导致存储结构转换

<font color='red'>为啥有两种存储结构，又为啥会在ziplist包含的元素个数超过一定数目时，会从ziplist转为list</font>。



### ziplist存储结构

ziplist 对象的类型REDIS_LIST，编码类型为REDIS_ENCODING_ZIPLIST

z_list.c

```c
#define ZIP_END 255  //ziplist结束标志
#define ZIP_BIGLEN 254  

/* Different encoding/length possibilities */
#define ZIP_STR_MASK 0xc0
#define ZIP_INT_MASK 0x30
#define ZIP_STR_06B (0 << 6)
#define ZIP_STR_14B (1 << 6)
#define ZIP_STR_32B (2 << 6)
#define ZIP_INT_16B (0xc0 | 0 << 4)
#define ZIP_INT_32B (0xc0 | 1 << 4) // 0001 左移4位     0001 0000 0x10
#define ZIP_INT_64B (0xc0 | 2 << 4) // 0000 0010         0010 0000 0x20
#define ZIP_INT_24B (0xc0 | 3 << 4) // 0000 0011 左移4位 0011 0000 0x30
#define ZIP_INT_8B 0xfe
/* 4 bit integer immediate encoding */
#define ZIP_INT_IMM_MASK 0x0f
#define ZIP_INT_IMM_MIN 0xf1 /* 11110001 */
#define ZIP_INT_IMM_MAX 0xfd /* 11111101 */
#define ZIP_INT_IMM_VAL(v) (v & ZIP_INT_IMM_MASK)

#define INT24_MAX 0x7fffff
#define INT24_MIN (-INT24_MAX - 1)

/* Macro to determine type */
/*编码方式是否是字符串编码 0xc0 1100 0000*/
#define ZIP_IS_STR(enc) (((enc)&ZIP_STR_MASK) < ZIP_STR_MASK)

#define ZIPLIST_BYTES(zl) (*((uint32_t *)(zl)))
#define ZIPLIST_TAIL_OFFSET(zl) (*((uint32_t *)((zl) + sizeof(uint32_t))))
#define ZIPLIST_LENGTH(zl) (*((uint16_t *)((zl) + sizeof(uint32_t) * 2)))
#define ZIPLIST_HEADER_SIZE (sizeof(uint32_t) * 2 + sizeof(uint16_t))

//指向ziplist头部
#define ZIPLIST_ENTRY_HEAD(zl) ((zl) + ZIPLIST_HEADER_SIZE)

//指向ziplist尾部最后一个元素位置
#define ZIPLIST_ENTRY_TAIL(zl) ((zl) + intrev32ifbe(ZIPLIST_TAIL_OFFSET(zl)))

//ziplist空间最后一个字节的前一个字节，指向结束符的位置
#define ZIPLIST_ENTRY_END(zl) ((zl) + intrev32ifbe(ZIPLIST_BYTES(zl)) - 1)
```



~~~c
//ziplist的等价struct定义，ziplist.h并没有此ziplist结构体的定义
struct ziplist{
    uint32_t size; //总字节数
    uint32_t tail; //最后一个元素的位置
    uint16_t len; //元素个数
    uint8_t data[];
}


typedef struct zlentry {
  //prevrawlensize 前一个元素的长度所占的字节数
  //prevrawlen 前一个元素的长度
  unsigned int prevrawlensize, prevrawlen;

  //lensize 当前元素的encoding 和 长度 所占字节数
  //len 当前元素所占字节数
  unsigned int lensize, len;

  //headersize = prevrawlensize + lensize
  unsigned int headersize;

  unsigned char encoding;

  //元素起始位置
  unsigned char *p;
} zlentry;
~~~



创建新的ziplist:

```c
unsigned char *ziplistNew(void) {
  unsigned int bytes = ZIPLIST_HEADER_SIZE + 1;
  unsigned char *zl = zmalloc(bytes);
  ZIPLIST_BYTES(zl) = intrev32ifbe(bytes);
  ZIPLIST_TAIL_OFFSET(zl) = intrev32ifbe(ZIPLIST_HEADER_SIZE); //指向 结束标志ZIP_END的内存位置
  ZIPLIST_LENGTH(zl) = 0;
  zl[bytes - 1] = ZIP_END;
  return zl;
}
```



#### 内存结构

```
---------------------------------------------------------------------------------------------
空间大小(4字节)| 最后一个元素位置(4字节) | 元素个数(2字节) | 元素1| 元素2 | ...| 元素n | 结束标志 1字节,值为255
-------------------------------------------------------------------------------------------

每个元素的结构：
---------------------------------------------------------------
前一个元素的长度(字节数,不固定) | 编码格式(1字节) | 当前元素长度(大端方式) | 当前元素 
-------------------------------------------------------------

前一个元素长度:
若长度小于254(ZIP_BIGLEN)，则占用1字节
若长度大于等于254,则占用5个字节。第一个字节的值为(ZIP_BIGLEN 254),实际长度占用四个字节
前一个元素长度=前一个元素得编码长度+ 长度信息占用空间+ 值占用空间

```







#### 编码方式

| 类型   | 值的长度                 | 编码方式           | 编码占用字节数           | 长度占用字节数 |
| ------ | ------------------------ | ------------------ | ------------------------ | -------------- |
| 字符串 | 不超过63字节             | ZIP_STR_06B(0)     | 编码和长度共用一字节     | 0              |
| 字符串 | 不超过16383              | ZIP_STR_14B(0x40)  | 编码和长度共用第一个字节 | 2              |
| 字符串 | 超过16383                | ZIIP_STR_32B(0x80) | 1                        | 4              |
| 整型   | [0, 12]                  | 0xf1 - 0xfd        | 1                        | 0              |
| 整型   | [-128, 127]              | ZIP_INT_8B(0xfe)   | 1                        | 0              |
| 整型   | -32768到32767            | ZIP_INT_16B(0xc0)  | 1                        | 0              |
| 整型   | -8388608 到 8388607      | ZIP_INT_24B(0xf0)  | 1                        | 0              |
| 整型   | -2147483648 到2147483647 | ZIP_INT_32B(0xd0)  | 1                        | 0              |
| 整型   | 超过32位的有符号整数     | ZIP_INT_64B(0xe0)  | 1                        | 0              |



```c
/* Encode the length 'l' writing it in 'p'. If p is NULL it just returns
 * the amount of bytes required to encode such a length. */
static unsigned int zipEncodeLength(unsigned char *p, unsigned char encoding,
                                    unsigned int rawlen) {
  unsigned char len = 1, buf[5];

  if (ZIP_IS_STR(encoding)) {
    /* Although encoding is given it may not be set for strings,
     * so we determine it here using the raw length. */
    //长度小于63
    if (rawlen <= 0x3f) {
      if (!p)
        return len;
      buf[0] = ZIP_STR_06B | rawlen;
    } else if (rawlen <= 0x3fff) { //小于16383(16384 是16KB)
      len += 1;                    // 2字节空间存放长度信息
      if (!p)
        return len;
      // 0000 0001
      // 左移6位 0100 0000
      // rawlen的高8位 & 0011 1111
      buf[0] = ZIP_STR_14B | ((rawlen >> 8) & 0x3f);
      buf[1] = rawlen & 0xff;
    } else {
      //超过16KB 为何加4
      len += 4; // 5字节空间存放长度信息
      if (!p)
        return len;
      buf[0] = ZIP_STR_32B;
      buf[1] = (rawlen >> 24) & 0xff;
      buf[2] = (rawlen >> 16) & 0xff;
      buf[3] = (rawlen >> 8) & 0xff;
      buf[4] = rawlen & 0xff;
    }
  } else {
    /* Implies integer encoding, so length is always 1. */
    if (!p)
      return len;
    buf[0] = encoding;
  }

  /* Store this length at p */
  memcpy(p, buf, len);
  return len;
}
```



#### 插入元素流程

插入元素时先尝试看是否能将元素以整型表示，若不能则以字符串形式存储。能够以整型存储的条件，数字字符串长度满足 0<= entrylen <=32且能够转为整型数值。以整型存储可以在一定程度上减少内存的使用，如字符串"1234"若以字符串形式存储需要4个字节，而以整型存储则需要2个字节，内存使用减少了一倍。



~~~c
/* Insert item at "p". */
static unsigned char *__ziplistInsert(unsigned char *zl, unsigned char *p, unsigned char *s, unsigned int slen) {
    size_t curlen = intrev32ifbe(ZIPLIST_BYTES(zl)), reqlen, prevlen = 0;
    size_t offset;
    int nextdiff = 0;
    unsigned char encoding = 0;
    long long value = 123456789; /* initialized to avoid warning. Using a value
                                    that is easy to see if for some reason
                                    we use it uninitialized. */
    zlentry entry, tail;

    /* Find out prevlen for the entry that is inserted. */
    if (p[0] != ZIP_END) {
        entry = zipEntry(p);
        prevlen = entry.prevrawlen;
    } else { 
        unsigned char *ptail = ZIPLIST_ENTRY_TAIL(zl);
        if (ptail[0] != ZIP_END) {
            prevlen = zipRawEntryLength(ptail);
        }
    }

    /* See if the entry can be encoded */
    if (zipTryEncoding(s,slen,&value,&encoding)) {
        /* 'encoding' is set to the appropriate integer encoding */
        //编码后元素长度
        reqlen = zipIntSize(encoding);
    } else {
        /* 'encoding' is untouched, however zipEncodeLength will use the
         * string length to figure out how to encode it. */
        reqlen = slen; 
    }
    /* We need space for both the length of the previous entry and
     * the length of the payload. */
    //加上前一个元素的长度信息所占字节数
    reqlen += zipPrevEncodeLength(NULL,prevlen);
    //当前元素长度所占字节数
    reqlen += zipEncodeLength(NULL,encoding,slen);

    /* When the insert position is not equal to the tail, we need to
     * make sure that the next entry can hold this entry's length in
     * its prevlen field. */
     //当前元素的长度所占字节数 和 下一个元素的“前一个元素长度”所占字节数的差值
    nextdiff = (p[0] != ZIP_END) ? zipPrevLenByteDiff(p,reqlen) : 0;

    /* Store offset because a realloc may change the address of zl. */
    offset = p-zl;
    zl = ziplistResize(zl,curlen+reqlen+nextdiff);
    p = zl+offset;

    /* Apply memory move when necessary and update tail offset. */
    if (p[0] != ZIP_END) {
        /* Subtract one because of the ZIP_END bytes */
        //p+reqlen 是待插入的新元素的结束位置
        //p-nextdiff 需要为当前元素的长度所占字节数超出部分
        memmove(p+reqlen,p-nextdiff,curlen-offset-1+nextdiff);

        //更新下一个元素的"前一个元素长度信息"
        /* Encode this entry's raw length in the next entry. */
        zipPrevEncodeLength(p+reqlen,reqlen);

        /* Update offset for tail */
        ZIPLIST_TAIL_OFFSET(zl) =
            intrev32ifbe(intrev32ifbe(ZIPLIST_TAIL_OFFSET(zl))+reqlen);

        /* When the tail contains more than one entry, we need to take
         * "nextdiff" in account as well. Otherwise, a change in the
         * size of prevlen doesn't have an effect on the *tail* offset. */
        tail = zipEntry(p+reqlen);
        if (p[reqlen+tail.headersize+tail.len] != ZIP_END) {
            ZIPLIST_TAIL_OFFSET(zl) =
                intrev32ifbe(intrev32ifbe(ZIPLIST_TAIL_OFFSET(zl))+nextdiff);
        }
    } else {
        /* This element will be the new tail. */
        ZIPLIST_TAIL_OFFSET(zl) = intrev32ifbe(p-zl);
    }

    /* When nextdiff != 0, the raw length of the next entry has changed, so
     * we need to cascade the update throughout the ziplist */
    if (nextdiff != 0) {
        offset = p-zl;
        zl = __ziplistCascadeUpdate(zl,p+reqlen);
        p = zl+offset;
    }

    /* Write the entry */
    p += zipPrevEncodeLength(p,prevlen);
    p += zipEncodeLength(p,encoding,slen);
    if (ZIP_IS_STR(encoding)) {
        memcpy(p,s,slen);
    } else {
        zipSaveInteger(p,value,encoding);
    }
    ZIPLIST_INCR_LENGTH(zl,1);
    return zl;
}


~~~



#### 长度



**当元素个数小于65535时，长度在ziplist头部。当超过65535时，元素个数信息不再准确，需要遍历ziplist统计元素个数**

~~~c
unsigned int ziplistLen(unsigned char *zl) {
    unsigned int len = 0;
    if (intrev16ifbe(ZIPLIST_LENGTH(zl)) < UINT16_MAX) {
        len = intrev16ifbe(ZIPLIST_LENGTH(zl));
    } else {
        unsigned char *p = zl+ZIPLIST_HEADER_SIZE;
        while (*p != ZIP_END) {
            p += zipRawEntryLength(p);
            len++;
        }

        /* Re-store length if small enough */
        if (len < UINT16_MAX) ZIPLIST_LENGTH(zl) = intrev16ifbe(len);
    }
    return len;
}
~~~



#### 劣势

每次插入、删除都需要重新分配内存


### list(双链表)存储结构

list对象类型是REDIS_LIST，编码类型是REDIS_ENCODING_LINKEDLIST

双链表 adlist.c



```c
typedef struct listNode {
    struct listNode *prev;
    struct listNode *next;
    void *value;
} listNode;

typedef struct listIter {
    listNode *next;
    int direction;
} listIter;

typedef struct list {
    listNode *head;
    listNode *tail;
    void *(*dup)(void *ptr);
    void (*free)(void *ptr);
    int (*match)(void *ptr, void *key);
    unsigned long len;
} list;
```


![image-20240308164109944](D:\个人笔记\doc\db\redis\3 list.assets\image-20240308164109944.png)

## QUICKLIST

redis版本7.0.5

代码在t_list.c、quicklist.c、listpack.c文件中

新版本中 OBJ_ENCODING_ZIPLIST 、OBJ_ENCODING_LINKEDLIST 两种作为list底层的存储结构已不再使用，取而代之的是OBJ_ENCODING_QUICKLIST类型的存储结构。quicklist是link list和ziplist的结合体

~~~c
* quicklist is a 40 byte struct (on 64-bit systems) describing a quicklist.
 * 'count' is the number of total entries.
 * 'len' is the number of quicklist nodes.
 * 'compress' is: 0 if compression disabled, otherwise it's the number
 *                of quicklistNodes to leave uncompressed at ends of quicklist.
 * 'fill' is the user-requested (or default) fill factor.
 * 'bookmarks are an optional feature that is used by realloc this struct,
 *      so that they don't consume memory when not used. */
typedef struct quicklist {
    quicklistNode *head;
    quicklistNode *tail;
    unsigned long count;        /* total count of all entries in all listpacks */
    unsigned long len;          /* number of quicklistNodes */
    signed int fill : QL_FILL_BITS;       /* fill factor for individual nodes */
    unsigned int compress : QL_COMP_BITS; /* depth of end nodes not to compress;0=off */
    unsigned int bookmark_count: QL_BM_BITS;
    quicklistBookmark bookmarks[];
} quicklist;

/* quicklistNode is a 32 byte struct describing a listpack for a quicklist.
 * We use bit fields keep the quicklistNode at 32 bytes.
 * count: 16 bits, max 65536 (max lp bytes is 65k, so max count actually < 32k).
 * encoding: 2 bits, RAW=1, LZF=2.
 * container: 2 bits, PLAIN=1 (a single item as char array), PACKED=2 (listpack with multiple items).
 * recompress: 1 bit, bool, true if node is temporary decompressed for usage.
 * attempted_compress: 1 bit, boolean, used for verifying during testing.
 * extra: 10 bits, free for future use; pads out the remainder of 32 bits */
typedef struct quicklistNode {
    struct quicklistNode *prev;
    struct quicklistNode *next;
    unsigned char *entry;
    size_t sz;             /* entry size in bytes */
    unsigned int count : 16;     /* count of items in listpack */
    unsigned int encoding : 2;   /* RAW==1 or LZF==2 */
    unsigned int container : 2;  /* PLAIN==1 or PACKED==2 */
    unsigned int recompress : 1; /* was this node previous compressed? */
    unsigned int attempted_compress : 1; /* node can't compress; too small */
    unsigned int dont_compress : 1; /* prevent compression of entry that will be used later */
    unsigned int extra : 9; /* more bits to steal for future usage */
} quicklistNode;
~~~



quicklist整体结构如图:

![image-20240301094927694](D:\个人笔记\doc\db\redis\3 list.assets\image-20240301094927694.png)

listpack内存结构:

listpack结构的元信息和数据放在一块连续的内存区域内。

~~~
---------------------------------------------------------------------------------------------
空间大小(4字节)| 元素个数(2字节, 最多65535元素)| 最后一个元素位置 | 元素1| 元素2 | ...| 元素n | 结束标志 1字节,值为255
-------------------------------------------------------------------------------------------

整型元素的结构：
---------------------------------------------------------------
 编码格式(1字节) | 当前元素长度| 当前元素 | 当前元素长度(包括编码信息占用的空间)
-------------------------------------------------------------

字符串类型元素的结构:
---------------------------------------------------------------
编码格式(1字节) | 当前元素长度| 当前元素 
-------------------------------------------------------------

前一个元素长度:
若长度小于254(ZIP_BIGLEN)，则占用1字节
若长度大于等于254,则占用5个字节。第一个字节的值为(ZIP_BIGLEN 254),实际长度占用四个字节
前一个元素长度=前一个元素得编码长度+ 长度信息占用空间+ 值占用空间
~~~

值存储时占用的空间大小(编码格式+长度+值本身的长度)， 被存储了两次。格式"长度 | 元素| 长度"，为什么存储两次可能是方便逆向遍历(果然是)

编码

| 类型   | 值的长度                 | 编码方式                                 | 编码占用字节数                                  | 长度占用字节数 |
| ------ | ------------------------ | ---------------------------------------- | ----------------------------------------------- | -------------- |
| 字符串 | 不超过64字节             | LP_ENCODING_6BIT_STR(0x80)               | 编码和长度共用一字节                            | 0              |
| 字符串 | 不超过4096               | LP_ENCODING_12BIT_STR(0xE0)              | 编码和长度共用第一个字节(共2字节)               | 2              |
| 字符串 |                          | LP_ENCODING_32BIT_STR(0xF0)              | 共5字节                                         | 4              |
| 整型   | [0, 127]                 | LP_ENCODING_7BIT_UINT(字节的最高位0标识) | 只有一个字节来存放整型值                        | 0              |
| 整型   | [-4096, 4095]            | LP_ENCODING_13BIT_INT(0xc0)              | 编码和整型值共用2个字节(第一个字节包含编码信息) | 0              |
| 整型   | -32768到32767            | LP_ENCODING_16BIT_INT(0xF1)              | 编码和整型值共用3个字节(第一个字节包含编码信息) | 0              |
| 整型   | -8388608 到 8388607      | LP_ENCODING_24BIT_INT(0xF2)              | 编码和整型值共用4个字节                         | 0              |
| 整型   | -2147483648 到2147483647 | LP_ENCODING_32BIT_INT(0xF3)              | 编码和整型值共用5个字节                         | 0              |
| 整型   | 超过32位的有符号整数     | LP_ENCODING_64BIT_INT(0xF4)              | 编码和整型值共用9个字节                         | 0              |



### 插入元素流程

listpack:  若插入元素后的listpack所占空间超过现在使用的空间，则重新分配内存(非必须)。插入位置之后的元素都向后移动，为新元素准备空间。新元素插入指定位置

### 删除元素流程



listpack: 删除指定位置的元素，会将此位置之后的元素向前移动。并重新分配内存，以释放被删除内存的占用的空间



### 查找流程



### 总结

1 一个小技巧， 在双链表中为快速定位第n个元素的位置时，若n超过元素数量的一般，可逆向开始遍历



## TODO

* 比较一下ziplist和list这两种存储方式的性能