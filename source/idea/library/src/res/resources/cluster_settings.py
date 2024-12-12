#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Dict, List, Tuple

import res.exceptions as exceptions
from res.utils import table_utils

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

CLUSTER_SETTINGS_TABLE_NAME = "cluster-settings"
CLUSTER_SETTINGS_HASH_KEY = "key"
CLUSTER_SETTINGS_VALUE_KEY = "value"
CLUSTER_SETTINGS_VERSION_KEY = "version"


def create_setting(key: str, value: Any) -> Dict[str, Any]:
    """
    Create setting in DDB
    """
    if not key:
        raise exceptions.InvalidParams("Key is required")
    # We allow null values in cluster-settings as well
    if not value:
        logger.warning(f"Value not provided for {key}. Setting value to None.")
    logging.info(f"Creating setting {key} with value {value}")
    setting = table_utils.create_item(
        CLUSTER_SETTINGS_TABLE_NAME,
        item={
            CLUSTER_SETTINGS_HASH_KEY: key,
            CLUSTER_SETTINGS_VALUE_KEY: value,
            CLUSTER_SETTINGS_VERSION_KEY: 1,
        },
    )
    return setting


def create_settings(settings: Dict[str, Any]) -> Tuple[Dict[str, Any]]:
    """
    Create multiple settings in DDB
    """
    for key, value in settings.items():
        if not key:
            raise exceptions.InvalidParams("Key required for all settings")
    success_list = []
    fail_list = []
    for key, value in settings.items():
        try:
            create_setting(key, value)
            success_list.append({key: value})
        except Exception as e:
            logger.warning(f"Cannot create setting for {key}. Reason: {e}")
            fail_list.append({key: value})
    return success_list, fail_list


def update_setting(key: str, value: Any) -> Dict[str, Any]:
    """
    Update setting in DDB
    """
    if not key or not value:
        raise exceptions.InvalidParams("Key and value are required")
    logging.info(f"Updating setting {key} with value {value}")
    setting = table_utils.update_item(
        CLUSTER_SETTINGS_TABLE_NAME,
        key={CLUSTER_SETTINGS_HASH_KEY: key},
        item={CLUSTER_SETTINGS_HASH_KEY: key, CLUSTER_SETTINGS_VALUE_KEY: value},
        versioned=True,
    )
    return setting


def get_setting(key: str) -> Any:
    """
    Retrieve setting from DDB
    :return: Setting value
    """
    settings = table_utils.get_item(
        CLUSTER_SETTINGS_TABLE_NAME,
        key={CLUSTER_SETTINGS_HASH_KEY: key},
    )

    if not settings:
        raise exceptions.SettingNotFound(
            f"Setting not found: {key}",
        )
    return settings.get(CLUSTER_SETTINGS_VALUE_KEY)


def get_settings() -> Dict[str, Any]:
    settings: List[Dict[str, Any]] = table_utils.list_items("cluster-settings")

    return {setting["key"]: setting["value"] for setting in settings}
