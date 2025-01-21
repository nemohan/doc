# closure

最近看《Programming Rust Fast、Safe Systems Development》，书中提到rust为闭包提供了两种方式从嵌套作用域(enclosing scope)获取数据：转移(move)和借用(borrow)。我最初理解此处的borrow即使用"&"获取的变量的引用，但实际不是。

书中给了一个这样的例子:

~~~rust
let dict = produce_glossary();
let debug_dump_dict = || {
    for (key, value) in dict{
        println!("{:?} - {:?}", key, value)
    }
}

error[E0382]: use of moved value: `debug_dump_dict`
--> closures_debug_dump_dict.rs:18:5
|
19 | debug_dump_dict();
| ----------------- `debug_dump_dict` moved due to this call
20 | debug_dump_dict();
| ^^^^^^^^^^^^^^^ value used here after move
|
note: closure cannot be invoked more than once because it moves the variable
`dict` out of its environment
--> src/main.rs:13:29
|
13 | for (key, value) in dict {
| ^^^^
~~~

若将闭包使用的borrow的语义理解为和使用"&"一样，则显然和上面的示例代码矛盾。为了进一步验证，又写了下面的代码，二者的语义是不同的

~~~rust
fn main() {
    let s = "hello".to_string();
    let func = move || println!("{}", s);
    func();
    println!("{} world", s);
    let refs = &s;
    let func2 = || s == refs;
    println!("{}", func2());
}

error[E0277]: can't compare `String` with `&String`
 --> src/main.rs:8:22
  |
8 |     let func2 = || s == refs;
  |                      ^^ no implementation for `String == &String`
  |
  = help: the trait `PartialEq<&String>` is not implemented for `String`
help: consider dereferencing here
  |
8 |     let func2 = || s == *refs;
  |                         +

For more information about this error, try `rustc --explain E0277`.
error: could not compile `closure` (bin "closure") due to 1 previous error

~~~

