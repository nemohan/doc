# limiter

limiter 是一个基于channel实现的并发限制模块

~~~go
// Fixed is a simple channel-based concurrency limiter.  It uses a fixed
// size channel to limit callers from proceeding until there is a value available
// in the channel.  If all are in-use, the caller blocks until one is freed.
type Fixed chan struct{}

func NewFixed(limit int) Fixed {
	return make(Fixed, limit)
}

// Idle returns true if the limiter has all its capacity is available.
func (t Fixed) Idle() bool {
	return len(t) == cap(t)
}

// Available returns the number of available tokens that may be taken.
func (t Fixed) Available() int {
	return cap(t) - len(t)
}

// Capacity returns the number of tokens can be taken.
func (t Fixed) Capacity() int {
	return cap(t)
}

// TryTake attempts to take a token and return true if successful, otherwise returns false.
func (t Fixed) TryTake() bool {
	select {
	case t <- struct{}{}:
		return true
	default:
		return false
	}
}

// Take attempts to take a token and blocks until one is available.
func (t Fixed) Take() {
	t <- struct{}{}
}

// Release releases a token back to the limiter.
func (t Fixed) Release() {
	<-t
}
~~~



## Writer

~~~
type Writer struct {
	w       io.WriteCloser
	limiter Rate
	ctx     context.Context
}

type Rate interface {
	WaitN(ctx context.Context, n int) error
	Burst() int
}

func NewRate(bytesPerSec, burstLimit int) Rate {
	limiter := rate.NewLimiter(rate.Limit(bytesPerSec), burstLimit)
	limiter.AllowN(time.Now(), burstLimit) // spend initial burst
	return limiter
}

// NewWriter returns a writer that implements io.Writer with rate limiting.
// The limiter use a token bucket approach and limits the rate to bytesPerSec
// with a maximum burst of burstLimit.
func NewWriter(w io.WriteCloser, bytesPerSec, burstLimit int) *Writer {
	limiter := NewRate(bytesPerSec, burstLimit)

	return &Writer{
		w:       w,
		ctx:     context.Background(),
		limiter: limiter,
	}
}

// WithRate returns a Writer with the specified rate limiter.
func NewWriterWithRate(w io.WriteCloser, limiter Rate) *Writer {
	return &Writer{
		w:       w,
		ctx:     context.Background(),
		limiter: limiter,
	}
}

// Write writes bytes from b.
func (s *Writer) Write(b []byte) (int, error) {
	if s.limiter == nil {
		return s.w.Write(b)
	}

	var n int
	for n < len(b) {
		wantToWriteN := len(b[n:])
		if wantToWriteN > s.limiter.Burst() {
			wantToWriteN = s.limiter.Burst()
		}

		wroteN, err := s.w.Write(b[n : n+wantToWriteN])
		if err != nil {
			return n, err
		}
		n += wroteN

		if err := s.limiter.WaitN(s.ctx, wroteN); err != nil {
			return n, err
		}
	}

	return n, nil
}
~~~

