# tap

[TOC]

使用linux tap虚拟网卡，实现用户态下的tcp/ip协议栈

添加tap设备、配置iptables

~~~bash
#!/bin/sh
ip tuntap add name tap0 mode tap user root
ip link set tap0 up
ip addr add 192.168.69.100/24 dev tap0
iptables -t nat -A POSTROUTING -s 192.168.69.1/32 -j MASQUERADE
iptables -t nat -A POSTROUTING -s 192.168.69.0/24 -j MASQUERADE
sysctl net.ipv4.ip_forward=1

iptables -A FORWARD -i tap0 -s 192.168.69.0/24 -j ACCEPT
iptables -A FORWARD -o tap0 -d 192.168.69.0/24 -j ACCEPT
~~~



tap0网卡信息如下图所示：

![image-20250715164332909](D:\个人笔记\doc\网络\tap.assets\image-20250715164332909.png)

测试代码

~~~go
package main

import (
	"bytes"
	"flag"
	"fmt"
	"net"
	"time"

	"github.com/google/netstack/tcpip/link/tun"
	"github.com/tsg/gopacket"
	"github.com/tsg/gopacket/layers"
	"gvisor.dev/gvisor/pkg/rawfile"
)

var (
	fSrcIP  = flag.String("src-ip", "192.168.1.1", "Source IP address")
	fDestIP = flag.String("dest-ip", "192.168.1.2", "Destination IP address")
)

func main() {
	flag.Parse()
	fd, err := tun.OpenTAP("tap0")
	if err != nil {
		panic(err)
	}

	for i := 0; i < 1; i++ {
		tcp := layers.TCP{
			DstPort: 80,
			SrcPort: 61782,
			SYN:     true,
			Seq:     1225262524,
			Window:  128,
			Options: []layers.TCPOption{
				layers.TCPOption{
					OptionType:   2,
					OptionLength: 4,
					OptionData:   []byte{0x5, 0xb4},
				},
				layers.TCPOption{
					OptionType:   3,
					OptionLength: 3,
					OptionData:   []byte{0x0},
				},

				layers.TCPOption{
					OptionType:   4,
					OptionLength: 2,
				},
				layers.TCPOption{
					OptionType: 0,
				},
			},
		}
		buffer := gopacket.NewSerializeBuffer()
		tcp.SetNetworkLayerForChecksum(&layers.IPv4{
			SrcIP:    net.ParseIP(*fSrcIP).To4(),
			DstIP:    net.ParseIP(*fDestIP).To4(),
			Protocol: layers.IPProtocolTCP,
		})
		if err := tcp.SerializeTo(buffer, gopacket.SerializeOptions{FixLengths: true, ComputeChecksums: true}); err != nil {
			panic(err)
		}

		//srcIP := net.ParseIP(*fSrcIP)
		//destIP := net.ParseIP(*fDestIP)
		fmt.Printf("src_ip:%s dest_ip:%s\n", net.ParseIP(*fSrcIP), net.ParseIP(*fDestIP))
		ip := layers.IPv4{
			Version:  4,
			SrcIP:    net.ParseIP(*fSrcIP).To4(),
			DstIP:    net.ParseIP(*fDestIP).To4(),
			Flags:    layers.IPv4DontFragment,
			Id:       0,
			TTL:      64,
			Protocol: layers.IPProtocolTCP,
		}
		if err := ip.SerializeTo(buffer, gopacket.SerializeOptions{FixLengths: true, ComputeChecksums: true}); err != nil {
			panic(err)
		}

		eth := layers.Ethernet{
			EthernetType: layers.EthernetTypeIPv4,
			//SrcMAC:       net.HardwareAddr{0xea, 0x49, 0x9b, 0x51, 0xe6, 0xa7},
			SrcMAC: net.HardwareAddr{0x02, 0x00, 0x00, 0x0, 0x0, 0x1},
			DstMAC: net.HardwareAddr{0xea, 0x49, 0x9b, 0x51, 0xe6, 0xa7},
			//DstMAC:       net.HardwareAddr{0x00, 0x0c, 0x29, 0x49, 0x42, 0x3a},
			//DstMAC:       net.HardwareAddr{0x02, 0x0c, 0x29, 0x49, 0x42, 0x3a},
		}
		eth.SerializeTo(buffer, gopacket.SerializeOptions{FixLengths: true, ComputeChecksums: true})

		err = rawfile.NonBlockingWrite(fd, buffer.Bytes())
		fmt.Printf("write err:%v\n", err)

		for {
			rdBuf := make([]byte, 1024)
			nr, errNo := rawfile.BlockingRead(fd, rdBuf)
			fmt.Printf("read nr:%d err:%v %v\n", nr, errNo, rdBuf[:nr])
			hexDump(rdBuf[:nr])

			eth := layers.Ethernet{}
			if err := eth.DecodeFromBytes(rdBuf[:nr], gopacket.NilDecodeFeedback); err != nil {
				panic(err)
			}
			if eth.EthernetType == layers.EthernetTypeARP {
				fmt.Printf("handle arp packet\n")
				arp, err := decodeARP(rdBuf[14:nr])
				if err != nil {
					fmt.Printf("decode arp err:%v\n", err)
				} else {
					if arp.Operation != layers.ARPReply && arp.Operation != layers.ARPRequest {
						fmt.Printf("not arp request or reply\n")
						continue
					}
					fmt.Printf("arp:%+v\n", arp)
					arpResp := layers.ARP{
						AddrType:          layers.LinkTypeEthernet,
						Protocol:          layers.EthernetTypeIPv4,
						HwAddressSize:     6,
						ProtAddressSize:   4,
						Operation:         layers.ARPReply,
						SourceHwAddress:   []byte{0x02, 0x00, 0x00, 0x0, 0x0, 0x1},
						SourceProtAddress: net.ParseIP(*fSrcIP).To4(),
						DstHwAddress:      arp.SourceHwAddress,
						DstProtAddress:    arp.SourceProtAddress,
					}

					arpBuf := gopacket.NewSerializeBuffer()
					if err := arpResp.SerializeTo(arpBuf, gopacket.SerializeOptions{FixLengths: true, ComputeChecksums: true}); err != nil {
						panic(err)
					}

					eth := layers.Ethernet{
						EthernetType: layers.EthernetTypeARP,
						//SrcMAC:       net.HardwareAddr{0xea, 0x49, 0x9b, 0x51, 0xe6, 0xa7},
						SrcMAC: net.HardwareAddr{0x02, 0x00, 0x00, 0x0, 0x0, 0x1},
						DstMAC: net.HardwareAddr{0xea, 0x49, 0x9b, 0x51, 0xe6, 0xa7},
						//DstMAC:       net.HardwareAddr{0x00, 0x0c, 0x29, 0x49, 0x42, 0x3a},
						//DstMAC:       net.HardwareAddr{0x02, 0x0c, 0x29, 0x49, 0x42, 0x3a},
					}
					eth.SerializeTo(arpBuf, gopacket.SerializeOptions{FixLengths: true, ComputeChecksums: true})

					fmt.Printf("send arp response :%+v\n", arpResp)
					rawfile.NonBlockingWrite(fd, arpBuf.Bytes())

				}
			}
		}
		time.Sleep(time.Second * 60)
	}

	fmt.Printf("%d\n", fd)
}
func hexDump(data []byte) {
	buf := bytes.NewBufferString("")
	for _, b := range data {
		buf.WriteString(fmt.Sprintf("%02x ", b))
	}
	fmt.Printf("hex_dump:%s\n", buf.String())
}
func decodeARP(data []byte) (*layers.ARP, error) {
	arp := &layers.ARP{}
	if err := arp.DecodeFromBytes(data, gopacket.NilDecodeFeedback); err != nil {
		return nil, err
	}
	return arp, nil
}

~~~



## 遇到的坑

尝试使用tap0的mac地址作为二层源地址、物理网卡ens33的mac地址作为二层目的地址时，发现发出的数据包无法到达网卡ens33。排查发现是操作系统会用函数eht_type_trans根据数据包的二层目的地址和收到该数据包的网卡skb->dev的mac地址设置数据包的skb->pkt_type方向：若数据包二层目的地址匹配网卡mac地址，skb->pkt_type设置为PACKET_HOST，即该数据包是送往本机的。若数据包的二层目的地址为网卡的广播地址，则skb->pkt_type设置为PACKET_BROADCAST；若数据包的二层目的地址为多播地址，设置为PACKET_MULTICAST；否则是skb->pkt_type设置为PACKET_OTHERHOST。skb->pkt_type类型为PACKET_OTHERHOST的数据包到达ip层时(函数ip_rcv)，会直接被丢弃

向tap虚拟网卡写入数据包，类似物理网卡收到了数据包，会先走一个正常的接收流程。此外，使用打开tap设备实际打开的是/dev/net/tun文件，然后调用ioctl设置了IFF_TAP标志。因此向tap设备写入数据包时，内核代码调用的是tun_get_user(tun_chr_write_iter -->tun_get_user)

以下代码来源于内核5.15.47

tun_get_user代码片段：

其中eth_type_trans(skb, tun->dev)判定skb的目的mac地址和tun->dev的mac地址不匹配，将skb->pkt_type设置为PACKET_OTHERHOST

![image-20251119163507818](D:\个人笔记\doc\网络\tap.assets\image-20251119163507818.png)



eth_type_trans实现:

需要注意的是PACKET_HOST的值为0，下面代码中skb->pkt_type默认是PACKET_HOST。

~~~c
__be16 eth_type_trans(struct sk_buff *skb, struct net_device *dev)
{
	unsigned short _service_access_point;
	const unsigned short *sap;
	const struct ethhdr *eth;

	skb->dev = dev;
	skb_reset_mac_header(skb);

	eth = (struct ethhdr *)skb->data;
	skb_pull_inline(skb, ETH_HLEN);

	if (unlikely(!ether_addr_equal_64bits(eth->h_dest,
					      dev->dev_addr))) {
		if (unlikely(is_multicast_ether_addr_64bits(eth->h_dest))) {
			if (ether_addr_equal_64bits(eth->h_dest, dev->broadcast))
				skb->pkt_type = PACKET_BROADCAST;
			else
				skb->pkt_type = PACKET_MULTICAST;
		} else {
			skb->pkt_type = PACKET_OTHERHOST;
		}
	}

	/*
	 * Some variants of DSA tagging don't have an ethertype field
	 * at all, so we check here whether one of those tagging
	 * variants has been configured on the receiving interface,
	 * and if so, set skb->protocol without looking at the packet.
	 */
	if (unlikely(netdev_uses_dsa(dev)))
		return htons(ETH_P_XDSA);

	if (likely(eth_proto_is_802_3(eth->h_proto)))
		return eth->h_proto;

	/*
	 *      This is a magic hack to spot IPX packets. Older Novell breaks
	 *      the protocol design and runs IPX over 802.3 without an 802.2 LLC
	 *      layer. We look for FFFF which isn't a used 802.2 SSAP/DSAP. This
	 *      won't work for fault tolerant netware but does for the rest.
	 */
	sap = skb_header_pointer(skb, 0, sizeof(*sap), &_service_access_point);
	if (sap && *sap == 0xFFFF)
		return htons(ETH_P_802_3);

	/*
	 *      Real 802.2 LLC
	 */
	return htons(ETH_P_802_2);
}
EXPORT_SYMBOL(eth_type_trans);
~~~



~~~c
int ip_rcv(struct sk_buff *skb, struct net_device *dev, struct packet_type *pt,
	   struct net_device *orig_dev)
{
	struct net *net = dev_net(dev);

	skb = ip_rcv_core(skb, net);
	if (skb == NULL)
		return NET_RX_DROP;

	return NF_HOOK(NFPROTO_IPV4, NF_INET_PRE_ROUTING,
		       net, NULL, skb, dev, NULL,
		       ip_rcv_finish);
}
~~~



~~~c
/*
 * 	Main IP Receive routine.
 */
static struct sk_buff *ip_rcv_core(struct sk_buff *skb, struct net *net)
{
	const struct iphdr *iph;
	u32 len;

	/* When the interface is in promisc. mode, drop all the crap
	 * that it receives, do not try to analyse it.
	 */
	if (skb->pkt_type == PACKET_OTHERHOST)
		goto drop;

	__IP_UPD_PO_STATS(net, IPSTATS_MIB_IN, skb->len);

	skb = skb_share_check(skb, GFP_ATOMIC);
	if (!skb) {
		__IP_INC_STATS(net, IPSTATS_MIB_INDISCARDS);
		goto out;
	}

	if (!pskb_may_pull(skb, sizeof(struct iphdr)))
		goto inhdr_error;

	iph = ip_hdr(skb);

	/*
	 *	RFC1122: 3.2.1.2 MUST silently discard any IP frame that fails the checksum.
	 *
	 *	Is the datagram acceptable?
	 *
	 *	1.	Length at least the size of an ip header
	 *	2.	Version of 4
	 *	3.	Checksums correctly. [Speed optimisation for later, skip loopback checksums]
	 *	4.	Doesn't have a bogus length
	 */

	if (iph->ihl < 5 || iph->version != 4)
		goto inhdr_error;

	BUILD_BUG_ON(IPSTATS_MIB_ECT1PKTS != IPSTATS_MIB_NOECTPKTS + INET_ECN_ECT_1);
	BUILD_BUG_ON(IPSTATS_MIB_ECT0PKTS != IPSTATS_MIB_NOECTPKTS + INET_ECN_ECT_0);
	BUILD_BUG_ON(IPSTATS_MIB_CEPKTS != IPSTATS_MIB_NOECTPKTS + INET_ECN_CE);
	__IP_ADD_STATS(net,
		       IPSTATS_MIB_NOECTPKTS + (iph->tos & INET_ECN_MASK),
		       max_t(unsigned short, 1, skb_shinfo(skb)->gso_segs));

	if (!pskb_may_pull(skb, iph->ihl*4))
		goto inhdr_error;

	iph = ip_hdr(skb);

	if (unlikely(ip_fast_csum((u8 *)iph, iph->ihl)))
		goto csum_error;

	len = ntohs(iph->tot_len);
	if (skb->len < len) {
		__IP_INC_STATS(net, IPSTATS_MIB_INTRUNCATEDPKTS);
		goto drop;
	} else if (len < (iph->ihl*4))
		goto inhdr_error;

	/* Our transport medium may have padded the buffer out. Now we know it
	 * is IP we can trim to the true length of the frame.
	 * Note this now means skb->len holds ntohs(iph->tot_len).
	 */
	if (pskb_trim_rcsum(skb, len)) {
		__IP_INC_STATS(net, IPSTATS_MIB_INDISCARDS);
		goto drop;
	}

	iph = ip_hdr(skb);
	skb->transport_header = skb->network_header + iph->ihl*4;

	/* Remove any debris in the socket control block */
	memset(IPCB(skb), 0, sizeof(struct inet_skb_parm));
	IPCB(skb)->iif = skb->skb_iif;

	/* Must drop socket now because of tproxy. */
	if (!skb_sk_is_prefetched(skb))
		skb_orphan(skb);

	return skb;

csum_error:
	__IP_INC_STATS(net, IPSTATS_MIB_CSUMERRORS);
inhdr_error:
	__IP_INC_STATS(net, IPSTATS_MIB_INHDRERRORS);
drop:
	kfree_skb(skb);
out:
	return NULL;
}
~~~

