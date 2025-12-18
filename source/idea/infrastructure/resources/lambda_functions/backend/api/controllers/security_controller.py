#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import os

from connexion.exceptions import OAuthProblem
from res.constants import COGNITO_SSO_IDP_PROVIDER_NAME  # type: ignore
from res.resources import accounts, token as token_resource  # type: ignore
from res.resources.cluster_settings import CLUSTER_SETTINGS_TABLE_NAME  # type: ignore
from res.utils import auth_utils, table_utils  # type: ignore


def bearer_auth(token, request):
    """
    Check and retrieve authentication information from custom bearer token.
    Returned value will be passed in 'token_info' parameter of your operation function, if there is one.
    'sub' or 'uid' will be set in 'user' parameter of your operation function, if there is one.

    :param token: Token provided by Authorization header
    :type token: str
    :param request: The request object containing headers and authorization information
    :type request: connexion.request
    :return: Decoded token information or None if token is invalid
    :rtype: dict | None
    """
    try:
        decoded_token = token_resource.decode_token(token=token, verify_exp=True)

        if not decoded_token.get("username"):
            raise OAuthProblem("Username missing in token")

        idp_name_record = table_utils.get_item(
            table_name=CLUSTER_SETTINGS_TABLE_NAME,
            key={"key": COGNITO_SSO_IDP_PROVIDER_NAME},
        )
        idp_name = idp_name_record.get("value") if idp_name_record else None
        username = auth_utils.get_ddb_user_name(
            username=decoded_token["username"], idp_name=idp_name
        )
    except Exception as e:
        # Check test mode
        if os.environ.get("RES_TEST_MODE", "").lower() == "true":
            # In test mode, extract username from X_RES_TEST_USERNAME header
            # This allows API testing to bypass authentication while still providing user context
            username = request.headers.get("X_RES_TEST_USERNAME", "")
            if not username:
                raise OAuthProblem("X_RES_TEST_USERNAME header is required in test mode")
        else:
            raise OAuthProblem(detail=f"Unable to retrieve username: {e}")

    try:
        if not accounts.is_active_user(username):
            raise OAuthProblem(detail="Inactive user")
    except Exception as e:
        raise OAuthProblem(detail=f"Failed to check user state: {e}")

    return {"uid": username}
