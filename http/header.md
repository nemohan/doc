# 一些容易混肴的header

### Transfer-Encoding

目前只定义了一个值: chunked

传输的消息传输所采用的编码方式，是消息的属性而不是body的属性

#### 值chunked

chunked编码将消息分成大小已知的消息块。每个消息块一个接一个的传输。采用chunked可以不用提前知道将要传输的内容的大小(content-lenght)。适用于动态生成的内容，比如视频采集.

有点类似于ip分片的意思。

~~~http
HTTP/1.1 200 OK<CR><LF>
Content-type: text/plain<CR><LF>
Transfer-encoding: chunked<CR><LF>
Trailer: Content-MD5<CR><LF>
<CR><LF>
27<CR><LF>
We hold these truths to be self-evident<CR><LF>
26<CR><LF>
, that all men are created equal, that<CR><LF>
84<CR><LF>
they are endowed by their Creator with certain
unalienable Rights, that among these are Life,
Liberty and the pursuit of Happiness.<CR><LF>
0<CR><LF>
Content-MD5:gjqei54p26tjisgj3p4utjgrj53<CR><LF>   //trailer header
~~~





### TE

在request header中使用，告诉服务器可以使用的拓展编码方式



### Trailer

摘自http 权威指南

A trailer can be added to a chunked message if the client’s TE header indicates that it
accepts trailers, or if the trailer is added by the server that created the original
response and the contents of the trailer are optional metadata that it is not necessary
for the client to understand and use (it is okay for the client to ignore and discard the
contents of the trailer).*
The trailer can contain additional header fields whose values might not have been
known at the start of the message (e.g., because the contents of the body had to be
generated first). An example of a header that can be sent in the trailer is the Content-
MD5 header—it would be difficult to calculate the MD5 of a document before the
document has been generated. Figure 15-6 illustrates the use of trailers. The message
headers contain a Trailer header listing the headers that will follow the chunked message.
The last chunk is followed by the headers listed in the Trailer header.
Any of the HTTP headers can be sent as trailers, except for the Transfer-Encoding,
Trailer, and Content-Length headers



### Content-Encoding

是要传输的内容所使用的编码方式，如压缩方式等

### Content-Type

传输的内容的类型，比如html或jpg

### 

### <font color="red">Transfer-Encoding和Content-Encoding的区别</font>

Transfer-Encoding 指定了消息传输的方式，并未转换消息内容本身

Content-Encoding 指定了对消息内容本身所采用的变换方式，如压缩