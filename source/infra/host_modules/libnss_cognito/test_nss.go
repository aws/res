// Unfortunately Golang doesn't support testing of functions with CGO directly,
// so this is the implementation of testing functions that can be called by the
// Test file
package main

/*
#include <stdlib.h>
#include <pwd.h>
#include <grp.h>
#include <errno.h>
#include <nss.h>
*/
import "C"
import (
	util "host_modules/util"
	"fmt"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
)

// MockIdentityProvider used for testing

type MockedIdentityProvider struct {
	mock.Mock
}

func (m *MockedIdentityProvider) GetUser(username string) (util.User, error) {
	args := m.Called(username)
	return (args.Get(0)).(util.User), args.Error(1)
}

func (m *MockedIdentityProvider) GetAllUsers() ([]util.User, error) {
	args := m.Called()
	return (args.Get(0)).([]util.User), args.Error(1)
}

func (m *MockedIdentityProvider) GetUserGroups(user util.User) ([]util.Group, error) {
	args := m.Called(user)
	return (args.Get(0)).([]util.Group), args.Error(1)
}

func (m *MockedIdentityProvider) GetAllGroups() ([]util.Group, error) {
	args := m.Called()
	return (args.Get(0)).([]util.Group), args.Error(1)
}

// MockCacheProvider used for testing

type MockedCacheProvider struct {
	mock.Mock
}

func (m MockedCacheProvider) GetUserByName(name string) (util.User, []util.Group, bool) {
	_ = m.Called(name)
	return util.User{}, nil, false
}

func (m MockedCacheProvider) GetUserByUid(uid uint64) (util.User, []util.Group, bool) {
	_ = m.Called(uid)
	return util.User{}, nil, false
}

func (m MockedCacheProvider) GetGroupByName(name string) (util.Group, bool) {
	_ = m.Called(name)
	return util.Group{}, false
}

func (m MockedCacheProvider) GetGroupByGid(gid uint64) (util.Group, bool) {
	_ = m.Called(gid)
	return util.Group{}, false
}

func (m MockedCacheProvider) UpdateUser(user util.User, groups []string) error {
	_ = m.Called(user, groups)
	return nil
}

func (m MockedCacheProvider) AddUsers(users []util.User) error {
	_ = m.Called(users)
	return nil
}

func (m MockedCacheProvider) AddGroups(groups []util.Group) error {
	_ = m.Called(groups)
	return nil
}

func (m MockedCacheProvider) LoadCache() error {
	return nil
}

func (m MockedCacheProvider) SaveCache() error {
	return nil
}

func mockCache() MockedCacheProvider {
	mockedCache := MockedCacheProvider{}
	mockedCache.On("GetUserByName", mock.AnythingOfType("string")).Return(util.User{}, nil, false)
	mockedCache.On("GetUserByUid", mock.AnythingOfType("uint64")).Return(util.User{}, nil, false)
	mockedCache.On("GetGroupByName", mock.AnythingOfType("string")).Return(util.Group{}, false)
	mockedCache.On("GetGroupByGid", mock.AnythingOfType("uint64")).Return(util.Group{}, false)

	mockedCache.On("UpdateUser", mock.AnythingOfType("util.User"), mock.AnythingOfType("[]string")).Return(nil)
	mockedCache.On("AddUsers", mock.AnythingOfType("[]util.User")).Return(nil)
	mockedCache.On("AddGroups", mock.AnythingOfType("[]util.Group")).Return(nil)
	return mockedCache
}

// Test the store user function that populates a C.struct_password with the
// values provided as parameters.
func testNssStoreUser(t *testing.T) {
	// Allocate memory
	struct_ptr_ := C.malloc(C.sizeof_struct_passwd)
	defer C.free(struct_ptr_)
	struct_ptr := (*C.struct_passwd)(struct_ptr_)

	buf_size := C.ulong(1024)
	buf_ptr_ := C.malloc(C.ulong(buf_size))
	defer C.free(buf_ptr_)
	buf_ptr := (*C.char)(buf_ptr_)

	// Parameters that will be stored
	errnop := C.int(0)
	username := "name"
	uid := uint64(64)
	gid := uint64(128)
	gecos := "gecos"
	home := "/home/name"
	shell := "/bin/bash"

	// Call the func
	status := storeUser(struct_ptr, buf_ptr, C.ulong(buf_size), &errnop, username, uid, gid, gecos, home, shell)

	// Validate storage
	if status != C.NSS_STATUS_SUCCESS {
		t.Errorf("storeUser gave invalid status: %d, expected: %d.", status, C.NSS_STATUS_SUCCESS)
	}

	if errnop != 0 {
		t.Errorf("storeUser should not have stored errnop: %d.", errnop)
	}

	if C.GoString(struct_ptr.pw_name) != username {
		t.Errorf("storeUser failed to store username: %s, expected: %s.", C.GoString(struct_ptr.pw_name), username)
	}

	if C.GoString(struct_ptr.pw_passwd) != "x" {
		t.Errorf("storeUser failed to store passwd: %s, expected: %s.", C.GoString(struct_ptr.pw_passwd), "x")
	}

	if (*struct_ptr).pw_uid != C.uint(uid) {
		t.Errorf("storeUser failed to store uid: %d, expected: %d.", struct_ptr.pw_uid, uid)
	}

	if (*struct_ptr).pw_gid != C.uint(gid) {
		t.Errorf("storeUser failed to store gid: %d, expected: %d.", struct_ptr.pw_gid, gid)
	}

	if C.GoString(struct_ptr.pw_gecos) != gecos {
		t.Errorf("storeUser failed to store gecos: %s, expected: %s.", C.GoString(struct_ptr.pw_gecos), gecos)
	}

	if C.GoString(struct_ptr.pw_dir) != home {
		t.Errorf("storeUser failed to store home: %s, expected: %s.", C.GoString(struct_ptr.pw_dir), home)
	}

	if C.GoString(struct_ptr.pw_shell) != shell {
		t.Errorf("storeUser failed to store shell: %s, expected: %s.", C.GoString(struct_ptr.pw_shell), shell)
	}

	status = storeUser(struct_ptr, buf_ptr, C.ulong(4), &errnop, username, uid, gid, gecos, home, shell)

	if status == C.NSS_STATUS_SUCCESS {
		t.Errorf("storeUser gave invalid status: %d, expected: %d.", status, C.NSS_STATUS_NOTFOUND)
	}

	if errnop != C.ERANGE {
		t.Errorf("storeUser should have stored errnop as ERANGE: %d.", errnop)
	}
}

func testNssStoreGroup(t *testing.T) {
	// Allocate memory
	struct_ptr_ := C.malloc(C.sizeof_struct_group)
	defer C.free(struct_ptr_)
	struct_ptr := (*C.struct_group)(struct_ptr_)

	buf_size := C.ulong(1024)
	buf_ptr_ := C.malloc(C.ulong(buf_size))
	defer C.free(buf_ptr_)
	buf_ptr := (*C.char)(buf_ptr_)

	// Parameters that will be stored
	errnop := C.int(0)
	groupname := "name"
	gid := uint64(128)

	// Call the func
	status := storeGroup(struct_ptr, buf_ptr, buf_size, &errnop, groupname, gid)

	// Validate storage
	if status != C.NSS_STATUS_SUCCESS {
		t.Errorf("storeGroup gave invalid status: %d, expected: %d.", status, C.NSS_STATUS_SUCCESS)
	}

	if errnop != 0 {
		t.Errorf("storeGroup should not have stored errnop: %d.", errnop)
	}

	if C.GoString(struct_ptr.gr_name) != groupname {
		t.Errorf("storeGroup failed to store groupname: %s, expected: %s.", C.GoString(struct_ptr.gr_name), groupname)
	}

	if C.GoString(struct_ptr.gr_passwd) != "x" {
		t.Errorf("storeGroup failed to store passwd: %s, expected: %s.", C.GoString(struct_ptr.gr_passwd), "x")
	}

	if (*struct_ptr).gr_gid != C.uint(gid) {
		t.Errorf("storeGroup failed to store gid: %d, expected: %d.", struct_ptr.gr_gid, gid)
	}

	status = storeGroup(struct_ptr, buf_ptr, C.ulong(4), &errnop, groupname, gid)

	if status == C.NSS_STATUS_SUCCESS {
		t.Errorf("storeGroup gave invalid status: %d, expected: %d.", status, C.NSS_STATUS_NOTFOUND)
	}

	if errnop != C.ERANGE {
		t.Errorf("storeGroup should have stored errnop as ERANGE: %d.", errnop)
	}
}

// Test that the C version returns successfully when we don't have a valid
// config (by default)
func testNssGetPwNam_c(t *testing.T) {
	// Allocate memory
	struct_ptr_ := C.malloc(C.sizeof_struct_passwd)
	defer C.free(struct_ptr_)
	struct_ptr := (*C.struct_passwd)(struct_ptr_)

	buf_size := C.ulong(1024)
	buf_ptr_ := C.malloc(C.ulong(buf_size))
	defer C.free(buf_ptr_)
	buf_ptr := (*C.char)(buf_ptr_)

	// Parameters that will be stored
	errnop := C.int(0)

	status := _nss_cognito_getpwnam_r(C.CString("user1"), struct_ptr, buf_ptr, buf_size, &errnop)

	if status != C.NSS_STATUS_NOTFOUND {
		t.Errorf("getpwnam_r gave invalid status: %d, expected: %d.", status, C.NSS_STATUS_NOTFOUND)
	}
}

// Test the Golang version of the functions

func testGetUserByName(t *testing.T) {
	// Allocate memory
	struct_ptr_ := C.malloc(C.sizeof_struct_passwd)
	defer C.free(struct_ptr_)
	struct_ptr := (*C.struct_passwd)(struct_ptr_)

	buf_size := C.ulong(1024)
	buf_ptr_ := C.malloc(C.ulong(buf_size))
	defer C.free(buf_ptr_)
	buf_ptr := (*C.char)(buf_ptr_)

	// Parameters that will be stored
	errnop := C.int(0)

	username := "user1"

	t.Run("GetUserByName should find users", func(t *testing.T) {
		mockIdp := new(MockedIdentityProvider)
		mockIdp.On("GetUser", username).Return(util.User{Name: username, Uid: 1001}, nil)
		mockIdp.On("GetUserGroups", mock.AnythingOfType("util.User")).Return([]util.Group{{Name: "group1", Gid: 1002}}, nil)

		mockedCache := mockCache()

		status := getUserByName(mockIdp, mockedCache, C.CString(username), struct_ptr, buf_ptr, buf_size, &errnop)
		assert.Equal(t, int(status), C.NSS_STATUS_SUCCESS)
		assert.Equal(t, C.GoString(struct_ptr.pw_name), username)
		assert.Equal(t, int(struct_ptr.pw_uid), 1001)
	})

	t.Run("GetUserByName should give STATUS_NOTFOUND when it cant find user", func(t *testing.T) {
		mockIdp := new(MockedIdentityProvider)
		mockIdp.On("GetUser", username).Return(util.User{}, fmt.Errorf("Not found."))

		mockedCache := mockCache()

		status := getUserByName(mockIdp, mockedCache, C.CString(username), struct_ptr, buf_ptr, buf_size, &errnop)
		assert.Equal(t, int(status), C.NSS_STATUS_NOTFOUND)
	})

}

func testGetUserByUid(t *testing.T) {
	// Allocate memory
	struct_ptr_ := C.malloc(C.sizeof_struct_passwd)
	defer C.free(struct_ptr_)
	struct_ptr := (*C.struct_passwd)(struct_ptr_)

	buf_size := C.ulong(1024)
	buf_ptr_ := C.malloc(C.ulong(buf_size))
	defer C.free(buf_ptr_)
	buf_ptr := (*C.char)(buf_ptr_)

	// Parameters that will be stored
	errnop := C.int(0)

	username := "user1"
	uid := uint64(1001)

	t.Run("GetUserByUid should find users", func(t *testing.T) {
		mockIdp := new(MockedIdentityProvider)
		mockIdp.On("GetAllUsers").Return([]util.User{{Name: username, Uid: uid}}, nil)
		mockIdp.On("GetUserGroups", mock.AnythingOfType("util.User")).Return([]util.Group{{Name: "group1", Gid: 1002}}, nil)

		mockedCache := mockCache()

		status := getUserByUid(mockIdp, mockedCache, C.uint(uid), struct_ptr, buf_ptr, buf_size, &errnop)
		assert.Equal(t, int(status), C.NSS_STATUS_SUCCESS)
		assert.Equal(t, C.GoString(struct_ptr.pw_name), username)
		assert.Equal(t, uint64(struct_ptr.pw_uid), uid)
	})

	t.Run("GetUserByUid should give STATUS_NOTFOUND when it cant find user", func(t *testing.T) {
		mockIdp := new(MockedIdentityProvider)
		mockIdp.On("GetAllUsers").Return([]util.User{}, nil)

		mockedCache := mockCache()

		status := getUserByUid(mockIdp, mockedCache, C.uint(uid), struct_ptr, buf_ptr, buf_size, &errnop)
		assert.Equal(t, int(status), C.NSS_STATUS_NOTFOUND)
	})

}

func testGetGroupByName(t *testing.T) {
	// Allocate memory
	struct_ptr_ := C.malloc(C.sizeof_struct_group)
	defer C.free(struct_ptr_)
	struct_ptr := (*C.struct_group)(struct_ptr_)

	buf_size := C.ulong(1024)
	buf_ptr_ := C.malloc(C.ulong(buf_size))
	defer C.free(buf_ptr_)
	buf_ptr := (*C.char)(buf_ptr_)

	// Parameters that will be stored
	errnop := C.int(0)

	groupname := "group1"
	gid := uint64(1002)

	t.Run("GetGroupByName should find users", func(t *testing.T) {
		mockIdp := new(MockedIdentityProvider)
		mockIdp.On("GetAllGroups").Return([]util.Group{{Name: "group1", Gid: 1002}}, nil)

		mockedCache := mockCache()

		status := getGroupByName(mockIdp, mockedCache, C.CString(groupname), struct_ptr, buf_ptr, buf_size, &errnop)
		assert.Equal(t, int(status), C.NSS_STATUS_SUCCESS)
		assert.Equal(t, C.GoString(struct_ptr.gr_name), groupname)
		assert.Equal(t, uint64(struct_ptr.gr_gid), gid)
	})

	t.Run("GetGroupByName should give STATUS_NOTFOUND when it cant find group", func(t *testing.T) {
		mockIdp := new(MockedIdentityProvider)
		mockIdp.On("GetAllGroups").Return([]util.Group{}, nil)

		mockedCache := mockCache()

		status := getGroupByName(mockIdp, mockedCache, C.CString(groupname), struct_ptr, buf_ptr, buf_size, &errnop)
		assert.Equal(t, int(status), C.NSS_STATUS_NOTFOUND)
	})

}

func testGetGroupByGid(t *testing.T) {
	// Allocate memory
	struct_ptr_ := C.malloc(C.sizeof_struct_group)
	defer C.free(struct_ptr_)
	struct_ptr := (*C.struct_group)(struct_ptr_)

	buf_size := C.ulong(1024)
	buf_ptr_ := C.malloc(C.ulong(buf_size))
	defer C.free(buf_ptr_)
	buf_ptr := (*C.char)(buf_ptr_)

	// Parameters that will be stored
	errnop := C.int(0)

	groupname := "group1"
	gid := uint64(1002)

	t.Run("GetGroupByGid should find users", func(t *testing.T) {
		mockIdp := new(MockedIdentityProvider)
		mockIdp.On("GetAllGroups").Return([]util.Group{{Name: "group1", Gid: 1002}}, nil)

		mockedCache := mockCache()

		status := getGroupByGid(mockIdp, mockedCache, C.uint(gid), struct_ptr, buf_ptr, buf_size, &errnop)
		assert.Equal(t, int(status), C.NSS_STATUS_SUCCESS)
		assert.Equal(t, C.GoString(struct_ptr.gr_name), groupname)
		assert.Equal(t, uint64(struct_ptr.gr_gid), gid)
	})

	t.Run("GetGetGroupByGid should give STATUS_NOTFOUND when it cant find group", func(t *testing.T) {
		mockIdp := new(MockedIdentityProvider)
		mockIdp.On("GetAllGroups").Return([]util.Group{}, nil)

		mockedCache := mockCache()

		status := getGroupByGid(mockIdp, mockedCache, C.uint(gid), struct_ptr, buf_ptr, buf_size, &errnop)
		assert.Equal(t, int(status), C.NSS_STATUS_NOTFOUND)
	})

}
