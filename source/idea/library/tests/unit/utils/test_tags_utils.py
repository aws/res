#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from res.utils import tags


def test_convert_custom_tags_to_key_value_pairs():
    """Test convert_custom_tags_to_key_value_pairs with valid tags."""
    custom_tags = ["Key=Environment,Value=Production", "Key=Team,Value=Engineering"]
    result = tags.convert_custom_tags_to_key_value_pairs(custom_tags)

    assert result == {"Environment": "Production", "Team": "Engineering"}


def test_convert_custom_tags_to_key_value_pairs_empty_values():
    """Test convert_custom_tags_to_key_value_pairs skips empty keys or values."""
    custom_tags = ["Key=,Value=Production", "Key=Team,Value="]
    result = tags.convert_custom_tags_to_key_value_pairs(custom_tags)

    assert result == {}


def test_convert_tags_list_of_dict_to_tags_dict():
    """Test convert_tags_list_of_dict_to_tags_dict with valid list."""
    tag_list = [
        {"session_tags_keys": "Environment", "session_tags_values": "Dev"},
        {"session_tags_keys": "Owner", "session_tags_values": "Alice"},
    ]
    result = tags.convert_tags_list_of_dict_to_tags_dict(tag_list)

    assert result == {"Environment": "Dev", "Owner": "Alice"}


def test_convert_tags_list_of_dict_to_tags_dict_empty_list():
    """Test convert_tags_list_of_dict_to_tags_dict with empty list."""
    result = tags.convert_tags_list_of_dict_to_tags_dict([])

    assert result == {}
