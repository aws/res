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


import base64
import os
import sys
from unittest.mock import patch

import pytest
from constants import CLUSTER_NAME, LOAD_BALANCER_DNS, SECRET_ARN, USER_POOL_ID
from ideasdk.utils import Utils
from lambda_functions.configure_sso import MODULE_IDENTITY_PROVIDER, SingleSignOnHelper

saml_payload = {
    "provider_name": "saml",
    "provider_type": "SAML",
    "provider_email_attribute": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
    "saml_metadata_url": "test.url",
    "saml_metadata_file": "",
}

oidc_payload = {
    "provider_name": "oidc",
    "provider_type": "OIDC",
    "provider_email_attribute": "email",
    "oidc_client_id": "test-client-id",
    "oidc_client_secret": "test-secret",
    "oidc_issuer": "test-issuer",
    "oidc_attributes_request_method": "GET",
    "oidc_authorize_scopes": "oidc",
    "oidc_authorize_url": "oidc.authorize.test",
    "oidc_token_url": "oidc.token.test",
    "oidc_attributes_url": "oidc.attr.test",
    "oidc_jwks_uri": "oidc.jwks.test",
}


@patch.object(SingleSignOnHelper, "_update_config_entry")
@patch.object(SingleSignOnHelper, "create_or_update_user_pool_client")
@patch.object(SingleSignOnHelper, "create_or_update_identity_provider")
def test_configure_sso(
    mock_create_or_update_identity_provider,
    mock_create_or_update_user_pool_client,
    mock_config_entry_update,
    sso_helper: SingleSignOnHelper,
):
    """
    configure_sso should create or update user pool client, create or update identity provider
    """

    sso_helper.configure_sso(request=saml_payload)
    assert mock_config_entry_update.call_count == 2
    mock_create_or_update_identity_provider.assert_called_with(saml_payload)
    mock_create_or_update_user_pool_client.assert_called_with(
        provider_name=saml_payload.get("provider_name"),
        refresh_token_validity_hours=None,
    )


@patch.dict(saml_payload, [("provider_name", "")])
def test_create_or_update_identity_provider_missing_provider_name(
    sso_helper: SingleSignOnHelper,
) -> None:
    """
    create_or_update_user_pool_client with missing provider name
    """
    with pytest.raises(Exception) as exc_info:
        sso_helper.create_or_update_identity_provider(saml_payload)
        assert str(exc_info) == "provider_name is required"


@patch.dict(saml_payload, [("provider_name", "Cognito")])
def test_create_or_update_identity_provider_invalid_provider_name(
    sso_helper: SingleSignOnHelper,
):
    """
    create_or_update_user_pool_client with missing provider name
    """
    with pytest.raises(Exception) as exc_info:
        sso_helper.create_or_update_identity_provider(saml_payload)
        assert (
            lambda_functions.configure_sso.SSO_SOURCE_PROVIDER_NAME_ERROR_MESSAGE
            == str(exc_info)
        )


@patch.dict(saml_payload, [("provider_type", "")])
def test_create_or_update_identity_provider_missing_provider_type(
    sso_helper: SingleSignOnHelper,
):
    """
    create_or_update_user_pool_client with missing provider type
    """
    with pytest.raises(Exception) as exc_info:
        sso_helper.create_or_update_identity_provider(saml_payload)
        assert "provider_type is required" == str(exc_info)


@patch.dict(saml_payload, [("provider_email_attribute", "")])
def test_create_or_update_identity_provider_missing_provider_email_attr(
    sso_helper: SingleSignOnHelper,
):
    """
    create_or_update_user_pool_client with missing provider email attribute
    """
    with pytest.raises(Exception) as exc_info:
        sso_helper.create_or_update_identity_provider(saml_payload)

        assert "provider_email_attribute is required" == str(exc_info)


@patch.dict(saml_payload, [("provider_type", "invalid")])
def test_create_or_update_identity_provider_invalid_provider_type(
    sso_helper: SingleSignOnHelper,
):
    """
    create_or_update_user_pool_client with invalid provider type
    """
    with pytest.raises(Exception) as exc_info:
        sso_helper.create_or_update_identity_provider(saml_payload)
        assert "provider type must be one of: SAML or OIDC" == str(exc_info)


@patch.object(SingleSignOnHelper, "_update_config_entry")
@patch.object(SingleSignOnHelper, "get_identity_provider", return_value=None)
@patch.object(
    SingleSignOnHelper, "get_saml_provider_details", return_value="provider-details"
)
def test_create_identity_provider_saml(
    mock_get_provider_details,
    mock_get_idp,
    mock_update_config,
    sso_helper: SingleSignOnHelper,
):
    """
    create_or_update_identity_provider call with SAML as provider type and no pre-existing idp
    """
    sso_helper.create_or_update_identity_provider(saml_payload)
    mock_get_provider_details.assert_called_with(saml_payload)
    mock_get_idp.assert_called()
    sso_helper.cognito_client.create_identity_provider.assert_called_with(
        UserPoolId=USER_POOL_ID,
        ProviderName=saml_payload.get("provider_name"),
        ProviderType=saml_payload.get("provider_type"),
        ProviderDetails="provider-details",
        AttributeMapping={"email": saml_payload.get("provider_email_attribute")},
        IdpIdentifiers=["single-sign-on-identity-provider"],
    )
    mock_update_config.assert_any_call(
        "cognito.sso_idp_provider_email_attribute",
        saml_payload.get("provider_email_attribute"),
    )
    mock_update_config.assert_any_call(
        "cognito.sso_idp_provider_name", saml_payload.get("provider_name")
    )
    mock_update_config.assert_any_call(
        "cognito.sso_idp_provider_type", saml_payload.get("provider_type")
    )
    mock_update_config.assert_any_call(
        "cognito.sso_idp_identifier", "single-sign-on-identity-provider"
    )


@patch.object(SingleSignOnHelper, "_update_config_entry")
@patch.object(SingleSignOnHelper, "get_identity_provider", return_value=None)
@patch.object(
    SingleSignOnHelper, "get_oidc_provider_details", return_value="provider-details"
)
def test_create_identity_provider_oidc(
    mock_get_provider_details,
    mock_get_idp,
    mock_update_config,
    sso_helper: SingleSignOnHelper,
):
    """
    create_or_update_identity_provider call with OIDC as provider type and no pre-existing idp
    """
    sso_helper.create_or_update_identity_provider(oidc_payload)

    mock_get_provider_details.assert_called_with(oidc_payload)
    mock_get_idp.assert_called()
    sso_helper.cognito_client.create_identity_provider.assert_called_with(
        UserPoolId=USER_POOL_ID,
        ProviderName=oidc_payload.get("provider_name"),
        ProviderType=oidc_payload.get("provider_type"),
        ProviderDetails="provider-details",
        AttributeMapping={"email": oidc_payload.get("provider_email_attribute")},
        IdpIdentifiers=["single-sign-on-identity-provider"],
    )

    mock_update_config.assert_any_call(
        "cognito.sso_idp_provider_email_attribute",
        oidc_payload.get("provider_email_attribute"),
    )
    mock_update_config.assert_any_call(
        "cognito.sso_idp_provider_name", oidc_payload.get("provider_name")
    )
    mock_update_config.assert_any_call(
        "cognito.sso_idp_provider_type", oidc_payload.get("provider_type")
    )
    mock_update_config.assert_any_call(
        "cognito.sso_idp_identifier", "single-sign-on-identity-provider"
    )


@patch.object(SingleSignOnHelper, "_update_config_entry")
@patch.object(
    SingleSignOnHelper,
    "get_identity_provider",
    return_value={
        "ProviderName": oidc_payload.get("provider_name"),
        "ProviderType": oidc_payload.get("provider_type"),
    },
)
@patch.object(
    SingleSignOnHelper, "get_oidc_provider_details", return_value="provider-details"
)
def test_update_identity_provider_oidc(
    mock_get_provider_details,
    mock_get_idp,
    mock_update_config,
    sso_helper: SingleSignOnHelper,
):
    """
    create_or_update_identity_provider call with OIDC as provider type and pre-existing idp
    """
    sso_helper.create_or_update_identity_provider(oidc_payload)

    mock_get_provider_details.assert_called_with(oidc_payload)
    mock_get_idp.assert_called()
    sso_helper.cognito_client.update_identity_provider.assert_called_with(
        UserPoolId=USER_POOL_ID,
        ProviderName=oidc_payload.get("provider_name"),
        ProviderDetails="provider-details",
        AttributeMapping={"email": oidc_payload.get("provider_email_attribute")},
        IdpIdentifiers=["single-sign-on-identity-provider"],
    )
    mock_update_config.assert_any_call(
        "cognito.sso_idp_provider_name", oidc_payload.get("provider_name")
    )
    mock_update_config.assert_any_call(
        "cognito.sso_idp_provider_type", oidc_payload.get("provider_type")
    )
    mock_update_config.assert_any_call(
        "cognito.sso_idp_identifier", "single-sign-on-identity-provider"
    )
    mock_update_config.assert_any_call(
        "cognito.sso_idp_provider_email_attribute",
        oidc_payload.get("provider_email_attribute"),
    )


@patch.object(SingleSignOnHelper, "_update_config_entry")
@patch.object(
    SingleSignOnHelper,
    "get_identity_provider",
    return_value={
        # Different name and type
        "ProviderName": saml_payload.get("provider_name"),
        "ProviderType": saml_payload.get("provider_type"),
    },
)
@patch.object(
    SingleSignOnHelper, "get_oidc_provider_details", return_value="provider-details"
)
def test_recreate_identity_provider_oidc(
    mock_get_provider_details,
    mock_get_idp,
    mock_update_config,
    sso_helper: SingleSignOnHelper,
):
    """
    create_or_update_identity_provider call with OIDC as provider type and pre-existing idp
    """
    sso_helper.create_or_update_identity_provider(oidc_payload)

    mock_get_provider_details.assert_called_with(oidc_payload)
    mock_get_idp.assert_called()
    sso_helper.cognito_client.create_identity_provider.assert_called_with(
        UserPoolId=USER_POOL_ID,
        ProviderName=oidc_payload.get("provider_name"),
        ProviderType=oidc_payload.get("provider_type"),
        ProviderDetails="provider-details",
        AttributeMapping={"email": oidc_payload.get("provider_email_attribute")},
        IdpIdentifiers=["single-sign-on-identity-provider"],
    )
    sso_helper.cognito_client.delete_identity_provider.assert_called_with(
        UserPoolId=USER_POOL_ID,
        ProviderName=saml_payload.get("provider_name"),
    )
    mock_update_config.assert_any_call(
        "cognito.sso_idp_provider_name", oidc_payload.get("provider_name")
    )
    mock_update_config.assert_any_call(
        "cognito.sso_idp_provider_type", oidc_payload.get("provider_type")
    )
    mock_update_config.assert_any_call(
        "cognito.sso_idp_identifier", "single-sign-on-identity-provider"
    )
    mock_update_config.assert_any_call(
        "cognito.sso_idp_provider_email_attribute",
        oidc_payload.get("provider_email_attribute"),
    )


@patch.object(SingleSignOnHelper, "_update_config_entry")
@patch.object(
    SingleSignOnHelper,
    "get_callback_logout_urls",
    return_value=(["test.callback.url"], ["test.logout.url"]),
)
def test_create_user_pool_client(
    mock_get_callback_logout_urls, mock_update_config, sso_helper: SingleSignOnHelper
):
    """
    create_or_update_user_pool_client with no pre-existing user pool client
    and no pre-existing secret
    """
    sso_helper.create_or_update_user_pool_client(
        provider_name=saml_payload.get("provider_name"), refresh_token_validity_hours=20
    )

    mock_get_callback_logout_urls.assert_called()
    argsList = sso_helper.cognito_client.create_user_pool_client.call_args
    create_user_pool_client_result = (
        sso_helper.cognito_client.create_user_pool_client.return_value
    )
    assert create_user_pool_client_result == {
        "UserPoolClient": {"ClientId": "test-id", "ClientSecret": "test-secret"}
    }
    assert argsList[1]["RefreshTokenValidity"] == 20
    assert argsList[1]["CallbackURLs"] == ["test.callback.url"]
    assert argsList[1]["LogoutURLs"] == ["test.logout.url"]
    assert argsList[1]["SupportedIdentityProviders"] == [
        saml_payload.get("provider_name")
    ]
    secret_name = f"{CLUSTER_NAME}-sso-client-secret"
    secret_tags = [
        {
            "Key": "res:EnvironmentName",
            "Value": CLUSTER_NAME,
        },
        {
            "Key": "res:ModuleName",
            "Value": "cluster-manager",
        },
    ]
    sso_helper.secretsmanager_client.describe_secret.assert_called_with(
        SecretId=secret_name
    )
    describe_secret_result = (
        sso_helper.secretsmanager_client.describe_secret.return_value
    )
    assert describe_secret_result == None

    mock_update_config.assert_any_call(
        "cognito.sso_client_id",
        create_user_pool_client_result["UserPoolClient"]["ClientId"],
    )
    mock_update_config.assert_any_call("cognito.sso_client_secret", SECRET_ARN)


@patch.object(SingleSignOnHelper, "_update_config_entry")
@patch.object(
    SingleSignOnHelper,
    "get_callback_logout_urls",
    return_value=(["test.callback.url"], ["test.logout.url"]),
)
def test_update_user_pool_client(
    mock_get_callback_logout_urls, mock_update_config, sso_helper: SingleSignOnHelper
):
    """
    create_or_update_user_pool_client with pre_existing user pool client should
    update user pool
    """

    sso_helper.config.add_to_db("identity-provider.cognito.sso_client_id", "test-id")
    sso_helper.create_or_update_user_pool_client(
        provider_name=saml_payload.get("provider_name"), refresh_token_validity_hours=20
    )

    mock_get_callback_logout_urls.assert_called()
    sso_helper.cognito_client.update_user_pool_client.assert_called()
    argsList = sso_helper.cognito_client.update_user_pool_client.call_args
    update_user_pool_client_result = (
        sso_helper.cognito_client.update_user_pool_client.return_value
    )
    assert update_user_pool_client_result == {
        "UserPoolClient": {"ClientId": "test-id", "ClientSecret": "test-secret"}
    }
    assert argsList[1]["RefreshTokenValidity"] == 20
    assert argsList[1]["CallbackURLs"] == ["test.callback.url"]
    assert argsList[1]["LogoutURLs"] == ["test.logout.url"]
    assert argsList[1]["SupportedIdentityProviders"] == [
        saml_payload.get("provider_name")
    ]

    sso_helper.config.remove_from_db("identity-provider.cognito.sso_client_id")


@patch.object(SingleSignOnHelper, "_update_config_entry")
@patch.object(
    SingleSignOnHelper,
    "get_callback_logout_urls",
    return_value=(["test.callback.url"], ["test.logout.url"]),
)
def test_create_user_pool_client_create_secret_with_key(
    mock_get_callback_logout_urls, mock_update_config, sso_helper: SingleSignOnHelper
):
    """
    create_or_update_user_pool_client should create secret with provided kms key
    when secret does not exixt and key exists
    """
    sso_helper.config.add_to_db("cluster.secretsmanager.kms_key_id", "test-key")
    secret_name = f"{CLUSTER_NAME}-sso-client-secret"

    sso_helper.create_or_update_user_pool_client(
        provider_name=saml_payload.get("provider_name"), refresh_token_validity_hours=20
    )

    create_user_pool_client_result = (
        sso_helper.cognito_client.create_user_pool_client.return_value
    )
    secret_name = f"{CLUSTER_NAME}-sso-client-secret"
    secret_tags = [
        {
            "Key": "res:EnvironmentName",
            "Value": CLUSTER_NAME,
        },
        {
            "Key": "res:ModuleName",
            "Value": "cluster-manager",
        },
    ]
    sso_helper.secretsmanager_client.describe_secret.assert_called_with(
        SecretId=secret_name
    )
    describe_secret_result = (
        sso_helper.secretsmanager_client.describe_secret.return_value
    )
    assert describe_secret_result == None
    sso_helper.secretsmanager_client.create_secret.assert_called_with(
        **{
            "Name": secret_name,
            "Description": f"Single Sign-On OAuth2 Client Secret for Cluster: {CLUSTER_NAME}",
            "Tags": secret_tags,
            "SecretString": create_user_pool_client_result["UserPoolClient"][
                "ClientSecret"
            ],
            "KmsKeyId": "test-key",
        }
    )

    sso_helper.config.remove_from_db("cluster.secretsmanager.kms_key_id")


@patch.object(SingleSignOnHelper, "_update_config_entry")
@patch.object(
    SingleSignOnHelper,
    "get_callback_logout_urls",
    return_value=(["test.callback.url"], ["test.logout.url"]),
)
def test_create_user_pool_client_with_existing_secret(
    mock_get_callback_logout_urls, mock_update_config, sso_helper: SingleSignOnHelper
):
    """
    create_or_update_user_pool_client should update secret when it exists
    """
    secret_name = f"{CLUSTER_NAME}-sso-client-secret"
    sso_helper.secretsmanager_client.describe_secret.return_value = {"ARN": "test:arn"}

    sso_helper.create_or_update_user_pool_client(
        provider_name=saml_payload.get("provider_name"), refresh_token_validity_hours=20
    )

    create_user_pool_client_result = (
        sso_helper.cognito_client.create_user_pool_client.return_value
    )
    describe_secret_result = (
        sso_helper.secretsmanager_client.describe_secret.return_value
    )
    assert describe_secret_result == {"ARN": "test:arn"}
    sso_helper.secretsmanager_client.update_secret.assert_called_with(
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
    mock_get_callback_logout_urls, mock_update_config, sso_helper: SingleSignOnHelper
):
    """
    create_or_update_user_pool_client should update secret when it exists
    with provided kms key when key exists
    """

    sso_helper.config.add_to_db("cluster.secretsmanager.kms_key_id", "test-key")
    secret_name = f"{CLUSTER_NAME}-sso-client-secret"
    sso_helper.secretsmanager_client.describe_secret.return_value = {"ARN": "test:arn"}

    sso_helper.create_or_update_user_pool_client(
        provider_name=saml_payload.get("provider_name"), refresh_token_validity_hours=20
    )

    create_user_pool_client_result = (
        sso_helper.cognito_client.create_user_pool_client.return_value
    )
    describe_secret_result = (
        sso_helper.secretsmanager_client.describe_secret.return_value
    )
    assert describe_secret_result == {"ARN": "test:arn"}
    sso_helper.secretsmanager_client.update_secret.assert_called_with(
        **{
            "SecretId": describe_secret_result["ARN"],
            "SecretString": create_user_pool_client_result["UserPoolClient"][
                "ClientSecret"
            ],
            "KmsKeyId": "test-key",
        }
    )

    sso_helper.config.remove_from_db("cluster.secretsmanager.kms_key_id")


@patch.object(SingleSignOnHelper, "_update_config_entry")
@patch.object(
    SingleSignOnHelper,
    "get_callback_logout_urls",
    return_value=(["test.callback.url"], ["test.logout.url"]),
)
def test_create__or_update_user_pool_client_missing_refresh_token(
    mock_get_callback_logout_urls, mock_update_config, sso_helper: SingleSignOnHelper
):
    """
    create_or_update_user_pool_client should set refresh token to 12 when missing
    """
    sso_helper.create_or_update_user_pool_client(
        provider_name=saml_payload.get("provider_name"),
        refresh_token_validity_hours=None,
    )

    argsList = sso_helper.cognito_client.create_user_pool_client.call_args
    assert argsList[1]["RefreshTokenValidity"] == 12


@patch.object(SingleSignOnHelper, "_update_config_entry")
@patch.object(
    SingleSignOnHelper,
    "get_callback_logout_urls",
    return_value=(["test.callback.url"], ["test.logout.url"]),
)
def test_create__or_update_user_pool_client_gt_max_refresh_token(
    mock_get_callback_logout_urls, mock_update_config, sso_helper: SingleSignOnHelper
):
    """
    create_or_update_user_pool_client should set refresh token to 12 when value is greater than max limit
    """
    sso_helper.create_or_update_user_pool_client(
        provider_name=saml_payload.get("provider_name"),
        refresh_token_validity_hours=87601,
    )

    argsList = sso_helper.cognito_client.create_user_pool_client.call_args
    assert argsList[1]["RefreshTokenValidity"] == 12


@patch.object(SingleSignOnHelper, "_update_config_entry")
@patch.object(
    SingleSignOnHelper,
    "get_callback_logout_urls",
    return_value=(["test.callback.url"], ["test.logout.url"]),
)
def test_create__or_update_user_pool_client_lt_min_refresh_token(
    mock_get_callback_logout_urls, mock_update_config, sso_helper: SingleSignOnHelper
):
    """
    create_or_update_user_pool_client with should set refresh token to 12 when value is greater than min limit
    """
    sso_helper.create_or_update_user_pool_client(
        provider_name=saml_payload.get("provider_name"), refresh_token_validity_hours=0
    )

    argsList = sso_helper.cognito_client.create_user_pool_client.call_args
    assert argsList[1]["RefreshTokenValidity"] == 12


def test_update_config_entry(sso_helper: SingleSignOnHelper):
    """
    _update_config_entry should update db and config
    """
    with patch.object(sso_helper, "config"):
        sso_helper._update_config_entry("key", "value")
        sso_helper.config.update_item.assert_called_with(
            f"{MODULE_IDENTITY_PROVIDER}.key", "value"
        )


def test_get_callback_logout_urls(sso_helper: SingleSignOnHelper):
    """
    get_callback_logout_urls should return default callback/logout url when no custom dns provided
    """

    result = sso_helper.get_callback_logout_urls()
    assert result == (
        [f"https://{LOAD_BALANCER_DNS}/sso/oauth2/callback"],
        [f"https://{LOAD_BALANCER_DNS}"],
    )


def test_get_callback_logout_urls_with_custom_dns_and_context_path(
    sso_helper: SingleSignOnHelper,
):
    """
    get_callback_logout_urls should return default callback/logout url and custom url when custom dns and context path provided
    """
    custom_dns = "test.custom.dns"
    context_path = "custom/path"
    sso_helper.config.add_to_db(
        "cluster.load_balancers.external_alb.certificates.custom_dns_name", custom_dns
    )
    sso_helper.config.add_to_db(
        "cluster-manager.server.web_resources_context_path", context_path
    )

    result = sso_helper.get_callback_logout_urls()

    assert result == (
        [
            f"https://{LOAD_BALANCER_DNS}/{context_path}/oauth2/callback",
            f"https://{custom_dns}/{context_path}/oauth2/callback",
        ],
        [
            f"https://{LOAD_BALANCER_DNS}/{context_path}",
            f"https://{custom_dns}/{context_path}",
        ],
    )

    sso_helper.config.add_to_db(
        "cluster.load_balancers.external_alb.certificates.custom_dns_name", ""
    )
    sso_helper.config.remove_from_db(
        "cluster-manager.server.web_resources_context_path"
    )


@patch.dict(saml_payload, [("saml_metadata_url", "")])
def test_get_saml_provider_details_with_missing_provider_details(
    sso_helper: SingleSignOnHelper,
):
    """
    get_saml_provider_details with missing url and file
    """
    with pytest.raises(Exception) as exc_info:
        sso_helper.get_saml_provider_details(saml_payload)
        assert (
            "Either one of [saml_metadata_url, saml_metadata_file] is required, when provider_type = SAML"
            == str(exc_info)
        )


def test_get_saml_provider_details_with_url(sso_helper: SingleSignOnHelper):
    """
    get_saml_provider_details should return dict with the metadata url
    """
    results = sso_helper.get_saml_provider_details(saml_payload)

    assert results == {
        "IDPSignout": "true",
        "MetadataURL": saml_payload.get("saml_metadata_url"),
    }


@patch.dict(saml_payload, [("saml_metadata_file", Utils.base64_encode("test file"))])
@patch.dict(saml_payload, [("saml_metadata_url", "")])
def test_get_saml_provider_details_with_file(sso_helper: SingleSignOnHelper):
    """
    get_saml_provider_details should return dict with the decoded
    metadata file contents
    """
    results = sso_helper.get_saml_provider_details(saml_payload)

    assert results == {
        "IDPSignout": "true",
        "MetadataFile": Utils.base64_decode(saml_payload.get("saml_metadata_file")),
    }


@patch.dict(oidc_payload, [("oidc_client_id", "")])
def test_get_oidc_provider_details_with_missing_client_id(
    sso_helper: SingleSignOnHelper,
):
    """
    get_oidc_provider_details with missing client_id
    """
    with pytest.raises(Exception) as exc_info:
        sso_helper.get_oidc_provider_details(oidc_payload)
        assert "oidc_client_id is required" == str(exc_info)


@patch.dict(oidc_payload, [("oidc_client_secret", "")])
def test_get_oidc_provider_details_with_missing_client_secret(
    sso_helper: SingleSignOnHelper,
):
    """
    get_oidc_provider_details with missing client_secret
    """
    with pytest.raises(Exception) as exc_info:
        sso_helper.get_oidc_provider_details(oidc_payload)
        assert "oidc_client_secret is required" == str(exc_info)


@patch.dict(oidc_payload, [("oidc_issuer", "")])
def test_get_oidc_provider_details_with_missing_issuer(sso_helper: SingleSignOnHelper):
    """
    get_oidc_provider_details with missing issuer
    """
    with pytest.raises(Exception) as exc_info:
        sso_helper.get_oidc_provider_details(oidc_payload)
        assert "oidc_cissuer is required" == str(exc_info)


def test_get_oidc_provider_details(sso_helper: SingleSignOnHelper):
    """
    get_oidc_provider_details should return dict with all provided provider details
    """
    result = sso_helper.get_oidc_provider_details(oidc_payload)
    assert result == {
        "client_id": oidc_payload.get("oidc_client_id"),
        "client_secret": oidc_payload.get("oidc_client_secret"),
        "oidc_issuer": oidc_payload.get("oidc_issuer"),
        "attributes_request_method": oidc_payload.get("oidc_attributes_request_method"),
        "authorize_scopes": oidc_payload.get("oidc_authorize_scopes"),
        "authorize_url": oidc_payload.get("oidc_authorize_url"),
        "token_url": oidc_payload.get("oidc_token_url"),
        "attributes_url": oidc_payload.get("oidc_attributes_url"),
        "jwks_uri": oidc_payload.get("oidc_jwks_uri"),
    }


def test_get_identity_provider(sso_helper: SingleSignOnHelper):
    """
    get_identity_provider should return identity provider result from botocore cognito_idp call
    """
    result = sso_helper.get_identity_provider()
    cognito_idp_result = (
        sso_helper.cognito_client.get_identity_provider_by_identifier.return_value
    )

    sso_helper.cognito_client.get_identity_provider_by_identifier.assert_called_with(
        UserPoolId=USER_POOL_ID,
        IdpIdentifier="single-sign-on-identity-provider",
    )

    assert result == cognito_idp_result["IdentityProvider"]
