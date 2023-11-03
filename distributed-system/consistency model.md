# consistency model

[TOC]

记录学习一致性模型过程中，对各种模型的一些理解及想法

## strict serializability

![image-20230818171632897](D:\个人笔记\doc\distributed-system\consistency model.assets\image-20230818171632897.png)

## linear consistency model

![image-20230818171606700](D:\个人笔记\doc\distributed-system\consistency model.assets\image-20230818171606700.png)

## sequential consistency model

第四版《分布式系统原理与泛型》一书中提到, sequential consistency model is not compositional。没理解 为什么是不可"compositional"。（第三版书中的图例是错误的)

![image-20230818164441166](D:\个人笔记\doc\distributed-system\consistency model.assets\image-20230818164441166.png)



![image-20230818164631104](D:\个人笔记\doc\distributed-system\consistency model.assets\image-20230818164631104.png)

对这段话“if we just consider the write and read operations on x, the fact that P1 reads the value "a" is perfectly consistent。The same holds for the operation R2(y)b by process P2。 However, when taken together, there is no way that we can  order the write operations on "x" and "y" such that we can have R1(X)a and R2(y)b(note that we need to keep the ordering as executed by each process) ”的理解。单从对"x"的读写操作来看，是顺序一致的。即在P1对应的data store上发生的操作是W2(x)b --> W1(x)a --> R1(x)a。类似P2对应的data store 上的操作是: W1(y)a --> W2(y)b -- > R2(y)b。但从整体来看（**每个data store需要看到P1、P2的全部操作)**，是不可能得到R1(x)a、R2(y)b这种结果的。能得到的结果如下图所示，这也是为什么 sequential consistency 不可" compositional"

![image-20230818163551317](D:\个人笔记\doc\distributed-system\consistency model.assets\image-20230818163551317.png)

