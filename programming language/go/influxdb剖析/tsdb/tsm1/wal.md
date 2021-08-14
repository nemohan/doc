# wal

[TOC]



## 总结



文件格式:

~~~
// The entries values are encode as follows:
 //
 // For each key and slice of values, first a 1 byte type for the []Values
 // slice is written.  Following the type, the length and key bytes are written.
 // Following the key, a 4 byte count followed by each value as a 8 byte time
 // and N byte value.  The value is dependent on the type being encoded.  float64,
 // int64, use 8 bytes, boolean uses 1 byte, and string is similar to the key encoding,
 // except that string values have a 4-byte length, and keys only use 2 bytes.
 //
 // This structure is then repeated for each key an value slices.
 //
 // ┌────────────────────────────────────────────────────────────────────┐
 // │                           WriteWALEntry                            │
 // ├──────┬─────────┬────────┬───────┬─────────┬─────────┬───┬──────┬───┤
 // │ Type │ Key Len │   Key  │ Count │  Time   │  Value  │...│ Type │...│
 // │1 byte│ 2 bytes │ N bytes│4 bytes│ 8 bytes │ N bytes │   │1 byte│   │
 // └──────┴─────────┴────────┴───────┴─────────┴─────────┴───┴──────┴───┘
 
 未压缩之前的格式, 压缩采用snappy
 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 type(1 byte) | key len(2 bytes) | key(n bytes) | value count(4 bytes) | time(8 bytes) | value1(n bytes)|time(8 bytes)|value2
 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 type(1 byte) | key len(2 bytes) | key(n bytes) | value count(4 bytes) | time(8 bytes) | value(n bytes)|time(8 bytes)| value
 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 
 value:
 +++++++++++++++
 float 8 bytes(big endian)
 +++++++++++++++
 integer 8 bytes(big endian)
 +++++++++++++++
 unsigned 8 bytes(big endian)
 +++++++++++++++
 boolean 1 byte
 ++++++++++++++++++++++++++++++
 string  | len(4 bytes ) big| string_value(n bytes)
 +++++++++++++++
 
 实际格式：
 ++++++++++++++++++++++++++++++++++++
 type(1 byte) | len(4 bytes) | compressed content
 +++++++++++++++++++++++++++++++++++
~~~

