# tc(traffic control)

[TOC]

![image-20231116160316830](D:\个人笔记\doc\ebpf\tc.assets\image-20231116160316830.png)

## 挂载

可以使用tc命令挂载对应类型的ebpf程序。tc实际使用的netlink进行挂载。

~~~bash
# tc qdisc add dev eth0 clsact
# tc filter add dev eth0 ingress bpf da obj myprog_kernel.o sec my_elf_sec
~~~



tc 实际挂载ebpf的代码在 iproute2 项目下的tc/tc_filter.c文件中

~~~c
static int tc_filter_modify(int cmd, unsigned int flags, int argc, char **argv)
{
	struct {
		struct nlmsghdr	n;
		struct tcmsg		t;
		char			buf[MAX_MSG];
	} req = {
		.n.nlmsg_len = NLMSG_LENGTH(sizeof(struct tcmsg)),
		.n.nlmsg_flags = NLM_F_REQUEST | flags,
		.n.nlmsg_type = cmd,
		.t.tcm_family = AF_UNSPEC,
	};
	struct filter_util *q = NULL;
	__u32 prio = 0;
	__u32 protocol = 0;
	int protocol_set = 0;
	__u32 block_index = 0;
	__u32 chain_index = 0;
	int chain_index_set = 0;
	char *fhandle = NULL;
	char  d[IFNAMSIZ] = {};
	char  k[FILTER_NAMESZ] = {};
	struct tc_estimator est = {};

	if (cmd == RTM_NEWTFILTER && flags & NLM_F_CREATE)
		protocol = htons(ETH_P_ALL);

	while (argc > 0) {
		if (strcmp(*argv, "dev") == 0) {
			NEXT_ARG();
			if (d[0])
				duparg("dev", *argv);
			if (block_index) {
				fprintf(stderr, "Error: \"dev\" and \"block\" are mutually exclusive\n");
				return -1;
			}
			strncpy(d, *argv, sizeof(d)-1);
		} else if (matches(*argv, "block") == 0) {
			NEXT_ARG();
			if (block_index)
				duparg("block", *argv);
			if (d[0]) {
				fprintf(stderr, "Error: \"dev\" and \"block\" are mutually exclusive\n");
				return -1;
			}
			if (get_u32(&block_index, *argv, 0) || !block_index)
				invarg("invalid block index value", *argv);
		} else if (strcmp(*argv, "root") == 0) {
			if (req.t.tcm_parent) {
				fprintf(stderr,
					"Error: \"root\" is duplicate parent ID\n");
				return -1;
			}
			req.t.tcm_parent = TC_H_ROOT;
		} else if (strcmp(*argv, "ingress") == 0) {
			if (req.t.tcm_parent) {
				fprintf(stderr,
					"Error: \"ingress\" is duplicate parent ID\n");
				return -1;
			}
			req.t.tcm_parent = TC_H_MAKE(TC_H_CLSACT,
						     TC_H_MIN_INGRESS);
		} else if (strcmp(*argv, "egress") == 0) {
			if (req.t.tcm_parent) {
				fprintf(stderr,
					"Error: \"egress\" is duplicate parent ID\n");
				return -1;
			}
			req.t.tcm_parent = TC_H_MAKE(TC_H_CLSACT,
						     TC_H_MIN_EGRESS);
		} else if (strcmp(*argv, "parent") == 0) {
			__u32 handle;

			NEXT_ARG();
			if (req.t.tcm_parent)
				duparg("parent", *argv);
			if (get_tc_classid(&handle, *argv))
				invarg("Invalid parent ID", *argv);
			req.t.tcm_parent = handle;
		} else if (strcmp(*argv, "handle") == 0) {
			NEXT_ARG();
			if (fhandle)
				duparg("handle", *argv);
			fhandle = *argv;
		} else if (matches(*argv, "preference") == 0 ||
			   matches(*argv, "priority") == 0) {
			NEXT_ARG();
			if (prio)
				duparg("priority", *argv);
			if (get_u32(&prio, *argv, 0) || prio > 0xFFFF)
				invarg("invalid priority value", *argv);
		} else if (matches(*argv, "protocol") == 0) {
			__u16 id;

			NEXT_ARG();
			if (protocol_set)
				duparg("protocol", *argv);
			if (ll_proto_a2n(&id, *argv))
				invarg("invalid protocol", *argv);
			protocol = id;
			protocol_set = 1;
		} else if (matches(*argv, "chain") == 0) {
			NEXT_ARG();
			if (chain_index_set)
				duparg("chain", *argv);
			if (get_u32(&chain_index, *argv, 0))
				invarg("invalid chain index value", *argv);
			chain_index_set = 1;
		} else if (matches(*argv, "estimator") == 0) {
			if (parse_estimator(&argc, &argv, &est) < 0)
				return -1;
		} else if (matches(*argv, "help") == 0) {
			usage();
			return 0;
		} else {
			strncpy(k, *argv, sizeof(k)-1);

			q = get_filter_kind(k);
			argc--; argv++;
			break;
		}

		argc--; argv++;
	}

	req.t.tcm_info = TC_H_MAKE(prio<<16, protocol);

	if (chain_index_set)
		addattr32(&req.n, sizeof(req), TCA_CHAIN, chain_index);

	if (k[0])
		addattr_l(&req.n, sizeof(req), TCA_KIND, k, strlen(k)+1);

	if (d[0])  {
		ll_init_map(&rth);

		req.t.tcm_ifindex = ll_name_to_index(d);
		if (req.t.tcm_ifindex == 0) {
			fprintf(stderr, "Cannot find device \"%s\"\n", d);
			return 1;
		}
	} else if (block_index) {
		req.t.tcm_ifindex = TCM_IFINDEX_MAGIC_BLOCK;
		req.t.tcm_block_index = block_index;
	}

	if (q) {
		if (q->parse_fopt(q, fhandle, argc, argv, &req.n))
			return 1;
	} else {
		if (fhandle) {
			fprintf(stderr,
				"Must specify filter type when using \"handle\"\n");
			return -1;
		}
		if (argc) {
			if (matches(*argv, "help") == 0)
				usage();
			fprintf(stderr,
				"Garbage instead of arguments \"%s ...\". Try \"tc filter help\".\n",
				*argv);
			return -1;
		}
	}

	if (est.ewma_log)
		addattr_l(&req.n, sizeof(req), TCA_RATE, &est, sizeof(est));

	if (rtnl_talk(&rth, &req.n, NULL) < 0) {
		fprintf(stderr, "We have an error talking to the kernel\n");
		return 2;
	}

	return 0;
}

~~~



### golang 使用netlink挂载

~~~go
import(
    	"github.com/cilium/ebpf"
	"github.com/cilium/ebpf/link"
"github.com/vishvananda/netlink"
)
func attachTC(){
	co, err := ebpf.LoadCollection("examples/tc_kern.o")
	if err != nil {
		panic(err)
	}
	h, err := netlink.NewHandle(unix.AF_NETLINK)
	if err != nil {
		panic(err)
	}
	if err := h.FilterAdd(&netlink.BpfFilter{
		FilterAttrs: netlink.FilterAttrs{
			LinkIndex: 2,
			//Parent:    4294967282,
			Parent:   netlink.HANDLE_MIN_EGRESS,
			Handle:   netlink.HANDLE_INGRESS,
			Protocol: unix.ETH_P_ALL,
		},
		Fd:           co.Programs["ingress_hook"].FD(),
		DirectAction: true,
	}); err != nil {
		panic(err)
	}
}
~~~



## 程序类型

| 程序类型                |      | section        |
| ----------------------- | ---- | -------------- |
| BPF_PROG_TYPE_SCHED_ACT |      | action         |
| BPF_PROG_TYPE_SCHED_CLS |      | classifire、tc |
|                         |      |                |



## 内核支持

cls_bpf 4.1

## 参考

* https://man7.org/linux/man-pages/man8/tc-bpf.8.html
* https://www.coverfire.com/articles/queueing-in-the-linux-network-stack/
* https://lwn.net/Articles/671458/

