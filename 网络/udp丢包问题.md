# udp 丢包问题





~~~go
package main

import (
    "fmt"
    "net"
    "time"
)

func main() {
    c, err := net.ListenUDP("udp", &net.UDPAddr{IP: net.ParseIP("0.0.0.0"), Port: 50000})
    if err != nil {
        panic(err)
    }

    ch := make(chan []byte, 1)
    go processPacket(ch)
    c.SetReadBuffer(1024 * 1024 * 16)
    for {
        data := make([]byte, 4096)
        n, _, err := c.ReadFrom(data)
        if err != nil {
            panic(err)
        }
        ch <- data[:n]
        fmt.Printf("read %d bytes %s\n", n, time.Now())
    }

}

func processPacket(chIn <-chan []byte) {
    for {
        data := <-chIn
        fmt.Printf("%d\n", len(data))
        time.Sleep(time.Millisecond * 100)
    }
}
~~~

