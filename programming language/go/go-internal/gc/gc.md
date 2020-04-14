# gc



[TOC]

go的gc是通过启动协程来执行的，该协程在包runtime 初始化阶段被启动(init函数)。执行函数forcegchelper

### forcegchelper

forcegchelper(runtime/proc.go) 是执行gc的协程

~~~go
func forcegchelper() {
	forcegc.g = getg()
	for {
		lock(&forcegc.lock)
		if forcegc.idle != 0 {
			throw("forcegc: phase error")
		}
		atomic.Store(&forcegc.idle, 1)
		goparkunlock(&forcegc.lock, "force gc (idle)", traceEvGoBlock, 1)
		// this goroutine is explicitly resumed by sysmon
		if debug.gctrace > 0 {
			println("GC forced")
		}
		gcStart(gcBackgroundMode, true)
	}
}
~~~

