#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import logging
import os
from typing import Any, Dict, TypedDict
from urllib.request import Request, urlopen

from res.constants import (  # type: ignore
    AD_SYNC_SECURITY_GROUP_ID_KEY,
    AD_SYNC_TASK_CLUSTER_KEY,
    AD_SYNC_TASK_DEFINITION_KEY,
)
from res.resources import cluster_settings  # type: ignore

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
    logger.info(f"Start populating AD sync resources")
    response = CustomResourceResponse(
        Status="SUCCESS",
        Reason="SUCCESS",
        PhysicalResourceId=event.get("LogicalResourceId", ""),
        StackId=event.get("StackId", ""),
        RequestId=event.get("RequestId", ""),
        LogicalResourceId=event.get("LogicalResourceId", ""),
    )
    try:
        if event["RequestType"] == "Create":
            env_to_ddb_keys = {
                "ad_sync_security_group_id": AD_SYNC_SECURITY_GROUP_ID_KEY,
                "ad_sync_task_cluster": AD_SYNC_TASK_CLUSTER_KEY,
                "ad_sync_task_definition": AD_SYNC_TASK_DEFINITION_KEY,
            }
            settings = {
                ddb_key: os.environ.get(env_key, "")
                for env_key, ddb_key in env_to_ddb_keys.items()
            }
            _, failed_list = cluster_settings.create_settings(settings=settings)
            if failed_list:
                raise Exception(f"Failed to create settings for: {failed_list}")

    except Exception as e:
        response["Status"] = "FAILED"
        response["Reason"] = "FAILED"
        logger.error(f"Failed to terminate AD sync ECS task: {str(e)}")
    finally:
        _send_response(url=event["ResponseURL"], response=response)


def _send_response(url: str, response: CustomResourceResponse) -> None:
    request = Request(
        method="PUT",
        url=url,
        data=json.dumps(response).encode("utf-8"),
    )

    urlopen(request)
