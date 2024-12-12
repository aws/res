#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import unittest
from typing import Dict, Optional

import pytest
import res as res
import res.exceptions as exceptions
from res.resources import software_stacks as stacks
from res.utils import table_utils

TEST_BASE_OS = "test_base_os"
RANDOM_TEST_BASE_OS = "random_base_os"
TEST_STACK_ID = "test_stack_id"
RANDOM_STACK_ID = "random_stack_id"
TEST_NAME = "test_name"
TEST_AMI_ID = "test_ami_id"
TEST_PROJECT_ID = "test_project_id"


class SoftwareStacksTestContext:
    software_stack: Optional[Dict]


class TestSoftwareStacks(unittest.TestCase):

    def setUp(self):
        self.context: SoftwareStacksTestContext = SoftwareStacksTestContext()
        self.context.software_stack = {
            stacks.SOFTWARE_STACK_DB_HASH_KEY: TEST_BASE_OS,
            stacks.SOFTWARE_STACK_DB_RANGE_KEY: TEST_STACK_ID,
            stacks.SOFTWARE_STACK_DB_NAME_KEY: TEST_NAME,
            stacks.SOFTWARE_STACK_DB_AMI_ID_KEY: TEST_AMI_ID,
            stacks.SOFTWARE_STACK_DB_PROJECTS_KEY: [TEST_PROJECT_ID],
        }
        table_utils.create_item(
            stacks.SOFTWARE_STACK_TABLE_NAME, item=self.context.software_stack
        )

    def test_software_stacks_get_invalid_stack_should_fail(self):
        """
        get software stack failure
        """
        error_msg = "Software stack not found"
        # invalid base_os
        with pytest.raises(exceptions.SoftwareStackNotFound) as exc_info:
            stacks.get_software_stack(
                base_os=RANDOM_TEST_BASE_OS, stack_id=TEST_STACK_ID
            )
        assert error_msg in exc_info.value.args[0]

        # invalid stack_id
        with pytest.raises(exceptions.SoftwareStackNotFound) as exc_info:
            stacks.get_software_stack(base_os=TEST_BASE_OS, stack_id=RANDOM_STACK_ID)
        assert error_msg in exc_info.value.args[0]

    def test_software_stacks_get_valid_stack_should_pass(self):
        """
        get software stack success
        """
        result = stacks.get_software_stack(base_os=TEST_BASE_OS, stack_id=TEST_STACK_ID)
        assert result is not None
        assert result.get(stacks.SOFTWARE_STACK_DB_HASH_KEY) == TEST_BASE_OS
        assert result.get(stacks.SOFTWARE_STACK_DB_RANGE_KEY) == TEST_STACK_ID
        assert result.get(stacks.SOFTWARE_STACK_DB_NAME_KEY) == TEST_NAME
        assert result.get(stacks.SOFTWARE_STACK_DB_AMI_ID_KEY) == TEST_AMI_ID
        assert result.get(stacks.SOFTWARE_STACK_DB_PROJECTS_KEY) == [TEST_PROJECT_ID]

    def test_software_stacks_create_stack_should_pass(self):
        """
        create software stack success
        """
        created_software_stack = stacks.create_software_stack(
            software_stack={
                stacks.SOFTWARE_STACK_DB_HASH_KEY: RANDOM_TEST_BASE_OS,
                stacks.SOFTWARE_STACK_DB_RANGE_KEY: RANDOM_STACK_ID,
                stacks.SOFTWARE_STACK_DB_NAME_KEY: TEST_NAME,
                stacks.SOFTWARE_STACK_DB_AMI_ID_KEY: TEST_AMI_ID,
                stacks.SOFTWARE_STACK_DB_PROJECTS_KEY: [TEST_PROJECT_ID],
            }
        )

        assert created_software_stack[stacks.SOFTWARE_STACK_DB_HASH_KEY] is not None
        assert created_software_stack[stacks.SOFTWARE_STACK_DB_RANGE_KEY] is not None
        assert created_software_stack[stacks.SOFTWARE_STACK_DB_NAME_KEY] is not None
        assert created_software_stack[stacks.SOFTWARE_STACK_DB_AMI_ID_KEY] is not None
        assert created_software_stack[stacks.SOFTWARE_STACK_DB_PROJECTS_KEY] is not None

        software_stack = stacks.get_software_stack(
            base_os=RANDOM_TEST_BASE_OS, stack_id=RANDOM_STACK_ID
        )
        assert software_stack is not None
        assert software_stack.get(
            stacks.SOFTWARE_STACK_DB_HASH_KEY
        ) == created_software_stack.get(stacks.SOFTWARE_STACK_DB_HASH_KEY)
        assert software_stack.get(
            stacks.SOFTWARE_STACK_DB_RANGE_KEY
        ) == created_software_stack.get(stacks.SOFTWARE_STACK_DB_RANGE_KEY)
        assert software_stack.get(
            stacks.SOFTWARE_STACK_DB_NAME_KEY
        ) == created_software_stack.get(stacks.SOFTWARE_STACK_DB_NAME_KEY)
        assert software_stack.get(
            stacks.SOFTWARE_STACK_DB_AMI_ID_KEY
        ) == created_software_stack.get(stacks.SOFTWARE_STACK_DB_AMI_ID_KEY)
        assert software_stack.get(
            stacks.SOFTWARE_STACK_DB_PROJECTS_KEY
        ) == created_software_stack.get(stacks.SOFTWARE_STACK_DB_PROJECTS_KEY)

    def test_software_stacks_create_duplicate_stack_should_fail(self):
        with pytest.raises(Exception) as exc_info:
            stacks.create_software_stack(
                software_stack={
                    stacks.SOFTWARE_STACK_DB_HASH_KEY: TEST_BASE_OS,
                    stacks.SOFTWARE_STACK_DB_RANGE_KEY: TEST_STACK_ID,
                }
            )
        assert "already exists" in exc_info.value.args[0]

    def test_software_stacks_create_stack_without_os_or_id_should_fail(self):

        error_msg = "base_os and stack_id are required"
        # missing base_os
        with pytest.raises(Exception) as exc_info:
            stacks.create_software_stack(
                software_stack={
                    stacks.SOFTWARE_STACK_DB_RANGE_KEY: RANDOM_STACK_ID,
                }
            )
        assert error_msg in exc_info.value.args[0]

        # missing stack_id
        with pytest.raises(Exception) as exc_info:
            stacks.create_software_stack(
                software_stack={
                    stacks.SOFTWARE_STACK_DB_HASH_KEY: RANDOM_TEST_BASE_OS,
                }
            )
        assert error_msg in exc_info.value.args[0]
