#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import unittest
from typing import Dict, Optional

import pytest
import res as res
from res import exceptions
from res.resources import session_permissions
from res.utils import table_utils

TEST_SESSION_ID = "test_session_id"
TEST_USER_NAME = "test_user_name"
RANDOM_SESSION_ID = "random_session_id"


class SessionPermissionsTestContext:
    session_permission: Optional[Dict]


class TestSessionPermissions(unittest.TestCase):

    def setUp(self):
        self.context: SessionPermissionsTestContext = SessionPermissionsTestContext()
        self.context.session_permission = {
            session_permissions.SESSION_PERMISSION_DB_HASH_KEY: TEST_SESSION_ID,
            session_permissions.SESSION_PERMISSION_DB_RANGE_KEY: TEST_USER_NAME,
        }
        table_utils.create_item(
            session_permissions.SESSION_PERMISSION_TABLE_NAME,
            item=self.context.session_permission,
        )

    def test_get_session_permission_pass(self):
        """
        get session permissions happy path
        """
        permissions = session_permissions.get_session_permission(
            TEST_SESSION_ID, TEST_USER_NAME
        )
        assert (
            permissions.get(session_permissions.SESSION_PERMISSION_DB_HASH_KEY)
            == TEST_SESSION_ID
        )
        assert (
            permissions.get(session_permissions.SESSION_PERMISSION_DB_RANGE_KEY)
            == TEST_USER_NAME
        )

    def test_get_session_permission_fail(self):
        """
        get session permissions failure
        """
        with pytest.raises(exceptions.SessionPermissionsNotFound) as exc_info:
            session_permissions.get_session_permission(
                RANDOM_SESSION_ID, TEST_USER_NAME
            )
        assert (
            f"Session permission not found for {session_permissions.SESSION_PERMISSION_DB_HASH_KEY}: {RANDOM_SESSION_ID} for {session_permissions.SESSION_PERMISSION_DB_RANGE_KEY} : {TEST_USER_NAME}"
            == exc_info.value.args[0]
        )

    def test_delete_session_permission_pass(self):
        """
        delete session permissions happy path
        """
        permissions = session_permissions.get_session_permission(
            TEST_SESSION_ID, TEST_USER_NAME
        )
        assert (
            permissions.get(session_permissions.SESSION_PERMISSION_DB_HASH_KEY)
            == TEST_SESSION_ID
        )
        assert (
            permissions.get(session_permissions.SESSION_PERMISSION_DB_RANGE_KEY)
            == TEST_USER_NAME
        )

        session_permissions.delete_session_permission(
            session_permission=self.context.session_permission
        )

        with pytest.raises(exceptions.SessionPermissionsNotFound) as exc_info:
            session_permissions.get_session_permission(TEST_SESSION_ID, TEST_USER_NAME)
        assert (
            f"Session permission not found for {session_permissions.SESSION_PERMISSION_DB_HASH_KEY}: {TEST_SESSION_ID} for {session_permissions.SESSION_PERMISSION_DB_RANGE_KEY} : {TEST_USER_NAME}"
            == exc_info.value.args[0]
        )

    def test_delete_session_permission_fail(self):
        """
        delete session permissions failure
        """
        session_permission_without_range_key = {
            session_permissions.SESSION_PERMISSION_DB_HASH_KEY: TEST_SESSION_ID,
        }
        with pytest.raises(Exception) as exc_info:
            session_permissions.delete_session_permission(
                session_permission=session_permission_without_range_key
            )
        assert (
            session_permissions.SESSION_PERMISSION_DB_RANGE_KEY
            in exc_info.value.args[0]
        )

        session_permission_without_hash_key = {
            session_permissions.SESSION_PERMISSION_DB_RANGE_KEY: TEST_USER_NAME,
        }
        with pytest.raises(Exception) as exc_info:
            session_permissions.delete_session_permission(
                session_permission=session_permission_without_hash_key
            )
        assert (
            session_permissions.SESSION_PERMISSION_DB_HASH_KEY in exc_info.value.args[0]
        )

    def test_get_session_permission_by_id_pass(self):
        """
        get session permissions by session id happy path
        """
        permissions = session_permissions.get_session_permission_by_id(TEST_SESSION_ID)
        assert len(permissions) == 1
        assert (
            permissions[0][session_permissions.SESSION_PERMISSION_DB_RANGE_KEY]
            == TEST_USER_NAME
        )

    def test_get_session_permission_by_id_fail(self):
        """
        get session permissions by session id happy fail
        """
        with pytest.raises(exceptions.SessionPermissionsNotFound) as exc_info:
            session_permissions.get_session_permission_by_id(RANDOM_SESSION_ID)
        assert (
            f"Session permission not found for {session_permissions.SESSION_PERMISSION_DB_HASH_KEY}: {RANDOM_SESSION_ID}"
            == exc_info.value.args[0]
        )

    def test_delete_session_permission_by_id_pass(self):
        """
        delete session permissions by session id happy path
        """
        permissions = session_permissions.get_session_permission(
            TEST_SESSION_ID, TEST_USER_NAME
        )
        assert (
            permissions.get(session_permissions.SESSION_PERMISSION_DB_HASH_KEY)
            == TEST_SESSION_ID
        )
        assert (
            permissions.get(session_permissions.SESSION_PERMISSION_DB_RANGE_KEY)
            == TEST_USER_NAME
        )

        session_permissions.delete_session_permission_by_id(TEST_SESSION_ID)

        with pytest.raises(exceptions.SessionPermissionsNotFound) as exc_info:
            session_permissions.get_session_permission(TEST_SESSION_ID, TEST_USER_NAME)
        assert (
            f"Session permission not found for {session_permissions.SESSION_PERMISSION_DB_HASH_KEY}: {TEST_SESSION_ID} for {session_permissions.SESSION_PERMISSION_DB_RANGE_KEY} : {TEST_USER_NAME}"
            == exc_info.value.args[0]
        )
