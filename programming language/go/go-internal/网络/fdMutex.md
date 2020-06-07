# fdMutex

fdMutex是为网络文件描述符提供的读写锁

##### fdMutex的定义

~~~go
// fdMutex is a specialized synchronization primitive that manages
// lifetime of an fd and serializes access to Read, Write and Close
// methods on netFD.
type fdMutex struct {
	state uint64
	rsema uint32
	wsema uint32
}
// fdMutex.state is organized as follows:
// 1 bit - whether netFD is closed, if set all subsequent lock operations will fail.
// 1 bit - lock for read operations.
// 1 bit - lock for write operations.
// 20 bits - total number of references (read+write+misc).
// 20 bits - number of outstanding read waiters.
// 20 bits - number of outstanding write waiters.
const (
    //前三位
	mutexClosed  = 1 << 0
	mutexRLock   = 1 << 1
	mutexWLock   = 1 << 2
	mutexRef     = 1 << 3
	mutexRefMask = (1<<20 - 1) << 3
    
	mutexRWait   = 1 << 23
	mutexRMask   = (1<<20 - 1) << 23
    
	mutexWWait   = 1 << 43
	mutexWMask   = (1<<20 - 1) << 43
)

~~~



#####  fdMutex.rwlock

net/fdMutex.go

* 当fdMutex.state的值为1时，表明锁已经被关闭

1 未上锁-->加读锁

* 在开始时，fdMutex.rsema、fdMutex.state都是0，调用者获取读锁，read参数为true
* mutexBit设置为mutexRLock(0x2),检查锁是否被关闭
* 若已经关闭则返回false,说明加锁失败
* old是fdMutex.state的值，检查是否已经被加上读锁。若之前处于锁定状态则跳到第三种情况
* 因为是第一种情况，所以检查条件不成立（之前不处于锁定状态)
* 设置fdMutex.state为读锁锁定状态, new= (old | mutexBit)  +mutexRef=(0 | 0x2) + 0x8



~~~go
// lock adds a reference to mu and locks mu.
// It reports whether mu is available for reading or writing.
func (mu *fdMutex) rwlock(read bool) bool {
	var mutexBit, mutexWait, mutexMask uint64
	var mutexSema *uint32
	if read {
		mutexBit = mutexRLock // 1 << 1
		mutexWait = mutexRWait // 1 << 23
		mutexMask = mutexRMask // (1<<20 - 1) << 23
		mutexSema = &mu.rsema
	} else {
		mutexBit = mutexWLock // 1 << 2
		mutexWait = mutexWWait // 1 << 43
        mutexMask = mutexWMask //(1 << 20-1) << 43
		mutexSema = &mu.wsema
	}
	for {
		old := atomic.LoadUint64(&mu.state)
		if old&mutexClosed != 0 {
			return false
		}
		var new uint64
		if old&mutexBit == 0 {
			// Lock is free, acquire it.
            //10 1000
			new = (old | mutexBit) + mutexRef
			if new&mutexRefMask == 0 {
				panic("net: inconsistent fdMutex")
			}
		} else {
			// Wait for lock.
            //读锁->读锁 new = 0xa + （1<<23)
			new = old + mutexWait
			if new&mutexMask == 0 {
				panic("net: inconsistent fdMutex")
			}
		}
		if atomic.CompareAndSwapUint64(&mu.state, old, new) {
			if old&mutexBit == 0 {
				return true
			}
			runtime_Semacquire(mutexSema)
			// The signaller has subtracted mutexWait.
		}
	}
}
~~~

