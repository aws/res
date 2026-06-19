#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Dict, List


def convert_custom_tags_to_key_value_pairs(custom_tags: List[str]) -> Dict:
    result = {}
    for custom_tag in custom_tags:
        tokens = custom_tag.split(",", 1)
        key = tokens[0].split("Key=")[1].strip()
        value = tokens[1].split("Value=")[1].strip()
        if not key:
            continue
        if not value:
            continue
        result[key] = value
    return result


def convert_tags_list_of_dict_to_tags_dict(tags_list: list[dict]) -> dict:
    result = {}
    if tags_list:
        for tag_pair in tags_list:
            key = tag_pair.get("session_tags_keys")
            value = tag_pair.get("session_tags_values")
            if key and value is not None:
                result[key] = value
    return result
