#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any


def remove_none_values(data: Any) -> Any:
    """
    Recursively remove None values from dictionaries and lists.

    This utility function is commonly used when preparing data for API requests
    to avoid schema validation errors where None values are not expected.

    Args:
        data: The data structure to clean (dict, list, or primitive type)

    Returns:
        The cleaned data structure with None values removed

    Example:
        >>> data = {"key1": "value1", "key2": None, "key3": {"nested": None}}
        >>> clean_data = remove_none_values(data)
        >>> # Returns: {"key1": "value1", "key3": {}}
    """
    if isinstance(data, dict):
        return {
            key: remove_none_values(value)
            for key, value in data.items()
            if value is not None
        }
    if isinstance(data, list):
        return [remove_none_values(item) for item in data if item is not None]
    return data
