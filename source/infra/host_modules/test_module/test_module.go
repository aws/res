package main

import "C"
import "fmt"

//export Hello
func Hello() {
    fmt.Println("Hello from Go!")
}

func main() {}
