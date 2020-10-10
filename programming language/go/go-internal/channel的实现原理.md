channel

[TOC]



### channel 一些使用的注意事项

* **向空的channel发送消息，会阻塞但不会导致panic(简单的测试代码不行，可以检测到)**
* 向已经关闭的channel发送消息，会导致panic
* 关闭已经关闭或为空的channel导致panic
* **读取为空的channel也会阻塞，不会导致panic**
* 读取已经关闭的channel，会读取到对应类型的0值



#### 注意

* <font color="red">对于带缓冲的channel，且缓冲已经有一些消息。关闭channel之后再去读取，会读取到已经在队列的消息么?还是读取到对应类型的0值。仍会读取到在队列的消息</font>
* 协程因等待接收或发送消息进入等待状态。因channel关闭或可以接收、发送消息被唤醒
* 进入等待队列的协程，都是拿到消息或发送消息成功后，才被唤醒





### channel 的定义(runtime/chan.go)

golang 的channel机制是通过锁和等待队列实现的

三要素

* 锁
* 等待接收消息和等待发送消息的协程队列
* 消息队列（循环队列)



~~~go
type hchan struct {
	qcount   uint           // total data in the queue  channel中的消息数目
	dataqsiz uint           // size of the circular queue  channel缓存大小
	buf      unsafe.Pointer // points to an array of dataqsiz elements
	elemsize uint16
	closed   uint32
	elemtype *_type // element type
	sendx    uint   // send index  下一个可用的位置
	recvx    uint   // receive index 下一个读取位置
	recvq    waitq  // list of recv waiters 接收协程等待队列
	sendq    waitq  // list of send waiters 发送协程等待队列

	// lock protects all fields in hchan, as well as several
	// fields in sudogs blocked on this channel.
	//
	// Do not change another G's status while holding this lock
	// (in particular, do not ready a G), as this can deadlock
	// with stack shrinking.
	lock mutex
}
~~~



### 创建channel

* 参数t 包含了channel元素的类型， size则指定了channel缓冲大小
* 不支持超过16K大小的元素类型
* 缓冲大小不能小于0， 也不能超过`(_MaxMem-hchanSize)/elem.size`确定的上限
* 若元素类型不包含指针 或 缓冲大小为0，则消息队列和chan公用一块内存；若包含指针则消息队列和hchan使用独立的内存块

~~~go
func makechan(t *chantype, size int64) *hchan {
	elem := t.elem

	// compiler checks this but be safe.
	if elem.size >= 1<<16 {
		throw("makechan: invalid channel element type")
	}
	if hchanSize%maxAlign != 0 || elem.align > maxAlign {
		throw("makechan: bad alignment")
	}
	if size < 0 || int64(uintptr(size)) != size || (elem.size > 0 && uintptr(size) > (_MaxMem-hchanSize)/elem.size) {
		panic(plainError("makechan: size out of range"))
	}

    //不含指针或缓冲大小为0
	var c *hchan
	if elem.kind&kindNoPointers != 0 || size == 0 {
		// Allocate memory in one call.
		// Hchan does not contain pointers interesting for GC in this case:
		// buf points into the same allocation, elemtype is persistent.
		// SudoG's are referenced from their owning thread so they can't be collected.
		// TODO(dvyukov,rlh): Rethink when collector can move allocated objects.
		c = (*hchan)(mallocgc(hchanSize+uintptr(size)*elem.size, nil, true))
        //缓冲大小不为0 且 元素大小不为0
		if size > 0 && elem.size != 0 {
			c.buf = add(unsafe.Pointer(c), hchanSize)
		} else {//缓冲大小为0 或 元素大小为0
			// race detector uses this location for synchronization
			// Also prevents us from pointing beyond the allocation (see issue 9401).
			c.buf = unsafe.Pointer(c)
		}
	} else {
		c = new(hchan)
		c.buf = newarray(elem, int(size))
	}
	c.elemsize = uint16(elem.size)
	c.elemtype = elem
	c.dataqsiz = uint(size)

	if debugChan {
		print("makechan: chan=", c, "; elemsize=", elem.size, "; elemalg=", elem.alg, "; dataqsiz=", size, "\n")
	}
	return c
}
~~~



### 发送消息

发送消息有两种方式，即阻塞模式和非阻塞模式。阻塞模式下chansend的block参数为true,非阻塞模式block参数为false

##### 以阻塞模式发送消息

1.  若channel为nil,则阻塞
2. 检查channel是否已经关闭,若已经关闭则panic；
3. 查看`等待接收消息的协程队列`，若有协程等待消息，则调用send, 然后返回。
4. 检查channel的缓冲是否有空间，若还有空间则将消息放到缓冲中,然后返回。
5. 若缓冲没有空间，则将发送协程放入等待队列并进入等待状态
6. 被唤醒，若gp.param为nil，且hchan.closed为true,因为channel关闭被唤醒，panic；若gp.param不为nil,则说明发送消息成功



##### 非阻塞模式发送消息

1. 若channel为nil,立即返回
2. channel未关闭。满足以下两个条件之一立即返回，channel不带缓冲且没有协程在`接收消息协程等待队列`；2）channel带缓冲且缓冲满
3. 检查channel是否已经关闭，若关闭则panic
4. 检查`等待接收消息的协程队列`,若有协程等待接收消息，则调用send，然后返回
5. 若channel的缓冲还有剩余空间，则消息放到缓冲中，然后返回
6. 以上条件都不满足，立即返回

~~~go
// 通过channel 发送消息
// c<-x 
// entry point for c <- x from compiled code
//go:nosplit
func chansend1(t *chantype, c *hchan, elem unsafe.Pointer) {
	chansend(t, c, elem, true, getcallerpc(unsafe.Pointer(&t)))
}

/*
 * generic single channel send/recv
 * If block is not nil,
 * then the protocol will not
 * sleep but return if it could
 * not complete.
 *
 * sleep can wake up with g.param == nil
 * when a channel involved in the sleep has
 * been closed.  it is easiest to loop and re-run
 * the operation; we'll see that it's now closed.
 */

// c <-x 时, block为true. 用select 时，block为false
func chansend(t *chantype, c *hchan, ep unsafe.Pointer, block bool, callerpc uintptr) bool {
	if raceenabled {
		raceReadObjectPC(t.elem, ep, callerpc, funcPC(chansend))
	}
	if msanenabled {
		msanread(ep, t.elem.size)
	}

    //channel为空，导致阻塞
	if c == nil {
		if !block {
			return false
		}
		gopark(nil, nil, "chan send (nil chan)", traceEvGoStop, 2)
		throw("unreachable")
	}

	if debugChan {
		print("chansend: chan=", c, "\n")
	}

	if raceenabled {
		racereadpc(unsafe.Pointer(c), callerpc, funcPC(chansend))
	}

	// Fast path: check for failed non-blocking operation without acquiring the lock.
	//
	// After observing that the channel is not closed, we observe that the channel is
	// not ready for sending. Each of these observations is a single word-sized read
	// (first c.closed and second c.recvq.first or c.qcount depending on kind of channel).
	// Because a closed channel cannot transition from 'ready for sending' to
	// 'not ready for sending', even if the channel is closed between the two observations,
	// they imply a moment between the two when the channel was both not yet closed
	// and not ready for sending. We behave as if we observed the channel at that moment,
	// and report that the send cannot proceed.
	//
	// It is okay if the reads are reordered here: if we observe that the channel is not
	// ready for sending and then observe that it is not closed, that implies that the
	// channel wasn't closed during the first observation.
    //满足以下条件，立即返回
    //条件1：非阻塞 并且 尚未关闭 并且 不带缓冲 并且 等待读取的协程队列为空
    //条件2： 非阻塞 并且尚未关闭 并且 带缓冲 并且缓冲已满
	if !block && c.closed == 0 && ((c.dataqsiz == 0 && c.recvq.first == nil) ||
		(c.dataqsiz > 0 && c.qcount == c.dataqsiz)) {
		return false
	}

	var t0 int64
	if blockprofilerate > 0 {
		t0 = cputicks()
	}

	lock(&c.lock)

    //channel已经关闭
	if c.closed != 0 {
		unlock(&c.lock)
		panic(plainError("send on closed channel"))
	}

    //有gorutine等待消息时，直接拷贝到对应的gorutine上
    //假如有多个gorutine在等待。则第一个先等到消息
	if sg := c.recvq.dequeue(); sg != nil {
		// Found a waiting receiver. We pass the value we want to send
		// directly to the receiver, bypassing the channel buffer (if any).
		send(c, sg, ep, func() { unlock(&c.lock) })
		return true
	}

    //带缓存的channel,且缓存仍有剩余空间
	if c.qcount < c.dataqsiz {
		// Space is available in the channel buffer. Enqueue the element to send.
		qp := chanbuf(c, c.sendx)
		if raceenabled {
			raceacquire(qp)
			racerelease(qp)
		}
        // 将消息放到缓存qp的位置, sendx指向下一个可用位置
		typedmemmove(c.elemtype, qp, ep)
		c.sendx++
        
        //队列满
		if c.sendx == c.dataqsiz {
			c.sendx = 0
		}
		c.qcount++
		unlock(&c.lock)
		return true
	}

    
	if !block {
		unlock(&c.lock)
		return false
	}

	// Block on the channel. Some receiver will complete our operation for us.
	gp := getg()
	mysg := acquireSudog()
	mysg.releasetime = 0
	if t0 != 0 {
		mysg.releasetime = -1
	}
	// No stack splits between assigning elem and enqueuing mysg
	// on gp.waiting where copystack can find it.
	mysg.elem = ep
	mysg.waitlink = nil
	mysg.g = gp
	mysg.selectdone = nil
	mysg.c = c
	gp.waiting = mysg
	gp.param = nil
	c.sendq.enqueue(mysg)
    //疑问: 切换当前goroutine后，被切换的仍在p的运行队列中么？？？？？？？？
	goparkunlock(&c.lock, "chan send", traceEvGoBlockSend, 3)

	// someone woke us up.
	if mysg != gp.waiting {
		throw("G waiting list is corrupted")
	}
	gp.waiting = nil
	if gp.param == nil {
        //什么时候触发这个
		if c.closed == 0 {
			throw("chansend: spurious wakeup")
		}
		panic(plainError("send on closed channel"))
	}
	gp.param = nil
	if mysg.releasetime > 0 {
		blockevent(mysg.releasetime-t0, 2)
	}
	mysg.c = nil
	releaseSudog(mysg)
	return true
}



~~~



##### send

* 调用sendDirect将消息直接拷贝到等待接收消息的协程的地址上
* 唤醒正在等待的第一个协程

~~~go
// send processes a send operation on an empty channel c.
// The value ep sent by the sender is copied to the receiver sg.
// The receiver is then woken up to go on its merry way.
// Channel c must be empty and locked.  send unlocks c with unlockf.
// sg must already be dequeued from c.
// ep must be non-nil and point to the heap or the caller's stack.
func send(c *hchan, sg *sudog, ep unsafe.Pointer, unlockf func()) {
	if raceenabled {
		if c.dataqsiz == 0 {
			racesync(c, sg)
		} else {
			// Pretend we go through the buffer, even though
			// we copy directly. Note that we need to increment
			// the head/tail locations only when raceenabled.
			qp := chanbuf(c, c.recvx)
			raceacquire(qp)
			racerelease(qp)
			raceacquireg(sg.g, qp)
			racereleaseg(sg.g, qp)
			c.recvx++
			if c.recvx == c.dataqsiz {
				c.recvx = 0
			}
			c.sendx = c.recvx // c.sendx = (c.sendx+1) % c.dataqsiz
		}
	}
	if sg.elem != nil {
		sendDirect(c.elemtype, sg, ep)
		sg.elem = nil
	}
	gp := sg.g
	unlockf()
	gp.param = unsafe.Pointer(sg)
	if sg.releasetime != 0 {
		sg.releasetime = cputicks()
	}
	goready(gp, 4)
}
~~~



##### sendDirect 直接将消息拷贝到接收协程的内存上

~~~go
// Sends and receives on unbuffered or empty-buffered channels are the
// only operations where one running goroutine writes to the stack of
// another running goroutine. The GC assumes that stack writes only
// happen when the goroutine is running and are only done by that
// goroutine. Using a write barrier is sufficient to make up for
// violating that assumption, but the write barrier has to work.
// typedmemmove will call bulkBarrierPreWrite, but the target bytes
// are not in the heap, so that will not help. We arrange to call
// memmove and typeBitsBulkBarrier instead.

func sendDirect(t *_type, sg *sudog, src unsafe.Pointer) {
	// src is on our stack, dst is a slot on another stack.

	// Once we read sg.elem out of sg, it will no longer
	// be updated if the destination's stack gets copied (shrunk).
	// So make sure that no preemption points can happen between read & use.
	dst := sg.elem
	typeBitsBulkBarrier(t, uintptr(dst), uintptr(src), t.size)
	memmove(dst, src, t.size)
}
~~~



###  接收消息

下面的消息队列即channel所带的缓冲

#### 阻塞模式接收消息

 以阻塞模式接收消息，即block参数为true。分为以下几种情况:

1. 若channel为nil，则阻塞
2. 若通道已经关闭，且消息队列中没有消息，返回对应元素的0值；
3. 消息发送协程等待队列不为空，则调用recv从发送协程处直接接收消息；
4. 消息队列不为空,从消息队列中取消息，完成；
5. 将接收协程 放入消息等待队列，并进入等待状态
6. 被唤醒后，根据gp.param是否为nil确定被唤醒的原因。若gp.param是nil则表示因channel关闭被唤醒。若不为nil,则表示因接收到消息被唤醒

#### 非阻塞模式接收消息

以非阻塞模式接收消息。即chanrecv的block参数为false。分为以下几种情况:

1. 若channel是nil,则直接、返回；
2. 非阻塞且channel未关闭时又分为两种情况, 一，channel不带缓冲,且发送消息队列为空，立即返回。二，channel带缓冲，且缓冲中没有等待读取的消息，立即返回；
3. <font color="red">channel已经关闭且消息队列中没有消息,返回对应元素的0值</font>
4. 发送协程等待队列不为空，即有协程在等待发送消息。调用recv
5. <font color="red">消息队列不为空时，并没有检查channel是否已经关闭。即使关闭，也会从消息队列取得消息并返回</font>
6. 以上条件都不满足，立即返回



从上面的分析可以看出，在channel的消息队列不为空，且被关闭后。继续从channel读取消息时，仍能读取到消息队列上的消息

~~~go
// entry points for <- c from compiled code
//go:nosplit
func chanrecv1(t *chantype, c *hchan, elem unsafe.Pointer) {
	chanrecv(t, c, elem, true)
}

//go:nosplit
func chanrecv2(t *chantype, c *hchan, elem unsafe.Pointer) (received bool) {
	_, received = chanrecv(t, c, elem, true)
	return
}

// chanrecv receives on channel c and writes the received data to ep.
// ep may be nil, in which case received data is ignored.
// If block == false and no elements are available, returns (false, false).
// Otherwise, if c is closed, zeros *ep and returns (true, false).
// Otherwise, fills in *ep with an element and returns (true, true).
// A non-nil ep must point to the heap or the caller's stack.
func chanrecv(t *chantype, c *hchan, ep unsafe.Pointer, block bool) (selected, received bool) {
	// raceenabled: don't need to check ep, as it is always on the stack
	// or is new memory allocated by reflect.

	if debugChan {
		print("chanrecv: chan=", c, "\n")
	}

    //读取为空的channel
    //阻塞模式，进入阻塞
    //非阻塞模式，立即返回
	if c == nil {
		if !block {
			return
		}
		gopark(nil, nil, "chan receive (nil chan)", traceEvGoStop, 2)
		throw("unreachable")
	}

	// Fast path: check for failed non-blocking operation without acquiring the lock.
	//
	// After observing that the channel is not ready for receiving, we observe that the
	// channel is not closed. Each of these observations is a single word-sized read
	// (first c.sendq.first or c.qcount, and second c.closed).
	// Because a channel cannot be reopened, the later observation of the channel
	// being not closed implies that it was also not closed at the moment of the
	// first observation. We behave as if we observed the channel at that moment
	// and report that the receive cannot proceed.
	//
	// The order of operations is important here: reversing the operations can lead to
	// incorrect behavior when racing with a close.
    //非阻塞 并且 channel未关闭 并且 以下条件之一， 立即返回
    // 不带缓冲 并且 发送队列为空
    //带缓冲 并且 缓冲没有消息
	if !block && (c.dataqsiz == 0 && c.sendq.first == nil ||
		c.dataqsiz > 0 && atomic.Loaduint(&c.qcount) == 0) &&
		atomic.Load(&c.closed) == 0 {
		return
	}

	var t0 int64
	if blockprofilerate > 0 {
		t0 = cputicks()
	}

	lock(&c.lock)

    //通道已经关闭 且缓冲为空
	if c.closed != 0 && c.qcount == 0 {
		if raceenabled {
			raceacquire(unsafe.Pointer(c))
		}
		unlock(&c.lock)
		if ep != nil {
			typedmemclr(c.elemtype, ep)
		}
		return true, false
	}

    //case 1: channel不带缓冲。
    //case 2: channel带缓冲，且缓冲已满
	if sg := c.sendq.dequeue(); sg != nil {
		// Found a waiting sender. If buffer is size 0, receive value
		// directly from sender. Otherwise, receive from head of queue
		// and add sender's value to the tail of the queue (both map to
		// the same buffer slot because the queue is full).
		recv(c, sg, ep, func() { unlock(&c.lock) })
		return true, true
	}
	
    //缓冲不为空
	if c.qcount > 0 {
		// Receive directly from queue
		qp := chanbuf(c, c.recvx)
		if raceenabled {
			raceacquire(qp)
			racerelease(qp)
		}
		if ep != nil {
			typedmemmove(c.elemtype, ep, qp)
		}
		typedmemclr(c.elemtype, qp)
		c.recvx++
		if c.recvx == c.dataqsiz {
			c.recvx = 0
		}
		c.qcount--
		unlock(&c.lock)
		return true, true
	}

    //以上条件没有一个满足，立即返回
	if !block {
		unlock(&c.lock)
		return false, false
	}

	// no sender available: block on this channel.
	gp := getg()
	mysg := acquireSudog()
	mysg.releasetime = 0
	if t0 != 0 {
		mysg.releasetime = -1
	}
	// No stack splits between assigning elem and enqueuing mysg
	// on gp.waiting where copystack can find it.
	mysg.elem = ep
	mysg.waitlink = nil
	gp.waiting = mysg
	mysg.g = gp
	mysg.selectdone = nil
	mysg.c = c 
    //gp.param 在这里用途????
	gp.param = nil
	c.recvq.enqueue(mysg)
	goparkunlock(&c.lock, "chan receive", traceEvGoBlockRecv, 3)

	// someone woke us up
	if mysg != gp.waiting {
		throw("G waiting list is corrupted")
	}
	gp.waiting = nil
	if mysg.releasetime > 0 {
		blockevent(mysg.releasetime-t0, 2)
	}
    //若gp.param 是nil,则表示协程因为channel关闭被唤醒,则closed为true
    //若gp.param不是nil,则表示接收到消息被唤醒
	closed := gp.param == nil
	gp.param = nil
	mysg.c = nil
	releaseSudog(mysg)
	return true, !closed
}


~~~



#### recv

1. 若channel不带缓冲，并且保存接收到的消息的地址不为空(ep !=nil)，则调用recvDirect
2. channel带缓冲，从缓冲拷贝消息。并将等待发送的消息拷贝到缓冲中
3. 唤醒一个在`等待发送消息协程队列`中的协程



疑问：

c.sendx 为什么更新为c.recvx

~~~go
// recv processes a receive operation on a full channel c.
// There are 2 parts:
// 1) The value sent by the sender sg is put into the channel
//    and the sender is woken up to go on its merry way.
// 2) The value received by the receiver (the current G) is
//    written to ep.
// For synchronous channels, both values are the same.
// For asynchronous channels, the receiver gets its data from
// the channel buffer and the sender's data is put in the
// channel buffer.
// Channel c must be full and locked. recv unlocks c with unlockf.
// sg must already be dequeued from c.
// A non-nil ep must point to the heap or the caller's stack.
func recv(c *hchan, sg *sudog, ep unsafe.Pointer, unlockf func()) {
	if c.dataqsiz == 0 {
		if raceenabled {
			racesync(c, sg)
		}
		if ep != nil {
			// copy data from sender
			recvDirect(c.elemtype, sg, ep)
		}
	} else {
		// Queue is full. Take the item at the
		// head of the queue. Make the sender enqueue
		// its item at the tail of the queue. Since the
		// queue is full, those are both the same slot.
		qp := chanbuf(c, c.recvx)
		if raceenabled {
			raceacquire(qp)
			racerelease(qp)
			raceacquireg(sg.g, qp)
			racereleaseg(sg.g, qp)
		}
		// copy data from queue to receiver
		if ep != nil {
			typedmemmove(c.elemtype, ep, qp)
		}
		// copy data from sender to queue
		typedmemmove(c.elemtype, qp, sg.elem)
		c.recvx++
		if c.recvx == c.dataqsiz {
			c.recvx = 0
		}
        //c.sendx 为什么更新为c.recvx
		c.sendx = c.recvx // c.sendx = (c.sendx+1) % c.dataqsiz
	}
	sg.elem = nil
	gp := sg.g
	unlockf()
	gp.param = unsafe.Pointer(sg)
	if sg.releasetime != 0 {
		sg.releasetime = cputicks()
	}
	goready(gp, 4)
}
~~~



### closechan 关闭channel

1. 若channel为nil，则panic
2. 若channel已经被关闭，则panic
3. 设置hchan.closed为1
4. 唤醒所有在`接收消息协程等待队列`的协程
5. 唤醒所有在`发送消息协程等待队列`的协程

~~~go
//关闭channel

func closechan(c *hchan) {
	if c == nil {
		panic(plainError("close of nil channel"))
	}

	lock(&c.lock)
	if c.closed != 0 {
		unlock(&c.lock)
		panic(plainError("close of closed channel"))
	}

	if raceenabled {
		callerpc := getcallerpc(unsafe.Pointer(&c))
		racewritepc(unsafe.Pointer(c), callerpc, funcPC(closechan))
		racerelease(unsafe.Pointer(c))
	}

	c.closed = 1

	var glist *g

	// release all readers
	for {
		sg := c.recvq.dequeue()
		if sg == nil {
			break
		}
		if sg.elem != nil {
			typedmemclr(c.elemtype, sg.elem)
			sg.elem = nil
		}
		if sg.releasetime != 0 {
			sg.releasetime = cputicks()
		}
		gp := sg.g
		gp.param = nil
		if raceenabled {
			raceacquireg(gp, unsafe.Pointer(c))
		}
		gp.schedlink.set(glist)
		glist = gp
	}

	// release all writers (they will panic)
	for {
		sg := c.sendq.dequeue()
		if sg == nil {
			break
		}
		sg.elem = nil
		if sg.releasetime != 0 {
			sg.releasetime = cputicks()
		}
		gp := sg.g
		gp.param = nil
		if raceenabled {
			raceacquireg(gp, unsafe.Pointer(c))
		}
		gp.schedlink.set(glist)
		glist = gp
	}
	unlock(&c.lock)

	// Ready all Gs now that we've dropped the channel lock.
	for glist != nil {
		gp := glist
		glist = glist.schedlink.ptr()
		gp.schedlink = 0
		goready(gp, 3)
	}
}

~~~





