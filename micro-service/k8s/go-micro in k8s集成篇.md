# go micro 和k8s

#### 背景

最近项目需要基于微服务进行重新整合。原本的项目都是基于web框架gin开发的，迁移到微服务之后希望可以继续使用gin，这样更便于其他写业务逻辑的同事。

找了两个微服务框架，一个是traefik。没仔细研究，这里就不多讲了。另一个是go micro，micro是一个插件式的微服务框架，不过更像是微服务工具集。

micro 的特性:

* 支持服务发现

* 负载均衡

* RPC通信

* PubSub 异步通信模式

* 编码插件

  

micro的官方文档：https://micro.mu/docs/go-api.html#http-handler

作图工具: http://asciiflow.com/

期望的架构:

~~~
api gateway、service 都运行在k8s管理的容器中
                                     +-----------------+
                                     |                 |
+-----------------+                  |                 |
|                 |                  |                 |
|                 |                  |                 |
|                 |                  |     service     |
|                 +------------------+                 |
|                 |                  |                 |
|      api gateway|                  +-----------------+
|                 |
|                 |                  ------------------+
|                 |                  |                 |
|                 +------------------+     service     |
|                 |                  |                 |
+-----------------+                  |                 |
                                     |                 |
                                     |                 |
                                     |                 |
                                     +-----------------+

~~~



#### 原型搭建

基本架构的原型已经确定，接下来就是搭建基于k8s、micro的微服务架构。

待解决的问题:

* 使用哪种服务发现机制
* api网关怎么实现
* 后端服务如何将gin集成到micro中
* 日志追踪、收集

micro 支持基于etcd、mdns、consul、k8s的服务发现机制。基于以上最初确定了3种服务发现机制。

1）通过k8s + mdns，在k8s内使用基于mdns的服务发现机制(没有尝试)

2) 基于k8s + consul, 在k8s内运行consul（没有尝试)

3) 基于k8s. 使用k8s原生的服务发现机制

结合官方文档我认为前两种方式，应该比较容易。那么第三种方案呢

看官网的文章，看了许久也没有明白应该如何让micro 使用k8s原生的服务发现机制。没办法只好去看micro的代码

~~~go
//github.com/micro/go-plugins/registry/kubernetes/kubernetes.go
// Package kubernetes provides a kubernetes registry
//此包用来实现k8s原生的服务注册、发现
/*
机制: 
注册过程: 当前在容器内的进程通过环境变量KUBERNETES_SERVICE_HOST、KUBERNETES_SERVICE_PORT获取k8s API server的地址和端口。注册时在api server 创建当前pod的micro.mu/selector-servicename= service label来注册服务。

服务发现过程: 调用GetService访问api server筛选出label为micro.mu/selecto-servicename=service的
pod
假设注册了一个名为hello的service。注册时则会在api server 创建一个名为micro.mu/selector-hello=service的label
*/
package kubernetes

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"regexp"
	"strings"
	"time"

	"github.com/micro/go-plugins/registry/kubernetes/client"

	"github.com/micro/go-micro/config/cmd"
	"github.com/micro/go-micro/registry"
)

type kregistry struct {
	client  client.Kubernetes
	timeout time.Duration
	options registry.Options
}

var (
	// used on pods as labels & services to select
	// eg: svcSelectorPrefix+"svc.name"
	svcSelectorPrefix = "micro.mu/selector-"
	svcSelectorValue  = "service"

	labelTypeKey          = "micro.mu/type"
	labelTypeValueService = "service"

	// used on k8s services to scope a serialised
	// micro service by pod name
	annotationServiceKeyPrefix = "micro.mu/service-"

	// Pod status
	podRunning = "Running"

	// label name regex
	labelRe = regexp.MustCompilePOSIX("[-A-Za-z0-9_.]")
)

// podSelector
var podSelector = map[string]string{
	labelTypeKey: labelTypeValueService,
}

func init() {
	cmd.DefaultRegistries["kubernetes"] = NewRegistry
}

//配置
func configure(k *kregistry, opts ...registry.Option) error {
	for _, o := range opts {
		o(&k.options)
	}

	// get first host
	var host string
	//谁的地址，master的地址么?
	if len(k.options.Addrs) > 0 && len(k.options.Addrs[0]) > 0 {
		host = k.options.Addrs[0]
	}

	if k.options.Timeout == 0 {
		k.options.Timeout = time.Second * 1
	}

	// if no hosts setup, assume InCluster
	var c client.Kubernetes
	if len(host) == 0 {
		//当前进程运行在pod内
		c = client.NewClientInCluster()
	} else {
		c = client.NewClientByHost(host)
	}

	k.client = c
	k.timeout = k.options.Timeout

	return nil
}

// serviceName generates a valid service name for k8s labels
func serviceName(name string) string {
	aname := make([]byte, len(name))

	for i, r := range []byte(name) {
		if !labelRe.Match([]byte{r}) {
			aname[i] = '_'
			continue
		}
		aname[i] = r
	}

	return string(aname)
}

// Init allows reconfig of options
func (c *kregistry) Init(opts ...registry.Option) error {
	return configure(c, opts...)
}

// Options returns the registry Options
func (c *kregistry) Options() registry.Options {
	return c.options
}

// Register sets a service selector label and an annotation with a
// serialised version of the service passed in.
func (c *kregistry) Register(s *registry.Service, opts ...registry.RegisterOption) error {
	if len(s.Nodes) == 0 {
		return errors.New("you must register at least one node")
	}

	// TODO: grab podname from somewhere better than this.
	podName := os.Getenv("HOSTNAME")
	svcName := s.Name

	// encode micro service
	b, err := json.Marshal(s)
	if err != nil {
		return err
	}
	svc := string(b)

	pod := &client.Pod{
		Metadata: &client.Meta{
			Labels: map[string]*string{
				labelTypeKey:                             &labelTypeValueService,
				svcSelectorPrefix + serviceName(svcName): &svcSelectorValue,
			},
			Annotations: map[string]*string{
				annotationServiceKeyPrefix + serviceName(svcName): &svc,
			},
		},
	}

	//TODO: c.client 是哪个。是kubernets.NewClient创建的
	if _, err := c.client.UpdatePod(podName, pod); err != nil {
		return err
	}

	return nil

}

// Deregister nils out any things set in Register
func (c *kregistry) Deregister(s *registry.Service) error {
	if len(s.Nodes) == 0 {
		return errors.New("you must deregister at least one node")
	}

	// TODO: grab podname from somewhere better than this.
	podName := os.Getenv("HOSTNAME")
	svcName := s.Name

	pod := &client.Pod{
		Metadata: &client.Meta{
			Labels: map[string]*string{
				svcSelectorPrefix + serviceName(svcName): nil,
			},
			Annotations: map[string]*string{
				annotationServiceKeyPrefix + serviceName(svcName): nil,
			},
		},
	}

	if _, err := c.client.UpdatePod(podName, pod); err != nil {
		return err
	}

	return nil

}

// GetService will get all the pods with the given service selector,
// and build services from the annotations.
func (c *kregistry) GetService(name string) ([]*registry.Service, error) {
	pods, err := c.client.ListPods(map[string]string{
		svcSelectorPrefix + serviceName(name): svcSelectorValue,
	})
	if err != nil {
		return nil, err
	}

	if len(pods.Items) == 0 {
		return nil, registry.ErrNotFound
	}

	// svcs mapped by version
	svcs := make(map[string]*registry.Service)

	// loop through items
	for _, pod := range pods.Items {
		if pod.Status.Phase != podRunning {
			continue
		}
		fmt.Printf("getService name:%s %s\n", name, annotationServiceKeyPrefix+serviceName(name))
		// get serialised service from annotation
		svcStr, ok := pod.Metadata.Annotations[annotationServiceKeyPrefix+serviceName(name)]
		if !ok {
			continue
		}

		// unmarshal service string
		var svc registry.Service
		err := json.Unmarshal([]byte(*svcStr), &svc)
		if err != nil {
			return nil, fmt.Errorf("could not unmarshal service '%s' from pod annotation", name)
		}
		fmt.Printf("GetService %v\n", svc)

		// merge up pod service & ip with versioned service.
		vs, ok := svcs[svc.Version]
		if !ok {
			svcs[svc.Version] = &svc
			continue
		}

		fmt.Printf("ok")
		vs.Nodes = append(vs.Nodes, svc.Nodes...)
	}

	var list []*registry.Service
	for _, val := range svcs {
		list = append(list, val)
	}
	return list, nil
}

// ListServices will list all the service names
func (c *kregistry) ListServices() ([]*registry.Service, error) {
	pods, err := c.client.ListPods(podSelector)
	if err != nil {
		return nil, err
	}

	// svcs mapped by name
	svcs := make(map[string]bool)

	for _, pod := range pods.Items {
		if pod.Status.Phase != podRunning {
			continue
		}
		for k, v := range pod.Metadata.Annotations {
			if !strings.HasPrefix(k, annotationServiceKeyPrefix) {
				continue
			}

			// we have to unmarshal the annotation itself since the
			// key is encoded to match the regex restriction.
			var svc registry.Service
			if err := json.Unmarshal([]byte(*v), &svc); err != nil {
				continue
			}
			svcs[svc.Name] = true
		}
	}

	var list []*registry.Service
	for val := range svcs {
		list = append(list, &registry.Service{Name: val})
	}
	return list, nil
}

// Watch returns a kubernetes watcher
func (c *kregistry) Watch(opts ...registry.WatchOption) (registry.Watcher, error) {
	return newWatcher(c, opts...)
}

func (c *kregistry) String() string {
	return "kubernetes"
}


//注册服务
// NewRegistry creates a kubernetes registry
//创建新的注册机制
func NewRegistry(opts ...registry.Option) registry.Registry {
	k := &kregistry{
		options: registry.Options{},
	}
	configure(k, opts...)
	return k
}

~~~







后端服务

~~~go
package main

import(
        "net/http"
        "os"
        "github.com/micro/go-micro/web"
        k8s "github.com/micro/examples/kubernetes/go/web"
)

func main(){
        service := k8s.NewService(web.Name("hello"))

        service.HandleFunc("/world", func(w http.ResponseWriter, r *http.Request){
                w.Write([]byte(os.Getenv("HOSTNAME")))
        })

        service.HandleFunc("/hello/world", func(w http.ResponseWriter, r *http.Request){
                w.Write([]byte(os.Getenv("HOSTNAME") +"haha"))
        })

        service.Init()
        service.Run()
}

~~~



api 网关

~~~go
package main

import(
        "github.com/micro/go-micro/web"
        //k8s "github.com/micro/examples/kubernetes/go/web"
        "github.com/micro/go-micro/api/handler/http"
        "github.com/micro/go-micro/api/handler"
        "github.com/micro/go-plugins/registry/kubernetes"
        "github.com/micro/go-micro/api/router/registry"
        "github.com/micro/go-micro/api/router"
)

func main(){
        router := registry.NewRouter(router.WithRegistry(kubernetes.NewRegistry()), router.WithHandler("http"))
        httpHandler := http.NewHandler(handler.WithRouter(router))

        service := web.NewService(web.Name("api-gateway"), web.Handler(httpHandler))
        service.Init()
        service.Run()

}

~~~



~~~go
// Package http is a http reverse proxy handler
package http

import (
	"errors"
	"fmt"
	"net/http"
	"net/http/httputil"
	"net/url"

	"github.com/micro/go-micro/api"
	"github.com/micro/go-micro/api/handler"
	"github.com/micro/go-micro/client/selector"
)

const (
	Handler = "http"
)

type httpHandler struct {
	options handler.Options

	// set with different initialiser
	s *api.Service
}

//
func (h *httpHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	service, err := h.getService(r)
	if err != nil {
		w.WriteHeader(500)
		return
	}

	if len(service) == 0 {
		w.WriteHeader(404)
		return
	}

	fmt.Printf("pass 404===================")
	//通过解析service得到得地址和端口作为后端服务得地址和端口
	rp, err := url.Parse(service)
	if err != nil {
		w.WriteHeader(500)
		return
	}

	httputil.NewSingleHostReverseProxy(rp).ServeHTTP(w, r)
}

// getService returns the service for this request from the selector
func (h *httpHandler) getService(r *http.Request) (string, error) {
	var service *api.Service

	fmt.Printf("h.s %v h.options.Router %v req:%v\n", h.s, h.options.Router, r.Host)
	if h.s != nil {
		// we were given the service
		service = h.s
	} else if h.options.Router != nil {
		// try get service from router
		s, err := h.options.Router.Route(r)
		if err != nil {
			return "", err
		}
		service = s
	} else {
		// we have no way of routing the request
		return "", errors.New("no route found")
	}

	// create a random selector
	next := selector.Random(service.Services)

	// get the next node
	s, err := next()
	if err != nil {
		return "", nil
	}

	fmt.Printf("address %s\n", s.Address)
	return fmt.Sprintf("http://%s", s.Address), nil
}

func (h *httpHandler) String() string {
	return "http"
}

// NewHandler returns a http proxy handler
func NewHandler(opts ...handler.Option) handler.Handler {
	options := handler.NewOptions(opts...)

	return &httpHandler{
		options: options,
	}
}

// WithService creates a handler with a service
func WithService(s *api.Service, opts ...handler.Option) handler.Handler {
	options := handler.NewOptions(opts...)

	return &httpHandler{
		options: options,
		s:       s,
	}
}

~~~



~~~go

~~~

