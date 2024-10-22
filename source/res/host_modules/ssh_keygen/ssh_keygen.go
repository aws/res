package main

/*
#cgo LDFLAGS: -lpam
#include <security/pam_modules.h>
#include <security/pam_ext.h>
*/
import "C"

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"encoding/pem"
	"errors"
	"io"
	"os"
	"os/user"
	util "host_modules/utils"
	"path/filepath"
	"strconv"
	"syscall"
	"unsafe"

	"golang.org/x/crypto/ssh"
)

func writeAuthorizedKeys(user *user.User, sshDir string, pubPath string) error {
	authKeysPath := filepath.Join(sshDir, "authorized_keys")
	uid, err := strconv.Atoi(user.Uid)
	gid, err := strconv.Atoi(user.Gid)
	perm := os.FileMode(0600)

    // Check if the authorized_keys file already exists
	if _, err := os.Stat(authKeysPath); err == nil {
		return errors.New("destination file already exists")
	} else if !os.IsNotExist(err) {
		return err
	}

	// If it doesn't exist then simply add the public key we've created to it
	in, err := os.Open(pubPath)
	if err != nil {
		return err
	}
	defer in.Close()

    // Create the authorized_keys file
	out, err := os.Create(authKeysPath)
	if err != nil {
		return err
	}
	defer out.Close()

	defer syscall.Chmod(authKeysPath, uint32(perm))
	defer os.Chown(authKeysPath, uid, gid)

    // Copy the public key to authorized_keys
	if _, err = io.Copy(out, in); err != nil {
		return err
	}
	return nil
}

func generateSshKeys(user *user.User, sshDir string, privPath string, pubPath string) error {
	perm := os.FileMode(0600)
	uid, err := strconv.Atoi(user.Uid)
	gid, err := strconv.Atoi(user.Gid)

	privateKey, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		panic(err)
	}

	// Save the private key in PEM format
	privateKeyFile, err := os.Create(privPath)
	if err != nil {
		return err
	}
	defer privateKeyFile.Close()
	defer syscall.Chmod(privPath, uint32(perm))
	defer os.Chown(privPath, uid, gid)

	privateKeyPEM := &pem.Block{
		Type:  "RSA PRIVATE KEY",
		Bytes: x509.MarshalPKCS1PrivateKey(privateKey),
	}
	if err := pem.Encode(privateKeyFile, privateKeyPEM); err != nil {
		return err
	}

	// Generate the public key in OpenSSH format
	pub, err := ssh.NewPublicKey(&privateKey.PublicKey)
	if err != nil {
		return err
	}

	// Save the public key
	publicKeyFile, err := os.Create(pubPath)
	if err != nil {
		return err
	}
	defer publicKeyFile.Close()
	defer syscall.Chmod(pubPath, uint32(perm))
	defer os.Chown(pubPath, uid, gid)

	if _, err = publicKeyFile.Write(ssh.MarshalAuthorizedKey(pub)); err != nil {
		return err
	}
	return nil
}

func doKeyGen(sshDir string, user *user.User) C.int {
	uid, err := strconv.Atoi(user.Uid)
	if err != nil {
        return C.PAM_AUTH_ERR // or handle the error as appropriate
    }
	gid, err := strconv.Atoi(user.Gid)
	if err != nil {
        return C.PAM_AUTH_ERR
    }
	// Ensure the .ssh directory exists
	if err := os.MkdirAll(sshDir, 0700); err != nil && !os.IsExist(err) {
		util.Logf("ssh_keygen", "error creating directory: %v", err)
		return C.PAM_AUTH_ERR
	}

	if err := os.Chown(sshDir, uid, gid); err != nil {
		util.Logf("ssh_keygen", "error changing ownership of directory: %v", err)
		return C.PAM_AUTH_ERR
	}

	// Paths to the private and public SSH keys
	privPath := filepath.Join(sshDir, "id_rsa")
	pubPath := filepath.Join(sshDir, "id_rsa.pub")

	// Generate SSH keys if they do not exist
	if _, err1 := os.Stat(privPath); os.IsNotExist(err1) {
		if _, err2 := os.Stat(pubPath); os.IsNotExist(err2) {
			if err := generateSshKeys(user, sshDir, privPath, pubPath); err != nil {
				return C.PAM_AUTH_ERR
			}
			if err := writeAuthorizedKeys(user, sshDir, pubPath); err != nil {
				return C.PAM_AUTH_ERR
			}
			return C.PAM_SUCCESS
		}
	}
	return C.PAM_AUTH_ERR
}

//export smOpenSession
func smOpenSession(pamh *C.pam_handle_t, flags C.int, argc C.int, argv **C.char) C.int {
	// Get the username from PAM
	var pUsername *C.char
	if retval := C.pam_get_user(pamh, &pUsername, (*C.char)(unsafe.Pointer(C.NULL))); retval != C.PAM_SUCCESS {
		return C.PAM_AUTH_ERR
	}

	// Lookup the user from the OS
	user, err := user.Lookup(C.GoString(pUsername))
	if err != nil {
		return C.PAM_AUTH_ERR
	}
    // Generate SSH keys and set up authorized_keys
	sshDir := filepath.Join(user.HomeDir, ".ssh")
	return doKeyGen(sshDir, user)
}

func main() {}
