# docker



## 使用docker作为跨平台编译环境

安装 `binfmt` 支持多平台

~~~
docker run --privileged --rm tonistiigi/binfmt --install all
~~~



创建自定义构建器时，需指定 `--driver-opt network=host` 并加载允许非 HTTPS 的配置文件

~~~
docker buildx create \
  --name mybuilder \
  --driver docker-container \
  --driver-opt network=host \
  --config /etc/buildkit/buildkitd.toml \
  --platform linux/amd64,linux/arm64
~~~

其中 `/etc/buildkit/buildkitd.toml` 内容需包含：

~~~toml
debug = true
insecure-entitlements = ["network.host", "security.insecure"]
[registry."http://私有仓库IP:端口"]
  http = true
  insecure = true
~~~

启用构建器:

~~~
docker buildx use mybuilder

~~~

构建多平台镜像:

~~~
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t 私有仓库IP:端口/镜像名:标签 \
  --push .

~~~

