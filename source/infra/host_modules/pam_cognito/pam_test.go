package main

// Unfortunately Golang doesn't support testing of functions with CGO directly,
// so this is a wrapper that will call the corresponding functions
import (
	"testing"
)

func TestPamAuthenticate(t *testing.T) {
	testPamAuthenticate(t)
}
