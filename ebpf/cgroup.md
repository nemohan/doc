# cgroup

[TOC]



## 手动启用cgroup v2

还可以通过修改内核 cmdline 引导参数在你的 Linux 发行版上手动启用 cgroup v2。 如果你的发行版使用 GRUB，则应在 `/etc/default/grub` 下的 `GRUB_CMDLINE_LINUX` 中添加 `systemd.unified_cgroup_hierarchy=1`， 然后执行 `sudo update-grub`。不过，推荐的方法仍是使用一个默认已启用 cgroup v2 的发行版

## 识别 Linux 节点上的 cgroup 版本

cgroup 版本取决于正在使用的 Linux 发行版和操作系统上配置的默认 cgroup 版本。 要检查你的发行版使用的是哪个 cgroup 版本，请在该节点上运行 `stat -fc %T /sys/fs/cgroup/` 命令：

```shell
stat -fc %T /sys/fs/cgroup/
```

对于 cgroup v2，输出为 `cgroup2fs`。

对于 cgroup v1，输出为 `tmpfs`

## 使用cgroup限制资源使用

使用cgroup v1版本限制cpu资源使用时，若线程先于启用cgroup，则开启cgroup 后，不能限制该线程的资源使用，必须手动将线程加入cgroup。cgroup生效后，创建的线程也最好手动加入cgroup。