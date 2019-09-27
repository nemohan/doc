# request.Body的坑

### 背景

我们的后台项目是基于go-micro的微服务，网关部分也是基于go-micro.  笔者在上面添加了权限检查的中间件。

使用过程中时不时都会出现POST/PUT请求体传递的参数不完整的现象，开始一直认为可能是前端同事的bug,也就没有细究。最近出现这种情况越来越频繁，笔者也很郁闷，正好趁此机会彻底解决一下。

### 解决

既然是消息体不完整，那就来看一下是否是真的不完整。用tcpdump抓包观察消息体发现是完整的，只是消息体分成了两个tcp 包。如此一来问题就明朗了， 就是在调用req.Body.Read时，只读到了第一部分数据。

克隆请求的代码如下:

~~~go
func cloneRequest(req *http.Request){
    contentLen := req.ContentLength
    buf := make([]byte, contnetLen)
    req.Body.Read(buf)
    body.Close()

	newBuf := make([]byte, contentLen)
	copy(newBuf, buf)
	req.Body = ioutil.NopCloser(bytes.NewReader(buf))
	clonedBody := bytes.NewReader(newBuf)
	newReq, err := http.NewRequest(req.Method, req.RequestURI, clonedBody)
}
~~~



修改之后的代码:

~~~go
func cloneRequest(req *http.Request){
    contentLen := req.ContentLength
    buf, _ := ioutil.ReadAll(req.Body) //重点, ReadAll直到遇到EOF错误才会返回
    body.Close()
	
	newBuf := make([]byte, contentLen)
	copy(newBuf, buf)
	req.Body = ioutil.NopCloser(bytes.NewReader(buf))
	clonedBody := bytes.NewReader(newBuf)
	newReq, err := http.NewRequest(req.Method, req.RequestURI, clonedBody)
}
~~~

