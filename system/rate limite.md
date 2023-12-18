# rate limit

[TOC]

## rate limit 算法

### Token bucket

看看golang.org/x/time/rate是如何实现的

### Leaky bucket



## concurrency limit

控制并发数能否使用 rate limiter，应该不能。rate limit的目的是保持一个平稳的速率，时间相关。并发控制则不然。例如想控制对数据库的并发访问数目，只要并发数目达到阈值，无论多久，新的访问请求都无法处理

## 参考

* golang.org/x/time/rate
* [github.com/uber-go/ratelimit](https://github.com/uber-go/ratelimit)