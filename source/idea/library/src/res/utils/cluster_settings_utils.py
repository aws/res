#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import re
from typing import Dict, List

from pyhocon import ConfigFactory, ConfigTree
from res.utils import table_utils

CLUSTER_SETTINGS_TABLE_NAME = "cluster-settings"
CLUSTER_SETTINGS_HASH_KEY = "key"
CLUSTER_SETTINGS_VALUE_KEY = "value"
CLUSTER_SETTINGS_VERSION_KEY = "version"


def build_config_from_db(query: str = None) -> ConfigTree:
    """
    build configuration by reading all entries from database
    if query is provided, all keys matching the query regex will be returned
    """
    entries = get_config_entries(query=query)
    config = ConfigFactory.from_dict({})

    for entry in entries:
        key = entry[CLUSTER_SETTINGS_HASH_KEY]
        value = entry[CLUSTER_SETTINGS_VALUE_KEY]
        config.put(key, value)

    return config


def get_config_entries(query: str = None) -> List[Dict]:
    """
    read configuration entries as a list of dict items
    if query is provided, all keys matching the query regex will be returned
    :return:
    """
    pattern = None
    if query:
        try:
            pattern = re.compile(query)
        except Exception as e:
            raise Exception(f"invalid search regex: {query} - {e}")

    config_entries = []
    settings = table_utils.scan(
        CLUSTER_SETTINGS_TABLE_NAME,
    )
    if settings:
        for setting in settings:
            key = setting.get(CLUSTER_SETTINGS_HASH_KEY)
            setting = post_process_ddb_config_entry(setting)

            if pattern:
                if pattern.match(key):
                    config_entries.append(setting)
            else:
                config_entries.append(setting)

    config_entries.sort(key=lambda entry: entry[CLUSTER_SETTINGS_HASH_KEY])
    return config_entries


def post_process_ddb_config_entry(item: Dict) -> Dict:
    """
    perform Decimal types to int or float conversions if applicable
    """
    version = item.get(CLUSTER_SETTINGS_VERSION_KEY)
    item[CLUSTER_SETTINGS_VERSION_KEY] = table_utils.check_and_convert_decimal_value(
        version
    )
    value = item.get(CLUSTER_SETTINGS_VALUE_KEY)
    item[CLUSTER_SETTINGS_VALUE_KEY] = table_utils.check_and_convert_decimal_value(
        value
    )
    return item


def convert_custom_tags_to_dict_list(tags: List[str]) -> List[Dict[str, str]]:
    """
    convert custom tags from list of str to list of dict
    """
    result = []
    for tag in tags:
        tokens = tag.split(",", 1)
        key = tokens[0].split("Key=")[1].strip()
        value = tokens[1].split("Value=")[1].strip()
        if not key:
            continue
        if not value:
            continue
        result.append({"Key": key, "Value": value})
    return result
