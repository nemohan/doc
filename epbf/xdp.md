# xdp

[TOC]



## xdp程序挂载及卸载

### 使用iproute2 

~~~bash
ip link set dev enp0s8 xdp obj program.o sec mysection
~~~

卸载

~~~
ip link set dev enp0s8 xdp off
~~~



## AF_XDP

AF_XDP是否能捕获本机出向的包

头文件: linux/if_xdp.h



## xdp单元测试

BPF_PROG_TEST_RUN

## 注意

XDP只能看到进入网卡的包，从本机出去的包看不到(lo 网卡是个例外)

## 应用

* 网络监控

* 缓解Ddos攻击，将非法数据包进入内核协议栈之前丢弃，减少CPU消耗

* 负载均衡

* 防火墙


## 参考

* af_xdp https://www.kernel.org/doc/html/latest/networking/af_xdp.html
* af_xdp http://vger.kernel.org/lpc_net2018_talks/lpc18_paper_af_xdp_perf-v2.pdf
* af_xdp https://lwn.net/Articles/750845/
* af_xdp https://networkbuilders.intel.com/docs/networkbuilders/af-xdp-sockets-high-performance-networking-for-cloud-native-networking-technology-guide.pdf