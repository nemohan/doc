## POST 和 PUT的区别



[from]: (https://stackoverflow.com/questions/107390/whats-the-difference-between-a-post-and-a-put-http-request)

PUT puts a file or resource at a specific URI, and exactly at that URI. If there's already a file or resource at that URI, PUT replaces that file or resource. If there is no file or resource there, PUT creates one. PUT is [idempotent](http://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html#sec9.1.2), but paradoxically PUT responses are not cacheable.

[HTTP 1.1 RFC location for PUT](http://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html#sec9.6)

**HTTP POST:**

POST sends data to a specific URI and expects the resource at that URI to handle the request. The web server at this point can determine what to do with the data in the context of the specified resource. The POST method is not [idempotent](http://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html#sec9.1.2), however POST responses *are* cacheable so long as the server sets the appropriate Cache-Control and Expires headers.

The official HTTP RFC specifies POST to be:

- Annotation of existing resources;
- Posting a message to a bulletin board, newsgroup, mailing list, or similar group of articles;
- Providing a block of data, such as the result of submitting a form, to a data-handling process;
- Extending a database through an append operation.

[HTTP 1.1 RFC location for POST](http://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html#sec9.5)

**Difference between POST and PUT:**

The RFC itself explains the core difference:

> The fundamental difference between the POST and PUT requests is reflected in the different meaning of the Request-URI. The URI in a POST request identifies the resource that will handle the enclosed entity. That resource might be a data-accepting process, a gateway to some other protocol, or a separate entity that accepts annotations. In contrast, the URI in a PUT request identifies the entity enclosed with the request -- the user agent knows what URI is intended and the server MUST NOT attempt to apply the request to some other resource. If the server desires that the request be applied to a different URI, it MUST send a 301 (Moved Permanently) response; the user agent MAY then make its own decision regarding whether or not to redirect the request.







###  article 2

from <https://www.keycdn.com/support/put-vs-post>

There are various HTTP methods that exist and each one is used for different purposes. The most popular HTTP method is the GET method which is used to retrieve data from a web server. For example, if you want to load an image from a particular website, your browser will make a request to the web server using the following command:

```none
GET https://website.com/path/to/image.jpg
```

However, apart from GET, there are other types of [HTTP methods](https://www.tutorialspoint.com/http/http_methods.htm) including:

- HEAD
- POST
- PUT
- DELETE
- CONNECT
- OPTIONS
- TRACE

Two of these methods are sometimes confused in regards to when each should be used. The two methods in question here are **PUT and POST**. In this article, we’re going to talk specifically about what the difference is between PUT vs POST as well as how to properly use each method.

## What Does the PUT Method Do?[#](https://www.keycdn.com/support/put-vs-post#what-does-the-put-method-do)

The PUT method completely replaces whatever currently exists at the target URL with something else. With this method, you can create a new resource or overwrite an existing one given **you know the exact Request-URI**. An example of a PUT method being used to create a new resource would resemble the following:

```none
PUT /forums/<new_thread> HTTP/2.0
Host: https://yourwebsite.com/
```

Where `<new_thread>` would be the actual name or ID number of the thread. Alternatively, a PUT method used to overwrite an existing resource could look like this:

```none
PUT /forums/<existing_thread> HTTP/2.0
Host: https://yourwebsite.com/
```

In short, the PUT method is used to **create or overwrite a resource at a particular URL that is known by the client**.

## What Does the POST Method Do?[#](https://www.keycdn.com/support/put-vs-post#what-does-the-post-method-do)

The HTTP POST method is used to send user-generated data to the web server. For example, a POST method is used when a user comments on a forum or if they upload a profile picture. A POST method should also be used **if you do not know the specific URL** of where your newly created resource should reside. In other words, if a new forum thread is created and the thread path is not specified then you could use some like:

```none
POST /forums HTTP/2.0
Host: https://yourwebsite.com/
```

Using this method, the URL path would be returned from the origin server and you would receive a response similar to:

```none
HTTP/2.0 201 Created
Location: /forums/<new_thread>
```

In short, the **POST method should be used to create a subordinate** (or child) of the resource identified by the Request-URI. In the example above, the Request-URI would be `/forums` and the subordinate or child would be `<new_thread>` as defined by the origin.

## When to Use PUT vs POST[#](https://www.keycdn.com/support/put-vs-post#when-to-use-put-vs-post)

So, now that you know more about the difference between PUT vs POST, you should have a better idea of which one to use in certain circumstances. However, this section will aim to further clarify when to use each method.

First off, choosing between using PUT vs POST should be based on the action’s [idempotence](https://en.wikipedia.org/wiki/Idempotence). As Wikipedia puts it,

> Idempotence is the property of certain operations in mathematics and computer science, that can be applied multiple times **without changing the result** beyond the initial application

With this definition, we can say that the **PUT method is idempotent** because no matter how many times we send the same request, the results will always be the same. On the other hand, the POST method is not idempotent since if we send the same POST request multiple times, we will receive various results (i.e. a new subordinate will be created each time).

[RFC 2616](https://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html), explains the difference between PUT vs POST as follows.

> The fundamental difference between the POST and PUT requests is reflected in the **different meaning of the Request-URI**. The URI in a POST request identifies the resource that will handle the enclosed entity… In contrast, the URI in a PUT request identifies the entity enclosed with the request.

When you know the URL of the thing you want to create or overwrite, a PUT method should be used. Alternatively, if you only know the URL of the category or sub-section of the thing you want to create something within, use the POST method.

## Summary[#](https://www.keycdn.com/support/put-vs-post#summary)

POST and PUT are both popular HTTP methods that may be sometimes confused or used interchangeably. However, it’s important to correctly **identify the idempotence of the action** at hand in order to determine whether a PUT vs POST method should be used. Otherwise, the misuse of each method may result in the occurrence of unexpected bugs.

### SUPERCHARGE YOUR CONTENT DELIVERY 🚀

Try KeyCDN with a free 30 day trial, no credit card required.

Get started

#### PRODUCT