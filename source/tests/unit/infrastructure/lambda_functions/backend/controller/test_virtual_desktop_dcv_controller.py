#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add the backend directory to Python path to match controller's import context
backend_path = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "../../../../../idea/backend",
    )
)
sys.path.insert(0, backend_path)

from api.controllers import virtual_desktop_dcv_controller
from api.exceptions import BadRequestException
from datamodel.models.bad_request_exception_response_content import (
    BadRequestExceptionResponseContent,
)
from datamodel.models.batch_get_dcv_sessions_response_content import (
    BatchGetDCVSessionsResponseContent,
)
from datamodel.models.internal_service_exception_response_content import (
    InternalServiceExceptionResponseContent,
)
from datamodel.models.list_dcv_servers_response_content import ListDCVServersResponseContent
from connexion.exceptions import OAuthProblem


class TestVirtualDesktopDCVController:
    """Test class for virtual_desktop_dcv_controller module."""

    @staticmethod
    def _setup_mock_servers_api(mock_get_servers_api, response_data=None):
        """Helper method to setup mock servers API for success cases.
        
        Args:
            mock_get_servers_api: The mock object for _get_servers_api
            response_data: Dict to return from describe_servers (default: {"servers": []})
        
        Returns:
            The configured mock servers API instance
        """
        mock_servers_api = MagicMock()
        mock_response = MagicMock()
        mock_response.to_dict.return_value = response_data or {"servers": []}
        mock_servers_api.describe_servers.return_value = mock_response
        mock_get_servers_api.return_value = mock_servers_api
        
        return mock_servers_api

    @patch("api.controllers.virtual_desktop_dcv_controller.accounts.is_active_admin")
    @patch("api.controllers.virtual_desktop_dcv_controller._get_servers_api")
    def test_list_dcv_servers_returns_correct_response_type(self, mock_get_servers_api, mock_is_active_admin):
        """Test that list_dcv_servers returns ListDCVServersResponseContent instance."""
        self._setup_mock_servers_api(mock_get_servers_api)

        result = virtual_desktop_dcv_controller.list_dcv_servers()

        assert isinstance(result, ListDCVServersResponseContent)
        assert hasattr(result, "response")

    @patch("api.controllers.virtual_desktop_dcv_controller.accounts.is_active_admin")
    @patch("api.controllers.virtual_desktop_dcv_controller._get_servers_api")
    def test_list_dcv_servers_returns_server_data(self, mock_get_servers_api, mock_is_active_admin):
        """Test that list_dcv_servers returns server data from DCV broker."""
        mock_server_data = {
            "servers": [
                {"id": "server1", "hostname": "host1.example.com"},
                {"id": "server2", "hostname": "host2.example.com"},
            ]
        }
        self._setup_mock_servers_api(mock_get_servers_api, response_data=mock_server_data)

        result = virtual_desktop_dcv_controller.list_dcv_servers()

        assert isinstance(result, ListDCVServersResponseContent)
        assert result.response == mock_server_data
        assert "servers" in result.response
        assert len(result.response["servers"]) == 2

    @patch("api.controllers.virtual_desktop_dcv_controller.accounts.is_active_admin")
    @patch("api.controllers.virtual_desktop_dcv_controller._get_servers_api")
    def test_list_dcv_servers_handles_empty_response(self, mock_get_servers_api, mock_is_active_admin):
        """Test that list_dcv_servers handles empty server list."""
        self._setup_mock_servers_api(mock_get_servers_api, response_data={"servers": []})

        result = virtual_desktop_dcv_controller.list_dcv_servers()

        assert isinstance(result, ListDCVServersResponseContent)
        assert result.response == {"servers": []}

    @patch("api.controllers.virtual_desktop_dcv_controller.accounts.is_active_admin")
    @patch("api.controllers.virtual_desktop_dcv_controller._get_servers_api")
    def test_list_dcv_servers_with_next_token(self, mock_get_servers_api, mock_is_active_admin):
        """Test that list_dcv_servers passes next_token to describe_servers."""
        mock_is_active_admin.return_value = True
        mock_servers_api = self._setup_mock_servers_api(
            mock_get_servers_api, 
            response_data={"servers": []}
        )

        virtual_desktop_dcv_controller.list_dcv_servers(next_token="token123")

        # Verify describe_servers was called once
        mock_servers_api.describe_servers.assert_called_once()
        
        # Verify the request_data passed has the next_token
        call_args = mock_servers_api.describe_servers.call_args
        # Check both kwargs and args
        if call_args.kwargs:
            request_data = call_args.kwargs.get('body')
        elif call_args.args:
            request_data = call_args.args[0]
        else:
            request_data = None
            
        assert request_data is not None
        assert hasattr(request_data, 'next_token')
        assert request_data.next_token == "token123"

    @patch("api.controllers.virtual_desktop_dcv_controller.accounts.is_active_admin")
    def test_list_dcv_servers_raises_oauth_problem_when_not_admin(self, mock_is_active_admin):
        """Test that list_dcv_servers raises OAuthProblem when user is not an active admin."""
        mock_is_active_admin.return_value = False

        user = {"username": "testuser"}
        with pytest.raises(OAuthProblem) as exc_info:
            virtual_desktop_dcv_controller.list_dcv_servers(user=user)

        assert str(exc_info.value) == "401: Unauthorized user"

    # Tests for batch_get_dcv_sessions

    @patch("api.controllers.virtual_desktop_dcv_controller.accounts.is_active_admin")
    @patch("api.controllers.virtual_desktop_dcv_controller.dcv_broker_client.describe_sessions")
    def test_batch_get_dcv_sessions_returns_correct_response_type(self, mock_describe_sessions, mock_is_active_admin):
        """Test that batch_get_dcv_sessions returns BatchGetDCVSessionsResponseContent instance."""
        mock_is_active_admin.return_value = True
        mock_describe_sessions.return_value = {"sessions": {}}

        body = {"sessions": []}
        result = virtual_desktop_dcv_controller.batch_get_dcv_sessions(body=body)

        assert isinstance(result, BatchGetDCVSessionsResponseContent)
        assert hasattr(result, "response")

    @patch("api.controllers.virtual_desktop_dcv_controller.accounts.is_active_admin")
    @patch("api.controllers.virtual_desktop_dcv_controller.dcv_broker_client.describe_sessions")
    def test_batch_get_dcv_sessions_returns_session_data(self, mock_describe_sessions, mock_is_active_admin):
        """Test that batch_get_dcv_sessions returns session data from DCV broker."""
        mock_is_active_admin.return_value = True
        mock_session_data = {
            "sessions": {
                "session1": {"id": "session1", "name": "Test Session 1"},
                "session2": {"id": "session2", "name": "Test Session 2"},
            }
        }
        mock_describe_sessions.return_value = mock_session_data

        body = {"sessions": [{"dcv_session_id": "session1"}, {"dcv_session_id": "session2"}]}
        result = virtual_desktop_dcv_controller.batch_get_dcv_sessions(body=body)

        assert isinstance(result, BatchGetDCVSessionsResponseContent)
        assert result.response == mock_session_data
        assert "sessions" in result.response
        assert len(result.response["sessions"]) == 2

    @patch("api.controllers.virtual_desktop_dcv_controller.accounts.is_active_admin")
    @patch("api.controllers.virtual_desktop_dcv_controller.dcv_broker_client.describe_sessions")
    def test_batch_get_dcv_sessions_handles_empty_sessions(self, mock_describe_sessions, mock_is_active_admin):
        """Test that batch_get_dcv_sessions handles empty session list."""
        mock_is_active_admin.return_value = True
        mock_describe_sessions.return_value = {"sessions": {}}

        body = {"sessions": []}
        result = virtual_desktop_dcv_controller.batch_get_dcv_sessions(body=body)

        assert isinstance(result, BatchGetDCVSessionsResponseContent)
        assert result.response == {"sessions": {}}

    @patch("api.controllers.virtual_desktop_dcv_controller.accounts.is_active_admin")
    @patch("api.controllers.virtual_desktop_dcv_controller.dcv_broker_client.describe_sessions")
    def test_batch_get_dcv_sessions_with_next_token(self, mock_describe_sessions, mock_is_active_admin):
        """Test that batch_get_dcv_sessions passes next_token to describe_sessions."""
        mock_is_active_admin.return_value = True
        mock_describe_sessions.return_value = {"sessions": {}, "next_token": "token456"}

        body = {"sessions": [], "nextToken": "token123"}
        result = virtual_desktop_dcv_controller.batch_get_dcv_sessions(body=body)

        # Verify describe_sessions was called with the next_token
        mock_describe_sessions.assert_called_once()
        call_args = mock_describe_sessions.call_args
        assert call_args[0][1] == "token123"  # next_token is the second positional arg
        
        # Verify the response includes the next_token
        assert result.next_token == "token456"

    @patch("api.controllers.virtual_desktop_dcv_controller.accounts.is_active_admin")
    @patch("api.controllers.virtual_desktop_dcv_controller.dcv_broker_client.describe_sessions")
    def test_batch_get_dcv_sessions_preserves_next_token_in_response(self, mock_describe_sessions, mock_is_active_admin):
        """Test that batch_get_dcv_sessions preserves next_token from DCV broker response."""
        mock_is_active_admin.return_value = True
        mock_describe_sessions.return_value = {
            "sessions": {"session1": {"id": "session1"}},
            "next_token": "next_page_token"
        }

        body = {"sessions": []}
        result = virtual_desktop_dcv_controller.batch_get_dcv_sessions(body=body)

        assert isinstance(result, BatchGetDCVSessionsResponseContent)
        assert result.next_token == "next_page_token"
        assert "next_token" not in result.response  # Should be removed from response dict

    @patch("api.controllers.virtual_desktop_dcv_controller.accounts.is_active_admin")
    def test_batch_get_dcv_sessions_raises_oauth_problem_when_not_admin(self, mock_is_active_admin):
        """Test that batch_get_dcv_sessions raises OAuthProblem when user is not an active admin."""
        mock_is_active_admin.return_value = False

        user = {"username": "testuser"}
        body = {"sessions": []}
        with pytest.raises(OAuthProblem) as exc_info:
            virtual_desktop_dcv_controller.batch_get_dcv_sessions(body=body, user=user)

        assert str(exc_info.value) == "401: Unauthorized user"
