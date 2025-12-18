#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import pytest
import os
from unittest.mock import patch, MagicMock

from connexion.exceptions import OAuthProblem
from idea.infrastructure.resources.lambda_functions.backend.api.controllers import security_controller


class TestSecurityController:
    """Test class for security_controller module."""

    @patch.dict(os.environ, {'RES_TEST_MODE': 'false'}, clear=False)
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.accounts')
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.table_utils')
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.auth_utils')
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.token_resource')
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
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.accounts')
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.table_utils')
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.auth_utils')
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.token_resource')
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
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.accounts')
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.table_utils')
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.auth_utils')
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.token_resource')
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
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.token_resource')
    def test_bearer_auth_missing_username_in_token(self, mock_token_resource):
        """Test bearer authentication fails when username is missing from token."""
        # Setup mocks
        mock_token_resource.decode_token.return_value = {}  # No username
        
        # Create mock request
        mock_request = MagicMock()
        
        # Test and assert exception
        with pytest.raises(OAuthProblem) as exc_info:
            security_controller.bearer_auth("invalid_token", mock_request)
        
        assert "Username missing in token" in str(exc_info.value)

    @patch.dict(os.environ, {'RES_TEST_MODE': 'false'}, clear=False)
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.token_resource')
    def test_bearer_auth_empty_username_in_token(self, mock_token_resource):
        """Test bearer authentication fails when username is empty in token."""
        # Setup mocks
        mock_token_resource.decode_token.return_value = {"username": ""}  # Empty username
        
        # Create mock request
        mock_request = MagicMock()
        
        # Test and assert exception
        with pytest.raises(OAuthProblem) as exc_info:
            security_controller.bearer_auth("invalid_token", mock_request)
        
        assert "Username missing in token" in str(exc_info.value)

    @patch.dict(os.environ, {'RES_TEST_MODE': 'false'}, clear=False)
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.token_resource')
    def test_bearer_auth_none_username_in_token(self, mock_token_resource):
        """Test bearer authentication fails when username is None in token."""
        # Setup mocks
        mock_token_resource.decode_token.return_value = {"username": None}  # None username
        
        # Create mock request
        mock_request = MagicMock()
        
        # Test and assert exception
        with pytest.raises(OAuthProblem) as exc_info:
            security_controller.bearer_auth("invalid_token", mock_request)
        
        assert "Username missing in token" in str(exc_info.value)

    @patch.dict(os.environ, {'RES_TEST_MODE': 'false'}, clear=False)
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.accounts')
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.table_utils')
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.auth_utils')
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.token_resource')
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
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.token_resource')
    def test_bearer_auth_token_decode_exception(self, mock_token_resource):
        """Test bearer authentication handles token decode exceptions."""
        # Setup mocks
        mock_token_resource.decode_token.side_effect = Exception("Token decode error")
        
        # Create mock request
        mock_request = MagicMock()
        
        # Test and assert exception
        with pytest.raises(OAuthProblem) as exc_info:
            security_controller.bearer_auth("invalid_token", mock_request)
        
        assert "Token decode error" in str(exc_info.value)

    @patch.dict(os.environ, {'RES_TEST_MODE': 'false'}, clear=False)
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.accounts')
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.table_utils')
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.auth_utils')
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.token_resource')
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
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.accounts')
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.table_utils')
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.auth_utils')
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.token_resource')
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
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.accounts')
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.table_utils')
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.auth_utils')
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.token_resource')
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
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.accounts')
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.table_utils')
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.auth_utils')
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.token_resource')
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
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.accounts')
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.table_utils')
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.auth_utils')
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.token_resource')
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
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.accounts')
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.table_utils')
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.auth_utils')
    @patch('idea.infrastructure.resources.lambda_functions.backend.api.controllers.security_controller.token_resource')
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
