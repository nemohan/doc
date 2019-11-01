# Approaches to Performance test

*by Matt Maccaux*
Originally published on BEA Dev2Dev September 2005

# Technical Article

### Abstract

There are many different ways to go about performance testing enterprise applications, some of them more difficult than others. The type of performance testing you will do depends on what type of results you want to achieve. For example, for repeatability, benchmark testing is the best methodology. However, to test the upper limits of the system from the perspective of concurrent user load, capacity planning tests should be used. This article discusses the differences and examines various ways to go about setting up and running these performance tests.

### Introduction

Performance testing a J2EE application can be a daunting and seemingly confusing task if you don't approach it with the proper plan in place. As with any software development process, you must gather requirements, understand the business needs, and lay out a formal schedule well in advance of the actual testing. The requirements for the performance testing should be driven by the needs of the business and should be explained with a set of use cases. These can be based on historical data (say, what the load pattern was on the server for a week) or on approximations based on anticipated usage. Once you have an understanding of what you need to test, you need to look at how you want to test your application.

Early on in the development cycle, benchmark tests should be used to determine if any performance regressions are in the application. Benchmark tests are great for gathering repeatable results in a relatively short period of time. The best way to benchmark is to change one and only one parameter between tests. For example, if you want to see if increasing the JVM memory has any impact on the performance of your application, increment the JVM memory in stages (for example, going from 1024 MB to 1224 MB, then to 1524 MB, and finally to 2024 MB) and stop at each stage to gather the results and environment data, record this information, and then move on to the next test. This way you'll have a clear trail to follow when you are analyzing the results of the tests. In the next section, I discuss what a benchmark test looks like and the best parameters for running these tests.

Later on in the development cycle, after the bugs have been worked out of the application and it has reached a stable point, you can run more complex types of tests to determine how the system will perform under different load patterns. These types of tests are called *capacity planning*, *soak tests*, and *peak-rest tests*, and are designed to test "real-world"-type scenarios by testing the reliability, robustness, and scalability of the application. The descriptions I use below should be taken in the abstract sense because every application's usage pattern will be different. For example, capacity-planning tests are generally used with slow ramp-ups (defined below), but if your application sees quick bursts of traffic during a period of the day, then certainly modify your test to reflect this. Keep in mind, though, that as you change variables in the test (such as the period of ramp-up that I talk about here or the "think-time" of the users) the outcome of the test will vary. It is always a good idea to run a series of baseline tests first to establish a known, controlled environment to compare your changes with later.

### Benchmarking

The key to benchmark testing is to have consistently reproducible results. Results that are reproducible allow you to do two things: reduce the number of times you have to rerun those tests; and gain confidence in the product you are testing and the numbers you produce. The performance-testing tool you use can have a great impact on your test results. Assuming two of the metrics you are benchmarking are the response time of the server and the throughput of the server, these are affected by how much load is put onto the server. The amount of load that is put onto the server can come from two different areas: the number of connections (or virtual users) that are hitting the server simultaneously; and the amount of think-time each virtual user has between requests to the server. Obviously, the more users hitting the server, the more load will be generated. Also, the shorter the think-time between requests from each user, the greater the load will be on the server. Combine those two attributes in various ways to come up with different levels of server load. Keep in mind that as you put more load on the server, the throughput will climb, to a point.

![img](https://www.oracleimg.com/technetwork/articles/entarch/rampup-pagespersecond-117573.jpg)

*Figure 1. The throughput of the system in pages per second as load increases over time*

*Note that the throughput increases at a constant rate and then at some point levels off.*

At some point, the execute queue starts growing because all the threads on the server will be in use. The incoming requests, instead of being processed immediately, will be put into a queue and processed when threads become available.

![img](https://www.oracleimg.com/technetwork/articles/entarch/rampup-executequeue-104134.jpg)

*Figure 2. The execute queue length of the system as load increases over time*

*Note that the queue length is zero for a period of time, but then starts to grow at a constant rate. This is because there is a steady increase in load on the system, and although initially the system had enough free threads to cope with the additional load, eventually it became overwhelmed and had to start queuing them up.*

When the system reaches the point of saturation, the throughput of the server plateaus, and you have reached the maximum for the system given those conditions. However, as server load continues to grow, the response time of the system also grows even as the throughput plateaus.

![img](https://www.oracleimg.com/technetwork/articles/entarch/rampup-transactionresponsetime-104145.jpg)

*Figure 3. The response times of two transactions on the system as load increases over time*

*Note that at the same time as the execute queue (above) starts to grow, the response time also starts to grow at an increased rate. This is because the requests cannot be served immediately.*

To have truly reproducible results, the system should be put under a high load with no variability. To accomplish this, the virtual users hitting the server should have 0 seconds of think-time between requests. This is because the server is immediately put under load and will start building an execute queue. If the number of requests (and virtual users) is kept consistent, the results of the benchmarking should be highly accurate and very reproducible.

One question you should raise is, "How do you measure the results?" An average should be taken of the response time and throughput for a given test. The only way to accurately get these numbers though is to load all the users at once, and then run them for a predetermined amount of time. This is called a "flat" run.

![img](https://www.oracleimg.com/technetwork/articles/entarch/flatrun-runningvusers-113714.jpg)

*Figure 4. This is what a flat run looks like. All the users are loaded simultaneously.*

The opposite is known as a "ramp-up" run.

![img](https://www.oracleimg.com/technetwork/articles/entarch/rampup-runningvusers-125316.jpg)

*Figure 5. This is what a ramp-up run looks like. The users are added at a constant rate (x number per second) throughout the duration of the test.*

The users in a ramp-up run are staggered (adding a few new users every x seconds). The ramp-up run does not allow for accurate and reproducible averages because the load on the system is constantly changing as the users are being added a few at a time. Therefore, the flat run is ideal for getting benchmark numbers.

This is not to discount the value in running ramp-up-style tests. In fact, ramp-up tests are valuable for finding the ballpark in which you think you later want to run flat runs. The beauty of a ramp-up test is that you can see how the measurements change as the load on the system changes. Then you can pick the range you later want to run with flat tests.

The problem with flat runs is that the system will experience "wave" effects.

![img](https://www.oracleimg.com/technetwork/articles/entarch/flatrun-pagespersecond-125364.jpg)

*Figure 6. The throughput of the system in pages per second as measured during a flat run*

*Note the appearance of waves over time. The throughput is not smooth but rather resembles a wave pattern.*

This is visible from all aspects of the system including the CPU utilization.

![img](https://www.oracleimg.com/technetwork/articles/entarch/flatrun-cpuutilization-125374.jpg)

*Figure 7. The CPU utilization of the system over time, as measured during a flat run*

*Note the appearance of waves over a period of time. The CPU utilization is not smooth but rather has very sharp peaks that resemble the throughput graph's waves.*

Additionally, the execute queue experiences this unstable load, and therefore you see the queue growing and shrinking as the load on the system increases and decreases over time.

![img](https://www.oracleimg.com/technetwork/articles/entarch/flatrun-executequeue-106218.jpg)

*Figure 8. The execute queue of the system over time as measured during a flat run*

*Note the appearance of waves over time. The execute queue exactly mimics the CPU utilization graph above.*

Finally, the response time of the transactions on the system will also resemble this wave pattern.

![img](https://www.oracleimg.com/technetwork/articles/entarch/flatrun-transactionresponsetime-125363.jpg)

*Figure 9. The response time of a transaction on the system over time as measured during a flat run*

*Note the appearance of waves over time. The transaction response time lines up with the above graphs, but the effect is diminished over time.*

This occurs when all the users are doing approximately the same thing at the same time during the test. This will produce very unreliable and inaccurate results, so something must be done to counteract this. There are two ways to gain accurate measurements from these types of results. If the test is allowed to run for a very long duration (sometimes several hours, depending on how long one user iteration takes) eventually a natural sort of randomness will set in and the throughput of the server will "flatten out." Alternatively, measurements can be taken only between two of the breaks in the waves. The drawback of this method is that the duration you are capturing data from is going to be short.

### Capacity Planning

For capacity-planning-type tests, your goal is to show how far a given application can scale under a specific set of circumstances. Reproducibility is not as important here as in benchmark testing because there will often be a randomness factor in the testing. This is introduced to try to simulate a more customer-like or real-world application with a real user load. Often the specific goal is to find out how many concurrent users the system can support below a certain server response time. As an example, the question you may ask is, "How many servers do I need to support 8,000 concurrent users with a response time of 5 seconds or less?" To answer this question, you'll need more information about the system.

To attempt to determine the capacity of the system, several factors must be taken into consideration. Often the total number of users on the system is thrown around (in the hundreds of thousands), but in reality, this number doesn't mean a whole lot. What you really need to know is how many of those users will be hitting the server concurrently. The next thing you need to know is what the think-time or time between requests for each user will be. This is critical because the lower the think-time, the fewer concurrent users the system will be able to support. For example, a system that has users with a 1-second think-time will probably be able to support only a few hundred concurrently. However, a system with a think-time of 30 seconds will be able to support tens of thousands (given that the hardware and application are the same). In the real world, it is often difficult to determine exactly what the think-time of the users is. It is also important to note that in the real world users won't be clicking at exactly that interval every time they send a request.

This is where randomization comes into play. If you know your average user has a think-time of 5 seconds give or take 20 percent, then when you design your load test, ensure that there is 5 seconds +/- 20 percent between every click. Additionally, the notion of "pacing" can be used to introduce more randomness into your load scenario. It works like this: After a virtual user has completed one full set of requests, that user pauses for either a set period of time or a small, randomized period of time (say, 2 seconds +/- 25 percent), and then continues on with the next full set of requests. Combining these two methods of randomization into the test run should provide more of a real-world-like scenario.

Now comes the part where you actually run your capacity planning test. The next question is, "How do I load the users to simulate the load?" The best way to do this is to try to emulate how users hit the server during peak hours. Does that user load happen gradually over a period of time? If so, a ramp-up-style load should be used, where x number of users are added ever y seconds. Or, do all the users hit the system in a very short period of time all at once? If that is the case, a flat run should be used, where all the users are simultaneously loaded onto the server. These different styles will produce different results that are not comparable. For instance, if a ramp-up run is done and you find out that the system can support 5,000 users with a response time of 4 seconds or less, and then you follow that test with a flat run with 5,000 users, you'll probably find that the average response time of the system with 5,000 users is higher than 4 seconds. This is an inherent inaccuracy in ramp-up runs that prevents them from pinpointing the exact number of concurrent users a system can support. For a portal application, for example, this inaccuracy is amplified as the size of the portal grows and as the size of the cluster is increased.

This is not to say that ramp-up tests should not be used. Ramp-up runs are great if the load on the system is slowly increased over a long period of time. This is because the system will be able to continually adjust over time. If a fast ramp-up is used, the system will lag and artificially report a lower response time than what would be seen if a similar number of users were being loaded during a flat run. So, what is the best way to determine capacity? Taking the best of both load types and running a series of tests will yield the best results. For example, using a ramp-up run to determine the range of users that the system can support should be used first. Then, once that range has been determined, doing a series of flat runs at various concurrent user loads within that range can be used to more accurately determine the capacity of the system.

### Soak Tests

A soak test is a straightforward type of performance test. Soak tests are long-duration tests with a static number of concurrent users that test the overall robustness of the system. These tests will show any performance degradations over time via memory leaks, increased garbage collection (GC), or other problems in the system. The longer the test, the more confidence in the system you will have. It is a good idea to run this test twice—once with a fairly moderate user load (but below capacity so that there is no execute queue) and once with a high user load (so that there is a positive execute queue).

These tests should be run for several days to really get a good idea of the long-term health of the application. Make sure that the application being tested is as close to real world as possible with a realistic user scenario (how the virtual users navigate through the application) testing all the features of the application. Ensure that all the necessary monitoring tools are running so problems will be accurately detected and tracked down later.

### Peak-Rest Tests

Peak-rest tests are a hybrid of the capacity-planning ramp-up-style tests and soak tests. The goal here is to determine how well the system recovers from a high load (such as one during peak hours of the system), goes back to near idle, and then goes back up to peak load and back down again.

The best way to implement this test is to do a series of quick ramp-up tests followed by a plateau (determined by the business requirements), and then a dropping off of the load. A pause in the system should then be used, followed by another quick ramp-up; then you repeat the process. A couple things can be determined from this: Does the system recover on the second "peak" and each subsequent peak to the same level (or greater) than the first peak? And does the system show any signs of memory or GC degradation over the course of the test? The longer this test is run (repeating the peak/idle cycle over and over), the better idea you'll have of what the long-term health of the system looks like.

### Conclusion

This article has described several approaches to performance testing. Depending on the business requirements, development cycle, and lifecycle of the application, some tests will be better suited than others for a given organization. In all cases though, you should ask some fundamental questions before going down one path or another. The answers to these questions will then determine how to best test the application.

These questions are:

- How repeatable do the results need to be?
- How many times do you want to run and rerun these tests?
- What stage of the development cycle are you in?
- What are your business requirements?
- What are your user requirements?
- How long do you expect the live production system to stay up between maintenance downtimes?
- What is the expected user load during an average business day?

By answering these questions and then seeing how the answers fit into the above performance test types, you should be able to come up with a solid plan for testing the overall performance of your application.

Matt Maccaux is a Portal Performance Engineer for BEA Systems. He is responsible for performance testing WebLogic Portal and writing performance documentation.

##### Resources for

- [Developers](https://developer.oracle.com/)
- [Startups](https://www.oracle.com/startup/)
- [Students and Educators](https://academy.oracle.com/en/oa-web-overview.html)



