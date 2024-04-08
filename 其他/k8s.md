# k8s



## 生成可访问apiserver的token

1 创建serviceAccount

2 将上一步创建的serviceAccount和具有指定权限的clusterRole通过roleBinding进行绑定

3  执行命令"kubectl describe secret xx"获取第一步创建的serviceAccount关联的secret的token。（通过kubectl get secret xx -o yaml获取的token是不可用的)