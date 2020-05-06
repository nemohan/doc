# go tool的使用

[TOC]



### go build 条件编译

构建约束(build constraint)或构建标签，以注释的形式出现，构建标签必须出现在"包声明"之前。如下

~~~go
// +build
~~~

构建约束的求值规则: 以空格分隔的选项使用OR操作符；以逗号分隔的选项使用AND操作符;以!为前缀的选项使用not

~~~
// +build linux,386 darwin,!cgo
~~~

对应

~~~
(linux AND 386) OR (darwin AND (not cgo))
~~~


一个文件可以有多个构建约束

~~~go
// +build linux darwin
// +build 386
~~~

对应

~~~
(linux OR darwin) AND 386
~~~



##### 阻止文件被编译

使用以下的构建约束可以防止文件被编译

~~~go
// +build ignore
~~~



##### 特殊的文件名

若某个文件去掉文件的拓展名或_test后缀后，匹配以下任意一个模式，如source_windows_amd64.go。GOOS和GOARCH代表已知的操作系统或CPU架构，这个文件则定义了隐式的“构建约束”。如dns_windows.go，只有为windows系统编译时，dns_windows.go才会被编译。math_386.s只有为32位的x86架构才会被编译

~~~
*_GOOS
*_GOARCH 
*_GOOS_GOARCH
~~~

Using GOOS=android matches build tags and files as for GOOS=linux in addition to android tags and files.

Using GOOS=illumos matches build tags and files as for GOOS=solaris in addition to illumos tags and files.