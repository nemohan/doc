epoll

[TOC]

## 总结

### 边缘触发(edge-trigger)和水平触发(level-trigger)

#### 边缘触发

#### 水平触发



#### 使用哪种触发模式



### 什么是wakeup event



### 阅读顺序

1. epoll(7)
2. epoll_create(2)





# epoll(7) — Linux manual page 

### 水平触发和边缘触发

设想以下场景：

1. 代表pipe读取端的文件描述符rfd，被添加到epoll实例
2. pipe的写入者向pipe写入2KB数据
3. 调用epoll_wait(2)返回满足条件的rfd
4. pipe的读取者从pipe读取1KB数据
5. 再次调用epoll_wait(2)

#### 水平触发(LT)

满足条件就一直处于触发状态

#### 边缘触发(ET)

在边缘触发模式下，上面的第5步调用epoll_wait(2)会一直阻塞。因为在这种模式下，仅在`文件描述符`上有事件发生时触发

收到多个数据片时，会产生多个事件

#### 实践



在边缘触发模式下：

- 以非阻塞模式使用`文件描述符`
- 读取`文件描述符`直到返回EAGAIN错误
- 多个线程调用epoll_wait等待同一个epoll文件描述符时，若某个使用ET模式的文件描述符满足条件时，只有一个线程会被唤醒



应该使用哪种模式呢？两种模式各有什么优缺点？golang使用的是ET模式

## NAME         [top](https://man7.org/linux/man-pages/man7/epoll.7.html#top_of_page)

```
       epoll - I/O event notification facility

```

## SYNOPSIS         [top](https://man7.org/linux/man-pages/man7/epoll.7.html#top_of_page)

```
       #include <sys/epoll.h>

```

## DESCRIPTION         [top](https://man7.org/linux/man-pages/man7/epoll.7.html#top_of_page)

```
       The epoll API performs a similar task to poll(2): monitoring multiple
       file descriptors to see if I/O is possible on any of them.  The epoll
       API can be used either as an edge-triggered or a level-triggered
       interface and scales well to large numbers of watched file
       descriptors.

       The central concept of the epoll API is the epoll instance, an in-
       kernel data structure which, from a user-space perspective, can be
       considered as a container for two lists:

       · The interest list (sometimes also called the epoll set): the set of
         file descriptors that the process has registered an interest in
         monitoring.

       · The ready list: the set of file descriptors that are "ready" for
         I/O.  The ready list is a subset of (or, more precisely, a set of
         references to) the file descriptors in the interest list.  The
         ready list is dynamically populated by the kernel as a result of
         I/O activity on those file descriptors.

       The following system calls are provided to create and manage an epoll
       instance:

       · epoll_create(2) creates a new epoll instance and returns a file
         descriptor referring to that instance.  (The more recent
         epoll_create1(2) extends the functionality of epoll_create(2).)

       · Interest in particular file descriptors is then registered via
         epoll_ctl(2), which adds items to the interest list of the epoll
         instance.

       · epoll_wait(2) waits for I/O events, blocking the calling thread if
         no events are currently available.  (This system call can be
         thought of as fetching items from the ready list of the epoll
         instance.)

   Level-triggered and edge-triggered
       The epoll event distribution interface is able to behave both as
       edge-triggered (ET) and as level-triggered (LT).  The difference
       between the two mechanisms can be described as follows.  Suppose that
       this scenario happens:

       1. The file descriptor that represents the read side of a pipe (rfd)
          is registered on the epoll instance.

       2. A pipe writer writes 2 kB of data on the write side of the pipe.

       3. A call to epoll_wait(2) is done that will return rfd as a ready
          file descriptor.

       4. The pipe reader reads 1 kB of data from rfd.

       5. A call to epoll_wait(2) is done.

       If the rfd file descriptor has been added to the epoll interface
       using the EPOLLET (edge-triggered) flag, the call to epoll_wait(2)
       done in step 5 will probably hang despite the available data still
       present in the file input buffer; meanwhile the remote peer might be
       expecting a response based on the data it already sent.  The reason
       for this is that edge-triggered mode delivers events only when
       changes occur on the monitored file descriptor.  So, in step 5 the
       caller might end up waiting for some data that is already present
       inside the input buffer.  In the above example, an event on rfd will
       be generated because of the write done in 2 and the event is consumed
       in 3.  Since the read operation done in 4 does not consume the whole
       buffer data, the call to epoll_wait(2) done in step 5 might block
       indefinitely.

		//使用边缘触发，应该注意的事项
       An application that employs the EPOLLET flag should use nonblocking
       file descriptors to avoid having a blocking read or write starve a
       task that is handling multiple file descriptors.  The suggested way
       to use epoll as an edge-triggered (EPOLLET) interface is as follows:

       a) with nonblocking file descriptors; and

       b) by waiting for an event only after read(2) or write(2) return
          EAGAIN.

       By contrast, when used as a level-triggered interface (the default,
       when EPOLLET is not specified), epoll is simply a faster poll(2), and
       can be used wherever the latter is used since it shares the same
       semantics.

		//即使在ET模式下，
       Since even with edge-triggered epoll, multiple events can be
       generated upon receipt of multiple chunks of data, the caller has the
       option to specify the EPOLLONESHOT flag, to tell epoll to disable the
       associated file descriptor after the receipt of an event with
       epoll_wait(2).  When the EPOLLONESHOT flag is specified, it is the
       caller's responsibility to rearm the file descriptor using
       epoll_ctl(2) with EPOLL_CTL_MOD.

       If multiple threads (or processes, if child processes have inherited
       the epoll file descriptor across fork(2)) are blocked in
       epoll_wait(2) waiting on the same epoll file descriptor and a file
       descriptor in the interest list that is marked for edge-triggered
       (EPOLLET) notification becomes ready, just one of the threads (or
       processes) is awoken from epoll_wait(2).  This provides a useful
       optimization for avoiding "thundering herd" wake-ups in some
       scenarios.

   Interaction with autosleep
       If the system is in autosleep mode via /sys/power/autosleep and an
       event happens which wakes the device from sleep, the device driver
       will keep the device awake only until that event is queued.  To keep
       the device awake until the event has been processed, it is necessary
       to use the epoll_ctl(2) EPOLLWAKEUP flag.

       When the EPOLLWAKEUP flag is set in the events field for a struct
       epoll_event, the system will be kept awake from the moment the event
       is queued, through the epoll_wait(2) call which returns the event
       until the subsequent epoll_wait(2) call.  If the event should keep
       the system awake beyond that time, then a separate wake_lock should
       be taken before the second epoll_wait(2) call.

   /proc interfaces
       The following interfaces can be used to limit the amount of kernel
       memory consumed by epoll:

       /proc/sys/fs/epoll/max_user_watches (since Linux 2.6.28)
              This specifies a limit on the total number of file descriptors
              that a user can register across all epoll instances on the
              system.  The limit is per real user ID.  Each registered file
              descriptor costs roughly 90 bytes on a 32-bit kernel, and
              roughly 160 bytes on a 64-bit kernel.  Currently, the default
              value for max_user_watches is 1/25 (4%) of the available low
              memory, divided by the registration cost in bytes.

   Example for suggested usage
       While the usage of epoll when employed as a level-triggered interface
       does have the same semantics as poll(2), the edge-triggered usage
       requires more clarification to avoid stalls in the application event
       loop.  In this example, listener is a nonblocking socket on which
       listen(2) has been called.  The function do_use_fd() uses the new
       ready file descriptor until EAGAIN is returned by either read(2) or
       write(2).  An event-driven state machine application should, after
       having received EAGAIN, record its current state so that at the next
       call to do_use_fd() it will continue to read(2) or write(2) from
       where it stopped before.

           #define MAX_EVENTS 10
           struct epoll_event ev, events[MAX_EVENTS];
           int listen_sock, conn_sock, nfds, epollfd;

           /* Code to set up listening socket, 'listen_sock',
              (socket(), bind(), listen()) omitted */

           epollfd = epoll_create1(0);
           if (epollfd == -1) {
               perror("epoll_create1");
               exit(EXIT_FAILURE);
           }

           ev.events = EPOLLIN;
           ev.data.fd = listen_sock;
           if (epoll_ctl(epollfd, EPOLL_CTL_ADD, listen_sock, &ev) == -1) {
               perror("epoll_ctl: listen_sock");
               exit(EXIT_FAILURE);
           }

           for (;;) {
               nfds = epoll_wait(epollfd, events, MAX_EVENTS, -1);
               if (nfds == -1) {
                   perror("epoll_wait");
                   exit(EXIT_FAILURE);
               }

               for (n = 0; n < nfds; ++n) {
                   if (events[n].data.fd == listen_sock) {
                       conn_sock = accept(listen_sock,
                                          (struct sockaddr *) &addr, &addrlen);
                       if (conn_sock == -1) {
                           perror("accept");
                           exit(EXIT_FAILURE);
                       }
                       setnonblocking(conn_sock);
                       ev.events = EPOLLIN | EPOLLET;
                       ev.data.fd = conn_sock;
                       if (epoll_ctl(epollfd, EPOLL_CTL_ADD, conn_sock,
                                   &ev) == -1) {
                           perror("epoll_ctl: conn_sock");
                           exit(EXIT_FAILURE);
                       }
                   } else {
                       do_use_fd(events[n].data.fd);
                   }
               }
           }

       When used as an edge-triggered interface, for performance reasons, it
       is possible to add the file descriptor inside the epoll interface
       (EPOLL_CTL_ADD) once by specifying (EPOLLIN|EPOLLOUT).  This allows
       you to avoid continuously switching between EPOLLIN and EPOLLOUT
       calling epoll_ctl(2) with EPOLL_CTL_MOD.

   Questions and answers
       0.  What is the key used to distinguish the file descriptors regis‐
           tered in an interest list?

           The key is the combination of the file descriptor number and the
           open file description (also known as an "open file handle", the
           kernel's internal representation of an open file).

       1.  What happens if you register the same file descriptor on an epoll
           instance twice?

           You will probably get EEXIST.  However, it is possible to add a
           duplicate (dup(2), dup2(2), fcntl(2) F_DUPFD) file descriptor to
           the same epoll instance.  This can be a useful technique for fil‐
           tering events, if the duplicate file descriptors are registered
           with different events masks.

       2.  Can two epoll instances wait for the same file descriptor?  If
           so, are events reported to both epoll file descriptors?

           Yes, and events would be reported to both.  However, careful pro‐
           gramming may be needed to do this correctly.

       3.  Is the epoll file descriptor itself poll/epoll/selectable?

           Yes.  If an epoll file descriptor has events waiting, then it
           will indicate as being readable.

       4.  What happens if one attempts to put an epoll file descriptor into
           its own file descriptor set?

           The epoll_ctl(2) call fails (EINVAL).  However, you can add an
           epoll file descriptor inside another epoll file descriptor set.

       5.  Can I send an epoll file descriptor over a UNIX domain socket to
           another process?

           Yes, but it does not make sense to do this, since the receiving
           process would not have copies of the file descriptors in the
           interest list.

       6.  Will closing a file descriptor cause it to be removed from all
           epoll interest lists?

           Yes, but be aware of the following point.  A file descriptor is a
           reference to an open file description (see open(2)).  Whenever a
           file descriptor is duplicated via dup(2), dup2(2), fcntl(2)
           F_DUPFD, or fork(2), a new file descriptor referring to the same
           open file description is created.  An open file description con‐
           tinues to exist until all file descriptors referring to it have
           been closed.

           A file descriptor is removed from an interest list only after all
           the file descriptors referring to the underlying open file
           description have been closed.  This means that even after a file
           descriptor that is part of an interest list has been closed,
           events may be reported for that file descriptor if other file
           descriptors referring to the same underlying file description
           remain open.  To prevent this happening, the file descriptor must
           be explicitly removed from the interest list (using epoll_ctl(2)
           EPOLL_CTL_DEL) before it is duplicated.  Alternatively, the
           application must ensure that all file descriptors are closed
           (which may be difficult if file descriptors were duplicated
           behind the scenes by library functions that used dup(2) or
           fork(2)).

		   如果在两次epoll_wait(2)之间有多个事件发生，这些事件是合并为一个还是每个单独上报
       7.  If more than one event occurs between epoll_wait(2) calls, are
           they combined or reported separately?

           They will be combined.

       8.  Does an operation on a file descriptor affect the already col‐
           lected but not yet reported events?

           You can do two operations on an existing file descriptor.  Remove
           would be meaningless for this case.  Modify will reread available
           I/O.

       9.  Do I need to continuously read/write a file descriptor until
           EAGAIN when using the EPOLLET flag (edge-triggered behavior)?

           Receiving an event from epoll_wait(2) should suggest to you that
           such file descriptor is ready for the requested I/O operation.
           You must consider it ready until the next (nonblocking)
           read/write yields EAGAIN.  When and how you will use the file
           descriptor is entirely up to you.

           For packet/token-oriented files (e.g., datagram socket, terminal
           in canonical mode), the only way to detect the end of the
           read/write I/O space is to continue to read/write until EAGAIN.

           For stream-oriented files (e.g., pipe, FIFO, stream socket), the
           condition that the read/write I/O space is exhausted can also be
           detected by checking the amount of data read from / written to
           the target file descriptor.  For example, if you call read(2) by
           asking to read a certain amount of data and read(2) returns a
           lower number of bytes, you can be sure of having exhausted the
           read I/O space for the file descriptor.  The same is true when
           writing using write(2).  (Avoid this latter technique if you can‐
           not guarantee that the monitored file descriptor always refers to
           a stream-oriented file.)

	//缺陷和避免的方法
   Possible pitfalls and ways to avoid them
       o Starvation (edge-triggered)

       If there is a large amount of I/O space, it is possible that by try‐
       ing to drain it the other files will not get processed causing star‐
       vation.  (This problem is not specific to epoll.)

       The solution is to maintain a ready list and mark the file descriptor
       as ready in its associated data structure, thereby allowing the
       application to remember which files need to be processed but still
       round robin amongst all the ready files.  This also supports ignoring
       subsequent events you receive for file descriptors that are already
       ready.

       o If using an event cache...

       If you use an event cache or store all the file descriptors returned
       from epoll_wait(2), then make sure to provide a way to mark its clo‐
       sure dynamically (i.e., caused by a previous event's processing).
       Suppose you receive 100 events from epoll_wait(2), and in event #47 a
       condition causes event #13 to be closed.  If you remove the structure
       and close(2) the file descriptor for event #13, then your event cache
       might still say there are events waiting for that file descriptor
       causing confusion.

       One solution for this is to call, during the processing of event 47,
       epoll_ctl(EPOLL_CTL_DEL) to delete file descriptor 13 and close(2),
       then mark its associated data structure as removed and link it to a
       cleanup list.  If you find another event for file descriptor 13 in
       your batch processing, you will discover the file descriptor had been
       previously removed and there will be no confusion.

```

## VERSIONS         [top](https://man7.org/linux/man-pages/man7/epoll.7.html#top_of_page)

```
       The epoll API was introduced in Linux kernel 2.5.44.  Support was
       added to glibc in version 2.3.2.

```

## CONFORMING TO         [top](https://man7.org/linux/man-pages/man7/epoll.7.html#top_of_page)

```
       The epoll API is Linux-specific.  Some other systems provide similar
       mechanisms, for example, FreeBSD has kqueue, and Solaris has
       /dev/poll.

```

## NOTES         [top](https://man7.org/linux/man-pages/man7/epoll.7.html#top_of_page)

```
       The set of file descriptors that is being monitored via an epoll file
       descriptor can be viewed via the entry for the epoll file descriptor
       in the process's /proc/[pid]/fdinfo directory.  See proc(5) for
       further details.

       The kcmp(2) KCMP_EPOLL_TFD operation can be used to test whether a
       file descriptor is present in an epoll instance.

```

## SEE ALSO         [top](https://man7.org/linux/man-pages/man7/epoll.7.html#top_of_page)

```
       epoll_create(2), epoll_create1(2), epoll_ctl(2), epoll_wait(2),
       poll(2), select(2)

```

## COLOPHON         [top](https://man7.org/linux/man-pages/man7/epoll.7.html#top_of_page)

```
       This page is part of release 5.08 of the Linux man-pages project.  A
       description of the project, information about reporting bugs, and the
       latest version of this page, can be found at
       https://www.kernel.org/doc/man-pages/.

Linux                            2019-03-06                         EPOLL(7)
```

------

Pages that refer to this page: [accept(2)](https://man7.org/linux/man-pages/man2/accept.2.html),  [accept4(2)](https://man7.org/linux/man-pages/man2/accept4.2.html),  [creat(2)](https://man7.org/linux/man-pages/man2/creat.2.html),  [epoll_create1(2)](https://man7.org/linux/man-pages/man2/epoll_create1.2.html), [epoll_create(2)](https://man7.org/linux/man-pages/man2/epoll_create.2.html),  [epoll_ctl(2)](https://man7.org/linux/man-pages/man2/epoll_ctl.2.html),  [epoll_pwait(2)](https://man7.org/linux/man-pages/man2/epoll_pwait.2.html),  [epoll_wait(2)](https://man7.org/linux/man-pages/man2/epoll_wait.2.html),  [eventfd2(2)](https://man7.org/linux/man-pages/man2/eventfd2.2.html), [eventfd(2)](https://man7.org/linux/man-pages/man2/eventfd.2.html),  [futex(2)](https://man7.org/linux/man-pages/man2/futex.2.html),  [kcmp(2)](https://man7.org/linux/man-pages/man2/kcmp.2.html),  [_newselect(2)](https://man7.org/linux/man-pages/man2/_newselect.2.html),  [open(2)](https://man7.org/linux/man-pages/man2/open.2.html),  [openat(2)](https://man7.org/linux/man-pages/man2/openat.2.html), [perf_event_open(2)](https://man7.org/linux/man-pages/man2/perf_event_open.2.html),  [perfmonctl(2)](https://man7.org/linux/man-pages/man2/perfmonctl.2.html),  [pidfd_open(2)](https://man7.org/linux/man-pages/man2/pidfd_open.2.html),  [poll(2)](https://man7.org/linux/man-pages/man2/poll.2.html),  [ppoll(2)](https://man7.org/linux/man-pages/man2/ppoll.2.html),  [pselect(2)](https://man7.org/linux/man-pages/man2/pselect.2.html), [pselect6(2)](https://man7.org/linux/man-pages/man2/pselect6.2.html),  [recv(2)](https://man7.org/linux/man-pages/man2/recv.2.html),  [recvfrom(2)](https://man7.org/linux/man-pages/man2/recvfrom.2.html),  [recvmsg(2)](https://man7.org/linux/man-pages/man2/recvmsg.2.html),  [select(2)](https://man7.org/linux/man-pages/man2/select.2.html),  [select_tut(2)](https://man7.org/linux/man-pages/man2/select_tut.2.html), [signalfd(2)](https://man7.org/linux/man-pages/man2/signalfd.2.html),  [signalfd4(2)](https://man7.org/linux/man-pages/man2/signalfd4.2.html),  [timerfd_create(2)](https://man7.org/linux/man-pages/man2/timerfd_create.2.html),  [timerfd_gettime(2)](https://man7.org/linux/man-pages/man2/timerfd_gettime.2.html), [timerfd_settime(2)](https://man7.org/linux/man-pages/man2/timerfd_settime.2.html),  [userfaultfd(2)](https://man7.org/linux/man-pages/man2/userfaultfd.2.html),  [eventfd_read(3)](https://man7.org/linux/man-pages/man3/eventfd_read.3.html),  [eventfd_write(3)](https://man7.org/linux/man-pages/man3/eventfd_write.3.html),  [fd_clr(3)](https://man7.org/linux/man-pages/man3/fd_clr.3.html), [FD_CLR(3)](https://man7.org/linux/man-pages/man3/FD_CLR.3.html),  [fd_isset(3)](https://man7.org/linux/man-pages/man3/fd_isset.3.html),  [FD_ISSET(3)](https://man7.org/linux/man-pages/man3/FD_ISSET.3.html),  [fd_set(3)](https://man7.org/linux/man-pages/man3/fd_set.3.html),  [FD_SET(3)](https://man7.org/linux/man-pages/man3/FD_SET.3.html),  [fd_zero(3)](https://man7.org/linux/man-pages/man3/fd_zero.3.html), [FD_ZERO(3)](https://man7.org/linux/man-pages/man3/FD_ZERO.3.html),  [sd-event(3)](https://man7.org/linux/man-pages/man3/sd-event.3.html),  [sd_event_add_io(3)](https://man7.org/linux/man-pages/man3/sd_event_add_io.3.html),  [sd_event_get_fd(3)](https://man7.org/linux/man-pages/man3/sd_event_get_fd.3.html), [sd_event_io_handler_t(3)](https://man7.org/linux/man-pages/man3/sd_event_io_handler_t.3.html),  [sd_event_source(3)](https://man7.org/linux/man-pages/man3/sd_event_source.3.html),  [sd_event_source_get_io_events(3)](https://man7.org/linux/man-pages/man3/sd_event_source_get_io_events.3.html), [sd_event_source_get_io_fd(3)](https://man7.org/linux/man-pages/man3/sd_event_source_get_io_fd.3.html),  [sd_event_source_get_io_fd_own(3)](https://man7.org/linux/man-pages/man3/sd_event_source_get_io_fd_own.3.html), [sd_event_source_get_io_revents(3)](https://man7.org/linux/man-pages/man3/sd_event_source_get_io_revents.3.html),  [sd_event_source_set_io_events(3)](https://man7.org/linux/man-pages/man3/sd_event_source_set_io_events.3.html), [sd_event_source_set_io_fd(3)](https://man7.org/linux/man-pages/man3/sd_event_source_set_io_fd.3.html),  [sd_event_source_set_io_fd_own(3)](https://man7.org/linux/man-pages/man3/sd_event_source_set_io_fd_own.3.html),  [proc(5)](https://man7.org/linux/man-pages/man5/proc.5.html),  [procfs(5)](https://man7.org/linux/man-pages/man5/procfs.5.html), [systemd.exec(5)](https://man7.org/linux/man-pages/man5/systemd.exec.5.html),  [capabilities(7)](https://man7.org/linux/man-pages/man7/capabilities.7.html),  [fanotify(7)](https://man7.org/linux/man-pages/man7/fanotify.7.html),  [inotify(7)](https://man7.org/linux/man-pages/man7/inotify.7.html),  [mq_overview(7)](https://man7.org/linux/man-pages/man7/mq_overview.7.html), [pipe(7)](https://man7.org/linux/man-pages/man7/pipe.7.html),  [socket(7)](https://man7.org/linux/man-pages/man7/socket.7.html),  [udp(7)](

# epoll_create(2) — Linux manual page



## NAME         

```
       epoll_create, epoll_create1 - open an epoll file descriptor
```

## SYNOPSIS       

```
       #include <sys/epoll.h>

       int epoll_create(int size);
       int epoll_create1(int flags);
```

## DESCRIPTION       

```
       epoll_create() creates a new epoll(7) instance.  Since Linux 2.6.8,
       the size argument is ignored, but must be greater than zero; see
       NOTES.

       epoll_create() returns a file descriptor referring to the new epoll
       instance.  This file descriptor is used for all the subsequent calls
       to the epoll interface.  When no longer required, the file descriptor
       returned by epoll_create() should be closed by using close(2).  When
       all file descriptors referring to an epoll instance have been closed,
       the kernel destroys the instance and releases the associated
       resources for reuse.

   epoll_create1()
       If flags is 0, then, other than the fact that the obsolete size
       argument is dropped, epoll_create1() is the same as epoll_create().
       The following value can be included in flags to obtain different
       behavior:

       EPOLL_CLOEXEC
              Set the close-on-exec (FD_CLOEXEC) flag on the new file
              descriptor.  See the description of the O_CLOEXEC flag in
              open(2) for reasons why this may be useful.
```

## RETURN VALUE         

```
       On success, these system calls return a file descriptor (a
       nonnegative integer).  On error, -1 is returned, and errno is set to
       indicate the error.
```

## ERRORS       

```
       EINVAL size is not positive.

       EINVAL (epoll_create1()) Invalid value specified in flags.

       EMFILE The per-user limit on the number of epoll instances imposed by
              /proc/sys/fs/epoll/max_user_instances was encountered.  See
              epoll(7) for further details.

       EMFILE The per-process limit on the number of open file descriptors
              has been reached.

       ENFILE The system-wide limit on the total number of open files has
              been reached.

       ENOMEM There was insufficient memory to create the kernel object.
```

## VERSIONS        

```
       epoll_create() was added to the kernel in version 2.6.  Library
       support is provided in glibc starting with version 2.3.2.

       epoll_create1() was added to the kernel in version 2.6.27.  Library
       support is provided in glibc starting with version 2.9.
```

## CONFORMING TO        

```
       epoll_create() is Linux-specific.
```

## NOTES         

```
       In the initial epoll_create() implementation, the size argument
       informed the kernel of the number of file descriptors that the caller
       expected to add to the epoll instance.  The kernel used this
       information as a hint for the amount of space to initially allocate
       in internal data structures describing events.  (If necessary, the
       kernel would allocate more space if the caller's usage exceeded the
       hint given in size.)  Nowadays, this hint is no longer required (the
       kernel dynamically sizes the required data structures without needing
       the hint), but size must still be greater than zero, in order to
       ensure backward compatibility when new epoll applications are run on
       older kernels.
```

## SEE ALSO         [top](https://www.man7.org/linux/man-pages/man2/epoll_create.2.html#top_of_page)

```
       close(2), epoll_ctl(2), epoll_wait(2), epoll(7)
```

## COLOPHON         [top](https://www.man7.org/linux/man-pages/man2/epoll_create.2.html#top_of_page)

```
       This page is part of release 5.08 of the Linux man-pages project.  A
       description of the project, information about reporting bugs, and the
       latest version of this page, can be found at
       https://www.kernel.org/doc/man-pages/.

Linux                            2020-04-11     
```



# epoll_create1(2) — Linux manual page

## NAME         [top](https://www.man7.org/linux/man-pages/man2/epoll_create1.2.html#top_of_page)

```
       epoll_create, epoll_create1 - open an epoll file descriptor
```

## SYNOPSIS         [top](https://www.man7.org/linux/man-pages/man2/epoll_create1.2.html#top_of_page)

```
       #include <sys/epoll.h>

       int epoll_create(int size);
       int epoll_create1(int flags);
```

## DESCRIPTION         [top](https://www.man7.org/linux/man-pages/man2/epoll_create1.2.html#top_of_page)

```
       epoll_create() creates a new epoll(7) instance.  Since Linux 2.6.8,
       the size argument is ignored, but must be greater than zero; see
       NOTES.

       epoll_create() returns a file descriptor referring to the new epoll
       instance.  This file descriptor is used for all the subsequent calls
       to the epoll interface.  When no longer required, the file descriptor
       returned by epoll_create() should be closed by using close(2).  When
       all file descriptors referring to an epoll instance have been closed,
       the kernel destroys the instance and releases the associated
       resources for reuse.

   epoll_create1()
       If flags is 0, then, other than the fact that the obsolete size
       argument is dropped, epoll_create1() is the same as epoll_create().
       The following value can be included in flags to obtain different
       behavior:

       EPOLL_CLOEXEC
              Set the close-on-exec (FD_CLOEXEC) flag on the new file
              descriptor.  See the description of the O_CLOEXEC flag in
              open(2) for reasons why this may be useful.
```

## RETURN VALUE         [top](https://www.man7.org/linux/man-pages/man2/epoll_create1.2.html#top_of_page)

```
       On success, these system calls return a file descriptor (a
       nonnegative integer).  On error, -1 is returned, and errno is set to
       indicate the error.
```

## ERRORS         [top](https://www.man7.org/linux/man-pages/man2/epoll_create1.2.html#top_of_page)

```
       EINVAL size is not positive.

       EINVAL (epoll_create1()) Invalid value specified in flags.

       EMFILE The per-user limit on the number of epoll instances imposed by
              /proc/sys/fs/epoll/max_user_instances was encountered.  See
              epoll(7) for further details.

       EMFILE The per-process limit on the number of open file descriptors
              has been reached.

       ENFILE The system-wide limit on the total number of open files has
              been reached.

       ENOMEM There was insufficient memory to create the kernel object.
```

## VERSIONS         [top](https://www.man7.org/linux/man-pages/man2/epoll_create1.2.html#top_of_page)

```
       epoll_create() was added to the kernel in version 2.6.  Library
       support is provided in glibc starting with version 2.3.2.

       epoll_create1() was added to the kernel in version 2.6.27.  Library
       support is provided in glibc starting with version 2.9.
```

## CONFORMING TO         [top](https://www.man7.org/linux/man-pages/man2/epoll_create1.2.html#top_of_page)

```
       epoll_create() is Linux-specific.
```

## NOTES         [top](https://www.man7.org/linux/man-pages/man2/epoll_create1.2.html#top_of_page)

```
       In the initial epoll_create() implementation, the size argument
       informed the kernel of the number of file descriptors that the caller
       expected to add to the epoll instance.  The kernel used this
       information as a hint for the amount of space to initially allocate
       in internal data structures describing events.  (If necessary, the
       kernel would allocate more space if the caller's usage exceeded the
       hint given in size.)  Nowadays, this hint is no longer required (the
       kernel dynamically sizes the required data structures without needing
       the hint), but size must still be greater than zero, in order to
       ensure backward compatibility when new epoll applications are run on
       older kernels.
```

## SEE ALSO         [top](https://www.man7.org/linux/man-pages/man2/epoll_create1.2.html#top_of_page)

```
       close(2), epoll_ctl(2), epoll_wait(2), epoll(7)
```

## COLOPHON         [top](https://www.man7.org/linux/man-pages/man2/epoll_create1.2.html#top_of_page)

```
       This page is part of release 5.08 of the Linux man-pages project.  A
       description of the project, information about reporting bugs, and the
       latest version of this page, can be found at
       https://www.kernel.org/doc/man-pages/.
```



# epoll_ctl(2) — Linux manual page

## NAME         [top](https://www.man7.org/linux/man-pages/man2/epoll_ctl.2.html#top_of_page)

```
       epoll_ctl - control interface for an epoll file descriptor
```

## SYNOPSIS        

```
       #include <sys/epoll.h>

       int epoll_ctl(int epfd, int op, int fd, struct epoll_event *event);
```

## DESCRIPTION

### 仅作为入参的事件

* EPOLLET
* EPOLLONESHOT



### 输出事件

 

```
       This system call is used to add, modify, or remove entries in the
       interest list of the epoll(7) instance referred to by the file
       descriptor epfd.  It requests that the operation op be performed for
       the target file descriptor, fd.

       Valid values for the op argument are:

       EPOLL_CTL_ADD
              Add an entry to the interest list of the epoll file
              descriptor, epfd.  The entry includes the file descriptor, fd,
              a reference to the corresponding open file description (see
              epoll(7) and open(2)), and the settings specified in event.

       EPOLL_CTL_MOD
              Change the settings associated with fd in the interest list to
              the new settings specified in event.

       EPOLL_CTL_DEL
              Remove (deregister) the target file descriptor fd from the
              interest list.  The event argument is ignored and can be NULL
              (but see BUGS below).

       The event argument describes the object linked to the file descriptor
       fd.  The struct epoll_event is defined as:

           typedef union epoll_data {
               void        *ptr;
               int          fd;
               uint32_t     u32;
               uint64_t     u64;
           } epoll_data_t;

           struct epoll_event {
               uint32_t     events;      /* Epoll events */
               epoll_data_t data;        /* User data variable */
           };

       The data member of the epoll_event structure specifies data that the
       kernel should save and then return (via epoll_wait(2)) when this file
       descriptor becomes ready.

       The events member of the epoll_event structure is a bit mask composed
       by ORing together zero or more of the following available event
       types:

       EPOLLIN
              The associated file is available for read(2) operations.

       EPOLLOUT
              The associated file is available for write(2) operations.

       EPOLLRDHUP (since Linux 2.6.17)
              Stream socket peer closed connection, or shut down writing
              half of connection.  (This flag is especially useful for writ‐
              ing simple code to detect peer shutdown when using edge-trig‐
              gered monitoring.)

       EPOLLPRI
              There is an exceptional condition on the file descriptor.  See
              the discussion of POLLPRI in poll(2).

       EPOLLERR
              Error condition happened on the associated file descriptor.
              This event is also reported for the write end of a pipe when
              the read end has been closed.

              epoll_wait(2) will always report for this event; it is not
              necessary to set it in events when calling epoll_ctl().

       EPOLLHUP
              Hang up happened on the associated file descriptor.

              epoll_wait(2) will always wait for this event; it is not nec‐
              essary to set it in events when calling epoll_ctl().

              Note that when reading from a channel such as a pipe or a
              stream socket, this event merely indicates that the peer
              closed its end of the channel.  Subsequent reads from the
              channel will return 0 (end of file) only after all outstanding
              data in the channel has been consumed.

		//设置边缘触发模式,默认是水平触发, 仅用于入参
       EPOLLET
              Requests edge-triggered notification for the associated file
              descriptor.  The default behavior for epoll is level-trig‐
              gered.  See epoll(7) for more detailed information about edge-
              triggered and level-triggered notification.

              This flag is an input flag for the event.events field when
              calling epoll_ctl(); it is never returned by epoll_wait(2).

		//ONE-SHOT
       EPOLLONESHOT (since Linux 2.6.2)
              Requests one-shot notification for the associated file
              descriptor.  This means that after an event notified for the
              file descriptor by epoll_wait(2), the file descriptor is dis‐
              abled in the interest list and no other events will be
              reported by the epoll interface.  The user must call
              epoll_ctl() with EPOLL_CTL_MOD to rearm the file descriptor
              with a new event mask.

              This flag is an input flag for the event.events field when
              calling epoll_ctl(); it is never returned by epoll_wait(2).

       EPOLLWAKEUP (since Linux 3.5)
              If EPOLLONESHOT and EPOLLET are clear and the process has the
              CAP_BLOCK_SUSPEND capability, ensure that the system does not
              enter "suspend" or "hibernate" while this event is pending or
              being processed.  The event is considered as being "processed"
              from the time when it is returned by a call to epoll_wait(2)
              until the next call to epoll_wait(2) on the same epoll(7) file
              descriptor, the closure of that file descriptor, the removal
              of the event file descriptor with EPOLL_CTL_DEL, or the clear‐
              ing of EPOLLWAKEUP for the event file descriptor with
              EPOLL_CTL_MOD.  See also BUGS.

              This flag is an input flag for the event.events field when
              calling epoll_ctl(); it is never returned by epoll_wait(2).

		//互斥模式, 当wakeup event
		//什么是wakeup event
       EPOLLEXCLUSIVE (since Linux 4.5)
              Sets an exclusive wakeup mode for the epoll file descriptor
              that is being attached to the target file descriptor, fd.
              When a wakeup event occurs and multiple epoll file descriptors
              are attached to the same target file using EPOLLEXCLUSIVE, one
              or more of the epoll file descriptors will receive an event
              with epoll_wait(2).  The default in this scenario (when
              EPOLLEXCLUSIVE is not set) is for all epoll file descriptors
              to receive an event.  EPOLLEXCLUSIVE is thus useful for avoid‐
              ing thundering herd problems in certain scenarios.

              If the same file descriptor is in multiple epoll instances,
              some with the EPOLLEXCLUSIVE flag, and others without, then
              events will be provided to all epoll instances that did not
              specify EPOLLEXCLUSIVE, and at least one of the epoll
              instances that did specify EPOLLEXCLUSIVE.

              The following values may be specified in conjunction with
              EPOLLEXCLUSIVE: EPOLLIN, EPOLLOUT, EPOLLWAKEUP, and EPOLLET.
              EPOLLHUP and EPOLLERR can also be specified, but this is not
              required: as usual, these events are always reported if they
              occur, regardless of whether they are specified in events.
              Attempts to specify other values in events yield the error
              EINVAL.

              EPOLLEXCLUSIVE may be used only in an EPOLL_CTL_ADD operation;
              attempts to employ it with EPOLL_CTL_MOD yield an error.  If
              EPOLLEXCLUSIVE has been set using epoll_ctl(), then a subse‐
              quent EPOLL_CTL_MOD on the same epfd, fd pair yields an error.
              A call to epoll_ctl() that specifies EPOLLEXCLUSIVE in events
              and specifies the target file descriptor fd as an epoll
              instance will likewise fail.  The error in all of these cases
              is EINVAL.

              The EPOLLEXCLUSIVE flag is an input flag for the event.events
              field when calling epoll_ctl(); it is never returned by
              epoll_wait(2).
```

## RETURN VALUE    返回值

* 成功返回0
* 失败返回-1

```
       When successful, epoll_ctl() returns zero.  When an error occurs,
       epoll_ctl() returns -1 and errno is set appropriately.
```

## ERRORS         [top](https://www.man7.org/linux/man-pages/man2/epoll_ctl.2.html#top_of_page)

```
       EBADF  epfd or fd is not a valid file descriptor.

       EEXIST op was EPOLL_CTL_ADD, and the supplied file descriptor fd is
              already registered with this epoll instance.

       EINVAL epfd is not an epoll file descriptor, or fd is the same as
              epfd, or the requested operation op is not supported by this
              interface.

       EINVAL An invalid event type was specified along with EPOLLEXCLUSIVE
              in events.

       EINVAL op was EPOLL_CTL_MOD and events included EPOLLEXCLUSIVE.

       EINVAL op was EPOLL_CTL_MOD and the EPOLLEXCLUSIVE flag has
              previously been applied to this epfd, fd pair.

       EINVAL EPOLLEXCLUSIVE was specified in event and fd refers to an
              epoll instance.

       ELOOP  fd refers to an epoll instance and this EPOLL_CTL_ADD
              operation would result in a circular loop of epoll instances
              monitoring one another.

       ENOENT op was EPOLL_CTL_MOD or EPOLL_CTL_DEL, and fd is not
              registered with this epoll instance.

       ENOMEM There was insufficient memory to handle the requested op
              control operation.

       ENOSPC The limit imposed by /proc/sys/fs/epoll/max_user_watches was
              encountered while trying to register (EPOLL_CTL_ADD) a new
              file descriptor on an epoll instance.  See epoll(7) for
              further details.

       EPERM  The target file fd does not support epoll.  This error can
              occur if fd refers to, for example, a regular file or a
              directory.
```

## VERSIONS         [top](https://www.man7.org/linux/man-pages/man2/epoll_ctl.2.html#top_of_page)

```
       epoll_ctl() was added to the kernel in version 2.6.
```

## CONFORMING TO         [top](https://www.man7.org/linux/man-pages/man2/epoll_ctl.2.html#top_of_page)

```
       epoll_ctl() is Linux-specific.  Library support is provided in glibc
       starting with version 2.3.2.
```

## NOTES         [top](https://www.man7.org/linux/man-pages/man2/epoll_ctl.2.html#top_of_page)

```
       The epoll interface supports all file descriptors that support
       poll(2).
```

## BUGS         [top](https://www.man7.org/linux/man-pages/man2/epoll_ctl.2.html#top_of_page)

```
       In kernel versions before 2.6.9, the EPOLL_CTL_DEL operation required
       a non-null pointer in event, even though this argument is ignored.
       Since Linux 2.6.9, event can be specified as NULL when using
       EPOLL_CTL_DEL.  Applications that need to be portable to kernels
       before 2.6.9 should specify a non-null pointer in event.

       If EPOLLWAKEUP is specified in flags, but the caller does not have
       the CAP_BLOCK_SUSPEND capability, then the EPOLLWAKEUP flag is
       silently ignored.  This unfortunate behavior is necessary because no
       validity checks were performed on the flags argument in the original
       implementation, and the addition of the EPOLLWAKEUP with a check that
       caused the call to fail if the caller did not have the
       CAP_BLOCK_SUSPEND capability caused a breakage in at least one
       existing user-space application that happened to randomly (and
       uselessly) specify this bit.  A robust application should therefore
       double check that it has the CAP_BLOCK_SUSPEND capability if
       attempting to use the EPOLLWAKEUP flag.
```

## SEE ALSO         [top](https://www.man7.org/linux/man-pages/man2/epoll_ctl.2.html#top_of_page)

```
       epoll_create(2), epoll_wait(2), poll(2), epoll(7)
```

## COLOPHON         [top](https://www.man7.org/linux/man-pages/man2/epoll_ctl.2.html#top_of_page)

```
       This page is part of release 5.08 of the Linux man-pages project.  A
       description of the project, information about reporting bugs, and the
       latest version of this page, can be found at
       https://www.kernel.org/doc/man-pages/.
```







# epoll_wait(2) — Linux manual page

* timeout 指定超时时间，若值为-1，则一直阻塞；若为0，立即返回
* 

## NAME         [top](https://www.man7.org/linux/man-pages/man2/epoll_wait.2.html#top_of_page)

```
       epoll_wait,  epoll_pwait  -  wait  for  an I/O event on an epoll file
       descriptor
```

## SYNOPSIS        

```
       #include <sys/epoll.h>

       int epoll_wait(int epfd, struct epoll_event *events,
                      int maxevents, int timeout);
       int epoll_pwait(int epfd, struct epoll_event *events,
                      int maxevents, int timeout,
                      const sigset_t *sigmask);
```

## DESCRIPTION         

```
       The epoll_wait() system call waits for events on the epoll(7)
       instance referred to by the file descriptor epfd.  The buffer pointed
       to by events is used to return information from the ready list about
       file descriptors in the interest list that have some events
       available.  Up to maxevents are returned by epoll_wait().  The
       maxevents argument must be greater than zero.

       The timeout argument specifies the number of milliseconds that
       epoll_wait() will block.  Time is measured against the
       CLOCK_MONOTONIC clock.

       A call to epoll_wait() will block until either:

       · a file descriptor delivers an event;

       · the call is interrupted by a signal handler; or

       · the timeout expires.

       Note that the timeout interval will be rounded up to the system clock
       granularity, and kernel scheduling delays mean that the blocking
       interval may overrun by a small amount.  Specifying a timeout of -1
       causes epoll_wait() to block indefinitely, while specifying a timeout
       equal to zero cause epoll_wait() to return immediately, even if no
       events are available.

       The struct epoll_event is defined as:

           typedef union epoll_data {
               void    *ptr;
               int      fd;
               uint32_t u32;
               uint64_t u64;
           } epoll_data_t;

           struct epoll_event {
               uint32_t     events;    /* Epoll events */
               epoll_data_t data;      /* User data variable */
           };

       The data field of each returned epoll_event structure contains the
       same data as was specified in the most recent call to epoll_ctl(2)
       (EPOLL_CTL_ADD, EPOLL_CTL_MOD) for the corresponding open file
       descriptor.

       The events field is a bit mask that indicates the events that have
       occurred for the corresponding open file description.  See
       epoll_ctl(2) for a list of the bits that may appear in this mask.

   epoll_pwait()
       The relationship between epoll_wait() and epoll_pwait() is analogous
       to the relationship between select(2) and pselect(2): like
       pselect(2), epoll_pwait() allows an application to safely wait until
       either a file descriptor becomes ready or until a signal is caught.

       The following epoll_pwait() call:

           ready = epoll_pwait(epfd, &events, maxevents, timeout, &sigmask);

       is equivalent to atomically executing the following calls:

           sigset_t origmask;

           pthread_sigmask(SIG_SETMASK, &sigmask, &origmask);
           ready = epoll_wait(epfd, &events, maxevents, timeout);
           pthread_sigmask(SIG_SETMASK, &origmask, NULL);

       The sigmask argument may be specified as NULL, in which case
       epoll_pwait() is equivalent to epoll_wait().
```

## RETURN VALUE         

* 成功，返回满足条件的`文件描述符`数目
* 超时，返回0
* 失败，返回-1

```
       When successful, epoll_wait() returns the number of file descriptors
       ready for the requested I/O, or zero if no file descriptor became
       ready during the requested timeout milliseconds.  When an error
       occurs, epoll_wait() returns -1 and errno is set appropriately.
```

## ERRORS        

```
       EBADF  epfd is not a valid file descriptor.

       EFAULT The memory area pointed to by events is not accessible with
              write permissions.

       EINTR  The call was interrupted by a signal handler before either (1)
              any of the requested events occurred or (2) the timeout
              expired; see signal(7).

       EINVAL epfd is not an epoll file descriptor, or maxevents is less
              than or equal to zero.
```

## VERSIONS         [top](https://www.man7.org/linux/man-pages/man2/epoll_wait.2.html#top_of_page)

```
       epoll_wait() was added to the kernel in version 2.6.  Library support
       is provided in glibc starting with version 2.3.2.

       epoll_pwait() was added to Linux in kernel 2.6.19.  Library support
       is provided in glibc starting with version 2.6.
```

## CONFORMING TO         [top](https://www.man7.org/linux/man-pages/man2/epoll_wait.2.html#top_of_page)

```
       epoll_wait() is Linux-specific.
```

## NOTES         [top](https://www.man7.org/linux/man-pages/man2/epoll_wait.2.html#top_of_page)

```
       While one thread is blocked in a call to epoll_wait(), it is possible
       for another thread to add a file descriptor to the waited-upon epoll
       instance.  If the new file descriptor becomes ready, it will cause
       the epoll_wait() call to unblock.

       If more than maxevents file descriptors are ready when epoll_wait()
       is called, then successive epoll_wait() calls will round robin
       through the set of ready file descriptors.  This behavior helps avoid
       starvation scenarios, where a process fails to notice that additional
       file descriptors are ready because it focuses on a set of file
       descriptors that are already known to be ready.

       Note that it is possible to call epoll_wait() on an epoll instance
       whose interest list is currently empty (or whose interest list
       becomes empty because file descriptors are closed or removed from the
       interest in another thread).  The call will block until some file
       descriptor is later added to the interest list (in another thread)
       and that file descriptor becomes ready.
```

## BUGS         [top](https://www.man7.org/linux/man-pages/man2/epoll_wait.2.html#top_of_page)

```
       In kernels before 2.6.37, a timeout value larger than approximately
       LONG_MAX / HZ milliseconds is treated as -1 (i.e., infinity).  Thus,
       for example, on a system where sizeof(long) is 4 and the kernel HZ
       value is 1000, this means that timeouts greater than 35.79 minutes
       are treated as infinity.

   C library/kernel differences
       The raw epoll_pwait() system call has a sixth argument, size_t
       sigsetsize, which specifies the size in bytes of the sigmask
       argument.  The glibc epoll_pwait() wrapper function specifies this
       argument as a fixed value (equal to sizeof(sigset_t)).
```

## SEE ALSO         [top](https://www.man7.org/linux/man-pages/man2/epoll_wait.2.html#top_of_page)

```
       epoll_create(2), epoll_ctl(2), epoll(7)
```

## COLOPHON         [top](https://www.man7.org/linux/man-pages/man2/epoll_wait.2.html#top_of_page)

```
       This page is part of release 5.08 of the Linux man-pages project.  A
       description of the project, information about reporting bugs, and the
       latest version of this page, can be found at
       https://www.kernel.org/doc/man-pages/.

Linux                            2020-04-11                    EPOLL_WAIT(2)
```





