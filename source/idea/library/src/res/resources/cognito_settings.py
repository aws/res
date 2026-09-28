#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict

import res.constants as constants
from res.clients.aws.aws_provider import get_aws_provider
from res.resources import cluster_settings
from res.utils import logging_utils

logger = logging_utils.get_logger("cognito-settings")

ENABLE_SELF_SIGN_UP_KEY = "cognito.enable_self_sign_up"


def update_settings(settings: Dict[str, Any]) -> None:
    enable_self_sign_up = settings.get(ENABLE_SELF_SIGN_UP_KEY)
    if enable_self_sign_up is not None:
        _toggle_self_signup(bool(enable_self_sign_up))


def _toggle_self_signup(enable: bool) -> None:
    user_pool_id = cluster_settings.get_setting(constants.IDENTITY_PROVIDER_USERPOOL_ID)
    client = get_aws_provider().cognito_idp()

    try:
        pool = client.describe_user_pool(UserPoolId=user_pool_id)["UserPool"]
        pool["AdminCreateUserConfig"] = {
            **(pool.get("AdminCreateUserConfig") or {}),
            "AllowAdminCreateUserOnly": not enable,
        }
        if enable:
            pool["AutoVerifiedAttributes"] = ["email"]
            pool["VerificationMessageTemplate"] = {
                "DefaultEmailOption": "CONFIRM_WITH_CODE",
                "EmailSubject": "Verify your email for RES",
            }

        client.update_user_pool(
            UserPoolId=user_pool_id,
            **{
                k: pool[k]
                for k in constants.COGNITO_UPDATE_USER_POOL_ARGUMENTS
                if k in pool
            },
        )
        logger.info(
            f"Toggled Cognito self-signup to {'ON' if enable else 'OFF'} for user pool: {user_pool_id}"
        )
    except Exception as e:
        logger.error(
            f"Failed to toggle Cognito self-signup for user pool {user_pool_id}: {e}"
        )
