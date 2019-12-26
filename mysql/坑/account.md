# mysql 创建用户报错
mysql 8.0.11


grant all on test.* to 'admin'@'localhost';
ERROR 1410 (42000): You are not allowed to create a user with GRANT

解决方法：
create user 'admin'@'localhost';
grant all on test.* to 'admin'@'localhost';

