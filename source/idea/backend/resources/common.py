#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
from typing import Any, Dict

import res.exceptions as exceptions  # type: ignore
from res.constants import COGNITO_SSO_IDP_PROVIDER_NAME  # type: ignore
from res.resources import accounts, token  # type: ignore
from res.resources.cluster_settings import CLUSTER_SETTINGS_TABLE_NAME  # type: ignore
from res.utils import auth_utils, table_utils  # type: ignore


def check_admin_authorized(event: Dict[str, Any]) -> None:
    auth_header = event.get("headers", {}).get("authorization", "")
    jwt_token = auth_header.split(" ")[1] if auth_header.startswith("Bearer ") else None

    username = None
    if os.environ.get("RES_TEST_MODE", "").lower() == "true":
        # In test mode, extract username from X_RES_TEST_USERNAME header.
        # ALB lowercases all header names.
        headers = event.get("headers", {})
        username = headers.get("x_res_test_username", "")
        if not username:
            raise exceptions.UnauthorizedAccess(
                message="X_RES_TEST_USERNAME header is required in test mode"
            )
    else:
        decoded_token = token.decode_token(token=jwt_token)
        username = decoded_token.get("username")

    if not username:
        raise exceptions.UnauthorizedAccess(message="Username missing in token")

    idp_name_record = table_utils.get_item(
        table_name=CLUSTER_SETTINGS_TABLE_NAME,
        key={"key": COGNITO_SSO_IDP_PROVIDER_NAME},
    )
    idp_name = idp_name_record.get("value") if idp_name_record else None
    username = auth_utils.get_ddb_user_name(
        username=username, idp_name=idp_name
    )

    if not accounts.is_active_admin(username):
        raise exceptions.UnauthorizedAccess()
