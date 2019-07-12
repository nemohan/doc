# python vs go

### python2.x 和 go的一些语法上差异

1 python 没有swtich语句

2 python 循环语句(for 和while) 可以跟随else

~~~python

for a in b:

	statements

else:

	statements

#若for 循环没有被break打断，则else执行

while True:
    statements
else:
    statements
~~~

3 slice的差异

~~~python
python支持负数索引
>>> l = [1, 2, 3]
>>> l[-1]  #负数索引

>>> l[0:-1] # 切片操作同样支持负数

~~~



4 有趣的逻辑操作符

~~~python
python 中的逻辑操作符为 and, or, not
逻辑操作符的几种使用方式:
1 用于生成bool类型的值
 if a and b:
        statements
2 选择合适的初始值
c = a and b # 选择第一个可以确定and结果的表达式为值
d = a or b #选择第一个表达式为True的作为值
>>> 1 and 0
0

>>> 1 and 2
2

>>> 0 and 1
1

>>> 0 or 1
1
>>> 1 or 0
1
>>> 0 or ""
""


~~~



5 空值None



6 Bool类型

7 if 的骚操作

~~~python
a = d if x else y #如果x的值为true, a 为d的值。否则为y的值
>>> a = 2 if 1 else 0
>>> a 
2
~~~



8 你还是你么 ==  vs is

~~~python
a == b 用于比较二者的值是否相等
a is b 比较二者是否指向同一个引用
>>> l = [1, 2]
>>> c = [1, 2]
>>> l == c
True
>>> l is c
False

>>> d = l
>>> d is l
True
~~~



9  list索引和索引处的值

~~~python
l = [1, 2, 3]
for (index, value) in enumerate(l):
	print(index, value)
~~~

10 module、package

~~~python
"""
python 和go 都有包(package)的概念，此外python还多了一个模块(module)概念
在python中每个文件就是一个模块
"""

~~~

