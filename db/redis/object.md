# 对象类型

redis定义了如下对象类型:
* STRING
* LIST
* SET
* ZSET
* HASH


```
typedef struct redisObject {
    unsigned type:4;        //对象类型
    unsigned notused:2;     /* Not used */
    unsigned encoding:4;    //对象编码方式
    unsigned lru:22;        /* lru time (relative to server.lruclock) */
    int refcount;           //引用计数
    void *ptr;
} robj;

```

对象编码方式,对象编码方式对什么有影响? 
字符串对象若可以转换成整数，则用对应的整数表示，可以减少存储空间的占用

```
#define REDIS_ENCODING_RAW 0     /* Raw representation */
#define REDIS_ENCODING_INT 1     /* Encoded as integer */
#define REDIS_ENCODING_HT 2      /* Encoded as hash table */
#define REDIS_ENCODING_ZIPMAP 3  /* Encoded as zipmap */
#define REDIS_ENCODING_LINKEDLIST 4 /* Encoded as regular linked list */
#define REDIS_ENCODING_ZIPLIST 5 /* Encoded as ziplist */
#define REDIS_ENCODING_INTSET 6  /* Encoded as intset */
#define REDIS_ENCODING_SKIPLIST 7  /* Encoded as skiplist */

```


对象类型
```
#define REDIS_STRING 0
#define REDIS_LIST 1
#define REDIS_SET 2
#define REDIS_ZSET 3
#define REDIS_HASH 4
```