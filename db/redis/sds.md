
# redis的字符串类型

```
struct sdshdr {
    int len; //buf中字符串长度,不包括字符'\0'
    int free; //剩余空闲空间
    char buf[];
};
```

预留空间时，根据新的预留空间大小确定需要拓展的额外空间.若预留空间未超过1MB, 则扩大2倍