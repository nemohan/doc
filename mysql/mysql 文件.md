# mysql 的文件

### 文件类型

![image-20191225093833684](E:\doc\mysql\${img}\image-20191225093833684.png)

#### 配置文件(参数文件)

![image-20191225094005347](E:\doc\mysql\${img}\image-20191225094005347.png)

查看配置参数的命令:

~~~mysql
show variables like "innodb_buffer%" \G;
~~~

![image-20191225094502054](E:\doc\mysql\${img}\image-20191225094502054.png)

##### 参数类型

![image-20191225094639296](E:\doc\mysql\${img}\image-20191225094639296.png)

静态变量可以在配置文件中修改。动态变量修改后，在数据库重启之后会失效

##### 常见的参数

datadir 数据文件存放路径



#### 日志文件

日志文件的种类:

* 错误日志(error log)
* 慢查询日志 (binlog)
* 二进制日志(slow query log)
* 查询日志(log)

##### 错误日志

![image-20191225100743386](E:\doc\mysql\${img}\image-20191225100743386.png)

##### 慢查询日志

![image-20191225102910374](E:\doc\mysql\${img}\image-20191225102910374.png)

![image-20191225103054794](E:\doc\mysql\${img}\image-20191225103054794.png)

![image-20191225103225501](E:\doc\mysql\${img}\image-20191225103225501.png)

mysql 5.1开始可以将慢查询日志放入mysql.slow_log表中。全局变量log_output指定了慢查询日志输出的位置。若值为FILE则慢查询日志输出到文件，若为TABLE则输出到slow_log表中。

slow_log表使用的引擎是CSV引擎，对大数据量下的查询效率不高，可以把引擎转为MyISAM,并在start_time列上添加索引。

InnoSQL版本加强了对于SQL语句的捕获方式。在原版本MYSQL的基础上在slow log中增加了对于逻辑读取(logical reads)和物理读取(physical reads)的统计。这里的物理读取是指从磁盘进行IO读取的次数。逻辑读取包含所有的读取，包括磁盘和缓冲池

![image-20191225104224719](E:\doc\mysql\${img}\image-20191225104224719.png)

##### 查询日志

查询日志记录立所有对MySQL数据库请求的信息，无论请求是否正确执行。默认文件名为: 主机名.log

##### 二进制日志

![image-20191225104651924](E:\doc\mysql\${img}\image-20191225104651924.png)

通过配置变量log_bin 可以启动二进制日志。如果不指定文件名，则默认二进制文件名为主机名，后缀名为二进制日志的序列号如mysql-bin.000004。bin_log.index文件中存放了已经生成的二进制日志文件名

二进制日志的作用:

![image-20191225104917204](E:\doc\mysql\${img}\image-20191225104917204.png)

影响二进制日志文件的一些参数:

* max_binlog_size
* binlog_cache_size
* sync_binlog
* binlog-do-db
* binlog-ignore-db
* log-slave-update
* binlog_format

![image-20191225105908966](E:\doc\mysql\${img}\image-20191225105908966.png)

![image-20191225110152570](E:\doc\mysql\${img}\image-20191225110152570.png)

![image-20191225110217237](E:\doc\mysql\${img}\image-20191225110217237.png)

![image-20191225110254044](E:\doc\mysql\${img}\image-20191225110254044.png)

#### 套接字文件

UNIX 系统下本地连接MySQL可以采用UNIX套接字方式，这种方式需要套接字文件。由变量socket控制，一般放在/tmp目录下，查看套接字文件的路径: show variables like "socket" \G;

#### pid 文件

存放当前数据库实例的进程id

#### 表结构文件

不管使用哪种存储引擎，都有一个以frm为后缀名的文件，这个文件记录了该表的表结构定义或视图定义（文本文件)。

#### InnoDB存储引擎文件

##### 表空间文件

![image-20191225111303455](E:\doc\mysql\${img}\image-20191225111303455.png)

##### 重做文件