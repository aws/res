#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from res.utils.model_utils import remove_none_values


class TestRemoveNoneValues:
    """Tests for remove_none_values."""

    def test_strips_none_values_from_top_level_dict(self):
        assert remove_none_values({"a": 1, "b": None, "c": "x"}) == {"a": 1, "c": "x"}

    def test_strips_none_values_recursively_from_nested_dicts(self):
        data = {
            "outer": {"keep": "v", "drop": None, "inner": {"x": None, "y": 2}},
        }
        assert remove_none_values(data) == {"outer": {"keep": "v", "inner": {"y": 2}}}

    def test_strips_none_items_from_lists(self):
        assert remove_none_values([1, None, 2, None]) == [1, 2]

    def test_strips_none_recursively_from_dicts_inside_lists(self):
        assert remove_none_values([{"a": None, "b": 1}, {"c": 2}]) == [
            {"b": 1},
            {"c": 2},
        ]

    def test_returns_primitives_unchanged(self):
        assert remove_none_values(42) == 42
        assert remove_none_values("hello") == "hello"
        assert remove_none_values(True) is True

    def test_returns_none_unchanged_when_passed_directly(self):
        # Top-level None is preserved; only None *entries* in dicts/lists are stripped.
        assert remove_none_values(None) is None

    def test_preserves_falsy_non_none_values(self):
        data = {
            "zero": 0,
            "empty_str": "",
            "empty_list": [],
            "false": False,
            "drop": None,
        }
        assert remove_none_values(data) == {
            "zero": 0,
            "empty_str": "",
            "empty_list": [],
            "false": False,
        }

    def test_empty_dict_and_list_unchanged(self):
        assert remove_none_values({}) == {}
        assert remove_none_values([]) == []
