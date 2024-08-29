#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

import pytest
from ideasdk.utils import Utils

from ideadatamodel import constants, errorcodes, exceptions


def test_utils_is_empty():
    assert Utils.is_empty(None) is True
    assert Utils.is_empty("") is True
    assert Utils.is_empty([]) is True
    assert Utils.is_empty({}) is True
    assert Utils.is_empty(()) is True
    assert Utils.is_empty(bytes()) is True
    assert Utils.is_empty(bytearray()) is True

    assert Utils.is_empty("x") is False
    assert Utils.is_empty(["x"]) is False
    assert Utils.is_empty({"x": "x"}) is False
    assert Utils.is_empty((1, 2)) is False
    assert Utils.is_empty(bytes(1)) is False
    assert Utils.is_empty(bytearray(1)) is False


def test_utils_is_true():
    assert Utils.is_true(True) is True
    assert Utils.is_true(False) is False
    assert Utils.is_true(None) is False
    assert Utils.is_true(1) is True
    assert Utils.is_true(100) is True
    assert Utils.is_true(-100) is True
    assert Utils.is_true(0) is False
    assert Utils.is_true(None, True) is True
    assert Utils.is_true(None, False) is False
    assert Utils.is_true(False, True) is False
    assert Utils.is_true(True, False) is True
    assert Utils.is_true("true") is True
    assert Utils.is_true("True") is True
    assert Utils.is_true("yes") is True
    assert Utils.is_true("Yes ") is True
    assert Utils.is_true("y") is True
    assert Utils.is_true("Y") is True
    assert Utils.is_true("1") is True
    assert Utils.is_true("") is False
    assert Utils.is_true("x") is False
    assert Utils.is_true("false") is False
    assert Utils.is_true("False") is False
    assert Utils.is_true("no") is False
    assert Utils.is_true("No ") is False
    assert Utils.is_true("n") is False
    assert Utils.is_true("N") is False
    assert Utils.is_true("0") is False
    assert Utils.is_true("true", False) is True
    assert Utils.is_true("True", False) is True
    assert Utils.is_true("yes", False) is True
    assert Utils.is_true("Yes ", False) is True
    assert Utils.is_true("y", False) is True
    assert Utils.is_true("Y", False) is True
    assert Utils.is_true("true", False) is True
    assert Utils.is_true("false", True) is False
    assert Utils.is_true("", True) is True
    assert Utils.is_true("  ", True) is True
    assert Utils.is_true("", False) is False
    assert Utils.is_true("  ", False) is False
    assert Utils.is_true("x", True) is False
    assert Utils.is_true("x", False) is False
    assert Utils.is_true(1, False) is True
    assert Utils.is_true(100, False) is True
    assert Utils.is_true(0, False) is False
    assert Utils.is_true(False, True) is False
    assert Utils.is_true("false", True) is False
    assert Utils.is_true("False", True) is False
    assert Utils.is_true("no", True) is False
    assert Utils.is_true("No ", True) is False
    assert Utils.is_true("n", True) is False
    assert Utils.is_true("N", True) is False


def test_utils_is_false():
    assert Utils.is_false(True) is False
    assert Utils.is_false(False) is True
    assert Utils.is_false(None) is False
    assert Utils.is_false(1) is False
    assert Utils.is_false(100) is False
    assert Utils.is_false(-100) is False
    assert Utils.is_false(0) is True
    assert Utils.is_false(None, True) is True
    assert Utils.is_false(None, False) is False
    assert Utils.is_false(False, True) is True
    assert Utils.is_false(True, False) is False
    assert Utils.is_false("true") is False
    assert Utils.is_false("True") is False
    assert Utils.is_false("yes") is False
    assert Utils.is_false("Yes ") is False
    assert Utils.is_false("y") is False
    assert Utils.is_false("Y") is False
    assert Utils.is_false("1") is False
    assert Utils.is_false("") is False
    assert Utils.is_false("x") is False
    assert Utils.is_false("false") is True
    assert Utils.is_false("False") is True
    assert Utils.is_false("no") is True
    assert Utils.is_false("No ") is True
    assert Utils.is_false("n") is True
    assert Utils.is_false("N") is True
    assert Utils.is_false("0") is True
    assert Utils.is_false("true", False) is False
    assert Utils.is_false("True", False) is False
    assert Utils.is_false("yes", False) is False
    assert Utils.is_false("Yes ", False) is False
    assert Utils.is_false("y", False) is False
    assert Utils.is_false("Y", False) is False
    assert Utils.is_false("true", False) is False
    assert Utils.is_false("false", True) is True
    assert Utils.is_false("", False) is False
    assert Utils.is_false("  ", False) is False
    assert Utils.is_false("", True) is True
    assert Utils.is_false("  ", True) is True
    assert Utils.is_false("x", True) is False
    assert Utils.is_false("x", False) is False
    assert Utils.is_false(1, False) is False
    assert Utils.is_false(100, False) is False
    assert Utils.is_false(0, False) is True
    assert Utils.is_false(False, True) is True
    assert Utils.is_false("false", True) is True
    assert Utils.is_false("False", True) is True
    assert Utils.is_false("no", True) is True
    assert Utils.is_false("No ", True) is True
    assert Utils.is_false("n", True) is True
    assert Utils.is_false("N", True) is True


def test_utils_is_int():
    assert Utils.is_int(1) is True
    assert Utils.is_int(0) is True
    assert Utils.is_int(100) is True
    assert Utils.is_int(-100) is True
    assert Utils.is_int("1") is True
    assert Utils.is_int("1 ") is True
    assert Utils.is_int(" 1 ") is True
    assert Utils.is_int("0") is True
    assert Utils.is_int("100") is True
    assert Utils.is_int("-100") is True
    assert Utils.is_int("1.0") is False
    assert Utils.is_int("x") is False
    assert Utils.is_int("- 1") is False
    assert Utils.is_int([]) is False  # noqa
    assert Utils.is_int({}) is False  # noqa
    assert Utils.is_int(set()) is False  # noqa


def test_utils_is_float():
    assert Utils.is_float(123.45) is True
    assert Utils.is_float(123) is True
    assert Utils.is_float(-123.45) is True
    assert Utils.is_float(-123) is True
    assert Utils.is_float("123.45") is True
    assert Utils.is_float("-123.45") is True
    assert Utils.is_float("123.45 ") is True
    assert Utils.is_float(" 123.45 ") is True
    assert Utils.is_float("0") is True
    assert Utils.is_float("100") is True
    assert Utils.is_float("-100") is True
    assert Utils.is_float("1.0") is True
    assert Utils.is_float("9.81E7") is True
    assert Utils.is_float([]) is False  # noqa
    assert Utils.is_float({}) is False  # noqa
    assert Utils.is_float(set()) is False  # noqa

    assert Utils.is_float("x") is False
    assert Utils.is_float("- 123.45") is False


def test_utils_get_as_string():
    assert Utils.get_as_string("") is None
    assert Utils.get_as_string("  ") is None
    assert Utils.get_as_string("\n") is None
    assert Utils.get_as_string("\n\n") is None
    assert Utils.get_as_string("\t") is None
    assert Utils.get_as_string("\t\t") is None
    assert Utils.get_as_string(" \t \n") is None
    assert Utils.get_as_string("x") == "x"
    assert Utils.get_as_string(" x ") == "x"
    assert Utils.get_as_string("x ") == "x"
    assert Utils.get_as_string(" x") == "x"
    assert Utils.get_as_string(True) == "True"
    assert Utils.get_as_string(False) == "False"
    assert Utils.get_as_string(1) == "1"
    assert Utils.get_as_string(-1) == "-1"
    assert Utils.get_as_string(0) == "0"
    assert Utils.get_as_string(123.45) == "123.45"
    assert Utils.get_as_string(-123.45) == "-123.45"
    assert Utils.get_as_string(0.0) == "0.0"
    assert Utils.get_as_string(-0.0) == "-0.0"
    assert Utils.get_as_string(0.0000) == "0.0"
    assert Utils.get_as_string(9.81e7) == "98100000.0"
    assert Utils.get_as_string("9.81E7") == "9.81E7"
    assert Utils.get_as_string({}) == "{}"
    assert Utils.get_as_string([]) == "[]"
    assert Utils.get_as_string(()) == "()"
    assert Utils.get_as_string(None, "x") == "x"
    assert Utils.get_as_string("", "x") == "x"
    assert Utils.get_as_string("  ", "x") == "x"
    assert Utils.get_as_string("\n", "x") == "x"
    assert Utils.get_as_string("\n\n", "x") == "x"
    assert Utils.get_as_string("\t", "x") == "x"
    assert Utils.get_as_string("\t\t", "x") == "x"
    assert Utils.get_as_string(" \t \n", "x") == "x"
    d1 = {"x": "x"}
    assert Utils.get_as_string(d1) == str(d1)
    s1 = {"x"}
    assert Utils.get_as_string(s1) == str(s1)
    l1 = ["x"]
    assert Utils.get_as_string(l1) == str(l1)

    val = Utils.get_as_string("x")
    assert type(val) == str


def test_utils_get_as_int():
    assert Utils.get_as_int(1) == 1
    assert Utils.get_as_int("1") == 1
    assert Utils.get_as_int(None) is None
    assert Utils.get_as_int("None") is None
    assert Utils.get_as_int(None, 1) == 1
    assert Utils.get_as_int("x", 1) == 1
    assert Utils.get_as_int("123", 1) == 123
    assert Utils.get_as_int(123.45) == 123
    assert Utils.get_as_int(123.45, 10) == 123
    assert Utils.get_as_int("123.45", 10) == 123

    val = Utils.get_as_int(1.0)
    assert type(val) == int

    val = Utils.get_as_int("1")
    assert type(val) == int

    val = Utils.get_as_int("123.45")
    assert type(val) == int


def test_utils_get_as_float():
    assert Utils.get_as_float(123.45) == 123.45
    assert Utils.get_as_float(123) == 123.0
    assert Utils.get_as_float("123") == 123.0
    assert Utils.get_as_float(None) is None
    assert Utils.get_as_float("None") is None
    assert Utils.get_as_float(None, 123.45) == 123.45
    assert Utils.get_as_float(None, 123) == 123.0
    assert Utils.get_as_float("x", 123.45) == 123.45
    assert Utils.get_as_float("123", 1) == 123.0
    assert Utils.get_as_float(123.45) == 123.45
    assert Utils.get_as_float(123.45, 10) == 123.45
    assert Utils.get_as_float("123.45", 10) == 123.45

    val = Utils.get_as_float(1)
    assert type(val) == float

    val = Utils.get_as_float("123.45")
    assert type(val) == float

    val = Utils.get_as_float(None, 1)
    assert type(val) == float


def test_utils_get_as_bool():
    assert Utils.get_as_bool(True) is True
    assert Utils.get_as_bool(False) is False
    assert Utils.get_as_bool(None) is None
    assert Utils.get_as_bool(1) is True
    assert Utils.get_as_bool(100) is True
    assert Utils.get_as_bool(-100) is True
    assert Utils.get_as_bool(0) is False
    assert Utils.get_as_bool(None, True) is True
    assert Utils.get_as_bool(None, False) is False
    assert Utils.get_as_bool(False, True) is False
    assert Utils.get_as_bool(True, False) is True
    assert Utils.get_as_bool("true") is True
    assert Utils.get_as_bool("True") is True
    assert Utils.get_as_bool("yes") is True
    assert Utils.get_as_bool("Yes ") is True
    assert Utils.get_as_bool("y") is True
    assert Utils.get_as_bool("Y") is True
    assert Utils.get_as_bool("1") is True
    assert Utils.get_as_bool("") is None
    assert Utils.get_as_bool("x") is None
    assert Utils.get_as_bool("false") is False
    assert Utils.get_as_bool("False") is False
    assert Utils.get_as_bool("no") is False
    assert Utils.get_as_bool("No ") is False
    assert Utils.get_as_bool("n") is False
    assert Utils.get_as_bool("N") is False
    assert Utils.get_as_bool("0") is False
    assert Utils.get_as_bool("true", False) is True
    assert Utils.get_as_bool("True", False) is True
    assert Utils.get_as_bool("yes", False) is True
    assert Utils.get_as_bool("Yes ", False) is True
    assert Utils.get_as_bool("y", False) is True
    assert Utils.get_as_bool("Y", False) is True
    assert Utils.get_as_bool("true", False) is True
    assert Utils.get_as_bool("false", True) is False
    assert Utils.get_as_bool("", True) is True
    assert Utils.get_as_bool("  ", True) is True
    assert Utils.get_as_bool("", False) is False
    assert Utils.get_as_bool("  ", False) is False
    assert Utils.get_as_bool("x", True) is True
    assert Utils.get_as_bool("x", False) is False
    assert Utils.get_as_bool(1, False) is True
    assert Utils.get_as_bool(100, False) is True
    assert Utils.get_as_bool(0, False) is False
    assert Utils.get_as_bool(False, True) is False
    assert Utils.get_as_bool("false", True) is False
    assert Utils.get_as_bool("False", True) is False
    assert Utils.get_as_bool("no", True) is False
    assert Utils.get_as_bool("No ", True) is False
    assert Utils.get_as_bool("n", True) is False
    assert Utils.get_as_bool("N", True) is False


def test_utils_get_ec2_block_device_name():
    assert Utils.get_ec2_block_device_name(constants.OS_AMAZONLINUX2) == "/dev/xvda"
    assert Utils.get_ec2_block_device_name(constants.OS_WINDOWS) == "/dev/sda1"
    assert Utils.get_ec2_block_device_name("unknown") == "/dev/sda1"


def test_utils_get_platform():
    assert Utils.get_platform(constants.OS_WINDOWS) == constants.PLATFORM_WINDOWS
    assert Utils.get_platform(constants.OS_AMAZONLINUX2) == constants.PLATFORM_LINUX
    with pytest.raises(exceptions.SocaException) as exc_info:
        Utils.get_platform("unknown")
    assert isinstance(exc_info.value, exceptions.SocaException)
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS


def test_utils_convert_tags_dict_to_aws_tags():
    tags = {
        "k1": "v1",  # valid
        "k2": None,
        "k3": 3,  # valid, converted to string
        "k4": "",
        "": "test",
        "k5": {},
    }
    tag_entries = Utils.convert_tags_dict_to_aws_tags(tags)
    assert len(tag_entries) == 2
    for entry in tag_entries:
        assert entry["Key"] in ["k1", "k3"]
        assert isinstance(entry["Value"], str)


def test_utils_convert_custom_tags_to_key_value_pairs():
    custom_tags = [
        "Key=k1,Value=v1",
        "Key=k2,Value=v2",
        "Key= k 3 , Value= v 3 ",
        "Key=k4,Value=",
        "Key=,Value=v5",
    ]
    tags = Utils.convert_custom_tags_to_key_value_pairs(custom_tags)
    assert len(tags) == 3
    assert "k1" in tags
    assert tags["k1"] == "v1"
    assert "k 3" in tags
    assert tags["k 3"] == "v 3"


def test_yaml_load_throws_error(mocker):
    mocker.patch(
        "yaml.safe_load",
        side_effect=Exception("mock error"),
    )
    with pytest.raises(Exception) as err:
        Utils.from_yaml("")
    assert str(err.value) == "mock error"


def test_flatten_dict():
    test_dict = {"a": {"b": "1", "c": 2, "d": [3, 4]}, "e": 5}
    expected_dict = {"a.b": "1", "a.c": 2, "a.d": [3, 4], "e": 5}
    assert Utils.flatten_dict(test_dict) == expected_dict
