

## Refactoring a Monolith into Microservices

#### Overview of Refactoring to Microservices

The process of transforming a monolithic application into microservices is a form of [application modernization](https://en.wikipedia.org/wiki/Software_modernization). That is something that developers have been doing for decades. As a result, there are some ideas that we can reuse when refactoring an application into microservices.

One strategy to not use is the “Big Bang” rewrite. That is when you focus all of your development efforts on building a new microservices‑based application from scratch. Although it sounds appealing, it is extremely risky and will likely end in failure. As Martin Fowler [reportedly said](http://www.randyshoup.com/evolutionary-architecture), “the only thing a Big Bang rewrite guarantees is a Big Bang!”

Instead of a Big Bang rewrite, you should incrementally refactor your monolithic application. You gradually build a new application consisting of microservices, and run it in conjunction with your monolithic application. Over time, the amount of functionality implemented by the monolithic application shrinks until either it disappears entirely or it becomes just another microservice. This strategy is akin to servicing your car while driving down the highway at 70 mph – challenging, but far less risky than attempting a Big Bang rewrite.

Martin Fowler refers to this application modernization strategy as the [Strangler Application](http://www.martinfowler.com/bliki/StranglerApplication.html). The name comes from the strangler vine (a.k.a. strangler fig) that is found in rainforests. A strangler vine grows around a tree in order to reach the sunlight above the forest canopy. Sometimes, the tree dies, leaving a tree-shaped vine. Application modernization follows the same pattern. We will build a new application consisting of microservices around the legacy application, which will eventually die.

![The strangler fig is a metaphor for building a microservices architecture that mimic the functions of a monolith and eventually replace it [Richardson microservices reference architecture]](https://www.nginx.com/wp-content/uploads/2016/03/Richardson-microservices-part7-fig.png)

Let’s look at different strategies for doing this.

## Strategy 1 – Stop Digging

The [Law of Holes](https://en.wikipedia.org/wiki/Law_of_holes) says that whenever you are in a hole you should stop digging. This is great advice to follow when your monolithic application has become unmanageable. In other words, you should stop making the monolith bigger. This means that when you are implementing new functionality you should not add more code to the monolith. Instead, the big idea with this strategy is to put that new code in a standalone microservice. The following diagram shows the system architecture after applying this approach.

![To start migrating from a monolith to a microservices architecture, implement new functionality as microservices; continue routing requests for legacy functionality to the monolith until there is a replacement microservice](https://www.nginx.com/wp-content/uploads/2016/03/Richardson-microservices-part7-pull-module-from-monolith.png)

As well as the new service and the legacy monolith, there are two other components. The first is a request router, which handles incoming (HTTP) requests. It is similar to the API gateway described in an [earlier article](https://www.nginx.com/blog/building-microservices-using-an-api-gateway). The router sends requests corresponding to new functionality to the new service. It routes legacy requests to the monolith.

The other component is the glue code, which integrates the service with the monolith. A service rarely exists in isolation and often needs to access data owned by the monolith. The glue code, which resides in either the monolith, the service, or both, is responsible for the data integration. The service uses the glue code to read and write data owned by the monolith.

There are three strategies that a service can use to access the monolith’s data:

- Invoke a remote API provided by the monolith
- Access the monolith’s database directly
- Maintain its own copy of the data, which is synchronized with the monolith’s database

The glue code is sometimes called an *anti‑corruption layer*. That is because the glue code prevents the service, which has its own pristine domain model, from being polluted by concepts from the legacy monolith’s domain model. The glue code translates between the two different models. The term anti‑corruption layer first appeared in the must‑read book [Domain Driven Design](https://domainlanguage.com/ddd/) by Eric Evans and was then refined in a [white paper](http://domainlanguage.com/ddd-resources/surrounded-by-legacy-software/). Developing an anti‑corruption layer can be a non‑trivial undertaking. But it is essential to create one if you want to grow your way out of monolithic hell.

Implementing new functionality as a lightweight service has a couple of benefits. It prevents the monolith from becoming even more unmanageable. The service can be developed, deployed, and scaled independently of the monolith. You experience the benefits of the microservices architecture for each new service that you create.

However, this approach does nothing to address the problems with the monolith. To fix those problems you need to break up the monolith. Let’s look at strategies for doing that.

## Strategy 2 – Split Frontend and Backend

A strategy that shrinks the monolithic application is to split the presentation layer from the business logic and data access layers. A typical enterprise application consists of at least three different types of components:

- Presentation layer – Components that handle HTTP requests and implement either a (REST) API or an HTML‑based web UI. In an application that has a sophisticated user interface, the presentation tier is often a substantial body of code.
- Business logic layer – Components that are the core of the application and implement the business rules.
- Data‑access layer – Components that access infrastructure components such as databases and message brokers.

There is usually a clean separation between the presentation logic on one side and the business and data‑access logic on the other. The business tier has a coarse‑grained API consisting of one or more facades, which encapsulate business‑logic components. This API is a natural seam along which you can split the monolith into two smaller applications. One application contains the presentation layer. The other application contains the business and data‑access logic. After the split, the presentation logic application makes remote calls to the business logic application. Thee following diagram shows the architecture before and after the refactoring.

[![Refactor a monolith into two apps: one for presentation logic and another for business and data-access logic [Richardson microservices reference architecture\]](https://www.nginx.com/wp-content/uploads/2016/04/Richardson-microservices-part7-refactoring.png)](https://www.nginx.com/wp-content/uploads/2016/04/Richardson-microservices-part7-refactoring.png)

Splitting a monolith in this way has two main benefits. It enables you to develop, deploy, and scale the two applications independently of one another. In particular, it allows the presentation‑layer developers to iterate rapidly on the user interface and easily perform A/B testing, for example. Another benefit of this approach is that it exposes a remote API that can be called by the microservices that you develop.

This strategy, however, is only a partial solution. It is very likely that one or both of the applications will be an unmanageable monolith. You need to use the third strategy to eliminate the remaining monolith or monoliths.

## Strategy 3 – Extract Services

The third refactoring strategy is to turn existing modules within the monolith into standalone microservices. Each time you extract a module and turn it into a service, the monolith shrinks. Once you have converted enough modules, the monolith will cease to be a problem. Either it disappears entirely or it becomes small enough that it is just another service.

### Prioritizing Which Modules to Convert into Services

A large, complex monolithic application consists of tens or hundreds of modules, all of which are candidates for extraction. Figuring out which modules to convert first is often challenging. A good approach is to start with a few modules that are easy to extract. This will give you experience with microservices in general and the extraction process in particular. After that you should extract those modules that will give you the greatest benefit.

Converting a module into a service is typically time consuming. You want to rank modules by the benefit you will receive. It is usually beneficial to extract modules that change frequently. Once you have converted a module into a service, you can develop and deploy it independently of the monolith, which will accelerate development.

It is also beneficial to extract modules that have resource requirements significantly different from those of the rest of the monolith. It is useful, for example, to turn a module that has an in‑memory database into a service, which can then be deployed on hosts with large amounts of memory. Similarly, it can be worthwhile to extract modules that implement computationally expensive algorithms, since the service can then be deployed on hosts with lots of CPUs. By turning modules with particular resource requirements into services, you can make your application much easier to scale.

When figuring out which modules to extract, it is useful to look for existing coarse‑grained boundaries (a.k.a seams). They make it easier and cheaper to turn modules into services. An example of such a boundary is a module that only communicates with the rest of the application via asynchronous messages. It can be relatively cheap and easy to turn that module into a microservice.

### How to Extract a Module

The first step of extracting a module is to define a coarse‑grained interface between the module and the monolith. It is mostly likely a bidirectional API, since the monolith will need data owned by the service and vice versa. It is often challenging to implement such an API because of the tangled dependencies and fine‑grained interaction patterns between the module and the rest of the application. Business logic implemented using the [Domain Model pattern](http://martinfowler.com/eaaCatalog/domainModel.html) is especially challenging to refactor because of numerous associations between domain model classes. You will often need to make significant code changes to break these dependencies. The following diagram shows the refactoring.

Once you implement the coarse‑grained interface, you then turn the module into a free‑standing service. To do that, you must write code to enable the monolith and the service to communicate through an API that uses an [inter‑process communication](https://www.nginx.com/blog/building-microservices-inter-process-communication/inter-process-communication) (IPC) mechanism. The following diagram shows the architecture before, during, and after the refactoring.

[![Extract a module/microservice from a monolith by defining a coarse-grained interface between the module and the monolith [Richardson microservices reference architecture\]](https://www.nginx.com/wp-content/uploads/2016/04/Richardson-microservices-part7-extract-module.png)](https://www.nginx.com/wp-content/uploads/2016/04/Richardson-microservices-part7-extract-module.png)

In this example, Module Z is the candidate module to extract. Its components are used by Module X and it uses Module Y. The first refactoring step is to define a pair of coarse-grained APIs. The first interface is an inbound interface that is used by Module X to invoke Module Z. The second is an outbound interface used by Module Z to invoke Module Y.

The second refactoring step turns the module into a standalone service. The inbound and outbound interfaces are implemented by code that uses an IPC mechanism. You will most likely need to build the service by combining Module Z with a [Microservice Chassis framework](http://microservices.io/patterns/microservice-chassis.html) that handles cross‑cutting concerns such as service discovery.

Once you have extracted a module, you have yet another service that can be developed, deployed, and scaled independently of the monolith and any other services. You can even rewrite the service from scratch; in this case, the API code that integrates the service with the monolith becomes an anti‑corruption layer that translates between the two domain models. Each time you extract a service, you take another step in the direction of microservices. Over time, the monolith will shrink and you will have an increasing number of microservices.

## Summary

The process of migrating an existing application into microservices is a form of application modernization. You should not move to microservices by rewriting your application from scratch. Instead, you should incrementally refactor your application into a set of microservices. There are three strategies you can use: implement new functionality as microservices; split the presentation components from the business and data access components; and convert existing modules in the monolith into services. Over time the number of microservices will grow, and the agility and velocity of your development team will increase.