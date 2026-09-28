#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from unittest.mock import patch

import pytest
from res.utils.auth_utils import get_ddb_user_name, validate_native_cognito_username


class TestValidateNativeCognitoUsername:
    """Tests for the shared username validation helper used by both
    auth_utils.get_ddb_user_name() and proxy_handler.get_ddb_user_name()."""

    def test_valid_username_passes(self):
        assert validate_native_cognito_username("clusteradmin") == "clusteradmin"

    def test_valid_username_with_numbers(self):
        assert validate_native_cognito_username("user123") == "user123"

    def test_valid_username_with_hyphens_underscores(self):
        assert validate_native_cognito_username("test-user_1") == "test-user_1"

    def test_rejects_username_with_at_sign(self):
        """Core attack vector: 'clusteradmin@!' would truncate to 'clusteradmin'."""
        with pytest.raises(Exception, match="Invalid Cognito username"):
            validate_native_cognito_username("clusteradmin@!")

    def test_rejects_email_format(self):
        with pytest.raises(Exception, match="Invalid Cognito username"):
            validate_native_cognito_username("admin@example.com")

    def test_rejects_at_sign_only(self):
        with pytest.raises(Exception, match="Invalid Cognito username"):
            validate_native_cognito_username("@")

    def test_rejects_trailing_at_sign(self):
        with pytest.raises(Exception, match="Invalid Cognito username"):
            validate_native_cognito_username("user@")

    def test_empty_username_rejected(self):
        """Empty string doesn't match the username regex."""
        with pytest.raises(Exception, match="Invalid Cognito username"):
            validate_native_cognito_username("")

    def test_error_message_includes_username(self):
        with pytest.raises(Exception, match="Invalid Cognito username: 'bad@user'"):
            validate_native_cognito_username("bad@user")


class TestGetDdbUserNameRejection:
    """Tests for auth_utils.get_ddb_user_name() rejection of '@' in native
    Cognito usernames. This is the code path used by the backend security
    controller (via connexion bearer_auth)."""

    def test_native_username_without_at_passes(self):
        assert get_ddb_user_name("clusteradmin", None) == "clusteradmin"

    def test_native_username_rejects_at_sign(self):
        """The core attack: 'clusteradmin@!' without IdP should not resolve."""
        with pytest.raises(Exception, match="Invalid Cognito username"):
            get_ddb_user_name("clusteradmin@!", None)

    def test_native_username_rejects_email_format(self):
        with pytest.raises(Exception, match="Invalid Cognito username"):
            get_ddb_user_name("test1@example.com", None)

    def test_native_username_rejects_trailing_at(self):
        with pytest.raises(Exception, match="Invalid Cognito username"):
            get_ddb_user_name("admin@", None)

    @patch("res.utils.auth_utils.table_utils.query")
    def test_idp_username_with_at_passes(self, mock_query):
        """When IdP IS configured, '@' in username is expected (it's an email)."""
        mock_query.return_value = [{"username": "admin_user"}]
        result = get_ddb_user_name("saml_admin@example.com", "saml")
        assert result == "admin_user"

    def test_idp_username_without_prefix_rejects_at_sign(self):
        """The IdP-path attack: 'clusteradmin@!2' with idp='saml' configured
        but no 'saml_' prefix should be rejected as a native user."""
        with pytest.raises(Exception, match="Invalid Cognito username"):
            get_ddb_user_name("clusteradmin@!2", "saml")
        with pytest.raises(Exception, match="Invalid Cognito username"):
            get_ddb_user_name("admin@example.com", "saml")

    def test_idp_username_without_prefix_no_at_passes(self):
        """Native user 'clusteradmin' with idp='saml' configured but no prefix
        should still resolve (legitimate native user in SSO environment)."""
        assert get_ddb_user_name("clusteradmin", "saml") == "clusteradmin"
