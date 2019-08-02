# cache

what every programmer should know about memory 笔记

### cpu core and thread

In addition we have processors which have multiple cores
and each core can have multiple “threads”. The difference
between a core and a thread is that separate cores
have separate copies of (almost17) all the hardware resources.
The cores can run completely independently
unless they are using the same resources–e.g., the connections
to the outside–at the same time. Threads, on the
other hand, share almost all of the processor’s resources.
Intel’s implementation of threads has only separate registers
for the threads and even that is limited, some registers
are shared. The complete picture for a modern CPU
therefore looks like

~~~
			


|processor 1	|				|
| ......  		|				|
| |core| 		|				|
| |....|		|				|  main memroy
----------------				|
|processor 2	|				|
| ......  		|          
| |	   | 		|
| |....|		|
---------------

~~~



#### 如何确定地址是否在缓存中

