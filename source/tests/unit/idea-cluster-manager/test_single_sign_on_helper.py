#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

"""
Test Cases for AccountsService
"""

from unittest.mock import patch

import pytest
from ideaclustermanager import AppContext
from ideaclustermanager.app.accounts.helpers.single_sign_on_helper import (
    SingleSignOnHelper,
)
from ideasdk.utils import Utils

from ideadatamodel import ConfigureSSORequest, constants, errorcodes, exceptions

saml_payload = ConfigureSSORequest(
    provider_name="saml",
    provider_type="SAML",
    provider_email_attribute="http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
    saml_metadata_url="test.url",
    saml_metadata_file="",
)

oidc_payload = ConfigureSSORequest(
    provider_name="oidc",
    provider_type="OIDC",
    provider_email_attribute="email",
    oidc_client_id="test-client-id",
    oidc_client_secret="test-secret",
    oidc_issuer="test-issuer",
    oidc_attributes_request_method="GET",
    oidc_authorize_scopes="oidc",
    oidc_authorize_url="oidc.authorize.test",
    oidc_token_url="oidc.token.test",
    oidc_attributes_url="oidc.attr.test",
    oidc_jwks_uri="oidc.jwks.test",
)


@patch.object(SingleSignOnHelper, "_update_config_entry")
@patch.object(SingleSignOnHelper, "link_existing_users")
@patch.object(SingleSignOnHelper, "create_or_update_user_pool_client")
@patch.object(SingleSignOnHelper, "create_or_update_identity_provider")
def test_configure_sso(
    mock_create_idp,
    mock_create_client,
    mock_link_users,
    mock_update_config,
    context: AppContext,
):
    """
    configure_sso should create or update user pool client, create or update identity provider,
    link users and update the config
    """

    context.accounts.single_sign_on_helper.configure_sso(request=saml_payload)
    mock_create_idp.assert_called_with(saml_payload)
    mock_create_client.assert_called_with(
        provider_name=saml_payload.provider_name, refresh_token_validity_hours=None
    )
    mock_link_users.assert_called()
    mock_update_config.assert_called_with("cognito.sso_enabled", True)


@patch.object(saml_payload, "provider_name", "")
def test_create_or_update_identity_provider_missing_provider_name(context: AppContext):
    """
    create_or_update_user_pool_client with missing provider name
    """
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.single_sign_on_helper.create_or_update_identity_provider(
            saml_payload
        )

        assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
        assert "provider_name is required" in exc_info.value.message


@patch.object(saml_payload, "provider_name", "Cognito")
def test_create_or_update_identity_provider_invalid_provider_name(context: AppContext):
    """
    create_or_update_user_pool_client with missing provider name
    """
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.single_sign_on_helper.create_or_update_identity_provider(
            saml_payload
        )

        assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
        assert (
            constants.SSO_SOURCE_PROVIDER_NAME_ERROR_MESSAGE == exc_info.value.message
        )


@patch.object(saml_payload, "provider_type", "")
def test_create_or_update_identity_provider_missing_provider_type(context: AppContext):
    """
    create_or_update_user_pool_client with missing provider type
    """
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.single_sign_on_helper.create_or_update_identity_provider(
            saml_payload
        )

        assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
        assert "provider_type is required" in exc_info.value.message


@patch.object(saml_payload, "provider_email_attribute", "")
def test_create_or_update_identity_provider_missing_provider_email_attr(
    context: AppContext,
):
    """
    create_or_update_user_pool_client with missing provider email attribute
    """
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.single_sign_on_helper.create_or_update_identity_provider(
            saml_payload
        )

        assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
        assert "provider_email_attribute is required" in exc_info.value.message


@patch.object(saml_payload, "provider_type", "invalid")
def test_create_or_update_identity_provider_invalid_provider_type(context: AppContext):
    """
    create_or_update_user_pool_client with invalid provider type
    """
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.single_sign_on_helper.create_or_update_identity_provider(
            saml_payload
        )

        assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
        assert "provider type must be one of: SAML or OIDC" in exc_info.value.message


@patch.object(SingleSignOnHelper, "_update_config_entry")
@patch.object(SingleSignOnHelper, "get_identity_provider", return_value=None)
@patch.object(
    SingleSignOnHelper, "get_saml_provider_details", return_value="provider-details"
)
def test_create_identity_provider_saml(
    mock_get_provider_details, mock_get_idp, mock_update_config, context: AppContext
):
    """
    create_or_update_identity_provider call with SAML as provider type and no pre-existing idp
    """
    context.accounts.single_sign_on_helper.create_or_update_identity_provider(
        saml_payload
    )

    mock_get_provider_details.assert_called_with(saml_payload)
    mock_get_idp.assert_called()
    context.aws().cognito_idp().create_identity_provider.assert_called_with(
        UserPoolId=context.config().get_string(
            "identity-provider.cognito.user_pool_id", required=True
        ),
        ProviderName=saml_payload.provider_name,
        ProviderType=saml_payload.provider_type,
        ProviderDetails="provider-details",
        AttributeMapping={"email": saml_payload.provider_email_attribute},
        IdpIdentifiers=["single-sign-on-identity-provider"],
    )
    mock_update_config.has_calls(
        [
            ("cognito.sso_idp_provider_name", saml_payload.provider_name),
            ("cognito.sso_idp_provider_type", saml_payload.provider_type),
            ("cognito.sso_idp_identifier", "single-sign-on-identity-provider"),
            (
                "cognito.sso_idp_provider_email_attribute",
                saml_payload.provider_email_attribute,
            ),
        ]
    )


@patch.object(SingleSignOnHelper, "_update_config_entry")
@patch.object(SingleSignOnHelper, "get_identity_provider", return_value=None)
@patch.object(
    SingleSignOnHelper, "get_oidc_provider_details", return_value="provider-details"
)
def test_create_identity_provider_oidc(
    mock_get_provider_details, mock_get_idp, mock_update_config, context: AppContext
):
    """
    create_or_update_identity_provider call with OIDC as provider type and no pre-existing idp
    """
    context.accounts.single_sign_on_helper.create_or_update_identity_provider(
        oidc_payload
    )

    mock_get_provider_details.assert_called_with(oidc_payload)
    mock_get_idp.assert_called()
    context.aws().cognito_idp().create_identity_provider.assert_called_with(
        UserPoolId=context.config().get_string(
            "identity-provider.cognito.user_pool_id", required=True
        ),
        ProviderName=oidc_payload.provider_name,
        ProviderType=oidc_payload.provider_type,
        ProviderDetails="provider-details",
        AttributeMapping={"email": oidc_payload.provider_email_attribute},
        IdpIdentifiers=["single-sign-on-identity-provider"],
    )
    mock_update_config.has_calls(
        [
            ("cognito.sso_idp_provider_name", oidc_payload.provider_name),
            ("cognito.sso_idp_provider_type", oidc_payload.provider_type),
            ("cognito.sso_idp_identifier", "single-sign-on-identity-provider"),
            (
                "cognito.sso_idp_provider_email_attribute",
                oidc_payload.provider_email_attribute,
            ),
        ]
    )


@patch.object(SingleSignOnHelper, "_update_config_entry")
@patch.object(
    SingleSignOnHelper,
    "get_identity_provider",
    return_value={
        "ProviderName": oidc_payload.provider_name,
        "ProviderType": oidc_payload.provider_type,
    },
)
@patch.object(
    SingleSignOnHelper, "get_oidc_provider_details", return_value="provider-details"
)
def test_update_identity_provider_oidc(
    mock_get_provider_details, mock_get_idp, mock_update_config, context: AppContext
):
    """
    create_or_update_identity_provider call with OIDC as provider type and pre-existing idp
    """
    context.accounts.single_sign_on_helper.create_or_update_identity_provider(
        oidc_payload
    )

    mock_get_provider_details.assert_called_with(oidc_payload)
    mock_get_idp.assert_called()
    context.aws().cognito_idp().update_identity_provider.assert_called_with(
        UserPoolId=context.config().get_string(
            "identity-provider.cognito.user_pool_id", required=True
        ),
        ProviderName=oidc_payload.provider_name,
        ProviderDetails="provider-details",
        AttributeMapping={"email": oidc_payload.provider_email_attribute},
        IdpIdentifiers=["single-sign-on-identity-provider"],
    )
    mock_update_config.has_calls(
        [
            ("cognito.sso_idp_provider_name", oidc_payload.provider_name),
            ("cognito.sso_idp_provider_type", oidc_payload.provider_type),
            ("cognito.sso_idp_identifier", "single-sign-on-identity-provider"),
            (
                "cognito.sso_idp_provider_email_attribute",
                oidc_payload.provider_email_attribute,
            ),
        ]
    )


@patch.object(SingleSignOnHelper, "_update_config_entry")
@patch.object(
    SingleSignOnHelper,
    "get_identity_provider",
    return_value={
        # Different name and type
        "ProviderName": saml_payload.provider_name,
        "ProviderType": saml_payload.provider_type,
    },
)
@patch.object(
    SingleSignOnHelper, "get_oidc_provider_details", return_value="provider-details"
)
def test_recreate_identity_provider_oidc(
    mock_get_provider_details, mock_get_idp, mock_update_config, context: AppContext
):
    """
    create_or_update_identity_provider call with OIDC as provider type and pre-existing idp
    """
    context.accounts.single_sign_on_helper.create_or_update_identity_provider(
        oidc_payload
    )

    mock_get_provider_details.assert_called_with(oidc_payload)
    mock_get_idp.assert_called()
    context.aws().cognito_idp().create_identity_provider.assert_called_with(
        UserPoolId=context.config().get_string(
            "identity-provider.cognito.user_pool_id", required=True
        ),
        ProviderName=oidc_payload.provider_name,
        ProviderType=oidc_payload.provider_type,
        ProviderDetails="provider-details",
        AttributeMapping={"email": oidc_payload.provider_email_attribute},
        IdpIdentifiers=["single-sign-on-identity-provider"],
    )
    context.aws().cognito_idp().delete_identity_provider.assert_called_with(
        UserPoolId=context.config().get_string(
            "identity-provider.cognito.user_pool_id", required=True
        ),
        ProviderName=saml_payload.provider_name,
    )
    mock_update_config.has_calls(
        [
            ("cognito.sso_idp_provider_name", oidc_payload.provider_name),
            ("cognito.sso_idp_provider_type", oidc_payload.provider_type),
            ("cognito.sso_idp_identifier", "single-sign-on-identity-provider"),
            (
                "cognito.sso_idp_provider_email_attribute",
                oidc_payload.provider_email_attribute,
            ),
        ]
    )


@patch.object(SingleSignOnHelper, "_update_config_entry")
@patch.object(
    SingleSignOnHelper,
    "get_callback_logout_urls",
    return_value=(["test.callback.url"], ["test.logout.url"]),
)
def test_create_user_pool_client(
    mock_get_callback_logout_urls, mock_update_config, context: AppContext
):
    """
    create_or_update_user_pool_client with no pre-existing user pool client
    and no pre-existing secret
    """
    context.accounts.single_sign_on_helper.create_or_update_user_pool_client(
        provider_name=saml_payload.provider_name, refresh_token_validity_hours=20
    )

    mock_get_callback_logout_urls.assert_called()
    argsList = context.aws().cognito_idp().create_user_pool_client.call_args
    create_user_pool_client_result = (
        context.aws().cognito_idp().create_user_pool_client.return_value
    )
    assert create_user_pool_client_result == {
        "UserPoolClient": {"ClientId": "test-id", "ClientSecret": "test-secret"}
    }
    assert argsList[1]["RefreshTokenValidity"] == 20
    assert argsList[1]["CallbackURLs"] == ["test.callback.url"]
    assert argsList[1]["LogoutURLs"] == ["test.logout.url"]
    assert argsList[1]["SupportedIdentityProviders"] == [saml_payload.provider_name]
    secret_name = f"{context._options.cluster_name}-sso-client-secret"
    secret_tags = [
        {
            "Key": constants.IDEA_TAG_ENVIRONMENT_NAME,
            "Value": context._options.cluster_name,
        },
        {
            "Key": constants.IDEA_TAG_MODULE_NAME,
            "Value": constants.MODULE_CLUSTER_MANAGER,
        },
    ]
    context.aws().secretsmanager().describe_secret.assert_called_with(
        SecretId=secret_name
    )
    describe_secret_result = context.aws().secretsmanager().describe_secret.return_value
    assert describe_secret_result == None
    secret_arn = (
        context.aws()
        .secretsmanager()
        .create_secret.assert_called_with(
            **{
                "Name": secret_name,
                "Description": f"Single Sign-On OAuth2 Client Secret for Cluster: {context._options.cluster_name}",
                "Tags": secret_tags,
                "SecretString": create_user_pool_client_result["UserPoolClient"][
                    "ClientSecret"
                ],
            }
        )
    )

    mock_update_config.has_calls(
        [
            (
                "cognito.sso_client_id",
                create_user_pool_client_result["UserPoolClient"]["ClientSecret"],
            ),
            ("cognito.sso_client_secret", secret_arn),
        ]
    )


@patch.object(SingleSignOnHelper, "_update_config_entry")
@patch.object(
    SingleSignOnHelper,
    "get_callback_logout_urls",
    return_value=(["test.callback.url"], ["test.logout.url"]),
)
def test_update_user_pool_client(
    mock_get_callback_logout_urls, mock_update_config, context: AppContext
):
    """
    create_or_update_user_pool_client with pre_existing user pool client should
    update user pool
    """
    context.config().put("identity-provider.cognito.sso_client_id", "test-id")

    context.accounts.single_sign_on_helper.create_or_update_user_pool_client(
        provider_name=saml_payload.provider_name, refresh_token_validity_hours=20
    )

    mock_get_callback_logout_urls.assert_called()
    context.aws().cognito_idp().update_user_pool_client.assert_called()
    argsList = context.aws().cognito_idp().update_user_pool_client.call_args
    update_user_pool_client_result = (
        context.aws().cognito_idp().update_user_pool_client.return_value
    )
    assert update_user_pool_client_result == {
        "UserPoolClient": {"ClientId": "test-id", "ClientSecret": "test-secret"}
    }
    assert argsList[1]["RefreshTokenValidity"] == 20
    assert argsList[1]["CallbackURLs"] == ["test.callback.url"]
    assert argsList[1]["LogoutURLs"] == ["test.logout.url"]
    assert argsList[1]["SupportedIdentityProviders"] == [saml_payload.provider_name]

    context.config().put("identity-provider.cognito.sso_client_id", "")


@patch.object(SingleSignOnHelper, "_update_config_entry")
@patch.object(
    SingleSignOnHelper,
    "get_callback_logout_urls",
    return_value=(["test.callback.url"], ["test.logout.url"]),
)
def test_create_user_pool_client_create_secret_with_key(
    mock_get_callback_logout_urls, mock_update_config, context: AppContext
):
    """
    create_or_update_user_pool_client should create secret with provided kms key
    when secret does not exixt and key exists
    """
    context.config().put("cluster.secretsmanager.kms_key_id", "test-key")
    secret_name = f"{context._options.cluster_name}-sso-client-secret"

    context.accounts.single_sign_on_helper.create_or_update_user_pool_client(
        provider_name=saml_payload.provider_name, refresh_token_validity_hours=20
    )

    create_user_pool_client_result = (
        context.aws().cognito_idp().create_user_pool_client.return_value
    )
    secret_name = f"{context._options.cluster_name}-sso-client-secret"
    secret_tags = [
        {
            "Key": constants.IDEA_TAG_ENVIRONMENT_NAME,
            "Value": context._options.cluster_name,
        },
        {
            "Key": constants.IDEA_TAG_MODULE_NAME,
            "Value": constants.MODULE_CLUSTER_MANAGER,
        },
    ]
    context.aws().secretsmanager().describe_secret.assert_called_with(
        SecretId=secret_name
    )
    describe_secret_result = context.aws().secretsmanager().describe_secret.return_value
    assert describe_secret_result == None
    context.aws().secretsmanager().create_secret.assert_called_with(
        **{
            "Name": secret_name,
            "Description": f"Single Sign-On OAuth2 Client Secret for Cluster: {context._options.cluster_name}",
            "Tags": secret_tags,
            "SecretString": create_user_pool_client_result["UserPoolClient"][
                "ClientSecret"
            ],
            "KmsKeyId": "test-key",
        }
    )

    context.config().put("cluster.secretsmanager.kms_key_id", "")


@patch.object(SingleSignOnHelper, "_update_config_entry")
@patch.object(
    SingleSignOnHelper,
    "get_callback_logout_urls",
    return_value=(["test.callback.url"], ["test.logout.url"]),
)
def test_create_user_pool_client_with_existing_secret(
    mock_get_callback_logout_urls, mock_update_config, context: AppContext
):
    """
    create_or_update_user_pool_client should update secret when it exists
    """
    secret_name = f"{context._options.cluster_name}-sso-client-secret"
    context.aws().secretsmanager().describe_secret.return_value = {"ARN": "test:arn"}

    context.accounts.single_sign_on_helper.create_or_update_user_pool_client(
        provider_name=saml_payload.provider_name, refresh_token_validity_hours=20
    )

    create_user_pool_client_result = (
        context.aws().cognito_idp().create_user_pool_client.return_value
    )
    describe_secret_result = context.aws().secretsmanager().describe_secret.return_value
    assert describe_secret_result == {"ARN": "test:arn"}
    context.aws().secretsmanager().update_secret.assert_called_with(
        **{
            "SecretId": describe_secret_result["ARN"],
            "SecretString": create_user_pool_client_result["UserPoolClient"][
                "ClientSecret"
            ],
        }
    )


@patch.object(SingleSignOnHelper, "_update_config_entry")
@patch.object(
    SingleSignOnHelper,
    "get_callback_logout_urls",
    return_value=(["test.callback.url"], ["test.logout.url"]),
)
def test_create_user_pool_client_with_existing_secret_and_key(
    mock_get_callback_logout_urls, mock_update_config, context: AppContext
):
    """
    create_or_update_user_pool_client should update secret when it exists
    with provided kms key when key exists
    """

    context.config().put("cluster.secretsmanager.kms_key_id", "test-key")
    secret_name = f"{context._options.cluster_name}-sso-client-secret"
    context.aws().secretsmanager().describe_secret.return_value = {"ARN": "test:arn"}

    context.accounts.single_sign_on_helper.create_or_update_user_pool_client(
        provider_name=saml_payload.provider_name, refresh_token_validity_hours=20
    )

    create_user_pool_client_result = (
        context.aws().cognito_idp().create_user_pool_client.return_value
    )
    describe_secret_result = context.aws().secretsmanager().describe_secret.return_value
    assert describe_secret_result == {"ARN": "test:arn"}
    context.aws().secretsmanager().update_secret.assert_called_with(
        **{
            "SecretId": describe_secret_result["ARN"],
            "SecretString": create_user_pool_client_result["UserPoolClient"][
                "ClientSecret"
            ],
            "KmsKeyId": "test-key",
        }
    )

    context.config().put("cluster.secretsmanager.kms_key_id", "")


@patch.object(SingleSignOnHelper, "_update_config_entry")
@patch.object(
    SingleSignOnHelper,
    "get_callback_logout_urls",
    return_value=(["test.callback.url"], ["test.logout.url"]),
)
def test_create__or_update_user_pool_client_missing_refresh_token(
    mock_get_callback_logout_urls, mock_update_config, context: AppContext
):
    """
    create_or_update_user_pool_client should set refresh token to 12 when missing
    """
    context.accounts.single_sign_on_helper.create_or_update_user_pool_client(
        provider_name=saml_payload.provider_name, refresh_token_validity_hours=None
    )

    argsList = context.aws().cognito_idp().create_user_pool_client.call_args
    assert argsList[1]["RefreshTokenValidity"] == 12


@patch.object(SingleSignOnHelper, "_update_config_entry")
@patch.object(
    SingleSignOnHelper,
    "get_callback_logout_urls",
    return_value=(["test.callback.url"], ["test.logout.url"]),
)
def test_create__or_update_user_pool_client_gt_max_refresh_token(
    mock_get_callback_logout_urls, mock_update_config, context: AppContext
):
    """
    create_or_update_user_pool_client should set refresh token to 12 when value is greater than max limit
    """
    context.accounts.single_sign_on_helper.create_or_update_user_pool_client(
        provider_name=saml_payload.provider_name, refresh_token_validity_hours=87601
    )

    argsList = context.aws().cognito_idp().create_user_pool_client.call_args
    assert argsList[1]["RefreshTokenValidity"] == 12


@patch.object(SingleSignOnHelper, "_update_config_entry")
@patch.object(
    SingleSignOnHelper,
    "get_callback_logout_urls",
    return_value=(["test.callback.url"], ["test.logout.url"]),
)
def test_create__or_update_user_pool_client_lt_min_refresh_token(
    mock_get_callback_logout_urls, mock_update_config, context: AppContext
):
    """
    create_or_update_user_pool_client with should set refresh token to 12 when value is greater than min limit
    """
    context.accounts.single_sign_on_helper.create_or_update_user_pool_client(
        provider_name=saml_payload.provider_name, refresh_token_validity_hours=0
    )

    argsList = context.aws().cognito_idp().create_user_pool_client.call_args
    assert argsList[1]["RefreshTokenValidity"] == 12


def test_update_config_entry(context: AppContext):
    """
    _update_config_entry should update db and config
    """
    with patch.object(context._config, "put"):
        context.accounts.single_sign_on_helper._update_config_entry("key", "value")

        module_id = context.config().get_module_id(constants.MODULE_IDENTITY_PROVIDER)
        context.config().db.set_config_entry.assert_called_with(
            f"{module_id}.key", "value"
        )
        context.config().put.assert_called_with(f"{module_id}.key", "value")


def test_get_callback_logout_urls(context: AppContext):
    """
    get_callback_logout_urls should return default callback/logout url when no custom dns provided
    """
    load_balancer_dns_name = context.config().get_string(
        "cluster.load_balancers.external_alb.load_balancer_dns_name", required=True
    )

    result = context.accounts.single_sign_on_helper.get_callback_logout_urls()
    assert result == (
        [f"https://{load_balancer_dns_name}/sso/oauth2/callback"],
        [f"https://{load_balancer_dns_name}"],
    )


def test_get_callback_logout_urls_with_custom_dns_and_context_path(context: AppContext):
    """
    get_callback_logout_urls should return default callback/logout url and custom url when custom dns and context path provided
    """
    custom_dns = "test.custom.dns"
    context_path = "custom/path"
    context.config().put(
        "cluster.load_balancers.external_alb.certificates.custom_dns_name", custom_dns
    )
    context.config().put(
        "cluster-manager.server.web_resources_context_path", context_path
    )
    load_balancer_dns_name = context.config().get_string(
        "cluster.load_balancers.external_alb.load_balancer_dns_name", required=True
    )

    result = context.accounts.single_sign_on_helper.get_callback_logout_urls()

    assert result == (
        [
            f"https://{load_balancer_dns_name}/{context_path}/oauth2/callback",
            f"https://{custom_dns}/{context_path}/oauth2/callback",
        ],
        [
            f"https://{load_balancer_dns_name}/{context_path}",
            f"https://{custom_dns}/{context_path}",
        ],
    )

    context.config().put(
        "cluster.load_balancers.external_alb.certificates.custom_dns_name", ""
    )
    context.config().put("cluster-manager.server.web_resources_context_path", "")


@patch.object(saml_payload, "saml_metadata_url", "")
def test_get_saml_provider_details_with_missing_provider_details(context: AppContext):
    """
    get_saml_provider_details with missing url and file
    """
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.single_sign_on_helper.get_saml_provider_details(saml_payload)

        assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
        assert (
            "Either one of [saml_metadata_url, saml_metadata_file] is required, when provider_type = SAML"
            in exc_info.value.message
        )


def test_get_saml_provider_details_with_url(context: AppContext):
    """
    get_saml_provider_details should return dict with the metadata url
    """
    results = context.accounts.single_sign_on_helper.get_saml_provider_details(
        saml_payload
    )

    assert results == {
        "IDPSignout": "true",
        "MetadataURL": saml_payload.saml_metadata_url,
    }


@patch.object(saml_payload, "saml_metadata_file", Utils.base64_encode("test-file"))
@patch.object(saml_payload, "saml_metadata_url", "")
def test_get_saml_provider_details_with_file(context: AppContext):
    """
    get_saml_provider_details should return dict with the decoded
    metadata file contents
    """
    results = context.accounts.single_sign_on_helper.get_saml_provider_details(
        saml_payload
    )

    assert results == {
        "IDPSignout": "true",
        "MetadataFile": Utils.base64_decode(saml_payload.saml_metadata_file),
    }


@patch.object(oidc_payload, "oidc_client_id", "")
def test_get_oidc_provider_details_with_missing_client_id(context: AppContext):
    """
    get_oidc_provider_details with missing client_id
    """
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.single_sign_on_helper.get_oidc_provider_details(oidc_payload)

        assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
        assert "oidc_client_id is required" in exc_info.value.message


@patch.object(oidc_payload, "oidc_client_secret", "")
def test_get_oidc_provider_details_with_missing_client_secret(context: AppContext):
    """
    get_oidc_provider_details with missing client_secret
    """
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.single_sign_on_helper.get_oidc_provider_details(oidc_payload)
        assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
        assert "oidc_client_secret is required" in exc_info.value.message


@patch.object(oidc_payload, "oidc_issuer", "")
def test_get_oidc_provider_details_with_missing_issuer(context: AppContext):
    """
    get_oidc_provider_details with missing issuer
    """
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.single_sign_on_helper.get_oidc_provider_details(oidc_payload)
        assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
        assert "oidc_cissuer is required" in exc_info.value.message


def test_get_oidc_provider_details(context: AppContext):
    """
    get_oidc_provider_details should return dict with all provided provider details
    """
    result = context.accounts.single_sign_on_helper.get_oidc_provider_details(
        oidc_payload
    )
    assert result == {
        "client_id": oidc_payload.oidc_client_id,
        "client_secret": oidc_payload.oidc_client_secret,
        "oidc_issuer": oidc_payload.oidc_issuer,
        "attributes_request_method": oidc_payload.oidc_attributes_request_method,
        "authorize_scopes": oidc_payload.oidc_authorize_scopes,
        "authorize_url": oidc_payload.oidc_authorize_url,
        "token_url": oidc_payload.oidc_token_url,
        "attributes_url": oidc_payload.oidc_attributes_url,
        "jwks_uri": oidc_payload.oidc_jwks_uri,
    }


def test_get_identity_provider(context: AppContext):
    """
    get_identity_provider should return identity provider result from botocore cognito_idp call
    """
    result = context.accounts.single_sign_on_helper.get_identity_provider()
    cognito_idp_result = (
        context.aws().cognito_idp().get_identity_provider_by_identifier.return_value
    )

    context.aws().cognito_idp().get_identity_provider_by_identifier.assert_called_with(
        UserPoolId=context.config().get_string(
            "identity-provider.cognito.user_pool_id", required=True
        ),
        IdpIdentifier="single-sign-on-identity-provider",
    )

    assert result == cognito_idp_result["IdentityProvider"]


def test_link_existing_users(context: AppContext):
    """
    list_existing_users should skip cluster admin and users with
    user_status EXTERNAL_PROVIDER, and link all others.
    """
    context.accounts.single_sign_on_helper.link_existing_users()

    call_count = context.aws().cognito_idp().admin_link_provider_for_user.call_count
    assert call_count == 1
    context.aws().cognito_idp().admin_link_provider_for_user.assert_called_with(
        UserPoolId=context.config().get_string(
            "identity-provider.cognito.user_pool_id"
        ),
        DestinationUser={
            "ProviderName": "Cognito",
            "ProviderAttributeName": "cognito:username",
            "ProviderAttributeValue": "unlinked",
        },
        SourceUser={
            "ProviderName": context.config().get_string(
                "identity-provider.cognito.sso_idp_provider_name"
            ),
            "ProviderAttributeName": context.config().get_string(
                "identity-provider.cognito.sso_idp_provider_email_attribute"
            ),
            "ProviderAttributeValue": "unlinked@user",
        },
    )
