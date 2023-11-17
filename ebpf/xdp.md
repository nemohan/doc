# xdp

[TOC]



## xdp程序挂载及卸载

### 使用iproute2 

iproute2实际使用的netlink挂载xdp程序

~~~bash
ip link set dev enp0s8 xdp obj program.o sec mysection
~~~

卸载

~~~
ip link set dev enp0s8 xdp off
~~~



### golang使用netlink挂载

~~~go
import(
    	"github.com/vishvananda/netlink"
	"github.com/cilium/ebpf"
)
func attachXDP(){
	spec, err := ebpf.LoadCollectionSpec("xdp_prog_kern.o")
	if err != nil{
		panic(err)
	}

	var objs struct {
		Prog  *ebpf.Program `ebpf:"xdp_stats1_func"`
		Stats *ebpf.Map     `ebpf:"xdp_stats_map"`
	}

	if err := spec.LoadAndAssign(&objs, nil); err != nil {
		panic(err)
	}
	defer objs.Prog.Close()
	defer objs.Stats.Close()

	lo, err := netlink.LinkByName("lo")
	if err != nil{
		panic(err)
	}
	
	if err := netlink.LinkSetXdpFd(lo, objs.Prog.FD()); err != nil{
		panic(err)
	}
}	

~~~



## 代码示例

~~~c
/* SPDX-License-Identifier: GPL-2.0 */
#include <stddef.h>
#include <linux/bpf.h>
#include <linux/in.h>
#include <linux/if_ether.h>
#include <linux/if_packet.h>
#include <linux/ipv6.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <linux/icmpv6.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>

#define MAX_FIVE_TUPLES 1024
/* Header cursor to keep track of current parsing position */
struct hdr_cursor {
	void *pos;
};

struct port_pair{
	__u16 src;
	__u16 dest;
};


struct kv_pair {
	__u32 addr;
	__u32 port;	//port 若使用__u16会导致bpf加载失败
};

struct ip_pair{
	__u32 saddr;
	__u32 daddr;
};

/* Keeps stats per (enum) xdp_action */
struct bpf_map_def SEC("maps") xdp_five_tuples = {
	.type        = BPF_MAP_TYPE_HASH,
    .key_size    = sizeof(__u64),
	.value_size  = sizeof(struct kv_pair),
	.max_entries = MAX_FIVE_TUPLES,
};

/* Packet parsing helpers.
 *
 * Each helper parses a packet header, including doing bounds checking, and
 * returns the type of its contents if successful, and -1 otherwise.
 *
 * For Ethernet and IP headers, the content type is the type of the payload
 * (h_proto for Ethernet, nexthdr for IPv6), for ICMP it is the ICMP type field.
 * All return values are in host byte order.
 */
static __always_inline int parse_ethhdr(struct hdr_cursor *nh,
					void *data_end,
					struct ethhdr **ethhdr)
{
	struct ethhdr *eth = nh->pos;
	int hdrsize = sizeof(*eth);

	/* Byte-count bounds check; check if current pointer + size of header
	 * is after data_end.
	 */
	//if (nh->pos + 1 > data_end)
	if (eth + 1 > data_end)
		return -1;

	nh->pos += hdrsize;
	*ethhdr = eth;

	return eth->h_proto; /* network-byte-order */
}

/* Assignment 2: Implement and use this */
static __always_inline int parse_iphdr(struct hdr_cursor *nh,
					void *data_end,
					struct iphdr **iphdr, struct ip_pair *addrs)
{
	struct iphdr *ip = nh->pos;
	int hdrsize = sizeof(*ip);
	
	//bounds check
	if (ip + 1 > data_end)
		return -1;

	nh->pos += hdrsize;
	*iphdr = ip;
	addrs->saddr = ip->saddr;
	addrs->daddr = ip->daddr;

	return ip->protocol;
}

/*
 * pase_tcphdr parse sorce port and destination port
 * 
 */
static __always_inline int parse_tcphdr(struct hdr_cursor *nh,
					void *data_end,
					 struct port_pair *ports)
{
	struct tcphdr *tcp = nh->pos;
	int hdrsize = sizeof(*tcp);
	
	//bounds check
	if (tcp + 1 > data_end)
		return -1;

	nh->pos += hdrsize;
	//*tcphdr = tcp;
    if ((bpf_ntohs(tcp->source) != 8000) && (bpf_ntohs(tcp->dest) != 8000)){
        return 1; 
    }
    bpf_printk(" s:%d d:%d\n",  bpf_ntohs(tcp->source), bpf_ntohs(tcp->dest));

	ports->src = tcp->source;
	ports->dest = tcp->dest;
	return 0;
}


SEC("xdp_packet_parser")
int  xdp_parser_func(struct xdp_md *ctx)
{
	void *data_end = (void *)(long)ctx->data_end;
	void *data = (void *)(long)ctx->data;
	struct ethhdr *eth;
	struct iphdr *ip;
	struct port_pair ports;
	struct ip_pair addrs;
	struct kv_pair kv ;
	__u64 key = 0;
	

	/* Default action XDP_PASS, imply everything we couldn't parse, or that
	 * we don't want to deal with, we just pass up the stack and let the
	 * kernel deal with it.
	 */
	__u32 action = XDP_PASS; /* Default action */

        /* These keep track of the next header type and iterator pointer */
	struct hdr_cursor nh;
	int nh_type;

	/*
	const int icmp = 1;
	const int icmpv6 = 58;
	*/
	const int tcp = 6;
	/* Start next header cursor position at data start */
	nh.pos = data;

	/* Packet parsing in steps: Get each header one at a time, aborting if
	 * parsing fails. Each helper function does sanity checking (is the
	 * header type in the packet correct?), and bounds checking.
	 */
	nh_type = parse_ethhdr(&nh, data_end, &eth);
	if (nh_type != bpf_htons(ETH_P_IP))
		goto out;
	
	/*
	 * drop icmp packet
	nh_type = parse_iphdr(&nh, data_end, &ip);
	if (nh_type != icmp && nh_type != icmpv6)
		goto out;
	*/
	
	
	nh_type = parse_iphdr(&nh, data_end, &ip, &addrs);
	if (nh_type == tcp){
		if (0 == parse_tcphdr(&nh, data_end, &ports)){
			key = ports.src;
			key = (key <<32) | addrs.saddr;
			kv.port = ports.dest;
			kv.addr = addrs.daddr;
			bpf_map_update_elem(&xdp_five_tuples, &key, &kv, BPF_ANY);
		}
	}	

	/* Assignment additions go below here */

	//action = XDP_DROP;
out:
    return XDP_PASS;
}

char _license[] SEC("license") = "GPL";
~~~



## AF_XDP

AF_XDP是否能捕获本机出向的包，应该也不能

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

### 限制

一个网卡只能挂载一个xdp程序


## 参考

* af_xdp https://www.kernel.org/doc/html/latest/networking/af_xdp.html
* af_xdp http://vger.kernel.org/lpc_net2018_talks/lpc18_paper_af_xdp_perf-v2.pdf
* af_xdp https://lwn.net/Articles/750845/
* af_xdp https://networkbuilders.intel.com/docs/networkbuilders/af-xdp-sockets-high-performance-networking-for-cloud-native-networking-technology-guide.pdf