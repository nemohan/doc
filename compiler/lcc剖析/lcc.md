# lcc

[TOC]



lcc 是一个可变目标编译器，《a retargetable C compiler 》讲述的就是lcc的实现



## 初始化



### init

inits.c

~~~c
void init(int argc, char *argv[]) {
	{extern void input_init(int, char *[]); input_init(argc, argv);}
	{extern void main_init(int, char *[]); main_init(argc, argv);}
	{extern void type_init(int, char *[]); type_init(argc, argv);}
}
~~~



### input_init

input.c

* 设置inited, inited为静态变量，可以确保只初始化一次
* 调用main_init。main_init同样含有inited静态变量，确保只初始化一次

~~~c
void input_init(int argc, char *argv[]) {
	static int inited;

	if (inited)
		return;
	inited = 1;
	main_init(argc, argv);
	limit = cp = &buffer[MAXLINE+1];
	bsize = -1;
	lineno = 0;
	file = NULL;
	fillbuf();
	if (cp >= limit)
		cp = limit;
	nextline();

~~~



### main_init

* 解析命令行参数
* 打开C输入文件，并重定向到标准输入



### type_init

~~~c
void type_init(int argc, char *argv[]) {
	static int inited;
	int i;

	if (inited)
		return;
	inited = 1;
	if (!IR)
		return;
	for (i = 1; i < argc; i++) {
		int size, align, outofline;
		if (strncmp(argv[i], "-unsigned_char=", 15) == 0)
			IR->unsigned_char = argv[i][15] - '0';
#define xx(name) \
		else if (sscanf(argv[i], "-" #name "=%d,%d,%d", &size, &align, &outofline) == 3) { \
			IR->name.size = size; IR->name.align = align; \
			IR->name.outofline = outofline; }
	xx(charmetric)
	xx(shortmetric)
	xx(intmetric)
	xx(longmetric)
	xx(longlongmetric)
	xx(floatmetric)
	xx(doublemetric)
	xx(longdoublemetric)
	xx(ptrmetric)
	xx(structmetric)
#undef xx
	}
#define xx(v,name,op,metrics) v=xxinit(op,name,IR->metrics)
	xx(chartype,        "char",              IR->unsigned_char ? UNSIGNED : INT,charmetric);
	xx(doubletype,      "double",            FLOAT,   doublemetric);
	xx(floattype,       "float",             FLOAT,   floatmetric);
	xx(inttype,         "int",               INT,     intmetric);
	xx(longdouble,      "long double",       FLOAT,   longdoublemetric);
	xx(longtype,        "long int",          INT,     longmetric);
	xx(longlong,        "long long int",     INT,     longlongmetric);
	xx(shorttype,       "short",             INT,     shortmetric);
	xx(signedchar,      "signed char",       INT,     charmetric);
	xx(unsignedchar,    "unsigned char",     UNSIGNED,charmetric);
	xx(unsignedlong,    "unsigned long",     UNSIGNED,longmetric);
	xx(unsignedshort,   "unsigned short",    UNSIGNED,shortmetric);
	xx(unsignedtype,    "unsigned int",      UNSIGNED,intmetric);
	xx(unsignedlonglong,"unsigned long long",UNSIGNED,longlongmetric);
#undef xx
	{
		Symbol p;
		p = install(string("void"), &types, GLOBAL, PERM);
		voidtype = type(VOID, NULL, 0, 0, p);
		p->type = voidtype;
	}
	pointersym = install(string("T*"), &types, GLOBAL, PERM);
	pointersym->addressed = IR->ptrmetric.outofline;
	pointersym->u.limits.max.p = (void*)ones(8*IR->ptrmetric.size);
	pointersym->u.limits.min.p = 0;
	voidptype = ptr(voidtype);
	funcptype = ptr(func(voidtype, NULL, 1));
	charptype = ptr(chartype);
#define xx(v,t) if (v==NULL && t->size==voidptype->size && t->align==voidptype->align) v=t
	xx(unsignedptr,unsignedshort);
	xx(unsignedptr,unsignedtype);
	xx(unsignedptr,unsignedlong);
	xx(unsignedptr,unsignedlonglong);
	if (unsignedptr == NULL)
		unsignedptr = type(UNSIGNED, NULL, voidptype->size, voidptype->align, voidptype->u.sym);
	xx(signedptr,shorttype);
	xx(signedptr,inttype);
	xx(signedptr,longtype);
	xx(signedptr,longlong);
	if (signedptr == NULL)
		signedptr = type(INT, NULL, voidptype->size, voidptype->align, voidptype->u.sym);
#undef xx
	widechar = unsignedshort;
	for (i = 0; i < argc; i++) {
#define xx(name,type) \
		if (strcmp(argv[i], "-wchar_t=" #name) == 0) \
			widechar = type;
		xx(unsigned_char,unsignedchar)
		xx(unsigned_int,unsignedtype)
		xx(unsigned_short,unsignedshort)
	}
#undef xx
}
~~~



## input模块



### 一些全局变量的定义

~~~c
static char rcsid[] = "$Id$";

static void pragma(void);
static void resynch(void);

static int bsize;
static unsigned char buffer[MAXLINE+1 + BUFSIZE+1];
unsigned char *cp;	/* current input character */
char *file;		/* current input file name */
char *firstfile;	/* first input file */
unsigned char *limit;	/* points to last character + 1 */
char *line;		/* current line */
int lineno;		/* line number of current line */
~~~



### fillbuf

fillbuf 从文件读取BUFSIZE(4096)字节内容到buffer。不明白为啥是从MAXLINE+1开始

~~~c
void fillbuf(void) {
	if (bsize == 0)
		return;
	if (cp >= limit)
		cp = &buffer[MAXLINE+1];
	else
		{
			int n = limit - cp;
			unsigned char *s = &buffer[MAXLINE+1] - n;
			assert(s >= buffer);
			line = (char *)s - ((char *)cp - line);
			while (cp < limit)
				*s++ = *cp++;
			cp = &buffer[MAXLINE+1] - n;
		}
	if (feof(stdin))
		bsize = 0;
	else
        //为什么从MAXLINE+1开始，而不是buffer[0]
		bsize = fread(&buffer[MAXLINE+1], 1, BUFSIZE, stdin);
	if (bsize < 0) {
		error("read error\n");
		exit(EXIT_FAILURE);
	}
	limit = &buffer[MAXLINE+1+bsize];
	*limit = '\n';
}
~~~



