# 字符串类型的数据结构
字符类型的数据结构通过set、get命令操作
对字符串类型做存/取操作时，都首先检查是否当前操作的key是否超时

## 存储

流程:
1) 对字符串对象进行编码
2) 查看当前的键值对是否过期,过期则删除
3) 保存键值对
4) 若之前该键值对设置了过期时间，但未过期。删除过期时间设置
5) 通知 “观察该键”的观察者

### 编码
1) 尝试将字符串转换为对应的数值类型, 以减少占用空间, 字符串长度(字节数)超过21或转换成数值导致溢出，则不进行编码。对象继续使用字符串编码方式
2) 若字符串可以转换成数值，且数值小于 REDIS_SHARD_INTEGER(10000),则使用内置的共享数值对象。

### 检查key是否过期

1) slave节点不处理过期的键，等待master删除过期键的同步
2) 
3) 从redisDB.dict删除对应的键值对


## 读取

1) 检查键值对是否过期，过期则删除

查找键的函数如下，个人认为有些不合理
```c
robj *lookupKeyRead(redisDb *db, robj *key) {
    robj *val;

    //expireIfNeeded 如果已经删除键值对，就没必要调用lookupKey
    //可以优化
    expireIfNeeded(db,key);
    val = lookupKey(db,key);
    if (val == NULL)
        server.stat_keyspace_misses++;
    else
        server.stat_keyspace_hits++;
    return val;
}
```