## python 的一些特性

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
Names that begin with a single underscore (_X) are not imported by a from
module import * statement (described in Chapter 19).
• Names that have two leading and trailing underscores (__X _ _) are systemdefined
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



