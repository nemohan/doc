

# c 

[TOC]



## 编译

如何将git commit的sha1值写入到c语言的二进制中，可以通过gcc 的"-D"选项来定义宏的方式实现。

~~~c
 void version(void)
{
	printf("%s COMMIT:%s COMPILE_DATE:%s\n",AGENT_VERSION, COMMIT_INFO, COMPILE_TIMESTAMP);
}

~~~



以下是使用-D定义宏COMMIT_INFO的makefile片段:

~~~c
COMMIT_INFO=`git rev-parse --short HEAD`

COMMIT_TIMESTAMP=`date +%s`

\#CFLAGS+= -O3 -std=gnu99 -Wall  -g -pthread 

CFLAGS+= -std=gnu99 -Wall  -g -pthread -DCOMMIT_INFO=\"$(COMMIT_INFO)\" -DCOMPILE_TIMESTAMP=\"$(COMMIT_TIMESTAMP)\"
~~~



## 优雅的释放资源



~~~c
static inline void
cleanup_containerp (libcrun_container_t **c)
{
  libcrun_container_t *container = *c;
  libcrun_container_free (container);
}

#define cleanup_container __attribute__ ((cleanup (cleanup_containerp)))

int
crun_command_create (struct crun_global_arguments *global_args, int argc, char **argv, libcrun_error_t *err)
{
  int first_arg = 0, ret;
  cleanup_container libcrun_container_t *container = NULL;
  cleanup_free char *bundle_cleanup = NULL;
  cleanup_free char *config_file_cleanup = NULL;
    ......
}
~~~



![image-20240510162419712](D:\个人笔记\doc\programming language\c.assets\image-20240510162419712.png)

