package main

/*
#cgo LDFLAGS: -lnss3 -lnssutil3
#include <pwd.h>
#include <grp.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <nss.h>

inline char* strcpy_idx(char *buf, char* src, unsigned long *offset){
	int start_offset = *offset;
	for(int i = 0; i < strlen(src) + 1; i++)
		buf[i + *offset] = src[i];
	*offset += strlen(src) + 1;
	return &buf[start_offset];
}
*/
import "C"
import (
	util "host_modules/util"
	"fmt"
)

// storeUser: Internal function that takes the properties of the user and
// populates the C.struct_passwd result parameter with the values. Each of the
// strings must be packed into the provided buf and ensure that we do not
// exceed bufflen.
func storeUser(result *C.struct_passwd, buf *C.char, bufflen C.size_t, errnop *C.int,
	name string, uid uint64, gid uint64, gecos string, home string, shell string) C.enum_nss_status {
	idx := C.ulong(0)

	if result == (*C.struct_passwd)(C.NULL) || buf == (*C.char)(C.NULL) || errnop == (*C.int)(C.NULL) {
		*errnop = C.EFAULT
		return C.NSS_STATUS_NOTFOUND
	}

	if idx+C.ulong(len(name)) >= bufflen {
		*errnop = C.ERANGE
		return C.NSS_STATUS_NOTFOUND
	}
	(*result).pw_name = C.strcpy_idx(buf, C.CString(name), &idx)

	if idx+C.ulong(len("x")) >= bufflen {
		*errnop = C.ERANGE
		return C.NSS_STATUS_NOTFOUND
	}
	(*result).pw_passwd = C.strcpy_idx(buf, C.CString("x"), &idx)
	(*result).pw_uid = C.uid_t(uid)
	(*result).pw_gid = C.gid_t(gid)

	if idx+C.ulong(len(gecos)) >= bufflen {
		*errnop = C.ERANGE
		return C.NSS_STATUS_NOTFOUND
	}
	(*result).pw_gecos = C.strcpy_idx(buf, C.CString(gecos), &idx)

	if idx+C.ulong(len(home)) >= bufflen {
		*errnop = C.ERANGE
		return C.NSS_STATUS_NOTFOUND
	}
	(*result).pw_dir = C.strcpy_idx(buf, C.CString(home), &idx)

	if idx+C.ulong(len(shell)) >= bufflen {
		*errnop = C.ERANGE
		return C.NSS_STATUS_NOTFOUND
	}
	(*result).pw_shell = C.strcpy_idx(buf, C.CString(shell), &idx)

	return C.NSS_STATUS_SUCCESS
}

// storeGroup: Internal function that takes the properties of the group and
// populates the C.struct_group result parameter with the values. Each of the
// strings must be packed into the provided buf and ensure that we do not
// exceed bufflen.
func storeGroup(result *C.struct_group, buf *C.char, bufflen C.size_t, errnop *C.int,
	name string, gid uint64) C.enum_nss_status {
	idx := C.ulong(0)

	if result == (*C.struct_group)(C.NULL) || buf == (*C.char)(C.NULL) || errnop == (*C.int)(C.NULL) {
		*errnop = C.EFAULT
		return C.NSS_STATUS_NOTFOUND
	}

	if idx+C.ulong(len(name)) >= bufflen {
		*errnop = C.ERANGE
		return C.NSS_STATUS_NOTFOUND
	}
	(*result).gr_name = C.strcpy_idx(buf, C.CString(name), &idx)

	if idx+C.ulong(len("x")) >= bufflen {
		*errnop = C.ERANGE
		return C.NSS_STATUS_NOTFOUND
	}
	(*result).gr_passwd = C.strcpy_idx(buf, C.CString("x"), &idx)
	(*result).gr_gid = C.gid_t(gid)

	return C.NSS_STATUS_SUCCESS
}

// go functions for the NSS interface that use an identity provider to resolve users, groups
// and user ids

func getUserByName(idp util.IdentityProvider, cache NssCacheProvider, name *C.char, result *C.struct_passwd, buf *C.char,
	bufflen C.size_t, errnop *C.int) C.enum_nss_status {

	user, groups, user_cached := cache.GetUserByName(C.GoString(name))

	groups_cached := groups != nil

	if !user_cached {
		var err error
		user, err = idp.GetUser(C.GoString(name))
		if err != nil {
			util.Logf("cognito_auth", "Unable to retrieve Cognito user: %s", err)
			return C.NSS_STATUS_NOTFOUND
		}
	}

	if !groups_cached {
		var err error
		groups, err = idp.GetUserGroups(user)
		if err != nil {
			util.Logf("cognito_auth", "Unable to retrieve Cognito groups: %s", err)
			return C.NSS_STATUS_NOTFOUND
		}
	}

	if !user_cached || !groups_cached {
		group_names := []string{}
		for _, group := range groups {
			group_names = append(group_names, group.Name)
		}
		cache.UpdateUser(user, group_names)
		cache.AddGroups(groups)
	}

	home := fmt.Sprintf("/home/%s", user.Name)
	return storeUser(result, buf, bufflen, errnop, user.Name, user.Uid, groups[0].Gid, "", home, "/bin/bash")
}

func getUserByUid(idp util.IdentityProvider, cache NssCacheProvider, uid C.uid_t, result *C.struct_passwd, buf *C.char, bufflen C.size_t, errnop *C.int) C.enum_nss_status {

	user, groups, user_cached := cache.GetUserByUid(uint64(uid))

	groups_cached := groups != nil
	found_user := user_cached

	// If we can't find the user in the cache, scan for them in cognito
	if !user_cached {
		found_user = false

		users, err := idp.GetAllUsers()
		if err != nil {
			util.Logf("cognito_auth", "Unable to retrieve Cognito users: %s", err)
			return C.NSS_STATUS_NOTFOUND
		}

		// Update the cache with the found users
		cache.AddUsers(users)

		for _, user = range users {
			if uint64(uid) == user.Uid {
				found_user = true
				break
			}
		}

	}

	// if we didn't find the user in scanned users bail
	if !found_user {
		return C.NSS_STATUS_NOTFOUND
	}

	// If we don't have the groups from the cache, retrieve them now and store
	// them in the cache.
	if !groups_cached {
		var err error
		groups, err = idp.GetUserGroups(user)
		if err != nil {
			util.Logf("cognito_auth", "Unable to retrieve Cognito groups: %s", err)
			return C.NSS_STATUS_NOTFOUND
		}
		cache.AddGroups(groups)
	}

	// Update the user in the cache with the group membership if that is new
	// information
	if !user_cached || !groups_cached {
		// Update user in cache with their respective groups
		group_names := []string{}
		for _, group := range groups {
			group_names = append(group_names, group.Name)
		}
		cache.UpdateUser(user, group_names)
	}

	home := fmt.Sprintf("/home/%s", user.Name)
	return storeUser(result, buf, bufflen, errnop, user.Name, user.Uid, groups[0].Gid, "", home, "/bin/bash")

}

func getGroupByName(idp util.IdentityProvider, cache NssCacheProvider, name *C.char, result *C.struct_group, buf *C.char, bufflen C.size_t, errnop *C.int) C.enum_nss_status {

	group, group_cached := cache.GetGroupByName(C.GoString(name))

	if group_cached {
		return storeGroup(result, buf, bufflen, errnop, group.Name, group.Gid)
	} else {
		groups, err := idp.GetAllGroups()
		if err != nil {
			util.Logf("cognito_auth", "Unable to retrieve Cognito groups: %s", err)
			return C.NSS_STATUS_NOTFOUND
		}
		cache.AddGroups(groups)

		for _, group := range groups {
			if C.GoString(name) == group.Name {
				return storeGroup(result, buf, bufflen, errnop, group.Name, group.Gid)
			}
		}
	}

	return C.NSS_STATUS_NOTFOUND
}

func getGroupByGid(idp util.IdentityProvider, cache NssCacheProvider, gid C.gid_t, result *C.struct_group, buf *C.char, bufflen C.size_t, errnop *C.int) C.enum_nss_status {

	group, group_cached := cache.GetGroupByGid(uint64(gid))

	if group_cached {
		return storeGroup(result, buf, bufflen, errnop, group.Name, group.Gid)
	} else {
		groups, err := idp.GetAllGroups()
		if err != nil {
			util.Logf("cognito_auth", "Error retrieving groups: %s", err)
			return C.NSS_STATUS_NOTFOUND
		}
		cache.AddGroups(groups)

		for _, group := range groups {
			if uint64(gid) == group.Gid {
				return storeGroup(result, buf, bufflen, errnop, group.Name, group.Gid)
			}
		}
	}

	return C.NSS_STATUS_NOTFOUND
}

//wrapper functions from the C calling interface into the Go functions defined
//above. This separation is so that the functions can be tested and accept
//interface(s) that can be mocked.

//export _nss_cognito_getpwnam_r
func _nss_cognito_getpwnam_r(name *C.char, result *C.struct_passwd, buf *C.char,
	bufflen C.size_t, errnop *C.int) C.enum_nss_status {

	config, err := util.ParseConfig()
	if err != nil {
		util.Logf("cognito_auth", "Unable to parse config: %s", err)
		return C.NSS_STATUS_NOTFOUND
	}
	idp := util.CognitoIdentityProvider{config}
	cache := DefaultCacheProvider(config)

	return getUserByName(idp, cache, name, result, buf, bufflen, errnop)

}

//export _nss_cognito_getpwuid_r
func _nss_cognito_getpwuid_r(uid C.uid_t, result *C.struct_passwd, buf *C.char, bufflen C.size_t, errnop *C.int) C.enum_nss_status {
	if uid == 0 {
		return C.NSS_STATUS_NOTFOUND
	}

	config, err := util.ParseConfig()
	if err != nil {
		util.Logf("cognito_auth", "Unable to parse config: %s", err)
		return C.NSS_STATUS_NOTFOUND
	}
	idp := util.CognitoIdentityProvider{config}
	cache := DefaultCacheProvider(config)

	return getUserByUid(idp, cache, uid, result, buf, bufflen, errnop)
}

//export _nss_cognito_getgrgid_r
func _nss_cognito_getgrgid_r(gid C.gid_t, result *C.struct_group, buf *C.char, bufflen C.size_t, errnop *C.int) C.enum_nss_status {

	config, err := util.ParseConfig()
	if err != nil {
		util.Logf("cognito_auth", "Unable to parse config: %s", err)
		return C.NSS_STATUS_NOTFOUND
	}
	idp := util.CognitoIdentityProvider{config}
	cache := DefaultCacheProvider(config)

	return getGroupByGid(idp, cache, gid, result, buf, bufflen, errnop)
}

//export _nss_cognito_getgrnam_r
func _nss_cognito_getgrnam_r(name *C.char, result *C.struct_group, buf *C.char, bufflen C.size_t, errnop *C.int) C.enum_nss_status {

	config, err := util.ParseConfig()
	if err != nil {
		util.Logf("cognito_auth", "Unable to parse config: %s", err)
		return C.NSS_STATUS_NOTFOUND
	}
	idp := util.CognitoIdentityProvider{config}
	cache := DefaultCacheProvider(config)

	return getGroupByName(idp, cache, name, result, buf, bufflen, errnop)
}

func main() {}
