#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
import os
from typing import Any, Dict, List

import boto3
from res.constants import ENVIRONMENT_NAME_KEY, ENVIRONMENT_NAME_TAG_KEY  # type: ignore
from res.utils.custom_resource_utils import (  # type: ignore
    CustomResourceResponse,
    send_response,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: Dict[str, Any], context: Dict[str, Any]) -> None:
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
        if event["RequestType"] == "Delete":
            logger.info(f"Start deleting target groups")
            _delete_target_groups()

    except Exception as e:
        response["Status"] = "FAILED"
        error_msg = f"Failed to delete target groups: {str(e)}"
        response["Reason"] = error_msg

        logger.error(error_msg)
    finally:
        send_response(url=event["ResponseURL"], response=response)


def _delete_target_groups() -> None:
    cluster_name = os.environ.get(ENVIRONMENT_NAME_KEY, "")

    try:
        elb_client = boto3.client("elbv2")
        paginator = elb_client.get_paginator("describe_target_groups")

        matching_prefix_tg_arns = []
        for page in paginator.paginate():
            for target_group in page.get("TargetGroups", []):

                target_group_name = target_group.get("TargetGroupName", "")
                target_group_arn = target_group.get("TargetGroupArn", "")
                if target_group_name.startswith(cluster_name):
                    matching_prefix_tg_arns.append(target_group_arn)

        tg_to_delete_arns = _validate_target_groups(
            matching_prefix_tg_arns, cluster_name, elb_client
        )

        if not tg_to_delete_arns:
            logger.info(f"No target groups found for cluster: {cluster_name}")
            return

        for target_group_arn in tg_to_delete_arns:
            elb_client.delete_target_group(TargetGroupArn=target_group_arn)

    except Exception as e:
        error_msg = f"Error deleting target groups: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)


def _validate_target_groups(
    target_group_arns: List[str], cluster_name: str, elb_client: Any
) -> List[str]:
    tg_to_delete_arns = []
    for i in range(0, len(target_group_arns), 20):
        batch_arns = target_group_arns[i : i + 20]
        try:
            response = elb_client.describe_tags(ResourceArns=batch_arns)
            tag_descriptions = response.get("TagDescriptions", [])

            for tag_description in tag_descriptions:
                tg_arn = tag_description.get("ResourceArn", "")
                tg_tags = tag_description.get("Tags", [])
                for tag in tg_tags:
                    if (
                        tag.get("Key") == ENVIRONMENT_NAME_TAG_KEY
                        and tag.get("Value") == cluster_name
                    ):
                        logger.info(f"Found target group to be deleted: {tg_arn}")
                        tg_to_delete_arns.append(tg_arn)
                        break

        except Exception as e:
            error_msg = f"Error when checking target group batch tags: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    return tg_to_delete_arns
