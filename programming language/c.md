

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



## 遇到过的问题

### memset 设置的长度超过缓冲区大小导致" buffer overflow detected"

### memcpy拷贝的长度超过缓冲区大小导致SIGSEGV

### 未检查snprintf的返回值

~~~c
int update_agent_status(cJSON* stat)
{
	int len;
	int ret;
	char buffer[512];
	len = make_agent_status_json(buffer, sizeof(buffer), 0);
    //len超过buffer大小，导致zookeeper存储的内容包含乱码
	ret = zk_write_file(g_agent_status.agent_stat_file,buffer,len);
	if(ret != 0)
	{
		log(LOG_ERR,"zk_write_file %s faild!\n",g_agent_status.agent_stat_file);
		return -1;
	}
	return 0;
}
~~~



