# perf event

[TOC]



## 参考代码

samples/bpf/trace_output_kern.c
samples/bpf/trace_output_user.c

### trace_output_kern.c

linux-5.4.0

~~~c
#include <linux/ptrace.h>
#include <linux/version.h>
#include <uapi/linux/bpf.h>
#include "bpf_helpers.h"

struct bpf_map_def SEC("maps") my_map = {
	.type = BPF_MAP_TYPE_PERF_EVENT_ARRAY,
	.key_size = sizeof(int),
	.value_size = sizeof(u32),
	.max_entries = 2,
};

SEC("kprobe/sys_write")
int bpf_prog1(struct pt_regs *ctx)
{
	struct S {
		u64 pid;
		u64 cookie;
	} data;

	data.pid = bpf_get_current_pid_tgid();
	data.cookie = 0x12345678;

	bpf_perf_event_output(ctx, &my_map, 0, &data, sizeof(data));

	return 0;
}

char _license[] SEC("license") = "GPL";
u32 _version SEC("version") = LINUX_VERSION_CODE;
~~~



### trace_output_user.c 分析

linux-5.4.0

分析trace_output_user.c的目的，看看perf event 和ebpf 程序是如何交互的。

交互过程:

用户态: 

以trace_output_user.c为例：

1）加载ebpf程序, 检查使用的map类型是否为BPF_MAP_TYPE_PERF_EVENT_ARRAY，若不是则报错

2）调用epoll_create创建用于监听event的描述符

3）调用perf_event_open为每个cpu创建一个采集运行在当前cpu上的进程、线程的文件描述符，并为文件描述符创建内存映射(mmap)，作为当前cpu上的ring buffer

4)调用 bpf_map_update_elem 将cpu的索引作为key，上一步创建的fd作为value写入map

5) 将每个cpu对应的 event 文件描述符加入到epoll监听器中

6) 等待event

内核态: 调用bpf_perf_event_output向用户态输出数据

BPF_MAP_TYPE_PERF_EVENT_ARRAY 类型map目的并不是用于传输perf event数据

samples/bpf/trace_output_user.c

~~~c
static __u64 time_get_ns(void)
{
	struct timespec ts;

	clock_gettime(CLOCK_MONOTONIC, &ts);
	return ts.tv_sec * 1000000000ull + ts.tv_nsec;
}

static __u64 start_time;
static __u64 cnt;

#define MAX_CNT 100000ll

static void print_bpf_output(void *ctx, int cpu, void *data, __u32 size)
{
	struct {
		__u64 pid;
		__u64 cookie;
	} *e = data;

	if (e->cookie != 0x12345678) {
		printf("BUG pid %llx cookie %llx sized %d\n",
		       e->pid, e->cookie, size);
		return;
	}

	cnt++;

	if (cnt == MAX_CNT) {
		printf("recv %lld events per sec\n",
		       MAX_CNT * 1000000000ll / (time_get_ns() - start_time));
		return;
	}
}

int main(int argc, char **argv)
{
	struct perf_buffer_opts pb_opts = {};
	struct perf_buffer *pb;
	char filename[256];
	FILE *f;
	int ret;

	snprintf(filename, sizeof(filename), "%s_kern.o", argv[0]);

	if (load_bpf_file(filename)) {
		printf("%s", bpf_log_buf);
		return 1;
	}

	pb_opts.sample_cb = print_bpf_output;
	pb = perf_buffer__new(map_fd[0], 8, &pb_opts);
	ret = libbpf_get_error(pb);
	if (ret) {
		printf("failed to setup perf_buffer: %d\n", ret);
		return 1;
	}

	f = popen("taskset 1 dd if=/dev/zero of=/dev/null", "r");
	(void) f;

	start_time = time_get_ns();
	while ((ret = perf_buffer__poll(pb, 1000)) >= 0 && cnt < MAX_CNT) {
	}
	kill(0, SIGINT);
	return ret;
}

~~~

#### 初始化

~~~c
struct perf_buffer {
	perf_buffer_event_fn event_cb;
	perf_buffer_sample_fn sample_cb;
	perf_buffer_lost_fn lost_cb;
	void *ctx; /* passed into callbacks */

	size_t page_size;
	size_t mmap_size;
	struct perf_cpu_buf **cpu_bufs;
	struct epoll_event *events;
	int cpu_cnt;
	int epoll_fd; /* perf event FD */
	int map_fd; /* BPF_MAP_TYPE_PERF_EVENT_ARRAY BPF map FD */ //ebpf map 的描述符
};

struct perf_cpu_buf {
	struct perf_buffer *pb;
	void *base; /* mmap()'ed memory */
	void *buf; /* for reconstructing segmented data */
	size_t buf_size;
	int fd;
	int cpu;
	int map_key;
};
typedef void (*perf_buffer_sample_fn)(void *ctx, int cpu,
				      void *data, __u32 size);
typedef void (*perf_buffer_lost_fn)(void *ctx, int cpu, __u64 cnt);
typedef enum bpf_perf_event_ret
(*perf_buffer_event_fn)(void *ctx, int cpu, struct perf_event_header *event);
~~~

##### perf_buffer__new

~~~c
struct perf_buffer *perf_buffer__new(int map_fd, size_t page_cnt,
				     const struct perf_buffer_opts *opts)
{
	struct perf_buffer_params p = {};
	struct perf_event_attr attr = { 0, };

	attr.config = PERF_COUNT_SW_BPF_OUTPUT,
	attr.type = PERF_TYPE_SOFTWARE;
	attr.sample_type = PERF_SAMPLE_RAW;
	attr.sample_period = 1;
	attr.wakeup_events = 1;

	p.attr = &attr;
	p.sample_cb = opts ? opts->sample_cb : NULL;
	p.lost_cb = opts ? opts->lost_cb : NULL;
	p.ctx = opts ? opts->ctx : NULL;

	return __perf_buffer__new(map_fd, page_cnt, &p);
}
~~~



~~~c



static struct perf_buffer *__perf_buffer__new(int map_fd, size_t page_cnt,
					      struct perf_buffer_params *p)
{
	struct bpf_map_info map = {};
	char msg[STRERR_BUFSIZE];
	struct perf_buffer *pb;
	__u32 map_info_len;
	int err, i;

	if (page_cnt & (page_cnt - 1)) {
		pr_warning("page count should be power of two, but is %zu\n",
			   page_cnt);
		return ERR_PTR(-EINVAL);
	}

	map_info_len = sizeof(map);
	err = bpf_obj_get_info_by_fd(map_fd, &map, &map_info_len);
	if (err) {
		err = -errno;
		pr_warning("failed to get map info for map FD %d: %s\n",
			   map_fd, libbpf_strerror_r(err, msg, sizeof(msg)));
		return ERR_PTR(err);
	}

	if (map.type != BPF_MAP_TYPE_PERF_EVENT_ARRAY) {
		pr_warning("map '%s' should be BPF_MAP_TYPE_PERF_EVENT_ARRAY\n",
			   map.name);
		return ERR_PTR(-EINVAL);
	}

	pb = calloc(1, sizeof(*pb));
	if (!pb)
		return ERR_PTR(-ENOMEM);

	pb->event_cb = p->event_cb;
	pb->sample_cb = p->sample_cb;
	pb->lost_cb = p->lost_cb;
	pb->ctx = p->ctx;

	pb->page_size = getpagesize();
	pb->mmap_size = pb->page_size * page_cnt;
	pb->map_fd = map_fd;

	pb->epoll_fd = epoll_create1(EPOLL_CLOEXEC);
	if (pb->epoll_fd < 0) {
		err = -errno;
		pr_warning("failed to create epoll instance: %s\n",
			   libbpf_strerror_r(err, msg, sizeof(msg)));
		goto error;
	}

	if (p->cpu_cnt > 0) {
		pb->cpu_cnt = p->cpu_cnt;
	} else {
		pb->cpu_cnt = libbpf_num_possible_cpus();
		if (pb->cpu_cnt < 0) {
			err = pb->cpu_cnt;
			goto error;
		}
		if (map.max_entries < pb->cpu_cnt)
			pb->cpu_cnt = map.max_entries;
	}

	pb->events = calloc(pb->cpu_cnt, sizeof(*pb->events));
	if (!pb->events) {
		err = -ENOMEM;
		pr_warning("failed to allocate events: out of memory\n");
		goto error;
	}
	pb->cpu_bufs = calloc(pb->cpu_cnt, sizeof(*pb->cpu_bufs));
	if (!pb->cpu_bufs) {
		err = -ENOMEM;
		pr_warning("failed to allocate buffers: out of memory\n");
		goto error;
	}

	for (i = 0; i < pb->cpu_cnt; i++) {
		struct perf_cpu_buf *cpu_buf;
		int cpu, map_key;

		cpu = p->cpu_cnt > 0 ? p->cpus[i] : i;
		map_key = p->cpu_cnt > 0 ? p->map_keys[i] : i;

		cpu_buf = perf_buffer__open_cpu_buf(pb, p->attr, cpu, map_key);
		if (IS_ERR(cpu_buf)) {
			err = PTR_ERR(cpu_buf);
			goto error;
		}

		pb->cpu_bufs[i] = cpu_buf;

		err = bpf_map_update_elem(pb->map_fd, &map_key,
					  &cpu_buf->fd, 0);
		if (err) {
			err = -errno;
			pr_warning("failed to set cpu #%d, key %d -> perf FD %d: %s\n",
				   cpu, map_key, cpu_buf->fd,
				   libbpf_strerror_r(err, msg, sizeof(msg)));
			goto error;
		}

		pb->events[i].events = EPOLLIN;
		pb->events[i].data.ptr = cpu_buf;
		if (epoll_ctl(pb->epoll_fd, EPOLL_CTL_ADD, cpu_buf->fd,
			      &pb->events[i]) < 0) {
			err = -errno;
			pr_warning("failed to epoll_ctl cpu #%d perf FD %d: %s\n",
				   cpu, cpu_buf->fd,
				   libbpf_strerror_r(err, msg, sizeof(msg)));
			goto error;
		}
	}

	return pb;

error:
	if (pb)
		perf_buffer__free(pb);
	return ERR_PTR(err);
}
~~~



##### perf_buffer__open_cpu_buf 为当前cpu创建一个内存映射区域

* 调用perf_event_open对应的系统调用，创建采集运行在指定cpu上的所有进程、线程的性能数据的文件描述符
* 为第一步创建的描述符创建内存映射

~~~c
static struct perf_cpu_buf *
perf_buffer__open_cpu_buf(struct perf_buffer *pb, struct perf_event_attr *attr,
			  int cpu, int map_key)
{
	struct perf_cpu_buf *cpu_buf;
	char msg[STRERR_BUFSIZE];
	int err;

	cpu_buf = calloc(1, sizeof(*cpu_buf));
	if (!cpu_buf)
		return ERR_PTR(-ENOMEM);

	cpu_buf->pb = pb;
	cpu_buf->cpu = cpu;
	cpu_buf->map_key = map_key;

	cpu_buf->fd = syscall(__NR_perf_event_open, attr, -1 /* pid */, cpu,
			      -1, PERF_FLAG_FD_CLOEXEC);
	if (cpu_buf->fd < 0) {
		err = -errno;
		pr_warning("failed to open perf buffer event on cpu #%d: %s\n",
			   cpu, libbpf_strerror_r(err, msg, sizeof(msg)));
		goto error;
	}

	cpu_buf->base = mmap(NULL, pb->mmap_size + pb->page_size,
			     PROT_READ | PROT_WRITE, MAP_SHARED,
			     cpu_buf->fd, 0);
	if (cpu_buf->base == MAP_FAILED) {
		cpu_buf->base = NULL;
		err = -errno;
		pr_warning("failed to mmap perf buffer on cpu #%d: %s\n",
			   cpu, libbpf_strerror_r(err, msg, sizeof(msg)));
		goto error;
	}

	if (ioctl(cpu_buf->fd, PERF_EVENT_IOC_ENABLE, 0) < 0) {
		err = -errno;
		pr_warning("failed to enable perf buffer event on cpu #%d: %s\n",
			   cpu, libbpf_strerror_r(err, msg, sizeof(msg)));
		goto error;
	}

	return cpu_buf;

error:
	perf_buffer__free_cpu_buf(pb, cpu_buf);
	return (struct perf_cpu_buf *)ERR_PTR(err);
}
~~~

#### 监听perf event事件

~~~c
int perf_buffer__poll(struct perf_buffer *pb, int timeout_ms)
{
	int i, cnt, err;

	cnt = epoll_wait(pb->epoll_fd, pb->events, pb->cpu_cnt, timeout_ms);
	for (i = 0; i < cnt; i++) {
		struct perf_cpu_buf *cpu_buf = pb->events[i].data.ptr;

		err = perf_buffer__process_records(pb, cpu_buf);
		if (err) {
			pr_warning("error while processing records: %d\n", err);
			return err;
		}
	}
	return cnt < 0 ? -errno : cnt;
}
~~~



~~~c
static int perf_buffer__process_records(struct perf_buffer *pb,
					struct perf_cpu_buf *cpu_buf)
{
	enum bpf_perf_event_ret ret;

	ret = bpf_perf_event_read_simple(cpu_buf->base, pb->mmap_size,
					 pb->page_size, &cpu_buf->buf,
					 &cpu_buf->buf_size,
					 perf_buffer__process_record, cpu_buf);
	if (ret != LIBBPF_PERF_EVENT_CONT)
		return ret;
	return 0;
}
~~~



toos/lib/bpf/libbpf.c

~~~c
enum bpf_perf_event_ret
bpf_perf_event_read_simple(void *mmap_mem, size_t mmap_size, size_t page_size,
			   void **copy_mem, size_t *copy_size,
			   bpf_perf_event_print_t fn, void *private_data)
{
	struct perf_event_mmap_page *header = mmap_mem;
	__u64 data_head = ring_buffer_read_head(header);
	__u64 data_tail = header->data_tail;
	void *base = ((__u8 *)header) + page_size;
	int ret = LIBBPF_PERF_EVENT_CONT;
	struct perf_event_header *ehdr;
	size_t ehdr_size;

	while (data_head != data_tail) {
		ehdr = base + (data_tail & (mmap_size - 1));
		ehdr_size = ehdr->size;

		if (((void *)ehdr) + ehdr_size > base + mmap_size) {
			void *copy_start = ehdr;
			size_t len_first = base + mmap_size - copy_start;
			size_t len_secnd = ehdr_size - len_first;

			if (*copy_size < ehdr_size) {
				free(*copy_mem);
				*copy_mem = malloc(ehdr_size);
				if (!*copy_mem) {
					*copy_size = 0;
					ret = LIBBPF_PERF_EVENT_ERROR;
					break;
				}
				*copy_size = ehdr_size;
			}

			memcpy(*copy_mem, copy_start, len_first);
			memcpy(*copy_mem + len_first, base, len_secnd);
			ehdr = *copy_mem;
		}

		ret = fn(ehdr, private_data);
		data_tail += ehdr_size;
		if (ret != LIBBPF_PERF_EVENT_CONT)
			break;
	}

	ring_buffer_write_tail(header, data_tail);
	return ret;
}
~~~



~~~c
static enum bpf_perf_event_ret
perf_buffer__process_record(struct perf_event_header *e, void *ctx)
{
	struct perf_cpu_buf *cpu_buf = ctx;
	struct perf_buffer *pb = cpu_buf->pb;
	void *data = e;

	/* user wants full control over parsing perf event */
	if (pb->event_cb)
		return pb->event_cb(pb->ctx, cpu_buf->cpu, e);

	switch (e->type) {
	case PERF_RECORD_SAMPLE: {
		struct perf_sample_raw *s = data;

		if (pb->sample_cb)
			pb->sample_cb(pb->ctx, cpu_buf->cpu, s->data, s->size);
		break;
	}
	case PERF_RECORD_LOST: {
		struct perf_sample_lost *s = data;

		if (pb->lost_cb)
			pb->lost_cb(pb->ctx, cpu_buf->cpu, s->lost);
		break;
	}
	default:
		pr_warning("unknown perf sample type %d\n", e->type);
		return LIBBPF_PERF_EVENT_ERROR;
	}
	return LIBBPF_PERF_EVENT_CONT;
}
~~~



## perf_event_open

~~~
    Given a list of parameters, perf_event_open() returns a file
       descriptor, for use in subsequent system calls (read(2), mmap(2),
       prctl(2), fcntl(2), etc.).

       A call to perf_event_open() creates a file descriptor that allows
       measuring performance information.  Each file descriptor
       corresponds to one event that is measured; these can be grouped
       together to measure multiple events simultaneously.

       Events can be enabled and disabled in two ways: via ioctl(2) and
       via prctl(2).  When an event is disabled it does not count or
       generate overflows but does continue to exist and maintain its
       count value.

       Events come in two flavors: counting and sampled.  A counting
       event is one that is used for counting the aggregate number of
       events that occur.  In general, counting event results are
       gathered with a read(2) call.  A sampling event periodically
       writes measurements to a buffer that can then be accessed via
       mmap(2).
~~~



##  bpf_perf_event_output

~~~
 long bpf_perf_event_output(void *ctx, struct bpf_map *map, u64
       flags, void *data, u64 size)

              Description
                     Write raw data blob into a special BPF perf event
                     held by map of type BPF_MAP_TYPE_PERF_EVENT_ARRAY.
                     This perf event must have the following attributes:
                     PERF_SAMPLE_RAW as sample_type, PERF_TYPE_SOFTWARE
                     as type, and PERF_COUNT_SW_BPF_OUTPUT as config.

                     The flags are used to indicate the index in map for
                     which the value must be put, masked with
                     BPF_F_INDEX_MASK.  Alternatively, flags can be set
                     to BPF_F_CURRENT_CPU to indicate that the index of
                     the current CPU core should be used.

                     The value to write, of size, is passed through eBPF
                     stack and pointed by data.

                     The context of the program ctx needs also be passed
                     to the helper.

                     On user space, a program willing to read the values
                     needs to call perf_event_open() on the perf event
                     (either for one or for all CPUs) and to store the
                     file descriptor into the map. This must be done
                     before the eBPF program can send data into it. An
                     example is available in file
                     samples/bpf/trace_output_user.c in the Linux kernel
                     source tree (the eBPF program counterpart is in
                     samples/bpf/trace_output_kern.c).

                     bpf_perf_event_output() achieves better performance
                     than bpf_trace_printk() for sharing data with user
                     space, and is much better suitable for streaming
                     data from eBPF programs.

                     Note that this helper is not restricted to tracing
                     use cases and can be used with programs attached to
                     TC or XDP as well, where it allows for passing data
                     to user space listeners. Data can be:

                     • Only custom structs,

                     • Only the packet payload, or

                     • A combination of both.

              Return 0 on success, or a negative error in case of
                     failure.
~~~



## 问题

perf event 使用的ring buffer满了表现出什么行为





