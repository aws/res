package main

import (
	. "host_modules/util"
	util "host_modules/util"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"strconv"
	"syscall"
	"time"
)

/*
Cache will have the following format
{
    "userID": {
        "<uid>": {
            "username": <username>,
            "groups": [<group1>, <group2>],
            "lastSynced": <LastSyncedTimestamp>
    },
    "groupID": {
        "<gid>": {
            "groupname": <groupname>,
            "lastSynced": <LastSyncedTimestamp>
        }
    }
}
*/

type NssCacheData struct {
	UserCache  NssUserCache  `json:"userID"`
	GroupCache NssGroupCache `json:"groupID"`
}

type NssCachedUser struct {
	Name       string   `json:"username"`
	Groups     []string `json:"groups"`
	LastSynced int64    `json:"lastSynced"`
}

type NssUserCache map[uint64]NssCachedUser

type NssCachedGroup struct {
	Name       string `json:"groupname"`
	LastSynced int64  `json:"lastSynced"`
}

type NssCacheIndex struct {
	UserIndex  map[string]uint64
	GroupIndex map[string]uint64
}

type NssGroupCache map[uint64]NssCachedGroup

// For reading from and writing to the cache.
type NssCacheProvider interface {
	GetUserByName(name string) (User, []Group, bool)
	GetUserByUid(uid uint64) (User, []Group, bool)
	GetGroupByName(name string) (Group, bool)
	GetGroupByGid(gid uint64) (Group, bool)

	UpdateUser(user User, groups []string) error

	AddUsers(users []User) error
	AddGroups(groups []Group) error

	LoadCache() error
	SaveCache() error
}

// This is the specific provider for the file cache.
type JsonNssCacheProvider struct {
	Config     Config
	Cache      NssCacheData
	CacheIndex NssCacheIndex
	TTL        int64
}

// Provide the JsonNssCacheProvider with blank cache / indexes
func DefaultCacheProvider(config Config) JsonNssCacheProvider {
	cache_data := NssCacheData{make(NssUserCache), make(NssGroupCache)}
	cache_index := NssCacheIndex{make(map[string]uint64), make(map[string]uint64)}

	TTL_s, exists := config["nss_cache_timeout_s"]
	if !exists {
		util.Logf("cognito_auth", "Unable to determine the cache TTL. Using: %d", 3600)
		TTL_s = "3600"
	}

	TTL, err := strconv.ParseInt(TTL_s, 10, 64)
	if err != nil || TTL < 0 {
		util.Logf("cognito_auth", "Unable to determine the cache TTL. Using: %d", 3600)
		TTL = 3600
	}

	c := JsonNssCacheProvider{config, cache_data, cache_index, TTL}
	err = c.LoadCache()
	if err != nil {
		util.Logf("cognito_auth", "Unable to load cache: %s", err)
	}
	return c
}

// Lookup a user by uid in the cache
func (c JsonNssCacheProvider) GetUserByUid(uid uint64) (User, []Group, bool) {
	var user User

	cachedUser, exist := c.Cache.UserCache[uid]
	if !exist {
		return user, nil, false
	}

	if c.TTL >= 0 && time.Now().Unix()-cachedUser.LastSynced >= c.TTL {
		return user, nil, false
	}

	//FIXME: how do we guarantee if the group name exists then the group exists in the cache
	if cachedUser.Groups == nil {
		return User{cachedUser.Name, uid}, nil, true
	}

	groups := []Group{}

	for _, groupname := range cachedUser.Groups {
		gid, exist := c.CacheIndex.GroupIndex[groupname]
		if !exist {
			// This shouldn't happen, if we have a groupname we should have it in the index
			return user, nil, false
		}
		groups = append(groups, Group{groupname, gid})
	}

	return User{cachedUser.Name, uid}, groups, true
}

// Lookup a user by name in the cache
func (c JsonNssCacheProvider) GetUserByName(name string) (User, []Group, bool) {
	var user User

	uid, exist := c.CacheIndex.UserIndex[name]
	if exist {
		return c.GetUserByUid(uid)
	}

	return user, nil, false
}

// Lookup a group by id in the cache
func (c JsonNssCacheProvider) GetGroupByGid(gid uint64) (Group, bool) {
	var group Group

	cachedGroup, exist := c.Cache.GroupCache[gid]
	if !exist {
		return group, false
	}

	if c.TTL > 0 && time.Now().Unix()-cachedGroup.LastSynced < c.TTL || c.TTL < 0 {
		group.Name = cachedGroup.Name
		group.Gid = gid
		return group, true
	}

	return Group{}, false
}

// Lookup a group by name in the cache
func (c JsonNssCacheProvider) GetGroupByName(name string) (Group, bool) {
	var group Group

	gid, exist := c.CacheIndex.GroupIndex[name]
	if exist {
		return c.GetGroupByGid(gid)
	}

	return group, false
}

func (c JsonNssCacheProvider) LoadCache() error {
	cache_file := c.Config["nss_cache_path"]
	file, err := os.ReadFile(cache_file)
	if err != nil {
		return fmt.Errorf("%s", err)
	}

	// Read from .json file
	err = json.Unmarshal(file, &c.Cache)

	// Handle caches not being available in file
	if c.Cache.UserCache == nil {
		c.Cache.UserCache = make(NssUserCache)
	}

	if c.Cache.GroupCache == nil {
		c.Cache.GroupCache = make(NssGroupCache)
	}

	if err != nil {
		return fmt.Errorf("%s", err)
	}

	// Store the caches
	for uid, cache_user := range c.Cache.UserCache {
		c.CacheIndex.UserIndex[cache_user.Name] = uid
	}

	for gid, cache_group := range c.Cache.GroupCache {
		c.CacheIndex.GroupIndex[cache_group.Name] = gid
	}

	return nil
}

func (c JsonNssCacheProvider) SaveCache() error {
	cache_file := c.Config["nss_cache_path"]

	// Write temp file
	dir, file := filepath.Split(cache_file)
	tmp_cache, err := ioutil.TempFile(dir, file)
	if err != nil {
		return err
	}

	// Remove the tempfile at the end of this function
	defer os.Remove(tmp_cache.Name())

	// Convert the cache data into json
	data, err := json.MarshalIndent(c.Cache, "", " ")
	if err != nil {
		return err
	}

	// Write the json string to the tempfile
	err = os.WriteFile(tmp_cache.Name(), data, 0644)
	if err != nil {
		return err
	}

	// Sync to flush writes
	if err := tmp_cache.Sync(); err != nil {
		return err
	}

	// Close temp file
	if err := tmp_cache.Close(); err != nil {
		return err
	}

	// Atomically rename/move temp to actual cache file location
	err = os.Rename(tmp_cache.Name(), cache_file)

	// Set the ownership so that others can read
	if err == nil {
		perm := os.FileMode(0644)
		syscall.Chmod(cache_file, uint32(perm))
	}

	return err
}

func (c JsonNssCacheProvider) UpdateUser(user User, groups []string) error {

	u := c.Cache.UserCache[user.Uid]

	u.Name = user.Name
	u.Groups = groups
	u.LastSynced = time.Now().Unix()
	c.Cache.UserCache[user.Uid] = u

	c.CacheIndex.UserIndex[user.Name] = user.Uid

	for _, groupname := range groups {
		gid, _ := GetGroupHash(c.Config, groupname)
		c.CacheIndex.GroupIndex[groupname] = gid
		c.Cache.GroupCache[gid] = NssCachedGroup{groupname, time.Now().Unix()}
	}

	return c.SaveCache()
}

func (c JsonNssCacheProvider) AddUsers(users []User) error {

	for _, user := range users {
		u, exist := c.Cache.UserCache[user.Uid]

		if !exist {
			u.Name = user.Name
			u.Groups = nil
			u.LastSynced = time.Now().Unix()
			c.Cache.UserCache[user.Uid] = u

			c.CacheIndex.UserIndex[user.Name] = user.Uid
		}
	}

	err := c.SaveCache()
	if err != nil {
		util.Logf("cognito_auth", "Unable to save cache: %s", err)
	}
	return err
}

func (c JsonNssCacheProvider) AddGroups(groups []Group) error {
	for _, group := range groups {

		g := c.Cache.GroupCache[group.Gid]
		g.Name = group.Name
		g.LastSynced = time.Now().Unix()
		c.Cache.GroupCache[group.Gid] = g

		c.CacheIndex.GroupIndex[group.Name] = group.Gid
	}

	err := c.SaveCache()
	if err != nil {
		util.Logf("cognito_auth", "Unable to save cache: %s", err)
	}
	return err
}
