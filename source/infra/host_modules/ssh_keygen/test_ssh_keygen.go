package main

/*
#cgo LDFLAGS: -lpam
#include <security/pam_appl.h>
#include <security/pam_modules.h>
#include <security/pam_ext.h>
*/
import "C"
import (
	"bytes"
	"io"
	"os"
	"os/user"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
)

// Helper functions
func fileExists(filename string) bool {
	info, err := os.Stat(filename)
	return err == nil && !info.IsDir()
}

func filePerms(filename string) int32 {
	info, _ := os.Stat(filename)
	return int32(info.Mode().Perm() & 0777)
}

func filesEqual(file1, file2 string) (bool, error) {
	f1, err := os.Open(file1)
	if err != nil {
		return false, err
	}
	defer f1.Close()

	f2, err := os.Open(file2)
	if err != nil {
		return false, err
	}
	defer f2.Close()

	const chunkSize = 8 * 1024
	buf1 := make([]byte, chunkSize)
	buf2 := make([]byte, chunkSize)

	for {
		n1, err1 := f1.Read(buf1)
		n2, err2 := f2.Read(buf2)

		if err1 == io.EOF && err2 == io.EOF {
			return true, nil
		} else if err1 != nil || err2 != nil || n1 != n2 {
			return false, nil
		}

		if !bytes.Equal(buf1[:n1], buf2[:n2]) {
			return false, nil
		}
	}
}

func fileSize(filePath string) (int64, error) {
	fileInfo, err := os.Stat(filePath)
	if err != nil {
		return 0, err
	}
	return fileInfo.Size(), nil
}

// Test function
func testPamKeygen(t *testing.T) {
	t.Run("Creates keys and authorized_keys with correct permissions", func(t *testing.T) {
		sshDir, err := os.MkdirTemp("", "temp")
		assert.NoError(t, err)
		defer os.RemoveAll(sshDir)

		privPath := filepath.Join(sshDir, "id_rsa")
		pubPath := filepath.Join(sshDir, "id_rsa.pub")
		authorizedKeys := filepath.Join(sshDir, "authorized_keys")
		currentUser, err := user.Current()
		assert.NoError(t, err)

		status := doKeyGen(sshDir, currentUser)

		assert.Equal(t, int(C.PAM_SUCCESS), int(status))
		assert.True(t, fileExists(privPath))
		assert.True(t, fileExists(pubPath))
		assert.True(t, fileExists(authorizedKeys))

		assert.Equal(t, int32(0600), filePerms(privPath))
		assert.Equal(t, int32(0600), filePerms(pubPath))
		assert.Equal(t, int32(0600), filePerms(authorizedKeys))

		filesAreEqual, err := filesEqual(pubPath, authorizedKeys)
		assert.NoError(t, err)
		assert.True(t, filesAreEqual)
	})

	t.Run("Does not run if private key exists", func(t *testing.T) {
		sshDir, err := os.MkdirTemp("", "temp")
		assert.NoError(t, err)
		defer os.RemoveAll(sshDir)

		privPath := filepath.Join(sshDir, "id_rsa")
		currentUser, err := user.Current()
		assert.NoError(t, err)

		// Create an empty private key file
		f, err := os.OpenFile(privPath, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0666)
		assert.NoError(t, err)
		f.Close()

		status := doKeyGen(sshDir, currentUser)

		privSize, err := fileSize(privPath)
		assert.NoError(t, err)

		assert.Equal(t, int(C.PAM_AUTH_ERR), int(status))
		assert.True(t, fileExists(privPath))
		assert.Equal(t, int64(0), privSize)
		assert.False(t, fileExists(filepath.Join(sshDir, "id_rsa.pub")))
		assert.False(t, fileExists(filepath.Join(sshDir, "authorized_keys")))
	})

	t.Run("Does not run if public key exists", func(t *testing.T) {
		sshDir, err := os.MkdirTemp("", "temp")
		assert.NoError(t, err)
		defer os.RemoveAll(sshDir)

		pubPath := filepath.Join(sshDir, "id_rsa.pub")
		currentUser, err := user.Current()
		assert.NoError(t, err)

		// Create an empty public key file
		f, err := os.OpenFile(pubPath, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0666)
		assert.NoError(t, err)
		f.Close()

		status := doKeyGen(sshDir, currentUser)

		pubSize, err := fileSize(pubPath)
		assert.NoError(t, err)

		assert.Equal(t, int(C.PAM_AUTH_ERR), int(status))
		assert.False(t, fileExists(filepath.Join(sshDir, "id_rsa")))
		assert.True(t, fileExists(pubPath))
		assert.Equal(t, int64(0), pubSize)
		assert.False(t, fileExists(filepath.Join(sshDir, "authorized_keys")))
	})

	t.Run("Does not run if authorized_keys exists", func(t *testing.T) {
		sshDir, err := os.MkdirTemp("", "temp")
		assert.NoError(t, err)
		defer os.RemoveAll(sshDir)

		authorizedKeys := filepath.Join(sshDir, "authorized_keys")
		currentUser, err := user.Current()
		assert.NoError(t, err)

		// Create an empty authorized_keys file
		f, err := os.OpenFile(authorizedKeys, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0666)
		assert.NoError(t, err)
		f.Close()

		status := doKeyGen(sshDir, currentUser)

		authKeysSize, err := fileSize(authorizedKeys)
		assert.NoError(t, err)

		assert.Equal(t, int(C.PAM_AUTH_ERR), int(status))
		assert.True(t, fileExists(filepath.Join(sshDir, "id_rsa")))
		assert.True(t, fileExists(filepath.Join(sshDir, "id_rsa.pub")))
		assert.True(t, fileExists(authorizedKeys))
		assert.Equal(t, int64(0), authKeysSize)
	})
}
