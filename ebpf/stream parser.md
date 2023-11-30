# stream parser

[TOC]

stream parser可使用两种类型ebpf程序: BPF_PROG_TYPE_SK_MSG、BPF_PROG_TYPE_SK_SKB

## 挂载

挂载到类型为`BPF_MAP_TYPE_SOCKMAP`  或 `BPF_MAP_TYPE_SOCKHASH` 的map的fd上。可使用的挂载类型为:

- `msg_parser` program - `BPF_SK_MSG_VERDICT`.
- `stream_parser` program - `BPF_SK_SKB_STREAM_PARSER`.
- `stream_verdict` program - `BPF_SK_SKB_STREAM_VERDICT`.
- `skb_verdict` program - `BPF_SK_SKB_VERDICT`.

注意：

<font color='red'>不允许用户将`stream_verdict` and `skb_verdict` 程序挂载到同一个map.</font>

挂载到map上的ebpf程序是何时被触发执行的？？？ 内核树中net/ipv4/tcp_bpf.c中或许有答案



### 内核中的挂载流程

bpf_prog_attach （kernel/bpf/syscall.c ）中挂载BPF_PROG_TYPE_SK_SKB、BPF_PROG_TYPE_SK_MSG类型的的ebpf程序的代码片段

![image-20231129135218655](D:\个人笔记\doc\ebpf\stream parser.assets\image-20231129135218655.png)

#### sock_map_get_from_fd 根据map的fd获取map

~~~c
int sock_map_get_from_fd(const union bpf_attr *attr, struct bpf_prog *prog)
{
	u32 ufd = attr->target_fd;
	struct bpf_map *map;
	struct fd f;
	int ret;

	f = fdget(ufd);
	map = __bpf_map_get(f);
	if (IS_ERR(map))
		return PTR_ERR(map);
	ret = sock_map_prog_update(map, prog, NULL, attr->attach_type);
	fdput(f);
	return ret;
}
~~~



内核树net/core/sock_map.c

~~~c

static struct sk_psock_progs *sock_map_progs(struct bpf_map *map)
{
	switch (map->map_type) {
	case BPF_MAP_TYPE_SOCKMAP:
		return &container_of(map, struct bpf_stab, map)->progs;
	case BPF_MAP_TYPE_SOCKHASH:
		return &container_of(map, struct bpf_htab, map)->progs;
	default:
		break;
	}

	return NULL;
}


int sock_map_prog_update(struct bpf_map *map, struct bpf_prog *prog,
			 struct bpf_prog *old, u32 which)
{
	struct sk_psock_progs *progs = sock_map_progs(map);
	struct bpf_prog **pprog;

	if (!progs)
		return -EOPNOTSUPP;

	switch (which) {
	case BPF_SK_MSG_VERDICT:
		pprog = &progs->msg_parser;
		break;
	case BPF_SK_SKB_STREAM_PARSER:
		pprog = &progs->skb_parser;
		break;
	case BPF_SK_SKB_STREAM_VERDICT:
		pprog = &progs->skb_verdict;
		break;
	default:
		return -EOPNOTSUPP;
	}

	if (old)
		return psock_replace_prog(pprog, prog, old);

	psock_set_prog(pprog, prog);
	return 0;
}

~~~

## 内核依赖

- `BPF_MAP_TYPE_SOCKMAP` was introduced in kernel version 4.14
- `BPF_MAP_TYPE_SOCKHASH` was introduced in kernel version 4.18

## 代码示例

类型为BPF_SK_SKB_STREAM_VERDICT的ebpf程序

~~~c
SEC("sk_skb2")
int bpf_prog2(struct __sk_buff *skb)
{
        __u32 lport = skb->local_port;
        __u32 rport = skb->remote_port;
        int len, *f, ret, zero = 0;
        __u64 flags = 0;

        if (lport == 10000)
                ret = 10;
        else
                ret = 1;

        len = (__u32)skb->data_end - (__u32)skb->data;
        f = bpf_map_lookup_elem(&sock_skb_opts, &zero);
        if (f && *f) {
                ret = 3;
                flags = *f;
        }

        bpf_printk("sk_skb2: redirect(%iB) flags=%i\n",
                   len, flags);
#ifdef SOCKMAP
        return bpf_sk_redirect_map(skb, &sock_map, ret, flags);
#else
        return bpf_sk_redirect_hash(skb, &sock_map, &ret, flags);
#endif

}

~~~

### 内核中代码示例分析

tools/testing/selftests/bpf/test_sockmap_kern.h

~~~c
struct {
	__uint(type, TEST_MAP_TYPE);
	__uint(max_entries, 20);
	__uint(key_size, sizeof(int));
	__uint(value_size, sizeof(int));
} sock_map SEC(".maps");

struct {
	__uint(type, TEST_MAP_TYPE);
	__uint(max_entries, 20);
	__uint(key_size, sizeof(int));
	__uint(value_size, sizeof(int));
} sock_map_txmsg SEC(".maps");

struct {
	__uint(type, TEST_MAP_TYPE);
	__uint(max_entries, 20);
	__uint(key_size, sizeof(int));
	__uint(value_size, sizeof(int));
} sock_map_redir SEC(".maps");

struct {
	__uint(type, BPF_MAP_TYPE_ARRAY);
	__uint(max_entries, 1);
	__type(key, int);
	__type(value, int);
} sock_apply_bytes SEC(".maps");

struct {
	__uint(type, BPF_MAP_TYPE_ARRAY);
	__uint(max_entries, 1);
	__type(key, int);
	__type(value, int);
} sock_cork_bytes SEC(".maps");

struct {
	__uint(type, BPF_MAP_TYPE_ARRAY);
	__uint(max_entries, 6);
	__type(key, int);
	__type(value, int);
} sock_bytes SEC(".maps");

struct {
	__uint(type, BPF_MAP_TYPE_ARRAY);
	__uint(max_entries, 1);
	__type(key, int);
	__type(value, int);
} sock_redir_flags SEC(".maps");

struct {
	__uint(type, BPF_MAP_TYPE_ARRAY);
	__uint(max_entries, 1);
	__type(key, int);
	__type(value, int);
} sock_skb_opts SEC(".maps");


//应用程序将bpf_prg1 挂载到sock_map
SEC("sk_skb1")
int bpf_prog1(struct __sk_buff *skb)
{
	return skb->len;
}

//应用程序将bpf_prog2 挂载到sock_map
SEC("sk_skb2")
int bpf_prog2(struct __sk_buff *skb)
{
	__u32 lport = skb->local_port;
	__u32 rport = skb->remote_port;
	int len, *f, ret, zero = 0;
	__u64 flags = 0;

    //本地端口10000， 是服务端监听端口
	if (lport == 10000)
		ret = 10;
	else
		ret = 1;

	len = (__u32)skb->data_end - (__u32)skb->data;
	f = bpf_map_lookup_elem(&sock_skb_opts, &zero);
	if (f && *f) {
		ret = 3;
		flags = *f;
	}

	bpf_printk("sk_skb2: redirect(%iB) flags=%i\n",
		   len, flags);
#ifdef SOCKMAP
	return bpf_sk_redirect_map(skb, &sock_map, ret, flags);
#else
	return bpf_sk_redirect_hash(skb, &sock_map, &ret, flags);
#endif

}

SEC("sockops")
int bpf_sockmap(struct bpf_sock_ops *skops)
{
	__u32 lport, rport;
	int op, err = 0, index, key, ret;


	op = (int) skops->op;

	switch (op) {
	case BPF_SOCK_OPS_PASSIVE_ESTABLISHED_CB:
		lport = skops->local_port;
		rport = skops->remote_port;

		if (lport == 10000) {
			ret = 1;
#ifdef SOCKMAP
			err = bpf_sock_map_update(skops, &sock_map, &ret,
						  BPF_NOEXIST);
#else
			err = bpf_sock_hash_update(skops, &sock_map, &ret,
						   BPF_NOEXIST);
#endif
			bpf_printk("passive(%i -> %i) map ctx update err: %d\n",
				   lport, bpf_ntohl(rport), err);
		}
		break;
	case BPF_SOCK_OPS_ACTIVE_ESTABLISHED_CB:
		lport = skops->local_port;
		rport = skops->remote_port;

		if (bpf_ntohl(rport) == 10001) {
			ret = 10;
#ifdef SOCKMAP
			err = bpf_sock_map_update(skops, &sock_map, &ret,
						  BPF_NOEXIST);
#else
			err = bpf_sock_hash_update(skops, &sock_map, &ret,
						   BPF_NOEXIST);
#endif
			bpf_printk("active(%i -> %i) map ctx update err: %d\n",
				   lport, bpf_ntohl(rport), err);
		}
		break;
	default:
		break;
	}

	return 0;
}

~~~



~~~c
SEC("sk_msg1")
int bpf_prog4(struct sk_msg_md *msg)
{
	int *bytes, zero = 0, one = 1, two = 2, three = 3, four = 4, five = 5;
	int *start, *end, *start_push, *end_push, *start_pop, *pop;

	bytes = bpf_map_lookup_elem(&sock_apply_bytes, &zero);
	if (bytes)
		bpf_msg_apply_bytes(msg, *bytes);
	bytes = bpf_map_lookup_elem(&sock_cork_bytes, &zero);
	if (bytes)
		bpf_msg_cork_bytes(msg, *bytes);
	start = bpf_map_lookup_elem(&sock_bytes, &zero);
	end = bpf_map_lookup_elem(&sock_bytes, &one);
	if (start && end)
		bpf_msg_pull_data(msg, *start, *end, 0);
	start_push = bpf_map_lookup_elem(&sock_bytes, &two);
	end_push = bpf_map_lookup_elem(&sock_bytes, &three);
	if (start_push && end_push)
		bpf_msg_push_data(msg, *start_push, *end_push, 0);
	start_pop = bpf_map_lookup_elem(&sock_bytes, &four);
	pop = bpf_map_lookup_elem(&sock_bytes, &five);
	if (start_pop && pop)
		bpf_msg_pop_data(msg, *start_pop, *pop, 0);
	return SK_PASS;
}

~~~



应用程序分别在10000、10001端口开启服务。各有一个客户端连接到这两个端口。 c1 和10000端口服务建立连接。 c2和10001端口建立连接

## 注意

BPF_PROG_TYPE_SK_MSG、BPF_PROG_TYPE_SK_SKB对文件ebpf中的文件的SEC没有要求

## xx

~~~
bpf_sock_map_update
~~~



## 参考

* https://blogs.oracle.com/linux/post/bpf-a-tour-of-program-types
* https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/configuring_and_managing_networking/assembly_understanding-the-ebpf-features-in-rhel-8_configuring-and-managing-networking
* BPF_MAP_TYPE_SOCKMAP https://www.kernel.org/doc/html/latest/bpf/map_sockmap.html
* https://lwn.net/Articles/748628/
* 5.4 内核 tools/testing/selftests/bpf/test_sockmap_kern.h、test_sockmap.c

