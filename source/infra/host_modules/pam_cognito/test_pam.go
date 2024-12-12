// Unfortunately Golang doesn't support testing of functions with CGO directly,
// so this is the implementation of testing functions that can be called by the
// Test file
package main

/*
#cgo LDFLAGS: -lpam
#include <security/pam_appl.h>
#include <security/pam_modules.h>
#include <security/pam_ext.h>
*/
import "C"
import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
)

type MockedAuthProvider struct {
	mock.Mock
}

func (m *MockedAuthProvider) AuthenticateUser(username string, password string) (bool, error) {
	args := m.Called(username, password)
	return (args.Get(0)).(bool), args.Error(1)
}

func testPamAuthenticate(t *testing.T) {

	username := "user1"
	valid := "valid"
	invalid := "invalid"

	mockIdp := new(MockedAuthProvider)
	mockIdp.On("AuthenticateUser", username, valid).Return(true, nil)
	mockIdp.On("AuthenticateUser", username, invalid).Return(false, nil)

	t.Run("Valid authentication returns true", func(t *testing.T) {
		status := authenticate(mockIdp, C.CString(username), C.CString(valid))
		assert.Equal(t, int(status), C.PAM_SUCCESS)
	})

	t.Run("Invalid authentication returns false", func(t *testing.T) {
		status := authenticate(mockIdp, C.CString(username), C.CString(invalid))
		assert.Equal(t, int(status), C.PAM_AUTH_ERR)
	})
}
