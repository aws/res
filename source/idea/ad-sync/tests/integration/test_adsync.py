#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import random
import time

import adsync.main as main
import pytest
from assertpy import assert_that
from res import exceptions
from res.resources import accounts


def do_adsync():
    "Run the AD Sync"
    start_time = time.time()
    main.main()
    print(f"-------------TIME: {time.time()-start_time}------------")


def get_usernames_in_group(group_name):
    users = accounts._get_users_in_group(group_name)
    return [user["username"] for user in users]


def test_adsync_user(context, ldap_helper, monkeypatch):
    "Run user crud tests on the AD Sync process."
    # Add a new user to the directory
    username = f"user{random.randint(200,2000000)}"
    ldap_helper.add_ldap_user(username)

    # Ensure that the LDAP add worked
    _dn, ldap_user = ldap_helper.find_ldap_user(username)
    assert_that(ldap_user["sAMAccountName"]).is_equal_to(username)

    # Do AD sync and ensure that the user is in the DDB
    do_adsync()

    res_user = accounts.get_user(username)
    assert_that(res_user["username"]).is_equal_to(username)

    # Delete the user from AD
    ldap_helper.delete_ldap_user(username)
    assert_that(ldap_helper.find_ldap_user(username)).is_none()

    # Do AD sync and ensure that the user is deleted in the DDB
    do_adsync()
    with pytest.raises(exceptions.UserNotFound):
        accounts.get_user(username)


def test_adsync_group(context, ldap_helper, monkeypatch):
    "Run group crud tests on the AD Sync process."
    # Add a new group to the directory
    groupname = f"group{random.randint(200,2000000)}"
    ldap_helper.add_ldap_group(groupname)

    # Ensure that the LDAP add worked
    _dn, ldap_group = ldap_helper.find_ldap_group(groupname)
    assert_that(ldap_group["sAMAccountName"]).is_equal_to(groupname)

    # Do AD sync and ensure that the group is in the DDB
    do_adsync()

    res_group = accounts.get_group(groupname)
    assert_that(res_group["group_name"]).is_equal_to(groupname)

    # Delete the group from AD
    ldap_helper.delete_ldap_group(groupname)
    assert_that(ldap_helper.find_ldap_group(groupname)).is_none()

    # Do AD sync and ensure that the user is deleted in the DDB
    do_adsync()
    with pytest.raises(exceptions.GroupNotFound) as group_error:
        accounts.get_group(groupname)

    assert_that(group_error).is_not_none()
