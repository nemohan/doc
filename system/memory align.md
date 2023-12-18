# 内存对齐

[TOC]



用下面的程序测试，感觉内存是否对齐对性能影响不大

~~~c
void Munge64( void *data, uint32_t size , void *src) {
    uint64_t *data64 = (uint64_t*) data;
    uint64_t *data64End = data64 + (size >> 3); /* Divide size by 8. */

    uint64_t *data64_src = (uint64_t*)src;

    uint8_t * data_src = (uint8_t*)src;
    uint8_t *data_end = src + size;
    uint32_t count =0;
    while( data64 != data64End ) {
        memcpy(data64++, src, 8);
        //内存对齐访问版本
        //memcpy(data64++, data64_src++, 8);
        src+=11;
        if((uint8_t*)(src) > data_end){
            src = data_src;
        }
    }
}

int main(int argc, char **argv){
    uint32_t size = 1024 * 1024 * 10;
    struct timeval begin, end;  
    uint32_t total = 0; 
    for (int i = 0; i < 500; i++){
        void *data = malloc(1024 * 1024 * 10);
        void * src = malloc(1024 * 1024 * 10);
        gettimeofday(&begin, NULL);
        //Munge8(data, size, src);
        Munge64(data, size, src);
        //Munge16(data, size);
        gettimeofday(&end, NULL);
        uint64_t begin_t = begin.tv_sec * 1000 * 1000 + begin.tv_usec; 
        uint64_t end_t = end.tv_sec * 1000 * 1000 +end.tv_usec;
        total +=  (end_t - begin_t);
        free(data);
    }
    printf("%dms\n", total / 500 / 1000);
    return 0;
}
~~~



* 在现代cpu上运行的应用，访问非对齐的内存对性能还有多大影响（怎么设计测试用例)

* 在什么情况下，必须确保内存地址对齐

  

## 参考

* https://programmerclick.com/article/76132676395/
* https://lemire.me/blog/2012/05/31/data-alignment-for-speed-myth-or-reality/
* https://stackoverflow.com/questions/381244/purpose-of-memory-alignment/381368#381368