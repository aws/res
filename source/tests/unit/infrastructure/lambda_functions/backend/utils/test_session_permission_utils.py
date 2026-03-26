#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import sys
from unittest.mock import patch, MagicMock
import pytest
from botocore.exceptions import ClientError

# Add the backend directory to Python path to match utils import context
backend_path = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "../../../../../idea/backend",
    )
)
sys.path.insert(0, backend_path)

from api.utils import session_permission_utils


class TestSessionPermissionUtils:
    """Test class for session_permission_utils module."""

    @patch("api.utils.session_permission_utils._validate_actors_for_session_permission_requests")
    @patch("api.utils.session_permission_utils._validate_session_for_session_permission_request")
    @patch("api.utils.session_permission_utils.sessions.get_session_if_owner")
    def test_validate_update_session_permission_request_success(
        self, mock_get_session, mock_validate_session, mock_validate_actors
    ):
        """Test validate_update_session_permission_request returns True for valid request."""
        # Setup
        mock_permission = MagicMock()
        mock_permission.idea_session_owner = "user1"
        mock_permission.idea_session_id = "session-123"

        request = MagicMock()
        request.create = [mock_permission]
        request.update = []
        request.delete = []

        mock_get_session.return_value = {
            "session_id": "session-123",
            "base_os": "amazonlinux2",
        }
        mock_validate_session.return_value = (True, "")
        mock_validate_actors.return_value = (True, "")

        # Test
        is_valid, result_request = (
            session_permission_utils.validate_update_session_permission_request(request)
        )

        # Assertions
        assert is_valid is True
        assert result_request == request

    @patch("api.utils.session_permission_utils.sessions.get_session_if_owner")
    @patch(
        "api.utils.session_permission_utils._validate_session_for_session_permission_request"
    )
    def test_validate_update_session_permission_request_invalid_session(
        self, mock_validate_session, mock_get_session
    ):
        """Test validate_update_session_permission_request returns False for invalid session."""
        # Setup
        mock_permission = MagicMock()
        mock_permission.idea_session_owner = "user1"
        mock_permission.idea_session_id = "session-123"

        request = MagicMock()
        request.create = [mock_permission]
        request.update = []
        request.delete = []

        mock_get_session.return_value = None
        mock_validate_session.return_value = (False, "Invalid session")

        # Test
        is_valid, result_request = (
            session_permission_utils.validate_update_session_permission_request(request)
        )

        # Assertions
        assert is_valid is False
        assert mock_permission.failure_reason == "Invalid session"

    def test_validate_actors_for_session_permission_requests_success(self):
        """Test _validate_actors_for_session_permission_requests returns True for unique actors."""
        # Setup
        permission1 = MagicMock()
        permission1.actor_name = "user1"
        permission2 = MagicMock()
        permission2.actor_name = "user2"

        # Test
        is_valid, message = (
            session_permission_utils._validate_actors_for_session_permission_requests(
                [permission1, permission2]
            )
        )

        # Assertions
        assert is_valid is True
        assert message == ""

    def test_validate_actors_for_session_permission_requests_duplicate_actors(self):
        """Test _validate_actors_for_session_permission_requests returns False for duplicate actors."""
        # Setup
        permission1 = MagicMock()
        permission1.actor_name = "user1"
        permission2 = MagicMock()
        permission2.actor_name = "user1"

        # Test
        is_valid, message = (
            session_permission_utils._validate_actors_for_session_permission_requests(
                [permission1, permission2]
            )
        )

        # Assertions
        assert is_valid is False
        assert "actors: {'user1'} not unique" in message

    def test_validate_actors_for_session_permission_requests_empty_list(self):
        """Test _validate_actors_for_session_permission_requests returns False for empty list."""
        # Test
        is_valid, message = (
            session_permission_utils._validate_actors_for_session_permission_requests(
                []
            )
        )

        # Assertions
        assert is_valid is False
        assert message == "Invalid session_permissions"

    def test_validate_session_for_session_permission_request_success(self):
        """Test _validate_session_for_session_permission_request returns True for valid session."""
        # Setup
        session = {"session_id": "session-123", "base_os": "amazonlinux2"}

        # Test
        is_valid, message = (
            session_permission_utils._validate_session_for_session_permission_request(
                session
            )
        )

        # Assertions
        assert is_valid is True
        assert message == ""

    def test_validate_session_for_session_permission_request_none_session(self):
        """Test _validate_session_for_session_permission_request returns False for None session."""
        # Test
        is_valid, message = (
            session_permission_utils._validate_session_for_session_permission_request(
                None
            )
        )

        # Assertions
        assert is_valid is False
        assert message == "Invalid session"

    def test_validate_session_for_session_permission_request_windows_session(self):
        """Test _validate_session_for_session_permission_request returns False for Windows session."""
        # Setup
        session = {"session_id": "session-123", "base_os": "windows"}

        # Test
        is_valid, message = (
            session_permission_utils._validate_session_for_session_permission_request(
                session
            )
        )

        # Assertions
        assert is_valid is False
        assert (
            message
            == "Windows sessions do not support sessions permissions for OpenLDAP"
        )
