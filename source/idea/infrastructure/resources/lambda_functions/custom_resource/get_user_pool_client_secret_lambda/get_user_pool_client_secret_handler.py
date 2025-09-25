#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import logging
from typing import Any, Dict

import boto3
from res.utils.custom_resource_utils import (  # type: ignore
    CustomResourceResponse,
    send_response,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: Dict[str, Any], context: Dict[str, Any]) -> None:
    logger.info(f"ReceivedEvent: {json.dumps(event)}")

    resource_properties = event.get("ResourceProperties", {})
    user_pool_id = resource_properties.get("UserPoolId")
    client_id = resource_properties.get("ClientId")

    logger.info(f"UserPoolId: {user_pool_id}, ClientId: {client_id}")

    response = CustomResourceResponse(
        Status="SUCCESS",
        Reason="SUCCESS",
        PhysicalResourceId=event.get("LogicalResourceId", ""),
        StackId=event.get("StackId", ""),
        RequestId=event.get("RequestId", ""),
        LogicalResourceId=event.get("LogicalResourceId", ""),
        Data={},
    )

    try:
        cognito_idp_client = boto3.client("cognito-idp")

        if event["RequestType"] == "Update" or event["RequestType"] == "Create":

            cognito_response = cognito_idp_client.describe_user_pool_client(
                UserPoolId=user_pool_id, ClientId=client_id
            )

            client = cognito_response.get("UserPoolClient", {})
            client_secret = client.get("ClientSecret", None)

            if client_secret:
                response["Data"] = {"ClientSecret": client_secret}
            else:
                error_msg = f"Could not find ClientSecret for ClientId: {client_id}"
                raise Exception(error_msg)
    except Exception as e:
        error_msg = f"Failed to get ClientSecret for UserPool Client. - {str(e)}"
        response["Status"] = "FAILED"
        response["Reason"] = error_msg
        logger.error(error_msg)

    finally:
        send_response(url=event["ResponseURL"], response=response)
