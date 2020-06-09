# 基于GC的内存分配接口

#### GC 的一些定义

~~~c
/* GC information is stored BEFORE the object structure. */
typedef union _gc_head {
	struct {
		union _gc_head *gc_next;
		union _gc_head *gc_prev;
		Py_ssize_t gc_refs;
	} gc;
	long double dummy;  /* force worst-case alignment */
} PyGC_Head;

//_PyGC_generation0 实际的定义在 gcmodule.c文件种。如下
//PyGC_Head *_PyGC_generation0 = GEN_HEAD(0);
extern PyGC_Head *_PyGC_generation0;


//将新分配的对象放到
//_PyGC_generation0的gc.gc_next 和gc.gc_prev在初始化时，都指向_PyGC_generation0自身
//维护了一个双链表。每个新分配的对象放到了队列尾部
#define _PyObject_GC_TRACK(o) do { \
	PyGC_Head *g = _Py_AS_GC(o); \
	if (g->gc.gc_refs != _PyGC_REFS_UNTRACKED) \
		Py_FatalError("GC object already tracked"); \
	g->gc.gc_refs = _PyGC_REFS_REACHABLE; \
	g->gc.gc_next = _PyGC_generation0; \
	g->gc.gc_prev = _PyGC_generation0->gc.gc_prev; \
	g->gc.gc_prev->gc.gc_next = g; \
	_PyGC_generation0->gc.gc_prev = g; \
    } while (0);
~~~



#### PyObject_GC_New 版本1

PyObject_GC_New 是提供给外部分配内存的接口

在python2.5中，PyObject_GC_New有两个版本

~~~c
//在 pymemcompat.h 中的定义

/* If your object is a container you probably want to support the
   cycle collector, which was new in Python 2.0.

   Unfortunately, the interface to the collector that was present in
   Python 2.0 and 2.1 proved to be tricky to use, and so changed in
   2.2 -- in a way that can't easily be papered over with macros.

   This file contains macros that let you program to the 2.2 GC API.
   Your module will compile against any Python since version 1.5.2,
   but the type will only participate in the GC in versions 2.2 and
   up.  Some work is still necessary on your part to only fill out the
   tp_traverse and tp_clear fields when they exist and set tp_flags
   appropriately.

   It is possible to support both the 2.0 and 2.2 GC APIs, but it's
   not pretty and this comment block is too narrow to contain a
   desciption of what's required... */

#if PY_VERSION_HEX < 0x020200B1
#define PyObject_GC_New         PyObject_New
#define PyObject_GC_NewVar      PyObject_NewVar
#define PyObject_GC_Del         PyObject_Del
#define PyObject_GC_Track(op)
#define PyObject_GC_UnTrack(op)
#endif
~~~

#### 版本2

~~~c
//在objimpl.h中的定义
#define PyObject_GC_New(type, typeobj) \
		( (type *) _PyObject_GC_New(typeobj) )



//gcmodule.c  2.5 版本使用的=====================================
PyObject *
_PyObject_GC_New(PyTypeObject *tp)
{
    //定义见内存管理
	PyObject *op = _PyObject_GC_Malloc(_PyObject_SIZE(tp));
	if (op != NULL)
		op = PyObject_INIT(op, tp);
	return op;
}

~~~

