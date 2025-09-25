#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import logging
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError
from res.utils.custom_resource_utils import (  # type: ignore
    CustomResourceResponse,
    send_response,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: Dict[str, Any], context: Dict[str, Any]) -> None:
    """
    Get the default actions of the ALB listener.

    After the cluster stack is deployed, the virtual desktop controller stack will update the default action to point to dcv broker
    to avoid replacing the default action set for dcv broker, fetch the default actions if the listener exists.

    Similar is applicable for cluster manager, when cluster manager stack is deployed, it will update the default listener on
    external ALB to point to web portal.

    When cluster stack is updated or re-rerun, the listener exists,
    fetch the existing listener configuration and apply the config to the listener.

    ** Note **
    Currently, only target group forwarding is supported. Additional implementation is required to support
    other types of existing listener configurations.
    """
    resource_properties = event.get("ResourceProperties", {})
    listener_arn = resource_properties.get("listener_arn")
    request_type = event.get("RequestType", None)

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
        if request_type != "Delete":
            default_actions = []
            if listener_arn:
                ec2_client = boto3.client("elbv2")
                describe_listeners_result = ec2_client.describe_listeners(
                    ListenerArns=[listener_arn]
                )

                existing_action = describe_listeners_result["Listeners"][0][
                    "DefaultActions"
                ][0]
                if existing_action["Type"] == "forward":
                    default_actions = [
                        {
                            "Type": "forward",
                            "ForwardConfig": {
                                "TargetGroups": [
                                    {
                                        "TargetGroupArn": existing_action[
                                            "TargetGroupArn"
                                        ]
                                    }
                                ]
                            },
                        }
                    ]
            if not default_actions:
                default_actions = [
                    {
                        "Type": "fixed-response",
                        "FixedResponseConfig": {
                            "StatusCode": "200",
                            "ContentType": "application/json",
                            "MessageBody": json.dumps(
                                {"success": True, "message": "OK"},
                                default=str,
                                separators=(",", ":"),
                            ),
                        },
                    }
                ]

            response["Data"] = {"default_actions": default_actions}

    except ClientError as e:
        error_message = f"failed to get default actions: {e}"
        response["Status"] = "FAILED"
        response["Reason"] = error_message

        logger.exception(error_message)

    finally:
        send_response(url=event["ResponseURL"], response=response)
