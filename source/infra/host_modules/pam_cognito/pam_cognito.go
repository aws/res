package main

/*
#cgo LDFLAGS: -lpam
#include <security/pam_modules.h>
#include <security/pam_ext.h>
*/
import "C"

import (
	util "host_modules/util"
	"unsafe"
)

func authenticate(ap util.AuthProvider, username *C.char, password *C.char) C.int {
	auth_retval, err := ap.AuthenticateUser(C.GoString(username), C.GoString(password))
	if auth_retval != true {
		util.Logf("cognito_auth", "Failed authentication: %s", err)
		return C.PAM_AUTH_ERR
	}

	return C.PAM_SUCCESS
}

//export smAuthenticate
func smAuthenticate(pamh *C.pam_handle_t, flags C.int, argc C.int, argv **C.char) C.int {
	config, err := util.ParseConfig()
	if err != nil {
		util.Logf("cognito_auth", "Unable to parse cognito-auth config: %s", err)
		return C.PAM_AUTH_ERR
	}

	var pUsername *C.char
	var pPassword *C.char

	retval := C.pam_get_user(pamh, &pUsername, (*C.char)(unsafe.Pointer(C.NULL)))
	if retval != C.PAM_SUCCESS {
		return C.PAM_AUTH_ERR
	}

	retval = C.pam_get_authtok(pamh, C.PAM_AUTHTOK, &pPassword, (*C.char)(unsafe.Pointer(C.NULL)))
	if retval != C.PAM_SUCCESS {
		return C.PAM_AUTH_ERR
	}

	ap := util.CognitoAuthProvider{config}
	return authenticate(ap, pUsername, pPassword)
}

func main() {}
