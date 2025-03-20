#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from unittest.mock import Mock, patch

import pytest
from ideavirtualdesktopcontroller.app.virtual_desktop_controller_utils import (
    VirtualDesktopControllerUtils,
)

from ideadatamodel import (
    VirtualDesktopArchitecture,
    VirtualDesktopBaseOS,
    VirtualDesktopGPU,
    VirtualDesktopPlacement,
    VirtualDesktopSoftwareStack,
    VirtualDesktopTenancy,
)

TEST_AMI = "ami-12345678"
TEST_WINDOWS_SOFTWARE_STACK = VirtualDesktopSoftwareStack(
    base_os=VirtualDesktopBaseOS.WINDOWS,
    ami_id=TEST_AMI,
    architecture=VirtualDesktopArchitecture.X86_64,
    gpu=VirtualDesktopGPU.NO_GPU,
)
TEST_NVIDIA_AL2_SOFTWARE_STACK = VirtualDesktopSoftwareStack(
    base_os=VirtualDesktopBaseOS.AMAZON_LINUX2,
    ami_id=TEST_AMI,
    architecture=VirtualDesktopArchitecture.X86_64,
    gpu=VirtualDesktopGPU.NVIDIA,
)
TEST_AMD_AL2_SOFTWARE_STACK = VirtualDesktopSoftwareStack(
    base_os=VirtualDesktopBaseOS.AMAZON_LINUX2,
    ami_id=TEST_AMI,
    architecture=VirtualDesktopArchitecture.X86_64,
    gpu=VirtualDesktopGPU.AMD,
)
TEST_DEDICATED_HOST_TENANCY_SOFTWARE_STACK = VirtualDesktopSoftwareStack(
    base_os=VirtualDesktopBaseOS.AMAZON_LINUX2,
    ami_id=TEST_AMI,
    architecture=VirtualDesktopArchitecture.X86_64,
    gpu=VirtualDesktopGPU.NO_GPU,
    placement=VirtualDesktopPlacement(
        tenancy=VirtualDesktopTenancy.HOST,
    ),
)
LEGACY_ONLY_INSTANCE_NAME = "test.legacy"
UEFI_ONLY_INSTANCE_NAME = "test.uefi"
BOTH_MODE_INSTANCE_NAME = "test.uefi-preferred"
NVIDIA_GPU_INSTANCE_NAME = "test.nvidia"
AMD_GPU_INSTANCE_NAME = "test.amd"
DEDICATED_HOST_SUPPORTED_INSTANCE_NAME = "test.dedicated-host-supported"
DEDICATED_HOST_UNSUPPORTED_INSTANCE_NAME = "test.dedicated-host-unsupported"
RPOCESSOR_INFO = {"SupportedArchitectures": ["x86_64"]}

TEST_INSTANCE_TYPES_CACHE = {
    "instance_types_names": [
        LEGACY_ONLY_INSTANCE_NAME,
        UEFI_ONLY_INSTANCE_NAME,
        BOTH_MODE_INSTANCE_NAME,
        NVIDIA_GPU_INSTANCE_NAME,
        AMD_GPU_INSTANCE_NAME,
        DEDICATED_HOST_SUPPORTED_INSTANCE_NAME,
        DEDICATED_HOST_UNSUPPORTED_INSTANCE_NAME,
    ],
    "instance_info": {
        LEGACY_ONLY_INSTANCE_NAME: {
            "SupportedBootModes": ["legacy-bios"],
            "ProcessorInfo": RPOCESSOR_INFO,
        },
        UEFI_ONLY_INSTANCE_NAME: {
            "SupportedBootModes": ["uefi"],
            "ProcessorInfo": RPOCESSOR_INFO,
        },
        BOTH_MODE_INSTANCE_NAME: {
            "SupportedBootModes": ["legacy-bios", "uefi"],
            "ProcessorInfo": RPOCESSOR_INFO,
        },
        NVIDIA_GPU_INSTANCE_NAME: {
            "SupportedBootModes": ["legacy-bios"],
            "ProcessorInfo": RPOCESSOR_INFO,
            "GpuInfo": {
                "Gpus": [
                    {
                        "Manufacturer": "NVIDIA",
                    }
                ]
            },
        },
        AMD_GPU_INSTANCE_NAME: {
            "SupportedBootModes": ["legacy-bios"],
            "ProcessorInfo": RPOCESSOR_INFO,
            "GpuInfo": {
                "Gpus": [
                    {
                        "Manufacturer": "AMD",
                    }
                ]
            },
        },
        DEDICATED_HOST_SUPPORTED_INSTANCE_NAME: {
            "ProcessorInfo": RPOCESSOR_INFO,
            "DedicatedHostsSupported": True,
        },
        DEDICATED_HOST_UNSUPPORTED_INSTANCE_NAME: {
            "ProcessorInfo": RPOCESSOR_INFO,
            "DedicatedHostsSupported": False,
        },
    },
}


@pytest.fixture
def virtual_desktop_controller_utils():
    context = Mock()
    return VirtualDesktopControllerUtils(context)


@pytest.fixture
def mock_cache():
    return TEST_INSTANCE_TYPES_CACHE


@pytest.fixture
def mock_environment(virtual_desktop_controller_utils, mock_cache):
    with (
        patch.object(
            virtual_desktop_controller_utils.context.cache().long_term(), "get"
        ) as mock_get,
        patch.object(
            virtual_desktop_controller_utils.context.config(), "get_list"
        ) as mock_get_list,
        patch.object(
            virtual_desktop_controller_utils, "describe_image_id"
        ) as mock_describe_image_id,
    ):

        mock_get.side_effect = lambda key: (
            mock_cache["instance_types_names"]
            if key
            == virtual_desktop_controller_utils.INSTANCE_TYPES_NAMES_LIST_CACHE_KEY
            else mock_cache["instance_info"]
        )
        mock_get_list.side_effect = [
            [
                LEGACY_ONLY_INSTANCE_NAME,
                UEFI_ONLY_INSTANCE_NAME,
                BOTH_MODE_INSTANCE_NAME,
                NVIDIA_GPU_INSTANCE_NAME,
                AMD_GPU_INSTANCE_NAME,
                DEDICATED_HOST_SUPPORTED_INSTANCE_NAME,
                DEDICATED_HOST_UNSUPPORTED_INSTANCE_NAME,
            ],
            [],
        ]

        yield virtual_desktop_controller_utils, mock_describe_image_id


def test_uefi_get_valid_instance_types(mock_environment):

    utils, mock_describe_image_id = mock_environment
    mock_describe_image_id.return_value = {"BootMode": "uefi"}
    result = utils.get_valid_instance_types_by_software_stack(
        hibernation_support=False, software_stack=TEST_WINDOWS_SOFTWARE_STACK
    )

    assert len(result) == 2
    assert (
        TEST_INSTANCE_TYPES_CACHE["instance_info"][LEGACY_ONLY_INSTANCE_NAME]
        not in result
    )


def test_uefi_preferred_get_valid_instance_types(mock_environment):

    utils, mock_describe_image_id = mock_environment
    mock_describe_image_id.return_value = {"BootMode": "uefi-preferred"}
    result = utils.get_valid_instance_types_by_software_stack(
        hibernation_support=False, software_stack=TEST_WINDOWS_SOFTWARE_STACK
    )

    assert len(result) == 5


def test_legacy_get_valid_instance_types(mock_environment):

    utils, mock_describe_image_id = mock_environment
    mock_describe_image_id.return_value = {"BootMode": "legacy-bios"}
    result = utils.get_valid_instance_types_by_software_stack(
        hibernation_support=False, software_stack=TEST_WINDOWS_SOFTWARE_STACK
    )

    assert len(result) == 2
    assert (
        TEST_INSTANCE_TYPES_CACHE["instance_info"][UEFI_ONLY_INSTANCE_NAME]
        not in result
    )


def test_no_boot_mode_get_valid_instance_types(mock_environment):
    utils, mock_describe_image_id = mock_environment
    mock_describe_image_id.return_value = {}
    result = utils.get_valid_instance_types_by_software_stack(
        hibernation_support=False, software_stack=TEST_WINDOWS_SOFTWARE_STACK
    )

    assert len(result) == 2
    assert (
        TEST_INSTANCE_TYPES_CACHE["instance_info"][UEFI_ONLY_INSTANCE_NAME]
        not in result
    )


def test_no_gpu_get_valid_instance_types(mock_environment):
    utils, mock_describe_image_id = mock_environment
    mock_describe_image_id.return_value = {"BootMode": "uefi-preferred"}
    result = utils.get_valid_instance_types_by_software_stack(
        hibernation_support=False, software_stack=TEST_WINDOWS_SOFTWARE_STACK
    )

    assert len(result) == 5
    assert (
        TEST_INSTANCE_TYPES_CACHE["instance_info"][NVIDIA_GPU_INSTANCE_NAME]
        not in result
    )
    assert (
        TEST_INSTANCE_TYPES_CACHE["instance_info"][AMD_GPU_INSTANCE_NAME] not in result
    )


def test_nvidia_gpu_get_valid_instance_types(mock_environment):
    utils, _ = mock_environment
    result = utils.get_valid_instance_types_by_software_stack(
        hibernation_support=False, software_stack=TEST_NVIDIA_AL2_SOFTWARE_STACK
    )

    assert len(result) == 1
    assert (
        TEST_INSTANCE_TYPES_CACHE["instance_info"][NVIDIA_GPU_INSTANCE_NAME] in result
    )


def test_amd_gpu_get_valid_instance_types(mock_environment):
    utils, _ = mock_environment
    result = utils.get_valid_instance_types_by_software_stack(
        hibernation_support=False, software_stack=TEST_AMD_AL2_SOFTWARE_STACK
    )

    assert len(result) == 1
    assert TEST_INSTANCE_TYPES_CACHE["instance_info"][AMD_GPU_INSTANCE_NAME] in result


def test_dedicated_host_tenancy_get_valid_instance_types(mock_environment):
    utils, _ = mock_environment
    result = utils.get_valid_instance_types_by_software_stack(
        hibernation_support=False,
        software_stack=TEST_DEDICATED_HOST_TENANCY_SOFTWARE_STACK,
    )

    assert len(result) == 1
    assert (
        TEST_INSTANCE_TYPES_CACHE["instance_info"][
            DEDICATED_HOST_SUPPORTED_INSTANCE_NAME
        ]
        in result
    )


def test_dedicated_hosts_supported_instance_type_return_true(mock_environment):
    utils, _ = mock_environment
    assert utils.dedicated_hosts_supported(DEDICATED_HOST_SUPPORTED_INSTANCE_NAME)


def test_dedicated_hosts_unsupported_instance_type_return_false(mock_environment):
    utils, _ = mock_environment
    assert not utils.dedicated_hosts_supported(DEDICATED_HOST_UNSUPPORTED_INSTANCE_NAME)
