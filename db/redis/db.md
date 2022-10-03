# db



```
typedef struct redisDb {
    dict *dict;                 /* The keyspace for this DB */
    dict *expires;              /* Timeout of keys with a timeout set */ //保存所有带超时时间的key
    dict *blocking_keys;        /* Keys with clients waiting for data (BLPOP) */
    dict *ready_keys;           /* Blocked keys that received a PUSH */
    dict *watched_keys;         /* WATCHED keys for MULTI/EXEC CAS */
    int id;
    long long avg_ttl;          /* Average TTL, just for stats */
} redisDb;
```

## 处理超时的键

## 问题
对于设置超时时间的“键值对”，redis是怎么删除已经超时的“键值对”的
1) 定期检查“键值对", 删除超时的
2) 每次被访问时，检查