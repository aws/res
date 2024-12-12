#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import logging
import os
from typing import Any, Dict, TypedDict
from urllib.request import Request, urlopen

import boto3
from res.constants import (  # type: ignore
    ADMIN_ROLE,
    CLUSTER_ADMIN_USERNAME,
    CLUSTER_ADMINISTRATOR_EMAIL,
    COGNITO_USER_IDP_TYPE,
    DEFAULT_REGION_KEY,
    ENVIRONMENT_NAME_KEY,
)
from res.exceptions import UserNotFound  # type: ignore
from res.resources import accounts, cluster_settings  # type: ignore
from res.utils import auth_utils  # type: ignore

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class CustomResourceResponse(TypedDict):
    # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/crpg-ref-responses.html
    Status: str
    Reason: str
    PhysicalResourceId: str
    StackId: str
    RequestId: str
    LogicalResourceId: str


def handler(event: Dict[str, Any], context: Dict[str, Any]) -> None:
    logger.info(f"Start populating final values")
    response = CustomResourceResponse(
        Status="SUCCESS",
        Reason="SUCCESS",
        PhysicalResourceId=event.get("LogicalResourceId", ""),
        StackId=event.get("StackId", ""),
        RequestId=event.get("RequestId", ""),
        LogicalResourceId=event.get("LogicalResourceId", ""),
    )
    try:
        if event["RequestType"] == "Create" or event["RequestType"] == "Update":
            _populate_clusteradmin_user()

    except Exception as e:
        response["Status"] = "FAILED"
        response["Reason"] = "FAILED"
        logger.error(f"Failed to populate final values: {str(e)}")
    finally:
        _send_response(url=event["ResponseURL"], response=response)


def _send_response(url: str, response: CustomResourceResponse) -> None:
    request = Request(
        method="PUT",
        url=url,
        data=json.dumps(response).encode("utf-8"),
    )

    urlopen(request)


def _populate_clusteradmin_user() -> None:
    cluster_name = os.environ.get(ENVIRONMENT_NAME_KEY, "")
    aws_region = os.environ.get(DEFAULT_REGION_KEY, "")

    try:
        _admin_user = accounts.get_user(username=CLUSTER_ADMIN_USERNAME)
        if _admin_user:
            logger.info("clusteradmin user already exists, returning")
            return
    except UserNotFound:
        logger.info(f"clusteradmin user not found, start populating")
        pass

    cognito_client = boto3.client("cognito-idp")
    email = cluster_settings.get_setting(CLUSTER_ADMINISTRATOR_EMAIL)
    cognito_pool_id = cluster_settings.get_setting(
        "identity-provider.cognito.user_pool_id"
    )
    password = auth_utils.generate_password()
    email = auth_utils.sanitize_email(email)
    email_verified = False
    logger.debug("populate_clusteradmin_user() - setting password to random value")
    logger.info(
        f"creating Cognito user pool entry: clusteradmin, Email: {email} , email_verified: False"
    )
    cognito_admin_user_params = {
        "UserPoolId": cognito_pool_id,
        "Username": CLUSTER_ADMIN_USERNAME,
        "TemporaryPassword": password,
        "UserAttributes": [
            {"Name": "email", "Value": email},
            {"Name": "email_verified", "Value": str(email_verified)},
            {"Name": "custom:cluster_name", "Value": cluster_name},
            {"Name": "custom:aws_region", "Value": aws_region},
            {"Name": "custom:uid", "Value": str(auth_utils.COGNITO_MIN_ID_INCLUSIVE)},
        ],
        "DesiredDeliveryMediums": ["EMAIL"],
    }

    cognito_result = cognito_client.admin_create_user(**cognito_admin_user_params)
    _created_cognito_user = cognito_result.get("User", None)
    status = _created_cognito_user.get("UserStatus", "")
    logger.info(f"CreateUser: clusteradmin, Status: {status}, EmailVerified: False")

    logger.info(f"Creating clusteradmin user in RES DDB table ")
    _created_user = accounts.create_user(
        {
            accounts.USERS_DB_HASH_KEY: CLUSTER_ADMIN_USERNAME,
            accounts.GSI_EMAIL_HASH_KEY: email,
            "uid": auth_utils.COGNITO_MIN_ID_INCLUSIVE,
            "gid": None,
            "additional_groups": [],
            "login_shell": auth_utils.DEFAULT_LOGIN_SHELL,
            "home_dir": os.path.join(
                auth_utils.USER_HOME_DIR_BASE, CLUSTER_ADMIN_USERNAME
            ),
            "sudo": False,
            "enabled": True,
            "role": ADMIN_ROLE,
            "is_active": True,
            "identity_source": COGNITO_USER_IDP_TYPE,
        }
    )
    return
