# unicode

~~~python


"""
抓取基金数据时遇到这样一个问题，将"\u504f\u80a1\u578b\u57fa\u91d1" 转为中文
抓取到的数据类似{"key":"\u504f\u80a1\u578b\u57fa\u91d1"},
用json.dumps()将抓取到的数据转为json时，结果却是这样
{"key":"\\u504f\\u80a1\\u578b\\u57fa\\u91d1"}

我想要的结果是：{"key":"偏股型基金"}
"""

data ="\u504f\u80a1\u578b\u57fa\u91d1"
data.encode("utf-8").decode("unicode-escape")
~~~

