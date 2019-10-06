# simple_server的启动

wsgiref 是python 提供的一个wsgi标准的参考实现

simple_server 启动一个http server,

2.7

#### simple_server 的启动

入口很简单没有什么需要赘述的，httpd.handle_request的说明在下面

~~~python
if __name__ == '__main__':
    httpd = make_server('', 8000, demo_app)
    sa = httpd.socket.getsockname()
    print "Serving HTTP on", sa[0], "port", sa[1], "..."
    """
    import webbrowser
    webbrowser.open('http://localhost:8000/xyz?abc')
    """
    httpd.handle_request()  # serve one request, then exit
~~~



~~~python

def make_server(
    host, port, app, server_class=WSGIServer, handler_class=WSGIRequestHandler
):
    """Create a new WSGI server listening on `host` and `port` for `app`"""
    server = server_class((host, port), handler_class)
    server.set_app(app)
    return server
~~~



WSGIServer的定义, WSGIServer 继承自HTTPServer

~~~python
class WSGIServer(HTTPServer):

    """BaseHTTPServer that implements the Python WSGI protocol"""

    application = None

    def server_bind(self):
        """Override server_bind to store the server name."""
        print "WSGIServer bind"
        HTTPServer.server_bind(self)
        self.setup_environ()

    def setup_environ(self):
        # Set up base environment
        env = self.base_environ = {}
        env['SERVER_NAME'] = self.server_name
        env['GATEWAY_INTERFACE'] = 'CGI/1.1'
        env['SERVER_PORT'] = str(self.server_port)
        env['REMOTE_HOST']=''
        env['CONTENT_LENGTH']=''
        env['SCRIPT_NAME'] = ''

    def get_app(self):
        return self.application

    def set_app(self,application):
        self.application = application
~~~



HTTPServer 定义在BaseHTTPServer.py中，其定义如下

~~~python
class HTTPServer(SocketServer.TCPServer):

    allow_reuse_address = 1    # Seems to make sense in testing environment

    def server_bind(self):
        """Override server_bind to store the server name."""
        print "HTTPServer bind"
        SocketServer.TCPServer.server_bind(self)
        host, port = self.socket.getsockname()[:2]
        self.server_name = socket.getfqdn(host)
        self.server_port = port
~~~



HTTPServer又继承自SocketServer.TCPServer,其部分定义如下

~~~python
class TCPServer(BaseServer):

    """Base class for various socket-based server classes.

    Defaults to synchronous IP stream (i.e., TCP).

    Methods for the caller:

    - __init__(server_address, RequestHandlerClass, bind_and_activate=True)
    - serve_forever(poll_interval=0.5)
    - shutdown()
    - handle_request()  # if you don't use serve_forever()
    - fileno() -> int   # for select()

    Methods that may be overridden:

    - server_bind()
    - server_activate()
    - get_request() -> request, client_address
    - handle_timeout()
    - verify_request(request, client_address)
    - process_request(request, client_address)
    - shutdown_request(request)
    - close_request(request)
    - handle_error()

    Methods for derived classes:

    - finish_request(request, client_address)

    Class variables that may be overridden by derived classes or
    instances:

    - timeout
    - address_family
    - socket_type
    - request_queue_size (only for stream sockets)
    - allow_reuse_address

    Instance variables:

    - server_address
    - RequestHandlerClass
    - socket

    """

    address_family = socket.AF_INET

    socket_type = socket.SOCK_STREAM

    request_queue_size = 5

    allow_reuse_address = False

    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
        """Constructor.  May be extended, do not override."""
        BaseServer.__init__(self, server_address, RequestHandlerClass)
        self.socket = socket.socket(self.address_family,
                                    self.socket_type)
        if bind_and_activate:
            self.server_bind()
            self.server_activate()

    def server_bind(self):
        """Called by constructor to bind the socket.

        May be overridden.

        """
        if self.allow_reuse_address:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)
       
        self.server_address = self.socket.getsockname()
        
 def server_activate(self):
        """Called by constructor to activate the server.

        May be overridden.

        """
        self.socket.listen(self.request_queue_size)
~~~



TCPServer的父类BaseServer的定义:

~~~python
class BaseServer:

    """Base class for server classes.

    Methods for the caller:

    - __init__(server_address, RequestHandlerClass)
    - serve_forever(poll_interval=0.5)
    - shutdown()
    - handle_request()  # if you do not use serve_forever()
    - fileno() -> int   # for select()

    Methods that may be overridden:

    - server_bind()
    - server_activate()
    - get_request() -> request, client_address
    - handle_timeout()
    - verify_request(request, client_address)
    - server_close()
    - process_request(request, client_address)
    - shutdown_request(request)
    - close_request(request)
    - handle_error()

    Methods for derived classes:

    - finish_request(request, client_address)

    Class variables that may be overridden by derived classes or
    instances:

    - timeout
    - address_family
    - socket_type
    - allow_reuse_address

    Instance variables:

    - RequestHandlerClass
    - socket

    """

    timeout = None

    def __init__(self, server_address, RequestHandlerClass):
        """Constructor.  May be extended, do not override."""
        self.server_address = server_address
        self.RequestHandlerClass = RequestHandlerClass
        self.__is_shut_down = threading.Event()
        self.__shutdown_request = False
~~~



有了上面的类的定义之后，回过头来看其端口绑定。首先，make_server会调用WSGIServer的构造函数来初始化，但WSGIServer并没有定义构造函数，此时就调用其父类或祖先的构造函数。我们逆流而上其父类HTTPServer同样没有定义构造函数，接着来到了TCPServer,TCPServer有构造函数。到此就可以停止查找了。接下来我们看看TCPServer的构造函数做了些什么:

* 调用其父类构造函数及BaseServer的“__init__"函数，父类的构造函数只是保存了服务地址，及请求处理的Handler

* 绑定端口，调用server_bind。但是TCPServer及其子类HTTPServer,孙子(WSGIServer)都定义了server_bind, 那么此时应该调用哪个呢。你也许会说是WSGIServer.server_bind，bingo,答对了。

* 调用server_activate。这里同上应该调用孙子WSGIServer.server_activate。但是WSGIServer并没有实现该方法，如此一来只好去看看儿子HTTPServer有没有了，HTTPServer同样没有实现。只能调用老爷子自己的TCPServer.server_activate了，就是开始监听

  再来看看，WSGIServer.server_bind又做了哪些事情:*

  * 调用父类HTTPServer.server_bind
  * <font color="red">调用WSGIServer.setup_envirion来设置env变量。整个env的设置会在env设置一篇详细介绍</font>



  TCPServer.server_bind做了哪些呢:

  * 绑定端口并获取绑定的地址



WSGIServer--->HTTPServer--->TCPServer---->BaseServer

到此server已经启动了，下一步应该是等待请求到来了。客官别急，咱们先去看看env的设置