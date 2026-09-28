#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import pytest

from idea.infrastructure.resources.lambda_functions.cognito_trigger_workflow_lambda import (
    cognito_pre_signup_handler,
)


def _make_event(username: str, trigger_source: str = "PreSignUp_SignUp") -> dict:
    return {
        "userName": username,
        "triggerSource": trigger_source,
        "request": {
            "userAttributes": {
                "email": f"{username}@example.com",
            }
        },
    }


class TestPreSignupHandler:
    def test_valid_username_passes(self):
        event = _make_event("validuser")
        result = cognito_pre_signup_handler.handle_event(event, None)
        assert result == event

    def test_valid_username_with_numbers_passes(self):
        event = _make_event("user123")
        result = cognito_pre_signup_handler.handle_event(event, None)
        assert result == event

    def test_valid_username_with_hyphens_underscores_passes(self):
        event = _make_event("test-user_1")
        result = cognito_pre_signup_handler.handle_event(event, None)
        assert result == event

    def test_rejects_username_with_at_sign(self):
        """The core attack vector - clusteradmin@! should be rejected."""
        event = _make_event("clusteradmin@!")
        with pytest.raises(
            Exception, match="Username must start with a lowercase letter"
        ):
            cognito_pre_signup_handler.handle_event(event, None)

    def test_rejects_username_with_email_format(self):
        event = _make_event("admin@example.com")
        with pytest.raises(
            Exception, match="Username must start with a lowercase letter"
        ):
            cognito_pre_signup_handler.handle_event(event, None)

    def test_rejects_username_starting_with_number(self):
        event = _make_event("1baduser")
        with pytest.raises(
            Exception, match="Username must start with a lowercase letter"
        ):
            cognito_pre_signup_handler.handle_event(event, None)

    def test_rejects_username_with_uppercase(self):
        event = _make_event("AdminUser")
        with pytest.raises(
            Exception, match="Username must start with a lowercase letter"
        ):
            cognito_pre_signup_handler.handle_event(event, None)

    def test_rejects_username_with_special_chars(self):
        event = _make_event("user!@#$")
        with pytest.raises(
            Exception, match="Username must start with a lowercase letter"
        ):
            cognito_pre_signup_handler.handle_event(event, None)

    def test_rejects_username_too_long(self):
        event = _make_event("a" * 33)
        with pytest.raises(
            Exception, match="Username must start with a lowercase letter"
        ):
            cognito_pre_signup_handler.handle_event(event, None)

    def test_admin_create_user_bypasses_validation(self):
        """Admin-created users should not be blocked by this trigger."""
        event = _make_event("AnyUsername@!", "PreSignUp_AdminCreateUser")
        result = cognito_pre_signup_handler.handle_event(event, None)
        assert result == event

    def test_external_provider_bypasses_validation(self):
        """SSO/federated users should not be blocked by this trigger."""
        event = _make_event("saml_user@example.com", "PreSignUp_ExternalProvider")
        result = cognito_pre_signup_handler.handle_event(event, None)
        assert result == event
