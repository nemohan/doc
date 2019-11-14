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

* decorator的返回值须是可调用的对象(函数，对象函数)
* decorator方便在调用函数之前以及之后做些额外操作
* 若装饰器自带参数，那么调用装饰器时传递的参数就是自带参数
* 若装饰器不带参数，那么调用时传递的参数就是被装饰的函数
* 被装饰的函数不带参数，装饰器函数有一层足以
* 若被装饰的函数有参数，那么装饰器（不带参数)至少嵌套两层，第一层的函数接收被装饰的函数，第二层函数接收被装饰函数的参数

~~~python

#函数不带参数的装饰器
# t.py
def func_dec(func):
    def new_func():
    	tmp = "call function %s" % func.__name__
        print(tmp)
        return func()
    return new_func

#第二种形式
def func_dec(func):
    print("call function %s" % func.__name__)
    return func

@func_dec
def func():
    print(1)

#等价于 func_dec(func)()
>>> import t
>>> t.func()
call function func
1


#================ 函数带参数=======================================
#若想记录被调用的函数及其参数只能用这种形式的
def func_dec_with_arg(func):
    def new_func(arg):
    	tmp = "call function func %s with argument:%s" %(func.__name__, arg)
        print(tmp)
        return func(arg)
    return new_func

#simple
def func_dec_with_arg(func):
    print("call function func %s" % func.__name__)
    return func

@func_dec_with_arg
def func_with_arg(a):
    print("arg:", a)
    
>>> import t2
>>> t2.func_with_arg("hello")
call function:func_with_arg  arg:hello
arg: hello
# 等价于 func_dec_with_arg(func_with_arg)(arg)



#========================== 带参数的装饰器===================================
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

# 应该按下面的方法写
def func_dec_with_arg2(arg):
    print("func_dec_with_arg:", arg)
    def dec_func(func):
        return func
    return dec_func

@func_dec_with_arg2("hello")
def func_with_arg2():
    print("++++")

func_with_arg2()
"""
func_dec_with_arg: hello
dec_func
real_func
++++
"""



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


####
@a @b @c
def func():
    pass
func = a(b(c(func)))
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



#### 默认参数

~~~python
def test_default(x=[]):
    x.append(1)
    print(x)

test_default()
test_default()

运行结果:
[1]
[1, ]
~~~



#### class

* 支持方法重载，即子类方法可以覆盖父类同名方法

* 支持操作符重载。

* python不提供默认的操作符重载方法

* 父类的构造函数，不会被自动调用

* <font color='red'>类也是对象</font>

* inheritance searches only happen on reference, not on assignment).


~~~python
#操作符重载命名规范:__x__
#每个类的实例都有一个__class__属性，指向其类
#每个类对象都有一个__base__属性tuple类型，指向其父类
"""
Each instance has a link to its class for inheritance,
though—it’s called _ _class_ _, if you want to inspect it:
>>> x._ _class_ _
<class _ _main_ _.rec at 0x00BAFF60>
Classes also have a _ _bases_ _ attribute, which is a tuple of their superclasses; these
two attributes are how class trees are literally represented in memory by Python.
The main point to take away from this look under the hood is that Python’s class
model is extremely dynamic. Classes and instances are just namespace objects, with
attributes created on the fly by assignment. Those assignments usually happen
within the class statements you code, but they can occur anywhere you have a reference
to one of the objects in the tree.
"""
#抽象类
class super:
    def delegete(self):
        self.action()
class provider(super):
    def action(self):
        print("provide action")
>>> x = provider()
>>> x.delegete()
provide action

"""
常见重载操作符:
__init__ 构造函数
__del__ 析构函数
__call__ 函数调用
__getattr__ 获取成员
__setattr__ 设置成员变量
__getitem__ 索引
__iter__ 迭代器
__next__ python 3.x
"""

"""
 成员访问: __getattribute__ 
 python 2.x 只适用于new-style类
 python 3.x new-sytle和classic-style 都适用
The _ _getattribute_ _ method, available for new-style classes only, allows a class to
intercept all attribute references, not just undefined references (like _ _getattr_ _). It
is also substantially trickier to use than _ _getattr_ _ and _ _setattr_ _ (it is prone to
loops). I’ll defer to Python’s standard documentation for more details on this
method.
"""
~~~

##### 操作符重载

~~~python
#__getitem__ 买一赠一堆
#如果类定义了__getitem__重载操作符，除了可用于索引使用外，在for、in、list comprehension、类型转换、map内置函数等情况下亦可使用
class A:
    def __init__(self, data):
        self.data = data
    def __getitem__(self, i):
        return self.data[i]
>>> X = A("Spam")
>>> 'p' in X # All call _ _getitem_ _ too
1
>>> [c for c in X] # List comprehension
['S', 'p', 'a', 'm']
>>> map(None, X) # map calls
['S', 'p', 'a', 'm']
>>> (a, b, c, d) = X # Sequence assignments
>>> a, c, d
('S', 'a', 'm')
>>> list(X), tuple(X), ''.join(X)
(['S', 'p', 'a', 'm'], ('S', 'p', 'a', 'm'), 'Spam')
>>> X
<_ _main_ _.stepper instance at 0x00A8D5D0>


#__iter__ 迭代
"""
Today, all iteration contexts in Python will try the _ _iter_ _ method first, before trying
_ _getitem_ _. That is, they prefer the iteration protocol we learned about in
Chapter 13 to repeatedly indexing an object; if the object does not support the iteration
protocol, indexing is attempted instead.
Technically, iteration contexts work by calling the iter built-in function to try to
find an _ _iter_ _ method, which is expected to return an iterator object. If it’s provided,
Python then repeatedly calls this iterator object’s next method to produce
items until a StopIteration exception is raised. If no such _ _iter_ _ method is found,
Python falls back on the _ _getitem_ _ scheme, and repeatedly indexes by offsets as
before, until an IndexError exception is raised

在所有迭代上下文中，python首先尝试调用__iter__。若没找到__iter__方法，则尝试__getitem__方法
"""
~~~

###### 属性设置、获取

~~~python
# __getattr__  __setattr__
#当类的实例定义了属性x时，访问x 不会调用__getattr__。若没有定义则会调用__getattr__
class A:
    def __init__(self):
        self.name = "hz"
    def __getattr__(self, attrname):
        print("attrname:", attrname, "not defined")
	def __setattr__(self, attrname, value):
        tmp = "set attrname:%s value:%s" %(attrname, value)
        print(tmp)
        self.__dict__[attrname] = value
>>> a = A
>>> print(a.name)
hz
>>> a.age
attrname age not defined

>>> a.name = "tt"
set attrname:name value:tt
>>> a.no = 10
set  attrname:no value:10
#__setattr__  使用时要避免递归调用。所以在__setattr__里面不能使用self.x = v的形式。必须使用
#self.__dict__[x] = v的形式

~~~

###### 字符串表示操作符

~~~python
#__str__,__repr__ 需要将类实例转换成字符串的地方，会首先调用__str__，若没有找到则调用__repr__。反过来不成立
~~~

###### 函数调用操作符

~~~python
#__call__ 函数式对象
class A:
    def __init__(self):
        self.data = 2
    def __call__(self, value):
        return self.data * value
>>> a = A()
>>> a(3)
>>> 6
~~~

###### 继承

支持多重继承

2.x

* new style class(class inheritance from class object)多重继承的成员搜索顺序是广度优先，从左到右
* classic class 的多重继承的成员搜索顺序是深度优先

3.x

* 广度优先

* python 3.x classic class 的多重继承的成员搜索顺序也是广度优先

~~~python
#classic style
class A:
 	attr=1
class B(A):
  	pass
class C(A):
    attr=2
class D(B,C):
    pass
x = D()
print(x.attr)

#new style
class A(object):
 	attr=1
class B(A):
  	pass
class C(A):
    attr=2
class D(B,C):
    pass
x = D()
print(x.attr)
~~~

###### name mangling

<font color="red">Here’s how name mangling works: names inside a class statement that start with
two underscores, but don’t end with two underscores, are automatically expanded to
include the name of the enclosing class. For instance, a name like __X within a class
named Spam is changed to _Spam_ _X automatically: the original name is prefixed with
a single underscore, and the enclosing class’ name. Because the modified name
contains the name of the enclosing class, it’s somewhat unique; it won’t clash with
similar names created by other classes in a hierarchy</font>

python2、python3都保留了此特性。



###### class的 property

property 提供了一种访问类成员的一种新的方式

语法: property(get, set, del, docstring)

~~~python
class A(object):
    def getage(self):
        return 40
    age = property(getage, None, None, None)
>>> x = A()
>>> x.age  #call getage
40
~~~

###### 类的静态方法和类方法(static method vs class method)

~~~python
class Multi:
def imeth(self, x): # Normal instance method
print self, x
def smeth(x): # Static: no instance passed
print x
def cmeth(cls, x): # Class: gets class, not instance
print cls, x
smeth = staticmethod(smeth) # Make smeth a static method
cmeth = classmethod(cmeth) # Make cmeth a class method.

"""
Technically, Python now supports three kinds of class-related methods: instance,
static, and class. Instance methods are the normal (and default) case that we’ve seen
in this book. You must always call an instance method with an instance object.
When you call it through an instance, Python passes the instance to the first (leftmost)
argument automatically; when you call it through a class, you pass along the
instance manually:
>>> obj = Multi( ) # Make an instance
>>> obj.imeth(1) # Normal call, through instance
<_ _main_ _.Multi instance...> 1
>>> Multi.imeth(obj, 2) # Normal call, through class
<_ _main_ _.Multi instance...> 2
By contrast, static methods are called without an instance argument; their names are
local to the scopes of the classes in which they are defined, and may be looked up by
inheritance. Mostly, they work like simple functions that happen to be coded inside
a class:
>>> Multi.smeth(3) # Static call, through class
3
>>> obj.smeth(4) # Static call, through instance
4
Class methods are similar, but Python automatically passes the class (not an instance)
in to a class method’s first (leftmost) argument:
>>> Multi.cmeth(5) # Class call, through class
_ _main_ _.Multi 5
>>> obj.cmeth(6) # Class call, through instance
_ _main_ _.Multi 6
"""
~~~



#### 异常

* python 2.x版本支持两种类型异常，字符串类型、对象类型
* 字符串类型的异常，通过is方法判定是否是能捕获该异常
* 对象类型通过继承关系来判定，即父类可以捕获子类型异常

* try except
* raise
* assert  
* with  as
* python 3.x 类类型异常，必须继承自BaseException 或Exception. python 2.x无此要求

~~~python
#try except、 try finally  python 2.x的语法
try:
except name, data:
except name1:
    <statements> #run if name1 is raised.
else:
    <statements> #run if no exception was raised during try block
    
#python 3.x的语法
try:
   	<statements>
except name as e:
    <statements>



try:
   	<statements>
finally:
    <statements>  #有没有异常抛出都会执行。抛出异常时，执行了finally的语句后，异常继续传播
    
#raise 抛出异常
#python 2.x 
raise E,V		#抛出指定类型的异常，外带附加数据
raise E			#抛出指定类型的异常
raise 			#重新抛出最近的异常
#python 3.x raise E(V)
#assert  assert test,data 如果test结果为false,则抛出异常


#类类型异常
class A(Exception): pass
class B(A): pass
class C(A): pass

def f0():
    raise A()

def f1():
    raise B()

def f2():
    raise C()

for func in (f0,f1,f2):
    try:
        func()
    except A:
        import sys
        print(sys.exc_info()[0])

~~~



###### with as

~~~python
"""
Here’s how the with statement actually works:
1. The expression is evaluated, and results in an object known as a context manager,
which must have _ _enter_ _ and _ _exit_ _ methods.
2. The context manager’s _ _enter_ _ method is called. The value it returns is
assigned to a variable if the as clause is present, or simply discarded otherwise.
3. The code in the nested with block is executed.
4. If the with block raises an exception, the _ _exit_ _(type, value, traceback) method
is called with the exception details. Note that these are the same values returned by
sys.exc_info, described in Python manuals and later in this part of the book. If this
method returns a false value, the exception is reraised; otherwise, the exception is
terminated. The exception should normally be reraised so that it is propagated outside
the with statement.
5. If the with block does not raise an exception, the _ _exit_ _ method is still called,
but its type, value, and traceback arguments are all passed in as None
"""
# with语句  上下文管理协议.
#支持上下文管理协议的类，重载__enter__, __exit__方法。__enter__的返回结果作为as变量的值.
#with里面的语句执行结束后，有没有异常发生都会调用__exit__方法
with expression [as variable]:
    <statements>

from _ _future_ _ import with_statement # Required in Python 2.5
class TraceBlock:
	def message(self, arg):
		print 'running', arg
	def _ _enter_ _(self):
		print 'starting with block'
		return self
	def _ _exit_ _(self, exc_type, exc_value, exc_tb):
		if exc_type is None:
			print 'exited normally\n'
		else:
			print 'raise an exception!', exc_type
		return False # propagate
with TraceBlock( ) as action:
	action.message('test 1')
	print 'reached'
    
with TraceBlock( ) as action:
	action.message('test 2')
	raise TypeError
	print 'not reached'

% python withas.py
starting with block
running test 1
reached
exited normally
starting with block
running test 2
raise an exception! <type 'exceptions.TypeError'>
Traceback (most recent call last):
File "C:/Python25/withas.py", line 22, in <module>
raise TypeError
TypeError
~~~



#### 基类调用子类方法

在基类的方法中调用子类拥有的同名方法时，调用的是子类方法。若最低层的子类没有该实现该方法，则调用其高层的方法

~~~python
class A:
    def __init__(self):
        print "init"
        self.setup()
        self.handle()
    def handle(self):
        print "a"
        
    def setup(self):
        print "set a"


class B(A):
    def handle(self):
        print "b"
    def setup(self):
        print "set b"


class C(B):
    def handle(self):
        print "c"

    def setup(self):
        print "set c"

c = C()

init 
set c
c 

#++++++++++++++++++++++++++++++++++++++++++++++++++++++
class A:
    def __init__(self):
        print "init"
        self.setup()
        self.handle()
    def handle(self):
        print "a"
        
    def setup(self):
        print "set a"


class B(A):
    def handle(self):
        print "b"
    def setup(self):
        print "set b"


class C(B):
    def handle(self):
        print "c"


c = C()

init 
set b
c 

~~~



#### 基类方法可以访问子类成员

~~~python
class A:
    def __init__(self):
        print "init"
        self.setup()
        self.handle()
    def handle(self):
        print "a"
        
    def setup(self):
        print "set a"
    def test(self):
        self.setup()


class B(A):
    def handle(self):
        print "b"
    def setup(self):
        print "set b"
    def out(self):
        print self.c


class C(B):
    def __init__(self):
        self.c = 1
    def handle(self):
        print "c"

    def setup(self):
        print "set c"

c = C()

c.test()
c.out()


输出:
    set c
    1
~~~

