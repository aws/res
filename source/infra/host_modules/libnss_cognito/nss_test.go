package main

// Unfortunately Golang doesn't support testing of functions with CGO directly,
// so this is a wrapper that will call the corresponding functions
import (
	"testing"
)

func TestNssStoreUser(t *testing.T) {
	testNssStoreUser(t)
}

func TestNssStoreGroup(t *testing.T) {
	testNssStoreGroup(t)
}

func TestNssGetPwnam_c(t *testing.T) {
	testNssGetPwNam_c(t)
}

// Test the Golang version of the functions

func TestGetUserByName(t *testing.T) {
	testGetUserByName(t)
}

func TestGetUserByUid(t *testing.T) {
	testGetUserByUid(t)
}

func TestGetGroupByName(t *testing.T) {
	testGetGroupByName(t)
}

func TestGetGroupByGid(t *testing.T) {
	testGetGroupByGid(t)
}
