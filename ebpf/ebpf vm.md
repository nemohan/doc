# ebpf vm

[TOC]

内核源码树 include/uapi/linux/bpf.h中定义了helper 函数对应的id，因此可以确定不同版本内核提供了哪些helper 函数

~~~c
#define __BPF_ENUM_FN(x) BPF_FUNC_ ## x
enum bpf_func_id {
	__BPF_FUNC_MAPPER(__BPF_ENUM_FN)
	__BPF_FUNC_MAX_ID,
};
~~~



## verifier

~~~c
static int check_helper_call(struct bpf_verifier_env *env, int func_id, int insn_idx)
{
	const struct bpf_func_proto *fn = NULL;
	struct bpf_reg_state *regs;
	struct bpf_call_arg_meta meta;
	bool changes_data;
	int i, err;

	/* find function prototype */
	if (func_id < 0 || func_id >= __BPF_FUNC_MAX_ID) {
		verbose(env, "invalid func %s#%d\n", func_id_name(func_id),
			func_id);
		return -EINVAL;
	}

	if (env->ops->get_func_proto)
		fn = env->ops->get_func_proto(func_id, env->prog);
	if (!fn) {
		verbose(env, "unknown func %s#%d\n", func_id_name(func_id),
			func_id);
		return -EINVAL;
	}
    
    .....
}
~~~

