#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import unittest
from unittest.mock import patch

import pytest

from idea.dcv_session_management.api.controllers import sessions_controller
from res.app.exceptions import ForbiddenException  # type: ignore
from res.exceptions import SessionAccessDenied  # type: ignore

TEST_SESSION_ID = "267afc1c-83ef-4735-92a9-03bfecbb97d8"
TEST_OWNER = "sessionowner"
TEST_USER = "testuser"
TEST_IDEA_SESSION_ID = "idea-sess-001"
TEST_SESSION = {"owner": TEST_OWNER, "dcv_session_id": TEST_SESSION_ID, "idea_session_id": TEST_IDEA_SESSION_ID}
TEST_CONNECTION_DATA = {
    "connectionToken": "dGVzdC1yYW5kb20tYmVhcmVyLXRva2VuLXZhbHVl",
    "webUrlPath": "/",
}


class TestGetSessionConnectionData(unittest.TestCase):

    @patch.object(sessions_controller, "session_connection_data")
    @patch.object(sessions_controller, "session_permissions")
    def test_success_as_owner(self, mock_perms, mock_scd):
        mock_perms.validate_session_access.return_value = {**TEST_SESSION, "owner": TEST_OWNER}
        mock_scd.get_session_connection_data.return_value = TEST_CONNECTION_DATA

        result = sessions_controller.get_session_connection_data(TEST_SESSION_ID, TEST_OWNER)
        assert result.session.id == TEST_SESSION_ID
        assert result.session.owner == TEST_OWNER
        assert result.session.server.web_url_path == "/"
        assert result.connection_token == TEST_CONNECTION_DATA["connectionToken"]

    @patch.object(sessions_controller, "session_connection_data")
    @patch.object(sessions_controller, "session_permissions")
    def test_success_as_shared_user(self, mock_perms, mock_scd):
        mock_perms.validate_session_access.return_value = TEST_SESSION
        mock_scd.get_session_connection_data.return_value = TEST_CONNECTION_DATA

        result = sessions_controller.get_session_connection_data(TEST_SESSION_ID, TEST_USER)
        assert result.session.id == TEST_SESSION_ID
        assert result.session.owner == TEST_OWNER
        assert result.connection_token == TEST_CONNECTION_DATA["connectionToken"]
        mock_perms.validate_session_access.assert_called_once_with(
            TEST_SESSION_ID, TEST_USER
        )
        mock_scd.get_session_connection_data.assert_called_once_with(
            TEST_SESSION_ID, TEST_USER
        )

    @patch.object(sessions_controller, "session_permissions")
    def test_session_not_found_raises_forbidden(self, mock_perms):
        mock_perms.validate_session_access.side_effect = SessionAccessDenied("not found")

        with pytest.raises(ForbiddenException):
            sessions_controller.get_session_connection_data(TEST_SESSION_ID, TEST_USER)

    @patch.object(sessions_controller, "session_permissions")
    def test_unauthorized_user_raises_forbidden(self, mock_perms):
        mock_perms.validate_session_access.side_effect = SessionAccessDenied("access denied")

        with pytest.raises(ForbiddenException):
            sessions_controller.get_session_connection_data(TEST_SESSION_ID, TEST_USER)

    @patch.object(sessions_controller, "session_connection_data")
    @patch.object(sessions_controller, "session_permissions")
    def test_internal_error_propagates(self, mock_perms, mock_scd):
        """Unexpected exceptions propagate — the ASGI app's catch-all handler returns 500."""
        mock_perms.validate_session_access.return_value = {**TEST_SESSION, "owner": TEST_OWNER}
        mock_scd.get_session_connection_data.side_effect = RuntimeError("DDB error")

        with pytest.raises(RuntimeError):
            sessions_controller.get_session_connection_data(TEST_SESSION_ID, TEST_OWNER)
