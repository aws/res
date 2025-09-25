#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import random
import signal
import threading
import time

import adsync.main as main
import pytest
from assertpy import assert_that
from res import exceptions
from res.clients.ad_sync import ad_sync_client
from res.clients.ldap_client import active_directory_client
from res.constants import AD_SYNC_STATUS_STATUS_KEY
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


def test_adsync_update_user_email(context, ldap_helper, monkeypatch):
    "Run update user email tests on the AD Sync process."

    new_email = "new@example.com"
    # Add a new user to the directory
    username = f"user{random.randint(200,2000000)}"
    ldap_helper.add_ldap_user(username)

    # Ensure that the LDAP add worked
    _dn, ldap_user = ldap_helper.find_ldap_user(username)
    print(ldap_user)
    assert_that(ldap_user["sAMAccountName"]).is_equal_to(username)
    assert_that(ldap_user["mail"]).is_equal_to(f"{username}@corp.res.com")

    # Do AD sync and ensure that the user is in the DDB
    do_adsync()

    res_user = accounts.get_user(username)
    assert_that(res_user["username"]).is_equal_to(username)

    # Update the user email in AD
    updates = {"mail": new_email.encode("utf-8")}
    ldap_helper.update_ldap_user(username, updates)
    _dn, ldap_user = ldap_helper.find_ldap_user(username)
    assert_that(ldap_user).is_not_none()
    assert_that(ldap_user["sAMAccountName"]).is_equal_to(username)
    assert_that(ldap_user["mail"]).is_equal_to(new_email)

    # Do AD sync and ensure that the user email is updated in DDB
    do_adsync()

    res_user = accounts.get_user(username)
    assert_that(res_user["username"]).is_equal_to(username)
    assert_that(res_user["email"]).is_equal_to(new_email)

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


def test_ad_sync_status_completed(context, ldap_helper, monkeypatch):
    do_adsync()
    assert_that(
        ad_sync_client.get_ad_sync_status().get(AD_SYNC_STATUS_STATUS_KEY)
    ).is_equal_to(ad_sync_client.ADSyncStatus.STOPPED)


def test_ad_sync_status_failed(context, ldap_helper, monkeypatch):
    monkeypatch.setattr(
        active_directory_client, "get_active_directory_client_options", lambda x: None
    )
    do_adsync()
    assert_that(
        ad_sync_client.get_ad_sync_status().get(AD_SYNC_STATUS_STATUS_KEY)
    ).is_equal_to(ad_sync_client.ADSyncStatus.ERROR)


def test_ad_sync_status_terminated(context, ldap_helper, monkeypatch):
    pid = os.getpid()

    # Send the signal.SIGTERM to simulate the behavior when the AD sync task is forced to stop
    def trigger_signal():
        while not ad_sync_client.get_ad_sync_status():
            time.sleep(0.2)
        os.kill(pid, signal.SIGTERM)

    thread = threading.Thread(target=trigger_signal)
    thread.daemon = True
    thread.start()

    # Sleep for 60 seconds during the AD sync process
    def _sleep(_url: str):
        time.sleep(60)

    monkeypatch.setattr(main, "_fetch_ldap_groups", _sleep)

    with pytest.raises(SystemExit):
        do_adsync()

        assert_that(
            ad_sync_client.get_ad_sync_status().get(AD_SYNC_STATUS_STATUS_KEY)
        ).is_equal_to(ad_sync_client.ADSyncStatus.STOPPED)
