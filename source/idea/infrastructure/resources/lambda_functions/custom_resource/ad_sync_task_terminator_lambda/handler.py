#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
import time
from typing import Any, Dict

from res.clients.ad_sync.ad_sync_client import (  # type: ignore
    is_task_terminated,
    stop_ad_sync,
)
from res.utils.custom_resource_utils import (  # type: ignore
    CustomResourceResponse,
    send_response,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

MAX_ATTEMPT = 10
WAIT_TIME = 10  # seconds


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
            _terminate_ad_sync()

    except Exception as e:
        error_message = f"Failed to terminate AD sync ECS task: {str(e)}"
        response["Status"] = "FAILED"
        response["Reason"] = error_message

        logger.error(error_message)
    finally:
        send_response(url=event["ResponseURL"], response=response)


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
