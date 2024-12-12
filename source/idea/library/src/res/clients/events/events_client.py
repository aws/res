#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import os
from typing import Any, Dict

import boto3
from res.constants import ENVIRONMENT_NAME_KEY
from res.resources import cluster_settings

DB_ENTRY_CREATED_EVENT = "DB_ENTRY_CREATED_EVENT"
VALIDATE_DCV_SESSION_DELETION_EVENT = "VALIDATE_DCV_SESSION_DELETION_EVENT"


def get_vdc_events_queue_url() -> str:
    return cluster_settings.get_setting("vdc.events_sqs_queue_url")


def get_event_json(event: dict) -> str:
    return json.dumps(event, default=str, separators=(",", ":"))


def publish_validate_dcv_session_deletion_event(session_id: str, owner: str) -> None:
    publish_virtual_desktop_event(
        {
            "event_group_id": session_id,
            "event_type": VALIDATE_DCV_SESSION_DELETION_EVENT,
            "detail": {"idea_session_id": session_id, "idea_session_owner": owner},
        }
    )


def publish_create_event(
    hash_key: str, range_key: str, new_entry: dict, table_name
) -> None:
    publish_virtual_desktop_event(
        {
            "event_group_id": f"{hash_key}-{range_key}",
            "event_type": DB_ENTRY_CREATED_EVENT,
            "detail": {
                "hash_key": hash_key,
                "range_key": range_key,
                "new_value": new_entry,
                "table_name": f"{os.environ.get(ENVIRONMENT_NAME_KEY)}.{table_name}",
            },
        }
    )


def publish_virtual_desktop_event(event: Dict[str, Any]):
    if not event:
        raise Exception("event is required")
    if not event["event_group_id"]:
        raise Exception("event_group_id is required")
    if not event["event_type"]:
        raise Exception("event_type is required")
    if not event["detail"]:
        raise Exception("detail is required")

    events_sqs_queue_url = get_vdc_events_queue_url()
    sqs_client = boto3.client("sqs")
    sqs_client.send_message(
        QueueUrl=events_sqs_queue_url,
        MessageBody=get_event_json(event),
        MessageGroupId=event["event_group_id"].replace(" ", "_"),
    )
