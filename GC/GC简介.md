# GC

### GC

什么是GC？GC是Garbage-Collection的简称，意即垃圾回收。GC是一种自动管理内存分的方式，另一种就就是手动分配、释放。用过C和C++的人对手动分配可能深有体会。

手动分配内存容易出现内存泄漏、悬挂指针等问题。GC的使用使得开发人员重点关注业务逻辑

#### 垃圾的定义

什么样的内存空间应该被当作垃圾回收呢？在生活当中不会再被使用的物品一般会被视为垃圾丢掉。在内存管理中类似，不会被使用的对象所占用的空间被视为垃圾。那么如何确定一个对象不会再被使用呢？这就比较困难甚至不可能的，但我们可以使用比较保守的方式，即能被跟踪到的对象，就可以认为不是垃圾，不能跟踪到的对象就是垃圾

### 常见的GC算法

* 标记-清除算法
* 复制算法
* 标记-压缩算法
* 引用计数算法

以及基于上面四种基本算法的变种：

* 分代回收算法
* 增量回收算法

#### 保守式GC和准确式GC

保守式GC: 一般指没有运行时系统(runtime system)支持，不能准确区分指针和非指针，将疑似指针的非指针当作指针类型。

~~~
A conservative (mark & sweep) garbage collector is one
that is able to collect memory without unambiguously
identify pointers at run time.
This is possible because, for a mark & sweep GC, an
approximation of the reachability graph is sufficient to
collect (some) garbage, as long as that approximation
includes the actual reachability graph.

A conservative GC assumes that everything that looks like a
pointer to an allocated object is a pointer to an allocated
object. This assumption is conservative — in that it can lead
to the retention of dead objects — but safe — in that it cannot
lead to the freeing of live objects.
It is however very important that the GC uses as many hints
as possible to avoid considering non-pointers as pointers,
as this can lead to memory being retained needlessly
~~~



准确式GC:

指针鉴别的一些技巧:

Several characteristics of the architecture or compiler can be
used to filter the set of potential pointers, e.g.:
– Many architectures require pointers to be aligned in
memory on 2 or 4 bytes boundaries. Therefore,
unaligned potential pointers can be ignored.
– Many compilers guarantee that if an object is reachable,
then there exists at least one pointer to its beginning.
Therefore, (potential) interior pointers can be ignored

### GC性能衡量指标

吞吐量、暂停时间、内存利用率



### GC 用到的一些定义

roots: 可以从全局变量、寄存器、栈(栈上的量)直接访问的对象被称为根



### 内存碎片化

外部碎片化: 内存有很多小块的空闲内存。这种情况下要求分配一个大的内存块时，不能满足要求

![1575813191821](E:\doc\GC\assets\1575813191821.png)

内部碎片化: 指提供的内存大于要求的内存时产生的碎片。比如要求分配3个字节大小的内存，实际提供了4字节大小的块，就会导致1个字节碎片。

![1575813305570](E:\doc\GC\assets\1575813305570.png)

### 近似或逼近的思想

GC算法中个人体会到的一种思想就是近似，比如无法确定哪些对象是不再被使用的，就通过找到所有可以跟踪到的对象，剩下的就是垃圾