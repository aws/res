#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from unittest.mock import Mock

from ideavirtualdesktopcontroller.app.software_stacks.virtual_desktop_software_stack_utils import (
    VirtualDesktopSoftwareStackUtils,
)

from ideadatamodel import (
    SocaMemory,
    VirtualDesktopBaseOS,
    VirtualDesktopGPU,
    VirtualDesktopPlacement,
    VirtualDesktopSoftwareStack,
    VirtualDesktopTenancy,
)


def test_validate_placement_dedicated_host_tenancy_missing_host_id_and_resource_group_return_false():
    test_software_stack = VirtualDesktopSoftwareStack(
        placement=VirtualDesktopPlacement(tenancy=VirtualDesktopTenancy.HOST)
    )
    assert not VirtualDesktopSoftwareStackUtils.validate_placement(test_software_stack)


def test_validate_placement_dedicated_host_tenancy_with_host_id_return_true():
    test_software_stack = VirtualDesktopSoftwareStack(
        placement=VirtualDesktopPlacement(
            tenancy=VirtualDesktopTenancy.HOST, host_id="test"
        )
    )
    assert VirtualDesktopSoftwareStackUtils.validate_placement(test_software_stack)


def test_validate_placement_dedicated_host_tenancy_with_host_resource_group_return_true():
    test_software_stack = VirtualDesktopSoftwareStack(
        placement=VirtualDesktopPlacement(
            tenancy=VirtualDesktopTenancy.HOST,
            host_resource_group_arn="test",
        )
    )
    assert VirtualDesktopSoftwareStackUtils.validate_placement(test_software_stack)


def test_validate_placement_dedicated_host_tenancy_with_host_id_and_resource_group_return_true():
    test_software_stack = VirtualDesktopSoftwareStack(
        placement=VirtualDesktopPlacement(
            tenancy=VirtualDesktopTenancy.HOST,
            host_id="test",
            host_resource_group_arn="test",
        )
    )
    assert not VirtualDesktopSoftwareStackUtils.validate_placement(test_software_stack)


def test_validate_placement_no_tenancy_specified_return_true():
    test_software_stack = VirtualDesktopSoftwareStack()
    assert not test_software_stack.placement
    assert VirtualDesktopSoftwareStackUtils.validate_placement(test_software_stack)
    assert test_software_stack.placement.tenancy == VirtualDesktopTenancy.DEFAULT


def test_validate_software_stack_fields_none_software_stack():
    utils = VirtualDesktopSoftwareStackUtils(Mock(), Mock())
    software_stack, is_valid = utils.validate_software_stack_fields(None)

    assert not is_valid
    assert software_stack.failure_reason == "software_stack missing"


def test_validate_software_stack_fields_missing_required_fields():
    utils = VirtualDesktopSoftwareStackUtils(Mock(), Mock())
    software_stack = VirtualDesktopSoftwareStack(
        description="test",
        ami_id="ami-123",
        base_os=VirtualDesktopBaseOS.WINDOWS,
        gpu=VirtualDesktopGPU.NVIDIA,
        min_ram=SocaMemory(value=10, unit="gb"),
        min_storage=SocaMemory(value=50, unit="gb"),
    )

    result_stack, is_valid = utils.validate_software_stack_fields(software_stack)
    assert not is_valid
    assert result_stack.failure_reason == "software_stack.name missing"


def test_validate_software_stack_fields_invalid_project_id():
    utils = VirtualDesktopSoftwareStackUtils(Mock(), Mock())
    software_stack = VirtualDesktopSoftwareStack(
        name="test",
        description="test",
        ami_id="ami-123",
        base_os=VirtualDesktopBaseOS.WINDOWS,
        gpu=VirtualDesktopGPU.NVIDIA,
        min_ram=SocaMemory(value=10, unit="gb"),
        min_storage=SocaMemory(value=50, unit="gb"),
        projects=[{"project_id": None}],
    )

    result_stack, is_valid = utils.validate_software_stack_fields(software_stack)
    assert not is_valid
    assert result_stack.failure_reason == "software_stack.project.project_id missing"


def test_validate_software_stack_fields_invalid_ami():
    utils = VirtualDesktopSoftwareStackUtils(Mock(), Mock())
    utils._controller_utils.describe_image_id = Mock(return_value=None)

    software_stack = VirtualDesktopSoftwareStack(
        name="test",
        description="test",
        ami_id="ami-123",
        base_os=VirtualDesktopBaseOS.WINDOWS,
        gpu=VirtualDesktopGPU.NVIDIA,
        min_ram=SocaMemory(value=10, unit="gb"),
        min_storage=SocaMemory(value=50, unit="gb"),
    )

    result_stack, is_valid = utils.validate_software_stack_fields(software_stack)
    assert not is_valid
    assert result_stack.failure_reason == "Invalid software_stack.ami_id: ami-123"


def test_validate_software_stack_fields_success():
    utils = VirtualDesktopSoftwareStackUtils(Mock(), Mock())
    utils._controller_utils.describe_image_id = Mock(
        return_value={"ImageId": "ami-123", "Architecture": "x86_64"}
    )

    software_stack = VirtualDesktopSoftwareStack(
        name="test",
        description="test",
        ami_id="ami-123",
        base_os=VirtualDesktopBaseOS.WINDOWS,
        gpu=VirtualDesktopGPU.NVIDIA,
        min_ram=SocaMemory(value=10, unit="gb"),
        min_storage=SocaMemory(value=50, unit="gb"),
    )

    result_stack, is_valid = utils.validate_software_stack_fields(software_stack)
    assert is_valid
    assert result_stack.architecture.value == "x86_64"
