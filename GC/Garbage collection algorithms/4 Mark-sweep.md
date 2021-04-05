# 4 Mark-sweep(标记—清扫算法)

[TOC]



在第2章我们考虑了简单的以递归方式实现的引用计数、标记-回收和拷贝垃圾回收。在第3章，我们看到了如何移除或至少改良引用计数的一些缺点。在这一章和第6章，我们看看两种跟踪式回收算法的高效实现并且比较它们的相对优点

## 4.1 Comparisons with reference counting(和引用计数相比)

 标记-回收算法相较于引用计数由几个优势。对许多应用来说，最重要的是回收循环引用数据结构不需要特殊的操作。虽然在引用计数框架中存在处理循环的技术（第3章3.5节），不过它们基本上要么只适用于特殊情况（纯函数式语言的实现），或者依赖编程人员声明或编程范式，又或者增加删除指针的开销。就我们所知，no empricial comparisons of cyclic reference counting techniques with other methods of garbage collection have been published。另一方面，用引用计数作为主要的内存管理方法的几个系统，同样也使用了后备的标记—回收式算法来回收循环引用结构(例如. Modula-2+ [DeTreville, 1990a])

算法4.1  使用栈的标记算法

~~~
gc() = 
	mark_heap()
	sweep()

mark_heap() = 
	mark_stack = empty
	for R in Roots
		mark_bit(R) = marked
		push(R, mark_stack)
		mark()
mark() = 
	while mark_stack != empty
		N = pop(mark_stack)
		for M in Children(N)
			if mark_bit(*M) == unmarked
				mark_bit(*M) = marked
				if not atom(*M)
					push(*M, mark_stack)
~~~



## 4.2 丢失了



## 4.3 Pointer reversal(指针反转)

