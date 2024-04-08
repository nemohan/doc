# 字典
[TOC]

版本: 7.0.5

redis中字典由哈希表实现

dict 可以说是redis的核心



## dict的定义

实现部分在dict.c中

~~~c

typedef struct dictType {
    uint64_t (*hashFunction)(const void *key);
    void *(*keyDup)(dict *d, const void *key);
    void *(*valDup)(dict *d, const void *obj);
    int (*keyCompare)(dict *d, const void *key1, const void *key2);
    void (*keyDestructor)(dict *d, void *key);
    void (*valDestructor)(dict *d, void *obj);
    int (*expandAllowed)(size_t moreMem, double usedRatio);
    /* Allow a dictEntry to carry extra caller-defined metadata.  The
     * extra memory is initialized to 0 when a dictEntry is allocated. */
    size_t (*dictEntryMetadataBytes)(dict *d);
} dictType;

typedef struct dictEntry {
    void *key;
    union {
        void *val;
        uint64_t u64;
        int64_t s64;
        double d;
    } v;
    struct dictEntry *next;     /* Next entry in the same hash bucket. */
    void *metadata[];           /* An arbitrary number of bytes (starting at a
                                 * pointer-aligned address) of size as returned
                                 * by dictType's dictEntryMetadataBytes(). */
} dictEntry;

struct dict {
    dictType *type;

    dictEntry **ht_table[2];
    unsigned long ht_used[2];

    long rehashidx; /* rehashing not in progress if rehashidx == -1 */

    /* Keep small vars at end for optimal (minimal) struct padding */
    int16_t pauserehash; /* If >0 rehashing is paused (<0 indicates coding error) */
    signed char ht_size_exp[2]; /* exponent of size. (size = 1<<exp) */
};

~~~




## rehash

### 增大哈希表的条件
若哈希表的初始大小为0，则将哈希表增加到由宏DICT_HT_INITIAL_SIZE定义的默认大小4。
否则根据哈希表中元素个数和哈希表的大小的比例确定是否拓展哈希表. 若满足拓展条件，将哈希表的大小拓展为哈希表当前元素个数的2倍。
若同时满足以下条件，则进行rehash:

* 当前哈希表的元素个数大于等于哈希表大小
* dict_can_resize 为1 或者元素个数/哈希表大小 超过dict_force_resize_ratio
* 对应的哈希类型允许拓展哈希表


~~~c
/* Expand the hash table if needed */
static int _dictExpandIfNeeded(dict *d)
{
    /* Incremental rehashing already in progress. Return. */
    if (dictIsRehashing(d)) return DICT_OK;

    /* If the hash table is empty expand it to the initial size. */
    if (DICTHT_SIZE(d->ht_size_exp[0]) == 0) return dictExpand(d, DICT_HT_INITIAL_SIZE);

    /* If we reached the 1:1 ratio, and we are allowed to resize the hash
     * table (global setting) or we should avoid it but the ratio between
     * elements/buckets is over the "safe" threshold, we resize doubling
     * the number of buckets. */
    if (d->ht_used[0] >= DICTHT_SIZE(d->ht_size_exp[0]) &&
        (dict_can_resize ||
         d->ht_used[0]/ DICTHT_SIZE(d->ht_size_exp[0]) > dict_force_resize_ratio) &&
        dictTypeExpandAllowed(d))
    {
        return dictExpand(d, d->ht_used[0] + 1);
    }
    return DICT_OK;
}
~~~

拓展哈希表。首先创建指定大小的哈希表，若第一个哈希表dict.ht[0]为空，表明是初次设置哈希表，将dict.ht[0]指向新创建的哈希表；否则 dict.ht[1]指向新创建的哈希表， 并将dict.rehashidx置为0



### 迁移bucket的过程
若当前有迭代器指向哈希表，则不执行迁移过程。函数int dictRehash(dict *d, int n) 执行bucket的迁移，参数n决定要迁移几个bucket。
迁移步骤:
1) n * 10 确定最大的连续空的bucket的个数
2) 若遇到n*10个连续的空的bucket，则放弃此次迁移过程。以免阻塞时间过长
3) 迁移dict.rehashidx指向的bucket，每迁移一个元素则将旧的哈希表的元素个数减1(dict.ht[0].used--)，新哈希表的元素个数加1。
当前bucket迁移完成后，rehashidx自增指向下一个bucket
4) 若旧的哈希表的元素个数为0，表明所有元素已经迁移到新的哈希表。则迁移过程结束, 释放旧的哈希表并将dict.ht[0]指向新的哈希表，dict.rehashidx置为-1

### rehash 进行中时的增删改查

#### 添加元素

若正在进行rehash, 则首先将dict.ht[0]的一个哈希桶的所有元素迁移到dict.ht[1]中。
查找时会先在旧的哈希表中查找,若正在进行rehash还会在新的哈希表(dict.ht_table[1])中查找。若元素已经存在则放弃添加。
若不存在，则根据是否进行rehash确定添加到新的哈希表中还是旧的哈希表中

#### 替换元素

若正在进行rehash, 则首先将dict.ht[0]的一个哈希桶的所有元素迁移到dict.ht[1]中。
查找时会先在旧的哈希表中查找,若正在进行rehash还会在新的哈希表(dict.ht_table[1])中查找)

找到则替换，未找到则添加

#### 查找元素

若正在进行rehash, 则首先将dict.ht[0]由rehashidx指向的哈希桶的所有元素迁移到dict.ht[1]中
首先在dict.ht[0]指向的哈希表中查找。若未找到，则根据是否在进行rehash,确定是否在dict.ht[1]中查找

#### 删除元素

若正在进行rehash, 则首先将dict.ht[0]的一个哈希桶的所有元素迁移到dict.ht[1]中
首先在dict.ht[0]指向的哈希表查找。若未找到，则根据是否在进行rehash,确定是否在dict.ht[1]中查找
若找到则删除并将元素个数减1

## 迭代器

迭代器的定义
~~~c
/* If safe is set to 1 this is a safe iterator, that means, you can call
 * dictAdd, dictFind, and other functions against the dictionary even while
 * iterating. Otherwise it is a non safe iterator, and only dictNext()
 * should be called while iterating. */
typedef struct dictIterator {
    dict *d;
    long index;
    int table, safe;
    dictEntry *entry, *nextEntry;
    /* unsafe iterator fingerprint for misuse detection. */
    long long fingerprint;
} dictIterator;
~~~
迭代器创建:
哈希表指向第一个哈希表dict.ht[0]
bucket索引为-1

迭代过程:
1) 迭代器的entry未指向任何元素。若迭代器指向dict->ht[0]且迭代器的bucket位置索引未指向任何bucket，若dictIterator.safe是1则将字典的迭代器数量增加1，否则根据字典的当前状态计算一个指纹值;
迭代器的bucket索引自增指向下一个bucket,若当前bucket索引超过哈希表大小且正在进行rehash， 则将迭代器指向新的哈希表(dict->ht[1]), bucket索引重置为0;
迭代器指向bucket的第一个元素
2) 迭代器的entry指向当前元素的下一个元素
3) 若迭代器的entry不为空，则保存指向下一个元素的指针到nextEntry(防止当前元素被删除)。<font color='red'>不能处理nextEntry指向的元素被删除的情况</font>


## 有意思的地方
* 为了能够存储任意类型的键值对,且为不同的键提供不同的hash值计算方法。将字典和dictType 绑定在一起. dictType提供了"键"的比较、hash值计算、释放等函数
* rehash