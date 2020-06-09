# SHA1WithRsa 签名算法

2019/9/25

今天对接支付平台，拿到平台给的测试密钥后，一直报如下错误

structure error: tags don't match (16 vs {class:1 tag:13 length:73 isCompound:false}) {optional:false explicit:false application:false private:false defaultValue:<nil> tag:<nil> stringType:0 timeType:0 set:false omitEmpty:false} pkcs8 @2

### SHA1WithRsa

~~~go
//有的签名需要bas464解码
//data, err := base64.StdEncoding.DecodeString(testMerchantPrivateKey)

privateKey, err := x509.ParsePKCS8PrivateKey(keyData)

    if err != nil {

        return nil, err

    }
    rsaPrivateKey := privateKey.(*rsa.PrivateKey)
   //param 为待签名参数
    hashed := sha1.Sum([]byte(param))
    signParam, err := rsa.SignPKCS1v15(nil, rsaPrivateKey, crypto.SHA1, hashed[:])
~~~

<font color="red"> 若调用x509.ParsePKCS8PrivateKey 遇到如下错误，有可能是密钥需要base64解码</font>

structure error: tags don't match (16 vs {class:1 tag:13 length:73 isCompound:false}) {optional:false explicit:false application:false private:false defaultValue:<nil> tag:<nil> stringType:0 timeType:0 set:false omitEmpty:false} pkcs8 @2



 