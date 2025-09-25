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

PHYSICAL_RESOURCE_ID = "user-pool-client"


def handler(event: Dict[str, Any], context: Dict[str, Any]) -> None:
    """
    Add OAuth scopes to an existing user pool client.
    """
    logger.info(f"ReceivedEvent: {json.dumps(event)}")

    resource_properties = event.get("ResourceProperties", {})
    cluster_name = resource_properties.get("cluster_name")
    module_id = resource_properties.get("module_id")
    stack_name = f"{cluster_name}-{module_id}"
    client_id_secrete_name = f"{stack_name}-client-id"
    user_pool_id = resource_properties.get("user_pool_id")
    o_auth_scopes_to_add = resource_properties.get("o_auth_scopes_to_add")

    logger.info(f"Adding OAuth scopes to existing {module_id} user pool client")

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
        if event["RequestType"] == "Update" or event["RequestType"] == "Create":
            # Retrieve the client ID from Secrets Manager
            secretsmanager = boto3.client("secretsmanager")
            client_id_secret = secretsmanager.get_secret_value(
                SecretId=client_id_secrete_name
            )
            client_id = client_id_secret.get("SecretString", "")

            # Read the current configuration of the user pool client
            idp_client = boto3.client("cognito-idp")
            user_pool_client_response = idp_client.describe_user_pool_client(
                UserPoolId=user_pool_id, ClientId=client_id
            )

            user_pool_client = user_pool_client_response.get("UserPoolClient", {})
            user_pool_client.pop("ClientSecret", None)
            user_pool_client.pop("LastModifiedDate", None)
            user_pool_client.pop("CreationDate", None)

            allowed_o_auth_scopes = user_pool_client.get("AllowedOAuthScopes", [])
            allowed_o_auth_scopes_is_updated = False
            for o_auth_scope in o_auth_scopes_to_add:
                if o_auth_scope not in allowed_o_auth_scopes:
                    allowed_o_auth_scopes.append(o_auth_scope)
                    allowed_o_auth_scopes_is_updated = True

            if allowed_o_auth_scopes_is_updated:
                # Only update the allowed OAuth scopes of the client and keep all the other attributes unchanged.
                logger.info(f"Updating {module_id} user pool client scopes...")
                user_pool_client["AllowedOAuthScopes"] = allowed_o_auth_scopes
                idp_client.update_user_pool_client(
                    **user_pool_client,
                )
                logger.info(
                    f"Added to {module_id} user pool client scopes successfully"
                )
            else:
                logger.info(
                    f"No need to update {module_id} user pool client scopes, skipping..."
                )

    except Exception as e:
        error_msg = (
            f"Failed to OAuth scopes to {module_id} user pool client. - {str(e)}"
        )
        response["Status"] = "FAILED"
        response["Reason"] = error_msg
        logger.error(error_msg)

    finally:
        send_response(url=event["ResponseURL"], response=response)
