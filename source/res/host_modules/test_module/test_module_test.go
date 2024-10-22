package main

import (
    "testing"
    "bytes"
    "os"
)

func TestHello(t *testing.T) {
    // Capture the output of the Hello function
    old := os.Stdout
    r, w, _ := os.Pipe()
    os.Stdout = w

    Hello()

    w.Close()
    os.Stdout = old

    var buf bytes.Buffer
    buf.ReadFrom(r)
    output := buf.String()

    expected := "Hello from Go!\n"
    if output != expected {
        t.Errorf("Expected %q but got %q", expected, output)
    }
}
