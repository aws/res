#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import unittest
from typing import Dict, Optional

import pytest
import res as res
from res.resources import modules
from res.utils import table_utils

TEST_MODULE_ID = "test_module_id"
TEST_MODULE_NAME = "test_module_name"


class ModulesTestContext:
    module: Optional[Dict]


class TestModules(unittest.TestCase):

    def setUp(self):
        self.context: ModulesTestContext = ModulesTestContext()
        self.context.module = {
            modules.MODULES_TABLE_HASH_KEY: TEST_MODULE_ID,
            modules.MODULES_TABLE_NAME_KEY: TEST_MODULE_NAME,
        }

    def test_create_module_should_pass(self):
        modules.create_module(self.context.module)
        module = table_utils.get_item(
            modules.MODULES_TABLE_NAME, {modules.MODULES_TABLE_HASH_KEY: TEST_MODULE_ID}
        )
        assert module is not None
        assert module[modules.MODULES_TABLE_NAME_KEY] == TEST_MODULE_NAME
