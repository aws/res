#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import unittest
from typing import Dict, Optional
from unittest.mock import patch

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
TEST_PROJECT = {
    "project_id": TEST_PROJECT_ID,
    "name": "Test Project",
    "title": "Test Project Title",
}


# Test constants for instance type filtering
INSTANCE_T3_SMALL = {
    "InstanceType": "t3.small",
    "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
    "MemoryInfo": {"SizeInMiB": 2048},
    "GpuInfo": {"Gpus": []},
}

INSTANCE_T3_MEDIUM = {
    "InstanceType": "t3.medium",
    "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
    "MemoryInfo": {"SizeInMiB": 4096},
    "GpuInfo": {"Gpus": []},
}

INSTANCE_T3_LARGE = {
    "InstanceType": "t3.large",
    "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
    "MemoryInfo": {"SizeInMiB": 8192},
    "GpuInfo": {"Gpus": []},
    "SupportedBootModes": ["uefi", "legacy-bios"],
}

INSTANCE_T3_XLARGE = {
    "InstanceType": "t3.xlarge",
    "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
    "MemoryInfo": {"SizeInMiB": 16384},
    "GpuInfo": {"Gpus": []},
}

INSTANCE_T4G_MEDIUM = {
    "InstanceType": "t4g.medium",
    "ProcessorInfo": {"SupportedArchitectures": ["arm64"]},
    "MemoryInfo": {"SizeInMiB": 4096},
    "GpuInfo": {"Gpus": []},
}

INSTANCE_M5_LARGE = {
    "InstanceType": "m5.large",
    "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
    "MemoryInfo": {"SizeInMiB": 8192},
    "GpuInfo": {"Gpus": []},
}

INSTANCE_M5_METAL = {
    "InstanceType": "m5.metal",
    "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
    "MemoryInfo": {"SizeInMiB": 393216},
    "GpuInfo": {"Gpus": []},
    "SupportedBootModes": ["legacy-bios"],  # Only supports legacy-bios, not uefi
}

INSTANCE_G4DN_XLARGE = {
    "InstanceType": "g4dn.xlarge",
    "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
    "MemoryInfo": {"SizeInMiB": 16384},
    "GpuInfo": {"Gpus": [{"Manufacturer": "Nvidia"}]},
}

INSTANCE_G5_XLARGE = {
    "InstanceType": "g5.xlarge",
    "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
    "MemoryInfo": {"SizeInMiB": 16384},
    "GpuInfo": {"Gpus": [{"Manufacturer": "Nvidia"}]},
}


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
            stacks.SOFTWARE_STACK_DB_PROJECTS_KEY: [TEST_PROJECT],
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
        assert result.get(stacks.SOFTWARE_STACK_DB_PROJECTS_KEY) == [TEST_PROJECT]

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
                stacks.SOFTWARE_STACK_DB_PROJECTS_KEY: [TEST_PROJECT],
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

    def test_update_software_stack_allowed_instance_types_should_pass(self):
        test_instance_types = ["t3"]
        test_stack_1 = {
            stacks.SOFTWARE_STACK_DB_HASH_KEY: "test_os_1",
            stacks.SOFTWARE_STACK_DB_RANGE_KEY: "stack_1",
            stacks.SOFTWARE_STACK_DB_ALLOWED_INSTANCE_TYPES_KEY: ["t3", "m6a"],
        }
        test_stack_2 = {
            stacks.SOFTWARE_STACK_DB_HASH_KEY: "test_os_2",
            stacks.SOFTWARE_STACK_DB_RANGE_KEY: "stack_2",
            stacks.SOFTWARE_STACK_DB_ALLOWED_INSTANCE_TYPES_KEY: ["m6a"],
        }

        table_utils.create_item(stacks.SOFTWARE_STACK_TABLE_NAME, item=test_stack_1)
        table_utils.create_item(stacks.SOFTWARE_STACK_TABLE_NAME, item=test_stack_2)

        stacks.update_software_stack_allowed_instance_types(test_instance_types)

        updated_stack_1 = stacks.get_software_stack(
            base_os="test_os_1", stack_id="stack_1"
        )
        updated_stack_2 = stacks.get_software_stack(
            base_os="test_os_2", stack_id="stack_2"
        )

        assert updated_stack_1[stacks.SOFTWARE_STACK_DB_ALLOWED_INSTANCE_TYPES_KEY] == [
            "t3"
        ]
        assert (
            updated_stack_2[stacks.SOFTWARE_STACK_DB_ALLOWED_INSTANCE_TYPES_KEY] == []
        )

    @patch("res.resources.software_stacks.projects.get_project")
    def test_update_software_stack_success(self, mock_get_project):
        """
        update software stack success - should increment version and update timestamp
        """
        mock_get_project.return_value = TEST_PROJECT

        # Create a software stack with version and created_on timestamp
        original_stack = {
            stacks.SOFTWARE_STACK_DB_HASH_KEY: "update_test_os",
            stacks.SOFTWARE_STACK_DB_RANGE_KEY: "update_test_stack",
            stacks.SOFTWARE_STACK_DB_NAME_KEY: "original_name",
            stacks.SOFTWARE_STACK_DB_VERSION_KEY: 5,
            stacks.SOFTWARE_STACK_DB_CREATED_ON_KEY: 1234567890,
            stacks.SOFTWARE_STACK_DB_PROJECTS_KEY: [TEST_PROJECT],
        }
        table_utils.create_item(stacks.SOFTWARE_STACK_TABLE_NAME, item=original_stack)

        # Prepare update data
        update_data = {
            stacks.SOFTWARE_STACK_DB_HASH_KEY: "update_test_os",
            stacks.SOFTWARE_STACK_DB_RANGE_KEY: "update_test_stack",
            stacks.SOFTWARE_STACK_DB_NAME_KEY: "updated_name",
            stacks.SOFTWARE_STACK_DB_CREATED_ON_KEY: 1234567890,  # Should be removed
            stacks.SOFTWARE_STACK_DB_AMI_ID_KEY: "ami-updated",
            stacks.SOFTWARE_STACK_DB_PROJECTS_KEY: [TEST_PROJECT],
        }

        # Call update
        result = stacks.update_software_stack(update_data)

        # Verify returned result
        assert result[stacks.SOFTWARE_STACK_DB_NAME_KEY] == "updated_name"
        assert (
            result[stacks.SOFTWARE_STACK_DB_VERSION_KEY] == 6
        )  # Should be incremented from 5 to 6
        assert result[stacks.SOFTWARE_STACK_DB_UPDATED_ON_KEY] is not None
        assert (
            stacks.SOFTWARE_STACK_DB_CREATED_ON_KEY not in result
        )  # Should be removed
        # Verify project details are expanded
        assert result[stacks.SOFTWARE_STACK_DB_PROJECTS_KEY] == [TEST_PROJECT]

        # Verify persisted data
        updated_stack = stacks.get_software_stack("update_test_os", "update_test_stack")
        assert updated_stack[stacks.SOFTWARE_STACK_DB_NAME_KEY] == "updated_name"
        assert updated_stack[stacks.SOFTWARE_STACK_DB_VERSION_KEY] == 6
        assert updated_stack[stacks.SOFTWARE_STACK_DB_UPDATED_ON_KEY] is not None
        assert updated_stack[stacks.SOFTWARE_STACK_DB_AMI_ID_KEY] == "ami-updated"

    def test_update_software_stack_missing_base_os_should_fail(self):
        """
        update software stack with missing base_os should raise KeyError
        """
        update_data = {
            stacks.SOFTWARE_STACK_DB_RANGE_KEY: "test_stack",
            stacks.SOFTWARE_STACK_DB_NAME_KEY: "updated_name",
        }

        with pytest.raises(KeyError):
            stacks.update_software_stack(update_data)

    def test_update_software_stack_missing_stack_id_should_fail(self):
        """
        update software stack with missing stack_id should raise KeyError
        """
        update_data = {
            stacks.SOFTWARE_STACK_DB_HASH_KEY: "test_os",
            stacks.SOFTWARE_STACK_DB_NAME_KEY: "updated_name",
        }

        with pytest.raises(KeyError):
            stacks.update_software_stack(update_data)

    def test_update_software_stack_nonexistent_stack_should_fail(self):
        """
        update non-existent software stack should raise SoftwareStackNotFound
        """
        update_data = {
            stacks.SOFTWARE_STACK_DB_HASH_KEY: "nonexistent_os",
            stacks.SOFTWARE_STACK_DB_RANGE_KEY: "nonexistent_stack",
            stacks.SOFTWARE_STACK_DB_NAME_KEY: "updated_name",
        }

        with pytest.raises(exceptions.SoftwareStackNotFound):
            stacks.update_software_stack(update_data)

    @patch("res.resources.software_stacks.projects.get_project")
    def test_update_software_stack_version_increment_from_zero(self, mock_get_project):
        """
        update software stack should handle version increment when starting from 0
        """
        mock_get_project.return_value = TEST_PROJECT

        # Create stack with version 0
        original_stack = {
            stacks.SOFTWARE_STACK_DB_HASH_KEY: "version_test_os",
            stacks.SOFTWARE_STACK_DB_RANGE_KEY: "version_test_stack",
            stacks.SOFTWARE_STACK_DB_NAME_KEY: "original_name",
            stacks.SOFTWARE_STACK_DB_VERSION_KEY: 0,
            stacks.SOFTWARE_STACK_DB_PROJECTS_KEY: [TEST_PROJECT],
        }
        table_utils.create_item(stacks.SOFTWARE_STACK_TABLE_NAME, item=original_stack)

        update_data = {
            stacks.SOFTWARE_STACK_DB_HASH_KEY: "version_test_os",
            stacks.SOFTWARE_STACK_DB_RANGE_KEY: "version_test_stack",
            stacks.SOFTWARE_STACK_DB_NAME_KEY: "updated_name",
            stacks.SOFTWARE_STACK_DB_PROJECTS_KEY: [TEST_PROJECT],
        }

        result = stacks.update_software_stack(update_data)
        assert result[stacks.SOFTWARE_STACK_DB_VERSION_KEY] == 1

    @patch("res.resources.software_stacks.projects.get_project")
    def test_update_software_stack_preserves_existing_fields(self, mock_get_project):
        """
        update software stack should preserve existing fields not in update
        """
        mock_get_project.return_value = {"project_id": "project1", "name": "Project 1"}

        # Create stack with multiple fields
        original_stack = {
            stacks.SOFTWARE_STACK_DB_HASH_KEY: "preserve_test_os",
            stacks.SOFTWARE_STACK_DB_RANGE_KEY: "preserve_test_stack",
            stacks.SOFTWARE_STACK_DB_NAME_KEY: "original_name",
            stacks.SOFTWARE_STACK_DB_AMI_ID_KEY: "ami-original",
            stacks.SOFTWARE_STACK_DB_PROJECTS_KEY: ["project1", "project2"],
            stacks.SOFTWARE_STACK_DB_VERSION_KEY: 3,
            stacks.SOFTWARE_STACK_DB_CREATED_ON_KEY: 1111111111,
        }
        table_utils.create_item(stacks.SOFTWARE_STACK_TABLE_NAME, item=original_stack)

        # Update only the name
        update_data = {
            stacks.SOFTWARE_STACK_DB_HASH_KEY: "preserve_test_os",
            stacks.SOFTWARE_STACK_DB_RANGE_KEY: "preserve_test_stack",
            stacks.SOFTWARE_STACK_DB_NAME_KEY: "new_name",
            stacks.SOFTWARE_STACK_DB_PROJECTS_KEY: ["project1", "project2"],
        }

        stacks.update_software_stack(update_data)

        # Verify preserved fields
        updated_stack = stacks.get_software_stack(
            "preserve_test_os", "preserve_test_stack"
        )
        assert updated_stack[stacks.SOFTWARE_STACK_DB_NAME_KEY] == "new_name"  # Updated
        assert (
            updated_stack[stacks.SOFTWARE_STACK_DB_AMI_ID_KEY] == "ami-original"
        )  # Preserved
        assert updated_stack[stacks.SOFTWARE_STACK_DB_PROJECTS_KEY] == [
            "project1",
            "project2",
        ]  # Preserved
        assert updated_stack[stacks.SOFTWARE_STACK_DB_VERSION_KEY] == 4  # Incremented
        assert (
            updated_stack[stacks.SOFTWARE_STACK_DB_CREATED_ON_KEY] == 1111111111
        )  # Preserved in DB

    @patch("res.resources.software_stacks.projects.get_project")
    def test_update_software_stack_removes_created_on_from_input(
        self, mock_get_project
    ):
        """
        update software stack should remove created_on from input data but preserve it in DB
        """
        mock_get_project.return_value = TEST_PROJECT

        # Create original stack
        original_stack = {
            stacks.SOFTWARE_STACK_DB_HASH_KEY: "created_on_test_os",
            stacks.SOFTWARE_STACK_DB_RANGE_KEY: "created_on_test_stack",
            stacks.SOFTWARE_STACK_DB_NAME_KEY: "original_name",
            stacks.SOFTWARE_STACK_DB_VERSION_KEY: 1,
            stacks.SOFTWARE_STACK_DB_CREATED_ON_KEY: 9999999999,
            stacks.SOFTWARE_STACK_DB_PROJECTS_KEY: [TEST_PROJECT],
        }
        table_utils.create_item(stacks.SOFTWARE_STACK_TABLE_NAME, item=original_stack)

        # Update with created_on in input (should be ignored/removed)
        update_data = {
            stacks.SOFTWARE_STACK_DB_HASH_KEY: "created_on_test_os",
            stacks.SOFTWARE_STACK_DB_RANGE_KEY: "created_on_test_stack",
            stacks.SOFTWARE_STACK_DB_NAME_KEY: "updated_name",
            stacks.SOFTWARE_STACK_DB_CREATED_ON_KEY: 8888888888,  # Should be ignored
            stacks.SOFTWARE_STACK_DB_PROJECTS_KEY: [TEST_PROJECT],
        }

        result = stacks.update_software_stack(update_data)

        # created_on should be removed from returned result
        assert stacks.SOFTWARE_STACK_DB_CREATED_ON_KEY not in result

        # But should be preserved in the database
        updated_stack = stacks.get_software_stack(
            "created_on_test_os", "created_on_test_stack"
        )
        assert (
            updated_stack[stacks.SOFTWARE_STACK_DB_CREATED_ON_KEY] == 9999999999
        )  # Original value preserved

    @patch("res.resources.software_stacks.ec2_utils.get_instance_ram")
    def test_validate_min_ram_success(self, mock_get_ram):
        """Test validate_min_ram returns True when instance has enough RAM."""
        # Setup
        software_stack_ddb = {
            stacks.SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY: 8.0,
            stacks.SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY: "GiB",
            stacks.SOFTWARE_STACK_DB_NAME_KEY: "test-stack",
        }
        mock_get_ram.return_value = (16384.0, "MiB")  # 16 GiB

        # Test
        result = stacks.validate_min_ram("t3.xlarge", software_stack_ddb)

        # Assertions
        assert result is True
        mock_get_ram.assert_called_once_with("t3.xlarge")

    @patch("res.resources.software_stacks.ec2_utils.get_instance_ram")
    def test_validate_min_ram_insufficient_memory(self, mock_get_ram):
        """Test validate_min_ram returns False when instance has insufficient RAM."""
        # Setup
        software_stack_ddb = {
            stacks.SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY: 16.0,
            stacks.SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY: "GiB",
            stacks.SOFTWARE_STACK_DB_NAME_KEY: "test-stack",
        }
        mock_get_ram.return_value = (8192.0, "MiB")  # 8 GiB

        # Test
        result = stacks.validate_min_ram("t3.large", software_stack_ddb)

        # Assertions
        assert result is False
        mock_get_ram.assert_called_once_with("t3.large")

    def test_validate_min_ram_no_software_stack(self):
        """Test validate_min_ram returns True when no software stack provided."""
        result = stacks.validate_min_ram("t3.large", None)
        assert result is True

    @patch("res.resources.software_stacks.ec2_utils.get_instance_ram")
    def test_validate_min_ram_no_min_ram_value(self, mock_get_ram):
        """Test validate_min_ram returns True when min_ram_value is None."""
        # Setup
        software_stack_ddb = {
            stacks.SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY: None,
            stacks.SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY: "GiB",
        }
        mock_get_ram.return_value = (16384.0, "MiB")

        # Test
        result = stacks.validate_min_ram("t3.large", software_stack_ddb)

        # Assertions
        assert result is True

    @patch(
        "res.resources.software_stacks.ec2_utils.get_valid_instance_types_by_allowed_list"
    )
    @patch("res.resources.software_stacks.cluster_settings.get_setting")
    def test_get_valid_instance_types_by_software_stack_no_stack(
        self, mock_get_setting, mock_get_allowed
    ):
        """Test get_valid_instance_types_by_software_stack with no software stack."""
        # Setup
        mock_get_setting.return_value = ["t3", "m5"]
        mock_get_allowed.return_value = {
            "t3.large": INSTANCE_T3_LARGE,
            "m5.large": INSTANCE_M5_LARGE,
        }

        # Test
        result = stacks.get_valid_instance_types_by_software_stack(
            hibernation_support=False
        )

        # Assertions
        assert len(result) == 2
        mock_get_setting.assert_called_once_with("vdc.dcv_session.instance_types.allow")
        mock_get_allowed.assert_called_once_with(False, ["t3", "m5"])

    @patch("res.resources.software_stacks.ec2_utils.get_instance_ram")
    @patch("res.resources.software_stacks.ec2_utils.describe_image_id")
    @patch(
        "res.resources.software_stacks.ec2_utils.get_valid_instance_types_by_allowed_list"
    )
    @patch("res.resources.software_stacks.cluster_settings.get_setting")
    def test_get_valid_instance_types_by_software_stack_with_windows(
        self, mock_get_setting, mock_get_allowed, mock_describe_image, mock_get_ram
    ):
        """Test get_valid_instance_types_by_software_stack with Windows software stack."""
        # Setup
        software_stack_ddb = {
            stacks.SOFTWARE_STACK_DB_BASE_OS_KEY: "windows",
            stacks.SOFTWARE_STACK_DB_AMI_ID_KEY: "ami-windows",
            stacks.SOFTWARE_STACK_DB_ARCHITECTURE_KEY: "x86_64",
            stacks.SOFTWARE_STACK_DB_GPU_KEY: "NO_GPU",
            stacks.SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY: 4.0,
            stacks.SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY: "GiB",
            stacks.SOFTWARE_STACK_DB_NAME_KEY: "windows-stack",
            stacks.SOFTWARE_STACK_DB_TENANCY_KEY: "default",
        }

        mock_get_setting.return_value = ["t3", "m5"]
        mock_describe_image.return_value = {"BootMode": "uefi"}
        mock_get_allowed.return_value = {
            "t3.large": INSTANCE_T3_LARGE,  # Supports both uefi and legacy-bios
            "m5.metal": INSTANCE_M5_METAL,  # Only supports legacy-bios
        }
        mock_get_ram.return_value = (8192.0, "MiB")

        # Test
        result = stacks.get_valid_instance_types_by_software_stack(
            hibernation_support=False, software_stack=software_stack_ddb
        )

        # Assertions
        assert len(result) == 1
        assert (
            result[0]["InstanceType"] == "t3.large"
        )  # m5.metal filtered (doesn't support uefi)
        mock_describe_image.assert_called_once_with("ami-windows")

    @patch("res.resources.software_stacks.ec2_utils.get_instance_ram")
    @patch(
        "res.resources.software_stacks.ec2_utils.get_valid_instance_types_by_allowed_list"
    )
    @patch("res.resources.software_stacks.cluster_settings.get_setting")
    def test_get_valid_instance_types_by_software_stack_filters_rhel8_g4dn(
        self, mock_get_setting, mock_get_allowed, mock_get_ram
    ):
        """Test get_valid_instance_types_by_software_stack filters out g4dn for RHEL8."""
        # Setup
        software_stack_ddb = {
            stacks.SOFTWARE_STACK_DB_BASE_OS_KEY: "rhel8",
            stacks.SOFTWARE_STACK_DB_ARCHITECTURE_KEY: "x86_64",
            stacks.SOFTWARE_STACK_DB_GPU_KEY: "NVIDIA",
            stacks.SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY: 4.0,
            stacks.SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY: "GiB",
            stacks.SOFTWARE_STACK_DB_NAME_KEY: "rhel8-stack",
            stacks.SOFTWARE_STACK_DB_TENANCY_KEY: "default",
        }

        mock_get_setting.return_value = ["g4dn", "g5"]
        mock_get_allowed.return_value = {
            "g4dn.xlarge": INSTANCE_G4DN_XLARGE,
            "g5.xlarge": INSTANCE_G5_XLARGE,
        }
        mock_get_ram.return_value = (16384.0, "MiB")

        # Test
        result = stacks.get_valid_instance_types_by_software_stack(
            hibernation_support=False, software_stack=software_stack_ddb
        )

        # Assertions
        assert len(result) == 1
        assert result[0]["InstanceType"] == "g5.xlarge"  # g4dn should be filtered out

    @patch("res.resources.software_stacks.ec2_utils.get_instance_ram")
    @patch(
        "res.resources.software_stacks.ec2_utils.get_valid_instance_types_by_allowed_list"
    )
    @patch("res.resources.software_stacks.cluster_settings.get_setting")
    def test_get_valid_instance_types_by_software_stack_filters_by_architecture(
        self, mock_get_setting, mock_get_allowed, mock_get_ram
    ):
        """Test get_valid_instance_types_by_software_stack filters by architecture."""
        # Setup
        software_stack_ddb = {
            stacks.SOFTWARE_STACK_DB_BASE_OS_KEY: "amazonlinux2",
            stacks.SOFTWARE_STACK_DB_ARCHITECTURE_KEY: "arm64",
            stacks.SOFTWARE_STACK_DB_GPU_KEY: "NO_GPU",
            stacks.SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY: 2.0,
            stacks.SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY: "GiB",
            stacks.SOFTWARE_STACK_DB_NAME_KEY: "arm-stack",
            stacks.SOFTWARE_STACK_DB_TENANCY_KEY: "default",
        }

        mock_get_setting.return_value = ["t3", "t4g"]
        mock_get_allowed.return_value = {
            "t3.medium": INSTANCE_T3_MEDIUM,
            "t4g.medium": INSTANCE_T4G_MEDIUM,
        }
        mock_get_ram.return_value = (4096.0, "MiB")

        # Test
        result = stacks.get_valid_instance_types_by_software_stack(
            hibernation_support=False, software_stack=software_stack_ddb
        )

        # Assertions
        assert len(result) == 1
        assert result[0]["InstanceType"] == "t4g.medium"  # Only ARM64 instance

    @patch("res.resources.software_stacks.ec2_utils.get_instance_ram")
    @patch(
        "res.resources.software_stacks.ec2_utils.get_valid_instance_types_by_allowed_list"
    )
    @patch("res.resources.software_stacks.cluster_settings.get_setting")
    def test_get_valid_instance_types_by_software_stack_filters_by_gpu(
        self, mock_get_setting, mock_get_allowed, mock_get_ram
    ):
        """Test get_valid_instance_types_by_software_stack filters by GPU requirement."""
        # Setup
        software_stack_ddb = {
            stacks.SOFTWARE_STACK_DB_BASE_OS_KEY: "ubuntu2204",
            stacks.SOFTWARE_STACK_DB_ARCHITECTURE_KEY: "x86_64",
            stacks.SOFTWARE_STACK_DB_GPU_KEY: "NVIDIA",
            stacks.SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY: 8.0,
            stacks.SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY: "GiB",
            stacks.SOFTWARE_STACK_DB_NAME_KEY: "gpu-stack",
            stacks.SOFTWARE_STACK_DB_TENANCY_KEY: "default",
        }

        mock_get_setting.return_value = ["t3", "g4dn"]
        mock_get_allowed.return_value = {
            "t3.xlarge": INSTANCE_T3_XLARGE,
            "g4dn.xlarge": INSTANCE_G4DN_XLARGE,
        }
        mock_get_ram.return_value = (16384.0, "MiB")

        # Test
        result = stacks.get_valid_instance_types_by_software_stack(
            hibernation_support=False, software_stack=software_stack_ddb
        )

        # Assertions
        assert len(result) == 1
        assert result[0]["InstanceType"] == "g4dn.xlarge"  # Only GPU instance

    @patch("res.resources.software_stacks.ec2_utils.get_instance_ram")
    @patch(
        "res.resources.software_stacks.ec2_utils.get_valid_instance_types_by_allowed_list"
    )
    @patch("res.resources.software_stacks.cluster_settings.get_setting")
    def test_get_valid_instance_types_by_software_stack_filters_by_ram(
        self, mock_get_setting, mock_get_allowed, mock_get_ram
    ):
        """Test get_valid_instance_types_by_software_stack filters by minimum RAM."""
        # Setup
        software_stack_ddb = {
            stacks.SOFTWARE_STACK_DB_BASE_OS_KEY: "amazonlinux2",
            stacks.SOFTWARE_STACK_DB_ARCHITECTURE_KEY: "x86_64",
            stacks.SOFTWARE_STACK_DB_GPU_KEY: "NO_GPU",
            stacks.SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY: 8.0,
            stacks.SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY: "GiB",
            stacks.SOFTWARE_STACK_DB_NAME_KEY: "ram-stack",
            stacks.SOFTWARE_STACK_DB_TENANCY_KEY: "default",
        }

        mock_get_setting.return_value = ["t3"]
        mock_get_allowed.return_value = {
            "t3.small": INSTANCE_T3_SMALL,
            "t3.xlarge": INSTANCE_T3_XLARGE,
        }
        # Return different RAM values for each instance
        mock_get_ram.side_effect = [(2048.0, "MiB"), (16384.0, "MiB")]

        # Test
        result = stacks.get_valid_instance_types_by_software_stack(
            hibernation_support=False, software_stack=software_stack_ddb
        )

        # Assertions
        assert len(result) == 1
        assert result[0]["InstanceType"] == "t3.xlarge"  # Only instance with enough RAM

    @patch("res.resources.software_stacks.ec2_utils.get_instance_ram")
    @patch(
        "res.resources.software_stacks.ec2_utils.get_valid_instance_types_by_allowed_list"
    )
    @patch("res.resources.software_stacks.cluster_settings.get_setting")
    def test_get_valid_instance_types_filters_no_gpu_requirement(
        self, mock_get_setting, mock_get_allowed, mock_get_ram
    ):
        """Test that NO_GPU requirement filters out GPU instances."""
        # Setup
        software_stack_ddb = {
            stacks.SOFTWARE_STACK_DB_BASE_OS_KEY: "amazonlinux2",
            stacks.SOFTWARE_STACK_DB_ARCHITECTURE_KEY: "x86_64",
            stacks.SOFTWARE_STACK_DB_GPU_KEY: "NO_GPU",
            stacks.SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY: 8.0,
            stacks.SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY: "GiB",
            stacks.SOFTWARE_STACK_DB_NAME_KEY: "no-gpu-stack",
            stacks.SOFTWARE_STACK_DB_TENANCY_KEY: "default",
        }

        mock_get_setting.return_value = ["t3", "g4dn"]
        mock_get_allowed.return_value = {
            "t3.xlarge": INSTANCE_T3_XLARGE,
            "g4dn.xlarge": INSTANCE_G4DN_XLARGE,
        }
        mock_get_ram.return_value = (16384.0, "MiB")

        # Test
        result = stacks.get_valid_instance_types_by_software_stack(
            hibernation_support=False, software_stack=software_stack_ddb
        )

        # Assertions
        assert len(result) == 1
        assert result[0]["InstanceType"] == "t3.xlarge"  # GPU instance filtered out

    @patch("res.resources.software_stacks.ec2_utils.dedicated_hosts_supported")
    @patch("res.resources.software_stacks.ec2_utils.get_instance_ram")
    @patch(
        "res.resources.software_stacks.ec2_utils.get_valid_instance_types_by_allowed_list"
    )
    @patch("res.resources.software_stacks.cluster_settings.get_setting")
    def test_get_valid_instance_types_filters_by_tenancy(
        self, mock_get_setting, mock_get_allowed, mock_get_ram, mock_dedicated_hosts
    ):
        """Test that host tenancy filters instances without dedicated host support."""
        # Setup
        software_stack_ddb = {
            stacks.SOFTWARE_STACK_DB_BASE_OS_KEY: "amazonlinux2",
            stacks.SOFTWARE_STACK_DB_ARCHITECTURE_KEY: "x86_64",
            stacks.SOFTWARE_STACK_DB_GPU_KEY: "NO_GPU",
            stacks.SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY: 4.0,
            stacks.SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY: "GiB",
            stacks.SOFTWARE_STACK_DB_NAME_KEY: "host-tenancy-stack",
            stacks.SOFTWARE_STACK_DB_TENANCY_KEY: "host",
        }

        mock_get_setting.return_value = ["t3", "m5"]
        mock_get_allowed.return_value = {
            "t3.large": INSTANCE_T3_LARGE,
            "m5.large": INSTANCE_M5_LARGE,
        }
        mock_get_ram.return_value = (8192.0, "MiB")
        # t3.large doesn't support dedicated hosts, m5.large does
        mock_dedicated_hosts.side_effect = lambda instance: instance == "m5.large"

        # Test
        result = stacks.get_valid_instance_types_by_software_stack(
            hibernation_support=False, software_stack=software_stack_ddb
        )

        # Assertions
        assert len(result) == 1
        assert result[0]["InstanceType"] == "m5.large"  # Only dedicated host supported

    @patch("res.resources.software_stacks.ec2_utils.get_instance_ram")
    @patch(
        "res.resources.software_stacks.ec2_utils.get_valid_instance_types_by_allowed_list"
    )
    @patch("res.resources.software_stacks.cluster_settings.get_setting")
    def test_get_valid_instance_types_gpu_parameter_overrides_stack(
        self, mock_get_setting, mock_get_allowed, mock_get_ram
    ):
        """Test that gpu parameter overrides software_stack GPU setting."""
        # Setup
        software_stack_ddb = {
            stacks.SOFTWARE_STACK_DB_BASE_OS_KEY: "amazonlinux2",
            stacks.SOFTWARE_STACK_DB_ARCHITECTURE_KEY: "x86_64",
            stacks.SOFTWARE_STACK_DB_GPU_KEY: "NO_GPU",
            stacks.SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY: 8.0,
            stacks.SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY: "GiB",
            stacks.SOFTWARE_STACK_DB_NAME_KEY: "test-stack",
            stacks.SOFTWARE_STACK_DB_TENANCY_KEY: "default",
        }

        mock_get_setting.return_value = ["t3", "g4dn"]
        mock_get_allowed.return_value = {
            "t3.xlarge": INSTANCE_T3_XLARGE,
            "g4dn.xlarge": INSTANCE_G4DN_XLARGE,
        }
        mock_get_ram.return_value = (16384.0, "MiB")

        # Test - gpu parameter should override stack's NO_GPU setting
        result = stacks.get_valid_instance_types_by_software_stack(
            hibernation_support=False, software_stack=software_stack_ddb, gpu="NVIDIA"
        )

        # Assertions
        assert len(result) == 1
        assert result[0]["InstanceType"] == "g4dn.xlarge"  # GPU override worked

    @patch(
        "res.resources.software_stacks.ec2_utils.get_valid_instance_types_by_allowed_list"
    )
    @patch("res.resources.software_stacks.cluster_settings.get_setting")
    def test_get_valid_instance_types_hibernation_support_propagated(
        self, mock_get_setting, mock_get_allowed
    ):
        """Test that hibernation_support is properly propagated."""
        # Setup
        mock_get_setting.return_value = ["t3"]
        mock_get_allowed.return_value = {
            "t3.large": INSTANCE_T3_LARGE,
        }

        # Test with hibernation enabled
        stacks.get_valid_instance_types_by_software_stack(hibernation_support=True)

        # Assertions
        mock_get_allowed.assert_called_once_with(True, ["t3"])

    @patch("res.resources.software_stacks.projects.get_project")
    def test_list_software_stacks_paginated_expands_projects(self, mock_get_project):
        """
        Test list_software_stacks_paginated expands project details for all stacks
        """
        # Setup - mock project details
        mock_get_project.return_value = TEST_PROJECT

        # Test - list software stacks
        result, next_token = stacks.list_software_stacks_paginated()

        # Assertions
        assert len(result) == 1

        # Verify projects are expanded
        assert stacks.SOFTWARE_STACK_DB_PROJECTS_KEY in result[0]
        assert len(result[0][stacks.SOFTWARE_STACK_DB_PROJECTS_KEY]) == 1
        assert result[0][stacks.SOFTWARE_STACK_DB_PROJECTS_KEY][0] == TEST_PROJECT
