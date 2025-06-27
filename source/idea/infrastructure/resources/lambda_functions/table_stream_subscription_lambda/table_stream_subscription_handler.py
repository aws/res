#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import base64
import json
import logging
from typing import Any, Dict, Optional

import res.constants as constants  # type: ignore
import res.exceptions as exceptions  # type: ignore
from boto3.dynamodb.types import TypeDeserializer
from res.clients.ad_sync import ad_sync_client  # type: ignore
from res.resources.dynamodb import dynamodb_stream_subscription  # type: ignore
from res.resources.dynamodb.dynamodb_stream_subscriber import (  # type: ignore
    IDynamoDBStreamSubscriber,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ddb_type_deserializer = TypeDeserializer()


class ADConfigEventSubscriber(IDynamoDBStreamSubscriber):  # type: ignore
    def on_create(self, entry: Dict[str, Any]) -> None:
        if entry.get("value"):
            self._start_ad_sync()

    def on_update(self, old_entry: Dict[str, Any], new_entry: Dict[str, Any]) -> None:
        if old_entry.get("value") != new_entry.get("value"):
            self._start_ad_sync()

    def on_delete(self, entry: Dict[str, Any]) -> None:
        self._start_ad_sync()

    def is_entry_monitored(self, entry: Dict[str, Any]) -> bool:
        return (
            entry["key"]
            in constants.AD_CONFIGURATION_REQUIRED_KEYS
            + constants.AD_CONFIGURATION_OPTIONAL_KEYS
        )

    @property
    def subscriber_name(self) -> Optional[str]:
        return "ad"

    @staticmethod
    def _start_ad_sync() -> None:
        # Only start AD sync if there's no running task. Otherwise, Forcing AD sync will stop the
        # existing task and start a new one quite frequently when customers edit multiple AD / SSSD
        # settings from the web portal, which brings unnecessary cost on ECS.
        try:
            ad_sync_client.start_ad_sync()
        except (
            exceptions.ADSyncConfigurationNotFound,
            exceptions.ADSyncInProcess,
        ) as e:
            logger.info(str(e))
        except Exception as e:
            logger.error(str(e))


def handle(event: Dict[str, Any], _context: Dict[str, Any]) -> None:
    subscribers = [ADConfigEventSubscriber()]

    for rec in event["Records"]:
        record_data = json.loads(
            base64.b64decode(rec.get("kinesis", {}).get("data", b"{}"))
        )
        dynamodb_stream_subscription.handle_record_data(
            record_data, ddb_type_deserializer, subscribers, logger
        )
