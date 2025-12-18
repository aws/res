#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Dict

import boto3
from res.resources import cluster_settings  # type: ignore
from res.utils.custom_resource_utils import (  # type: ignore
    CustomResourceResponse,
    send_response,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: Dict[str, Any], context: Dict[str, Any]) -> None:
    logger.info(f"Start populating cloudformation custom tags to cluster-settings DDB")

    stack_id = event.get("StackId", "")

    response = CustomResourceResponse(
        Status="SUCCESS",
        Reason="SUCCESS",
        PhysicalResourceId=event.get("LogicalResourceId", ""),
        StackId=stack_id,
        RequestId=event.get("RequestId", ""),
        LogicalResourceId=event.get("LogicalResourceId", ""),
        Data={},
    )
    try:
        if event["RequestType"] == "Create" or event["RequestType"] == "Update":
            cfn_client = boto3.client("cloudformation")
            cfn_response = cfn_client.describe_stacks(StackName=stack_id)
            tags = cfn_response["Stacks"][0].get("Tags", [])
            formatted_tags = []
            for tag in tags:
                if tag["Key"].startswith("res:") or tag["Key"] == "Name":
                    raise Exception(
                        f"Custom tagging key res:* and Name are restricted due to RES environment usage."
                    )
                formatted_tags.append(f"Key={tag['Key']},Value={tag['Value']}")

            cluster_settings.update_setting(
                "global-settings.custom_tags", formatted_tags
            )

    except Exception as e:
        error_message = (
            f"Failed to populate custom tags to cluster-settings DDB: {str(e)}"
        )
        response["Status"] = "FAILED"
        response["Reason"] = error_message

        logger.error(error_message)
    finally:
        send_response(url=event["ResponseURL"], response=response)
