# TIME_TO_SEC的坑

笔者负责的APP运营后台有个定时推送通知的功能，运营的同事使用的时候配置了两条推送通知，一条是今天19点推送，另一条是明天19点推送。等到了19点时，却发现今天和明天的通知都推送出去了。推送通知是放在mysql数据库里面的，后台使用定时任务每隔几分钟去数据库查询一次，通知时间在当前时间前后3分钟之内都算是有效的。sql语句如下

~~~sql
SELECT * FROM `notice`  WHERE (status=1 and ABS(TIME_TO_SEC(now()) - TIME_TO_SEC(notice_time)) < '180')
 ORDER BY `id` LIMIT 10 OFFSET 0
~~~



估摸着可能是TIME_TO_SEC有问题，查看select TIME_TO_SEC(NOW())的值果然不对。原来TIME_TO_SEC只是将日期部分的时，分，秒换算成对应的秒。而不是整个日期，将TIME_TO_SEC换成UNIX_TIMESTAMP就可以了

~~~sql
SELECT * FROM `notice`  WHERE (status=1 and ABS(UNIX_TIMESTAMP(now()) - UNIX_TIMESTAMP(notice_time)) < '180') ORDER BY `id` LIMIT 10 OFFSET 0
~~~

