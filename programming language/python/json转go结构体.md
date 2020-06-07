# json 转换为go 结构体

~~~python
def map_to_go_struct(structName, kv):
    print("type elecSheet struct{")
    
    for k in kv:
        vType = ""
        if isinstance(kv[k],int):
            vType = "int"
        else:
            vType = "string"
        msg = "%s %s" % (k, vType)
        print(msg)
        

    print("}")
~~~

