#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import unittest
from typing import Dict, Optional

import pytest
import res as res
import res.exceptions as exceptions
from res.resources import cluster_settings
from res.utils import table_utils, time_utils

TEST_SETTING = "test_setting"
TEST_SETTING_VALUE = "test_setting_value"
EXTRA_SETTINGS = {
    "test_settings1": "test_setting_value1",
    "test_settings2": "test_setting_value2",
}
RANDOM_SETTING = "random_setting"


class ClusterSettingsTestContext:
    settings: Optional[Dict]


class TestClusterSettings(unittest.TestCase):

    def setUp(self):
        self.context: ClusterSettingsTestContext = ClusterSettingsTestContext()
        self.context.settings = {
            cluster_settings.CLUSTER_SETTINGS_HASH_KEY: TEST_SETTING,
            cluster_settings.CLUSTER_SETTINGS_VALUE_KEY: TEST_SETTING_VALUE,
        }
        cluster_settings.create_setting(TEST_SETTING, TEST_SETTING_VALUE)
        cluster_settings.create_settings(EXTRA_SETTINGS)

    def test_cluster_settings_get_setting_invalid_request_should_fail(self):
        """
        get setting failure
        """
        with pytest.raises(exceptions.SettingNotFound) as exc_info:
            cluster_settings.get_setting(key=RANDOM_SETTING)
        assert f"Setting not found: {RANDOM_SETTING}" == exc_info.value.args[0]

    def test_cluster_settings_get_setting_valid_request_should_pass(self):
        """
        get setting happy path
        """
        result = cluster_settings.get_setting(key=TEST_SETTING)
        assert result is not None
        assert result == TEST_SETTING_VALUE

        result = cluster_settings.get_setting(key="test_settings1")
        assert result is not None
        assert result == EXTRA_SETTINGS["test_settings1"]

    def test_cluster_settings_update_setting_should_pass(self):
        """
        update setting happy path
        """
        new_value = "new_value"
        cluster_settings.update_setting(key=TEST_SETTING, value=new_value)
        result = cluster_settings.get_setting(key=TEST_SETTING)
        assert result is not None
        assert result == new_value

        complete_result = table_utils.get_item(
            cluster_settings.CLUSTER_SETTINGS_TABLE_NAME,
            {cluster_settings.CLUSTER_SETTINGS_HASH_KEY: TEST_SETTING},
        )
        assert complete_result is not None
        assert complete_result.get("version") == 2
