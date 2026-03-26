#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import unittest
from typing import Dict, Optional
from unittest.mock import patch

import pytest
import res as res
import res.exceptions as exceptions
from boto3.dynamodb.conditions import And, Attr
from res.resources import sessions
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
