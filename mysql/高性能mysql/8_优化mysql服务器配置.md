# 8 优化服务器配置

首先考虑索引、查询语句的问题、优化服务器配置是最后（除非必须)才考虑的

#### 1 找到配置mysql的配置文件

在类*nix系统上，一般在/etc/my.cnf 或/etc/mysql/my.cnf

在不能确定配置文件位置的情况下，可以执行如下命令:

~~~shell
$ which mysqld
/usr/sbin/mysqld
$/usr/sbin/mysqld --verbose --help | grep -A 1 'Default options'
~~~



