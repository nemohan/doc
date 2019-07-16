# 高性能mysql 6  查询优化



## COUNT()

若存储引擎是myISAM, 并且没有WHERE 限制条件。count(*)统计表的行数是个常量。因为myISAM引擎已经存储了当前表的行数

其他方式: 用其他表来存储类似COUNT()的统计信息

## JOIN





## LIMIT and OFFSET()

SELECT * FROM table1 LIMIT 100 OFFSET 10000; 

这种语句会导致sql查询10100条结果然后丢弃掉前面的10000条数据。

两种方式可以优化类似语句:

SELECT * FROM table1 WHERE id < 1000  LIMIT 100 order by id;



~~~sql
 
 方式2： film_id上有索引
 SELECT film.film_id, film.description
-> FROM sakila.film
-> INNER JOIN (
-> SELECT film_id FROM sakila.film
-> ORDER BY title LIMIT 50, 5
-> ) AS lim USING(film_id);
~~~





