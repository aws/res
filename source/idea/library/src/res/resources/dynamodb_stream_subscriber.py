#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from abc import ABC, abstractmethod
from typing import Dict

import res.constants as constants  # type: ignore
import res.exceptions as exceptions  # type: ignore
from res.clients.ad_sync import ad_sync_client  # type: ignore
from res.resources import cluster_settings  # type: ignore
from res.utils import sssd_utils  # type: ignore

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class IDynamoDBStreamSubscriber(ABC):

    @abstractmethod
    def on_create(self, entry: Dict): ...

    @abstractmethod
    def on_update(self, old_entry: Dict, new_entry: Dict): ...

    @abstractmethod
    def on_delete(self, entry: Dict): ...


TABLE_STREAM_SUBSCRIBERS = {}


def register_table_stream_subscriber(table_name: str):
    def decorator(subscriber_class_type):
        TABLE_STREAM_SUBSCRIBERS[table_name] = subscriber_class_type
        return subscriber_class_type

    return decorator


def get_table_stream_subscriber(table_name: str) -> IDynamoDBStreamSubscriber:
    try:
        return TABLE_STREAM_SUBSCRIBERS[table_name]()
    except KeyError:
        raise ValueError(f"No stream subscriber for table {table_name} is registered")


@register_table_stream_subscriber(cluster_settings.CLUSTER_SETTINGS_TABLE_NAME)
class ClusterSettingsTableStreamSubscriber(IDynamoDBStreamSubscriber):
    def on_create(self, entry: Dict):
        key = entry["key"]
        if (
            key
            in constants.AD_CONFIGURATION_REQUIRED_KEYS
            + constants.AD_CONFIGURATION_OPTIONAL_KEYS
        ) and entry.get("value"):
            self._start_ad_sync()

    def on_update(self, old_entry: Dict, new_entry: Dict):
        key = new_entry["key"]
        if (
            key
            in constants.AD_CONFIGURATION_REQUIRED_KEYS
            + constants.AD_CONFIGURATION_OPTIONAL_KEYS
        ) and old_entry.get("value") != new_entry.get("value"):
            self._start_ad_sync()

    def on_delete(self, entry: Dict):
        key = entry["key"]
        if key in constants.AD_CONFIGURATION_OPTIONAL_KEYS:
            self._start_ad_sync()

    @staticmethod
    def _start_ad_sync():
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
