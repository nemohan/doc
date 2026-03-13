# libbpf

[TOC]

从用户态的角度出发，了解一下ebpf加载过程中的一些细节。分两步入手：1）ebpf 目标文件的解析过程 ；2）目标文件中的ebpf程序加载到内核的过程

以libbpf 0.3.0版本为分析对象。

## ebpf 目标文件解析



bpf_object的定义:

~~~c
struct bpf_object {
	char name[BPF_OBJ_NAME_LEN];
	char license[64];
	__u32 kern_version;

	struct bpf_program *programs;
	size_t nr_programs;
	struct bpf_map *maps;
	size_t nr_maps;
	size_t maps_cap;

	char *kconfig;
	struct extern_desc *externs;
	int nr_extern;
	int kconfig_map_idx;
	int rodata_map_idx;

	bool loaded;
	bool has_subcalls;

	/*
	 * Information when doing elf related work. Only valid if fd
	 * is valid.
	 */
	struct {
		int fd;
		const void *obj_buf;
		size_t obj_buf_sz;
		Elf *elf;
		GElf_Ehdr ehdr;
		Elf_Data *symbols;
		Elf_Data *data;
		Elf_Data *rodata;
		Elf_Data *bss;
		Elf_Data *st_ops_data;
		size_t shstrndx; /* section index for section name strings */
		size_t strtabidx;
		struct {
			GElf_Shdr shdr;
			Elf_Data *data;
		} *reloc_sects;
		int nr_reloc_sects;
		int maps_shndx;
		int btf_maps_shndx;
		__u32 btf_maps_sec_btf_id;
		int text_shndx;
		int symbols_shndx;
		int data_shndx;
		int rodata_shndx;
		int bss_shndx;
		int st_ops_shndx;
	} efile;
	/*
	 * All loaded bpf_object is linked in a list, which is
	 * hidden to caller. bpf_objects__<func> handlers deal with
	 * all objects.
	 */
	struct list_head list;

	struct btf *btf;
	struct btf_ext *btf_ext;

	/* Parse and load BTF vmlinux if any of the programs in the object need
	 * it at load time.
	 */
	struct btf *btf_vmlinux;
	/* vmlinux BTF override for CO-RE relocations */
	struct btf *btf_vmlinux_override;
	/* Lazily initialized kernel module BTFs */
	struct module_btf *btf_modules;
	bool btf_modules_loaded;
	size_t btf_module_cnt;
	size_t btf_module_cap;

	void *priv;
	bpf_object_clear_priv_t clear_priv;

	char path[];
};
~~~



### 解析elf文件中的section

这一步涉及到的主要函数是bpf_object__elf_collect。收集ebpf涉及到的目标文件中的各个section。

1）确定符号表所在的section

2) section名称为下面的:

* "license" ，license信息保存到bpf_object.license
* "version"，内核版本信息保存到bpf_object.kern_version
* "maps" 包含了以老式方式定义的map。缺点：map中key和value的类型信息丢失。被"BTF Style map"取代
* ".maps" BTF Style map，btf 方式定义map（可选)
* ".BTF" btf数据
* ".BTF.ext" 包含CO-RE信息
* 类型为SHT_PROGBITS的section。包括：sh_flag为SHF_EXECINSTR 即包含可执行的机器指令或名称为".data"、".rodata"、".struct_ops"的section。若是包含可执行指令的section(sh_flag为SHF_EXECINSTR)，调用bpf_object__add_programs收集上述section中包含的函数。bpf_program保存函数的详细信息，包括函数的指令的位置(<font color=blue>*相对于所在section的位置，位置以指令条数计数非字节*</font>）、指令条数
* 类型为SHT_REL(重定位)的section。只包括三种类型: 包含机器指令的section(sh_flag为SHF_EXECINSTR)、名字为".rel.struct_ops"、".rel.maps"的section
* 类型为SHT_NOBITS 且名称为".bss"

3) 收集section ".BTF"、".BTF.ext"中的btf数据。1)解析".BTF"中字符串表在elf文件中的位置及大小，类型表中类型个数。将每个类型的相对于类型表的相对位置存在数组中方便后续查找；btf信息保存到bpf_object.btf 2）解析".BTF.ext"中的数据；若加载出错且bpf程序确实需要btf数据则上报错误。三种情况必需btf数据: elf中有 ".maps" section或".struct_ops" section 或有外部符号时

bpf_program的定义如下:

~~~c
/*
 * bpf_prog should be a better name but it has been used in
 * linux/filter.h.
 */
struct bpf_program {
	const struct bpf_sec_def *sec_def;
	char *sec_name;
	size_t sec_idx;
	/* this program's instruction offset (in number of instructions)
	 * within its containing ELF section
	 */
	size_t sec_insn_off;
	/* number of original instructions in ELF section belonging to this
	 * program, not taking into account subprogram instructions possible
	 * appended later during relocation
	 */
	size_t sec_insn_cnt;
	/* Offset (in number of instructions) of the start of instruction
	 * belonging to this BPF program  within its containing main BPF
	 * program. For the entry-point (main) BPF program, this is always
	 * zero. For a sub-program, this gets reset before each of main BPF
	 * programs are processed and relocated and is used to determined
	 * whether sub-program was already appended to the main program, and
	 * if yes, at which instruction offset.
	 */
	size_t sub_insn_off;

	char *name;
	/* sec_name with / replaced by _; makes recursive pinning
	 * in bpf_object__pin_programs easier
	 */
	char *pin_name;

	/* instructions that belong to BPF program; insns[0] is located at
	 * sec_insn_off instruction within its ELF section in ELF file, so
	 * when mapping ELF file instruction index to the local instruction,
	 * one needs to subtract sec_insn_off; and vice versa.
	 */
	struct bpf_insn *insns;
	/* actual number of instruction in this BPF program's image; for
	 * entry-point BPF programs this includes the size of main program
	 * itself plus all the used sub-programs, appended at the end
	 */
	size_t insns_cnt;

	struct reloc_desc *reloc_desc;
	int nr_reloc;
	int log_level;

	struct {
		int nr;
		int *fds;
	} instances;
	bpf_program_prep_t preprocessor;

	struct bpf_object *obj;
	void *priv;
	bpf_program_clear_priv_t clear_priv;

	bool load;
	enum bpf_prog_type type;
	enum bpf_attach_type expected_attach_type;
	int prog_ifindex;
	__u32 attach_btf_obj_fd;
	__u32 attach_btf_id;
	__u32 attach_prog_fd;
	void *func_info;
	__u32 func_info_rec_size;
	__u32 func_info_cnt;

	void *line_info;
	__u32 line_info_rec_size;
	__u32 line_info_cnt;
	__u32 prog_flags;
};
~~~



### 收集符号表中的的外部(extern)符号

函数：bpf_object__collect_externs(struct bpf_object *obj)

外部符号只来自于".ksym"、".kconfig" section。需要使用宏"\__kconfig"、"\__ksym"定义外部符号，两个宏的使用方法见https://docs.ebpf.io/ebpf-library/libbpf/ebpf/__kconfig/

1) 收集符号表中同时满足以下条件的外部符号:

* section index为 SHN_UNDEF

* 绑定属性为STB_GLOBAL 或STB_WEAK

* 类型为STT_NOTYPE

  收集的符号存储在数组bpf_object.externs中，以下是来自bpf_object__collect_externs的代码片段:

  ~~~c
  		ext = obj->externs;
  		ext = libbpf_reallocarray(ext, obj->nr_extern + 1, sizeof(*ext));
  		if (!ext)
  			return -ENOMEM;
  		obj->externs = ext;
  		ext = &ext[obj->nr_extern];
  		memset(ext, 0, sizeof(*ext));
  		obj->nr_extern++;
  ~~~

  

2) 在".BTF" section中定义了每个外部符号的类型信息。类型信息包括以下部分：

* 外部符号的名称

* 外部符号所在的section。section由".BTF"中类型为BTF_KIND_DATA_SEC的记录指定。目前外部符号所在section只能为".kconfig"或".ksyms"

  以下是来自bpf_object__collect_externs的代码片段:

  ~~~c
  		ext->sec_btf_id = find_extern_sec_btf_id(obj->btf, ext->btf_id);
  		if (ext->sec_btf_id <= 0) {
  			pr_warn("failed to find BTF for extern '%s' [%d] section: %d\n",
  				ext_name, ext->btf_id, ext->sec_btf_id);
  			return ext->sec_btf_id;
  		}
  		sec = (void *)btf__type_by_id(obj->btf, ext->sec_btf_id);
  		sec_name = btf__name_by_offset(obj->btf, sec->name_off);
  
  		if (strcmp(sec_name, KCONFIG_SEC) == 0) {
  			kcfg_sec = sec;
  			ext->type = EXT_KCFG;
  			ext->kcfg.sz = btf__resolve_size(obj->btf, t->type);
  			if (ext->kcfg.sz <= 0) {
  				pr_warn("failed to resolve size of extern (kcfg) '%s': %d\n",
  					ext_name, ext->kcfg.sz);
  				return ext->kcfg.sz;
  			}
  			ext->kcfg.align = btf__align_of(obj->btf, t->type);
  			if (ext->kcfg.align <= 0) {
  				pr_warn("failed to determine alignment of extern (kcfg) '%s': %d\n",
  					ext_name, ext->kcfg.align);
  				return -EINVAL;
  			}
  			ext->kcfg.type = find_kcfg_type(obj->btf, t->type,
  						        &ext->kcfg.is_signed);
  			if (ext->kcfg.type == KCFG_UNKNOWN) {
  				pr_warn("extern (kcfg) '%s' type is unsupported\n", ext_name);
  				return -ENOTSUP;
  			}
  		} else if (strcmp(sec_name, KSYMS_SEC) == 0) {
  			ksym_sec = sec;
  			ext->type = EXT_KSYM;
  			skip_mods_and_typedefs(obj->btf, t->type,
  					       &ext->ksym.type_id);
  		} else {
  			pr_warn("unrecognized extern section '%s'\n", sec_name);
  			return -ENOTSUP;
  		}
  ~~~

  

  extern_desc的定义:
  
  ~~~c
  struct extern_desc {
  	enum extern_type type;
  	int sym_idx;
  	int btf_id;
  	int sec_btf_id;
  	const char *name;
  	bool is_set;
  	bool is_weak;
  	union {
  		struct {
  			enum kcfg_type type;
  			int sz;
  			int align;
  			int data_off;
  			bool is_signed;
  		} kcfg;
  		struct {
  			unsigned long long addr;
  
  			/* target btf_id of the corresponding kernel var. */
  			int vmlinux_btf_id;
  
  			/* local btf_id of the ksym extern's type. */
  			__u32 type_id;
  		} ksym;
  	};
  };
  ~~~
  
  
  
  

### BTF中 DATASEC定义的变量的相对位置的修正

针对".BTF"中所有类型为BTF_KIND_DATASEC的项，每个BTF_KIND_DATASEC 后面跟随了btf_type.info.vlen个btf_var_secinfo记录。1）对每个bft_ver_secinfo.type指向的其他类型为BTF_KIND_VAR 的btf_type。若btf_var的连接属性非BTF_VAR_STATIC则根据变量名称从elf的符号表中找到该符号，用该符号的st_value(变量的虚拟地址)设置btf_var_secinfo.offset字段

BTF_KIND_DATASEC类型的格式如下:

~~~
btf_type  // btf_type.info.vlen 指定了btf_var_secinfo数量
btf_var_secinfo
btf_var_secinfo
...
~~~

btf_var_sectinfo的定义:

~~~c
/* BTF_KIND_DATASEC is followed by multiple "struct btf_var_secinfo"
 * to describe all BTF_KIND_VAR types it contains along with it's
 * in-section offset as well as size.
 */
struct btf_var_secinfo {
	__u32	type; //指向其他btf_type的索引id
	__u32	offset; //the in-section offset of the variable
	__u32	size; // the size of the variable in bytes
};
~~~

btf_var的定义:

~~~c
enum {
	BTF_VAR_STATIC = 0,
	BTF_VAR_GLOBAL_ALLOCATED = 1,
	BTF_VAR_GLOBAL_EXTERN = 2,
};

enum btf_func_linkage {
	BTF_FUNC_STATIC = 0,
	BTF_FUNC_GLOBAL = 1,
	BTF_FUNC_EXTERN = 2,
};

/* BTF_KIND_VAR is followed by a single "struct btf_var" to describe
 * additional information related to the variable such as its linkage.
 */
struct btf_var {
	__u32	linkage;
};
~~~

下图展示了描述map的类型信息的DATASEC的格式：

![image-20251210164019828](D:\个人笔记\doc\ebpf\libbpf\libbpf.assets\image-20251210164019828.png)

### 解析map

目标文件中定义的map都保存在数组bpf_object.maps中

#### 解析Legacy方式定义的map

1）调用bpf_object__init_user_maps收集所有以legacy方式定义的map。从elf的符号表中找到所有section index(st_shndx)为"maps"的索引的符号

老式map定义方式:

~~~c
struct bpf_map_def my_map = {
    .type = BPF_MAP_TYPE_HASH,
    .key_size = sizeof(int),
    .value_size = sizeof(int),
    .max_entries = 100,
    .map_flags = BPF_F_NO_PREALLOC,
} SEC("maps");
~~~



#### 解析BTF Style定义的map

2）调用bpf_object\__init_user_btf_maps收集"BTF Style"的map。若目标文件无".maps" section则结束处理。从".BTF"找到类型为BTF_KIND_DATASEC且名称为".maps"的记录，没找到则报错。该btf记录中包含所有map的btf id。针对每个map调用bpf_object__init_user_btf_map解析map的定义

bpf_object__init_user_btf_maps片段:

~~~c
nr_types = btf__get_nr_types(obj->btf);
	for (i = 1; i <= nr_types; i++) {
		t = btf__type_by_id(obj->btf, i);
		if (!btf_is_datasec(t))
			continue;
		name = btf__name_by_offset(obj->btf, t->name_off);
		if (strcmp(name, MAPS_ELF_SEC) == 0) {
			sec = t;
			obj->efile.btf_maps_sec_btf_id = i;
			break;
		}
	}

	if (!sec) {
		pr_warn("DATASEC '%s' not found.\n", MAPS_ELF_SEC);
		return -ENOENT;
	}

	vlen = btf_vlen(sec);
	for (i = 0; i < vlen; i++) {
		err = bpf_object__init_user_btf_map(obj, sec, i,
						    obj->efile.btf_maps_shndx,
						    data, strict,
						    pin_root_path);
		if (err)
			return err;
	}
~~~



bpf_object__init_user_btf_map的处理逻辑：

* 检查map名称是否有效，检查map定义所占空间是否超过 ".maps" section的大小
* 检查定义的map的是否为变量类型，即btf类型必须为BTF_KIND_VAR，连接属性必须为BTF_VAR_GLOBAL_ALLOCATED或BTF_VAR_STATIC
* 检查map的变量的类型必须为BTF_KIND_STRUCT
* 调用parse_btf_map_def解析定义map的结构体，检查结构体的"type"、"key"等成员是否合法



BTF Style map定义方式:

~~~c
struct my_value { int x, y, z; };

struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __type(key, int);
    __type(value, struct my_value);
    __uint(max_entries, 16);
} icmpcnt SEC(".maps");
~~~



3) 若elf中存在".data"、".rodata"、".bss"则创建 internal map并调用mmap映射到进程内存空间。全局变量包含在这些section中。全局变量实际以BPF_MAP_TYPE_ARRAY类型的map创建。以下是bpf_object__init_global_data_maps的代码片段

~~~c
	if (obj->efile.data_shndx >= 0) {
		err = bpf_object__init_internal_map(obj, LIBBPF_MAP_DATA,
						    obj->efile.data_shndx,
						    obj->efile.data->d_buf,
						    obj->efile.data->d_size);
		if (err)
			return err;
	}
~~~



bpf_object__init_internal_map的代码片段：

~~~c
	def = &map->def;
	def->type = BPF_MAP_TYPE_ARRAY;
	def->key_size = sizeof(int);
	def->value_size = data_sz;
	def->max_entries = 1;
	def->map_flags = type == LIBBPF_MAP_RODATA || type == LIBBPF_MAP_KCONFIG
			 ? BPF_F_RDONLY_PROG : 0;
	def->map_flags |= BPF_F_MMAPABLE;
~~~



4) 若存在类型为EXT_KCFG 即来自".kconfig"的外部符号，则创建类型为BPF_MAP_TYPE_ARRAY的internal map

~~~c
static int bpf_object__init_kconfig_map(struct bpf_object *obj)
{
	struct extern_desc *last_ext = NULL, *ext;
	size_t map_sz;
	int i, err;

	for (i = 0; i < obj->nr_extern; i++) {
		ext = &obj->externs[i];
		if (ext->type == EXT_KCFG)
			last_ext = ext;
	}

	if (!last_ext)
		return 0;

	map_sz = last_ext->kcfg.data_off + last_ext->kcfg.sz;
	err = bpf_object__init_internal_map(obj, LIBBPF_MAP_KCONFIG,
					    obj->efile.symbols_shndx,
					    NULL, map_sz);
	if (err)
		return err;

	obj->kconfig_map_idx = obj->nr_maps - 1;

	return 0;
}
~~~



5)若在btf中存在名称为".struct_ops"且类型为BTF_KIND_DATASEC的记录，则创建map (TODO)

### 收集重定位信息

bpf_object__collect_relos

1）若重定位指向的section 为".struct_ops"。TODO

2）若重定位指向的section为 ".maps"，只针对BPF_MAP_TYPE_ARRAY_OF_MAPS、BPF_MAP_TYPE_HASH_OF_MAPS两种类型的map。TODO

3）收集需要重定位的函数指令。对于在重定位section中并且在符号表中已经定义的符号sym(即重定位信息应用的符号，比如调用一个外部函数），根据GElf_Rel.r_offset 计算重定位应用的指令的索引（bpf中每个指令的大小固定为sizeof(struct bpf_insn) ) 。以下是计算指令索引的代码片段，来自bpf_object__collect_relos

~~~
insn_idx = rel.r_offset / BPF_INSN_SZ;
~~~

根据指令所在的section和指令索引找到指令归属的program。调整指令索引，idx 减去program的第一条指令的位置即bpf_program.sec_insn_off。根据指令类型调用bpf_program\__record_reloc将需要重定位的指令信息保存在bpf_program.reloc_desc数组中，以下是bpf_program__record_reloc的处理逻辑:

* 指令为BPF_JMP或BPF_CALL ，若bpf_insn.src_reg不是BPF_PSEUDO_CALL则报错。若符号所在的section 索引为0 或section索引号不等于".text" section的索引号，报错。若符号的sym.st_value不能整除sizeof(struct bpf_insn)则报错。设置reloc_desc.type 为RELO_CALL，reloc_desc.insn_idx 为上述计算的指令索引，reloc_desc.sym_off = sym->st_value。结束处理

~~~c
		reloc_desc->type = RELO_CALL;
		reloc_desc->insn_idx = insn_idx;
		reloc_desc->sym_off = sym->st_value;
		return 0;
~~~



* 指令不是BPF_LD、BPF_IMM、BPF_DW，报错。

* 若等待重定位的符号是外部符号,  reloc_desc.type设置为RELO_EXTERN，reloc_desc.sym_off 设置为外部符号在收集的外部符号数组中的位置(bpf_object.externs数组中的位置)。结束处理

  ~~~c
  		reloc_desc->type = RELO_EXTERN;
  		reloc_desc->insn_idx = insn_idx;
  		reloc_desc->sym_off = i; /* sym_off stores extern index */
  		return 0;
  ~~~

  

* 若待重定位的符号所在的section 的索引为0 或大于SHN_LORESERVE，报错

* 若待重定位的符号的section非".data"、".bss"、".rodata"、符号表，则认为该符号是某个定义的map。reloc_desc.type 设置为RELO_LD64，reloc_desc.insn_idx设置为指令索引，reloc_desc.map_idx设置为map在bpf_object.maps数组中的位置。结束处理

~~~c
		reloc_desc->type = RELO_LD64;
		reloc_desc->insn_idx = insn_idx;
		reloc_desc->map_idx = map_idx;
		reloc_desc->sym_off = 0; /* sym->st_value determines map_idx */
		return 0;
~~~

* 若待重定位符号的section非".data"、".bss"、".rodata"，则报错

  ~~~c
  	reloc_desc->type = RELO_DATA;
  	reloc_desc->insn_idx = insn_idx;
  	reloc_desc->map_idx = map_idx;
  	reloc_desc->sym_off = sym->st_value;
  	return 0;
  ~~~

  

bpf_insn定义如下:

~~~c
struct bpf_insn {
	__u8	code;		/* opcode */
	__u8	dst_reg:4;	/* dest register */
	__u8	src_reg:4;	/* source register */
	__s16	off;		/* signed offset */
	__s32	imm;		/* signed immediate constant */
};
~~~

重定位section中每个项的格式:

~~~c
typedef struct {
    Elf64_Addr      r_offset;  // 重定位目标地址（内存偏移）
    Elf64_Xword     r_info;    // 符号索引和重定位类型
} GElf_Rel;

~~~

reloc_desc记录重定位信息:

~~~c
enum reloc_type {
	RELO_LD64,
	RELO_CALL,
	RELO_DATA,
	RELO_EXTERN,
};
struct reloc_desc {
	enum reloc_type type;
	int insn_idx; //应用重定位的指令
	int map_idx; //待重定位的符号是map，map_idx指向bpf_object.maps中的位置索引
	int sym_off; //需要重定位的符号的实际位置么？？？
	bool processed;
};
~~~



## 加载目标文件到内核

### 探测内核是否支持BPF

调用bpf_object__probe_loading 加载BPF_PROG_TYPE_SOCKET_FILTER类型bpf program，检查内核是否支持BPF

###  读取vmlinux文件中的BTF信息

1) 检查是否需要加载vmlinux中的BTF数据。满足以下条件之一，则需要加载vmlinux中的btf数据:

* 若bpf目标文件包含".BTF.ext"且该section中包含CO-RE重定位信息。来自obj_needs_vmlinux_btf的代码片段：

  ~~~c
  	/* CO-RE relocations need kernel BTF */
  	if (obj->btf_ext && obj->btf_ext->core_relo_info.len)
  		return true;
  ~~~

* 若bpf目标文件包含外部符号即bpf_object.externs，且外部符号(类型为EXT_KSYM)来自".ksym" section。来自obj_needs_vmlinux_btf的代码片段：

~~~c
	/* Support for typed ksyms needs kernel BTF */
	for (i = 0; i < obj->nr_extern; i++) {
		const struct extern_desc *ext;

		ext = &obj->externs[i];
		if (ext->type == EXT_KSYM && ext->ksym.type_id)
			return true;
	}
~~~

* bpf_program类型为BPF_PROG_TYPE_STRUCT_OPS或BPF_PROG_TYPE_LSM。或者bpf_program.type为BPF_PROG_TYPE_TRACING且prog->attach_prog_fd为0

  ~~~c
  static bool prog_needs_vmlinux_btf(struct bpf_program *prog)
  {
  	if (prog->type == BPF_PROG_TYPE_STRUCT_OPS ||
  	    prog->type == BPF_PROG_TYPE_LSM)
  		return true;
  
  	/* BPF_PROG_TYPE_TRACING programs which do not attach to other programs
  	 * also need vmlinux BTF
  	 */
  	if (prog->type == BPF_PROG_TYPE_TRACING && !prog->attach_prog_fd)
  		return true;
  
  	return false;
  }
  ~~~




2) 调用libbpf_find_kernel_btf加载vmlinux文件中btf数据。保存到bpf_object.btf_vmlinux中

vmlinux文件路径:

~~~c
struct {
		const char *path_fmt;
		bool raw_btf;
	} locations[] = {
		/* try canonical vmlinux BTF through sysfs first */
		{ "/sys/kernel/btf/vmlinux", true /* raw BTF */ },
		/* fall back to trying to find vmlinux ELF on disk otherwise */
		{ "/boot/vmlinux-%1$s" },
		{ "/lib/modules/%1$s/vmlinux-%1$s" },
		{ "/lib/modules/%1$s/build/vmlinux" },
		{ "/usr/lib/modules/%1$s/kernel/vmlinux" },
		{ "/usr/lib/debug/boot/vmlinux-%1$s" },
		{ "/usr/lib/debug/boot/vmlinux-%1$s.debug" },
		{ "/usr/lib/debug/lib/modules/%1$s/vmlinux" },
	};
~~~



### 解析外部符号

调用bpf_object__resolve_externs解析外部符号

解析\__kconfig、\__ksym宏定义的外部符号。bpf_object__resolve_externs的代码片段：

~~~c
for(i = 0; i < obj->nr_extern; i++)
    if(ext->type == EXT_KCFG && strcmp(ext->name, "LINUX_KERNEL_VERSION") == 0){
        ...
} else if (ext->type == EXT_KCFG &&
			   strncmp(ext->name, "CONFIG_", 7) == 0) {
			need_config = true;
    } else if(ext->type == EXT_KSYM){
        	if (ext->ksym.type_id)
				need_vmlinux_btf = true;
			else
				need_kallsyms = true;
    }else{
        return -EINVAL;
    }
~~~



~~~c
#define __kconfig __attribute__((section(".kconfig")))
#define __ksym __attribute__((section(".ksyms")))
~~~



1）若外部符号来自__kconfig，则外部符号的值在文件/boot/config-内核版本号 或 /proc/config.gz中。读取文件给外部符号赋值

2) 若外部符号来自\__ksym，分两种情况：第一种外部符号来自/proc/kallsyms文件，从该文件中找到符号地址保存在extern_desc.ksym.addr。第二种外部符号来自vmlinux 的btf(need_vmlinux_btf为true)即extern_desc.ksym.type_id不为0，调用bpf_object\__resolve_ksyms_btf_id从vmlinux 的btf中找到其对应的类型id，并检查该外部符号的类型信息(来自elf的btf section) 是否兼容目标内核(vmlinux)中该符号的类型信息。从bpf_object.btf_vmlinux找到符号的btf id保存至extern_desc.vmlinux_btf_id字段。若不兼容则报错

bpf_object__resolve_ksyms_btf_id片段:

~~~c
static int bpf_object__resolve_ksyms_btf_id(struct bpf_object *obj)
{
	struct extern_desc *ext;
	int i, id;

	for (i = 0; i < obj->nr_extern; i++) {
		const struct btf_type *targ_var, *targ_type;
		__u32 targ_type_id, local_type_id;
		const char *targ_var_name;
		int ret;

		ext = &obj->externs[i];
		if (ext->type != EXT_KSYM || !ext->ksym.type_id)
			continue;

		id = btf__find_by_name_kind(obj->btf_vmlinux, ext->name,
					    BTF_KIND_VAR);
		if (id <= 0) {
			pr_warn("extern (ksym) '%s': failed to find BTF ID in vmlinux BTF.\n",
				ext->name);
			return -ESRCH;
		}
        ...
        ...
    }
~~~



类型兼容性检查由函数bpf_core_types_are_compat完成，兼容性的规则见函数注释部分。以下是代码片段:

~~~c
/* Check local and target types for compatibility. This check is used for
 * type-based CO-RE relocations and follow slightly different rules than
 * field-based relocations. This function assumes that root types were already
 * checked for name match. Beyond that initial root-level name check, names
 * are completely ignored. Compatibility rules are as follows:
 *   - any two STRUCTs/UNIONs/FWDs/ENUMs/INTs are considered compatible, but
 *     kind should match for local and target types (i.e., STRUCT is not
 *     compatible with UNION);
 *   - for ENUMs, the size is ignored;
 *   - for INT, size and signedness are ignored;
 *   - for ARRAY, dimensionality is ignored, element types are checked for
 *     compatibility recursively;
 *   - CONST/VOLATILE/RESTRICT modifiers are ignored;
 *   - TYPEDEFs/PTRs are compatible if types they pointing to are compatible;
 *   - FUNC_PROTOs are compatible if they have compatible signature: same
 *     number of input args and compatible return and argument types.
 * These rules are not set in stone and probably will be adjusted as we get
 * more experience with using BPF CO-RE relocations.
 */
static int bpf_core_types_are_compat(const struct btf *local_btf, __u32 local_id,
				     const struct btf *targ_btf, __u32 targ_id)
{
	const struct btf_type *local_type, *targ_type;
	int depth = 32; /* max recursion depth */

	/* caller made sure that names match (ignoring flavor suffix) */
	local_type = btf__type_by_id(local_btf, local_id);
	targ_type = btf__type_by_id(targ_btf, targ_id);
	if (btf_kind(local_type) != btf_kind(targ_type))
		return 0;
    ....
    ....
}
~~~

3) 检查所有外部符号是否已经完成解析

~~~c
	for (i = 0; i < obj->nr_extern; i++) {
		ext = &obj->externs[i];

		if (!ext->is_set && !ext->is_weak) {
			pr_warn("extern %s (strong) not resolved\n", ext->name);
			return -ESRCH;
		} else if (!ext->is_set) {
			pr_debug("extern %s (weak) not resolved, defaulting to zero\n",
				 ext->name);
		}
	}
~~~



extern_desc的定义:

~~~c
struct extern_desc {
	enum extern_type type;
	int sym_idx;
	int btf_id;
	int sec_btf_id;
	const char *name;
	bool is_set;
	bool is_weak;
	union {
		struct {
			enum kcfg_type type;
			int sz;
			int align;
			int data_off;
			bool is_signed;
		} kcfg;
		struct {
			unsigned long long addr;

			/* target btf_id of the corresponding kernel var. */
			int vmlinux_btf_id;

			/* local btf_id of the ksym extern's type. */
			__u32 type_id; //收集外部符号时，设置的类型id,指向elf文件中的btf 类型
		} ksym;
	};
};
~~~



### 加载elf中BTF信息到内核

bpf_object__sanitize_and_load_btf btf健康检查并加载到内核

1）检查elf是否包含BTF数据

2）内核是否支持btf数据。libbpf通过加载一个简单的btf数据来探测内核是否支持BTF

3) 内核是否支持BTF_KIND_FUNC、连接属性为global 的BTF_KIND_FUNC、BTF_KIND_DATASEC。若内核不支持上述类型的某些，拷贝一份btf数据，对拷贝调用bpf_object__sanitize_btf对上述类型的btf记录进行替换后再加载

* 若内核不支持BTF_KIND_DATASEC，

  * btf类型为BTF_KIND_VAR。BTF_KIND_VAR被替换为BTF_KIND_INT
  * btf类型为BTF_KIND_DATASEC，被替换为BTF_KIND_STRUCT

* 不支持BTF_KIND_FUNC

  * BTF_KIND_FUNC_PROTO被替换为BTF_KIND_ENUM
  * BTF_KIND_FUNC被替换为BTF_KIND_TYPEDEF

* 不支持全局类型的BTF_KIND_FUNC，替换为连接属性为"static"的BTF_KIND_FUNC。以下是来自bpf_object__sanitize_btf的片段

  ~~~c
   else if (!has_func_global && btf_is_func(t)) {
  			/* replace BTF_FUNC_GLOBAL with BTF_FUNC_STATIC */
  			t->info = BTF_INFO_ENC(BTF_KIND_FUNC, 0, 0);
  		}
  ~~~

4) 加载sanitize之后的btf到内核

### map sanitize

bpf_object__sanitize_maps

针对每个非"internal map"，1）通过加载一小段访问BPF_MAP_TYPE_ARRAY类型map的BPF_PROG_TYPE_SOCKET_FILTER 类型bpf 代码 检查内核是否支持bpf program访问map。

~~~c
static int bpf_object__sanitize_maps(struct bpf_object *obj)
{
	struct bpf_map *m;

	bpf_object__for_each_map(m, obj) {
		if (!bpf_map__is_internal(m))
			continue;
		if (!kernel_supports(FEAT_GLOBAL_DATA)) {
			pr_warn("kernel doesn't support global data\n");
			return -ENOTSUP;
		}
		if (!kernel_supports(FEAT_ARRAY_MMAP))
			m->def.map_flags ^= BPF_F_MMAPABLE;
	}

	return 0;
}

~~~



### 初始化struct ops maps (TODO)

bpf_object__init_kern_struct_ops_maps

### 创建maps

bpf_object__create_maps 创建map

1) 若bpf_map.pin_path不为空，调用bpf_object__reuse_map。

bpf_object__create_maps代码片段:

~~~c
	if (map->pin_path) {
			err = bpf_object__reuse_map(map);
			if (err) {
				pr_warn("map '%s': error reusing pinned map\n",
					map->name);
				goto err_out;
			}
		}
~~~

bpf_object__reuse_map处理逻辑:

* 调用bpf_obj_get根据bpf_map.pin_path获取被pin的map的fd
* 根据map的fd调用bpf_obj_get_info_by_fd获取map信息，检查带创建的map和被pin的map的类型是否兼容。不兼容则报错
* 若兼容则调用bpf_map__reuse_fd复用fd，并用被pin的map的类型信息设置当前待创建的map的信息

2)若bpf_map.fd大于0，跳过已经创建的map。否则调用bpf_object\___create_map创建map，创建失败则返回并报错。若map为internal map调用bpf_object\__populate_internal_map

~~~c
if (map->fd >= 0) {
			pr_debug("map '%s': skipping creation (preset fd=%d)\n",
				 map->name, map->fd);
		} else {
			err = bpf_object__create_map(obj, map);
			if (err)
				goto err_out;

			pr_debug("map '%s': created successfully, fd=%d\n",
				 map->name, map->fd);

    		//TODO:
			if (bpf_map__is_internal(map)) {
				err = bpf_object__populate_internal_map(obj, map);
				if (err < 0) {
					zclose(map->fd);
					goto err_out;
				}
			}
			//TODO:使用场景
			if (map->init_slots_sz) {
				err = init_map_slots(map);
				if (err < 0) {
					zclose(map->fd);
					goto err_out;
				}
			}
		}
~~~



3)若bpf_map.pin_path不为空且bpf_map.pinned为false，调用bpf_map__pin

bpf_object__create_maps代码片段:

~~~c
if (map->pin_path && !map->pinned) {
			err = bpf_map__pin(map, NULL);
			if (err) {
				pr_warn("map '%s': failed to auto-pin at '%s': %d\n",
					map->name, map->pin_path, err);
				zclose(map->fd);
				goto err_out;
			}
		}
~~~



~~~c
struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, __u64);
    __uint(pinning, LIBBPF_PIN_BY_NAME);
} pinmap SEC(".maps");
~~~



### 应用重定位

#### CO-RE重定位

1) 若bpf_object.bpf_ext(即".BTF.ext" section中的数据)存在CO-RE数据，调用bpf_object\__relocate_core应用CO-RE重定位信息。遍历bpf_object.btf_ext.core_relo_info.info指向的btf_ext_info_sec数组。以btf_ext_info_sec.sec_name_off 指向的section 的名称 在bpf_object.programes数组中找到相同名字的bpf_program。由此可以看出btf_ext_info_sec 保存对应的某个函数的CO-RE重定位信息(可能不是1:1关系)。以下是bpf_object__relocate_core的片段

~~~c
	seg = &obj->btf_ext->core_relo_info;
	for_each_btf_ext_sec(seg, sec) {
		sec_name = btf__name_by_offset(obj->btf, sec->sec_name_off);
		if (str_is_empty(sec_name)) {
			err = -EINVAL;
			goto out;
		}
		/* bpf_object's ELF is gone by now so it's not easy to find
		 * section index by section name, but we can find *any*
		 * bpf_program within desired section name and use it's
		 * prog->sec_idx to do a proper search by section index and
		 * instruction offset
		 */
		prog = NULL;
		for (i = 0; i < obj->nr_programs; i++) {
			prog = &obj->programs[i];
			if (strcmp(prog->sec_name, sec_name) == 0)
				break;
		}
        if (!prog) {
			pr_warn("sec '%s': failed to find a BPF program\n", sec_name);
			return -ENOENT;
		}
        ......
        ......
~~~



2) 然后，对找到的program，遍历btf_ext_info_sec.data指向的bpf_core_relo数组，根据bpf_core_relo.insn_off 找到指令所在的函数。调用bpf_core_apply_relo对函数的指令应用重定位信息。

bpf_core_apply_relo的算法:

~~~
/*
 * CO-RE relocate single instruction.
 *
 * The outline and important points of the algorithm:
 * 1. For given local type, find corresponding candidate target types.
 *    Candidate type is a type with the same "essential" name, ignoring
 *    everything after last triple underscore (___). E.g., `sample`,
 *    `sample___flavor_one`, `sample___flavor_another_one`, are all candidates
 *    for each other. Names with triple underscore are referred to as
 *    "flavors" and are useful, among other things, to allow to
 *    specify/support incompatible variations of the same kernel struct, which
 *    might differ between different kernel versions and/or build
 *    configurations.
 *
 *    N.B. Struct "flavors" could be generated by bpftool's BTF-to-C
 *    converter, when deduplicated BTF of a kernel still contains more than
 *    one different types with the same name. In that case, ___2, ___3, etc
 *    are appended starting from second name conflict. But start flavors are
 *    also useful to be defined "locally", in BPF program, to extract same
 *    data from incompatible changes between different kernel
 *    versions/configurations. For instance, to handle field renames between
 *    kernel versions, one can use two flavors of the struct name with the
 *    same common name and use conditional relocations to extract that field,
 *    depending on target kernel version.
 * 2. For each candidate type, try to match local specification to this
 *    candidate target type. Matching involves finding corresponding
 *    high-level spec accessors, meaning that all named fields should match,
 *    as well as all array accesses should be within the actual bounds. Also,
 *    types should be compatible (see bpf_core_fields_are_compat for details).
 * 3. It is supported and expected that there might be multiple flavors
 *    matching the spec. As long as all the specs resolve to the same set of
 *    offsets across all candidates, there is no error. If there is any
 *    ambiguity, CO-RE relocation will fail. This is necessary to accomodate
 *    imprefection of BTF deduplication, which can cause slight duplication of
 *    the same BTF type, if some directly or indirectly referenced (by
 *    pointer) type gets resolved to different actual types in different
 *    object files. If such situation occurs, deduplicated BTF will end up
 *    with two (or more) structurally identical types, which differ only in
 *    types they refer to through pointer. This should be OK in most cases and
 *    is not an error.
 * 4. Candidate types search is performed by linearly scanning through all
 *    types in target BTF. It is anticipated that this is overall more
 *    efficient memory-wise and not significantly worse (if not better)
 *    CPU-wise compared to prebuilding a map from all local type names to
 *    a list of candidate type names. It's also sped up by caching resolved
 *    list of matching candidates per each local "root" type ID, that has at
 *    least one bpf_core_relo associated with it. This list is shared
 *    between multiple relocations for the same type ID and is updated as some
 *    of the candidates are pruned due to structural incompatibility.
 */
~~~

根据bpf_core_relo.type_id在bpf_object.btf中找到需要重定位符号的类型信息及其类型名称、由bpf_core_relo.access_str_off指向的对该类型的访问模式字符串如"0:1:2"(最多64层间接访问)，然后调用bpf_core_parse_spec解析访问模式并校验访问模式的有效性。bpf_core_parse_spec的处理逻辑大致如下:

*  若重定位符号是访问某个类型，且bpf_core_relo.access_str_off指向的访问模式为"0"则结束处理。否则报错。什么类型是type_based？整型

~~~c
static bool core_relo_is_type_based(enum bpf_core_relo_kind kind)
{
	switch (kind) {
	case BPF_TYPE_ID_LOCAL:
	case BPF_TYPE_ID_TARGET:
	case BPF_TYPE_EXISTS:
	case BPF_TYPE_SIZE:
		return true;
	default:
		return false;
	}
}
~~~



* 若重定位符号为枚举类型，且满足以下三个条件: 符号类型为枚举类型；访问模式字符串长度为1(即待访问的枚举变量的多个枚举值中的索引)；枚举值索引不超过枚举值数目；则记录访问的枚举成员到bpf_core_accessor.name。否则出错

~~~c
static bool core_relo_is_enumval_based(enum bpf_core_relo_kind kind)
{
	switch (kind) {
	case BPF_ENUMVAL_EXISTS:
	case BPF_ENUMVAL_VALUE:
		return true;
	default:
		return false;
	}
}

~~~

bpf_core_parse_spec 代码片段:

~~~c
	if (core_relo_is_enumval_based(relo_kind)) {
		if (!btf_is_enum(t) || spec->raw_len > 1 || access_idx >= btf_vlen(t))
			return -EINVAL;

		/* record enumerator name in a first accessor */
		acc->name = btf__name_by_offset(btf, btf_enum(t)[access_idx].name_off);
		return 0;
	}
~~~



* 若非访问某个符号的某个字段，则报错。以下是bpf_core_parse_spec片段

~~~c
if (!core_relo_is_field_based(relo_kind))
		return -EINVAL;
~~~



~~~c
static bool core_relo_is_field_based(enum bpf_core_relo_kind kind)
{
	switch (kind) {
	case BPF_FIELD_BYTE_OFFSET:
	case BPF_FIELD_BYTE_SIZE:
	case BPF_FIELD_EXISTS:
	case BPF_FIELD_SIGNED:
	case BPF_FIELD_LSHIFT_U64:
	case BPF_FIELD_RSHIFT_U64:
		return true;
	default:
		return false;
	}
}

~~~



* 访问数组或结构体/union的某个成员。计算成员在结构体或数组中的位置(字节)。将访问模式的每一层涉及到的符号保存到bpf_core_spec.spec数组中，待访问的成员的偏移量保存到bpf_core_spec.bit_offset中(单位bit)



bpf_core_accessor、bpf_core_spec的定义:

~~~c
/* represents BPF CO-RE field or array element accessor */
struct bpf_core_accessor {
	__u32 type_id;		/* struct/union type or array element type */
	__u32 idx;		/* field index or array index */
	const char *name;	/* field name or NULL for array accessor */
};

struct bpf_core_spec {
	const struct btf *btf;
	/* high-level spec: named fields and array indices only */
	struct bpf_core_accessor spec[BPF_CORE_SPEC_MAX_LEN];
	/* original unresolved (no skip_mods_or_typedefs) root type ID */
	__u32 root_type_id;
	/* CO-RE relocation kind */
	enum bpf_core_relo_kind relo_kind;
	/* high-level spec length */
	int len;
	/* raw, low-level spec: 1-to-1 with accessor spec string */
	int raw_spec[BPF_CORE_SPEC_MAX_LEN];
	/* raw spec length */
	int raw_len;
	/* field bit offset represented by spec */
	__u32 bit_offset;
};
~~~



3) 访问模式解析校验完成后，检查重定位类型bpf_core_relo.kind。若重定位类型为BPF_TYPE_ID_LOCAL，则调用bpf_core_patch_insn结束处理。否则在存储候选符号的哈希表中查找候选符号，未找到则调用bpf_core_find_cands找到匹配该符号的候选者并保存到哈希表中。

<font color='red'> 什么是候选符号，即匹配待重定位符号的名称、类型信息的外部符号</font>

<font color='blue'> 可否利用从内核中查找外部符号的机制，使得同一个map可以跨多个bpf目标文件进行访问</font>

bpf_core_find_cands的处理过程:

* 调用bpf_core_add_cands从来自vmlinux(优先使用bpf_object.btf_vmlinux_override中查找，其次bpf_object.btf_vmlinux)的btf中查找候选符号，检查符号的名称、类型BTF_KIND_*是否匹配，找到的候选符号可能有多个。若查找过程出错则结束处理并报错

  bpf_core_find_cands片段:

~~~c
	/* Attempt to find target candidates in vmlinux BTF first */
	main_btf = obj->btf_vmlinux_override ?: obj->btf_vmlinux;
	err = bpf_core_add_cands(&local_cand, local_essent_len, main_btf, "vmlinux", 1, cands);
	if (err)
		goto err_out;

~~~



* 若找到候选符号，或者是从obj->btf_vmlinux_override(没找到)中查找的，则返回找到的符号。否则从调用load_module_btfs内核已经加载的btf模块中查找候选符号，bpf系统调用使用BPF_BTF_GET_NEXT_ID命令从内核中获取已经加载的btf

  bpf_core_find_cands片段:

  ~~~c
  	/* if vmlinux BTF has any candidate, don't got for module BTFs */
  	if (cands->len)
  		return cands;
  
  	/* if vmlinux BTF was overridden, don't attempt to load module BTFs */
  	if (obj->btf_vmlinux_override)
  		return cands;
  
  	/* now look through module BTFs, trying to still find candidates */
  	err = load_module_btfs(obj);
  	if (err)
  		goto err_out;
  ~~~

  

4)遍历找到的候选符号，进行以下处理

* 对每个候选符号调用bpf_core_spec_match检查访问模式是否匹配，并记录访问成员在候选符号中的信息。bpf_core_spec_match的处理过程：

  * 若重定位符号是基于类型的(core_relo_is_type_based)，调用bpf_core_types_are_compat检查类型是否兼容。

  ~~~c
  /* Check local and target types for compatibility. This check is used for
   * type-based CO-RE relocations and follow slightly different rules than
   * field-based relocations. This function assumes that root types were already
   * checked for name match. Beyond that initial root-level name check, names
   * are completely ignored. Compatibility rules are as follows:
   *   - any two STRUCTs/UNIONs/FWDs/ENUMs/INTs are considered compatible, but
   *     kind should match for local and target types (i.e., STRUCT is not
   *     compatible with UNION);
   *   - for ENUMs, the size is ignored;
   *   - for INT, size and signedness are ignored;
   *   - for ARRAY, dimensionality is ignored, element types are checked for
   *     compatibility recursively;
   *   - CONST/VOLATILE/RESTRICT modifiers are ignored;
   *   - TYPEDEFs/PTRs are compatible if types they pointing to are compatible;
   *   - FUNC_PROTOs are compatible if they have compatible signature: same
   *     number of input args and compatible return and argument types.
   * These rules are not set in stone and probably will be adjusted as we get
   * more experience with using BPF CO-RE relocations.
   */
   static int bpf_core_types_are_compat(const struct btf *local_btf, __u32 local_id,
  				     const struct btf *targ_btf, __u32 targ_id)
  {
  	....
  }
  ~~~

  

  *  重定位符号是枚举类型。检查重定位符号是否匹配目标枚举类型中某个成员的名称，若匹配则成功。也就是枚举类型的匹配忽略数值是否匹配。并将访问目标枚举类型的成员的位置信息记录bpf_core_spec中

  ~~~c
  if (core_relo_is_enumval_based(local_spec->relo_kind)) {
  		size_t local_essent_len, targ_essent_len;
  		const struct btf_enum *e;
  		const char *targ_name;
  
  		/* has to resolve to an enum */
  		targ_type = skip_mods_and_typedefs(targ_spec->btf, targ_id, &targ_id);
  		if (!btf_is_enum(targ_type))
  			return 0;
  
  		local_essent_len = bpf_core_essential_name_len(local_acc->name);
  
  		for (i = 0, e = btf_enum(targ_type); i < btf_vlen(targ_type); i++, e++) {
  			targ_name = btf__name_by_offset(targ_spec->btf, e->name_off);
  			targ_essent_len = bpf_core_essential_name_len(targ_name);
  			if (targ_essent_len != local_essent_len)
  				continue;
  			if (strncmp(local_acc->name, targ_name, local_essent_len) == 0) {
  				targ_acc->type_id = targ_id;
  				targ_acc->idx = i;
  				targ_acc->name = targ_name;
  				targ_spec->len++;
  				targ_spec->raw_spec[targ_spec->raw_len] = targ_acc->idx;
  				targ_spec->raw_len++;
  				return 1;
  			}
  		}
  		return 0;
  	}
  ~~~

  

  * 重定位符号非结构体或数组成员，报错并结束处理。数组：结构体/union:

  * 若重定位符号是对数组、结构体或union的成员的访问，则需要检查每一层访问是否兼容，以下是bpf_core_spec_match的片段:

    ~~~c
    for (i = 0; i < local_spec->len; i++, local_acc++, targ_acc++) {
    		targ_type = skip_mods_and_typedefs(targ_spec->btf, targ_id,
    						   &targ_id);
    		if (!targ_type)
    			return -EINVAL;
    
    		if (local_acc->name) {
    			matched = bpf_core_match_member(local_spec->btf,
    							local_acc,
    							targ_btf, targ_id,
    							targ_spec, &targ_id);
    			if (matched <= 0)
    				return matched;
    		} else {
    			/* for i=0, targ_id is already treated as array element
    			 * type (because it's the original struct), for others
    			 * we should find array element type first
    			 */
    			if (i > 0) {
    				const struct btf_array *a;
    				bool flex;
    
    				if (!btf_is_array(targ_type))
    					return 0;
    
    				a = btf_array(targ_type);
    				flex = is_flex_arr(targ_btf, targ_acc - 1, a);
    				if (!flex && local_acc->idx >= a->nelems)
    					return 0;
    				if (!skip_mods_and_typedefs(targ_btf, a->type,
    							    &targ_id))
    					return -EINVAL;
    			}
    
    			/* too deep struct/union/array nesting */
    			if (targ_spec->raw_len == BPF_CORE_SPEC_MAX_LEN)
    				return -E2BIG;
    
    			targ_acc->type_id = targ_id;
    			targ_acc->idx = local_acc->idx;
    			targ_acc->name = NULL;
    			targ_spec->len++;
    			targ_spec->raw_spec[targ_spec->raw_len] = targ_acc->idx;
    			targ_spec->raw_len++;
    
    			sz = btf__resolve_size(targ_btf, targ_id);
    			if (sz < 0)
    				return sz;
    			targ_spec->bit_offset += local_acc->idx * sz * 8;
    		}
    	}
    
    ~~~

    

  

* 调用bpf_core_calc_relo计算重定位符号和对应的符号的数值。若有多个候选符号，多个候选符号的类型信息也需要保持一致。

  * 若重定位符号满足core_relo_is_type_based，对重定位符号和对应的候选符号调用bpf_core_calc_type_relo计算重定位符号的值并分别保存在bpf_core_relo_res.orig_val、bpf_core_relo_res.new_val中，以下是bpf_core_calc_relo的片段

  ~~~c
  else if (core_relo_is_type_based(relo->kind)) {
  		err = bpf_core_calc_type_relo(relo, local_spec, &res->orig_val);
  		err = err ?: bpf_core_calc_type_relo(relo, targ_spec, &res->new_val);
  ~~~

  

  * 重定位符号满足core_relo_is_enumval_based，对重定位符号和对应的候选符号调用bpf_core_calc_enumval_relo计算重定位符号的值并分别保存在bpf_core_relo_res.orig_val、bpf_core_relo_res.new_val中，以下是bpf_core_calc_relo的片段

    ~~~c
    else if (core_relo_is_enumval_based(relo->kind)) {
    		err = bpf_core_calc_enumval_relo(relo, local_spec, &res->orig_val);
    		err = err ?: bpf_core_calc_enumval_relo(relo, targ_spec, &res->new_val);
    	}
    ~~~

    

  * 重定位符号满足core_relo_is_field_based





5) 调用bpf_core_patch_insn对指令进行修正

* 若指令类型为BPF_ALU、BPF_ALU64，使用候选符号的值修正指令的"immediate"部分。以下是bpf_core_patch_insn片段:

~~~c
	case BPF_ALU:
	case BPF_ALU64:
		if (BPF_SRC(insn->code) != BPF_K)
			return -EINVAL;
		if (res->validate && insn->imm != orig_val) {
			pr_warn("prog '%s': relo #%d: unexpected insn #%d (ALU/ALU64) value: got %u, exp %u -> %u\n",
				prog->name, relo_idx,
				insn_idx, insn->imm, orig_val, new_val);
			return -EINVAL;
		}
		orig_val = insn->imm;
		insn->imm = new_val;
		pr_debug("prog '%s': relo #%d: patched insn #%d (ALU/ALU64) imm %u -> %u\n",
			 prog->name, relo_idx, insn_idx,
			 orig_val, new_val);
		break;
~~~



* 若指令类型为BPF_LDX、BPF_ST、BPF_STX
* 若指令类型BPF_LD

以下是libbpf加载ebpf 目标文件应用重定位时的一些日志片段:

![image-20251212155402997](D:\个人笔记\doc\ebpf\libbpf\libbpf.assets\image-20251212155402997.png)



bpf_core_relo_kind的定义:

~~~c
/* bpf_core_relo_kind encodes which aspect of captured field/type/enum value
 * has to be adjusted by relocations.
 */
enum bpf_core_relo_kind {
	BPF_FIELD_BYTE_OFFSET = 0,	/* field byte offset */
	BPF_FIELD_BYTE_SIZE = 1,	/* field size in bytes */
	BPF_FIELD_EXISTS = 2,		/* field existence in target kernel */
	BPF_FIELD_SIGNED = 3,		/* field signedness (0 - unsigned, 1 - signed) */
	BPF_FIELD_LSHIFT_U64 = 4,	/* bitfield-specific left bitshift */
	BPF_FIELD_RSHIFT_U64 = 5,	/* bitfield-specific right bitshift */
	BPF_TYPE_ID_LOCAL = 6,		/* type ID in local BPF object */
	BPF_TYPE_ID_TARGET = 7,		/* type ID in target kernel */
	BPF_TYPE_EXISTS = 8,		/* type existence in target kernel */
	BPF_TYPE_SIZE = 9,		/* type size in bytes */ //sizeof(xx)
	BPF_ENUMVAL_EXISTS = 10,	/* enum value existence in target kernel */
	BPF_ENUMVAL_VALUE = 11,		/* enum value integer value */
};
~~~



btf_ext_info_sec的定义:

* info 指向btf_ext_info_sec数组
* len 整个数组长度，单位字节

~~~c
struct btf_ext_info {
	/*
	 * info points to the individual info section (e.g. func_info and
	 * line_info) from the .BTF.ext. It does not include the __u32 rec_size.
	 */
	void *info;
	__u32 rec_size;
	__u32 len;
};
~~~



btf_ext_info_sec

* data指向bpf_core_relo数组。
* num_info指定数组的维度。
* sec_name_off指向CO-RE重定位信息应用的section的名称(bpf program所在的section的名称)

~~~c
struct btf_ext_info_sec {
	__u32	sec_name_off;
	__u32	num_info;
	/* Followed by num_info * record_size number of bytes */
	__u8	data[];
};
~~~



bpf_core_relo的定义:

* access_str_off 定义了访问某个类型的模式。格式即语义见注释

~~~c
/* The minimum bpf_core_relo checked by the loader
 *
 * CO-RE relocation captures the following data:
 * - insn_off - instruction offset (in bytes) within a BPF program that needs
 *   its insn->imm field to be relocated with actual field info;
 * - type_id - BTF type ID of the "root" (containing) entity of a relocatable
 *   type or field;
 * - access_str_off - offset into corresponding .BTF string section. String
 *   interpretation depends on specific relocation kind:
 *     - for field-based relocations, string encodes an accessed field using
 *     a sequence of field and array indices, separated by colon (:). It's
 *     conceptually very close to LLVM's getelementptr ([0]) instruction's
 *     arguments for identifying offset to a field.
 *     - for type-based relocations, strings is expected to be just "0";
 *     - for enum value-based relocations, string contains an index of enum
 *     value within its enum type;
 *
 * Example to provide a better feel.
 *
 *   struct sample {
 *       int a;
 *       struct {
 *           int b[10];
 *       };
 *   };
 *
 *   struct sample *s = ...;
 *   int x = &s->a;     // encoded as "0:0" (a is field #0)
 *   int y = &s->b[5];  // encoded as "0:1:0:5" (anon struct is field #1, 
 *                      // b is field #0 inside anon struct, accessing elem #5)
 *   int z = &s[10]->b; // encoded as "10:1" (ptr is used as an array)
 *
 * type_id for all relocs in this example  will capture BTF type id of
 * `struct sample`.
 *
 * Such relocation is emitted when using __builtin_preserve_access_index()
 * Clang built-in, passing expression that captures field address, e.g.:
 *
 * bpf_probe_read(&dst, sizeof(dst),
 *		  __builtin_preserve_access_index(&src->a.b.c));
 *
 * In this case Clang will emit field relocation recording necessary data to
 * be able to find offset of embedded `a.b.c` field within `src` struct.
 *
 *   [0] https://llvm.org/docs/LangRef.html#getelementptr-instruction
 */
struct bpf_core_relo {
	__u32   insn_off;
	__u32   type_id;
	__u32   access_str_off;
	enum bpf_core_relo_kind kind;
};
~~~



bpf_core_relo_res:

~~~c
struct bpf_core_relo_res
{
	/* expected value in the instruction, unless validate == false */
	__u32 orig_val;
	/* new value that needs to be patched up to */
	__u32 new_val;
	/* relocation unsuccessful, poison instruction, but don't fail load */
	bool poison;
	/* some relocations can't be validated against orig_val */
	bool validate;
	/* for field byte offset relocations or the forms:
	 *     *(T *)(rX + <off>) = rY
	 *     rX = *(T *)(rY + <off>),
	 * we remember original and resolved field size to adjust direct
	 * memory loads of pointers and integers; this is necessary for 32-bit
	 * host kernel architectures, but also allows to automatically
	 * relocate fields that were resized from, e.g., u32 to u64, etc.
	 */
	bool fail_memsz_adjust;
	__u32 orig_sz;
	__u32 orig_type_id;
	__u32 new_sz;
	__u32 new_type_id;
};
~~~



bpf_core_spec的定义:

~~~c
struct bpf_core_spec {
	const struct btf *btf;
	/* high-level spec: named fields and array indices only */
	struct bpf_core_accessor spec[BPF_CORE_SPEC_MAX_LEN];
	/* original unresolved (no skip_mods_or_typedefs) root type ID */
	__u32 root_type_id;
	/* CO-RE relocation kind */
	enum bpf_core_relo_kind relo_kind;
	/* high-level spec length */
	int len;
	/* raw, low-level spec: 1-to-1 with accessor spec string */
	int raw_spec[BPF_CORE_SPEC_MAX_LEN];
	/* raw spec length */
	int raw_len;
	/* field bit offset represented by spec */
	__u32 bit_offset;
};
~~~



### 加载ebpf programs

调用bpf_object\__load_progs加载bpf_object.programs中的program。

1） 针对每个program调用bpf_object__sanitize_prog，检查program使用的bpf helper函数是否被内核支持

* BPF_FUNC_probe_read_kernel(id 113)、BPF_FUNC_probe_read_user（112）若这两个函数不被支持，则替换为BPF_FUNC_probe_read
* BPF_FUNC_probe_read_kernel_str、BPF_FUNC_probe_read_user_str不被支持，则替换为BPF_FUNC_probe_read_str

以下是bpf_object__saitize_prog函数:

~~~c
static int bpf_object__sanitize_prog(struct bpf_object* obj, struct bpf_program *prog)
{
	struct bpf_insn *insn = prog->insns;
	enum bpf_func_id func_id;
	int i;

	for (i = 0; i < prog->insns_cnt; i++, insn++) {
		if (!insn_is_helper_call(insn, &func_id))
			continue;

		/* on kernels that don't yet support
		 * bpf_probe_read_{kernel,user}[_str] helpers, fall back
		 * to bpf_probe_read() which works well for old kernels
		 */
		switch (func_id) {
		case BPF_FUNC_probe_read_kernel:
		case BPF_FUNC_probe_read_user:
			if (!kernel_supports(FEAT_PROBE_READ_KERN))
				insn->imm = BPF_FUNC_probe_read;
			break;
		case BPF_FUNC_probe_read_kernel_str:
		case BPF_FUNC_probe_read_user_str:
			if (!kernel_supports(FEAT_PROBE_READ_KERN))
				insn->imm = BPF_FUNC_probe_read_str;
			break;
		default:
			break;
		}
	}
	return 0;
}
~~~



2) 调用bpf_program_load加载每个program

bpf_object__load_progs片段:

~~~c
	for (i = 0; i < obj->nr_programs; i++) {
		prog = &obj->programs[i];
		if (prog_is_subprog(obj, prog))
			continue;
		if (!prog->load) {
			pr_debug("prog '%s': skipped loading\n", prog->name);
			continue;
		}
		prog->log_level |= log_level;
		err = bpf_program__load(prog, obj->license, obj->kern_version);
		if (err)
			return err;
	}
~~~

bpf_program_load处理逻辑：

* 若bpf_program.type为BPF_PROG_TYPE_TRACING、BPF_PROG_TYPE_LSM、BPF_PROG_TYPE_EXT，且bpf_programe.attach_btf_id为0，则调用libbpf_find_attach_btf_id获取btf信息

* 若bpf_program.preprocessor(预处理器)为空调用load_program处理，以下是bpf_program_load片段

  ~~~c
  	if (!prog->preprocessor) {
  		if (prog->instances.nr != 1) {
  			pr_warn("prog '%s': inconsistent nr(%d) != 1\n",
  				prog->name, prog->instances.nr);
  		}
  		err = load_program(prog, prog->insns, prog->insns_cnt,
  				   license, kern_ver, &fd);
  		if (!err)
  			prog->instances.fds[0] = fd;
  		goto out;
  	}
  ~~~



* prog->preprocessor不为空，调用预处理器。然后调用load_program处理

## 总结

1) 可否利用在应用CO-RE重定位时，会从内核中已经加载的BTF模块中查找外部符号的机制，使得同一个map可以跨多个bpf目标文件进行访问

2)使用map pin跨多个目标文件访问同一个map，应该可行。下面引用的https://docs.ebpf.io/linux/concepts/pinning/

~~~
Pins are usually used as an easy method of sharing or transferring a BPF object between processes or applications.
~~~

3)在ebpf中使用全局变量，用户程序通过全局变量配置ebpf 程序

4) "\__ksym"、"\__kconfig"宏的使用

## BTF

见 https://www.kernel.org/doc/html/latest/bpf/btf.html

BTF数据分布在elf的".BTF"、".BTF.ext"两个section中。BTF(BPF Type Format)是一种对 BPF 程序和map的调试信息编码的元数据格式。专注于描述数据类型、定义的子程序的函数信息。提供的调试信息可用于map可视化、函数签名、辅助生成带注释的源码、JIT-ed code、校验日志

### .BTF

".BTF" section的数据格式：头部| 类型信息表| 字符串表。字符串表的格式跟elf中字符串表的格式一样。类型信息表格式: 类型1|类型2|类型3；每个类型的大小由类型决定

btf_header定义了btf的头部格式

~~~c
#define BTF_MAGIC 0xeB9F
#define BTF_VERSION 1
struct btf_header {
	__u16	magic;
	__u8	version;
	__u8	flags;
	__u32	hdr_len;

	/* All offsets are in bytes relative to the end of this header */
	__u32	type_off;	/* offset of type section	*/
	__u32	type_len;	/* length of type section	*/
	__u32	str_off;	/* offset of string section	*/
	__u32	str_len;	/* length of string section	*/
};
~~~



btf_type定义了每种btf类型

~~~c
/* Max # of type identifier */
#define BTF_MAX_TYPE	0x000fffff
/* Max offset into the string section */
#define BTF_MAX_NAME_OFFSET	0x00ffffff
/* Max # of struct/union/enum members or func args */
#define BTF_MAX_VLEN	0xffff


#define BTF_INFO_KIND(info)	(((info) >> 24) & 0x0f)
#define BTF_INFO_VLEN(info)	((info) & 0xffff)
#define BTF_INFO_KFLAG(info)	((info) >> 31)

#define BTF_KIND_UNKN		0	/* Unknown	*/
#define BTF_KIND_INT		1	/* Integer	*/
#define BTF_KIND_PTR		2	/* Pointer	*/
#define BTF_KIND_ARRAY		3	/* Array	*/
#define BTF_KIND_STRUCT		4	/* Struct	*/
#define BTF_KIND_UNION		5	/* Union	*/
#define BTF_KIND_ENUM		6	/* Enumeration	*/
#define BTF_KIND_FWD		7	/* Forward	*/
#define BTF_KIND_TYPEDEF	8	/* Typedef	*/
#define BTF_KIND_VOLATILE	9	/* Volatile	*/
#define BTF_KIND_CONST		10	/* Const	*/
#define BTF_KIND_RESTRICT	11	/* Restrict	*/
#define BTF_KIND_FUNC		12	/* Function	*/
#define BTF_KIND_FUNC_PROTO	13	/* Function Proto	*/
#define BTF_KIND_VAR		14	/* Variable	*/
#define BTF_KIND_DATASEC	15	/* Section	*/
#define BTF_KIND_MAX		BTF_KIND_DATASEC
#define NR_BTF_KINDS		(BTF_KIND_MAX + 1)

struct btf_type {
	__u32 name_off;
	/* "info" bits arrangement
	 * bits  0-15: vlen (e.g. # of struct's members)
	 * bits 16-23: unused
	 * bits 24-27: kind (e.g. int, ptr, array...etc)
	 * bits 28-30: unused
	 * bit     31: kind_flag, currently used by
	 *             struct, union and fwd
	 */
	__u32 info;
	/* "size" is used by INT, ENUM, STRUCT, UNION and DATASEC.
	 * "size" tells the size of the type it is describing.
	 *
	 * "type" is used by PTR, TYPEDEF, VOLATILE, CONST, RESTRICT,
	 * FUNC, FUNC_PROTO and VAR.
	 * "type" is a type_id referring to another type.
	 */
	union {
		__u32 size;
		__u32 type;
	};
};


~~~



#### BTF定义的数据 类型



##### BTF_KIND_ARRAY

- `struct btf_type` encoding requirement:

  `name_off`: 0

  `info.kind_flag`: 0

  `info.kind`: BTF_KIND_ARRAY

  `info.vlen`: 0

  `size/type`: 0, not used

`btf_type` is followed by one `struct btf_array`:

```
struct btf_array {
    __u32   type;
    __u32   index_type;
    __u32   nelems;
};
```

- The `struct btf_array` encoding:

  `type`: the element type

  `index_type`: the index type

  `nelems`: the number of elements for this array (`0` is also allowed).

The `index_type` can be any regular int type (`u8`, `u16`, `u32`, `u64`, `unsigned __int128`). The original design of including `index_type` follows DWARF, which has an `index_type` for its array type. Currently in BTF, beyond type verification, the `index_type` is not used.

The `struct btf_array` allows chaining through element type to represent multidimensional arrays. For example, for `int a[5][6]`, the following type information illustrates the chaining:

> - [1]: int
>
> - [2]: array, `btf_array.type = [1]`, `btf_array.nelems = 6`
>
> - [3]: array, `btf_array.type = [2]`, `btf_array.nelems = 5`

Currently, both pahole and llvm collapse multidimensional array into one-dimensional array, e.g., for `a[5][6]`, the `btf_array.nelems` is equal to `30`. This is because the original use case is map pretty print where the whole array is dumped out so one-dimensional array is enough. As more BTF usage is explored, pahole and llvm can be changed to generate proper chained representation for multidimensional arrays

##### BTF_KIND_ENUM

`struct btf_type` encoding requirement:

* `name_off`: 0 or offset to a valid C identifier

* `info.kind_flag`: 0 for unsigned, 1 for signed

* `info.kind`: BTF_KIND_ENUM

* `info.vlen`: number of `enum values``

* ``size`: 1/2/4/8

`btf_type` is followed by `info.vlen` number of `struct btf_enum`.:

```
struct btf_enum {
    __u32   name_off;
    __s32   val;
};
```

- The `btf_enum` encoding:

  `name_off`: offset to a valid C identifier`val`: any value

If the original `enum value` is signed and the size is less than 4, that value will be sign extended into 4 bytes. If the size is 8, the value will be truncated into 4 bytes.

![image-20251223162531781](D:\个人笔记\doc\ebpf\libbpf\libbpf.assets\image-20251223162531781.png)

##### BTF_KIND_TYPEDEF

struct btf_type` encoding requirement:

* `name_off`: offset to a valid C identifier
* `info.kind_flag`: 0
* `info.kind`: BTF_KIND_TYPEDEF
* `info.vlen`: 0
* `type`: the type which can be referred by name at `name_off`

No additional type data follow `btf_type`.

以下是来自bpf 目标文件中的btf信息片段:

~~~
...
[9] TYPEDEF 'size_t' type_id=10
[10] TYPEDEF '__kernel_size_t' type_id=11
[11] TYPEDEF '__kernel_ulong_t' type_id=12
[12] INT 'long unsigned int' size=8 bits_offset=0 nr_bits=64 encoding=(none)
...

~~~

#####  BTF_KIND_VOLATILE[¶](https://www.kernel.org/doc/html/latest/bpf/btf.html#btf-kind-volatile)

struct btf_type` encoding requirement:

* `name_off`: 0

* `info.kind_flag`: 0

* `info.kind`: BTF_KIND_VOLATILE

* `info.vlen`: 0

* `type`: the type with `volatile` qualifier

No additional type data follow `btf_type`.

#####  BTF_KIND_CONST

struct btf_type` encoding requirement:

* `name_off`: 0

* `info.kind_flag`: 0

* `info.kind`: BTF_KIND_CONST

* `info.vlen`: 0

* `type`: the type with `const` qualifier

No additional type data follow `btf_type`.

~~~
[445] CONST '(anon)' type_id=892
[446] PTR '(anon)' type_id=893
[447] PTR '(anon)' type_id=448
[448] CONST '(anon)' type_id=909
[449] PTR '(anon)' type_id=450
[450] CONST '(anon)' type_id=866
....

[909] FWD 'net_device_ops' fwd_kind=struct
[910] FWD 'netdev_queue' fwd_kind=struct

~~~



##### BTF_KIND_RESTRICT

`struct btf_type` encoding requirement:

* `name_off`: 0

* `info.kind_flag`: 0

* `info.kind`: BTF_KIND_RESTRICT

* `info.vlen`: 0

* `type`: the type with `restrict` qualifier

No additional type data follow `btf_type`.

##### BTF_KIND_UNION/STRUCT

- `struct btf_type` encoding requirement:

  `name_off`: 0 or offset to a valid C identifier`info.kind_flag`: 0 or 1`info.kind`: BTF_KIND_STRUCT or BTF_KIND_UNION`info.vlen`: the number of struct/`union members``info.size`: the size of the struct/`union in` bytes

`btf_type` is followed by `info.vlen` number of `struct btf_member`.:

```
struct btf_member {
    __u32   name_off;
    __u32   type;
    __u32   offset;
};
```

- `struct btf_member` encoding:

  `name_off`: offset to a valid C identifier`type`: the member type`offset`: <see below>

If the type info `kind_flag` is not set, the offset contains only bit offset of the member. Note that the base type of the bitfield can only be int or `enum type`. If the bitfield size is 32, the base type can be either int or `enum type`. If the bitfield size is not 32, the base type must be int, and int type `BTF_INT_BITS()` encodes the bitfield size.

If the `kind_flag` is set, the `btf_member.offset` contains both member bitfield size and bit offset. The bitfield size and bit offset are calculated as below.:

```
#define BTF_MEMBER_BITFIELD_SIZE(val)   ((val) >> 24)
#define BTF_MEMBER_BIT_OFFSET(val)      ((val) & 0xffffff)
```

In this case, if the base type is an int type, it must be a regular int type:

> - `BTF_INT_OFFSET()` must be 0.
> - `BTF_INT_BITS()` must be equal to `{1,2,4,8,16} * 8`.

来自btf的片段:

~~~
[744] STRUCT 'nf_conntrack_zone' size=4 vlen=3
        'id' type_id=127 bits_offset=0
        'flags' type_id=60 bits_offset=16
        'dir' type_id=60 bits_offset=24

~~~





### .BTF.ext

.BTF.ext section包括了func_info、line_info、CO-RE重定位信息

.BTF.ext在elf中的格式: 头部 | func_info | line_info | core_relo_info

func_info格式: record_size(4字节) | btf_ext_info_sec | btf_ext_info_sec。btf_ext_info_sec见struct btf_ext_info_sec的定义

line_info、core_relo_info的格式同func_info

btf_ext_header的定义：

~~~c
/*
 * The .BTF.ext ELF section layout defined as
 *   struct btf_ext_header
 *   func_info subsection
 *
 * The func_info subsection layout:
 *   record size for struct bpf_func_info in the func_info subsection
 *   struct btf_sec_func_info for section #1
 *   a list of bpf_func_info records for section #1
 *     where struct bpf_func_info mimics one in include/uapi/linux/bpf.h
 *     but may not be identical
 *   struct btf_sec_func_info for section #2
 *   a list of bpf_func_info records for section #2
 *   ......
 *
 * Note that the bpf_func_info record size in .BTF.ext may not
 * be the same as the one defined in include/uapi/linux/bpf.h.
 * The loader should ensure that record_size meets minimum
 * requirement and pass the record as is to the kernel. The
 * kernel will handle the func_info properly based on its contents.
 */
struct btf_ext_header {
	__u16	magic;
	__u8	version;
	__u8	flags;
	__u32	hdr_len;

	/* All offsets are in bytes relative to the end of this header */
	__u32	func_info_off;
	__u32	func_info_len;
	__u32	line_info_off;
	__u32	line_info_len;

	/* optional part of .BTF.ext header */
	__u32	core_relo_off;
	__u32	core_relo_len;
};

struct btf_ext_info {
	/*
	 * info points to the individual info section (e.g. func_info and
	 * line_info) from the .BTF.ext. It does not include the __u32 rec_size.
	 */
	void *info;
	__u32 rec_size;
	__u32 len;
};
~~~



func_info 的格式如下:

~~~
func_info_rec_size              /* __u32 value */
btf_ext_info_sec for section #1 /* func_info for section #1 */
btf_ext_info_sec for section #2 /* func_info for section #2 */
...
~~~

生成.BTF.ext时，**func_info_rec_size** 指定了bpf_func_info结构体的大小

`func_info_rec_size` specifies the size of `bpf_func_info` structure when .BTF.ext is generated. `btf_ext_info_sec`, defined below, is a collection of func_info for each specific ELF section.:

~~~c
struct btf_ext_info_sec {
	__u32	sec_name_off;
	__u32	num_info;
	/* Followed by num_info * record_size number of bytes */
	__u8	data[];
};

~~~



line_info格式如下:

~~~
line_info_rec_size              /* __u32 value */
btf_ext_info_sec for section #1 /* line_info for section #1 */
btf_ext_info_sec for section #2 /* line_info for section #2 */
...
~~~

`line_info_rec_size` specifies the size of `bpf_line_info` structure when .BTF.ext is generated.

The interpretation of `bpf_func_info->insn_off` and `bpf_line_info->insn_off` is different between kernel API and ELF API. For kernel API, the `insn_off` is the instruction offset in the unit of `struct bpf_insn`. For ELF API, the `insn_off` is the byte offset from the beginning of section (`btf_ext_info_sec->sec_name_off`).

core_relo格式如下:

~~~
core_relo_rec_size              /* __u32 value */
btf_ext_info_sec for section #1 /* core_relo for section #1 */
btf_ext_info_sec for section #2 /* core_relo for section #2 */
~~~

`core_relo_rec_size` specifies the size of `bpf_core_relo` structure when .BTF.ext is generated. All `bpf_core_relo` structures within a single `btf_ext_info_sec` describe relocations applied to section named by `btf_ext_info_sec->sec_name_off`.

## 参考资料

* Legacy Maps 和 BTF Style Maps的介绍 https://docs.ebpf.io/linux/concepts/maps/
* BPF_PROG_TYPE_STRUCT_OPS https://docs.ebpf.io/linux/program-type/BPF_PROG_TYPE_STRUCT_OPS/
* BTF https://www.kernel.org/doc/html/latest/bpf/btf.html

