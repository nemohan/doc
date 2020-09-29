# epoll

[TOC]



# epoll_create(2) — Linux manual page



## NAME         [top](https://www.man7.org/linux/man-pages/man2/epoll_create.2.html#top_of_page)

```
       epoll_create, epoll_create1 - open an epoll file descriptor
```

## SYNOPSIS         [top](https://www.man7.org/linux/man-pages/man2/epoll_create.2.html#top_of_page)

```
       #include <sys/epoll.h>

       int epoll_create(int size);
       int epoll_create1(int flags);
```

## DESCRIPTION         [top](https://www.man7.org/linux/man-pages/man2/epoll_create.2.html#top_of_page)

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

## RETURN VALUE         [top](https://www.man7.org/linux/man-pages/man2/epoll_create.2.html#top_of_page)

```
       On success, these system calls return a file descriptor (a
       nonnegative integer).  On error, -1 is returned, and errno is set to
       indicate the error.
```

## ERRORS         [top](https://www.man7.org/linux/man-pages/man2/epoll_create.2.html#top_of_page)

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

## VERSIONS         [top](https://www.man7.org/linux/man-pages/man2/epoll_create.2.html#top_of_page)

```
       epoll_create() was added to the kernel in version 2.6.  Library
       support is provided in glibc starting with version 2.3.2.

       epoll_create1() was added to the kernel in version 2.6.27.  Library
       support is provided in glibc starting with version 2.9.
```

## CONFORMING TO         [top](https://www.man7.org/linux/man-pages/man2/epoll_create.2.html#top_of_page)

```
       epoll_create() is Linux-specific.
```

## NOTES         [top](https://www.man7.org/linux/man-pages/man2/epoll_create.2.html#top_of_page)

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

## SYNOPSIS         [top](https://www.man7.org/linux/man-pages/man2/epoll_ctl.2.html#top_of_page)

```
       #include <sys/epoll.h>

       int epoll_ctl(int epfd, int op, int fd, struct epoll_event *event);
```

## DESCRIPTION         [top](https://www.man7.org/linux/man-pages/man2/epoll_ctl.2.html#top_of_page)

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

       EPOLLET
              Requests edge-triggered notification for the associated file
              descriptor.  The default behavior for epoll is level-trig‐
              gered.  See epoll(7) for more detailed information about edge-
              triggered and level-triggered notification.

              This flag is an input flag for the event.events field when
              calling epoll_ctl(); it is never returned by epoll_wait(2).

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

## RETURN VALUE         [top](https://www.man7.org/linux/man-pages/man2/epoll_ctl.2.html#top_of_page)

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

## NAME         [top](https://www.man7.org/linux/man-pages/man2/epoll_wait.2.html#top_of_page)

```
       epoll_wait,  epoll_pwait  -  wait  for  an I/O event on an epoll file
       descriptor
```

## SYNOPSIS         [top](https://www.man7.org/linux/man-pages/man2/epoll_wait.2.html#top_of_page)

```
       #include <sys/epoll.h>

       int epoll_wait(int epfd, struct epoll_event *events,
                      int maxevents, int timeout);
       int epoll_pwait(int epfd, struct epoll_event *events,
                      int maxevents, int timeout,
                      const sigset_t *sigmask);
```

## DESCRIPTION         [top](https://www.man7.org/linux/man-pages/man2/epoll_wait.2.html#top_of_page)

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

## RETURN VALUE         [top](https://www.man7.org/linux/man-pages/man2/epoll_wait.2.html#top_of_page)

```
       When successful, epoll_wait() returns the number of file descriptors
       ready for the requested I/O, or zero if no file descriptor became
       ready during the requested timeout milliseconds.  When an error
       occurs, epoll_wait() returns -1 and errno is set appropriately.
```

## ERRORS         [top](https://www.man7.org/linux/man-pages/man2/epoll_wait.2.html#top_of_page)

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