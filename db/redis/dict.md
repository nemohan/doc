# 字典
[TOC]



2.6.17
redis中字典由哈希表实现

dict 可以说是redis的核心



## dict的定义

实现部分在dict.c中

~~~c

typedef struct dictType {
    unsigned int (*hashFunction)(const void *key);
    void *(*keyDup)(void *privdata, const void *key);
    void *(*valDup)(void *privdata, const void *obj);
    int (*keyCompare)(void *privdata, const void *key1, const void *key2);
    void (*keyDestructor)(void *privdata, void *key);
    void (*valDestructor)(void *privdata, void *obj);
} dictType;

/* This is our hash table structure. Every dictionary has two of this as we
 * implement incremental rehashing, for the old to the new table. */
typedef struct dictht {
    dictEntry **table;
    unsigned long size; //哈希表大小
    unsigned long sizemask;
    unsigned long used; //当前元素个数
} dictht;

typedef struct dict {
    dictType *type;
    void *privdata;
    dictht ht[2]; //ht[0] 未进行rehash时，使用的哈希表
    int rehashidx; /* rehashing not in progress if rehashidx == -1 */ //是否正在进行rehash。 不为-1时，表示当前需要迁移的哈希桶的索引,从0开始递增
    int iterators; /* number of iterators currently running */
} dict;
~~~




## rehash

### 前提条件
根据哈希表中元素个数和哈希表的大小的比例确定是否进行rehash. rehash时，将哈希表的大小拓展为原来的2倍
满足以下两个条件之一，则进行rehash:

* dictht.used >= dictht.size 并且 dict_can_resize 设置为1
* dictht.used >= dictht.size 并且dictht.used / dictht.size > dict_force_resize_ratio(当前版本是5)。
  进行rehash时，创建第二个哈希表即 dict.ht[1] 并设置正在进行rehash的标志(dict.rehashidx)



~~~c
  /* If we reached the 1:1 ratio, and we are allowed to resize the hash
     * table (global setting) or we should avoid it but the ratio between
     * elements/buckets is over the "safe" threshold, we resize doubling
     * the number of buckets. */
    if (d->ht[0].used >= d->ht[0].size &&
        (dict_can_resize ||
         d->ht[0].used/d->ht[0].size > dict_force_resize_ratio))
    {
        //这段代码有问题，根据上面的条件 d->ht[0].size > d->ht[0].used 永远不会成立
        return dictExpand(d, ((d->ht[0].size > d->ht[0].used) ?
                                    d->ht[0].size : d->ht[0].used)*2);
    }
~~~




### 过程
int dictRehash(dict *d, int n)
是否执行dictRehash 还取决于当前是否有迭代器指向哈希表

* 添加新的键值对时(dictAdd)，每次迁移一个哈希桶中的所有元素, 要迁移的哈希桶由dict.rehashidx确定
* 当前哈希桶迁移完成后，将dict.rehashidx增1。
* 每迁移一个元素将dict.ht[0].used 减1。



~~~c
int dictRehash(dict *d, int n) {
	/*哈希表没有rehash 直接返回*/
    if (!dictIsRehashing(d)) return 0;

    while(n--) {
        dictEntry *de, *nextde;

        /* Check if we already rehashed the whole table... */
	 /*rehash 完成*/
        if (d->ht[0].used == 0) {
            zfree(d->ht[0].table);
            d->ht[0] = d->ht[1];
            _dictReset(&d->ht[1]);
            d->rehashidx = -1;
            return 0;
        }

        /* Note that rehashidx can't overflow as we are sure there are more
         * elements because ht[0].used != 0 */
        assert(d->ht[0].size > (unsigned)d->rehashidx);
	    //跳过空的哈希桶
        while(d->ht[0].table[d->rehashidx] == NULL) d->rehashidx++;

	 
        de = d->ht[0].table[d->rehashidx];
        /* Move all the keys in this bucket from the old to the new hash HT */
        while(de) {
            unsigned int h;

            nextde = de->next;
            /* Get the index in the new hash table */
            h = dictHashKey(d, de->key) & d->ht[1].sizemask;
            de->next = d->ht[1].table[h];
            d->ht[1].table[h] = de;
            d->ht[0].used--;
            d->ht[1].used++;
            de = nextde;
        }
        d->ht[0].table[d->rehashidx] = NULL;
		//指向下一个要迁移的哈系桶
        d->rehashidx++;
    }
    return 1;
}

~~~



### 结束rehash

根据dict.ht[0].used是否减少到0，确定rehash是否完成. rehash完成时，释放dict.ht[0]。
并将dict.ht[1]重新赋值给dict.ht[0], dict.ht[1]则被重置为初始状态



## 添加元素
若正在进行rehash, 则首先将dict.ht[0]的一个哈希桶的所有元素迁移到dict.ht[1]中
在添加时，根据是否正在进行rehash确定是只在dict.ht[0]中查找，还是两个哈希表中都查找
若键值对不存在,根据是否在rehash分为两种情况:

* 正在进行rehash。则将新的键值对添加到dict.ht[1]中
* 否则添加到dict.ht[0]中

## 查找元素
若正在进行rehash, 则首先将dict.ht[0]的一个哈希桶的所有元素迁移到dict.ht[1]中
首先在dict.ht[0]指向的哈希表中查找。若未找到，则根据是否在进行rehash,确定是否在dict.ht[1]中查找

## 删除元素
若正在进行rehash, 则首先将dict.ht[0]的一个哈希桶的所有元素迁移到dict.ht[1]中
首先在dict.ht[0]指向的哈希表查找。若未找到，则根据是否在进行rehash,确定是否在dict.ht[1]中查找

## 迭代器

```c

```


## 有意思的地方
* 为了能够存储任意类型的键值对,且为不同的键提供不同的hash值计算方法。将字典和dictType 绑定在一起. dictType提供了"键"的比较、hash值计算、释放等函数
* rehash