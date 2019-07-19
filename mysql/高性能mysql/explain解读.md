# explain解读

~~~mysql
mysql> explain select * from weibo_id \G
*************************** 1. row ***************************
           id: 1
  select_type: SIMPLE
        table: weibo_id
         type: ALL
possible_keys: NULL
          key: NULL
      key_len: NULL
          ref: NULL
         rows: 5
        Extra: NULL
1 row in set (0.00 sec)

Extra: using where 代表在server端而不是在存储引擎端使用where条件过滤了不符合条件的数据
Extra: using index 代表使用了覆盖索引
rows: 代表最终的结果集有多少行， 还是为了得到结果集mysql处理了多少行
key: 代表使用的索引
type: ?
~~~

