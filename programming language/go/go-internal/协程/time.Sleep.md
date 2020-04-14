# time.Sleep



[TOC]

### 总结

time.Sleep 可能会使得当前的线程m被挂起，而挂载m的p会由其他m负责执行

### time.Sleep

time.Sleep函数实际由runtime.timeSleep函数实现(定义在runtime/time.go ).

* 将当前

实际上是维护了一个小根堆，等待时间时间最小的为根

~~~go
type timer struct {
	i int // heap index

	// Timer wakes up at when, and then at when+period, ... (period > 0 only)
	// each time calling f(arg, now) in the timer goroutine, so f must be
	// a well-behaved function and not block.
	when   int64
	period int64
	f      func(interface{}, uintptr)
	arg    interface{}
	seq    uintptr
}

var timers struct {
	lock         mutex
	gp           *g
	created      bool
	sleeping     bool
	rescheduling bool
	waitnote     note
	t            []*timer
}

// nacl fake time support - time in nanoseconds since 1970
var faketime int64

// Package time APIs.
// Godoc uses the comments in package time, not these.

// time.now is implemented in assembly.

// timeSleep puts the current goroutine to sleep for at least ns nanoseconds.
//go:linkname timeSleep time.Sleep
func timeSleep(ns int64) {
	if ns <= 0 {
		return
	}

	t := new(timer)
	t.when = nanotime() + ns
	t.f = goroutineReady
	t.arg = getg()
	lock(&timers.lock)
	addtimerLocked(t)
	goparkunlock(&timers.lock, "sleep", traceEvGoSleep, 2)
}
~~~



### addtimerLocked

~~~go
// Add a timer to the heap and start or kick timerproc if the new timer is
// earlier than any of the others.
// Timers are locked.
func addtimerLocked(t *timer) {
	// when must never be negative; otherwise timerproc will overflow
	// during its delta calculation and never expire other runtime timers.
	if t.when < 0 {
		t.when = 1<<63 - 1
	}
	t.i = len(timers.t)
	timers.t = append(timers.t, t)
	siftupTimer(t.i)
	if t.i == 0 {
		// siftup moved to top: new earliest deadline.
		if timers.sleeping {
			timers.sleeping = false
			notewakeup(&timers.waitnote)
		}
		if timers.rescheduling {
			timers.rescheduling = false
			goready(timers.gp, 0)
		}
	}
	if !timers.created {
		timers.created = true
		go timerproc()
	}
}
~~~



### siftupTimer



~~~go
/ Heap maintenance algorithms.

func siftupTimer(i int) {
	t := timers.t
	when := t[i].when
	tmp := t[i]
	for i > 0 {
		p := (i - 1) / 4 // parent
		if when >= t[p].when {
			break
		}
		t[i] = t[p]
		t[i].i = i
		t[p] = tmp
		t[p].i = p
		i = p
	}
}
~~~



### timerproc

timerproc 是负责处理因调用time.Sleep而进入等待状态的协程。

* 若当前没有协程在等待定时器，则立即进行重新调度即当前协程让出cpu
* 若当前有协程在等待定时器触发，且定时器未到期则调用notetsleepg进入睡眠，notesleep则将p和m分离使得p可以被其他m运行。当前的线程m则调用系统调用futex进入阻塞
* 当前有协程在等待定时器触发，且定时器到期。将根节点从小根堆移除并调整小根堆。调用goroutineReady函数将等待协程放入到调度队列。再次检查队列看是否有已经触发的定时器或条件1、2满足

~~~go
// Timerproc runs the time-driven events.
// It sleeps until the next event in the timers heap.
// If addtimer inserts a new earlier event, it wakes timerproc early.
func timerproc() {
	timers.gp = getg()
	for {
		lock(&timers.lock)
		timers.sleeping = false
		now := nanotime()
		delta := int64(-1)
		for {
			if len(timers.t) == 0 {
				delta = -1
				break
			}
			t := timers.t[0]
			delta = t.when - now
			if delta > 0 {
				break
			}
			if t.period > 0 {
				// leave in heap but adjust next time to fire
				t.when += t.period * (1 + -delta/t.period)
				siftdownTimer(0)
			} else {
				// remove from heap
				last := len(timers.t) - 1
				if last > 0 {
					timers.t[0] = timers.t[last]
					timers.t[0].i = 0
				}
				timers.t[last] = nil
				timers.t = timers.t[:last]
				if last > 0 {
					siftdownTimer(0)
				}
				t.i = -1 // mark as removed
			}
			f := t.f
			arg := t.arg
			seq := t.seq
			unlock(&timers.lock)
			if raceenabled {
				raceacquire(unsafe.Pointer(t))
			}
			f(arg, seq)
			lock(&timers.lock)
		}
		if delta < 0 || faketime > 0 {
			// No timers left - put goroutine to sleep.
			timers.rescheduling = true
			goparkunlock(&timers.lock, "timer goroutine (idle)", traceEvGoBlock, 1)
			continue
		}
		// At least one timer pending. Sleep until then.
		timers.sleeping = true
		noteclear(&timers.waitnote)
		unlock(&timers.lock)
		notetsleepg(&timers.waitnote, delta)
	}
}
~~~





### goroutineReady(runtime/time.go)

goroutineReady 调用goready(runtime/proc.go)将处于等待状态的goroutine的状态修改为可运行状态并放置到p维护的可运行队列中（goready的分析可以看协程-恢复)

~~~go
// Ready the goroutine arg.
func goroutineReady(arg interface{}, seq uintptr) {
	goready(arg.(*g), 0)
}
~~~



### notetsleepg

~~~
// same as runtime·notetsleep, but called on user g (not g0)
// calls only nosplit functions between entersyscallblock/exitsyscall
func notetsleepg(n *note, ns int64) bool {
	gp := getg()
	if gp == gp.m.g0 {
		throw("notetsleepg on g0")
	}

	entersyscallblock(0)
	ok := notetsleep_internal(n, ns)
	exitsyscall(0)
	return ok
}
~~~



### 线程m被阻塞