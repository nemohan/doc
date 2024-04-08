# radix tree

[TOC]



~~~c
typedef struct rax {
    raxNode *head;
    uint64_t numele;
    uint64_t numnodes;
} rax;

typedef struct raxNode {
    uint32_t iskey:1;     /* Does this node contain a key? */
    uint32_t isnull:1;    /* Associated value is NULL (don't store it). */
    uint32_t iscompr:1;   /* Node is compressed. */
    uint32_t size:29;     /* Number of children, or compressed string len. */
    /* Data layout is as follows:
     *
     * If node is not compressed we have 'size' bytes, one for each children
     * character, and 'size' raxNode pointers, point to each child node.
     * Note how the character is not stored in the children but in the
     * edge of the parents:
     *
     * [header iscompr=0][abc][a-ptr][b-ptr][c-ptr](value-ptr?)
     *
     * if node is compressed (iscompr bit is 1) the node has 1 children.
     * In that case the 'size' bytes of the string stored immediately at
     * the start of the data section, represent a sequence of successive
     * nodes linked one after the other, for which only the last one in
     * the sequence is actually represented as a node, and pointed to by
     * the current compressed node.
     *
     * [header iscompr=1][xyz][z-ptr](value-ptr?)
     *
     * Both compressed and not compressed nodes can represent a key
     * with associated data in the radix tree at any level (not just terminal
     * nodes).
     *
     * If the node has an associated key (iskey=1) and is not NULL
     * (isnull=0), then after the raxNode pointers pointing to the
     * children, an additional value pointer is present (as you can see
     * in the representation above as "value-ptr" field).
     */
    unsigned char data[]; //存放key和子节点的指针
} raxNode;
~~~



## 插入数据流程



radix tree为空时，如下图所示:



![image-20240305164940723](D:\个人笔记\doc\db\redis\4 radix tree.assets\image-20240305164940723.png)

插入abcd之后:

![image-20240306133301474](D:\个人笔记\doc\db\redis\4 radix tree.assets\image-20240306133301474.png)



插入abqf:

1 节点"abcd" 从'c'开是分裂，分裂成"ab"、"c"、"d"三部分

2 "c"成为分裂节点splitnode

3 节点"ab"的子节点指向"c"所在节点

4 节点"c"的子节点指向"d"所在节点

5 "q"插入到"c"所在节点, 子节点指向"f"所在节点

![image-20240307160437930](D:\个人笔记\doc\db\redis\4 radix tree.assets\image-20240307160437930.png)



插入abcdef

![image-20240307165828476](D:\个人笔记\doc\db\redis\4 radix tree.assets\image-20240307165828476.png)