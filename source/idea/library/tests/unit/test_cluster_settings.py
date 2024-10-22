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
        table_utils.create_item(
            cluster_settings.CLUSTER_SETTINGS_TABLE_NAME, item=self.context.settings
        )

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
