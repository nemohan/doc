# statistics collector 进程 

[TOC]

postgreSQL's 的statistics collector 进程用于收集和报告服务器的活动。





### 配置项

| 配置项               | 默认值                 | 备注 |
| -------------------- | ---------------------- | ---- |
| stats_temp_directory | 存放统计信息的临时目录 |      |
|                      |                        |      |
|                      |                        |      |



## 启动过程

postmaster调用pgstat_init函数执行一些pg_stat进程启动之前的初始化工作。主要包括以下几点：

- 创建收集统计信息的udp socket。期间会通过发送信息测试 socket是否可用。创建的socket保存在全局变量**pgStatSock**中

pg_stat进程入口函数PgstatCollectorMain 位于postmaster/Pgstat.c文件。主要工作包括以下几点:

* 设置信号量处理函数
* 设置全局变量**pgStatRunningInCollector**为true
* 调用pgstat_read_statsfiles读取已有的统计信息文件或初始化统计信息。已有的统计信息文件存储在pg_stat/global.stat文件中。pgstat_read_statsfiles会创建并设置当前的内存上下问为**pgStatLocalContext**; 创建保存统计信息的哈希表**pgStatDBHash**；清零保存统计信息的结构体**globalStats**和**archiverStats**；从vfd模块打开统计信息文件；读取统计信息文件，读取的内容包含以下几部分: 1)格式id 2)globalStats 3）archiverStats 4)读取PgStat_StatDBEntry 存入之前创建的哈希表中



**globalStats**的定义:

~~~c
/*
 * Global statistics kept in the stats collector
 */
typedef struct PgStat_GlobalStats
{
	TimestampTz stats_timestamp;	/* time of stats file update */
	PgStat_Counter timed_checkpoints;
	PgStat_Counter requested_checkpoints;
	PgStat_Counter checkpoint_write_time;	/* times in milliseconds */
	PgStat_Counter checkpoint_sync_time;
	PgStat_Counter buf_written_checkpoints;
	PgStat_Counter buf_written_clean;
	PgStat_Counter maxwritten_clean;
	PgStat_Counter buf_written_backend;
	PgStat_Counter buf_fsync_backend;
	PgStat_Counter buf_alloc;
	TimestampTz stat_reset_timestamp;
} PgStat_GlobalStats;
~~~



**archiverStats**的定义如下:

~~~c
typedef struct PgStat_ArchiverStats
{
	PgStat_Counter archived_count;	/* archival successes */
	char		last_archived_wal[MAX_XFN_CHARS + 1];	/* last WAL file
														 * archived */
	TimestampTz last_archived_timestamp;	/* last archival success time */
	PgStat_Counter failed_count;	/* failed archival attempts */
	char		last_failed_wal[MAX_XFN_CHARS + 1]; /* WAL file involved in
													 * last failure */
	TimestampTz last_failed_timestamp;	/* last archival failure time */
	TimestampTz stat_reset_timestamp;
} PgStat_ArchiverStats;
~~~



PgStat_StatDBEntry的定义:

~~~c
/* ------------------------------------------------------------
 * Statistic collector data structures follow
 *
 * PGSTAT_FILE_FORMAT_ID should be changed whenever any of these
 * data structures change.
 * ------------------------------------------------------------
 */

#define PGSTAT_FILE_FORMAT_ID	0x01A5BC9D

/* ----------
 * PgStat_StatDBEntry			The collector's data per database
 * ----------
 */
typedef struct PgStat_StatDBEntry
{
	Oid			databaseid;
	PgStat_Counter n_xact_commit;
	PgStat_Counter n_xact_rollback;
	PgStat_Counter n_blocks_fetched;
	PgStat_Counter n_blocks_hit;
	PgStat_Counter n_tuples_returned;
	PgStat_Counter n_tuples_fetched;
	PgStat_Counter n_tuples_inserted;
	PgStat_Counter n_tuples_updated;
	PgStat_Counter n_tuples_deleted;
	TimestampTz last_autovac_time;
	PgStat_Counter n_conflict_tablespace;
	PgStat_Counter n_conflict_lock;
	PgStat_Counter n_conflict_snapshot;
	PgStat_Counter n_conflict_bufferpin;
	PgStat_Counter n_conflict_startup_deadlock;
	PgStat_Counter n_temp_files;
	PgStat_Counter n_temp_bytes;
	PgStat_Counter n_deadlocks;
	PgStat_Counter n_block_read_time;	/* times in microseconds */
	PgStat_Counter n_block_write_time;

	TimestampTz stat_reset_timestamp;
	TimestampTz stats_timestamp;	/* time of db stats file update */

	/*
	 * tables and functions must be last in the struct, because we don't write
	 * the pointers out to the stats file.
	 */
	HTAB	   *tables;
	HTAB	   *functions;
} PgStat_StatDBEntry;
~~~



## 统计信息文件格式

格式id | globalStats | archiverStats |  字符'D' | PgStat_StatDBEntry | 字符'D'| PgStat_StatDBEntry |...| 'E'结束字符

