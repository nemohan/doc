## json parser

~~~python
import scanner

class Parser():
    def __init__(self, buf):
        self.obj = None
        self.scanner = scanner.Scanner(data)
        
    def parse_obj(self):
        self.scanner.match("{")
        #obj = {}
        if not self.obj:
            self.obj = {}
        self.parse_key()
        token, lexeme = self.scanner.next()
        self.scanner.match("}")

    def parse_array(self):
        pass

    def parse_key(self):
        scanner = self.scanner
        token, lexeme = self.scanner.next()
        self.scanner.match(lexeme)
        self.obj[lexeme] = None
        key = lexeme

        token, lexeme = self.scanner.next()
        if scanner.match(":"):
            self.obj[key] = self.parse_value()

        token, lexeme = scanner.next()
        if scanner.match(","):
            self.parse_key()

    def parse_value(self):
        scanner = self.scanner
        token, lexeme = scanner.next()
        print(token, lexeme)
        # 若这要解析对象改怎么修改
        if scanner.match("{"):
            pass
        if scanner.match("["):
            return self.parse_array()
        #TODO: optimize this
        elif scanner.match('\\'):
            return self.parse_value()
        elif scanner.match('"'):
            token, lexeme = scanner.next()
            key = lexeme
            scanner.match(lexeme)
            token, lexeme = scanner.next()
            if scanner.match('"'):
                print(key)
                return key
        else:
            return lexeme

        return

    def parse_kv():
        pass


if __name__ == "__main__":
    data = '{key:"hello", value:"world", tt:123}'
    parser = Parser(data)
    parser.parse_obj()
    print("obj:", parser.obj)
    
    """
    这一版的问题:
    无法解析对象嵌套对象的问题
    """
    
    ### version2 =================================================
import scanner

class Parser():
    def __init__(self, buf):
        self.obj = None
        self.scanner = scanner.Scanner(data)

    def parse_obj(self):
        token, lexeme = self.scanner.next()
        self.scanner.match("{")
        if not self.obj:
            self.obj = {}
        self.parse_key()
        token, lexeme = self.scanner.next()
        self.scanner.match("}")

    def parse_array(self):
        pass

    def parse_key(self):
        scanner = self.scanner
        token, lexeme = self.scanner.next()
        self.scanner.match(lexeme)
        self.obj[lexeme] = None
        key = lexeme

        token, lexeme = self.scanner.next()
        if scanner.match(":"):
            self.obj[key] = self.parse_value()

        token, lexeme = scanner.next()
        if scanner.match(","):
            self.parse_key()

    def parse_value(self):
        scanner = self.scanner
        token, lexeme = scanner.next()
        print(token, lexeme)
        if scanner.match("{"):
            old_obj = self.obj
            self.obj = {}
            self.parse_key()
            new_obj = self.obj
            self.obj = old_obj
            print(new_obj) 
            return new_obj
        if scanner.match("["):
            return self.parse_array()
        #TODO: optimize this
        elif scanner.match('\\'):
            return self.parse_value()
        elif scanner.match('"'):
            token, lexeme = scanner.next()
            key = lexeme
            scanner.match(lexeme)
            token, lexeme = scanner.next()
            if scanner.match('"'):
                print(key)
                return key
        else:
            return lexeme

        return

    def parse_kv():
        pass


if __name__ == "__main__":
    data = '{key:"hello", value:"world", tt:{xx:"123", yy:{zz:"456"}}}'
    parser = Parser(data)
    parser.parse_obj()
    print("obj:", parser.obj)


~~~



~~~python
import codecs, time

_punc = 0
_str = 1
_key = 2
_eof = 3


class Scanner():
    def __init__(self, buf):
        self.buf = buf
        self.begin = 0
        self.end = None
        self.forward = 0 
        self.buf_size = len(buf)
        

    def next(self):
        while self.forward < self.buf_size:
            i = self.forward
            c = self.buf[i]
            if c == "{":
                self.end = i + 1
                return _punc, self.lexeme() 
            elif c == "}":
                self.forward += 1
                self.end = i + 1
                return _punc, self.lexeme()
            elif c == "[":
                self.end = i + 1
                return _punc, self.lexeme()

            elif c == "]":
                self.end = i + 1
                return _punc, self.lexeme()

            elif c == ":":
                if self.begin != self.forward:
                    self.end = i 
                    self.forward -= 1
                else:
                    self.end += 1
                return _key, self.lexeme()
            elif c == ",":
                if self.begin != self.forward:
                    self.end = i 
                    self.forward -= 1
                else:
                    self.end += 1
                return _punc, self.lexeme()
            elif c == '"':
                if self.begin != self.forward:
                    self.end = i 
                    self.forward -= 1
                else:
                    self.end += 1

                return _punc, self.lexeme()
            else:
                self.forward += 1
        return _eof, ""

    def lexeme(self):
        return str(self.buf[self.begin:self.end])

    def match(self, lexeme):
        if str(self.buf[self.begin:self.end]) == lexeme:
            self.forward += 1
            self.begin = self.forward
            return True
        return False

def load_test_data():
    f = codecs.open("1.json", "r", encoding="utf-8")
    data = f.read()
    data = data.lstrip(r""""//<script>location.href='http://sina.com.cn'; </script>\nIO.XSRV2.CallbackList['AzyM$roc3MtVGb9I']((""")
    data = data.rstrip('))"\n')
    return data

if __name__ == "__main__":
    '''
    f = codecs.open("1.json", "r", encoding="utf-8")
    data = f.read()
    data = data.lstrip(r""""//<script>location.href='http://sina.com.cn'; </script>\nIO.XSRV2.CallbackList['AzyM$roc3MtVGb9I']((""")
    data = data.rstrip('))"\n')
    '''
    data = '{key:"hello", value:"world"}'
    scanner = Scanner(data)
    while True:
        token, lexeme = scanner.next()
        if token == _eof:
            break
        print(token, lexeme, flush=True)
        time.sleep(1)
        scanner.match(lexeme)

        

~~~

