#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
from typing import Any, Callable, Dict, List

from res.resources.vdc_events import VDCEventType  # type: ignore
from res.utils import logging_utils  # type: ignore

from .event_handlers import (
    ec2_state_change_handler,
    ssm_commands_handler,
    validate_software_stack_handler,
)

logger = logging_utils.get_logger(__name__)

EVENT_HANDLER_MAP: Dict[str, Callable[[str, Dict[str, Any]], None]] = {
    VDCEventType.EC2_INSTANCE_STATE_CHANGED: ec2_state_change_handler.handle,
    VDCEventType.SSM_COMMAND_STATUS: ssm_commands_handler.handle,
    VDCEventType.VALIDATE_SOFTWARE_STACK_CREATION: validate_software_stack_handler.handle,
}


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    SQS-triggered Lambda that processes VDC events and SNS notifications.
    """
    records: List[Dict[str, Any]] = event.get("Records", [])
    batch_item_failures: List[Dict[str, str]] = []

    for record in records:
        message_id = record.get("messageId", "")
        try:
            body = json.loads(record.get("body", "{}"))

            # SNS messages have a "Type" field — route to SSM handler
            if body.get("Type") == "Notification":
                ssm_commands_handler.handle(message_id, body)
                continue

            event_type = body.get("event_type")

            if not event_type:
                logger.error(
                    f"[msg-id: {message_id}] Missing event_type in message body. Discarding."
                )
                continue

            event_handler = EVENT_HANDLER_MAP.get(event_type)
            if event_handler:
                event_handler(message_id, body)
            else:
                logger.warning(
                    f"[msg-id: {message_id}] Unhandled event_type: {event_type}. Discarding."
                )

        except validate_software_stack_handler.AMINotReady as e:
            logger.info(f"[msg-id: {message_id}] {e}")
            batch_item_failures.append({"itemIdentifier": message_id})

        except Exception:
            logger.exception(f"[msg-id: {message_id}] Failed to process record.")
            batch_item_failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": batch_item_failures}
