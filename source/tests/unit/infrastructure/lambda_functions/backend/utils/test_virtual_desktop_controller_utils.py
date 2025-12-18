#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import sys
from unittest.mock import patch, MagicMock
import pytest
from botocore.exceptions import ClientError

# Add the backend directory to Python path to match utils import context
backend_path = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "../../../../../../idea/infrastructure/resources/lambda_functions/backend",
    )
)
sys.path.insert(0, backend_path)

from api.utils import virtual_desktop_controller_utils
from api.exceptions import BadRequestException
from api.models.res_memory import ResMemory
from api.models.virtual_desktop_architecture import VirtualDesktopArchitecture
from api.models.virtual_desktop_base_os import VirtualDesktopBaseOs
from api.models.virtual_desktop_gpu import VirtualDesktopGpu
from api.models.virtual_desktop_session import VirtualDesktopSession
from api.models.virtual_desktop_software_stack import VirtualDesktopSoftwareStack


class TestVirtualDesktopControllerUtils:
    """Test class for virtual_desktop_controller_utils module."""

    def setup_method(self):
        """Setup test fixtures."""
        # Clear the cache before each test to ensure clean state
        virtual_desktop_controller_utils._instance_types_cache.clear()

    @patch.object(virtual_desktop_controller_utils, 'get_instance_type_info')
    def test_get_instance_ram_success(self, mock_get_instance_type_info):
        """Test get_instance_ram returns correct ResMemory object."""
        # Setup mock
        mock_get_instance_type_info.return_value = {
            "MemoryInfo": {"SizeInMiB": 4096}
        }

        # Test
        result = virtual_desktop_controller_utils.get_instance_ram("t3.large")

        # Assertions
        assert isinstance(result, ResMemory)
        assert result.value == 4096.0
        assert result.unit == "MiB"
        mock_get_instance_type_info.assert_called_once_with("t3.large")

    @patch.object(virtual_desktop_controller_utils, 'get_instance_type_info')
    def test_get_instance_ram_missing_memory_info(self, mock_get_instance_type_info):
        """Test get_instance_ram with missing memory info."""
        # Setup mock
        mock_get_instance_type_info.return_value = {}

        # Test
        result = virtual_desktop_controller_utils.get_instance_ram("t3.nano")

        # Assertions
        assert isinstance(result, ResMemory)
        assert result.value == 0.0
        assert result.unit == "MiB"

    @patch.object(virtual_desktop_controller_utils, 'get_instance_type_info')
    def test_get_architecture_x86_64(self, mock_get_instance_type_info):
        """Test get_architecture returns x86_64 architecture."""
        # Setup mock
        mock_get_instance_type_info.return_value = {
            "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]}
        }

        # Test
        result = virtual_desktop_controller_utils.get_architecture("t3.large")

        # Assertions
        assert result == VirtualDesktopArchitecture.X86_64

    @patch.object(virtual_desktop_controller_utils, 'get_instance_type_info')
    def test_get_architecture_arm64(self, mock_get_instance_type_info):
        """Test get_architecture returns ARM64 architecture."""
        # Setup mock
        mock_get_instance_type_info.return_value = {
            "ProcessorInfo": {"SupportedArchitectures": ["arm64"]}
        }

        # Test
        result = virtual_desktop_controller_utils.get_architecture("t4g.large")

        # Assertions
        assert result == VirtualDesktopArchitecture.ARM64

    @patch.object(virtual_desktop_controller_utils, 'get_instance_type_info')
    def test_get_gpu_manufacturer_nvidia(self, mock_get_instance_type_info):
        """Test get_gpu_manufacturer returns NVIDIA."""
        # Setup mock
        mock_get_instance_type_info.return_value = {
            "GpuInfo": {"Gpus": [{"Manufacturer": "NVIDIA"}]}
        }

        # Test
        result = virtual_desktop_controller_utils.get_gpu_manufacturer("g4dn.large")

        # Assertions
        assert result == VirtualDesktopGpu.NVIDIA

    @patch.object(virtual_desktop_controller_utils, 'get_instance_type_info')
    def test_get_gpu_manufacturer_amd(self, mock_get_instance_type_info):
        """Test get_gpu_manufacturer returns AMD."""
        # Setup mock
        mock_get_instance_type_info.return_value = {
            "GpuInfo": {"Gpus": [{"Manufacturer": "AMD"}]}
        }

        # Test
        result = virtual_desktop_controller_utils.get_gpu_manufacturer("g4ad.large")

        # Assertions
        assert result == VirtualDesktopGpu.AMD

    @patch.object(virtual_desktop_controller_utils, 'get_instance_type_info')
    def test_get_gpu_manufacturer_no_gpu(self, mock_get_instance_type_info):
        """Test get_gpu_manufacturer returns NO_GPU when no GPUs present."""
        # Setup mock
        mock_get_instance_type_info.return_value = {
            "GpuInfo": {"Gpus": []}
        }

        # Test
        result = virtual_desktop_controller_utils.get_gpu_manufacturer("t3.large")

        # Assertions
        assert result == VirtualDesktopGpu.NO_GPU

    @patch.object(virtual_desktop_controller_utils, 'get_instance_type_info')
    def test_is_gpu_instance_true(self, mock_get_instance_type_info):
        """Test is_gpu_instance returns True for GPU instances."""
        # Setup mock
        mock_get_instance_type_info.return_value = {
            "GpuInfo": {"Gpus": [{"Manufacturer": "NVIDIA"}]}
        }

        # Test
        result = virtual_desktop_controller_utils.is_gpu_instance("g4dn.large")

        # Assertions
        assert result is True

    @patch.object(virtual_desktop_controller_utils, 'get_instance_type_info')
    def test_is_gpu_instance_false(self, mock_get_instance_type_info):
        """Test is_gpu_instance returns False for non-GPU instances."""
        # Setup mock
        mock_get_instance_type_info.return_value = {
            "GpuInfo": {"Gpus": []}
        }

        # Test
        result = virtual_desktop_controller_utils.is_gpu_instance("t3.large")

        # Assertions
        assert result is False

    @patch.object(virtual_desktop_controller_utils, 'get_instance_type_info')
    def test_dedicated_hosts_supported_true(self, mock_get_instance_type_info):
        """Test dedicated_hosts_supported returns True when supported."""
        # Setup mock
        mock_get_instance_type_info.return_value = {
            "DedicatedHostsSupported": True
        }

        # Test
        result = virtual_desktop_controller_utils.dedicated_hosts_supported("c5.large")

        # Assertions
        assert result is True

    @patch.object(virtual_desktop_controller_utils, 'get_instance_type_info')
    def test_dedicated_hosts_supported_false(self, mock_get_instance_type_info):
        """Test dedicated_hosts_supported returns False when not supported."""
        # Setup mock
        mock_get_instance_type_info.return_value = {
            "DedicatedHostsSupported": False
        }

        # Test
        result = virtual_desktop_controller_utils.dedicated_hosts_supported("t3.large")

        # Assertions
        assert result is False

    @patch.object(virtual_desktop_controller_utils, 'get_instance_ram')
    @patch.object(virtual_desktop_controller_utils, 'res_memory_utils')
    def test_validate_min_ram_success(self, mock_res_memory_utils, mock_get_instance_ram):
        """Test validate_min_ram returns True when instance has enough RAM."""
        # Setup mocks
        software_stack = VirtualDesktopSoftwareStack(
            min_ram=ResMemory(value=4.0, unit="GiB")
        )
        mock_get_instance_ram.return_value = ResMemory(value=8192.0, unit="MiB")
        mock_res_memory_utils.is_greater_than.return_value = False  # Software stack requirement NOT greater

        # Test
        result = virtual_desktop_controller_utils.validate_min_ram("t3.large", software_stack)

        # Assertions
        assert result is True
        mock_res_memory_utils.is_greater_than.assert_called_once()

    @patch.object(virtual_desktop_controller_utils, 'get_instance_ram')
    @patch.object(virtual_desktop_controller_utils, 'res_memory_utils')
    def test_validate_min_ram_insufficient_memory(self, mock_res_memory_utils, mock_get_instance_ram):
        """Test validate_min_ram returns False when instance has insufficient RAM."""
        # Setup mocks
        software_stack = VirtualDesktopSoftwareStack(
            name="High Memory Stack",
            min_ram=ResMemory(value=16.0, unit="GiB")
        )
        mock_get_instance_ram.return_value = ResMemory(value=4096.0, unit="MiB")
        mock_res_memory_utils.is_greater_than.return_value = True  # Software stack requirement IS greater

        # Test
        result = virtual_desktop_controller_utils.validate_min_ram("t3.large", software_stack)

        # Assertions
        assert result is False

    def test_validate_min_ram_no_software_stack(self):
        """Test validate_min_ram returns True when no software stack provided."""
        # Test
        result = virtual_desktop_controller_utils.validate_min_ram("t3.large", None)

        # Assertions
        assert result is True

    @patch.object(virtual_desktop_controller_utils, 'describe_image_id')
    def test_set_software_stack_architecture_success_with_auto_detect(self, mock_describe_image_id):
        """Test set_software_stack_architecture auto-detects architecture when not provided."""
        # Setup
        software_stack = VirtualDesktopSoftwareStack(
            ami_id="ami-12345678",
            architecture=None  # No architecture provided
        )
        mock_describe_image_id.return_value = {"Architecture": "x86_64"}

        # Test
        virtual_desktop_controller_utils.set_software_stack_architecture(software_stack)

        # Assertions
        assert software_stack.architecture == VirtualDesktopArchitecture.X86_64
        mock_describe_image_id.assert_called_once_with("ami-12345678")

    @patch.object(virtual_desktop_controller_utils, 'describe_image_id')
    def test_set_software_stack_architecture_success_with_matching_architecture(self, mock_describe_image_id):
        """Test set_software_stack_architecture succeeds when provided architecture matches AMI."""
        # Setup
        software_stack = VirtualDesktopSoftwareStack(
            ami_id="ami-87654321",
            architecture=VirtualDesktopArchitecture.ARM64
        )
        mock_describe_image_id.return_value = {"Architecture": "arm64"}

        # Test
        virtual_desktop_controller_utils.set_software_stack_architecture(software_stack)

        # Assertions - architecture should remain unchanged
        assert software_stack.architecture == VirtualDesktopArchitecture.ARM64
        mock_describe_image_id.assert_called_once_with("ami-87654321")

    @patch.object(virtual_desktop_controller_utils, 'describe_image_id')
    def test_set_software_stack_architecture_invalid_ami(self, mock_describe_image_id):
        """Test set_software_stack_architecture raises exception for invalid AMI."""
        # Setup
        software_stack = VirtualDesktopSoftwareStack(
            ami_id="ami-invalid",
            architecture=VirtualDesktopArchitecture.X86_64
        )
        mock_describe_image_id.return_value = {}  # Empty dict indicates invalid AMI

        # Test and assert exception
        with pytest.raises(BadRequestException) as exc_info:
            virtual_desktop_controller_utils.set_software_stack_architecture(software_stack)

        assert "Invalid software_stack.ami_id: ami-invalid" in str(exc_info.value)

    @patch.object(virtual_desktop_controller_utils, 'describe_image_id')
    def test_set_software_stack_architecture_architecture_mismatch(self, mock_describe_image_id):
        """Test set_software_stack_architecture raises exception for architecture mismatch."""
        # Setup
        software_stack = VirtualDesktopSoftwareStack(
            ami_id="ami-12345678",
            architecture=VirtualDesktopArchitecture.X86_64  # x86_64 requested
        )
        mock_describe_image_id.return_value = {"Architecture": "arm64"}  # But AMI is ARM64

        # Test and assert exception
        with pytest.raises(BadRequestException) as exc_info:
            virtual_desktop_controller_utils.set_software_stack_architecture(software_stack)

        assert "Invalid software_stack.ami_id: ami-12345678 with architecture: x86_64" in str(exc_info.value)

    @patch.object(virtual_desktop_controller_utils._aws_client_provider, 'ssm')
    def test_get_systems_manager_parameter_success(self, mock_ssm):
        """Test get_systems_manager_parameter returns parameter successfully."""
        # Setup mock
        mock_ssm_client = MagicMock()
        mock_ssm.return_value = mock_ssm_client
        mock_ssm_client.get_parameter.return_value = {
            "Parameter": {"Name": "test-param", "Value": "test-value"}
        }

        # Test
        result = virtual_desktop_controller_utils.get_systems_manager_parameter("arn:aws:ssm:us-east-1:123456789012:parameter/test-param")

        # Assertions
        assert result == {"Name": "test-param", "Value": "test-value"}
        mock_ssm_client.get_parameter.assert_called_once_with(
            Name="arn:aws:ssm:us-east-1:123456789012:parameter/test-param"
        )

    @patch.object(virtual_desktop_controller_utils._aws_client_provider, 'ssm')
    def test_get_systems_manager_parameter_client_error(self, mock_ssm):
        """Test get_systems_manager_parameter handles ClientError gracefully."""
        # Setup mock
        mock_ssm_client = MagicMock()
        mock_ssm.return_value = mock_ssm_client
        mock_ssm_client.get_parameter.side_effect = ClientError(
            {"Error": {"Code": "ParameterNotFound"}}, "GetParameter"
        )

        # Test
        result = virtual_desktop_controller_utils.get_systems_manager_parameter("invalid-param")

        # Assertions
        assert result == {}

    @patch.object(virtual_desktop_controller_utils, 'get_systems_manager_parameter')
    @patch.object(virtual_desktop_controller_utils._aws_client_provider, 'ec2')
    def test_describe_image_id_success(self, mock_ec2, mock_get_ssm_param):
        """Test describe_image_id returns image info successfully."""
        # Setup mock
        mock_ec2_client = MagicMock()
        mock_ec2.return_value = mock_ec2_client
        mock_ec2_client.describe_images.return_value = {
            "Images": [{"ImageId": "ami-12345678", "Architecture": "x86_64"}]
        }

        # Test
        result = virtual_desktop_controller_utils.describe_image_id("ami-12345678")

        # Assertions
        assert result == {"ImageId": "ami-12345678", "Architecture": "x86_64"}
        mock_ec2_client.describe_images.assert_called_once_with(ImageIds=["ami-12345678"])

    @patch.object(virtual_desktop_controller_utils, 'get_systems_manager_parameter')
    @patch.object(virtual_desktop_controller_utils._aws_client_provider, 'ec2')
    def test_describe_image_id_arn_parameter(self, mock_ec2, mock_get_ssm_param):
        """Test describe_image_id handles ARN parameter correctly."""
        # Setup mocks
        mock_get_ssm_param.return_value = {"Value": "ami-87654321"}
        mock_ec2_client = MagicMock()
        mock_ec2.return_value = mock_ec2_client
        mock_ec2_client.describe_images.return_value = {
            "Images": [{"ImageId": "ami-87654321", "Architecture": "arm64"}]
        }

        # Test
        result = virtual_desktop_controller_utils.describe_image_id("arn:aws:ssm:us-east-1:123456789012:parameter/ami-param")

        # Assertions
        assert result == {"ImageId": "ami-87654321", "Architecture": "arm64"}
        mock_get_ssm_param.assert_called_once_with("arn:aws:ssm:us-east-1:123456789012:parameter/ami-param")
        mock_ec2_client.describe_images.assert_called_once_with(ImageIds=["ami-87654321"])

    @patch.object(virtual_desktop_controller_utils._aws_client_provider, 'ec2')
    def test_describe_image_id_client_error(self, mock_ec2):
        """Test describe_image_id handles ClientError gracefully."""
        # Setup mock
        mock_ec2_client = MagicMock()
        mock_ec2.return_value = mock_ec2_client
        mock_ec2_client.describe_images.side_effect = ClientError(
            {"Error": {"Code": "InvalidAMIID.NotFound"}}, "DescribeImages"
        )

        # Test
        result = virtual_desktop_controller_utils.describe_image_id("ami-invalid")

        # Assertions
        assert result == {}

    def test_describe_image_id_empty_ami_id(self):
        """Test describe_image_id returns empty dict for empty AMI ID."""
        # Test
        result = virtual_desktop_controller_utils.describe_image_id("")

        # Assertions
        assert result == {}

    def test_describe_image_id_none_ami_id(self):
        """Test describe_image_id returns empty dict for None AMI ID."""
        # Test
        result = virtual_desktop_controller_utils.describe_image_id(None)

        # Assertions
        assert result == {}

    @patch.object(virtual_desktop_controller_utils._aws_client_provider, 'ec2')
    def test_describe_image_id_no_images_returned(self, mock_ec2):
        """Test describe_image_id returns empty dict when no images found."""
        # Setup mock
        mock_ec2_client = MagicMock()
        mock_ec2.return_value = mock_ec2_client
        mock_ec2_client.describe_images.return_value = {"Images": []}

        # Test
        result = virtual_desktop_controller_utils.describe_image_id("ami-nonexistent")

        # Assertions
        assert result == {}
