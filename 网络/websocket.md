# websocket

[TOC]

## 介绍

为什么要引入websocket协议

* 相对于http来说，效率较高。因为头部较小

* 允许客户端-服务器双向通信


## websocket

websocket分为两个阶段

* 握手阶段。客户端发送握手请求到服务器，服务器回复握手请求，确认服务器支持websocket协议并升级到websocket。进入数据传输阶段

* 数据传输阶段


### 握手阶段

#### 握手过程

1. 建立链接后，客户端发送一个http升级请求
2. 服务端回复握手请求

#### 客户端的握手请求

握手请求必须满足的条件：

* 必须是有效的HTTP请求
* 必须使用GET方法，且版本号至少是1.1
* 必须包含`Host`头部
* 必须含有`Upgrade`头部,且值必须是`websocket`
* 必须含有`Connection`头部，且值必须是`Upgrade`
* 必须含有`Sec-WebSocket-Key`头部，值是随机生成的16字节(先生成16字节数值后base64编码），且被base64编码
* 若请求来自浏览器必须包含`Origin`头部，否则不必包含
* 必须含有`Sec-WebSocket-Version`头部,且值是13



握手请求的可选头部：

* `Sec-WebSocket-Protocol`, 其值是逗号分隔的客户端支持的协议
* `Sec-WebSocket-extensions`,其值表示客户端希望的`protocol-level extensions`
* 其他头部比如用于认证的头部`Authorization`



客户端的握手请求：

~~~
 GET /chat HTTP/1.1
        Host: server.example.com
        Upgrade: websocket
        Connection: Upgrade
        Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==
        Origin: http://example.com
        Sec-WebSocket-Protocol: chat, superchat
        Sec-WebSocket-Version: 13
~~~



#### 服务端的握手回复

若服务器在解析握手请求过程中，发现请求包含的信息不满足上面提到的条件，返回4xx错误

若服务端接受握手请求，则回复必须包含的信息：

* 状态码101
* `Upgrade`头部且值是`websocket``
* ``Connection`头部且值是`upgrade`
* `Sec-Websocket-Accept`头部



Sec-Websocket-Accept的值的计算方法：

```
 As an example, if the value of the |Sec-WebSocket-Key| header
   field in the client's handshake were "dGhlIHNhbXBsZSBub25jZQ==", the
   server would append the string "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
   to form the string "dGhlIHNhbXBsZSBub25jZQ==258EAFA5-E914-47DA-95CA-
   C5AB0DC85B11".  The server would then take the SHA-1 hash of this
   string, giving the value 0xb3 0x7a 0x4f 0x2c 0xc0 0x62 0x4f 0x16 0x90
   0xf6 0x46 0x06 0xcf 0x38 0x59 0x45 0xb2 0xbe 0xc4 0xea.  This value
   is then base64-encoded, to give the value
   "s3pPLMBiTxaQ9kYGzzhZRbK+xOo=", which would be returned in the
   |Sec-WebSocket-Accept| header field.
```

服务端的握手回复：

~~~
HTTP/1.1 101 Switching Protocols
        Upgrade: websocket
        Connection: Upgrade
        Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
~~~



### 数据传输阶段

websocket数据传输单元是`frame(帧)`。有两种类型的`frame`,分别是`控制帧`和`数据帧`。`数据帧`具有类型信息表明消息是文本消息还是二进制数据消息。一个消息可能包含多个分片(fragment)，每个分片是一个独立的帧

客户端发送到服务端的帧必须经过`掩码`处理，服务端发送到客户端的帧则禁止进行`掩码`处理

#### 帧的格式

```
 0                   1                   2                   3
      0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
     +-+-+-+-+-------+-+-------------+-------------------------------+
     |F|R|R|R| opcode|M| Payload len |    Extended payload length    |
     |I|S|S|S|  (4)  |A|     (7)     |             (16/64)           |
     |N|V|V|V|       |S|             |   (if payload len==126/127)   |
     | |1|2|3|       |K|             |                               |
     +-+-+-+-+-------+-+-------------+ - - - - - - - - - - - - - - - +
     |     Extended payload length continued, if payload len == 127  |
     + - - - - - - - - - - - - - - - +-------------------------------+
     |                               |Masking-key, if MASK set to 1  |
     +-------------------------------+-------------------------------+
     | Masking-key (continued)       |          Payload Data         |
     +-------------------------------- - - - - - - - - - - - - - - - +
     :                     Payload Data continued ...                :
     + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
     |                     Payload Data continued ...                |
     +---------------------------------------------------------------+
```



* FIN 指示当前的帧是消息的最后一个分片
* RSV1,RSV2,RSV3 必须是0，保留位
* Opcode 4位，表示帧的类型。0 对应当前帧分片；1 对应帧内的数据是文本数据；2对应二进制数据；3-7保留；8 对应关闭链接的帧；9 对应当前帧是ping；0xA对应帧Pong；0xB-0xF为以后的控制帧保留
* Mask 1位。表示数据是否经过`掩码`处理。若为1，则对应的masking key 在masking-key里
* Payload length 数据长度。若payload len的值介于0-125之间，则这就是数据长度；若payload len的值是126，则紧跟在后面的16位用于表示实际长度。若值是127，则紧跟在后面的64位表示数据长度
* masking-key 4字节
* extension-data可选
* application-data

数据帧：

控制帧：

* close
* ping
* pong

## 参考

* rfc6455 <https://tools.ietf.org/html/rfc6455>