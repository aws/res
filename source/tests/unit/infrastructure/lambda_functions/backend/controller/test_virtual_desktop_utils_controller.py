#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import sys
from unittest.mock import patch

import pytest

# Add the backend directory to Python path to match controller's import context
backend_path = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "../../../../../../idea/infrastructure/resources/lambda_functions/backend",
    )
)
sys.path.insert(0, backend_path)

from api.controllers import virtual_desktop_utils_controller
from api.exceptions import BadRequestException
from api.models.list_allowed_instance_types_request_content import ListAllowedInstanceTypesRequestContent
from api.models.list_allowed_instance_types_response_content import ListAllowedInstanceTypesResponseContent
from api.models.list_allowed_instance_types_for_session_request_content import ListAllowedInstanceTypesForSessionRequestContent
from api.models.list_allowed_instance_types_for_session_response_content import ListAllowedInstanceTypesForSessionResponseContent
from api.models.res_memory import ResMemory
from api.models.list_schedule_types_response_content import ListScheduleTypesResponseContent
from api.models.list_supported_gpus_response_content import ListSupportedGpusResponseContent
from api.models.list_supported_oses_response_content import ListSupportedOsesResponseContent
from api.models.virtual_desktop_architecture import VirtualDesktopArchitecture
from api.models.get_permission_profile_response_content import GetPermissionProfileResponseContent
from api.models.list_permission_profiles_response_content import ListPermissionProfilesResponseContent
from api.models.bad_request_exception_response_content import BadRequestExceptionResponseContent
from api.models.internal_service_exception_response_content import InternalServiceExceptionResponseContent
from api.models.virtual_desktop_base_os import VirtualDesktopBaseOs
from api.models.virtual_desktop_gpu import VirtualDesktopGpu
from api.models.virtual_desktop_schedule_type import VirtualDesktopScheduleType
from api.models.virtual_desktop_session import VirtualDesktopSession
from api.models.virtual_desktop_software_stack import VirtualDesktopSoftwareStack
from connexion.exceptions import OAuthProblem


class TestVirtualDesktopUtilsController:
    """Test class for virtual_desktop_utils_controller module."""

    @patch("res.resources.accounts.is_active_admin")
    def test_list_supported_oses_returns_correct_response_type(self, mock_is_active_admin):
        """Test that list_supported_oses returns ListSupportedOsesResponseContent instance."""
        # Setup mocks
        mock_is_active_admin.return_value = True

        # Test
        result = virtual_desktop_utils_controller.list_supported_oses()

        # Assertions
        assert isinstance(result, ListSupportedOsesResponseContent)
        assert hasattr(result, "listing")

    @patch("res.resources.accounts.is_active_admin")
    def test_list_supported_oses_returns_all_enum_values(self, mock_is_active_admin):
        """Test that list_supported_oses returns all VirtualDesktopBaseOs enum values."""
        # Setup mocks
        mock_is_active_admin.return_value = True

        # Test
        result = virtual_desktop_utils_controller.list_supported_oses()

        expected_values = [os.value for os in VirtualDesktopBaseOs]
        assert result.listing == expected_values

    @patch("res.resources.accounts.is_active_admin")
    def test_list_schedule_types_returns_correct_response_type(self, mock_is_active_admin):
        """Test that list_schedule_types returns ListScheduleTypesResponseContent instance."""
        # Setup mocks
        mock_is_active_admin.return_value = True

        # Test
        result = virtual_desktop_utils_controller.list_schedule_types()

        # The function returns a ListScheduleTypesResponseContent instance
        assert isinstance(result, ListScheduleTypesResponseContent)
        assert hasattr(result, "listing")

    @patch("res.resources.accounts.is_active_admin")
    def test_list_schedule_types_returns_all_enum_values(self, mock_is_active_admin):
        """Test that list_schedule_types returns all VirtualDesktopScheduleType enum values."""
        # Setup mocks
        mock_is_active_admin.return_value = True

        # Test
        result = virtual_desktop_utils_controller.list_schedule_types()

        expected_values = [type_.value for type_ in VirtualDesktopScheduleType]
        assert result.listing == expected_values

    @patch("res.resources.accounts.is_active_admin")
    def test_list_supported_gpus_returns_correct_response_type(self, mock_is_active_admin):
        """Test that list_supported_gpus returns ListSupportedGpusResponseContent instance."""
        # Setup mocks
        mock_is_active_admin.return_value = True

        # Test
        result = virtual_desktop_utils_controller.list_supported_gpus()

        # The function returns a ListSupportedGpusResponseContent instance
        assert isinstance(result, ListSupportedGpusResponseContent)
        assert hasattr(result, "listing")

    @patch("res.resources.accounts.is_active_admin")
    def test_list_supported_gpus_returns_all_enum_values(self, mock_is_active_admin):
        """Test that list_supported_gpus returns all VirtualDesktopGpu enum values."""
        # Setup mocks
        mock_is_active_admin.return_value = True

        # Test
        result = virtual_desktop_utils_controller.list_supported_gpus()

        expected_values = [gpu.value for gpu in VirtualDesktopGpu]
        assert result.listing == expected_values

    # Tests for unauthorized access (is_active_admin returns False)
    @patch("res.resources.accounts.is_active_admin")
    def test_list_supported_oses_raises_oauth_problem_when_not_admin(
        self, mock_is_active_admin
    ):
        """Test that list_supported_oses raises OAuthProblem when user is not an active admin."""
        # Setup mocks
        mock_is_active_admin.return_value = False

        # Test and Assert
        with pytest.raises(OAuthProblem) as exc_info:
            virtual_desktop_utils_controller.list_supported_oses()

        assert str(exc_info.value) == "401: Unauthorized user"

    @patch("res.resources.accounts.is_active_admin")
    def test_list_schedule_types_raises_oauth_problem_when_not_admin(
        self, mock_is_active_admin
    ):
        """Test that list_schedule_types raises OAuthProblem when user is not an active admin."""
        # Setup mocks
        mock_is_active_admin.return_value = False

        # Test and Assert
        with pytest.raises(OAuthProblem) as exc_info:
            virtual_desktop_utils_controller.list_schedule_types()

        assert str(exc_info.value) == "401: Unauthorized user"

    @patch("res.resources.accounts.is_active_admin")
    def test_list_supported_gpus_raises_oauth_problem_when_not_admin(
        self, mock_is_active_admin
    ):
        """Test that list_supported_gpus raises OAuthProblem when user is not an active admin."""
        # Setup mocks
        mock_is_active_admin.return_value = False

        # Test and Assert
        with pytest.raises(OAuthProblem) as exc_info:
            virtual_desktop_utils_controller.list_supported_gpus()

        assert str(exc_info.value) == "401: Unauthorized user"

 # Tests for list_allowed_instance_types method
    @patch("api.controllers.virtual_desktop_utils_controller.virtual_desktop_controller_utils")
    def test_list_allowed_instance_types_no_software_stack(self, mock_utils):
        """Test list_allowed_instance_types with no software stack."""
        # Setup mocks
        mock_instance_types = [{"InstanceType": "t3.micro"}, {"InstanceType": "t3.small"}]
        mock_utils.get_valid_instance_types_by_software_stack.return_value = mock_instance_types

        # Create request body
        body = {"hibernation_support": True}

        # Test
        result = virtual_desktop_utils_controller.list_allowed_instance_types(body=body)

        # Assertions
        assert isinstance(result, ListAllowedInstanceTypesResponseContent)
        assert result.listing == mock_instance_types
        mock_utils.get_valid_instance_types_by_software_stack.assert_called_once_with(True)

    @patch("api.controllers.virtual_desktop_utils_controller.virtual_desktop_controller_utils")
    def test_list_allowed_instance_types_with_software_stack_success(self, mock_utils):
        """Test list_allowed_instance_types with valid software stack."""
        # Setup mocks
        mock_instance_types = [{"InstanceType": "t3.large"}, {"InstanceType": "m5.xlarge"}]
        mock_utils.get_valid_instance_types_by_software_stack.return_value = mock_instance_types

        # Create request body
        body = {
            "hibernation_support": False,
            "software_stack": {
                "ami_id": "ami-12345678",
                "architecture": "x86_64"
            }
        }

        # Test
        result = virtual_desktop_utils_controller.list_allowed_instance_types(body=body)

        # Assertions
        assert isinstance(result, ListAllowedInstanceTypesResponseContent)
        assert result.listing == mock_instance_types
        mock_utils.set_software_stack_architecture.assert_called_once()
        mock_utils.get_valid_instance_types_by_software_stack.assert_called_once()

    # Tests for list_allowed_instance_types_for_session method
    @patch("api.controllers.virtual_desktop_utils_controller.virtual_desktop_controller_utils")
    def test_list_allowed_instance_types_for_session_success(self, mock_utils):
        """Test list_allowed_instance_types_for_session with valid session."""
        # Setup mocks
        mock_instance_types_dict = {
            "t3.micro": {"InstanceType": "t3.micro", "MemoryInfo": {"SizeInMiB": 1024}},
            "t3.small": {"InstanceType": "t3.small", "MemoryInfo": {"SizeInMiB": 2048}}
        }
        mock_utils.get_valid_instance_types_by_allowed_list.return_value = mock_instance_types_dict

        # Mock validate_min_ram to return True for both instances
        mock_utils.validate_min_ram.side_effect = [True, True]

        # Create request body
        body = {
            "session": {
                "hibernation_enabled": True,
                "software_stack": {
                    "allowed_instance_types": ["t3.micro", "t3.small"],
                    "min_ram": {"value": 2.0, "unit": "GiB"}
                }
            }
        }

        # Test
        result = virtual_desktop_utils_controller.list_allowed_instance_types_for_session(body=body)

        # Assertions
        assert isinstance(result, ListAllowedInstanceTypesForSessionResponseContent)
        assert len(result.listing) == 2
        mock_utils.set_software_stack_architecture.assert_called_once()
        mock_utils.get_valid_instance_types_by_allowed_list.assert_called_once_with(
            True, ["t3.micro", "t3.small"]
        )

    @patch("api.controllers.virtual_desktop_utils_controller.virtual_desktop_controller_utils")
    def test_list_allowed_instance_types_for_session_ram_filtering(self, mock_utils):
        """Test list_allowed_instance_types_for_session filters instances based on RAM requirements."""
        # Setup mocks
        mock_instance_types_dict = {
            "t3.nano": {"InstanceType": "t3.nano", "MemoryInfo": {"SizeInMiB": 512}},     # Too small
            "t3.small": {"InstanceType": "t3.small", "MemoryInfo": {"SizeInMiB": 2048}}, # Too small
            "t3.large": {"InstanceType": "t3.large", "MemoryInfo": {"SizeInMiB": 8192}}  # OK
        }
        mock_utils.get_valid_instance_types_by_allowed_list.return_value = mock_instance_types_dict

        # Mock validate_min_ram to return False for small instances, True for large
        mock_utils.validate_min_ram.side_effect = [False, False, True]

        # Create request body
        body = {
            "session": {
                "hibernation_enabled": False,
                "software_stack": {
                    "allowed_instance_types": ["t3.nano", "t3.small", "t3.large"],
                    "min_ram": {"value": 4.0, "unit": "GiB"}
                }
            }
        }

        # Test
        result = virtual_desktop_utils_controller.list_allowed_instance_types_for_session(body=body)

        # Assertions
        assert isinstance(result, ListAllowedInstanceTypesForSessionResponseContent)
        assert len(result.listing) == 1  # Only t3.large should pass RAM validation
        assert result.listing[0]["InstanceType"] == "t3.large"
        mock_utils.set_software_stack_architecture.assert_called_once()

    @patch("api.controllers.virtual_desktop_utils_controller.virtual_desktop_controller_utils")
    def test_list_allowed_instance_types_hibernation_support_propagated(self, mock_utils):
        """Test that hibernation_support is properly propagated to utility functions."""
        # Setup mocks
        mock_utils.get_valid_instance_types_by_software_stack.return_value = []

        # Test with hibernation enabled
        body_hibernation_true = {"hibernation_support": True}
        virtual_desktop_utils_controller.list_allowed_instance_types(body=body_hibernation_true)
        mock_utils.get_valid_instance_types_by_software_stack.assert_called_with(True)

        # Reset mock
        mock_utils.reset_mock()

        # Test with hibernation disabled
        body_hibernation_false = {"hibernation_support": False}
        virtual_desktop_utils_controller.list_allowed_instance_types(body=body_hibernation_false)
        mock_utils.get_valid_instance_types_by_software_stack.assert_called_with(False)
    @patch('api.controllers.virtual_desktop_utils_controller.accounts.is_active_admin')
    @patch('api.controllers.virtual_desktop_utils_controller.permission_profiles')
    def test_get_permission_profile_returns_correct_response_type(self, mock_permission_profiles, mock_is_active_admin):
        """Test that get_permission_profile returns GetPermissionProfileResponseContent instance."""
        mock_is_active_admin.return_value = True
        mock_profile = {
            'profile_id': 'test-profile',
            'title': 'Test Profile',
            'description': 'Test Description',
            'permissions': [],
            'created_on': 1234567890,
            'updated_on': 1234567890
        }
        mock_permission_profiles.get_permission_profile.return_value = mock_profile

        result = virtual_desktop_utils_controller.get_permission_profile('test-profile')

        assert isinstance(result, GetPermissionProfileResponseContent)
        assert hasattr(result, 'profile')
        assert result.profile.profile_id == 'test-profile'
        assert result.profile.title == 'Test Profile'
        # Timestamps should be converted to ISO format strings
        assert isinstance(result.profile.created_on, str)
        assert isinstance(result.profile.updated_on, str)

    @patch('api.controllers.virtual_desktop_utils_controller.accounts.is_active_admin')
    @patch('api.controllers.virtual_desktop_utils_controller.permission_profiles')
    def test_get_permission_profile_calls_with_correct_profile_id(self, mock_permission_profiles, mock_is_active_admin):
        """Test that get_permission_profile calls the library function with correct profile_id."""
        mock_is_active_admin.return_value = True
        mock_profile = {'profile_id': 'test-profile'}
        mock_permission_profiles.get_permission_profile.return_value = mock_profile

        virtual_desktop_utils_controller.get_permission_profile('test-profile')

        mock_permission_profiles.get_permission_profile.assert_called_once_with('test-profile')

    @patch('api.controllers.virtual_desktop_utils_controller.accounts.is_active_admin')
    @patch('api.controllers.virtual_desktop_utils_controller.permission_profiles')
    @patch('api.controllers.virtual_desktop_utils_controller.exceptions')
    def test_get_permission_profile_returns_404_when_not_found(self, mock_exceptions, mock_permission_profiles, mock_is_active_admin):
        """Test that get_permission_profile returns 404 when profile not found."""
        mock_is_active_admin.return_value = True
        mock_exceptions.PermissionProfileNotFound = Exception
        mock_permission_profiles.get_permission_profile.side_effect = Exception('Profile not found')

        result, status_code = virtual_desktop_utils_controller.get_permission_profile('nonexistent-profile')

        assert isinstance(result, BadRequestExceptionResponseContent)
        assert status_code == 400

    @patch('api.controllers.virtual_desktop_utils_controller.accounts.is_active_admin')
    @patch('api.controllers.virtual_desktop_utils_controller.table_utils')
    def test_list_permission_profiles_returns_correct_response_type(self, mock_table_utils, mock_is_active_admin):
        """Test that list_permission_profiles returns ListPermissionProfilesResponseContent instance."""
        mock_is_active_admin.return_value = True
        mock_table_utils.list_items.return_value = [
            {'profile_id': 'profile1', 'title': 'Profile 1'},
            {'profile_id': 'profile2', 'title': 'Profile 2'}
        ]

        result = virtual_desktop_utils_controller.list_permission_profiles()

        assert isinstance(result, ListPermissionProfilesResponseContent)
        assert hasattr(result, 'listing')

    @patch('api.controllers.virtual_desktop_utils_controller.accounts.is_active_admin')
    @patch('api.controllers.virtual_desktop_utils_controller.table_utils')
    def test_list_permission_profiles_returns_all_profiles(self, mock_table_utils, mock_is_active_admin):
        """Test that list_permission_profiles returns all profiles from DynamoDB."""
        mock_is_active_admin.return_value = True
        mock_profiles = [
            {'profile_id': 'profile1', 'title': 'Profile 1'},
            {'profile_id': 'profile2', 'title': 'Profile 2'}
        ]
        mock_table_utils.list_items.return_value = mock_profiles

        result = virtual_desktop_utils_controller.list_permission_profiles()

        assert len(result.listing) == 2
        assert result.listing[0].profile_id == 'profile1'
        assert result.listing[1].profile_id == 'profile2'

    @patch('api.controllers.virtual_desktop_utils_controller.accounts.is_active_admin')
    @patch('api.controllers.virtual_desktop_utils_controller.table_utils')
    def test_list_permission_profiles_handles_pagination(self, mock_table_utils, mock_is_active_admin):
        """Test that list_permission_profiles returns all items (pagination not yet implemented)."""
        mock_is_active_admin.return_value = True
        mock_table_utils.list_items.return_value = [{'profile_id': 'profile1'}]

        result = virtual_desktop_utils_controller.list_permission_profiles()

        # Pagination not yet implemented, so next_token should be None
        assert hasattr(result, 'next_token')
        assert result.next_token is None

    @patch("api.controllers.virtual_desktop_utils_controller.accounts.is_active_admin")
    def test_get_permission_profile_raises_oauth_problem_when_not_admin(self, mock_is_active_admin):
        """Test that get_permission_profile raises OAuthProblem when user is not an active admin."""
        # Setup mocks
        mock_is_active_admin.return_value = False

        # Test and Assert
        with pytest.raises(OAuthProblem) as exc_info:
            virtual_desktop_utils_controller.get_permission_profile('test-profile')

        assert str(exc_info.value) == "401: Unauthorized user"

    @patch("api.controllers.virtual_desktop_utils_controller.accounts.is_active_admin")
    def test_list_permission_profiles_raises_oauth_problem_when_not_admin(self, mock_is_active_admin):
        """Test that list_permission_profiles raises OAuthProblem when user is not an active admin."""
        # Setup mocks
        mock_is_active_admin.return_value = False

        # Test and Assert
        with pytest.raises(OAuthProblem) as exc_info:
            virtual_desktop_utils_controller.list_permission_profiles()

        assert str(exc_info.value) == "401: Unauthorized user"

