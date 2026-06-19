#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import pytest
from unittest.mock import patch

from idea.dcv_session_management.api.controllers import sessions_controller
from res.resources import session_permissions
from res.exceptions import SessionAccessDenied

from datamodel.models.get_session_screenshots_response_content import (
    GetSessionScreenshotsResponseContent,
)
from datamodel.models.dcv_session_management.describe_sessions_response_content import (
    DescribeSessionsResponseContent,
)
from datamodel.models.dcv_session_management.update_session_permissions_response_content import (
    UpdateSessionPermissionsResponseContent,
)


SESSION_ID_1 = "ses-111"
SESSION_ID_2 = "ses-222"
OWNER_1 = "user1"
OWNER_2 = "user2"
PERMISSIONS_FILE_B64 = "cGVybWlzc2lvbnM="
DCV_OUTPUT = {
    "format": "png",
    "base64": "iVBOR...",
    "created_on": 1712345678000,
    "primary": True,
}


class TestSessionsController:
    """SessionsController unit test stubs"""

    def _get_screenshots_body(self, session_ids=None, requester=OWNER_1):
        if session_ids is None:
            session_ids = [SESSION_ID_1]
        return {
            "requester": requester,
            "sessions": [{"session_id": sid} for sid in session_ids],
        }

    @patch.object(sessions_controller, "session_permissions")
    @patch.object(sessions_controller, "session_screenshots")
    def test_get_session_screenshots_success(self, mock_ss, mock_perms):
        mock_perms.validate_session_access.return_value = {"owner": OWNER_1}
        mock_ss.get_session_screenshots.return_value = (
            [
                {
                    "session_id": SESSION_ID_1,
                    "images": [DCV_OUTPUT],
                }
            ],
            [],
        )

        body = self._get_screenshots_body()
        result = sessions_controller.get_session_screenshots(body)

        assert isinstance(result, GetSessionScreenshotsResponseContent)
        assert len(result.successful_list) == 1
        assert len(result.unsuccessful_list) == 0
        assert result.successful_list[0].session_screenshot.session_id == SESSION_ID_1
        mock_perms.validate_session_access.assert_called_once_with(SESSION_ID_1, OWNER_1)
        mock_ss.get_session_screenshots.assert_called_once_with([SESSION_ID_1])

    @patch.object(sessions_controller, "session_permissions")
    @patch.object(sessions_controller, "session_screenshots")
    def test_get_session_screenshots_all_failed(self, mock_ss, mock_perms):
        mock_perms.validate_session_access.return_value = {"owner": OWNER_1}
        mock_ss.get_session_screenshots.return_value = (
            [],
            [{"session_id": SESSION_ID_1, "failure_reason": "Session not found"}],
        )

        body = self._get_screenshots_body()
        result = sessions_controller.get_session_screenshots(body)

        assert isinstance(result, GetSessionScreenshotsResponseContent)
        assert len(result.successful_list) == 0
        assert len(result.unsuccessful_list) == 1
        assert (
            result.unsuccessful_list[0].get_session_screenshot_request_data.session_id
            == SESSION_ID_1
        )
        assert result.unsuccessful_list[0].failure_reason == "Session not found"

    @patch.object(sessions_controller, "session_permissions")
    @patch.object(sessions_controller, "session_screenshots")
    def test_get_session_screenshots_mixed_results(self, mock_ss, mock_perms):
        mock_perms.validate_session_access.return_value = {"owner": OWNER_1}
        mock_ss.get_session_screenshots.return_value = (
            [
                {
                    "session_id": SESSION_ID_1,
                    "images": [DCV_OUTPUT],
                }
            ],
            [{"session_id": SESSION_ID_2, "failure_reason": "Timed out"}],
        )

        body = self._get_screenshots_body([SESSION_ID_1, SESSION_ID_2])
        result = sessions_controller.get_session_screenshots(body)

        assert isinstance(result, GetSessionScreenshotsResponseContent)
        assert len(result.successful_list) == 1
        assert len(result.unsuccessful_list) == 1
        assert result.successful_list[0].session_screenshot.session_id == SESSION_ID_1
        assert (
            result.unsuccessful_list[0].get_session_screenshot_request_data.session_id
            == SESSION_ID_2
        )

    @patch.object(sessions_controller, "session_permissions")
    @patch.object(sessions_controller, "session_screenshots")
    def test_get_session_screenshots_multiple_sessions(self, mock_ss, mock_perms):
        mock_perms.validate_session_access.return_value = {"owner": OWNER_1}
        mock_ss.get_session_screenshots.return_value = (
            [
                {"session_id": SESSION_ID_1, "images": [DCV_OUTPUT]},
                {"session_id": SESSION_ID_2, "images": [DCV_OUTPUT]},
            ],
            [],
        )

        body = self._get_screenshots_body([SESSION_ID_1, SESSION_ID_2])
        result = sessions_controller.get_session_screenshots(body)

        assert isinstance(result, GetSessionScreenshotsResponseContent)
        assert len(result.successful_list) == 2
        assert len(result.unsuccessful_list) == 0

    @patch.object(sessions_controller.session_permissions, "validate_session_access")
    @patch.object(sessions_controller, "session_screenshots")
    def test_get_session_screenshots_unauthorized_session_skipped(self, mock_ss, mock_validate):

        def access_side_effect(session_id, username):
            if session_id == SESSION_ID_2:
                raise SessionAccessDenied("denied")
            return {"owner": OWNER_1}

        mock_validate.side_effect = access_side_effect
        mock_ss.get_session_screenshots.return_value = (
            [{"session_id": SESSION_ID_1, "images": [DCV_OUTPUT]}],
            [],
        )

        body = self._get_screenshots_body([SESSION_ID_1, SESSION_ID_2], requester=OWNER_1)
        result = sessions_controller.get_session_screenshots(body)

        mock_ss.get_session_screenshots.assert_called_once_with([SESSION_ID_1])
        assert len(result.successful_list) == 1
        assert len(result.unsuccessful_list) == 1
        unauthorized = result.unsuccessful_list[0]
        assert unauthorized.get_session_screenshot_request_data.session_id == SESSION_ID_2
        assert unauthorized.failure_reason == session_permissions.ACCESS_DENIED_MSG

    @patch.object(sessions_controller.session_permissions, "validate_session_access")
    @patch.object(sessions_controller, "session_screenshots")
    def test_get_session_screenshots_all_unauthorized_skips_dcv_call(self, mock_ss, mock_validate):

        mock_validate.side_effect = SessionAccessDenied("denied")
        mock_ss.get_session_screenshots.return_value = ([], [])

        body = self._get_screenshots_body([SESSION_ID_1], requester=OWNER_2)
        result = sessions_controller.get_session_screenshots(body)

        mock_ss.get_session_screenshots.assert_called_once_with([])
        assert result.successful_list == []
        assert len(result.unsuccessful_list) == 1
        assert result.unsuccessful_list[0].failure_reason == session_permissions.ACCESS_DENIED_MSG


class TestExternalAuthController:

    @patch.object(sessions_controller, "external_auth_service")
    def test_returns_yes_on_valid_token(self, mock_service):
        mock_service.validate_connection_token.return_value = ("testuser", None)

        result = sessions_controller.external_auth(
            {"authentication_token": "valid-token", "session_id": "console"}, "ses-1"
        )
        assert result == {"result": "yes", "username": "testuser"}
        mock_service.validate_connection_token.assert_called_once_with("valid-token", "ses-1")

    @patch.object(sessions_controller, "external_auth_service")
    def test_returns_no_on_error(self, mock_service):
        mock_service.validate_connection_token.return_value = (None, "Authentication failed")

        result = sessions_controller.external_auth(
            {"authentication_token": "expired-token", "session_id": "console"}, "ses-1"
        )
        assert result == {"result": "no", "message": "Authentication failed"}
        mock_service.validate_connection_token.assert_called_once_with("expired-token", "ses-1")

    @patch.object(sessions_controller, "external_auth_service")
    def test_returns_no_on_unexpected_exception(self, mock_service):
        mock_service.validate_connection_token.side_effect = RuntimeError("unexpected")

        result = sessions_controller.external_auth(
            {"authentication_token": "token", "session_id": "console"}, "ses-1"
        )
        assert result == {"result": "no", "message": "Authentication failed"}
        mock_service.validate_connection_token.assert_called_once_with("token", "ses-1")


class TestUpdateSessionPermissionsController:

    def _get_permissions_body(self, sessions=None):
        if sessions is None:
            sessions = [
                {"session_id": SESSION_ID_1, "owner": OWNER_1, "permissions_file": PERMISSIONS_FILE_B64}
            ]
        return {"sessions": sessions}

    @patch.object(sessions_controller, "dcv_session_permissions")
    def test_update_session_permissions_success(self, mock_sp):
        mock_sp.update_session_permissions.return_value = (
            [{"session_id": SESSION_ID_1}],
            [],
        )

        body = self._get_permissions_body()
        result = sessions_controller.update_session_permissions(body)

        assert isinstance(result, UpdateSessionPermissionsResponseContent)
        assert len(result.successful_list) == 1
        assert len(result.unsuccessful_list) == 0
        assert result.successful_list[0].session_id == SESSION_ID_1

    @patch.object(sessions_controller, "dcv_session_permissions")
    def test_update_session_permissions_all_failed(self, mock_sp):
        mock_sp.update_session_permissions.return_value = (
            [],
            [{"session_id": SESSION_ID_1, "failure_reason": "Session not found"}],
        )

        body = self._get_permissions_body()
        result = sessions_controller.update_session_permissions(body)

        assert isinstance(result, UpdateSessionPermissionsResponseContent)
        assert len(result.successful_list) == 0
        assert len(result.unsuccessful_list) == 1
        assert result.unsuccessful_list[0].session_id == SESSION_ID_1
        assert result.unsuccessful_list[0].failure_reason == "Session not found"

    @patch.object(sessions_controller, "dcv_session_permissions")
    def test_update_session_permissions_mixed_results(self, mock_sp):
        mock_sp.update_session_permissions.return_value = (
            [{"session_id": SESSION_ID_1}],
            [{"session_id": SESSION_ID_2, "failure_reason": "No instance_id found"}],
        )

        body = self._get_permissions_body([
            {"session_id": SESSION_ID_1, "owner": OWNER_1, "permissions_file": PERMISSIONS_FILE_B64},
            {"session_id": SESSION_ID_2, "owner": OWNER_1, "permissions_file": PERMISSIONS_FILE_B64},
        ])
        result = sessions_controller.update_session_permissions(body)

        assert isinstance(result, UpdateSessionPermissionsResponseContent)
        assert len(result.successful_list) == 1
        assert len(result.unsuccessful_list) == 1
        assert result.successful_list[0].session_id == SESSION_ID_1
        assert result.unsuccessful_list[0].session_id == SESSION_ID_2

    @patch.object(sessions_controller, "dcv_session_permissions")
    def test_update_session_permissions_empty_request(self, mock_sp):
        """Test that an empty sessions list raises ValueError from the model."""

        body = self._get_permissions_body([])
        with pytest.raises(ValueError, match="must be greater than or equal to"):
            sessions_controller.update_session_permissions(body)

    @patch.object(sessions_controller, "dcv_session_permissions")
    def test_update_session_permissions_invalid_base64_rejected(self, mock_sp):
        """Test that invalid base64 is caught at the controller level."""
        body = self._get_permissions_body([
            {"session_id": SESSION_ID_1, "owner": OWNER_1, "permissions_file": '; rm -rf / ; echo "'},
        ])
        result = sessions_controller.update_session_permissions(body)

        assert isinstance(result, UpdateSessionPermissionsResponseContent)
        assert len(result.successful_list) == 0
        assert len(result.unsuccessful_list) == 1
        assert "invalid base64 characters" in result.unsuccessful_list[0].failure_reason
        mock_sp.update_session_permissions.assert_not_called()


class TestDescribeSessionsController:

    def _get_describe_body(self, sessions=None):
        if sessions is None:
            sessions = [{"session_id": SESSION_ID_1, "owner": OWNER_1}]
        return {"sessions": sessions}

    @patch.object(sessions_controller, "dcv_sessions")
    @patch.object(sessions_controller, "sessions")
    def test_describe_sessions_success(self, mock_sessions, mock_ds):
        ddb_session = {
            "owner": OWNER_1,
            "idea_session_id": SESSION_ID_1,
            "server": {"instance_id": "i-aaa"},
        }
        mock_sessions.get_session.return_value = ddb_session
        mock_ds.describe_sessions.return_value = (
            [{"session_id": SESSION_ID_1, "num_of_connections": 3}],
            [],
        )

        body = self._get_describe_body()
        result = sessions_controller.describe_sessions(body)

        assert isinstance(result, DescribeSessionsResponseContent)
        assert len(result.successful_list) == 1
        assert len(result.unsuccessful_list) == 0
        assert result.successful_list[0].session_id == SESSION_ID_1
        assert result.successful_list[0].num_of_connections == 3
        mock_sessions.get_session.assert_called_once_with(
            owner=OWNER_1, session_id=SESSION_ID_1
        )
        mock_ds.describe_sessions.assert_called_once_with(
            {SESSION_ID_1: ddb_session}
        )

    @patch.object(sessions_controller, "dcv_sessions")
    @patch.object(sessions_controller, "sessions")
    def test_describe_sessions_all_failed(self, mock_sessions, mock_ds):
        mock_sessions.get_session.return_value = {
            "owner": OWNER_1,
            "idea_session_id": SESSION_ID_1,
            "server": {"instance_id": "i-aaa"},
        }
        mock_ds.describe_sessions.return_value = (
            [],
            [{"session_id": SESSION_ID_1, "failure_reason": "instance unreachable"}],
        )

        body = self._get_describe_body()
        result = sessions_controller.describe_sessions(body)

        assert isinstance(result, DescribeSessionsResponseContent)
        assert len(result.successful_list) == 0
        assert len(result.unsuccessful_list) == 1
        assert result.unsuccessful_list[0].session_id == SESSION_ID_1
        assert result.unsuccessful_list[0].failure_reason == "instance unreachable"

    @patch.object(sessions_controller, "dcv_sessions")
    @patch.object(sessions_controller, "UserSessionNotFound", new=Exception)
    @patch.object(sessions_controller, "sessions")
    def test_describe_sessions_session_not_found_passes_none(
        self, mock_sessions, mock_ds
    ):
        """When a session is not in DDB, the controller passes None in the session_map."""
        mock_sessions.get_session.side_effect = Exception("not found")
        mock_ds.describe_sessions.return_value = (
            [],
            [{"session_id": SESSION_ID_1, "failure_reason": "User session not found"}],
        )

        body = self._get_describe_body()
        result = sessions_controller.describe_sessions(body)

        assert len(result.unsuccessful_list) == 1
        mock_ds.describe_sessions.assert_called_once_with({SESSION_ID_1: None})

    @patch.object(sessions_controller, "dcv_sessions")
    @patch.object(sessions_controller, "sessions")
    def test_describe_sessions_mixed_results(self, mock_sessions, mock_ds):
        found = {
            "owner": OWNER_1,
            "idea_session_id": SESSION_ID_1,
            "server": {"instance_id": "i-aaa"},
        }

        def fake_get_session(owner, session_id):
            if session_id == SESSION_ID_1:
                return found
            raise sessions_controller.UserSessionNotFound("not found")

        mock_sessions.get_session.side_effect = fake_get_session
        mock_ds.describe_sessions.return_value = (
            [{"session_id": SESSION_ID_1, "num_of_connections": 0}],
            [{"session_id": SESSION_ID_2, "failure_reason": "Timed out"}],
        )

        body = self._get_describe_body([
            {"session_id": SESSION_ID_1, "owner": OWNER_1},
            {"session_id": SESSION_ID_2, "owner": OWNER_1},
        ])
        result = sessions_controller.describe_sessions(body)

        assert isinstance(result, DescribeSessionsResponseContent)
        assert len(result.successful_list) == 1
        assert len(result.unsuccessful_list) == 1
        assert result.successful_list[0].session_id == SESSION_ID_1
        assert result.successful_list[0].num_of_connections == 0
        assert result.unsuccessful_list[0].session_id == SESSION_ID_2

    @patch.object(sessions_controller, "dcv_sessions")
    def test_describe_sessions_empty_request(self, mock_ds):
        """Test that an empty sessions list raises ValueError from the model."""

        body = self._get_describe_body([])
        with pytest.raises(ValueError, match="must be greater than or equal to"):
            sessions_controller.describe_sessions(body)
        mock_ds.describe_sessions.assert_not_called()
