# LRU和LFU

[TOC]



### [146. LRU缓存机制](https://leetcode-cn.com/problems/lru-cache/)

难度中等953收藏分享切换为英文接收动态反馈

运用你所掌握的数据结构，设计和实现一个  [LRU (最近最少使用) 缓存机制](https://baike.baidu.com/item/LRU)。它应该支持以下操作： 获取数据 `get` 和 写入数据 `put` 。

获取数据 `get(key)` - 如果关键字 (key) 存在于缓存中，则获取关键字的值（总是正数），否则返回 -1。
写入数据 `put(key, value)` - 如果关键字已经存在，则变更其数据值；如果关键字不存在，则插入该组「关键字/值」。当缓存容量达到上限时，它应该在写入新数据之前删除最久未使用的数据值，从而为新的数据值留出空间。

 进阶:

你是否可以在 O(1) 时间复杂度内完成这两种操作？

 

示例:

LRUCache cache = new LRUCache( 2 /* 缓存容量 */ );

cache.put(1, 1);
cache.put(2, 2);
cache.get(1);       // 返回  1
cache.put(3, 3);    // 该操作会使得关键字 2 作废
cache.get(2);       // 返回 -1 (未找到)
cache.put(4, 4);    // 该操作会使得关键字 1 作废
cache.get(1);       // 返回 -1 (未找到)
cache.get(3);       // 返回  3
cache.get(4);       // 返回  4

来源：力扣（LeetCode）
链接：https://leetcode-cn.com/problems/lru-cache
著作权归领扣网络所有。商业转载请联系官方授权，非商业转载请注明出处。



#### 思路

最初的思路就是`哈希表`加上`优先级队列`，只不过key-value的最近使用时间用的是time.Now().Unix()。使用time.Now().Unix()，会导致两个key的最近使用时间相同，因为Unix()返回的是以描述为单位的时间戳。因此使用一个整数序列表示逻辑时间

~~~go
type node struct {
	lastTime int
	key      int
	value    int
	index    int
}

type LRUCache struct {
	size  int
	count int
	cache map[int]*node
	queue *priQueue
}

//小根堆，最久未使用的为根
type priQueue struct {
	size int
	data []*node
}

func (this *priQueue) put(pn *node) {
	this.size++
	this.data[this.size] = pn

	i := this.size
	for i > 1 {
		p := i / 2
		if this.data[p].lastTime > pn.lastTime {
			this.data[i] = this.data[p]
			this.data[i].index = i
		} else {
			break
		}
		i = p
	}
	this.data[i] = pn
	pn.index = i
}

func (this *priQueue) update(pn *node) {
	idx := pn.index
	data := this.data

	for idx < this.size {
		l := idx * 2
		r := l + 1
        if l > this.size{
            break
        }
		if r <= this.size && this.data[l].lastTime > this.data[r].lastTime {
			l = r
		}
		//move up
       // fmt.Printf("%d %d %d\n", l,r, this.size)
		if pn.lastTime > this.data[l].lastTime {
			data[idx] = data[l]
			data[idx].index = idx
		} else {
			break
		}
		idx = l
	}
	data[idx] = pn
	pn.index = idx
	//this.dump()
}

func (this *priQueue) del() int {
	//this.dump()
	data := this.data
	key := data[1].key
	pn := data[this.size]
	this.size--
	i := 1
	for i < this.size {
		l := i * 2
        if l > this.size{
            break
        }
		if l+1 <= this.size && this.data[l].lastTime > this.data[l+1].lastTime {
			l = l + 1
		}
		//move up
		if pn.lastTime > this.data[l].lastTime {
			data[i] = data[l]
			data[i].index = i
		} else {
			break
		}
		i = l
	}
	data[i] = pn
	data[i].index = i
	//this.dump()
	return key

}

func (this *priQueue) dump() {
	for i, v := range this.data {
		if v == nil {
			continue
		}
		fmt.Printf("i:%d key:%d v:%d index:%d time:%d\n", i, v.key, v.value, v.index, v.lastTime)
	}
}

func Constructor(capacity int) LRUCache {
	return LRUCache{
		size:  capacity,
		count: 0,
		cache: make(map[int]*node, capacity),
		queue: &priQueue{
			size: 0,
			data: make([]*node, capacity+1),
		},
	}
}

func (this *LRUCache) Get(key int) int {
	if v, ok := this.cache[key]; ok {
		v.lastTime = getNow()
		this.queue.update(v)
		return v.value
	}
	return -1
}

func (this *LRUCache) Put(key int, value int) {
	if v, ok := this.cache[key]; ok {
		v.value = value
		v.lastTime = getNow()
		this.queue.update(v)
		return
	}
	if this.count == this.size {
		key := this.queue.del()
		delete(this.cache, key)
		this.count--
	}

	now := getNow()
	n := &node{key: key, value: value, lastTime: now}
	this.cache[key] = n
	this.count++
	this.queue.put(n)
}

var logicTime = 0

func getNow() int {
	logicTime++
	return logicTime
}

~~~





![1603029078994](${img}/1603029078994.png)





#### [460. LFU缓存](https://leetcode-cn.com/problems/lfu-cache/)

难度困难281收藏分享切换为英文接收动态反馈

请你为 [最不经常使用（LFU）](https://baike.baidu.com/item/%E7%BC%93%E5%AD%98%E7%AE%97%E6%B3%95)缓存算法设计并实现数据结构。它应该支持以下操作：`get` 和 `put`。

- `get(key)` - 如果键存在于缓存中，则获取键的值（总是正数），否则返回 -1。
- `put(key, value)` - 如果键已存在，则变更其值；如果键不存在，请插入键值对。当缓存达到其容量时，则应该在插入新项之前，使最不经常使用的项无效。在此问题中，当存在平局（即两个或更多个键具有相同使用频率）时，应该去除最久未使用的键。

「项的使用次数」就是自插入该项以来对其调用 `get` 和 `put` 函数的次数之和。使用次数会在对应项被移除后置为 0 。

 

**进阶：**
你是否可以在 **O(1)** 时间复杂度内执行两项操作？

 

**示例：**

```
LFUCache cache = new LFUCache( 2 /* capacity (缓存容量) */ );

cache.put(1, 1);
cache.put(2, 2);
cache.get(1);       // 返回 1
cache.put(3, 3);    // 去除 key 2
cache.get(2);       // 返回 -1 (未找到key 2)
cache.get(3);       // 返回 3
cache.put(4, 4);    // 去除 key 1
cache.get(1);       // 返回 -1 (未找到 key 1)
cache.get(3);       // 返回 3
cache.get(4);       // 返回 4
```