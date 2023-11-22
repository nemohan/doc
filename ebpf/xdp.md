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

### 使用bpftool

~~~bash
strace bpftool net attach xdpgeneric id 796 dev lo
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



### 内核xdp安装过程

~~~c
static int generic_xdp_install(struct net_device *dev, struct netdev_bpf *xdp)
{
	struct bpf_prog *old = rtnl_dereference(dev->xdp_prog);
	struct bpf_prog *new = xdp->prog;
	int ret = 0;

	switch (xdp->command) {
	case XDP_SETUP_PROG:
		rcu_assign_pointer(dev->xdp_prog, new);
		if (old)
			bpf_prog_put(old);

		if (old && !new) {
			static_branch_dec(&generic_xdp_needed_key);
		} else if (new && !old) {
			static_branch_inc(&generic_xdp_needed_key);
			dev_disable_lro(dev);
			dev_disable_gro_hw(dev);
		}
		break;

	case XDP_QUERY_PROG:
		xdp->prog_id = old ? old->aux->id : 0;
		break;

	default:
		ret = -EINVAL;
		break;
	}

	return ret;
}
~~~



### 内核中xdp执行流程

~~~c
static int __netif_receive_skb_core(struct sk_buff **pskb, bool pfmemalloc,
				    struct packet_type **ppt_prev)
{
	struct packet_type *ptype, *pt_prev;
	rx_handler_func_t *rx_handler;
	struct sk_buff *skb = *pskb;
	struct net_device *orig_dev;
	bool deliver_exact = false;
	int ret = NET_RX_DROP;
	__be16 type;

	net_timestamp_check(!READ_ONCE(netdev_tstamp_prequeue), skb);

	trace_netif_receive_skb(skb);

	orig_dev = skb->dev;

	skb_reset_network_header(skb);
	if (!skb_transport_header_was_set(skb))
		skb_reset_transport_header(skb);
	skb_reset_mac_len(skb);

	pt_prev = NULL;

another_round:
	skb->skb_iif = skb->dev->ifindex;

	__this_cpu_inc(softnet_data.processed);

	if (static_branch_unlikely(&generic_xdp_needed_key)) {
		int ret2;

		preempt_disable();
		ret2 = do_xdp_generic(rcu_dereference(skb->dev->xdp_prog), skb);
        
        ......
        ......
            
    }
~~~



~~~c
int do_xdp_generic(struct bpf_prog *xdp_prog, struct sk_buff *skb)
{
	if (xdp_prog) {
		struct xdp_buff xdp;
		u32 act;
		int err;

		act = netif_receive_generic_xdp(skb, &xdp, xdp_prog);
		if (act != XDP_PASS) {
			switch (act) {
			case XDP_REDIRECT:
				err = xdp_do_generic_redirect(skb->dev, skb,
							      &xdp, xdp_prog);
				if (err)
					goto out_redir;
				break;
			case XDP_TX:
				generic_xdp_tx(skb, xdp_prog);
				break;
			}
			return XDP_DROP;
		}
	}
	return XDP_PASS;
out_redir:
	kfree_skb(skb);
	return XDP_DROP;
}
~~~



~~~c
void generic_xdp_tx(struct sk_buff *skb, struct bpf_prog *xdp_prog)
{
	struct net_device *dev = skb->dev;
	struct netdev_queue *txq;
	bool free_skb = true;
	int cpu, rc;

	txq = netdev_core_pick_tx(dev, skb, NULL);
	cpu = smp_processor_id();
	HARD_TX_LOCK(dev, txq, cpu);
	if (!netif_xmit_stopped(txq)) {
		rc = netdev_start_xmit(skb, dev, txq, 0);
		if (dev_xmit_complete(rc))
			free_skb = false;
	}
	HARD_TX_UNLOCK(dev, txq);
	if (free_skb) {
		trace_xdp_exception(dev, xdp_prog, XDP_TX);
		kfree_skb(skb);
	}
}
~~~



~~~c
static u32 netif_receive_generic_xdp(struct sk_buff *skb,
				     struct xdp_buff *xdp,
				     struct bpf_prog *xdp_prog)
{
	struct netdev_rx_queue *rxqueue;
	void *orig_data, *orig_data_end;
	u32 metalen, act = XDP_DROP;
	__be16 orig_eth_type;
	struct ethhdr *eth;
	bool orig_bcast;
	int hlen, off;
	u32 mac_len;

	/* Reinjected packets coming from act_mirred or similar should
	 * not get XDP generic processing.
	 */
	if (skb_is_redirected(skb))
		return XDP_PASS;

	/* XDP packets must be linear and must have sufficient headroom
	 * of XDP_PACKET_HEADROOM bytes. This is the guarantee that also
	 * native XDP provides, thus we need to do it here as well.
	 */
	if (skb_cloned(skb) || skb_is_nonlinear(skb) ||
	    skb_headroom(skb) < XDP_PACKET_HEADROOM) {
		int hroom = XDP_PACKET_HEADROOM - skb_headroom(skb);
		int troom = skb->tail + skb->data_len - skb->end;

		/* In case we have to go down the path and also linearize,
		 * then lets do the pskb_expand_head() work just once here.
		 */
		if (pskb_expand_head(skb,
				     hroom > 0 ? ALIGN(hroom, NET_SKB_PAD) : 0,
				     troom > 0 ? troom + 128 : 0, GFP_ATOMIC))
			goto do_drop;
		if (skb_linearize(skb))
			goto do_drop;
	}

	/* The XDP program wants to see the packet starting at the MAC
	 * header.
	 */
	mac_len = skb->data - skb_mac_header(skb);
	hlen = skb_headlen(skb) + mac_len;
	xdp->data = skb->data - mac_len;
	xdp->data_meta = xdp->data;
	xdp->data_end = xdp->data + hlen;
	xdp->data_hard_start = skb->data - skb_headroom(skb);
	orig_data_end = xdp->data_end;
	orig_data = xdp->data;
	eth = (struct ethhdr *)xdp->data;
	orig_bcast = is_multicast_ether_addr_64bits(eth->h_dest);
	orig_eth_type = eth->h_proto;

	rxqueue = netif_get_rxqueue(skb);
	xdp->rxq = &rxqueue->xdp_rxq;

	act = bpf_prog_run_xdp(xdp_prog, xdp);

	/* check if bpf_xdp_adjust_head was used */
	off = xdp->data - orig_data;
	if (off) {
		if (off > 0)
			__skb_pull(skb, off);
		else if (off < 0)
			__skb_push(skb, -off);

		skb->mac_header += off;
		skb_reset_network_header(skb);
	}

	/* check if bpf_xdp_adjust_tail was used. it can only "shrink"
	 * pckt.
	 */
	off = orig_data_end - xdp->data_end;
	if (off != 0) {
		skb_set_tail_pointer(skb, xdp->data_end - xdp->data);
		skb->len -= off;

	}

	/* check if XDP changed eth hdr such SKB needs update */
	eth = (struct ethhdr *)xdp->data;
	if ((orig_eth_type != eth->h_proto) ||
	    (orig_bcast != is_multicast_ether_addr_64bits(eth->h_dest))) {
		__skb_push(skb, ETH_HLEN);
		skb->protocol = eth_type_trans(skb, skb->dev);
	}

	switch (act) {
	case XDP_REDIRECT:
	case XDP_TX:
		__skb_push(skb, mac_len);
		break;
	case XDP_PASS:
		metalen = xdp->data - xdp->data_meta;
		if (metalen)
			skb_metadata_set(skb, metalen);
		break;
	default:
		bpf_warn_invalid_xdp_action(act);
		/* fall through */
	case XDP_ABORTED:
		trace_xdp_exception(skb->dev, xdp_prog, act);
		/* fall through */
	case XDP_DROP:
	do_drop:
		kfree_skb(skb);
		break;
	}

	return act;
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

### 工作原理

以AF_XDP 地址协议簇调用socket()，生成一个socket文件描述符用于移动数据包。 首先，在用户态创建一块内存"UMEM"，它是一块连续的内存区域，被分成大小相等的"frames"(每个frame的大小可有调用者指定)，每个frame存储一个数据包。UMEM如下图所示:

![image-20231120154717527](D:\个人笔记\doc\ebpf\xdp.assets\image-20231120154717527.png)

UMEM分配好之后，通过系统调用setsocketopt()并使用XDP_UMEM_REG命令将socket和UMEM绑定在一起

在UMEM的每个frame所在的整数索引被称作"descriptor"(描述符)。为了使用这些描述符，应用程序使用命令XDP_UMEM_FILL_QUEUE 和setsockopt() 创建一个被称作"fill queue"的循环队列，然后这个队列可以使用mmap()被映射到用户态内存区域。应用程序可以通过将frame 的descriptor放到"fill queue"中请求内核将接收到的数据包放到指定的位于UMEM数组的frame中。

![image-20231120155450334](D:\个人笔记\doc\ebpf\xdp.assets\image-20231120155450334.png)

一旦descriptor放到"fill queue"中，内核就拥有对应的frame的使用权。将descriptor归还应用程序需要用到另一个队列"receive queue"，可以使用XDP_RX_QUEUE 和setsockopt()来创建。该队列也会被映射到用户空间的内存区域；一旦frame被放入数据包，对应的descriptor就会被放到 "receive queue"。可以调用poll()来等待数据包到达receive queue

![image-20231120160346037](D:\个人笔记\doc\ebpf\xdp.assets\image-20231120160346037.png)

在发送端有着类似的过程。应用程序使用XDP_TX_QUEUE创建发送队列 "TX queue"并映射到用户空间；将准备发送的数据包的descriptor放到"TX queue"中。调用sendmsg通知内核一个或多个descriptor准备就绪。数据包发送完成后，内核会将对应的descriptor放到"completion queue"(使用XDP_UMEM_COMPLETION_QUEUE创建)中。真个结构如下图

![image-20231120160010773](D:\个人笔记\doc\ebpf\xdp.assets\image-20231120160010773.png)

整个数据结构的设计使得在内核和用户空间零拷贝(zero-copy)移动数据包成为可能。由于descriptor可以用于接收或发送数据包，也允许收到的包无需拷贝的情况下重新传输。

UMEM 数组可以在多个进程间共享，如果一个进程想创建一个AF_XDP socket和现有的UMEM绑定，只需要将socket file descriptor 和拥有UMEM的socket一起传给bind()即可；第二个socket的file descriptor放到sockaddr_xdp结构sxdp_shared_umem_fd 中。不管有多少进程使用一个UMEM，只有一个"fill queue"和一个"completion queue"和UMEM关联。换句话说，在多进程使用配置中，预期一个进程（线程) 只负责管理UMEM frames，其他负责处理数据包相关的任务

内核是如何确定将收到的数据包放到哪个"receive queue"中的呢？有两方面：1）BPF_MAP_TYPE_XSKMAP类型的map，这种类型map是一个数组，每个元素可以包含一个AF_XDP socket。使用UMEM的进程可以通过系统调用bpf() 将socket file descriptor放到map中；2） 需要加载一个xdp类型的bpf程序，负责将包发到map中包含的socket

### libbpf 中AF_XDP相关代码

~~~c
struct xsk_umem {
	struct xsk_ring_prod *fill;
	struct xsk_ring_cons *comp;
	char *umem_area;
	struct xsk_umem_config config;
	int fd;
	int refcount;
};

struct xdp_ring_offset {
	__u64 producer;
	__u64 consumer;
	__u64 desc;
	__u64 flags;
};

struct xdp_mmap_offsets {
	struct xdp_ring_offset rx;
	struct xdp_ring_offset tx;
	struct xdp_ring_offset fr; /* Fill */
	struct xdp_ring_offset cr; /* Completion */
};

/* Do not access these members directly. Use the functions below. */
#define DEFINE_XSK_RING(name) \
struct name { \
	__u32 cached_prod; \
	__u32 cached_cons; \
	__u32 mask; \
	__u32 size; \
	__u32 *producer; \
	__u32 *consumer; \
	void *ring; \
	__u32 *flags; \
}

DEFINE_XSK_RING(xsk_ring_prod);
DEFINE_XSK_RING(xsk_ring_cons);
~~~



#### 设置umem

~~~c
int xsk_umem__create_v0_0_4(struct xsk_umem **umem_ptr, void *umem_area,
			    __u64 size, struct xsk_ring_prod *fill,
			    struct xsk_ring_cons *comp,
			    const struct xsk_umem_config *usr_config)
{
	struct xdp_mmap_offsets off;
	struct xdp_umem_reg mr;
	struct xsk_umem *umem;
	void *map;
	int err;

	if (!umem_area || !umem_ptr || !fill || !comp)
		return -EFAULT;
	if (!size && !xsk_page_aligned(umem_area))
		return -EINVAL;

	umem = calloc(1, sizeof(*umem));
	if (!umem)
		return -ENOMEM;

	umem->fd = socket(AF_XDP, SOCK_RAW, 0);
	if (umem->fd < 0) {
		err = -errno;
		goto out_umem_alloc;
	}

	umem->umem_area = umem_area;
	xsk_set_umem_config(&umem->config, usr_config);

	memset(&mr, 0, sizeof(mr));
	mr.addr = (uintptr_t)umem_area;
	mr.len = size;
	mr.chunk_size = umem->config.frame_size;
	mr.headroom = umem->config.frame_headroom;
	mr.flags = umem->config.flags;

	err = setsockopt(umem->fd, SOL_XDP, XDP_UMEM_REG, &mr, sizeof(mr));
	if (err) {
		err = -errno;
		goto out_socket;
	}
    //fill_size 默认XSK_RING_PROD__DEFAULT_NUM_DESCS  2048
	err = setsockopt(umem->fd, SOL_XDP, XDP_UMEM_FILL_RING,
			 &umem->config.fill_size,
			 sizeof(umem->config.fill_size));
	if (err) {
		err = -errno;
		goto out_socket;
	}
    
    //comp_size默认2048
	err = setsockopt(umem->fd, SOL_XDP, XDP_UMEM_COMPLETION_RING,
			 &umem->config.comp_size,
			 sizeof(umem->config.comp_size));
	if (err) {
		err = -errno;
		goto out_socket;
	}

	err = xsk_get_mmap_offsets(umem->fd, &off);
	if (err) {
		err = -errno;
		goto out_socket;
	}

    //设置存储frame descriptor的 FILL QUEUE
	map = mmap(NULL, off.fr.desc + umem->config.fill_size * sizeof(__u64),
		   PROT_READ | PROT_WRITE, MAP_SHARED | MAP_POPULATE, umem->fd,
		   XDP_UMEM_PGOFF_FILL_RING);
	if (map == MAP_FAILED) {
		err = -errno;
		goto out_socket;
	}

	umem->fill = fill;
	fill->mask = umem->config.fill_size - 1;
	fill->size = umem->config.fill_size;
	fill->producer = map + off.fr.producer;
	fill->consumer = map + off.fr.consumer;
	fill->flags = map + off.fr.flags;
	fill->ring = map + off.fr.desc;
	fill->cached_cons = umem->config.fill_size;

	map = mmap(NULL, off.cr.desc + umem->config.comp_size * sizeof(__u64),
		   PROT_READ | PROT_WRITE, MAP_SHARED | MAP_POPULATE, umem->fd,
		   XDP_UMEM_PGOFF_COMPLETION_RING);
	if (map == MAP_FAILED) {
		err = -errno;
		goto out_mmap;
	}

	umem->comp = comp;
	comp->mask = umem->config.comp_size - 1;
	comp->size = umem->config.comp_size;
	comp->producer = map + off.cr.producer;
	comp->consumer = map + off.cr.consumer;
	comp->flags = map + off.cr.flags;
	comp->ring = map + off.cr.desc;

	*umem_ptr = umem;
	return 0;

out_mmap:
	munmap(map, off.fr.desc + umem->config.fill_size * sizeof(__u64));
out_socket:
	close(umem->fd);
out_umem_alloc:
	free(umem);
	return err;
}
~~~

#### 设置socket

~~~c
struct xsk_socket_config {
	__u32 rx_size;
	__u32 tx_size;
	__u32 libbpf_flags;
	__u32 xdp_flags;
	__u16 bind_flags;
};

struct xsk_socket {
	struct xsk_ring_cons *rx;
	struct xsk_ring_prod *tx;
	__u64 outstanding_tx;
	struct xsk_umem *umem;
	struct xsk_socket_config config;
	int fd;
	int ifindex;
	int prog_fd;
	int xsks_map_fd;
	__u32 queue_id;
	char ifname[IFNAMSIZ];
};

int xsk_socket__create(struct xsk_socket **xsk_ptr, const char *ifname,
		       __u32 queue_id, struct xsk_umem *umem,
		       struct xsk_ring_cons *rx, struct xsk_ring_prod *tx,
		       const struct xsk_socket_config *usr_config)
{
	void *rx_map = NULL, *tx_map = NULL;
	struct sockaddr_xdp sxdp = {};
	struct xdp_mmap_offsets off;
	struct xsk_socket *xsk;
	int err;

	if (!umem || !xsk_ptr || !(rx || tx))
		return -EFAULT;

	xsk = calloc(1, sizeof(*xsk));
	if (!xsk)
		return -ENOMEM;

	err = xsk_set_xdp_socket_config(&xsk->config, usr_config);
	if (err)
		goto out_xsk_alloc;

	if (umem->refcount &&
	    !(xsk->config.libbpf_flags & XSK_LIBBPF_FLAGS__INHIBIT_PROG_LOAD)) {
		pr_warn("Error: shared umems not supported by libbpf supplied XDP program.\n");
		err = -EBUSY;
		goto out_xsk_alloc;
	}

	if (umem->refcount++ > 0) {
		xsk->fd = socket(AF_XDP, SOCK_RAW, 0);
		if (xsk->fd < 0) {
			err = -errno;
			goto out_xsk_alloc;
		}
	} else {
		xsk->fd = umem->fd;
	}

	xsk->outstanding_tx = 0;
	xsk->queue_id = queue_id;
	xsk->umem = umem;
	xsk->ifindex = if_nametoindex(ifname);
	if (!xsk->ifindex) {
		err = -errno;
		goto out_socket;
	}
	memcpy(xsk->ifname, ifname, IFNAMSIZ - 1);
	xsk->ifname[IFNAMSIZ - 1] = '\0';

	if (rx) {
		err = setsockopt(xsk->fd, SOL_XDP, XDP_RX_RING,
				 &xsk->config.rx_size,
				 sizeof(xsk->config.rx_size));
		if (err) {
			err = -errno;
			goto out_socket;
		}
	}
	if (tx) {
		err = setsockopt(xsk->fd, SOL_XDP, XDP_TX_RING,
				 &xsk->config.tx_size,
				 sizeof(xsk->config.tx_size));
		if (err) {
			err = -errno;
			goto out_socket;
		}
	}

	err = xsk_get_mmap_offsets(xsk->fd, &off);
	if (err) {
		err = -errno;
		goto out_socket;
	}

    //设置数据包接收循环队列
	if (rx) {
		rx_map = mmap(NULL, off.rx.desc +
			      xsk->config.rx_size * sizeof(struct xdp_desc),
			      PROT_READ | PROT_WRITE, MAP_SHARED | MAP_POPULATE,
			      xsk->fd, XDP_PGOFF_RX_RING);
		if (rx_map == MAP_FAILED) {
			err = -errno;
			goto out_socket;
		}

		rx->mask = xsk->config.rx_size - 1;
		rx->size = xsk->config.rx_size;
		rx->producer = rx_map + off.rx.producer;
		rx->consumer = rx_map + off.rx.consumer;
		rx->flags = rx_map + off.rx.flags;
		rx->ring = rx_map + off.rx.desc;
	}
	xsk->rx = rx;

    //设置数据包发送循环队列
	if (tx) {
		tx_map = mmap(NULL, off.tx.desc +
			      xsk->config.tx_size * sizeof(struct xdp_desc),
			      PROT_READ | PROT_WRITE, MAP_SHARED | MAP_POPULATE,
			      xsk->fd, XDP_PGOFF_TX_RING);
		if (tx_map == MAP_FAILED) {
			err = -errno;
			goto out_mmap_rx;
		}

		tx->mask = xsk->config.tx_size - 1;
		tx->size = xsk->config.tx_size;
		tx->producer = tx_map + off.tx.producer;
		tx->consumer = tx_map + off.tx.consumer;
		tx->flags = tx_map + off.tx.flags;
		tx->ring = tx_map + off.tx.desc;
		tx->cached_cons = xsk->config.tx_size;
	}
	xsk->tx = tx;

	sxdp.sxdp_family = PF_XDP;
	sxdp.sxdp_ifindex = xsk->ifindex;
	sxdp.sxdp_queue_id = xsk->queue_id;
	if (umem->refcount > 1) {
		sxdp.sxdp_flags = XDP_SHARED_UMEM;
		sxdp.sxdp_shared_umem_fd = umem->fd;
	} else {
		sxdp.sxdp_flags = xsk->config.bind_flags;
	}

	err = bind(xsk->fd, (struct sockaddr *)&sxdp, sizeof(sxdp));
	if (err) {
		err = -errno;
		goto out_mmap_tx;
	}

	xsk->prog_fd = -1;

	if (!(xsk->config.libbpf_flags & XSK_LIBBPF_FLAGS__INHIBIT_PROG_LOAD)) {
		err = xsk_setup_xdp_prog(xsk);
		if (err)
			goto out_mmap_tx;
	}

	*xsk_ptr = xsk;
	return 0;

out_mmap_tx:
	if (tx)
		munmap(tx_map, off.tx.desc +
		       xsk->config.tx_size * sizeof(struct xdp_desc));
out_mmap_rx:
	if (rx)
		munmap(rx_map, off.rx.desc +
		       xsk->config.rx_size * sizeof(struct xdp_desc));
out_socket:
	if (--umem->refcount)
		close(xsk->fd);
out_xsk_alloc:
	free(xsk);
	return err;
}
~~~



libbpf中的AF_XDP时，会默认加载一个xdp 程序

~~~c
static int xsk_load_xdp_prog(struct xsk_socket *xsk)
{
	static const int log_buf_size = 16 * 1024;
	char log_buf[log_buf_size];
	int err, prog_fd;

	/* This is the C-program:
	 * SEC("xdp_sock") int xdp_sock_prog(struct xdp_md *ctx)
	 * {
	 *     int ret, index = ctx->rx_queue_index;
	 *
	 *     // A set entry here means that the correspnding queue_id
	 *     // has an active AF_XDP socket bound to it.
	 *     ret = bpf_redirect_map(&xsks_map, index, XDP_PASS);
	 *     if (ret > 0)
	 *         return ret;
	 *
	 *     // Fallback for pre-5.3 kernels, not supporting default
	 *     // action in the flags parameter.
	 *     if (bpf_map_lookup_elem(&xsks_map, &index))
	 *         return bpf_redirect_map(&xsks_map, index, 0);
	 *     return XDP_PASS;
	 * }
	 */
	struct bpf_insn prog[] = {
		/* r2 = *(u32 *)(r1 + 16) */
		BPF_LDX_MEM(BPF_W, BPF_REG_2, BPF_REG_1, 16),
		/* *(u32 *)(r10 - 4) = r2 */
		BPF_STX_MEM(BPF_W, BPF_REG_10, BPF_REG_2, -4),
		/* r1 = xskmap[] */
		BPF_LD_MAP_FD(BPF_REG_1, xsk->xsks_map_fd),
		/* r3 = XDP_PASS */
		BPF_MOV64_IMM(BPF_REG_3, 2),
		/* call bpf_redirect_map */
		BPF_EMIT_CALL(BPF_FUNC_redirect_map),
		/* if w0 != 0 goto pc+13 */
		BPF_JMP32_IMM(BPF_JSGT, BPF_REG_0, 0, 13),
		/* r2 = r10 */
		BPF_MOV64_REG(BPF_REG_2, BPF_REG_10),
		/* r2 += -4 */
		BPF_ALU64_IMM(BPF_ADD, BPF_REG_2, -4),
		/* r1 = xskmap[] */
		BPF_LD_MAP_FD(BPF_REG_1, xsk->xsks_map_fd),
		/* call bpf_map_lookup_elem */
		BPF_EMIT_CALL(BPF_FUNC_map_lookup_elem),
		/* r1 = r0 */
		BPF_MOV64_REG(BPF_REG_1, BPF_REG_0),
		/* r0 = XDP_PASS */
		BPF_MOV64_IMM(BPF_REG_0, 2),
		/* if r1 == 0 goto pc+5 */
		BPF_JMP_IMM(BPF_JEQ, BPF_REG_1, 0, 5),
		/* r2 = *(u32 *)(r10 - 4) */
		BPF_LDX_MEM(BPF_W, BPF_REG_2, BPF_REG_10, -4),
		/* r1 = xskmap[] */
		BPF_LD_MAP_FD(BPF_REG_1, xsk->xsks_map_fd),
		/* r3 = 0 */
		BPF_MOV64_IMM(BPF_REG_3, 0),
		/* call bpf_redirect_map */
		BPF_EMIT_CALL(BPF_FUNC_redirect_map),
		/* The jumps are to this instruction */
		BPF_EXIT_INSN(),
	};
	size_t insns_cnt = sizeof(prog) / sizeof(struct bpf_insn);

	prog_fd = bpf_load_program(BPF_PROG_TYPE_XDP, prog, insns_cnt,
				   "LGPL-2.1 or BSD-2-Clause", 0, log_buf,
				   log_buf_size);
	if (prog_fd < 0) {
		pr_warn("BPF log buffer:\n%s", log_buf);
		return prog_fd;
	}

	err = bpf_set_link_xdp_fd(xsk->ifindex, prog_fd, xsk->config.xdp_flags);
	if (err) {
		close(prog_fd);
		return err;
	}

	xsk->prog_fd = prog_fd;
	return 0;
}
~~~



## xdp单元测试

BPF_PROG_TEST_RUN

## 应用

* 网络监控
* 缓解Ddos攻击，将非法数据包进入内核协议栈之前丢弃，减少CPU消耗
* 负载均衡
* 防火墙

### 限制

* 一个网卡只能挂载一个xdp程序, libxdp支持挂载多个

* XDP只能看到进入网卡的包，从本机出去的包看不到(lo 网卡是个例外)


## 参考

* af_xdp https://www.kernel.org/doc/html/latest/networking/af_xdp.html
* af_xdp http://vger.kernel.org/lpc_net2018_talks/lpc18_paper_af_xdp_perf-v2.pdf
* af_xdp 介绍 https://lwn.net/Articles/750845/
* af_xdp https://networkbuilders.intel.com/docs/networkbuilders/af-xdp-sockets-high-performance-networking-for-cloud-native-networking-technology-guide.pdf
* xdp-turorial
* libxdp代码及文档  https://github.com/xdp-project/xdp-tools/tree/master/lib/libxdp
*  bpf示例代码  https://github.com/xdp-project/bpf-examples
*  http://vger.kernel.org/lpc_net2018_talks/lpc18_paper_af_xdp_perf-v2.pdf