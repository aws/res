#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from unittest.mock import MagicMock, Mock, patch

import pytest
from botocore.exceptions import ClientError
from res.resources import software_stacks
from res.utils import ec2_utils


class TestEC2Utils:
    """Test class for ec2_utils module."""

    def setup_method(self):
        """Setup test fixtures."""
        # Clear the cache before each test to ensure clean state
        ec2_utils.instance_types_cache.clear()

    @patch.object(ec2_utils, "get_instance_type_info")
    def test_get_instance_ram_success(self, mock_get_instance_type_info):
        """Test get_instance_ram returns correct tuple."""
        # Setup mock
        mock_get_instance_type_info.return_value = {"MemoryInfo": {"SizeInMiB": 4096}}

        # Test
        result = ec2_utils.get_instance_ram("t3.large")

        # Assertions
        assert result == (4096.0, "MiB")
        mock_get_instance_type_info.assert_called_once_with("t3.large")

    @patch.object(ec2_utils, "get_instance_type_info")
    def test_get_instance_ram_missing_memory_info(self, mock_get_instance_type_info):
        """Test get_instance_ram with missing memory info."""
        # Setup mock
        mock_get_instance_type_info.return_value = {}

        # Test
        result = ec2_utils.get_instance_ram("t3.nano")

        # Assertions
        assert result == (0.0, "MiB")

    @patch.object(ec2_utils, "get_instance_type_info")
    def test_get_architecture_x86_64(self, mock_get_instance_type_info):
        """Test get_architecture returns x86_64 architecture."""
        # Setup mock
        mock_get_instance_type_info.return_value = {
            "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]}
        }

        # Test
        result = ec2_utils.get_architecture("t3.large")

        # Assertions
        assert result == "x86_64"

    @patch.object(ec2_utils, "get_instance_type_info")
    def test_get_architecture_arm64(self, mock_get_instance_type_info):
        """Test get_architecture returns arm64 architecture."""
        # Setup mock
        mock_get_instance_type_info.return_value = {
            "ProcessorInfo": {"SupportedArchitectures": ["arm64"]}
        }

        # Test
        result = ec2_utils.get_architecture("t4g.large")

        # Assertions
        assert result == "arm64"

    @patch.object(ec2_utils, "get_instance_type_info")
    def test_get_architecture_none_when_unsupported(self, mock_get_instance_type_info):
        """Test get_architecture returns None for unsupported architecture."""
        # Setup mock
        mock_get_instance_type_info.return_value = {
            "ProcessorInfo": {"SupportedArchitectures": ["unknown_arch"]}
        }

        # Test
        result = ec2_utils.get_architecture("unknown.type")

        # Assertions
        assert result is None

    @patch.object(ec2_utils, "get_instance_type_info")
    def test_get_gpu_manufacturer_nvidia(self, mock_get_instance_type_info):
        """Test get_gpu_manufacturer returns NVIDIA."""
        # Setup mock
        mock_get_instance_type_info.return_value = {
            "GpuInfo": {"Gpus": [{"Manufacturer": "NVIDIA"}]}
        }

        # Test
        result = ec2_utils.get_gpu_manufacturer("g4dn.large")

        # Assertions
        assert result == ec2_utils.VirtualDesktopGpu.NVIDIA

    @patch.object(ec2_utils, "get_instance_type_info")
    def test_get_gpu_manufacturer_amd(self, mock_get_instance_type_info):
        """Test get_gpu_manufacturer returns AMD."""
        # Setup mock
        mock_get_instance_type_info.return_value = {
            "GpuInfo": {"Gpus": [{"Manufacturer": "AMD"}]}
        }

        # Test
        result = ec2_utils.get_gpu_manufacturer("g4ad.large")

        # Assertions
        assert result == ec2_utils.VirtualDesktopGpu.AMD

    @patch.object(ec2_utils, "get_instance_type_info")
    def test_get_gpu_manufacturer_no_gpu(self, mock_get_instance_type_info):
        """Test get_gpu_manufacturer returns NO_GPU when no GPUs present."""
        # Setup mock
        mock_get_instance_type_info.return_value = {"GpuInfo": {"Gpus": []}}

        # Test
        result = ec2_utils.get_gpu_manufacturer("t3.large")

        # Assertions
        assert result == ec2_utils.VirtualDesktopGpu.NO_GPU

    @patch.object(ec2_utils, "get_instance_type_info")
    def test_get_gpu_manufacturer_case_insensitive(self, mock_get_instance_type_info):
        """Test get_gpu_manufacturer handles case-insensitive manufacturer names."""
        # Setup mock
        mock_get_instance_type_info.return_value = {
            "GpuInfo": {"Gpus": [{"Manufacturer": "Nvidia"}]}  # lowercase
        }

        # Test
        result = ec2_utils.get_gpu_manufacturer("g4dn.large")

        # Assertions
        assert result == ec2_utils.VirtualDesktopGpu.NVIDIA

    @patch.object(ec2_utils, "get_instance_type_info")
    def test_is_gpu_instance_true(self, mock_get_instance_type_info):
        """Test is_gpu_instance returns True for GPU instances."""
        # Setup mock
        mock_get_instance_type_info.return_value = {
            "GpuInfo": {"Gpus": [{"Manufacturer": "NVIDIA"}]}
        }

        # Test
        result = ec2_utils.is_gpu_instance("g4dn.large")

        # Assertions
        assert result is True

    @patch.object(ec2_utils, "get_instance_type_info")
    def test_is_gpu_instance_false(self, mock_get_instance_type_info):
        """Test is_gpu_instance returns False for non-GPU instances."""
        # Setup mock
        mock_get_instance_type_info.return_value = {"GpuInfo": {"Gpus": []}}

        # Test
        result = ec2_utils.is_gpu_instance("t3.large")

        # Assertions
        assert result is False

    @patch.object(ec2_utils, "get_instance_type_info")
    def test_dedicated_hosts_supported_true(self, mock_get_instance_type_info):
        """Test dedicated_hosts_supported returns True when supported."""
        # Setup mock
        mock_get_instance_type_info.return_value = {"DedicatedHostsSupported": True}

        # Test
        result = ec2_utils.dedicated_hosts_supported("c5.large")

        # Assertions
        assert result is True

    @patch.object(ec2_utils, "get_instance_type_info")
    def test_dedicated_hosts_supported_false(self, mock_get_instance_type_info):
        """Test dedicated_hosts_supported returns False when not supported."""
        # Setup mock
        mock_get_instance_type_info.return_value = {"DedicatedHostsSupported": False}

        # Test
        result = ec2_utils.dedicated_hosts_supported("t3.large")

        # Assertions
        assert result is False

    @patch.object(ec2_utils, "get_instance_type_info")
    def test_dedicated_hosts_supported_missing_key(self, mock_get_instance_type_info):
        """Test dedicated_hosts_supported returns False when key is missing."""
        # Setup mock
        mock_get_instance_type_info.return_value = {}

        # Test
        result = ec2_utils.dedicated_hosts_supported("t3.large")

        # Assertions
        assert result is False

    @patch.object(ec2_utils._aws_client_provider, "ssm")
    def test_get_systems_manager_parameter_success(self, mock_ssm):
        """Test get_systems_manager_parameter returns parameter successfully."""
        # Setup mock
        mock_ssm_client = MagicMock()
        mock_ssm.return_value = mock_ssm_client
        mock_ssm_client.get_parameter.return_value = {
            "Parameter": {"Name": "test-param", "Value": "test-value"}
        }

        # Test
        result = ec2_utils.get_systems_manager_parameter(
            "arn:aws:ssm:us-east-1:123456789012:parameter/test-param"
        )

        # Assertions
        assert result == {"Name": "test-param", "Value": "test-value"}
        mock_ssm_client.get_parameter.assert_called_once_with(
            Name="arn:aws:ssm:us-east-1:123456789012:parameter/test-param"
        )

    @patch.object(ec2_utils._aws_client_provider, "ssm")
    def test_get_systems_manager_parameter_client_error(self, mock_ssm):
        """Test get_systems_manager_parameter handles ClientError gracefully."""
        # Setup mock
        mock_ssm_client = MagicMock()
        mock_ssm.return_value = mock_ssm_client
        mock_ssm_client.get_parameter.side_effect = ClientError(
            {"Error": {"Code": "ParameterNotFound"}}, "GetParameter"
        )

        # Test
        result = ec2_utils.get_systems_manager_parameter("invalid-param")

        # Assertions
        assert result == {}

    @patch.object(ec2_utils, "get_systems_manager_parameter")
    @patch.object(ec2_utils._aws_client_provider, "ec2")
    def test_describe_image_id_success(self, mock_ec2, mock_get_ssm_param):
        """Test describe_image_id returns image info successfully."""
        # Setup mock
        mock_ec2_client = MagicMock()
        mock_ec2.return_value = mock_ec2_client
        mock_ec2_client.describe_images.return_value = {
            "Images": [{"ImageId": "ami-12345678", "Architecture": "x86_64"}]
        }

        # Test
        result = ec2_utils.describe_image_id("ami-12345678")

        # Assertions
        assert result == {"ImageId": "ami-12345678", "Architecture": "x86_64"}
        mock_ec2_client.describe_images.assert_called_once_with(
            ImageIds=["ami-12345678"]
        )

    @patch.object(ec2_utils, "get_systems_manager_parameter")
    @patch.object(ec2_utils._aws_client_provider, "ec2")
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
        result = ec2_utils.describe_image_id(
            "arn:aws:ssm:us-east-1:123456789012:parameter/ami-param"
        )

        # Assertions
        assert result == {"ImageId": "ami-87654321", "Architecture": "arm64"}
        mock_get_ssm_param.assert_called_once_with(
            "arn:aws:ssm:us-east-1:123456789012:parameter/ami-param"
        )
        mock_ec2_client.describe_images.assert_called_once_with(
            ImageIds=["ami-87654321"]
        )

    @patch.object(ec2_utils._aws_client_provider, "ec2")
    def test_describe_image_id_client_error(self, mock_ec2):
        """Test describe_image_id handles ClientError gracefully."""
        # Setup mock
        mock_ec2_client = MagicMock()
        mock_ec2.return_value = mock_ec2_client
        mock_ec2_client.describe_images.side_effect = ClientError(
            {"Error": {"Code": "InvalidAMIID.NotFound"}}, "DescribeImages"
        )

        # Test
        result = ec2_utils.describe_image_id("ami-invalid")

        # Assertions
        assert result == {}

    def test_describe_image_id_empty_ami_id(self):
        """Test describe_image_id returns empty dict for empty AMI ID."""
        result = ec2_utils.describe_image_id("")
        assert result == {}

    def test_describe_image_id_none_ami_id(self):
        """Test describe_image_id returns empty dict for None AMI ID."""
        result = ec2_utils.describe_image_id(None)
        assert result == {}

    @patch.object(ec2_utils._aws_client_provider, "ec2")
    def test_describe_image_id_no_images_returned(self, mock_ec2):
        """Test describe_image_id returns empty dict when no images found."""
        # Setup mock
        mock_ec2_client = MagicMock()
        mock_ec2.return_value = mock_ec2_client
        mock_ec2_client.describe_images.return_value = {"Images": []}

        # Test
        result = ec2_utils.describe_image_id("ami-nonexistent")

        # Assertions
        assert result == {}

    @patch.object(ec2_utils._aws_client_provider, "ec2")
    def test_add_instance_data_to_cache(self, mock_ec2):
        """Test add_instance_data_to_cache populates cache correctly."""
        # Setup mock
        mock_ec2_client = MagicMock()
        mock_ec2.return_value = mock_ec2_client
        mock_ec2_client.describe_instance_types.return_value = {
            "InstanceTypes": [
                {"InstanceType": "t3.micro", "MemoryInfo": {"SizeInMiB": 1024}},
                {"InstanceType": "t3.small", "MemoryInfo": {"SizeInMiB": 2048}},
            ]
        }

        # Test
        test_cache = {}
        ec2_utils.add_instance_data_to_cache(test_cache)

        # Assertions
        assert "aws.ec2.all-instance-types-names-list" in test_cache
        assert "aws.ec2.all-instance-types-data" in test_cache
        assert "t3.micro" in test_cache["aws.ec2.all-instance-types-names-list"]
        assert "t3.small" in test_cache["aws.ec2.all-instance-types-names-list"]
        assert (
            test_cache["aws.ec2.all-instance-types-data"]["t3.micro"]["MemoryInfo"][
                "SizeInMiB"
            ]
            == 1024
        )

    @patch.object(ec2_utils._aws_client_provider, "ec2")
    def test_add_instance_data_to_cache_pagination(self, mock_ec2):
        """Test add_instance_data_to_cache handles pagination."""
        # Setup mock
        mock_ec2_client = MagicMock()
        mock_ec2.return_value = mock_ec2_client
        mock_ec2_client.describe_instance_types.side_effect = [
            {"InstanceTypes": [{"InstanceType": "t3.micro"}], "NextToken": "token1"},
            {
                "InstanceTypes": [{"InstanceType": "t3.small"}],
            },
        ]

        # Test
        test_cache = {}
        ec2_utils.add_instance_data_to_cache(test_cache)

        # Assertions
        assert len(test_cache["aws.ec2.all-instance-types-names-list"]) == 2
        assert mock_ec2_client.describe_instance_types.call_count == 2

    @patch.object(ec2_utils, "add_instance_data_to_cache")
    def test_get_instance_type_info_uses_cache(self, mock_add_to_cache):
        """Test get_instance_type_info uses cached data."""
        # Setup cache
        ec2_utils.instance_types_cache["aws.ec2.all-instance-types-data"] = {
            "t3.large": {"InstanceType": "t3.large", "MemoryInfo": {"SizeInMiB": 8192}}
        }

        # Test
        result = ec2_utils.get_instance_type_info("t3.large")

        # Assertions
        assert result == {"InstanceType": "t3.large", "MemoryInfo": {"SizeInMiB": 8192}}
        mock_add_to_cache.assert_not_called()  # Should not fetch if cached

    @patch.object(ec2_utils, "add_instance_data_to_cache")
    def test_get_instance_type_info_populates_cache_when_empty(self, mock_add_to_cache):
        """Test get_instance_type_info populates cache when empty."""

        # Setup
        def populate_cache(cache_dict):
            cache_dict["aws.ec2.all-instance-types-data"] = {
                "t3.large": {"InstanceType": "t3.large"}
            }

        mock_add_to_cache.side_effect = populate_cache

        # Test
        result = ec2_utils.get_instance_type_info("t3.large")

        # Assertions
        mock_add_to_cache.assert_called_once()
        assert result == {"InstanceType": "t3.large"}

    @patch("res.resources.cluster_settings.get_setting")
    @patch.object(ec2_utils, "add_instance_data_to_cache")
    def test_get_valid_instance_types_by_allowed_list(
        self, mock_add_to_cache, mock_get_setting
    ):
        """Test get_valid_instance_types_by_allowed_list filters correctly."""

        # Setup
        def populate_cache(cache_dict):
            cache_dict["aws.ec2.all-instance-types-names-list"] = [
                "t3.micro",
                "t3.small",
                "t3.large",
                "g4dn.xlarge",
            ]
            cache_dict["aws.ec2.all-instance-types-data"] = {
                "t3.micro": {"HibernationSupported": False},
                "t3.small": {"HibernationSupported": True},
                "t3.large": {"HibernationSupported": True},
                "g4dn.xlarge": {"HibernationSupported": False},
            }

        mock_add_to_cache.side_effect = populate_cache
        mock_get_setting.return_value = []  # No denied types

        # Test
        result = ec2_utils.get_valid_instance_types_by_allowed_list(
            hibernation_support=True,
            allowed_instance_types=["t3", "g4dn"],  # Allow t3 family and g4dn family
        )

        # Assertions
        assert "t3.small" in result
        assert "t3.large" in result
        assert "t3.micro" not in result  # No hibernation support
        assert "g4dn.xlarge" not in result  # No hibernation support

    @patch("res.resources.cluster_settings.get_setting")
    @patch.object(ec2_utils, "add_instance_data_to_cache")
    def test_get_valid_instance_types_by_allowed_list_with_denied(
        self, mock_add_to_cache, mock_get_setting
    ):
        """Test get_valid_instance_types_by_allowed_list respects denied list."""

        # Setup
        def populate_cache(cache_dict):
            cache_dict["aws.ec2.all-instance-types-names-list"] = [
                "t3.micro",
                "t3.small",
                "t3.large",
            ]
            cache_dict["aws.ec2.all-instance-types-data"] = {
                "t3.micro": {"HibernationSupported": False},
                "t3.small": {"HibernationSupported": False},
                "t3.large": {"HibernationSupported": False},
            }

        mock_add_to_cache.side_effect = populate_cache
        mock_get_setting.return_value = ["t3.small"]  # Deny t3.small

        # Test
        result = ec2_utils.get_valid_instance_types_by_allowed_list(
            hibernation_support=False, allowed_instance_types=["t3"]
        )

        # Assertions
        assert "t3.micro" in result
        assert "t3.large" in result
        assert "t3.small" not in result  # Denied
