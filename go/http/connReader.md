# connReader

connReader定义在http/server.go.  connReader是net.Conn的封装

#### 为什么要加锁

假设这样一种情况:

读取的POST/PUT请求的消息体并不完整，此时调用了Handler. 假如我在Handler里面有使用另外的goroutine来读取request.Body。那么如果没有锁将会导致并发问题。

~~~go
// connReader is the io.Reader wrapper used by *conn. It combines a
// selectively-activated io.LimitedReader (to bound request header
// read sizes) with support for selectively keeping an io.Reader.Read
// call blocked in a background goroutine to wait for activity and
// trigger a CloseNotifier channel.
type connReader struct {
	conn *conn

	mu      sync.Mutex // guards following
	hasByte bool
	byteBuf [1]byte
	bgErr   error // non-nil means error happened on background read
	cond    *sync.Cond
	inRead  bool
	aborted bool  // set true before conn.rwc deadline is set to past
	remain  int64 // bytes remaining
}

func (cr *connReader) lock() {
	cr.mu.Lock()
	if cr.cond == nil {
		cr.cond = sync.NewCond(&cr.mu)
	}
}

func (cr *connReader) unlock() { cr.mu.Unlock() }

func (cr *connReader) startBackgroundRead() {
	cr.lock()
	defer cr.unlock()
	if cr.inRead {
		panic("invalid concurrent Body.Read call")
	}
	if cr.hasByte {
		return
	}
	cr.inRead = true
	cr.conn.rwc.SetReadDeadline(time.Time{})
	go cr.backgroundRead()
}

func (cr *connReader) backgroundRead() {
	n, err := cr.conn.rwc.Read(cr.byteBuf[:])
	cr.lock()
	if n == 1 {
		cr.hasByte = true
		// We were at EOF already (since we wouldn't be in a
		// background read otherwise), so this is a pipelined
		// HTTP request.
		cr.closeNotifyFromPipelinedRequest()
	}
	if ne, ok := err.(net.Error); ok && cr.aborted && ne.Timeout() {
		// Ignore this error. It's the expected error from
		// another goroutine calling abortPendingRead.
	} else if err != nil {
		cr.handleReadError(err)
	}
	cr.aborted = false
	cr.inRead = false
	cr.unlock()
	cr.cond.Broadcast()
}

func (cr *connReader) abortPendingRead() {
	cr.lock()
	defer cr.unlock()
	if !cr.inRead {
		return
	}
	cr.aborted = true
	cr.conn.rwc.SetReadDeadline(aLongTimeAgo)
	for cr.inRead {
		cr.cond.Wait()
	}
	cr.conn.rwc.SetReadDeadline(time.Time{})
}

func (cr *connReader) setReadLimit(remain int64) { cr.remain = remain }
func (cr *connReader) setInfiniteReadLimit()     { cr.remain = maxInt64 }
func (cr *connReader) hitReadLimit() bool        { return cr.remain <= 0 }

// may be called from multiple goroutines.
func (cr *connReader) handleReadError(err error) {
	cr.conn.cancelCtx()
	cr.closeNotify()
}

// closeNotifyFromPipelinedRequest simply calls closeNotify.
//
// This method wrapper is here for documentation. The callers are the
// cases where we send on the closenotify channel because of a
// pipelined HTTP request, per the previous Go behavior and
// documentation (that this "MAY" happen).
//
// TODO: consider changing this behavior and making context
// cancelation and closenotify work the same.
func (cr *connReader) closeNotifyFromPipelinedRequest() {
	cr.closeNotify()
}

// may be called from multiple goroutines.
func (cr *connReader) closeNotify() {
	res, _ := cr.conn.curReq.Load().(*response)
	if res != nil {
		if atomic.CompareAndSwapInt32(&res.didCloseNotify, 0, 1) {
			res.closeNotifyCh <- true
		}
	}
}

//2 种情况，读取的字节数等于buffer p的大小
//读取的字节数少于buffer p的大小

func (cr *connReader) Read(p []byte) (n int, err error) {
	cr.lock()
	if cr.inRead {
		cr.unlock()
		panic("invalid concurrent Body.Read call")
	}
    //TODO:
	if cr.hitReadLimit() {
		cr.unlock()
		return 0, io.EOF
	}
	if cr.bgErr != nil {
		err = cr.bgErr
		cr.unlock()
		return 0, err
	}
	if len(p) == 0 {
		cr.unlock()
		return 0, nil
	}
    
    //cr.remain初始设置为1M + 4K
	if int64(len(p)) > cr.remain {
		p = p[:cr.remain]
	}
    //++++++++++++++++++++++++++++++++++
    //hasByte
	if cr.hasByte {
		p[0] = cr.byteBuf[0]
		cr.hasByte = false
		cr.unlock()
		return 1, nil
	}
	cr.inRead = true
	cr.unlock()
	n, err = cr.conn.rwc.Read(p)

	cr.lock()
	cr.inRead = false
	if err != nil {
		cr.handleReadError(err)
	}
	cr.remain -= int64(n)
	cr.unlock()

	cr.cond.Broadcast()
	return n, err
}
~~~



### startBackgroundRead 的意图

~~~go
func (cr *connReader) unlock() { cr.mu.Unlock() }

func (cr *connReader) startBackgroundRead() {
	cr.lock()
	defer cr.unlock()
	if cr.inRead {
		panic("invalid concurrent Body.Read call")
	}
	if cr.hasByte {
		return
	}
	cr.inRead = true
	cr.conn.rwc.SetReadDeadline(time.Time{})
	go cr.backgroundRead()
}

//cr.byteBuf 是1字节大小的数组
func (cr *connReader) backgroundRead() {
	n, err := cr.conn.rwc.Read(cr.byteBuf[:])
	cr.lock()
    //有数据可读
	if n == 1 {
		cr.hasByte = true
		// We were at EOF already (since we wouldn't be in a
		// background read otherwise), so this is a pipelined
		// HTTP request.
		cr.closeNotifyFromPipelinedRequest()
	}
	if ne, ok := err.(net.Error); ok && cr.aborted && ne.Timeout() {
		// Ignore this error. It's the expected error from
		// another goroutine calling abortPendingRead.
	} else if err != nil {
		cr.handleReadError(err)
	}
	cr.aborted = false
	cr.inRead = false
	cr.unlock()
	cr.cond.Broadcast()
}

//cr.cond.Wait会等待多久
//如果后台协程一直读取不到数据，应该会一直卡在Wait
func (cr *connReader) abortPendingRead() {
	cr.lock()
	defer cr.unlock()
	if !cr.inRead {
		return
	}
	cr.aborted = true
	cr.conn.rwc.SetReadDeadline(aLongTimeAgo)
	for cr.inRead {
		cr.cond.Wait()
	}
	cr.conn.rwc.SetReadDeadline(time.Time{})
}

func (cr *connReader) setReadLimit(remain int64) { cr.remain = remain }
func (cr *connReader) setInfiniteReadLimit()     { cr.remain = maxInt64 }
func (cr *connReader) hitReadLimit() bool        { return cr.remain <= 0 }

// may be called from multiple goroutines.
func (cr *connReader) handleReadError(err error) {
	cr.conn.cancelCtx()
	cr.closeNotify()
}
~~~



### abortPendingRead

~~~go
func (cr *connReader) abortPendingRead() {
	cr.lock()
	defer cr.unlock()
	if !cr.inRead {
		return
	}
	cr.aborted = true
	cr.conn.rwc.SetReadDeadline(aLongTimeAgo)
	for cr.inRead {
		cr.cond.Wait()
	}
	cr.conn.rwc.SetReadDeadline(time.Time{})
}
~~~

