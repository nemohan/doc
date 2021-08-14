# defer

学过golang的人都知道，defer可以定义在函数结束时自动调用的函数，形如defer xx(arg)，这对函数结束时释放资源很便利。但是有个细节可能容易被忽略，就是defer 定义的函数参数是在定义时被求值，而非函数执行时求值

笔者最近就遇到了这个坑。有以下代码片段，但函数xx在遇到错误结束执行时，传递给handleErr的err参数始终为nil。笔者也是费了一番心力才发现使用下面的操作才能解决这个问题，这时才想起defer的某些细节可能被我忽略了，所以去官方文档看了看defer使用介绍，确实有defer定义函数时的参数求值时机这一细节。

~~~go
func xx(){
	var err error
	defer handleErr(err)
    //do something ...
    //err occuer here
}
~~~

正确的操作：

~~~go
func xx(){
    var err error
    defer func(){
        handleErr(err)
    }()
}
~~~

