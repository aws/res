#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import unittest
from typing import Dict, Optional
from unittest.mock import patch

import pytest
import res as res
from boto3.dynamodb.conditions import And, Attr
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
            session_permission=self.context.session_permission, publish_event=False
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
                session_permission=session_permission_without_range_key,
                publish_event=False,
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
                session_permission=session_permission_without_hash_key,
                publish_event=False,
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

    def test_list_session_permissions_paginated_no_filter(self):
        """Test list_session_permissions_paginated without filter"""
        result, next_token = session_permissions.list_session_permissions_paginated()

        assert result is not None
        assert len(result) >= 1
        assert next_token is None

    def test_list_session_permissions_paginated_with_filter(self):
        """Test list_session_permissions_paginated with filter expression"""

        filter_expr = Attr(session_permissions.SESSION_PERMISSION_DB_RANGE_KEY).eq(
            TEST_USER_NAME
        )
        result, next_token = session_permissions.list_session_permissions_paginated(
            filter_expression=filter_expr
        )

        assert result is not None
        for permission in result:
            assert (
                permission.get(session_permissions.SESSION_PERMISSION_DB_RANGE_KEY)
                == TEST_USER_NAME
            )
        assert next_token is None

    @patch("res.resources.session_permissions.list_session_permissions_paginated")
    def test_list_session_permissions_with_username_filter(self, mock_list_paginated):
        """Test list_session_permissions with username filter"""

        mock_list_paginated.return_value = ([], None)

        session_permissions.list_session_permissions(username=TEST_USER_NAME)

        mock_list_paginated.assert_called_once()
        call_args = mock_list_paginated.call_args
        assert call_args[1]["filter_expression"] == Attr("actor_name").eq(
            TEST_USER_NAME
        )

    @patch("res.resources.session_permissions.list_session_permissions_paginated")
    def test_list_session_permissions_with_state_filter(self, mock_list_paginated):
        """Test list_session_permissions with state filter"""

        mock_list_paginated.return_value = ([], None)

        session_permissions.list_session_permissions(username="user2", state="READY")

        mock_list_paginated.assert_called_once()
        call_args = mock_list_paginated.call_args
        expected_filter = And(
            Attr("actor_name").eq("user2"), Attr("idea_session_state").eq("READY")
        )
        assert call_args[1]["filter_expression"] == expected_filter

    @patch("res.resources.session_permissions.list_session_permissions_paginated")
    def test_list_session_permissions_with_base_os_filter(self, mock_list_paginated):
        """Test list_session_permissions with base_os filter"""

        mock_list_paginated.return_value = ([], None)

        session_permissions.list_session_permissions(
            username="user3", base_os="windows"
        )

        mock_list_paginated.assert_called_once()
        call_args = mock_list_paginated.call_args
        expected_filter = And(
            Attr("actor_name").eq("user3"), Attr("idea_session_base_os").eq("windows")
        )
        assert call_args[1]["filter_expression"] == expected_filter

    @patch("res.resources.session_permissions.list_session_permissions_paginated")
    def test_list_session_permissions_with_session_name_filter(
        self, mock_list_paginated
    ):
        """Test list_session_permissions with session_name filter"""

        mock_list_paginated.return_value = ([], None)

        session_permissions.list_session_permissions(
            username="user4", session_name="test"
        )

        mock_list_paginated.assert_called_once()
        call_args = mock_list_paginated.call_args
        expected_filter = And(
            Attr("actor_name").eq("user4"), Attr("idea_session_name").contains("test")
        )
        assert call_args[1]["filter_expression"] == expected_filter

    @patch("res.resources.session_permissions.list_session_permissions_paginated")
    def test_list_session_permissions_with_date_range_filter(self, mock_list_paginated):
        """Test list_session_permissions with date range filter"""

        mock_list_paginated.return_value = ([], None)

        session_permissions.list_session_permissions(
            username="user5",
            date_range_key="created_on",
            after="1000000",
            before="2000000",
        )

        mock_list_paginated.assert_called_once()
        call_args = mock_list_paginated.call_args
        expected_filter = And(
            Attr("actor_name").eq("user5"), Attr("created_on").between(1000000, 2000000)
        )
        assert call_args[1]["filter_expression"] == expected_filter

    @patch("res.resources.session_permissions.list_session_permissions_paginated")
    def test_list_session_permissions_with_multiple_filters(self, mock_list_paginated):
        """Test list_session_permissions with multiple filters combined"""

        mock_list_paginated.return_value = ([], None)

        session_permissions.list_session_permissions(
            username="user6",
            state="READY",
            base_os="windows",
            session_name="test",
            date_range_key="created_on",
            after="1000000",
            before="2000000",
        )

        mock_list_paginated.assert_called_once()
        call_args = mock_list_paginated.call_args
        expected_filter = And(
            And(
                And(
                    And(
                        Attr("actor_name").eq("user6"),
                        Attr("idea_session_state").eq("READY"),
                    ),
                    Attr("idea_session_base_os").eq("windows"),
                ),
                Attr("idea_session_name").contains("test"),
            ),
            Attr("created_on").between(1000000, 2000000),
        )
        assert call_args[1]["filter_expression"] == expected_filter

    @patch("res.resources.session_permissions.list_session_permissions_paginated")
    def test_list_session_permissions_empty_result(self, mock_list_paginated):
        """Test list_session_permissions returns empty list when no permissions match"""
        mock_list_paginated.return_value = ([], None)

        result, next_token = session_permissions.list_session_permissions(
            username="nonexistent_user"
        )

        assert result == []
        assert next_token is None


class TestValidateSessionAccess:

    @patch("res.resources.session_permissions.sessions.get_sessions_by_ids")
    def test_returns_session_when_user_is_owner(self, mock_get_sessions):
        session = {
            "owner": "alice",
            "idea_session_id": "ses-1",
            "dcv_session_id": "dcv-1",
        }
        mock_get_sessions.return_value = {"ses-1": session}

        result = session_permissions.validate_session_access("ses-1", "alice")
        assert result == session

    @patch("res.resources.session_permissions.sessions.get_sessions_by_ids")
    def test_raises_when_session_not_found(self, mock_get_sessions):
        mock_get_sessions.return_value = {}

        with pytest.raises(exceptions.SessionAccessDenied):
            session_permissions.validate_session_access("ses-1", "alice")

    @patch("res.resources.session_permissions.get_session_permission")
    @patch("res.resources.session_permissions.sessions.get_sessions_by_ids")
    def test_returns_session_when_user_has_permission(
        self, mock_get_sessions, mock_get_perm
    ):
        session = {
            "owner": "bob",
            "idea_session_id": "ses-1",
            "dcv_session_id": "dcv-1",
        }
        mock_get_sessions.return_value = {"ses-1": session}
        mock_get_perm.return_value = {"actor_name": "alice"}

        result = session_permissions.validate_session_access("ses-1", "alice")
        assert result == session

    @patch("res.resources.session_permissions.get_session_permission")
    @patch("res.resources.session_permissions.sessions.get_sessions_by_ids")
    def test_raises_when_user_lacks_permission(self, mock_get_sessions, mock_get_perm):
        session = {
            "owner": "bob",
            "idea_session_id": "ses-1",
            "dcv_session_id": "dcv-1",
        }
        mock_get_sessions.return_value = {"ses-1": session}
        mock_get_perm.side_effect = exceptions.SessionPermissionsNotFound("not found")

        with pytest.raises(exceptions.SessionAccessDenied):
            session_permissions.validate_session_access("ses-1", "alice")
