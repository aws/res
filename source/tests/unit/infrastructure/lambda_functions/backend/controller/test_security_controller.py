#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import pytest
import os
from unittest.mock import patch, MagicMock

from connexion.exceptions import OAuthProblem
from idea.backend.api.controllers import security_controller


class TestSecurityController:
    """Test class for security_controller module."""

    @patch.dict(os.environ, {'RES_TEST_MODE': 'false'}, clear=False)
    @patch('idea.backend.api.controllers.security_controller.accounts')
    @patch('idea.backend.api.controllers.security_controller.table_utils')
    @patch('idea.backend.api.controllers.security_controller.auth_utils')
    @patch('idea.backend.api.controllers.security_controller.token_resource')
    def test_bearer_auth_success(self, mock_token_resource, mock_auth_utils, mock_table_utils, mock_accounts):
        """Test successful bearer authentication."""
        # Setup mocks
        mock_token_resource.decode_token.return_value = {"username": "test_user"}
        mock_table_utils.get_item.return_value = {"value": "test_idp"}
        mock_auth_utils.get_ddb_user_name.return_value = "test_user@test_idp"
        mock_accounts.is_active_user.return_value = True
        
        # Create mock request
        mock_request = MagicMock()
        
        # Test
        result = security_controller.bearer_auth("valid_token", mock_request)
        
        # Assertions
        assert result == {"uid": "test_user@test_idp"}
        mock_token_resource.decode_token.assert_called_once_with(token="valid_token", verify_exp=True)
        mock_table_utils.get_item.assert_called_once()
        mock_auth_utils.get_ddb_user_name.assert_called_once_with(username="test_user", idp_name="test_idp")
        mock_accounts.is_active_user.assert_called_once_with("test_user@test_idp")

    @patch.dict(os.environ, {'RES_TEST_MODE': 'false'}, clear=False)
    @patch('idea.backend.api.controllers.security_controller.accounts')
    @patch('idea.backend.api.controllers.security_controller.table_utils')
    @patch('idea.backend.api.controllers.security_controller.auth_utils')
    @patch('idea.backend.api.controllers.security_controller.token_resource')
    def test_bearer_auth_success_no_idp_name(self, mock_token_resource, mock_auth_utils, mock_table_utils, mock_accounts):
        """Test successful bearer authentication when no IDP name is found."""
        # Setup mocks
        mock_token_resource.decode_token.return_value = {"username": "test_user"}
        mock_table_utils.get_item.return_value = None  # No IDP name record
        mock_auth_utils.get_ddb_user_name.return_value = "test_user"
        mock_accounts.is_active_user.return_value = True
        
        # Create mock request
        mock_request = MagicMock()
        
        # Test
        result = security_controller.bearer_auth("valid_token", mock_request)
        
        # Assertions
        assert result == {"uid": "test_user"}
        mock_auth_utils.get_ddb_user_name.assert_called_once_with(username="test_user", idp_name=None)

    @patch.dict(os.environ, {'RES_TEST_MODE': 'false'}, clear=False)
    @patch('idea.backend.api.controllers.security_controller.accounts')
    @patch('idea.backend.api.controllers.security_controller.table_utils')
    @patch('idea.backend.api.controllers.security_controller.auth_utils')
    @patch('idea.backend.api.controllers.security_controller.token_resource')
    def test_bearer_auth_success_empty_idp_record(self, mock_token_resource, mock_auth_utils, mock_table_utils, mock_accounts):
        """Test successful bearer authentication when IDP record exists but has no value."""
        # Setup mocks
        mock_token_resource.decode_token.return_value = {"username": "test_user"}
        mock_table_utils.get_item.return_value = {}  # Empty record
        mock_auth_utils.get_ddb_user_name.return_value = "test_user"
        mock_accounts.is_active_user.return_value = True
        
        # Create mock request
        mock_request = MagicMock()
        
        # Test
        result = security_controller.bearer_auth("valid_token", mock_request)
        
        # Assertions
        assert result == {"uid": "test_user"}
        mock_auth_utils.get_ddb_user_name.assert_called_once_with(username="test_user", idp_name=None)

    @patch.dict(os.environ, {'RES_TEST_MODE': 'false'}, clear=False)
    @patch('idea.backend.api.controllers.security_controller.token_resource')
    def test_bearer_auth_missing_username_in_token(self, mock_token_resource):
        """Test bearer authentication fails when token has no username and no scope."""
        # Setup mocks
        mock_token_resource.decode_token.return_value = {}  # No username or scope

        # Create mock request
        mock_request = MagicMock()

        # Test and assert exception
        with pytest.raises(OAuthProblem) as exc_info:
            security_controller.bearer_auth("invalid_token", mock_request)

        assert "Username or scope missing in token" in str(exc_info.value)

    @patch.dict(os.environ, {'RES_TEST_MODE': 'false'}, clear=False)
    @patch('idea.backend.api.controllers.security_controller.token_resource')
    def test_bearer_auth_empty_username_in_token(self, mock_token_resource):
        """Test bearer authentication fails when username is empty in token and no scope."""
        # Setup mocks
        mock_token_resource.decode_token.return_value = {"username": ""}  # Empty username, no scope

        # Create mock request
        mock_request = MagicMock()

        # Test and assert exception
        with pytest.raises(OAuthProblem) as exc_info:
            security_controller.bearer_auth("invalid_token", mock_request)

        assert "Username or scope missing in token" in str(exc_info.value)

    @patch.dict(os.environ, {'RES_TEST_MODE': 'false'}, clear=False)
    @patch('idea.backend.api.controllers.security_controller.token_resource')
    def test_bearer_auth_none_username_in_token(self, mock_token_resource):
        """Test bearer authentication fails when username is None in token and no scope."""
        # Setup mocks
        mock_token_resource.decode_token.return_value = {"username": None}  # None username, no scope

        # Create mock request
        mock_request = MagicMock()

        # Test and assert exception
        with pytest.raises(OAuthProblem) as exc_info:
            security_controller.bearer_auth("invalid_token", mock_request)

        assert "Username or scope missing in token" in str(exc_info.value)

    @patch.dict(os.environ, {'RES_TEST_MODE': 'false'}, clear=False)
    @patch('idea.backend.api.controllers.security_controller.accounts')
    @patch('idea.backend.api.controllers.security_controller.table_utils')
    @patch('idea.backend.api.controllers.security_controller.auth_utils')
    @patch('idea.backend.api.controllers.security_controller.token_resource')
    def test_bearer_auth_inactive_user(self, mock_token_resource, mock_auth_utils, mock_table_utils, mock_accounts):
        """Test bearer authentication fails for inactive user."""
        # Setup mocks
        mock_token_resource.decode_token.return_value = {"username": "test_user"}
        mock_table_utils.get_item.return_value = {"value": "test_idp"}
        mock_auth_utils.get_ddb_user_name.return_value = "test_user@test_idp"
        mock_accounts.is_active_user.return_value = False  # Inactive user
        
        # Create mock request
        mock_request = MagicMock()
        
        # Test and assert exception
        with pytest.raises(OAuthProblem) as exc_info:
            security_controller.bearer_auth("valid_token", mock_request)
        
        assert "Inactive user" in str(exc_info.value)

    @patch.dict(os.environ, {'RES_TEST_MODE': 'false'}, clear=False)
    @patch('idea.backend.api.controllers.security_controller.token_resource')
    def test_bearer_auth_token_decode_exception(self, mock_token_resource):
        """Test bearer authentication handles token decode exceptions."""
        # Setup mocks
        mock_token_resource.decode_token.side_effect = Exception("decode failed")

        # Create mock request
        mock_request = MagicMock()

        # Test and assert exception
        with pytest.raises(OAuthProblem) as exc_info:
            security_controller.bearer_auth("invalid_token", mock_request)

        assert "decode failed" in str(exc_info.value)

    @patch.dict(os.environ, {'RES_TEST_MODE': 'false'}, clear=False)
    @patch('idea.backend.api.controllers.security_controller.accounts')
    @patch('idea.backend.api.controllers.security_controller.table_utils')
    @patch('idea.backend.api.controllers.security_controller.auth_utils')
    @patch('idea.backend.api.controllers.security_controller.token_resource')
    def test_bearer_auth_table_utils_exception(self, mock_token_resource, mock_auth_utils, mock_table_utils, mock_accounts):
        """Test bearer authentication handles table_utils exceptions."""
        # Setup mocks
        mock_token_resource.decode_token.return_value = {"username": "test_user"}
        mock_table_utils.get_item.side_effect = Exception("Database error")
        
        # Create mock request
        mock_request = MagicMock()
        
        # Test and assert exception
        with pytest.raises(OAuthProblem) as exc_info:
            security_controller.bearer_auth("valid_token", mock_request)
        
        assert "Database error" in str(exc_info.value)

    @patch.dict(os.environ, {'RES_TEST_MODE': 'false'}, clear=False)
    @patch('idea.backend.api.controllers.security_controller.accounts')
    @patch('idea.backend.api.controllers.security_controller.table_utils')
    @patch('idea.backend.api.controllers.security_controller.auth_utils')
    @patch('idea.backend.api.controllers.security_controller.token_resource')
    def test_bearer_auth_auth_utils_exception(self, mock_token_resource, mock_auth_utils, mock_table_utils, mock_accounts):
        """Test bearer authentication handles auth_utils exceptions."""
        # Setup mocks
        mock_token_resource.decode_token.return_value = {"username": "test_user"}
        mock_table_utils.get_item.return_value = {"value": "test_idp"}
        mock_auth_utils.get_ddb_user_name.side_effect = Exception("Auth utils error")
        
        # Create mock request
        mock_request = MagicMock()
        
        # Test and assert exception
        with pytest.raises(OAuthProblem) as exc_info:
            security_controller.bearer_auth("valid_token", mock_request)
        
        assert "Auth utils error" in str(exc_info.value)

    @patch.dict(os.environ, {'RES_TEST_MODE': 'false'}, clear=False)
    @patch('idea.backend.api.controllers.security_controller.accounts')
    @patch('idea.backend.api.controllers.security_controller.table_utils')
    @patch('idea.backend.api.controllers.security_controller.auth_utils')
    @patch('idea.backend.api.controllers.security_controller.token_resource')
    def test_bearer_auth_accounts_exception(self, mock_token_resource, mock_auth_utils, mock_table_utils, mock_accounts):
        """Test bearer authentication handles accounts service exceptions."""
        # Setup mocks
        mock_token_resource.decode_token.return_value = {"username": "test_user"}
        mock_table_utils.get_item.return_value = {"value": "test_idp"}
        mock_auth_utils.get_ddb_user_name.return_value = "test_user@test_idp"
        mock_accounts.is_active_user.side_effect = Exception("Accounts service error")
        
        # Create mock request
        mock_request = MagicMock()
        
        # Test and assert exception
        with pytest.raises(OAuthProblem) as exc_info:
            security_controller.bearer_auth("valid_token", mock_request)
        
        assert "Accounts service error" in str(exc_info.value)

    @patch.dict(os.environ, {'RES_TEST_MODE': 'false'}, clear=False)
    @patch('idea.backend.api.controllers.security_controller.accounts')
    @patch('idea.backend.api.controllers.security_controller.table_utils')
    @patch('idea.backend.api.controllers.security_controller.auth_utils')
    @patch('idea.backend.api.controllers.security_controller.token_resource')
    def test_bearer_auth_correct_table_name_used(self, mock_token_resource, mock_auth_utils, mock_table_utils, mock_accounts):
        """Test that bearer_auth uses the correct table name for cluster settings."""
        # Setup mocks
        mock_token_resource.decode_token.return_value = {"username": "test_user"}
        mock_table_utils.get_item.return_value = {"value": "test_idp"}
        mock_auth_utils.get_ddb_user_name.return_value = "test_user@test_idp"
        mock_accounts.is_active_user.return_value = True
        
        # Create mock request
        mock_request = MagicMock()
        
        # Test
        security_controller.bearer_auth("valid_token", mock_request)
        
        # Check that get_item was called with the correct table name and key
        call_args = mock_table_utils.get_item.call_args
        assert call_args[1]['table_name'] == security_controller.CLUSTER_SETTINGS_TABLE_NAME
        assert call_args[1]['key'] == {"key": security_controller.COGNITO_SSO_IDP_PROVIDER_NAME}

    @patch.dict(os.environ, {'RES_TEST_MODE': 'false'}, clear=False)
    @patch('idea.backend.api.controllers.security_controller.accounts')
    @patch('idea.backend.api.controllers.security_controller.table_utils')
    @patch('idea.backend.api.controllers.security_controller.auth_utils')
    @patch('idea.backend.api.controllers.security_controller.token_resource')
    def test_bearer_auth_token_verification_enabled(self, mock_token_resource, mock_auth_utils, mock_table_utils, mock_accounts):
        """Test that bearer_auth calls token decode with expiration verification enabled."""
        # Setup mocks
        mock_token_resource.decode_token.return_value = {"username": "test_user"}
        mock_table_utils.get_item.return_value = {"value": "test_idp"}
        mock_auth_utils.get_ddb_user_name.return_value = "test_user@test_idp"
        mock_accounts.is_active_user.return_value = True
        
        # Create mock request
        mock_request = MagicMock()
        
        # Test
        security_controller.bearer_auth("valid_token", mock_request)
        
        # Check that decode_token was called with verify_exp=True
        mock_token_resource.decode_token.assert_called_once_with(token="valid_token", verify_exp=True)

    @patch.dict(os.environ, {'RES_TEST_MODE': 'false'}, clear=False)
    @patch('idea.backend.api.controllers.security_controller.accounts')
    @patch('idea.backend.api.controllers.security_controller.table_utils')
    @patch('idea.backend.api.controllers.security_controller.auth_utils')
    @patch('idea.backend.api.controllers.security_controller.token_resource')
    def test_bearer_auth_return_format(self, mock_token_resource, mock_auth_utils, mock_table_utils, mock_accounts):
        """Test that bearer_auth returns the correct format."""
        # Setup mocks
        mock_token_resource.decode_token.return_value = {"username": "test_user"}
        mock_table_utils.get_item.return_value = {"value": "test_idp"}
        mock_auth_utils.get_ddb_user_name.return_value = "test_user@test_idp"
        mock_accounts.is_active_user.return_value = True

        # Create mock request
        mock_request = MagicMock()

        # Test
        result = security_controller.bearer_auth("valid_token", mock_request)

        # Assertions
        assert isinstance(result, dict)
        assert "uid" in result
        assert len(result) == 1  # Should only contain uid
        assert isinstance(result["uid"], str)

    @patch.dict(os.environ, {'RES_TEST_MODE': 'false'}, clear=False)
    @patch('idea.backend.api.controllers.security_controller.token_resource')
    def test_bearer_auth_service_token_success(self, mock_token_resource):
        """Test successful service token authentication with scope and client_id."""
        mock_token_resource.decode_token.return_value = {
            "scope": "test-vdc/read test-vdc/write",
            "client_id": "cluster-manager-client-id",
        }

        result = security_controller.bearer_auth("svc_token", MagicMock())

        assert result == {
            "uid": "cluster-manager-client-id",
            "scope": ["test-vdc/read", "test-vdc/write"],
        }

    @patch.dict(os.environ, {'RES_TEST_MODE': 'false'}, clear=False)
    @patch('idea.backend.api.controllers.security_controller.token_resource')
    def test_bearer_auth_service_token_single_scope(self, mock_token_resource):
        """Test service token authentication with a single scope."""
        mock_token_resource.decode_token.return_value = {
            "scope": "test-vdc/read",
            "client_id": "client-abc",
        }

        result = security_controller.bearer_auth("svc_token", MagicMock())

        assert result == {"uid": "client-abc", "scope": ["test-vdc/read"]}

    @patch.dict(os.environ, {'RES_TEST_MODE': 'false'}, clear=False)
    @patch('idea.backend.api.controllers.security_controller.token_resource')
    def test_bearer_auth_service_token_missing_client_id(self, mock_token_resource):
        """Test service token authentication fails when client_id is missing."""
        mock_token_resource.decode_token.return_value = {"scope": "test-vdc/read"}

        with pytest.raises(OAuthProblem) as exc_info:
            security_controller.bearer_auth("svc_token", MagicMock())

        assert "Service token missing client_id" in str(exc_info.value)

    @patch.dict(os.environ, {'RES_TEST_MODE': 'false'}, clear=False)
    @patch('idea.backend.api.controllers.security_controller.accounts')
    @patch('idea.backend.api.controllers.security_controller.table_utils')
    @patch('idea.backend.api.controllers.security_controller.auth_utils')
    @patch('idea.backend.api.controllers.security_controller.token_resource')
    def test_bearer_auth_user_token_takes_precedence_over_scope(
        self, mock_token_resource, mock_auth_utils, mock_table_utils, mock_accounts
    ):
        """Test user token branch is used when both username and scope are present."""
        mock_token_resource.decode_token.return_value = {
            "username": "test_user",
            "scope": "test-vdc/write",
            "client_id": "should-not-be-used",
        }
        mock_table_utils.get_item.return_value = {"value": "test_idp"}
        mock_auth_utils.get_ddb_user_name.return_value = "test_user@test_idp"
        mock_accounts.is_active_user.return_value = True

        result = security_controller.bearer_auth("token", MagicMock())

        assert result == {"uid": "test_user@test_idp"}

    @patch.dict(os.environ, {'RES_TEST_MODE': 'true'}, clear=False)
    @patch('idea.backend.api.controllers.security_controller.accounts')
    @patch('idea.backend.api.controllers.security_controller.token_resource')
    def test_bearer_auth_test_mode_falls_back_when_decode_fails(
        self, mock_token_resource, mock_accounts
    ):
        """Test that RES_TEST_MODE falls back to X_RES_TEST_USERNAME when decode_token fails."""
        # Integration tests pass a fake 'test' token that fails JWT decode; the
        # test-mode fallback must still apply so the request can proceed.
        mock_token_resource.decode_token.side_effect = Exception("not a JWT")
        mock_accounts.is_active_user.return_value = True

        mock_request = MagicMock()
        mock_request.headers.get.return_value = "integ_test_user"

        result = security_controller.bearer_auth("test", mock_request)

        assert result == {"uid": "integ_test_user"}

    @patch.dict(os.environ, {'RES_TEST_MODE': 'true'}, clear=False)
    @patch('idea.backend.api.controllers.security_controller.token_resource')
    def test_bearer_auth_test_mode_missing_header_raises(self, mock_token_resource):
        """Test that test mode without X_RES_TEST_USERNAME header raises OAuthProblem."""
        mock_token_resource.decode_token.side_effect = Exception("not a JWT")

        mock_request = MagicMock()
        mock_request.headers.get.return_value = ""

        with pytest.raises(OAuthProblem) as exc_info:
            security_controller.bearer_auth("test", mock_request)

        assert "X_RES_TEST_USERNAME header is required" in str(exc_info.value)

    @patch.dict(os.environ, {'RES_TEST_MODE': 'true'}, clear=False)
    @patch('idea.backend.api.controllers.security_controller.token_resource')
    def test_bearer_auth_test_mode_does_not_mask_service_token_rejection(
        self, mock_token_resource
    ):
        """Test mode must not silently allow a malformed service token (missing client_id)."""
        mock_token_resource.decode_token.return_value = {"scope": "test-vdc/read"}

        mock_request = MagicMock()
        mock_request.headers.get.return_value = "integ_test_user"

        with pytest.raises(OAuthProblem) as exc_info:
            security_controller.bearer_auth("svc_token", mock_request)

        assert "Service token missing client_id" in str(exc_info.value)

    @patch.dict(os.environ, {'RES_TEST_MODE': 'true'}, clear=False)
    @patch('idea.backend.api.controllers.security_controller.token_resource')
    def test_bearer_auth_test_mode_does_not_mask_invalid_token(self, mock_token_resource):
        """Test mode must not silently allow a token with neither username nor scope."""
        mock_token_resource.decode_token.return_value = {}

        mock_request = MagicMock()
        mock_request.headers.get.return_value = "integ_test_user"

        with pytest.raises(OAuthProblem) as exc_info:
            security_controller.bearer_auth("token", mock_request)

        assert "Username or scope missing in token" in str(exc_info.value)
