#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import unittest
from typing import Dict, Optional
from unittest.mock import patch

import pytest
import res as res
import res.exceptions as exceptions
from boto3.dynamodb.conditions import And, Attr
from res.resources import accounts, sessions
from res.utils import table_utils, time_utils

TEST_OWNER = "test_owner"
TEST_SESSION_ID = "test_session_id"
RANDOM_OWNER = "random_owner"
RANDOM_SESSION_ID = "random_session_id"
TEST_STATE = "test_state"
UPDATED_STATE = "updates_state"


class SessionsTestContext:
    session: Optional[Dict]


class TestSessions(unittest.TestCase):

    def setUp(self):
        self.context: SessionsTestContext = SessionsTestContext()
        self.context.session = {
            sessions.SESSION_DB_HASH_KEY: TEST_OWNER,
            sessions.SESSION_DB_RANGE_KEY: TEST_SESSION_ID,
            sessions.SESSION_DB_STATE_KEY: TEST_STATE,
        }
        table_utils.create_item(sessions.SESSIONS_TABLE_NAME, item=self.context.session)

        # Create additional test sessions for list operations
        self.test_sessions = [
            {
                sessions.SESSION_DB_HASH_KEY: "user1",
                sessions.SESSION_DB_RANGE_KEY: "session1",
                sessions.SESSION_DB_STATE_KEY: "READY",
                "base_os": "amazonlinux2",
            },
            {
                sessions.SESSION_DB_HASH_KEY: "user1",
                sessions.SESSION_DB_RANGE_KEY: "session2",
                sessions.SESSION_DB_STATE_KEY: "STOPPED",
                "base_os": "windows",
            },
            {
                sessions.SESSION_DB_HASH_KEY: "user2",
                sessions.SESSION_DB_RANGE_KEY: "session3",
                sessions.SESSION_DB_STATE_KEY: "READY",
                "project": {"project_id": "project1"},
            },
            {
                sessions.SESSION_DB_HASH_KEY: "user3",
                sessions.SESSION_DB_RANGE_KEY: "session4",
                sessions.SESSION_DB_DCV_SESSION_ID_KEY: "dcv-aaa",
                sessions.SESSION_DB_BASE_OS_KEY: "linux",
                "server": {"instance_id": "i-111"},
            },
            {
                sessions.SESSION_DB_HASH_KEY: "user4",
                sessions.SESSION_DB_RANGE_KEY: "session5",
                sessions.SESSION_DB_DCV_SESSION_ID_KEY: "dcv-bbb",
                sessions.SESSION_DB_BASE_OS_KEY: "windows",
                "server": {"instance_id": "i-222"},
            },
        ]
        for session in self.test_sessions:
            table_utils.create_item(sessions.SESSIONS_TABLE_NAME, item=session)

    def tearDown(self):
        # Clean up test sessions
        sessions.delete_session(self.context.session)
        for session in self.test_sessions:
            sessions.delete_session(session)

    def test_sessions_get_sessions_invalid_request_should_fail(self):
        """
        get session failure
        """
        # invalid owner
        with pytest.raises(exceptions.UserSessionNotFound) as exc_info:
            sessions.get_session(owner=RANDOM_OWNER, session_id=TEST_SESSION_ID)
        assert f"Session not found: {TEST_SESSION_ID}" == exc_info.value.args[0]

        # invalid session id
        with pytest.raises(exceptions.UserSessionNotFound) as exc_info:
            sessions.get_session(owner=TEST_OWNER, session_id=RANDOM_SESSION_ID)
        assert f"Session not found: {RANDOM_SESSION_ID}" == exc_info.value.args[0]

    def test_sessions_get_sessions_valid_request_should_pass(self):
        """
        get session happy path
        """
        result = sessions.get_session(owner=TEST_OWNER, session_id=TEST_SESSION_ID)
        assert result is not None
        assert result.get(sessions.SESSION_DB_HASH_KEY) == TEST_OWNER
        assert result.get(sessions.SESSION_DB_RANGE_KEY) == TEST_SESSION_ID

    def test_sessions_update_session_should_pass(self):
        """
        update session happy path
        """
        assert self.context.session is not None
        updated_session = self.context.session
        updated_session["state"] = UPDATED_STATE
        sessions.update_session(updated_session)
        session = sessions.get_session(owner=TEST_OWNER, session_id=TEST_SESSION_ID)
        assert session is not None
        assert session.get(sessions.SESSION_DB_HASH_KEY) == TEST_OWNER
        assert session.get(sessions.SESSION_DB_RANGE_KEY) == TEST_SESSION_ID
        assert session.get(sessions.SESSION_DB_STATE_KEY) == UPDATED_STATE

        curr_time = time_utils.current_time_ms()
        assert session.get(sessions.SESSION_DB_UPDATED_ON_KEY) is not None
        assert session.get(sessions.SESSION_DB_UPDATED_ON_KEY) <= curr_time

    def test_list_sessions_paginated_no_filter(self):
        """
        Test list_sessions_paginated without filter
        """
        result, next_token = sessions.list_sessions_paginated()

        assert result is not None
        assert len(result) >= 3  # At least 3 test sessions
        assert next_token is None

    def test_list_sessions_paginated_with_filter(self):
        """
        Test list_sessions_paginated with filter
        """
        filter_expr = Attr("state").eq("READY")
        result, next_token = sessions.list_sessions_paginated(
            filter_expression=filter_expr
        )

        assert result is not None
        for session in result:
            assert session.get("state") == "READY"
        assert next_token is None

    def test_list_sessions_paginated_with_base_os_filter(self):
        """
        Test list_sessions_paginated with base_os filter
        """
        filter_expr = Attr("base_os").eq("windows")
        result, next_token = sessions.list_sessions_paginated(
            filter_expression=filter_expr
        )

        assert result is not None
        for session in result:
            assert session.get("base_os") == "windows"
        assert next_token is None

    def test_list_sessions_for_user_no_additional_filter(self):
        """
        Test list_sessions_for_user without additional filter
        """
        result, next_token = sessions.list_sessions_for_user("user1")

        assert result is not None
        for session in result:
            assert session.get(sessions.SESSION_DB_HASH_KEY) == "user1"
        assert next_token is None

    def test_list_sessions_for_user_with_additional_filter(self):
        """
        Test list_sessions_for_user with additional filter
        """
        additional_filter = Attr("state").eq("READY")
        result, next_token = sessions.list_sessions_for_user(
            "user1", filter_expression=additional_filter
        )

        assert result is not None
        assert result[0].get(sessions.SESSION_DB_HASH_KEY) == "user1"
        assert result[0].get("state") == "READY"
        assert next_token is None

    def test_list_sessions_for_user_with_projects_no_additional_filter(self):
        """
        Test list_sessions_for_user with project_ids without additional filter
        """
        result, next_token = sessions.list_sessions_for_user(
            "user1", project_ids=["project1", "project2"]
        )

        assert result is not None
        for session in result:
            owner_match = session.get(sessions.SESSION_DB_HASH_KEY) == "user1"
            project_match = session.get("project", {}).get("project_id") in [
                "project1",
                "project2",
            ]
            assert (
                owner_match or project_match
            ), f"Session {session} doesn't match filter criteria"
        assert next_token is None

    def test_list_sessions_for_user_with_projects_and_additional_filter(self):
        """
        Test list_sessions_for_user with project_ids and additional filter
        """
        additional_filter = Attr("state").eq("READY")
        result, next_token = sessions.list_sessions_for_user(
            "user1", project_ids=["project1"], filter_expression=additional_filter
        )

        assert result is not None
        for session in result:
            assert session.get("state") == "READY"
            assert (
                session.get(sessions.SESSION_DB_HASH_KEY) == "user1"
                or session.get("project", {}).get("project_id") == "project1"
            )
        assert next_token is None

    def test_list_sessions_paginated_empty_result(self):
        """
        Test list_sessions_paginated returns empty list when no sessions match filter
        """
        filter_expr = Attr("state").eq("NONEXISTENT_STATE")
        result, next_token = sessions.list_sessions_paginated(
            filter_expression=filter_expr
        )

        assert result == []
        assert next_token is None

    def test_list_sessions_for_user_empty_result(self):
        """
        Test list_sessions_for_user returns empty list when user has no sessions
        """
        result, next_token = sessions.list_sessions_for_user("nonexistent_user")

        assert result == []
        assert next_token is None

    def test_list_sessions_for_user_with_projects_empty_result(self):
        """
        Test list_sessions_for_user with project_ids returns empty list when no sessions found
        """
        result, next_token = sessions.list_sessions_for_user(
            "nonexistent_user", project_ids=["nonexistent_project"]
        )

        assert result == []
        assert next_token is None

    @patch("res.resources.accounts.is_active_admin")
    @patch("res.resources.sessions.list_sessions_paginated")
    @patch("res.resources.projects.list_user_manage_sessions_projects")
    def test_list_sessions_admin_no_filters(
        self, mock_list_projects, mock_list_paginated, mock_is_admin
    ):
        """Test list_sessions for admin with no filters"""
        mock_is_admin.return_value = True
        mock_list_paginated.return_value = ([], None)

        sessions.list_sessions(user="admin")

        mock_list_projects.assert_not_called()
        mock_list_paginated.assert_called_once()
        call_args = mock_list_paginated.call_args
        assert call_args.kwargs.get("filter_expression") is None

    @patch("res.resources.accounts.is_active_admin")
    @patch("res.resources.sessions.list_sessions_paginated")
    @patch("res.resources.projects.list_user_manage_sessions_projects")
    def test_list_sessions_admin_with_state_filter(
        self, mock_list_projects, mock_list_paginated, mock_is_admin
    ):
        """Test list_sessions for admin with state filter"""
        mock_is_admin.return_value = True
        mock_list_paginated.return_value = ([], None)

        sessions.list_sessions(user="admin", state="READY")

        mock_list_projects.assert_not_called()
        mock_list_paginated.assert_called_once()
        call_args = mock_list_paginated.call_args
        assert call_args.kwargs.get("filter_expression") == Attr("state").eq("READY")

    @patch("res.resources.accounts.is_active_admin")
    @patch("res.resources.sessions.list_sessions_paginated")
    @patch("res.resources.projects.list_user_manage_sessions_projects")
    def test_list_sessions_admin_with_base_os_linux_filter(
        self, mock_list_projects, mock_list_paginated, mock_is_admin
    ):
        """Test list_sessions for admin with base_os=linux filter"""
        mock_is_admin.return_value = True
        mock_list_paginated.return_value = ([], None)

        sessions.list_sessions(user="admin", base_os="linux")

        mock_list_projects.assert_not_called()
        mock_list_paginated.assert_called_once()
        call_args = mock_list_paginated.call_args
        assert call_args.kwargs.get("filter_expression") == Attr("base_os").ne(
            "windows"
        )

    @patch("res.resources.accounts.is_active_admin")
    @patch("res.resources.sessions.list_sessions_paginated")
    @patch("res.resources.projects.list_user_manage_sessions_projects")
    def test_list_sessions_admin_with_base_os_windows_filter(
        self, mock_list_projects, mock_list_paginated, mock_is_admin
    ):
        """Test list_sessions for admin with base_os=windows filter"""
        mock_is_admin.return_value = True
        mock_list_paginated.return_value = ([], None)

        sessions.list_sessions(user="admin", base_os="windows")

        mock_list_projects.assert_not_called()
        mock_list_paginated.assert_called_once()
        call_args = mock_list_paginated.call_args
        assert call_args.kwargs.get("filter_expression") == Attr("base_os").eq(
            "windows"
        )

    @patch("res.resources.accounts.is_active_admin")
    @patch("res.resources.sessions.list_sessions_paginated")
    @patch("res.resources.sessions.projects.list_user_manage_sessions_projects")
    def test_list_sessions_admin_with_session_name_filter(
        self, mock_list_projects, mock_list_paginated, mock_is_admin
    ):
        """Test list_sessions for admin with session_name filter"""
        mock_is_admin.return_value = True
        mock_list_paginated.return_value = ([], None)

        sessions.list_sessions(user="admin", session_name="test")

        mock_list_projects.assert_not_called()
        mock_list_paginated.assert_called_once()
        call_args = mock_list_paginated.call_args
        assert call_args.kwargs.get("filter_expression") == Attr("name").contains(
            "test"
        )

    @patch("res.resources.accounts.is_active_admin")
    @patch("res.resources.sessions.list_sessions_paginated")
    @patch("res.resources.sessions.projects.list_user_manage_sessions_projects")
    def test_list_sessions_admin_with_stack_id_filter(
        self, mock_list_projects, mock_list_paginated, mock_is_admin
    ):
        """Test list_sessions for admin with stack_id filter"""
        mock_is_admin.return_value = True
        mock_list_paginated.return_value = ([], None)

        sessions.list_sessions(user="admin", stack_id="stack123")

        mock_list_projects.assert_not_called()
        mock_list_paginated.assert_called_once()
        call_args = mock_list_paginated.call_args
        assert call_args.kwargs.get("filter_expression") == Attr(
            "software_stack.stack_id"
        ).eq("stack123")

    @patch("res.resources.accounts.is_active_admin")
    @patch("res.resources.sessions.list_sessions_paginated")
    @patch("res.resources.sessions.projects.list_user_manage_sessions_projects")
    def test_list_sessions_admin_with_date_range_filter(
        self, mock_list_projects, mock_list_paginated, mock_is_admin
    ):
        """Test list_sessions for admin with date range filter"""
        mock_is_admin.return_value = True
        mock_list_paginated.return_value = ([], None)

        sessions.list_sessions(
            user="admin", date_range_key="created_on", after="1000000", before="2000000"
        )

        mock_list_projects.assert_not_called()
        mock_list_paginated.assert_called_once()
        call_args = mock_list_paginated.call_args
        assert call_args.kwargs.get("filter_expression") == Attr("created_on").between(
            1000000, 2000000
        )

    @patch("res.resources.accounts.is_active_admin")
    @patch("res.resources.sessions.list_sessions_paginated")
    @patch("res.resources.sessions.projects.list_user_manage_sessions_projects")
    def test_list_sessions_admin_with_multiple_filters(
        self, mock_list_projects, mock_list_paginated, mock_is_admin
    ):
        """Test list_sessions for admin with multiple filters combined"""
        mock_is_admin.return_value = True
        mock_list_paginated.return_value = ([], None)

        sessions.list_sessions(
            user="admin",
            state="READY",
            base_os="linux",
            session_name="test",
            date_range_key="created_on",
            after="1000000",
            before="2000000",
        )

        mock_list_projects.assert_not_called()
        mock_list_paginated.assert_called_once()
        call_args = mock_list_paginated.call_args
        expected_filter = And(
            And(
                And(Attr("state").eq("READY"), Attr("base_os").ne("windows")),
                Attr("name").contains("test"),
            ),
            Attr("created_on").between(1000000, 2000000),
        )
        assert call_args.kwargs.get("filter_expression") == expected_filter

    @patch("res.resources.accounts.is_active_admin")
    @patch("res.resources.sessions.list_sessions_for_user")
    @patch("res.resources.sessions.projects.list_user_manage_sessions_projects")
    def test_list_sessions_non_admin_no_manage_projects(
        self, mock_list_projects, mock_list_for_user, mock_is_admin
    ):
        """Test list_sessions for non-admin without manage permissions"""
        mock_is_admin.return_value = False
        mock_list_projects.return_value = []
        mock_list_for_user.return_value = ([], None)

        sessions.list_sessions(user="user1")

        mock_list_projects.assert_called_once_with("user1")
        mock_list_for_user.assert_called_once()
        call_args = mock_list_for_user.call_args
        assert call_args.args[0] == "user1"
        assert call_args.kwargs.get("project_ids") == []
        assert call_args.kwargs.get("filter_expression") is None

    @patch("res.resources.accounts.is_active_admin")
    @patch("res.resources.sessions.list_sessions_for_user")
    @patch("res.resources.sessions.projects.list_user_manage_sessions_projects")
    def test_list_sessions_non_admin_with_manage_projects(
        self, mock_list_projects, mock_list_for_user, mock_is_admin
    ):
        """Test list_sessions for non-admin with manage permissions"""
        mock_is_admin.return_value = False
        mock_list_projects.return_value = ["project1"]
        mock_list_for_user.return_value = ([], None)

        sessions.list_sessions(user="user1")

        mock_list_projects.assert_called_once_with("user1")
        mock_list_for_user.assert_called_once()
        call_args = mock_list_for_user.call_args
        assert call_args.args[0] == "user1"
        assert call_args.kwargs.get("project_ids") == ["project1"]
        assert call_args.kwargs.get("filter_expression") is None

    @patch("res.resources.sessions.list_sessions_paginated")
    @patch("res.resources.accounts.is_active_admin")
    def test_list_sessions_with_owner_filter_as_admin(
        self, mock_is_admin, mock_list_paginated
    ):
        """Test list_sessions with owner filter for admin"""
        mock_is_admin.return_value = True
        mock_list_paginated.return_value = ([], None)
        sessions.list_sessions(user="admin", owner="user1")

        mock_list_paginated.assert_called_once()
        call_args = mock_list_paginated.call_args
        assert call_args.kwargs.get("filter_expression") == Attr("owner").eq("user1")

    @patch("res.resources.sessions.list_sessions_for_user")
    @patch("res.resources.sessions.projects.list_user_manage_sessions_projects")
    @patch("res.resources.accounts.is_active_admin")
    def test_list_sessions_with_owner_filter_as_non_admin(
        self, mock_is_admin, mock_list_projects, mock_list_for_user
    ):
        """Test list_sessions with owner filter for non-admin"""
        mock_is_admin.return_value = False
        mock_list_projects.return_value = []
        mock_list_for_user.return_value = ([], None)
        sessions.list_sessions(user="user1", owner="user2")

        mock_list_for_user.assert_called_once()
        call_args = mock_list_for_user.call_args
        assert call_args.kwargs.get("filter_expression") == Attr("owner").eq("user2")

    @patch("res.resources.cluster_settings.get_setting")
    def test_get_session_logins_both_enabled(self, mock_get_setting):
        """Test get_session_logins returns both SSO and Cognito when both enabled."""
        mock_get_setting.side_effect = [True, True]

        result = sessions.get_session_logins()

        assert len(result) == 2
        assert "SSO" in result
        assert "Native user" in result

    @patch("res.resources.cluster_settings.get_setting")
    def test_get_session_logins_only_sso(self, mock_get_setting):
        """Test get_session_logins returns only SSO when Cognito disabled."""
        mock_get_setting.side_effect = [True, False]

        result = sessions.get_session_logins()

        assert len(result) == 1
        assert "SSO" in result

    @patch("res.resources.cluster_settings.get_setting")
    def test_get_session_logins_only_cognito(self, mock_get_setting):
        """Test get_session_logins returns only Cognito when SSO disabled."""
        mock_get_setting.side_effect = [False, True]

        result = sessions.get_session_logins()

        assert len(result) == 1
        assert "Native user" in result

    @patch("res.resources.cluster_settings.get_setting")
    def test_get_session_logins_none_enabled(self, mock_get_setting):
        """Test get_session_logins returns empty list when both disabled."""
        mock_get_setting.side_effect = [False, False]

        result = sessions.get_session_logins()

        assert len(result) == 0

    def test_get_sessions_by_dcv_session_ids_returns_matching(self):
        result = sessions.get_sessions_by_dcv_session_ids(["dcv-aaa", "dcv-bbb"])

        assert len(result) == 2
        assert result["dcv-aaa"]["server"]["instance_id"] == "i-111"
        assert result["dcv-bbb"]["server"]["instance_id"] == "i-222"

    def test_get_sessions_by_dcv_session_ids_partial_match(self):
        result = sessions.get_sessions_by_dcv_session_ids(
            ["dcv-aaa", "dcv-nonexistent"]
        )

        assert len(result) == 1
        assert "dcv-aaa" in result
        assert "dcv-nonexistent" not in result

    def test_get_sessions_by_dcv_session_ids_no_matches(self):
        result = sessions.get_sessions_by_dcv_session_ids(["dcv-nonexistent"])

        assert result == {}

    def test_get_sessions_by_dcv_session_ids_empty_input(self):
        result = sessions.get_sessions_by_dcv_session_ids([])

        assert result == {}

    def test_group_sessions_by_os_linux(self):
        session_map = sessions.get_sessions_by_ids(["session4"])
        result, unsuccessful = sessions.group_sessions_by_os(session_map)

        assert "linux" in result
        assert len(result["linux"]) == 1
        assert result["linux"][0]["session_id"] == "session4"
        assert result["linux"][0]["instance_id"] == "i-111"
        assert len(unsuccessful) == 0

    def test_group_sessions_by_os_windows(self):
        session_map = sessions.get_sessions_by_ids(["session5"])
        result, unsuccessful = sessions.group_sessions_by_os(session_map)

        assert "windows" in result
        assert len(result["windows"]) == 1
        assert result["windows"][0]["session_id"] == "session5"
        assert len(unsuccessful) == 0

    def test_group_sessions_by_os_mixed(self):
        session_map = sessions.get_sessions_by_ids(["session4", "session5"])
        result, unsuccessful = sessions.group_sessions_by_os(session_map)

        assert len(result["linux"]) == 1
        assert len(result["windows"]) == 1
        assert len(unsuccessful) == 0

    def test_group_sessions_by_os_missing_session(self):
        # When the caller passes a None entry, group_sessions_by_os surfaces
        # it via unsuccessful_list rather than dropping it silently.
        result, unsuccessful = sessions.group_sessions_by_os({"nonexistent": None})

        assert result == {}
        assert len(unsuccessful) == 1
        assert "nonexistent" in unsuccessful[0]["failure_reason"]

    def test_group_sessions_by_os_empty_input(self):
        result, unsuccessful = sessions.group_sessions_by_os({})

        assert result == {}
        assert len(unsuccessful) == 0


class TestUpdateSession:
    """Test update_session function"""

    @patch("res.resources.sessions.ec2_utils.create_tag")
    @patch("res.resources.sessions.schedules.update_schedule_for_session")
    @patch("res.resources.sessions._update_session_record")
    def test_basic_session_update_name_description_only(
        self, mock_update_record, mock_update_schedule, mock_create_tag
    ):
        """Test updating session name and description without instance type change."""
        old_session = {
            sessions.SESSION_DB_NAME_KEY: "old-name",
            sessions.SESSION_DB_DESCRIPTION_KEY: "old-description",
            sessions.SESSION_DB_SERVER_KEY: {},
            sessions.SESSION_DB_HASH_KEY: "user1",
            sessions.SESSION_DB_STATE_KEY: "READY",
        }
        new_session = {
            sessions.SESSION_DB_NAME_KEY: "new-name",
            sessions.SESSION_DB_DESCRIPTION_KEY: "new-description",
            sessions.SESSION_DB_STATE_KEY: "READY",
            sessions.SESSION_DB_SERVER_KEY: {
                sessions.SESSION_DB_SERVER_NESTED_INSTANCE_ID_KEY: None
            },  # None instance_id to skip instance logic
        }

        mock_update_schedule.return_value = {
            sessions.SESSION_DB_NAME_KEY: "new-name",
            sessions.SESSION_DB_DESCRIPTION_KEY: "new-description",
            sessions.SESSION_DB_SERVER_KEY: {},
            sessions.SESSION_DB_HASH_KEY: "user1",
        }

        result = sessions.update_session(new_session, old_session)

        assert result[sessions.SESSION_DB_NAME_KEY] == "new-name"
        assert result[sessions.SESSION_DB_DESCRIPTION_KEY] == "new-description"
        mock_update_record.assert_called_once()
        mock_update_schedule.assert_called_once()

    @patch("res.resources.sessions.ec2_utils.create_tag")
    @patch("res.resources.sessions.ec2_utils.change_instance_type")
    @patch("res.resources.sessions.schedules.update_schedule_for_session")
    @patch("res.resources.sessions._update_session_record")
    def test_instance_type_change_success(
        self,
        mock_update_record,
        mock_update_schedule,
        mock_change_instance,
        mock_create_tag,
    ):
        """Test successful instance type change."""
        instance_id = "i-123456"
        old_session = {
            sessions.SESSION_DB_NAME_KEY: "test-session",
            sessions.SESSION_DB_DESCRIPTION_KEY: "test-desc",
            sessions.SESSION_DB_SERVER_KEY: {
                "instance_id": instance_id,
                "instance_type": "m5.large",
            },
            sessions.SESSION_DB_HASH_KEY: "user1",
            sessions.SESSION_DB_STATE_KEY: "READY",
        }
        new_session = {
            sessions.SESSION_DB_NAME_KEY: "test-session",
            sessions.SESSION_DB_DESCRIPTION_KEY: "test-desc",
            sessions.SESSION_DB_STATE_KEY: "READY",
            sessions.SESSION_DB_SERVER_KEY: {
                "instance_id": instance_id,
                "instance_type": "m5.xlarge",
            },
        }

        mock_update_schedule.return_value = {
            sessions.SESSION_DB_NAME_KEY: "test-session",
            sessions.SESSION_DB_DESCRIPTION_KEY: "test-desc",
            sessions.SESSION_DB_SERVER_KEY: {"instance_type": "m5.xlarge"},
        }

        result = sessions.update_session(new_session, old_session)

        mock_change_instance.assert_called_once_with(
            instance_id=instance_id, instance_type_name="m5.xlarge"
        )
        mock_update_record.assert_called_once()

    @patch("res.resources.sessions.ec2_utils.create_tag")
    @patch("res.resources.sessions.ec2_utils.change_instance_type")
    @patch("res.resources.sessions.schedules.update_schedule_for_session")
    @patch("res.resources.sessions._update_session_record")
    def test_instance_type_no_change_skips_ec2_call(
        self,
        mock_update_record,
        mock_update_schedule,
        mock_change_instance,
        mock_create_tag,
    ):
        """Test that no EC2 call is made when instance type hasn't changed."""
        instance_id = "i-123456"
        old_session = {
            sessions.SESSION_DB_NAME_KEY: "test-session",
            sessions.SESSION_DB_DESCRIPTION_KEY: "test-desc",
            sessions.SESSION_DB_SERVER_KEY: {
                "instance_id": instance_id,
                "instance_type": "m5.large",
            },
            sessions.SESSION_DB_HASH_KEY: "user1",
            sessions.SESSION_DB_STATE_KEY: "READY",
        }
        new_session = {
            sessions.SESSION_DB_NAME_KEY: "test-session",
            sessions.SESSION_DB_DESCRIPTION_KEY: "test-desc",
            sessions.SESSION_DB_STATE_KEY: "READY",
            sessions.SESSION_DB_SERVER_KEY: {
                "instance_id": instance_id,
                "instance_type": "m5.large",
            },
        }

        mock_update_schedule.return_value = old_session.copy()

        sessions.update_session(new_session, old_session)

        mock_change_instance.assert_not_called()

    @patch("res.resources.sessions.ec2_utils.create_tag")
    @patch("res.resources.sessions.schedules.update_schedule_for_session")
    @patch("res.resources.sessions._update_session_record")
    def test_no_changes_does_not_update_record(
        self, mock_update_record, mock_update_schedule, mock_create_tag
    ):
        """Test that no update is performed when session data hasn't changed."""
        old_session = {
            sessions.SESSION_DB_NAME_KEY: "same-name",
            sessions.SESSION_DB_DESCRIPTION_KEY: "same-desc",
            sessions.SESSION_DB_SERVER_KEY: {"instance_type": "m5.large"},
            sessions.SESSION_DB_HASH_KEY: "user1",
            sessions.SESSION_DB_STATE_KEY: "READY",
        }
        new_session = {
            sessions.SESSION_DB_NAME_KEY: "same-name",
            sessions.SESSION_DB_DESCRIPTION_KEY: "same-desc",
            sessions.SESSION_DB_STATE_KEY: "READY",
            sessions.SESSION_DB_SERVER_KEY: {
                sessions.SESSION_DB_SERVER_NESTED_INSTANCE_ID_KEY: None
            },
        }

        mock_update_schedule.return_value = old_session.copy()

        result = sessions.update_session(new_session, old_session)

        mock_update_record.assert_not_called()
        assert result[sessions.SESSION_DB_NAME_KEY] == "same-name"

    @patch("res.resources.sessions.ec2_utils.create_tag")
    @patch("res.resources.sessions.schedules.update_schedule_for_session")
    @patch("res.resources.sessions._update_session_record")
    def test_schedule_only_update(
        self, mock_update_record, mock_update_schedule, mock_create_tag
    ):
        """Test that schedule-only changes trigger an update."""
        old_session = {
            sessions.SESSION_DB_NAME_KEY: "test-session",
            sessions.SESSION_DB_DESCRIPTION_KEY: "test-desc",
            sessions.SESSION_DB_SERVER_KEY: {"instance_type": "m5.large"},
            sessions.SESSION_DB_HASH_KEY: "user1",
            sessions.SESSION_DB_STATE_KEY: "READY",
            "monday_schedule": {"schedule_type": "NO_SCHEDULE"},
        }
        new_session = {
            sessions.SESSION_DB_NAME_KEY: "test-session",
            sessions.SESSION_DB_DESCRIPTION_KEY: "test-desc",
            sessions.SESSION_DB_STATE_KEY: "READY",
            sessions.SESSION_DB_SERVER_KEY: {
                sessions.SESSION_DB_SERVER_NESTED_INSTANCE_ID_KEY: None
            },
            "monday_schedule": {"schedule_type": "WORKING_HOURS"},
        }

        updated = old_session.copy()
        updated["monday_schedule"] = {"schedule_type": "WORKING_HOURS"}
        mock_update_schedule.return_value = updated

        result = sessions.update_session(new_session, old_session)

        mock_update_schedule.assert_called_once()
        mock_update_record.assert_called_once()
        assert result["monday_schedule"]["schedule_type"] == "WORKING_HOURS"


class TestUpdateSessionState(unittest.TestCase):
    @patch("res.resources.sessions.table_utils.update_item")
    @patch("res.resources.sessions.get_session")
    def test_no_publish_uses_table_utils(self, mock_get_session, mock_update_item):
        """publish_event=False (default): direct DDB update, no get_session, no event publish."""
        mock_update_item.return_value = {sessions.SESSION_DB_STATE_KEY: "READY"}

        result = sessions.update_session_state(
            owner=TEST_OWNER, session_id=TEST_SESSION_ID, state="READY"
        )

        mock_get_session.assert_not_called()
        mock_update_item.assert_called_once()
        kwargs = mock_update_item.call_args.kwargs
        assert kwargs["item"][sessions.SESSION_DB_STATE_KEY] == "READY"
        assert sessions.SESSION_DB_UPDATED_ON_KEY in kwargs["item"]
        assert result == {sessions.SESSION_DB_STATE_KEY: "READY"}

    @patch("res.resources.sessions._update_session_record")
    @patch("res.resources.sessions.get_session")
    def test_publish_event_fetches_old_and_publishes(
        self, mock_get_session, mock_update_record
    ):
        """publish_event=True: fetch old session, merge state, call _update_session_record with publish."""
        old_session = {
            sessions.SESSION_DB_HASH_KEY: TEST_OWNER,
            sessions.SESSION_DB_RANGE_KEY: TEST_SESSION_ID,
            sessions.SESSION_DB_STATE_KEY: "CREATING",
        }
        mock_get_session.return_value = old_session
        mock_update_record.return_value = {
            **old_session,
            sessions.SESSION_DB_STATE_KEY: "READY",
        }

        result = sessions.update_session_state(
            owner=TEST_OWNER,
            session_id=TEST_SESSION_ID,
            state="READY",
            publish_event=True,
        )

        mock_get_session.assert_called_once_with(
            owner=TEST_OWNER, session_id=TEST_SESSION_ID
        )
        mock_update_record.assert_called_once()
        call_kwargs = mock_update_record.call_args.kwargs
        # First positional is the new_session dict
        new_session_arg = mock_update_record.call_args.args[0]
        assert new_session_arg[sessions.SESSION_DB_STATE_KEY] == "READY"
        # old_session preserved (unchanged) for diff in event publish
        assert call_kwargs["old_session"] is old_session
        assert call_kwargs["publish_event"] is True
        assert result[sessions.SESSION_DB_STATE_KEY] == "READY"

    @patch("res.resources.sessions._update_session_record")
    @patch("res.resources.sessions.get_session")
    def test_publish_event_propagates_get_session_failure(
        self, mock_get_session, mock_update_record
    ):
        """publish_event=True: if get_session raises, the error propagates and no update happens."""
        mock_get_session.side_effect = exceptions.UserSessionNotFound("not found")

        with pytest.raises(exceptions.UserSessionNotFound):
            sessions.update_session_state(
                owner=TEST_OWNER,
                session_id=TEST_SESSION_ID,
                state="READY",
                publish_event=True,
            )

        mock_update_record.assert_not_called()


class TestGetSessionConnection(unittest.TestCase):

    @patch("res.resources.sessions.cluster_settings.get_setting")
    @patch(
        "res.clients.dcv_session_manager.dcv_session_manager_client.get_session_connection_data"
    )
    def test_returns_connection_with_custom_dns_endpoint(
        self, mock_get_connection, mock_get_setting
    ):
        mock_get_connection.return_value = {
            "idea_session_id": "session-1",
            "idea_session_owner": "user1",
            "username": "user1",
            "web_url_path": "/",
            "access_token": "test-token",
        }
        mock_get_setting.side_effect = lambda key: (
            "custom.example.com" if key == sessions.CUSTOM_DNS_NAME_KEY else None
        )

        result = sessions.get_session_connection("session-1", "user1", "user1")

        assert result["idea-session-id"] == "session-1"
        assert result["idea-session-owner"] == "user1"
        assert result["endpoint"] == "https://custom.example.com"
        assert result["web-url-path"] == "/"
        assert result["access-token"] == "test-token"

    @patch("res.resources.sessions.cluster_settings.get_setting")
    @patch(
        "res.clients.dcv_session_manager.dcv_session_manager_client.get_session_connection_data"
    )
    def test_returns_connection_with_nlb_endpoint_when_no_custom_dns(
        self, mock_get_connection, mock_get_setting
    ):
        mock_get_connection.return_value = {
            "idea_session_id": "session-1",
            "idea_session_owner": "user1",
            "username": "user1",
            "web_url_path": "/",
            "access_token": "test-token",
        }
        mock_get_setting.side_effect = lambda key: (
            "nlb.example.com" if key == sessions.EXTERNAL_NLB_DNS_NAME_KEY else None
        )

        result = sessions.get_session_connection("session-1", "user1", "user1")

        assert result["endpoint"] == "https://nlb.example.com"

    @patch("res.resources.sessions.cluster_settings.get_setting")
    @patch(
        "res.clients.dcv_session_manager.dcv_session_manager_client.get_session_connection_data"
    )
    def test_custom_dns_takes_precedence_over_nlb(
        self, mock_get_connection, mock_get_setting
    ):
        mock_get_connection.return_value = {
            "idea_session_id": "session-1",
            "idea_session_owner": "user1",
            "username": "user1",
            "web_url_path": "/",
            "access_token": "test-token",
        }

        def setting_lookup(key):
            if key == sessions.CUSTOM_DNS_NAME_KEY:
                return "custom.example.com"
            if key == sessions.EXTERNAL_NLB_DNS_NAME_KEY:
                return "nlb.example.com"
            return None

        mock_get_setting.side_effect = setting_lookup

        result = sessions.get_session_connection("session-1", "user1", "user1")

        assert result["endpoint"] == "https://custom.example.com"

    @patch("res.resources.sessions.cluster_settings.get_setting")
    @patch(
        "res.clients.dcv_session_manager.dcv_session_manager_client.get_session_connection_data"
    )
    def test_raises_when_no_endpoint_configured(
        self, mock_get_connection, mock_get_setting
    ):
        mock_get_connection.return_value = {
            "idea_session_id": "session-1",
            "idea_session_owner": "user1",
            "username": "user1",
            "web_url_path": "/",
            "access_token": "test-token",
        }
        mock_get_setting.return_value = None

        with pytest.raises(
            exceptions.SettingNotFound,
            match="No connection gateway endpoint configured",
        ):
            sessions.get_session_connection("session-1", "user1", "user1")

    @patch("res.resources.sessions.cluster_settings.get_setting")
    @patch(
        "res.clients.dcv_session_manager.dcv_session_manager_client.get_session_connection_data"
    )
    def test_passes_correct_params_to_dcv_client(
        self, mock_get_connection, mock_get_setting
    ):
        mock_get_connection.return_value = {
            "idea_session_id": "session-1",
            "idea_session_owner": "user1",
            "username": "user1",
            "web_url_path": "/",
            "access_token": "test-token",
        }
        mock_get_setting.side_effect = lambda key: (
            "custom.example.com" if key == sessions.CUSTOM_DNS_NAME_KEY else None
        )

        sessions.get_session_connection("session-1", "user1", "user1")

        mock_get_connection.assert_called_once_with(
            session_id="session-1", username="user1"
        )

    @patch("res.resources.sessions.cluster_settings.get_setting")
    @patch(
        "res.clients.dcv_session_manager.dcv_session_manager_client.get_session_connection_data"
    )
    def test_shared_user_token_issued_under_connecting_username(
        self, mock_get_connection, mock_get_setting
    ):
        """A non-owner connecting to a shared session must get a DCV token under their own username."""
        mock_get_connection.return_value = {
            "idea_session_id": "session-1",
            "idea_session_owner": "owner_user",
            "username": "shared_user",
            "web_url_path": "/",
            "access_token": "shared-user-token",
        }
        mock_get_setting.side_effect = lambda key: (
            "custom.example.com" if key == sessions.CUSTOM_DNS_NAME_KEY else None
        )

        result = sessions.get_session_connection(
            "session-1", "owner_user", "shared_user"
        )

        # DCV token is requested for the connecting user, not the owner
        mock_get_connection.assert_called_once_with(
            session_id="session-1", username="shared_user"
        )
        assert result["idea-session-owner"] == "owner_user"
