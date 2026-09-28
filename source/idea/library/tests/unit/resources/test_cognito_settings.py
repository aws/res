#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from unittest.mock import MagicMock, patch

import pytest
from res.resources import cognito_settings


@pytest.fixture
def mock_cognito_client():
    client = MagicMock()
    client.describe_user_pool.return_value = {
        "UserPool": {
            "AdminCreateUserConfig": {"AllowAdminCreateUserOnly": True},
            "Policies": {"PasswordPolicy": {"MinimumLength": 8}},
        }
    }
    return client


@pytest.fixture
def mock_deps(monkeypatch, mock_cognito_client):
    monkeypatch.setattr(
        "res.resources.cognito_settings.cluster_settings.get_setting",
        lambda key: "us-east-1_testpool",
    )
    with patch("res.resources.cognito_settings.get_aws_provider") as mock_provider:
        mock_provider.return_value.cognito_idp.return_value = mock_cognito_client
        yield mock_cognito_client


def test_update_settings_no_op_when_key_absent(mock_deps):
    cognito_settings.update_settings({"some.other.key": "value"})
    mock_deps.describe_user_pool.assert_not_called()


def test_update_settings_enables_self_signup(mock_deps):
    cognito_settings.update_settings({"cognito.enable_self_sign_up": True})

    mock_deps.update_user_pool.assert_called_once()
    call_kwargs = mock_deps.update_user_pool.call_args[1]
    assert call_kwargs["UserPoolId"] == "us-east-1_testpool"
    assert call_kwargs["AdminCreateUserConfig"]["AllowAdminCreateUserOnly"] is False
    assert call_kwargs["AutoVerifiedAttributes"] == ["email"]
    assert (
        call_kwargs["VerificationMessageTemplate"]["DefaultEmailOption"]
        == "CONFIRM_WITH_CODE"
    )


def test_update_settings_disables_self_signup(mock_deps):
    cognito_settings.update_settings({"cognito.enable_self_sign_up": False})

    call_kwargs = mock_deps.update_user_pool.call_args[1]
    assert call_kwargs["AdminCreateUserConfig"]["AllowAdminCreateUserOnly"] is True
    assert "AutoVerifiedAttributes" not in call_kwargs


def test_update_settings_logs_error_on_exception(mock_deps, monkeypatch):
    mock_deps.describe_user_pool.side_effect = Exception("API error")
    logged_errors = []
    monkeypatch.setattr(
        "res.resources.cognito_settings.logger",
        MagicMock(error=lambda msg: logged_errors.append(msg)),
    )

    cognito_settings.update_settings({"cognito.enable_self_sign_up": True})

    assert len(logged_errors) == 1
    assert "API error" in logged_errors[0]
