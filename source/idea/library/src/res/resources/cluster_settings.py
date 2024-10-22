#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any

import res.exceptions as exceptions
from res.utils import table_utils

CLUSTER_SETTINGS_TABLE_NAME = "cluster-settings"
CLUSTER_SETTINGS_HASH_KEY = "key"
CLUSTER_SETTINGS_VALUE_KEY = "value"


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
