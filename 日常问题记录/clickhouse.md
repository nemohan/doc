# clickhouse



## 同一个分片之间的副本未同步的问题

同事搭建了一个6个节点的clickhouse集群，包含3个分片，每个分片有两个副本。通过写分布式表即test_all中插入数据时，数据可以写到其中某个分片及其对应的副本上。但是直接写入s1分片的其中一个副本r1时，数据并没有同步到副本r4。

开始没有想到先看看clickhouse日志，走了不少弯路。先去zookeeper上查看了/clickhouse/tables/s1/ncompass_datas/test/replicas 上面保存的元数据，偶然发现了一个"/clickhouse/tables/s1/ncompass_datas/test/replicas/r4/queue/queue-0000000009"的路径，该文件内容如下：

~~~
ormat version: 4
create_time: 2024-06-28 10:42:14
source replica: r1
block_id: all_17783277549191444346_10028290792132357736
get
all_8_8_0
part_type: Compact

~~~

应该跟复制关系比较密切，而且在r1的test表新插入一条数据时，"/clickhouse/tables/s1/ncompass_datas/test/replicas/r4/queue"路径下多了一个"queue-0000000010"的文件。通过queue这个关键词，搜索到了system.replication_queue这个表可以查看副本的复制状态，去r4所在节点上查看该表的内容，看到了如下错误:

~~~
database:               ncompass_datas
table:                  test
replica_name:           r4
position:               6
node_name:              queue-0000000009
type:                   GET_PART
create_time:            2024-06-28 10:42:14
required_quorum:        0
source_replica:         r1
new_part_name:          all_8_8_0
parts_to_merge:         []
is_detach:              0
is_currently_executing: 0
num_tries:              290
last_exception:         Poco::Exception. Code: 1000, e.code() = 0, e.displayText() = Host not found: 01dfc07fee67 (version 21.3.11.5 (official build))
last_attempt_time:      2024-06-28 10:45:19
num_postponed:          0
postpone_reason:        
last_postpone_time:     1970-01-01 08:00:00
merge_type:             



~~~

异常信息"Host not found: 01dfc07fee67"显示 r4主机尝试从r1获取数据时， 解析主机名"01dfc07fee67"对应的ip地址失败，这个主机名正是r1的主机名。将主机名和其ip地址添加到r4主机的/etc/hosts 文件，成功解决了副本之间不同步的问题(还需开放9009端口)

以下是分布式表、以及分片s1对应的两个副本上的表的表结构

分布式表:

~~~sql
CREATE TABLE ncompass_datas.test_all
(
    `id` UInt32,
    `value` String
)
ENGINE = Distributed('ncompass_cluster', 'ncompass_datas', 'test', rand())
~~~

分片s1 对应的副本r1:

~~~c
CREATE TABLE ncompass_datas.test
(
    `id` UInt32,
    `value` String
)
ENGINE = ReplicatedMergeTree('/clickhouse/tables/s1/ncompass_datas/test', 'r1')
ORDER BY id
SETTINGS index_granularity = 8192
~~~

分片s1对应的副本r2:

~~~sql
CREATE TABLE ncompass_datas.test
(
    `id` UInt32,
    `value` String
)
ENGINE = ReplicatedMergeTree('/clickhouse/tables/s1/ncompass_datas/test', 'r4')
ORDER BY id
SETTINGS index_granularity = 8192
~~~

### 解决思路

* 看clickhouse日志
* 查看system.replication_queue查看副本上的复制状态

查看副本的复制状态:

~~~sql
SELECT * FROM system.replication_queue FORMAT Vertical;

~~~

