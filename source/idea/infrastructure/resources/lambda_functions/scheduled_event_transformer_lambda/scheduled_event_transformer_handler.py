#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
Scheduled event transformer
This function is triggered by an event-bridge event rule periodically. It repackages the event and forwards it to the
Controller Events Queue.
"""

import json
import logging
import os
from typing import Any, Dict

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: Dict[str, Any], context: Dict[str, Any]) -> None:
    sqs_client = boto3.client("sqs")
    try:
        detail_type = event["detail-type"]
        if detail_type != "Scheduled Event":
            return

        forwarding_event = {
            "event_group_id": "SCHEDULED_EVENT",
            "event_type": "SCHEDULED_EVENT",
            "detail": {"time": event["time"]},
        }

        logger.info("Forwarding scheduled event to Controller")
        response = sqs_client.send_message(
            QueueUrl=os.environ.get("IDEA_CONTROLLER_EVENTS_QUEUE_URL"),
            MessageBody=json.dumps(forwarding_event),
            MessageGroupId="SCHEDULED_EVENT",
        )
        logger.info(response)
    except Exception as e:
        logger.exception(f"error in handling scheduled event: {event}, error: {e}")
