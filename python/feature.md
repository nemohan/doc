## python 2.7 的一些特性

1 不常使用的一些特性

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

