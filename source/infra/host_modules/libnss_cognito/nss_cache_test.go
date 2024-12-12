package main

import (
	. "host_modules/util"
	util "host_modules/util"
	"fmt"
	"os"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestNssCache(t *testing.T) {
	// Test reading from a file specified in the environment
	t.Setenv("CONFIG_PATH", "../../resources/cognito_auth.conf")

	t.Setenv(strings.ToUpper("nss_cache_timeout_s"), "60")
	tmp_cache, _ := os.CreateTemp("", "nss_cache.")
	t.Setenv(strings.ToUpper("nss_cache_path"), tmp_cache.Name())

	fmt.Println("Cache file: ", tmp_cache.Name())

	config, err := util.ParseConfig()
	if err != nil {
		t.Errorf("Couldn't parse: %s", err)
	}

	cache := DefaultCacheProvider(config)

	t.Run("Invalid cache false", func(t *testing.T) {
		_, _, found := cache.GetUserByName("nvalid")
		assert.Equal(t, found, false)
	})

	t.Run("Read back after update user", func(t *testing.T) {
		cache.UpdateUser(User{"username", 1001}, []string{"group1", "group2"})
		user, groups, found := cache.GetUserByName("username")
		assert.Equal(t, found, true)
		assert.Equal(t, user.Uid, uint64(1001))
		assert.Equal(t, groups[0].Name, "group1")
		assert.Equal(t, groups[1].Name, "group2")

		user, groups, found = cache.GetUserByUid(1001)
		assert.Equal(t, found, true)
		assert.Equal(t, user.Uid, uint64(1001))
		assert.Equal(t, groups[0].Name, "group1")
		assert.Equal(t, groups[1].Name, "group2")

		_, found = cache.GetGroupByName("group1")
		assert.Equal(t, found, true)

		gid, _ := util.GetGroupHash(config, "group1")
		_, found = cache.GetGroupByGid(gid)
		assert.Equal(t, found, true)
	})

	// Test adding all users
	t.Run("Read back after bulk add user", func(t *testing.T) {
		users := []User{{"bulk_user1", 4001}, {"bulk_user2", 4002}}
		cache.AddUsers(users)

		_, groups, found := cache.GetUserByName("bulk_user1")
		assert.Equal(t, found, true)
		assert.Equal(t, groups == nil, true)

		_, _, found = cache.GetUserByUid(4001)
		assert.Equal(t, found, true)
	})

	// Test adding all groups
	t.Run("Read back after bulk add group", func(t *testing.T) {
		groups := []Group{{"bulk_group1", 4003}, {"bulk_group2", 4004}}
		cache.AddGroups(groups)

		_, found := cache.GetGroupByName("bulk_group1")
		assert.Equal(t, found, true)

		_, found = cache.GetGroupByGid(4003)
		assert.Equal(t, found, true)
	})

	// Test expired TTL
	t.Setenv(strings.ToUpper("nss_cache_timeout_s"), "0")
	config, err = util.ParseConfig()
	if err != nil {
		t.Errorf("Couldn't parse: %s", err)
	}
	cache = DefaultCacheProvider(config)

	t.Run("Read back with zero TTL", func(t *testing.T) {
		_, found := cache.GetGroupByName("bulk_group1")
		assert.Equal(t, found, false)

		_, found = cache.GetGroupByGid(4003)
		assert.Equal(t, found, false)
	})
}
