#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json

import boto3
from res.resources import cluster_settings

VALIDATE_DCV_SESSION_DELETION_EVENT = "VALIDATE_DCV_SESSION_DELETION_EVENT"


def get_vdc_events_queue_url() -> str:
    return cluster_settings.get_setting("vdc.events_sqs_queue_url")


def get_event_json(event: dict) -> str:
    return json.dumps(event, default=str, separators=(",", ":"))


def publish_validate_dcv_session_deletion_event(session_id: str, owner: str) -> None:
    events_sqs_queue_url = get_vdc_events_queue_url()
    sqs_client = boto3.client("sqs")

    event = {
        "event_group_id": session_id,
        "event_type": VALIDATE_DCV_SESSION_DELETION_EVENT,
        "detail": {"idea_session_id": session_id, "idea_session_owner": owner},
    }

    sqs_client.send_message(
        QueueUrl=events_sqs_queue_url,
        MessageBody=get_event_json(event),
        MessageGroupId=event["event_group_id"].replace(" ", "_"),
    )
