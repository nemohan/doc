# containerd

[TOC]

containerd命令的入口及初始化相关的代码都在containerd/containerd/cmd/containerd包中。

### 配置containerd

命令行参数级别高于配置文件级别。

* 从配置文件加载配置

* 设置日志级别，默认debug级别
* 设置日志格式json或text，默认text
* 设置日志hook
* 

### 默认配置

containerd的默认配置在containerd/containerd/defaults包中。默认配置在不同的操作系统上有不同的值，下面的是unix操作系统的配置(defaults_unix.go)

~~~go
const (
	// DefaultRootDir is the default location used by containerd to store
	// persistent data
	DefaultRootDir = "/var/lib/containerd"
	// DefaultStateDir is the default location used by containerd to store
	// transient data
	DefaultStateDir = "/run/containerd"
	// DefaultAddress is the default unix socket address
	DefaultAddress = "/run/containerd/containerd.sock"
	// DefaultDebugAddress is the default unix socket address for pprof data
	DefaultDebugAddress = "/run/containerd/debug.sock"
	// DefaultFIFODir is the default location used by client-side cio library
	// to store FIFOs.
	DefaultFIFODir = "/run/containerd/fifo"
	// DefaultRuntime is the default linux runtime
	DefaultRuntime = "io.containerd.runc.v2"
	// DefaultConfigDir is the default location for config files.
	DefaultConfigDir = "/etc/containerd"
)
~~~

