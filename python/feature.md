## python 2.7 的一些特性

1 不常使用的一些特性



函数式工具

map、reduce、filter

1 enumerate

~~~python
>>> l = "abcd"
>>> for (i,v) in enumerate(l):
    ... print(i,v)
0 a
1 b
2 c
3 d
~~~



2 list comprehension

一般形式:

[ expression for target1 in sequence1 [if condition]
for target2 in sequence2 [if condition] ...
for targetN in sequenceN [if condition] ]

~~~python
>>> [x for x in range(10) if x %2 == 0]
>>> 0,2,4,6,8

~~~



3 zip



4 变量命名的一些约定

~~~python
#大小写敏感
"""   
1 Names that begin with a single underscore (_X) are not imported by a from
module import * statement (described in Chapter 19).
2 Names that have two leading and trailing underscores (__X__) are systemdefined
names that have special meaning to the interpreter.
• Names that begin with two underscores, and do not end with two more (__X)
are localized (“mangled”) to enclosing classes (described in Chapter 26).
• The name that is just a single underscore (_) retains the result of the last expression
when working interactively.
"""
_a # import * 不会自动导入的变量
__a
__a__ #python自己内部使用的一些变量

~~~



5 函数参数匹配

~~~python
1 func(value) Caller Normal argument: matched by position
    
2 func(name=value) Caller Keyword argument: matched by name
    
3 func(*name) Caller Pass all objects in name as individual positional arguments

4 func(**name) Caller Pass all key/value pairs in name as individual keyword arguments


def func(name) Function Normal argument: matches any by position or name
    
def func(name=value) Function Default argument value, if not passed in the call

def func(*name) Function Matches and collects remaining positional arguments (in a tuple)

def func(**name) Function Matches and collects remaining keyword arguments (in a dictionary
~~~



6 module

~~~python
"""
Some C programmers like to compare the Python module import operation to a C
#include, but they really shouldn’t—in Python, imports are not just textual insertions
of one file into another. They are really runtime operations that perform three
distinct steps the first time a program imports a given file:
1. Find the module’s file.
2. Compile it to byte code (if needed).
3. Run the module’s code to build the objects it defines

To better understand module imports, we’ll explore these steps in turn. Bear in mind
that all three of these steps are carried out only the first time a module is imported
during a program’s execution; later imports of the same module bypass all of these
steps, and simply fetch the already loaded module object in memory

1 模块搜索路径
搜索顺序
 1)程序所在 当前目录
 2)PYTHONPATH 环境变量设置的目录
 3)标准库
 4) .pth结尾的文件的内容
 
 以上四个部分定义的路径会以列表的形式保存在sys.path中
 
如何从同一个包里面导入父包中模块
from .. import module_name
"""


~~~



#### 匿名函数lambda

lambda的一般形式:

lambda argument1, argument2: expression using arguments

lambda 和def 的差别:

* lambda 是表达式(expression),不是语句(lambda is an expression, not a statement)
* lambda 的函数体只能是单个表达式，不能是语句块(lambda's body is a single expression,not a block of statements)

~~~python
def func(x, y,z):
  	return x + y +z
#等同的lambda
f = lambda x, y, z: x + y +z
~~~



#### decorator(装饰器)

~~~python
#函数不带参数的装饰器
# t.py
def func_dec(func):
    def new_func():
    	tmp = "call function %s" % func.__name__
        print(tmp)
        return func()
    return new_func

@func_dec
def func():
    print(1)

#等价于 func_dec(func)()
>>> import t
>>> t.func()
call function func
1


#================ 函数带参数的=======================================
def func_dec_with_arg(func):
    def new_func(arg):
    	tmp = "call function func %s with argument:%s" %(func.__name__, arg)
        print(tmp)
        return func(arg)
    return new_func

@func_dec_with_arg
def func_with_arg(a):
    print("arg:", a)
    
>>> import t2
>>> t2.func_with_arg("hello")
call function:func
call function:func_with_arg  arg:hello
arg: hello
# 等价于 func_dec_with_arg(func_with_arg)(arg)

#版本3
def func_dec_with_arg2(arg):
    print("func_dec_with_arg:", arg)
 	def dec_func(func):
        print("dec_func")
    	def real_func():
            print("real_func")
            return func()
        return real_func
    return dec_func

@func_dec_with_arg2(arg)
def func_with_arg2():
    print("++++")
    
#版本4
def func_dec_with_arg2(arg):
    print("func_dec_with_arg2:", arg)
    def dec_func(func):
        print("dec_func")
        def real_func(arg2):
            print("real_func")
            return func(arg2)
        return real_func
    return dec_func

@func_dec_with_arg2("haha")
def func_with_arg2(arg2):
    print("+++++", arg2)


func_with_arg2("no work")


~~~



#### apply

apply 是python内置的函数。调用方式apply(func, args)

~~~python
def echo(*args, **kwargs):
    print args, kwargs
>>> pargs = (1, 2)
>>> kargs= {"a":3, "b":4}
>>> apply(echo, pargs, kargs)
~~~



#### iterator(迭代器)

python3:

这个版本的迭代器不再提供next()方法

python 2.x:

有next()方法

~~~

~~~



#### generator(生成器)

python3:

这个版本不再提供next()方法

~~~python

"""
Unlike normal functions that return a value and exit, generator functions automatically
suspend and resume their execution and state around the point of value generation
"""
def gen(n):
    for i in range(n):
        yield i ** 2
 
~~~

