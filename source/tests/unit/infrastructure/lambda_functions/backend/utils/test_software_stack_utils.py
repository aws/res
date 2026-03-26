#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add the backend directory to Python path to match utils import context
backend_path = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "../../../../../idea/backend",
    )
)
sys.path.insert(0, backend_path)

from api.exceptions import BadRequestException
from api.utils import software_stack_utils
from datamodel.models.project import Project
from datamodel.models.virtual_desktop_affinity import VirtualDesktopAffinity
from datamodel.models.virtual_desktop_architecture import VirtualDesktopArchitecture
from datamodel.models.virtual_desktop_placement import VirtualDesktopPlacement
from datamodel.models.virtual_desktop_software_stack import VirtualDesktopSoftwareStack
from datamodel.models.virtual_desktop_tenancy import VirtualDesktopTenancy


class TestSoftwareStackUtils:
    """Test class for software_stack_utils module."""

    # Tests for set_software_stack_architecture
    @patch('res.utils.ec2_utils.describe_image_id')
    def test_set_software_stack_architecture_success_with_auto_detect(self, mock_describe_image_id):
        """Test set_software_stack_architecture auto-detects architecture when not provided."""
        # Setup
        software_stack = VirtualDesktopSoftwareStack(
            ami_id="ami-12345678",
            architecture=None  # No architecture provided
        )
        mock_describe_image_id.return_value = {"Architecture": "x86_64"}

        # Test
        software_stack_utils.set_software_stack_architecture(software_stack)

        # Assertions
        assert software_stack.architecture == VirtualDesktopArchitecture.X86_64
        mock_describe_image_id.assert_called_once_with("ami-12345678")

    @patch('res.utils.ec2_utils.describe_image_id')
    def test_set_software_stack_architecture_success_with_matching_architecture(self, mock_describe_image_id):
        """Test set_software_stack_architecture succeeds when provided architecture matches AMI."""
        # Setup
        software_stack = VirtualDesktopSoftwareStack(
            ami_id="ami-87654321",
            architecture=VirtualDesktopArchitecture.ARM64
        )
        mock_describe_image_id.return_value = {"Architecture": "arm64"}

        # Test
        software_stack_utils.set_software_stack_architecture(software_stack)

        # Assertions - architecture should remain unchanged
        assert software_stack.architecture == VirtualDesktopArchitecture.ARM64
        mock_describe_image_id.assert_called_once_with("ami-87654321")

    @patch('res.utils.ec2_utils.describe_image_id')
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
            software_stack_utils.set_software_stack_architecture(software_stack)

        assert "Invalid software_stack.ami_id: ami-invalid" in str(exc_info.value)

    @patch('res.utils.ec2_utils.describe_image_id')
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
            software_stack_utils.set_software_stack_architecture(software_stack)

        assert "Invalid software_stack.ami_id: ami-12345678 with architecture: x86_64" in str(exc_info.value)

    # Tests for validate_placement
    def test_validate_placement_default_tenancy(self):
        """Test validate_placement sets default placement when none provided."""
        # Setup
        software_stack = VirtualDesktopSoftwareStack()

        # Test
        result = software_stack_utils.validate_placement(software_stack)

        # Assertions
        assert result is True
        assert software_stack.placement is not None
        assert software_stack.placement.tenancy == VirtualDesktopTenancy.DEFAULT

    def test_validate_placement_host_with_host_id(self):
        """Test validate_placement succeeds with host tenancy and host_id."""
        # Setup
        software_stack = VirtualDesktopSoftwareStack(
            placement=VirtualDesktopPlacement(
                tenancy=VirtualDesktopTenancy.HOST,
                host_id="h-12345678"
            )
        )

        # Test
        result = software_stack_utils.validate_placement(software_stack)

        # Assertions
        assert result is True
        assert software_stack.placement.affinity == VirtualDesktopAffinity.DEFAULT

    def test_validate_placement_host_with_resource_group(self):
        """Test validate_placement succeeds with host tenancy and resource group."""
        # Setup
        software_stack = VirtualDesktopSoftwareStack(
            placement=VirtualDesktopPlacement(
                tenancy=VirtualDesktopTenancy.HOST,
                host_resource_group_arn="arn:aws:resource-groups:us-east-1:123456789012:group/my-group"
            )
        )

        # Test
        result = software_stack_utils.validate_placement(software_stack)

        # Assertions
        assert result is True
        assert software_stack.placement.affinity == VirtualDesktopAffinity.DEFAULT

    def test_validate_placement_host_missing_both(self):
        """Test validate_placement fails when host tenancy has neither host_id nor resource group."""
        # Setup
        software_stack = VirtualDesktopSoftwareStack(
            placement=VirtualDesktopPlacement(
                tenancy=VirtualDesktopTenancy.HOST
            )
        )

        # Test
        result = software_stack_utils.validate_placement(software_stack)

        # Assertions
        assert result is False
        assert "Either software_stack.placement.host_id or placement.host_resource_group_arn is required" in software_stack.failure_reason

    def test_validate_placement_host_has_both(self):
        """Test validate_placement fails when host tenancy has both host_id and resource group."""
        # Setup
        software_stack = VirtualDesktopSoftwareStack(
            placement=VirtualDesktopPlacement(
                tenancy=VirtualDesktopTenancy.HOST,
                host_id="h-12345678",
                host_resource_group_arn="arn:aws:resource-groups:us-east-1:123456789012:group/my-group"
            )
        )

        # Test
        result = software_stack_utils.validate_placement(software_stack)

        # Assertions
        assert result is False
        assert "Both software_stack.placement.host_id and placement.host_resource_group_arn are provided" in software_stack.failure_reason

    # Tests for validate_software_stack_fields
    @patch('res.resources.software_stacks.get_software_stack_by_name')
    @patch.object(software_stack_utils, 'set_software_stack_architecture')
    @patch.object(software_stack_utils, 'validate_placement')
    @patch('res.utils.table_utils.get_item')
    def test_validate_software_stack_fields_success(self, mock_get_item, mock_validate_placement, mock_set_arch, mock_get_by_name):
        """Test validate_software_stack_fields returns True for valid stack."""
        
        stack_name="test-stack"
        # Setup
        software_stack = VirtualDesktopSoftwareStack(
            name=stack_name,
            projects=[Project(project_id="proj-123")]
        )
        mock_get_by_name.return_value = None  # No existing stack
        mock_validate_placement.return_value = True
        mock_get_item.return_value = {"project_id": "proj-123"}  # Project exists
        
        result_stack, is_valid = software_stack_utils.validate_software_stack_fields(software_stack)
        
        assert is_valid is True
        assert result_stack == software_stack
        mock_get_by_name.assert_called_once_with(stack_name)
        mock_set_arch.assert_called_once_with(software_stack)
        mock_validate_placement.assert_called_once_with(software_stack)


    @patch('res.resources.software_stacks.get_software_stack_by_name')
    def test_validate_software_stack_fields_duplicate_name_no_stack_id(self, mock_get_stack):
        """Test validate_software_stack_fields fails when name exists and no stack_id provided."""
        # Setup mocks
        mock_get_stack.return_value = {"stack_id": "ss-existing", "name": "Test Stack"}

        software_stack = VirtualDesktopSoftwareStack(
            name="Test Stack",
            ami_id="ami-12345678"
        )

        # Test
        result_stack, is_valid = software_stack_utils.validate_software_stack_fields(software_stack)

        # Assertions
        assert is_valid is False
        assert 'Software stack with name "Test Stack" already exists' in result_stack.failure_reason

    @patch('res.resources.software_stacks.get_software_stack_by_name')
    def test_validate_software_stack_fields_duplicate_name_different_stack_id(self, mock_get_stack):
        """Test validate_software_stack_fields fails when name exists with different stack_id."""
        # Setup mocks
        mock_get_stack.return_value = {"stack_id": "ss-existing", "name": "Test Stack"}

        software_stack = VirtualDesktopSoftwareStack(
            name="Test Stack",
            stack_id="ss-different",
            ami_id="ami-12345678"
        )

        # Test
        result_stack, is_valid = software_stack_utils.validate_software_stack_fields(software_stack)

        # Assertions
        assert is_valid is False
        assert 'Another Software stack with name "Test Stack" already exists' in result_stack.failure_reason

    @patch('res.resources.software_stacks.get_software_stack_by_name')
    @patch('res.resources.projects._get_project_by_id')
    @patch('res.utils.ec2_utils.describe_image_id')
    def test_validate_software_stack_fields_missing_project_id(self, mock_describe_image, mock_get_project, mock_get_stack):
        """Test validate_software_stack_fields fails when project_id is missing."""
        # Setup mocks
        mock_get_stack.return_value = None
        mock_describe_image.return_value = {"Architecture": "x86_64"}

        software_stack = VirtualDesktopSoftwareStack(
            name="Test Stack",
            ami_id="ami-12345678",
            projects=[Project()]  # No project_id
        )

        # Test
        result_stack, is_valid = software_stack_utils.validate_software_stack_fields(software_stack)

        # Assertions
        assert is_valid is False
        assert "software_stack.project.project_id missing" in result_stack.failure_reason

    @patch('res.resources.software_stacks.get_software_stack_by_name')
    @patch('res.resources.projects._get_project_by_id')
    @patch('res.utils.ec2_utils.describe_image_id')
    def test_validate_software_stack_fields_invalid_project_id(self, mock_describe_image, mock_get_project, mock_get_stack):
        """Test validate_software_stack_fields fails when project_id doesn't exist."""
        # Setup mocks
        mock_get_stack.return_value = None
        mock_describe_image.return_value = {"Architecture": "x86_64"}
        mock_get_project.return_value = None  # Project not found

        software_stack = VirtualDesktopSoftwareStack(
            name="Test Stack",
            ami_id="ami-12345678",
            projects=[Project(project_id="proj-invalid")]
        )

        # Test
        result_stack, is_valid = software_stack_utils.validate_software_stack_fields(software_stack)

        # Assertions
        assert is_valid is False
        assert "Invalid software_stack.project.project_id: proj-invalid" in result_stack.failure_reason
