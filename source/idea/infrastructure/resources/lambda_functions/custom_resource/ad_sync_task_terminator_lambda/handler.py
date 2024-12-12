#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import logging
import time
from typing import Any, Dict, TypedDict
from urllib.request import Request, urlopen

from res.clients.ad_sync.ad_sync_client import (  # type: ignore
    is_task_terminated,
    stop_ad_sync,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

MAX_ATTEMPT = 10
WAIT_TIME = 10  # seconds


class CustomResourceResponse(TypedDict):
    # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/crpg-ref-responses.html
    Status: str
    Reason: str
    PhysicalResourceId: str
    StackId: str
    RequestId: str
    LogicalResourceId: str


def handler(event: Dict[str, Any], context: Dict[str, Any]) -> None:
    response = CustomResourceResponse(
        Status="SUCCESS",
        Reason="SUCCESS",
        PhysicalResourceId=event.get("LogicalResourceId", ""),
        StackId=event.get("StackId", ""),
        RequestId=event.get("RequestId", ""),
        LogicalResourceId=event.get("LogicalResourceId", ""),
    )
    try:
        if event["RequestType"] == "Delete":
            _terminate_ad_sync()

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


def _terminate_ad_sync() -> None:
    try:
        task_id = stop_ad_sync()
        if task_id:
            attempt = 0
            while attempt < MAX_ATTEMPT:
                if is_task_terminated(task_id):
                    logger.info(
                        f"AD sync task: {task_id} has been successfully stopped"
                    )
                    return

                logger.info(f"Waiting for task: {task_id} to stop...")
                time.sleep(WAIT_TIME)
                attempt += 1
            logger.info(
                f"AD sync task: {task_id} did not stop after {MAX_ATTEMPT} attempts"
            )

    except Exception as e:
        logger.exception(f"Error in terminating AD sync ECS task, error: {e}")
        raise e
