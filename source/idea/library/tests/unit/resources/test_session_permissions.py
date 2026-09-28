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
            session_permission=self.context.session_permission,
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
    def test_list_session_permissions_with_session_id_filter(self, mock_list_paginated):
        """Test list_session_permissions with session_id filter"""

        mock_list_paginated.return_value = ([], None)

        session_permissions.list_session_permissions(
            username="user6",
            session_id="ses-123",
        )

        mock_list_paginated.assert_called_once()
        call_args = mock_list_paginated.call_args
        expected_filter = And(
            Attr("actor_name").eq("user6"), Attr("idea_session_id").eq("ses-123")
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


class TestListAllSessionPermissions:

    @patch("res.resources.session_permissions.list_session_permissions_paginated")
    def test_single_page_returns_all(self, mock_list_paginated):
        """Test single page with no next_token returns all items."""
        mock_list_paginated.return_value = (
            [{"idea_session_id": "ses-1"}, {"idea_session_id": "ses-2"}],
            None,
        )

        result = session_permissions.list_all_session_permissions(username="user1")

        assert len(result) == 2
        mock_list_paginated.assert_called_once()

    @patch("res.resources.session_permissions.list_session_permissions_paginated")
    def test_multi_page_concatenates_results(self, mock_list_paginated):
        """Test multiple pages are concatenated into a single list."""
        mock_list_paginated.side_effect = [
            ([{"idea_session_id": "ses-1"}], "token-page2"),
            ([{"idea_session_id": "ses-2"}], "token-page3"),
            ([{"idea_session_id": "ses-3"}], None),
        ]

        result = session_permissions.list_all_session_permissions(username="user1")

        assert len(result) == 3
        assert result[0]["idea_session_id"] == "ses-1"
        assert result[2]["idea_session_id"] == "ses-3"
        assert mock_list_paginated.call_count == 3

    @patch("res.resources.session_permissions.list_session_permissions_paginated")
    def test_empty_results(self, mock_list_paginated):
        """Test empty table returns empty list."""
        mock_list_paginated.return_value = ([], None)

        result = session_permissions.list_all_session_permissions(username="user1")

        assert result == []
        mock_list_paginated.assert_called_once()


class TestEnrichAndFilterPermissionsWithSessionData:
    """Tests for enrich_and_filter_permissions_with_session_data."""

    @patch("res.resources.session_permissions.sessions.get_sessions_by_owner_and_ids")
    def test_enriches_permissions_with_session_data(self, mock_get_sessions):
        """Test that permissions are enriched with session attributes."""
        permissions = [
            {
                "idea_session_id": "ses-1",
                "idea_session_owner": "owner1",
                "actor_name": "viewer1",
            },
        ]
        mock_get_sessions.return_value = {
            "ses-1": {
                "name": "My Desktop",
                "base_os": "linux",
                "state": "READY",
                "server": {"instance_type": "m5.xlarge"},
                "session_type": "CONSOLE",
                "hibernation_enabled": True,
            }
        }

        result = session_permissions.enrich_and_filter_permissions_with_session_data(
            permissions
        )

        assert len(result) == 1
        assert result[0]["idea_session_name"] == "My Desktop"
        assert result[0]["idea_session_base_os"] == "linux"
        assert result[0]["idea_session_state"] == "READY"
        assert result[0]["idea_session_instance_type"] == "m5.xlarge"
        assert result[0]["idea_session_type"] == "CONSOLE"
        assert result[0]["idea_session_hibernation_enabled"] is True
        mock_get_sessions.assert_called_once_with([("owner1", "ses-1")])

    @patch("res.resources.session_permissions.sessions.get_sessions_by_owner_and_ids")
    def test_excludes_permissions_with_missing_session(self, mock_get_sessions):
        """Test that permissions are excluded when session is not found."""
        permissions = [
            {
                "idea_session_id": "ses-1",
                "idea_session_owner": "owner1",
                "actor_name": "viewer1",
            },
            {
                "idea_session_id": "ses-2",
                "idea_session_owner": "owner2",
                "actor_name": "viewer2",
            },
        ]
        mock_get_sessions.return_value = {
            "ses-1": {
                "name": "Desktop 1",
                "base_os": "linux",
                "state": "READY",
                "server": {"instance_type": "m5.large"},
                "session_type": "CONSOLE",
                "hibernation_enabled": False,
            }
        }

        result = session_permissions.enrich_and_filter_permissions_with_session_data(
            permissions
        )

        assert len(result) == 1
        assert result[0]["idea_session_id"] == "ses-1"

    @patch("res.resources.session_permissions.sessions.get_sessions_by_owner_and_ids")
    def test_filters_by_state(self, mock_get_sessions):
        """Test filtering by session state."""
        permissions = [
            {
                "idea_session_id": "ses-1",
                "idea_session_owner": "owner1",
                "actor_name": "v1",
            },
            {
                "idea_session_id": "ses-2",
                "idea_session_owner": "owner2",
                "actor_name": "v2",
            },
        ]
        mock_get_sessions.return_value = {
            "ses-1": {
                "name": "D1",
                "base_os": "linux",
                "state": "READY",
                "server": {},
                "session_type": "CONSOLE",
                "hibernation_enabled": False,
            },
            "ses-2": {
                "name": "D2",
                "base_os": "linux",
                "state": "STOPPED",
                "server": {},
                "session_type": "CONSOLE",
                "hibernation_enabled": False,
            },
        }

        result = session_permissions.enrich_and_filter_permissions_with_session_data(
            permissions, state="READY"
        )

        assert len(result) == 1
        assert result[0]["idea_session_id"] == "ses-1"

    @patch("res.resources.session_permissions.sessions.get_sessions_by_owner_and_ids")
    def test_filters_by_base_os(self, mock_get_sessions):
        """Test filtering by base OS."""
        permissions = [
            {
                "idea_session_id": "ses-1",
                "idea_session_owner": "owner1",
                "actor_name": "v1",
            },
            {
                "idea_session_id": "ses-2",
                "idea_session_owner": "owner2",
                "actor_name": "v2",
            },
        ]
        mock_get_sessions.return_value = {
            "ses-1": {
                "name": "D1",
                "base_os": "linux",
                "state": "READY",
                "server": {},
                "session_type": "CONSOLE",
                "hibernation_enabled": False,
            },
            "ses-2": {
                "name": "D2",
                "base_os": "windows",
                "state": "READY",
                "server": {},
                "session_type": "CONSOLE",
                "hibernation_enabled": False,
            },
        }

        result = session_permissions.enrich_and_filter_permissions_with_session_data(
            permissions, base_os="windows"
        )

        assert len(result) == 1
        assert result[0]["idea_session_id"] == "ses-2"

    @patch("res.resources.session_permissions.sessions.get_sessions_by_owner_and_ids")
    def test_filters_by_session_name_substring(self, mock_get_sessions):
        """Test filtering by session name substring."""
        permissions = [
            {
                "idea_session_id": "ses-1",
                "idea_session_owner": "owner1",
                "actor_name": "v1",
            },
            {
                "idea_session_id": "ses-2",
                "idea_session_owner": "owner2",
                "actor_name": "v2",
            },
        ]
        mock_get_sessions.return_value = {
            "ses-1": {
                "name": "Dev Desktop",
                "base_os": "linux",
                "state": "READY",
                "server": {},
                "session_type": "CONSOLE",
                "hibernation_enabled": False,
            },
            "ses-2": {
                "name": "Prod Machine",
                "base_os": "linux",
                "state": "READY",
                "server": {},
                "session_type": "CONSOLE",
                "hibernation_enabled": False,
            },
        }

        result = session_permissions.enrich_and_filter_permissions_with_session_data(
            permissions, session_name="Dev"
        )

        assert len(result) == 1
        assert result[0]["idea_session_id"] == "ses-1"

    @patch("res.resources.session_permissions.sessions.get_sessions_by_owner_and_ids")
    def test_no_filters_returns_all_enriched(self, mock_get_sessions):
        """Test that without filters all permissions with sessions are returned."""
        permissions = [
            {
                "idea_session_id": "ses-1",
                "idea_session_owner": "owner1",
                "actor_name": "v1",
            },
            {
                "idea_session_id": "ses-2",
                "idea_session_owner": "owner2",
                "actor_name": "v2",
            },
        ]
        mock_get_sessions.return_value = {
            "ses-1": {
                "name": "D1",
                "base_os": "linux",
                "state": "READY",
                "server": {"instance_type": "m5.large"},
                "session_type": "CONSOLE",
                "hibernation_enabled": False,
            },
            "ses-2": {
                "name": "D2",
                "base_os": "windows",
                "state": "STOPPED",
                "server": {"instance_type": "t3.micro"},
                "session_type": "VIRTUAL",
                "hibernation_enabled": True,
            },
        }

        result = session_permissions.enrich_and_filter_permissions_with_session_data(
            permissions
        )

        assert len(result) == 2

    @patch("res.resources.session_permissions.sessions.get_sessions_by_owner_and_ids")
    def test_empty_permissions_returns_empty(self, mock_get_sessions):
        """Test that empty permissions list returns empty."""
        mock_get_sessions.return_value = {}

        result = session_permissions.enrich_and_filter_permissions_with_session_data([])

        assert result == []
        mock_get_sessions.assert_called_once_with([])


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


class TestEnforcePermissionsForSession:

    @patch(
        "res.clients.dcv_session_manager.dcv_session_manager_client.update_session_permissions"
    )
    @patch("res.resources.dcv.session_permissions.generate_permissions_content")
    @patch("res.resources.session_permissions.cluster_settings")
    @patch("res.resources.session_permissions.sessions.get_session")
    def test_pushes_permissions_when_session_ready(
        self,
        mock_get_session,
        mock_cluster_settings,
        mock_generate_permissions_content,
        mock_update_session_permissions,
    ):
        mock_get_session.return_value = {
            "idea_session_id": "ses-1",
            "owner": "alice",
            session_permissions.sessions.SESSION_DB_STATE_KEY: "READY",
        }
        mock_cluster_settings.get_setting.return_value = "clusteradmin"
        mock_generate_permissions_content.return_value = (
            "[groups]\ngroup:ideaadmin=user:clusteradmin\n"
        )

        session_permissions.enforce_permissions_for_session(
            idea_session_id="ses-1", idea_session_owner="alice"
        )

        mock_generate_permissions_content.assert_called_once_with(
            session_id="ses-1", admin_username="clusteradmin"
        )
        mock_update_session_permissions.assert_called_once()
        kwargs = mock_update_session_permissions.call_args.kwargs
        assert kwargs["session_id"] == "ses-1"
        assert kwargs["owner"] == "alice"
        assert kwargs["permissions_file"] is not None

    @patch(
        "res.clients.dcv_session_manager.dcv_session_manager_client.update_session_permissions"
    )
    @patch("res.resources.dcv.session_permissions.generate_permissions_content")
    @patch("res.resources.session_permissions.cluster_settings")
    @patch("res.resources.session_permissions.sessions.get_session")
    def test_skips_when_session_not_ready(
        self,
        mock_get_session,
        mock_cluster_settings,
        mock_generate_permissions_content,
        mock_update_session_permissions,
    ):
        mock_get_session.return_value = {
            "idea_session_id": "ses-1",
            "owner": "alice",
            session_permissions.sessions.SESSION_DB_STATE_KEY: "STOPPED",
        }

        session_permissions.enforce_permissions_for_session(
            idea_session_id="ses-1", idea_session_owner="alice"
        )

        mock_generate_permissions_content.assert_not_called()
        mock_update_session_permissions.assert_not_called()

    @patch(
        "res.clients.dcv_session_manager.dcv_session_manager_client.update_session_permissions"
    )
    @patch("res.resources.session_permissions.sessions.get_session")
    def test_skips_when_session_missing(
        self, mock_get_session, mock_update_session_permissions
    ):
        mock_get_session.side_effect = exceptions.UserSessionNotFound("missing")

        session_permissions.enforce_permissions_for_session(
            idea_session_id="ses-1", idea_session_owner="alice"
        )

        mock_update_session_permissions.assert_not_called()


class TestUpdatePermissionsForSessionsCallsEnforce:

    @patch("res.resources.session_permissions.enforce_permissions_for_session")
    @patch("res.resources.session_permissions.delete_session_permission")
    @patch("res.resources.session_permissions.update_session_permission")
    @patch("res.resources.session_permissions.create_session_permission")
    def test_enforce_called_per_unique_session(
        self,
        mock_create,
        mock_update,
        mock_delete,
        mock_enforce,
    ):
        mock_create.side_effect = lambda p: p
        mock_update.side_effect = lambda p: p

        permission_to_create = [
            {
                session_permissions.SESSION_PERMISSION_DB_HASH_KEY: "ses-1",
                session_permissions.SESSION_PERMISSION_DB_SESSION_OWNER_KEY: "alice",
            }
        ]
        permission_to_update = [
            {
                session_permissions.SESSION_PERMISSION_DB_HASH_KEY: "ses-1",
                session_permissions.SESSION_PERMISSION_DB_SESSION_OWNER_KEY: "alice",
            }
        ]
        permission_to_delete = [
            {
                session_permissions.SESSION_PERMISSION_DB_HASH_KEY: "ses-2",
                session_permissions.SESSION_PERMISSION_DB_SESSION_OWNER_KEY: "bob",
            }
        ]

        session_permissions.update_permissions_for_sessions(
            permission_to_create, permission_to_update, permission_to_delete
        )

        assert mock_enforce.call_count == 2
        called_with = {
            (
                call.kwargs["idea_session_id"],
                call.kwargs["idea_session_owner"],
            )
            for call in mock_enforce.call_args_list
        }
        assert called_with == {("ses-1", "alice"), ("ses-2", "bob")}
