#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import base64
import json
import logging
import os
from typing import Any, Dict

from boto3.dynamodb.types import TypeDeserializer
from res.resources.dynamodb_stream_subscriber import (  # type: ignore
    get_table_stream_subscriber,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ddb_type_deserializer = TypeDeserializer()


def handle(event: Dict[str, Any], _context: Dict[str, Any]) -> None:
    stream_subscriber = get_table_stream_subscriber(os.environ.get("TABLE_NAME"))

    for rec in event["Records"]:
        record_data = json.loads(
            base64.b64decode(rec.get("kinesis", {}).get("data", b"{}"))
        )
        logger.info("Record: %s", record_data)

        event_name = record_data["eventName"]
        if event_name == "INSERT":
            logger.debug(f"Received INSERT event from {os.environ.get('TABLE_NAME')}")

            config_entry_raw = record_data["dynamodb"]["NewImage"]
            config_entry = {
                k: ddb_type_deserializer.deserialize(v)
                for k, v in config_entry_raw.items()
            }
            stream_subscriber.on_create(config_entry)
        elif event_name == "MODIFY":
            logger.debug(f"Received MODIFY event from {os.environ.get('TABLE_NAME')}")

            old_config_entry_raw = record_data["dynamodb"]["OldImage"]
            old_config_entry = {
                k: ddb_type_deserializer.deserialize(v)
                for k, v in old_config_entry_raw.items()
            }
            new_config_entry_raw = record_data["dynamodb"]["NewImage"]
            new_config_entry = {
                k: ddb_type_deserializer.deserialize(v)
                for k, v in new_config_entry_raw.items()
            }
            stream_subscriber.on_update(old_config_entry, new_config_entry)
        elif event_name == "REMOVE":
            logger.debug(f"Received REMOVE event from {os.environ.get('TABLE_NAME')}")

            config_entry_raw = record_data["dynamodb"]["OldImage"]
            config_entry = {
                k: ddb_type_deserializer.deserialize(v)
                for k, v in config_entry_raw.items()
            }
            stream_subscriber.on_delete(config_entry)
