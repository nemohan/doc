# JAVA中的GC

### JAVA 8

#### Concurrent mark sweep (CMS) garbage collection

CMS garbage collection is essentially an upgraded mark and sweep method. It scans heap memory **using multiple threads**. It was modified to take advantage of faster systems and had performance enhancements.

It attempts to minimize the pauses due to garbage collection by doing most of the garbage collection work *concurrently* with the application threads. It uses the parallel stop-the-world **mark-copy** algorithm in the Young Generation and the mostly concurrent **mark-sweep** algorithm in the Old Generation.

To use CMS GC, use below JVM argument:

```
`-XX:+UseConcMarkSweepGC`
```

###### CMS GC Optimization Options

| FLAG                                   | DESCRIPTION                                                  |
| -------------------------------------- | ------------------------------------------------------------ |
| -XX:+UseCMSInitiating\OccupancyOnly    | Indicates that you want to solely use occupancy as a criterion for starting a CMS collection operation. |
| -XX:CMSInitiating\OccupancyFraction=70 | Sets the percentage CMS generation occupancy to start a CMS collection cycle. |
| -XX:CMSTriggerRatio=70                 | This is the percentage of `MinHeapFreeRatio` in CMS generation that is allocated prior to a CMS cycle starts. |
| -XX:CMSTriggerPermRatio=90             | Sets the percentage of `MinHeapFreeRatio` in the CMS permanent generation that is allocated before starting a CMS collection cycle. |
| -XX:CMSWaitDuration=2000               | Use the parameter to specify how long the CMS is allowed to wait for young collection. |
| -XX:+UseParNewGC                       | Elects to use the parallel algorithm for young space collection. |
| -XX:+CMSConcurrentMTEnabled            | Enables the use of multiple threads for concurrent phases.   |
| -XX:ConcGCThreads=2                    | Sets the number of parallel threads used for the concurrent phases. |
| -XX:ParallelGCThreads=2                | Sets the number of parallel threads you want used for *stop-the-world* phases. |
| -XX:+CMSIncrementalMode                | Enable the incremental CMS (iCMS) mode.                      |
| -XX:+CMSClassUnloadingEnabled          | If this is not enabled, CMS will not clean permanent space.  |
| -XX:+ExplicitGCInvokes\Concurrent      | This allows `System.gc()` to trigger concurrent collection instead of a full garbage collection cycle. |

#### Serial garbage collection (串行垃圾回收)

This algorithm uses *mark-copy* for the Young Generation and *mark-sweep-compact* for the Old Generation. It works on a single thread. When executing, it freezes all other threads until garbage collection operations have concluded.

Due to the thread-freezing nature of serial garbage collection, it is only feasible for very small programs.

To use Serial GC, use below JVM argument:

```
`-XX:+UseSerialGC`
```

#### Parallel garbage collection

Simimar to serial GC, It uses `mark-copy` in the Young Generation and `mark-sweep-compact` in the Old Generation. Multiple concurrent threads are used for marking and copying / compacting phases. You can configure the number of threads using `-XX:ParallelGCThreads=N` option.

Parallel Garbage Collector is suitable on multi-core machines in cases where your primary goal is to increase throughput by efficient usage of existing system resources. Using this approach, GC cycle times can be considerably reduced.

Till Java 8, we have seen Parallel GC as default garbage collector. Java 9 onwards, G1 is the default garbage collector on 32- and 64-bit server configurations. – [JEP [248\]](https://openjdk.java.net/jeps/248)

To use parallel GC, use below JVM argument:



```
`-XX:+UseParallelGC`
```



### JAVA 9

#### G1 garbage collection

The G1 (Garbage First) garbage collector was available in Java 7 and is designed to be the long term replacement for the CMS collector. The G1 collector is a parallel, concurrent, and incrementally compacting low-pause garbage collector.

This approach involves segmenting the memory heap into multiple small regions (typically 2048). Each region is marked as either young generation (further devided into eden regions or survivor regions) or old generation. This allows the GC to avoid collecting the entire heap at once, and instead approach the problem incrementally. It means that only a subset of the regions is considered at a time.

![Memory regions marked - G1](https://howtodoinjava.com/wp-content/uploads/2018/04/Memory-regions-marked-G1.png)Memory regions marked – G1

G1 keep tracking of the amount of live data that each region contains. This information is used in determining the regions that contain the most garbage; so they are collected first. That’s why it is name **garbage-first** collection.

Just like other algorithms, unfortunately, the compacting operation takes place using the *Stop the World* approach. But as per it’s design goal, you can set specific performance goals to it. You can configure the pauses duration e.g. no more than 10 milliseconds in any given second. Garbage-First GC will do its best to meet this goal with high probability (but not with certainty, that would be hard real-time due to OS level thread management).

If you want to use in Java 7 or Java 8 machines, use JVM argument as below:

```
`-XX:+UseG1GC`
```

###### G1 Optimization Options

| FLAG                          | DESCRIPTION                                                  |
| ----------------------------- | ------------------------------------------------------------ |
| -XX:G1HeapRegionSize=16m      | Size of the heap region. The value will be a power of two and can range from 1MB to 32MB. The goal is to have around 2048 regions based on the minimum Java heap size. |
| -XX:MaxGCPauseMillis=200      | Sets a target value for desired maximum pause time. The default value is 200 milliseconds. The specified value does not adapt to your heap size. |
| -XX:G1ReservePercent=5        | This determines the minimum reserve in the heap.             |
| -XX:G1ConfidencePercent=75    | This is the confidence coefficient pause prediction heuristics. |
| -XX:GCPauseIntervalMillis=200 | This is the pause interval time slice per MMU in milliseconds. |

## GC Customization Options

#### GC configuration flags

| FLAG                    | DESCRIPTION                                                  |
| ----------------------- | ------------------------------------------------------------ |
| -Xms2048m -Xmx3g        | Sets the initial and maximum heap size (young space plus tenured space). |
| -XX:+DisableExplicitGC  | This will cause the JVM to ignore any System.gc() method invocations by an application. |
| -XX:+UseGCOverheadLimit | This is the use policy used to limit the time spent in garbage collection before an OutOfMemory error is thrown. |
| -XX:GCTimeLimit=95      | This limits the proportion of time spent in garbage collection before an `OutOfMemory` error is thrown. This is used with `GCHeapFreeLimit`. |
| -XX:GCHeapFreeLimit=5   | This sets the minimum percentage of free space after a full garbage collection before an `OutOfMemory` error is thrown. This is used with `GCTimeLimit`. |
| -XX:InitialHeapSize=3g  | Sets the initial heap size (young space plus tenured space). |
| -XX:MaxHeapSize=3g      | Sets the maximum heap size (young space plus tenured space). |
| -XX:NewSize=128m        | Sets the initial size of young space.                        |
| -XX:MaxNewSize=128m     | Sets the maximum size of young space.                        |
| -XX:SurvivorRatio=15    | Sets the size of single survivor space as a portion of Eden space size. |
| -XX:PermSize=512m       | Sets the initial size of the permanent space.                |
| -XX:MaxPermSize=512m    | Sets the maximum size of the permanent space.                |
| -Xss512k                | Sets the size of the stack area dedicated to each thread in bytes. |

#### GC logging flags

| FLAG                             | DESCRIPTION                                                  |
| -------------------------------- | ------------------------------------------------------------ |
| -verbose:gc or -XX:+PrintGC      | This prints the basic garbage collection information.        |
| -XX:+PrintGCDetails              | This will print more detailed garbage collection information. |
| -XX:+PrintGCTimeStamps           | You can print timestamps for each garbage collection event. The seconds are sequential and begin from the JVM start time. |
| -XX:+PrintGCDateStamps           | You can print date stamps for each garbage collection event. |
| -Xloggc:                         | Using this you can redirect garbage collection output to a file instead of the console. |
| -XX:+Print\TenuringDistribution  | You can print detailed information regarding young space following each collection cycle. |
| -XX:+PrintTLAB                   | You can use this flag to print TLAB allocation statistics.   |
| -XX:+PrintReferenceGC            | Using this flag, you can print the times for reference processing (that is, weak, soft, and so on) during stop-the-world pauses. |
| -XX:+HeapDump\OnOutOfMemoryError | This creates a heap dump file in an out-of-memory condition. |

## 来自 https://howtodoinjava.com/java/garbage-collection/all-garbage-collection-algorithms/ 