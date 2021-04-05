# 5 Mark-Compact Garbage Collection

[TOC]

在第4章，我们看到标记—清扫垃圾回收和半空间—拷贝回收在某些情况下的竞争。尤其是，标记—清扫 有者更好的虚拟内存行为(virtual memory behaviour)。其主要的的缺点在于处理不同大小的的对象时导致的堆空间碎片化。在每次垃圾回收过后，堆空间可能有许多小的"洞"(hole)

## 5.1 Fragmentation(碎片化)

碎片化可能意味着在不扩展堆空间的情况下不能放下一个大的对象，因为没有哪个"洞"(hole)足够大以容纳新对象，虽然总的空闲空间可能足够。反过来，当分配小的对象时面临这样一个困境。就是应该使用哪种分配策略？应该是First-Fit策略么，有导致上述碎片化问题的风险，或者为新对象找到Best-Fit位置而付出代价的分配器？又或者使用Buddy system？这个问题并不只存在于标记—清扫算法中；分配不同大小的对象但不移动它们的任意系统都存在这个问题。引用计数和采用显示分配、释放动态内存的系统也存在这个困境(quandary)。

与此相反，紧缩(compact)堆内存的回收系统，包括半空间—拷贝回收器，有着非常小的内存分配开销。在这些系统中堆空间的分配策略可以被认为遵从栈(stack)的规则：使用的内存区域一直增长直到垃圾回收被触发，此时，寄希望于大部分被回收。对象的分配就会比较简单（the area of memory believed to be in use always grows until a garbage collection takes place when, hopefully, it shrinks by a large amount。Object allocation is then simple)。假设堆上有足够的空间，可能轻推指向“next-free-space"的指针对象大小就能分配一个对象（ an object may be allocated by nudging a "next-free-space" pointer by the size of the object)

<font color="red">一种具有吸引力的堆空间组织方式适用于非移动(non-moving)回收器，就是为每个大小不同的对象维护一个单独的free-list。在这种情况下，内存分配的开销不会比拷贝式回收器的大多少(正如第4章看到的）。虽然这种技术减轻了分配和释放固定大小对象的问题，本质上没有解决内存碎片化的问题。仍然存在一个free-list维护的区域已经满了，而其他free-list维护的区域是空闲的(while that maintained by another is comparatively empty)</font>



### <font color="red">Two-level allocation</font>

<font color="red">Two-level 分配器，比如被Boehm-Demers-Weiser回收器使用的，可以极大地减轻这个问题[Boehm and Weiser，1988]。在低层，分配器维护一个内存块列表(a list of blocks of memory)。假如用于某个大小的对象的free-list为空，可以为这个free-list分配一个块(block)。在较高层，每个free-list 从低层(low-level)获取的的块(blocks)中为单一大小对象分配空间。假设free-list不为空，总是能以较低的开销获得小对象。在垃圾回收的清扫阶段(sweep phase)若发现整个块(block)都是空闲的，这个块(block)可以归还给低层分配器（it can be returned to the low-level allocator to be recycled between the different free-lists)(4.5节讨论了清扫技术)。two-level分配系统的另一个优势是堆(heap)空间不必是连续的</font>

Two-level分配也不能完全消除碎片。分配超过单个块(block)大小的对象可能仍然困难，因为需要找到足够的连续的(adjacent)空闲块来容纳对象。针对这一问题的一个方案就是将大型对象分成固定大小的头部(fixed size header)和body来单独管理大型的对象(for eample, Kyoto Common Lisp uses this technique [Yuasa and Hagiya, 1985])。头部可以被标记—清扫回收器使用适当大小的free-list来管理，而body在单独的堆区域中分配。这个大型对象区域(Large Object Area) 被单独的策略管理；可能是某种使用压缩的回收算法。

Two-level分配也仍然允许被单个free-list管理的块(block)内的碎片化。在不妨碍分配的情况下(While not impeding allocation)，这种碎片化可能影响客户程序(client program)的空间局部性。在垃圾回收之后，空闲区域将会散布着存活对象(live objects)。这些空闲区域将会被客户程序的不同部分分配新对象填充，使得虚拟内存页包含不同年龄的对象。结果就是程序的工作集(working set)将会分散到超过必须的更多的页面, 可能导致大量的paging traffic。因为这个原因，简单的标记—清扫算法有时被认为不适合虚拟内存环境。工作集参数(woking set argument)和其他的非移动(non-moving)系统也相关，比如引用计数，或者不遵循局部性的移动对象的回收系统。一个例子就是5.3节要讨论的Two-Finger 紧缩(compaction)算法。（翻译的不咋滴）

然而，局部性问题可能并不像简单的分析表明的那样糟糕。Objects that are active at the same time are often created at the same time and may share similar lifetimes. If such clusters of objects do indeed live and die in groups, the objects are liely to be allocated closely, spatially as well as temporarily, and likely to be reclaimed at about the same time[Hayes,1991; Wilson, 1994]

## 5.2 Styles of compaction 

在这一章我们讨论紧缩(compacting)堆上的存活的数据结构的方法。紧缩(compaction)意味着，在紧缩阶段结束后，堆空间会被划分成两个连续的区域。一个区域存放所有活动的数据，而另一个区域则为空闲区域。为了区分于压缩(compressing)数据结构的技术，一些人将这种技术称为compactifying，

## 5.3 The Two-Finger Algorithm

