

# docker 容器收不到流量的问题

[TOC]

同事去客户那里做产品升级后(docker也升级了)，有一个接收syslog(udp流量，端口30001)的容器服务接收不到流量了，但这个容器的其他的udp目的端口还可以接收到流量。经过下面一系列的检查:

1) 容器监听端口正常

2）宿主机监听端口正常

3）宿主机能收到这个端口的流量

4) iptables配置正常

5）conntrack是否正常

确定是宿主机收到流量后，流量未能到达容器，然后又检查了iptables、conntrack、反向路径过滤都没有问题。最后我想起了查看/var/log/messages果然看到了该端口的错误信息。



下图是容器的nat规则，可以看到30001端口的规则未命中任何流量。同一个容器的30003端口则命中了流量

![image-20260313105351234](D:\个人笔记\doc\网络\docker容器收不到流量的问题.assets\image-20260313105351234.png)





/var/log/messages中有端口30001的错误信息



![image-20260313111309111](D:\个人笔记\doc\网络\docker容器收不到流量的问题.assets\image-20260313111309111.png)





对30001端口施行禁止跟踪后，容器可以收到流量了

iptables -t raw -A PREROUTING -p udp --dport 30001 -j NOTRACK
iptables -t raw -A OUTPUT -p udp --sport 30001 -j NOTRACK



## 可能会影响流量的一些系统配置

### 反向路径过滤

反向路径过滤（RP Filter）是一种机制，它可以帮助防止IP欺骗攻击。在Linux中，可以通过`ip_rp_filter`内核参数来启用或配置反向路径过滤。

~~~
sysctl net.ipv4.conf.all.rp_filter
sysctl net.ipv4.conf.p3p1.rp_filter
~~~



### conntrack

系统的连接跟踪模块

检查conntrack表状态

~~~
# 查看当前条目数 vs 最大值
conntrack -C
sysctl net.netfilter.nf_conntrack_count
sysctl net.netfilter.nf_conntrack_max
~~~



若conntrack表已满，扩容:

~~~
# 临时生效
sysctl -w net.netfilter.nf_conntrack_max=262144

# 永久生效
echo "net.netfilter.nf_conntrack_max=262144" >> /etc/sysctl.conf
sysctl -p
~~~



手动删除指定端口的连接跟踪记录:

~~~
conntrack -D -p udp --dport 30001
~~~



缩短UDP conntrack超时

~~~
# 默认 180s，高流量场景建议降低
sysctl -w net.netfilter.nf_conntrack_udp_timeout=30
sysctl -w net.netfilter.nf_conntrack_udp_timeout_stream=60
~~~





### iptables配置

查看

~~~
iptables -t nat -n -v
~~~



添加日志排查

~~~
# ====== PREROUTING (数据包刚到达，NAT之前) ======
iptables -t raw -I PREROUTING -p udp --dport 30001 -j LOG --log-prefix "[RAW-PRE-30001] " --log-level 4
iptables -t nat -I PREROUTING -p udp --dport 30001 -j LOG --log-prefix "[NAT-PRE-30001] " --log-level 4

# ====== INPUT (进入本机协议栈) ======
iptables -t filter -I INPUT -p udp --dport 30001 -j LOG --log-prefix "[INPUT-30001] " --log-level 4

# ====== FORWARD (转发到容器/其他网卡) ======
iptables -t filter -I FORWARD -p udp --dport 30001 -j LOG --log-prefix "[FORWARD-30001] " --log-level 4

# ====== DOCKER-USER (Docker自定义链，如果存在) ======
iptables -t filter -I DOCKER-USER -p udp --dport 30001 -j LOG --log-prefix "[DOCKER-USER-30001] " --log-level 4 2>/dev/null

# ====== POSTROUTING (离开本机之前) ======

iptables -t nat -I POSTROUTING -p udp --dport 30001 -j LOG --log-prefix "[NAT-POST-30001] " --log-level 4



iptables -t raw -D PREROUTING -p udp --dport 30001 -j LOG --log-prefix "[RAW-PRE-30001] " --log-level 4
iptables -t nat -D PREROUTING -p udp --dport 30001 -j LOG --log-prefix "[NAT-PRE-30001] " --log-level 4
iptables -t filter -D INPUT -p udp --dport 30001 -j LOG --log-prefix "[INPUT-30001] " --log-level 4
iptables -t filter -D FORWARD -p udp --dport 30001 -j LOG --log-prefix "[FORWARD-30001] " --log-level 4
iptables -t filter -D DOCKER-USER -p udp --dport 30001 -j LOG --log-prefix "[DOCKER-USER-30001] " --log-level 4 2>/dev/null
iptables -t nat -D POSTROUTING -p udp --dport 30001 -j LOG --log-prefix "[NAT-POST-30001] " --log-level 4

~~~



### 防火墙



## 总结

1 确定是系统问题后，检查一下/var/log/messages或许会有意外收获

2 按一个方向排查，如自顶向下或自底向上，不要跳来跳去。否则会浪费不少时间



