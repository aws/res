#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch, Mock
import pytest

# Add the backend directory to Python path to match controller's import context
backend_path = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "../../../../../idea/backend",
    )
)
sys.path.insert(0, backend_path)

from connexion.exceptions import OAuthProblem
from api.controllers import virtual_desktop_controller
from api.exceptions import (
    BadRequestException,
    NotFoundException,
    InternalServiceException,
)
from datamodel.models.virtual_desktop_software_stack import VirtualDesktopSoftwareStack
from datamodel.models.virtual_desktop_permission_profile import (
    VirtualDesktopPermissionProfile,
)
from datamodel.models.virtual_desktop_session_permission import (
    VirtualDesktopSessionPermission,
)
from datamodel.models.create_software_stack_response_content import (
    CreateSoftwareStackResponseContent,
)
from datamodel.models.create_permission_profile_response_content import (
    CreatePermissionProfileResponseContent,
)
from datamodel.models.delete_software_stack_response_content import (
    DeleteSoftwareStackResponseContent,
)
from datamodel.models.delete_permission_profile_response_content import (
    DeletePermissionProfileResponseContent,
)
from datamodel.models.list_software_stacks_response_content import (
    ListSoftwareStacksResponseContent,
)
from datamodel.models.get_software_stack_response_content import (
    GetSoftwareStackResponseContent,
)
from datamodel.models.list_sessions_response_content import ListSessionsResponseContent
from datamodel.models.update_permission_profile_response_content import (
    UpdatePermissionProfileResponseContent,
)
from datamodel.models.update_software_stack_response_content import (
    UpdateSoftwareStackResponseContent,
)
from datamodel.models.update_session_permissions_response_content import (
    UpdateSessionPermissionsResponseContent,
)
from datamodel.models.list_shared_permissions_response_content import (
    ListSharedPermissionsResponseContent,
)
from res.exceptions import (
    SoftwareStackNotFound,
    PermissionProfileNotFound,
    SessionPermissionsNotFound,
    UserSessionNotFound,
)
from res.resources import session_permissions


class TestVirtualDesktopController:
    """VirtualDesktopController unit test stubs"""

    def _get_base_body(self, **overrides):
        """Helper method to create base request body with optional overrides."""
        base = {
            "software_stack": {
                "name": "Test Stack",
                "description": "Test Description",
                "ami_id": "ami-12345678",
                "base_os": "amazonlinux2",
                "gpu": "NO_GPU",
                "min_ram": {"value": 4, "unit": "GB"},
                "min_storage": {"value": 20, "unit": "GB"},
            }
        }
        if overrides:
            base["software_stack"].update(overrides)
        return base

    def _get_permission_profile_body(self, **overrides):
        """Helper method to create base permission profile request body with optional overrides."""
        base = {
            "profile": {
                "profile_id": "test-profile-123",
                "title": "Test Permission Profile",
                "description": "Test permission profile for integration testing",
                "permissions": [
                    {"key": "audio_in", "name": "audio_in", "enabled": True}
                ],
            }
        }
        if overrides:
            base["profile"].update(overrides)
        return base

    def _get_update_session_permissions_body(self, **overrides):
        """Helper method to create base update session permissions request body with optional overrides."""
        base = {
            "create": [
                {
                    "idea_session_id": "session-123",
                    "actor_name": "user1",
                    "idea_session_owner": "user1",
                    "actor_type": "USER",
                    "permission_profile": {"profile_id": "profile-123"},
                }
            ],
            "update": [],
            "delete": [],
        }
        if overrides:
            base.update(overrides)
        return base

    @patch(
        "api.controllers.virtual_desktop_controller.CreateSoftwareStackRequestContent.from_dict"
    )
    @patch("api.controllers.virtual_desktop_controller.validate_software_stack_fields")
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    @patch(
        "api.controllers.virtual_desktop_controller.software_stacks.create_software_stack"
    )
    @patch(
        "api.controllers.virtual_desktop_controller.VirtualDesktopSoftwareStack.from_ddb_dict"
    )
    def test_create_software_stack_admin_returns_correct_response_type(
        self,
        mock_from_ddb_dict,
        mock_create_software_stack,
        mock_is_active_admin,
        mock_validate,
        mock_from_dict,
    ):
        """Test that create_software_stack returns CreateSoftwareStackResponseContent instance for admin."""
        # Create a mock software stack object and mock request
        mock_software_stack_object = Mock()
        mock_software_stack_object.to_ddb_dict.return_value = {
            "name": "Test Stack",
            "ami_id": "ami-12345678",
        }

        mock_request = Mock()
        mock_request.software_stack = mock_software_stack_object
        mock_from_dict.return_value = mock_request

        body = self._get_base_body()

        mock_is_active_admin.return_value = True
        mock_validate.return_value = (mock_software_stack_object, True)
        mock_create_software_stack.return_value = {
            "stack_id": "test-stack-123",
            "name": "Test Stack",
        }
        mock_from_ddb_dict.return_value = VirtualDesktopSoftwareStack(
            name="Test Stack", stack_id="test-stack-123"
        )

        result = virtual_desktop_controller.create_software_stack(
            body, user={"username": "clusteradmin"}
        )
        assert isinstance(result, CreateSoftwareStackResponseContent)
        assert hasattr(result, "software_stack")
        mock_software_stack_object.to_ddb_dict.assert_called_once()
        mock_validate.assert_called_once()
        mock_create_software_stack.assert_called_once()
        mock_from_ddb_dict.assert_called_once()

    @patch("api.controllers.virtual_desktop_controller.validate_software_stack_fields")
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_create_software_stack_non_admin_raises_oauth_problem(
        self, mock_is_active_admin, mock_validate
    ):
        """Test that create_software_stack raises OAuthProblem for non-admin users."""
        body = self._get_base_body()

        mock_is_active_admin.return_value = False

        with pytest.raises(OAuthProblem) as exc_info:
            virtual_desktop_controller.create_software_stack(
                body, user={"username": "user1"}
            )

        assert "Unauthorized user" in str(exc_info.value)
        mock_is_active_admin.assert_called_once()
        mock_validate.assert_not_called()

    @patch(
        "api.controllers.virtual_desktop_controller.CreateSoftwareStackRequestContent.from_dict"
    )
    @patch("api.controllers.virtual_desktop_controller.validate_software_stack_fields")
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_create_software_stack_invalid_fields_raises_bad_request(
        self, mock_is_active_admin, mock_validate, mock_from_dict
    ):

        body = self._get_base_body(ami_id="invalid-ami", base_os="test-os")

        mock_is_active_admin.return_value = True

        mock_request = Mock()
        mock_request.software_stack = Mock()
        mock_from_dict.return_value = mock_request

        mock_failed_stack = Mock()
        mock_failed_stack.failure_reason = "Invalid AMI ID"
        mock_validate.return_value = (mock_failed_stack, False)

        with pytest.raises(BadRequestException) as exc_info:
            virtual_desktop_controller.create_software_stack(
                body, user={"username": "clusteradmin"}
            )

        assert "Invalid software stack request: Invalid AMI ID" in str(exc_info.value)
        mock_is_active_admin.assert_called_once()
        mock_validate.assert_called_once()

    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_create_software_stack_invalid_base_os_raises_value_error(
        self, mock_is_active_admin
    ):
        """Test that create_software_stack raises ValueError for invalid base_os enum value."""
        body = self._get_base_body(base_os="invalid-os")
        mock_is_active_admin.return_value = True

        with pytest.raises(ValueError) as exc_info:
            virtual_desktop_controller.create_software_stack(
                body, user={"username": "clusteradmin"}
            )

        assert "'invalid-os' is not a valid VirtualDesktopBaseOs" in str(exc_info.value)

    @patch("api.controllers.virtual_desktop_controller.validate_software_stack_fields")
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_create_software_stack_project_without_id_raises_bad_request(
        self, mock_is_active_admin, mock_validate
    ):

        body = self._get_base_body(
            projects=[{"name": "test-project"}]
        )  # Missing project_id

        mock_is_active_admin.return_value = True

        mock_failed_stack = Mock()
        mock_failed_stack.failure_reason = "Project missing required field: project_id"
        mock_validate.return_value = (mock_failed_stack, False)

        with pytest.raises(BadRequestException) as exc_info:
            virtual_desktop_controller.create_software_stack(
                body, user={"username": "clusteradmin"}
            )

        assert "Project missing required field: project_id" in str(exc_info.value)
        mock_is_active_admin.assert_called_once()
        mock_validate.assert_called_once()

    @patch("api.controllers.virtual_desktop_controller.validate_software_stack_fields")
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_create_software_stack_missing_required_fields_raises_bad_request(
        self, mock_is_active_admin, mock_validate
    ):
        """Test that create_software_stack raises BadRequestException for missing required fields."""

        body = self._get_base_body()
        # Remove required fields to test validation
        del body["software_stack"]["ami_id"]
        del body["software_stack"]["base_os"]

        mock_is_active_admin.return_value = True

        mock_failed_stack = Mock()
        mock_failed_stack.failure_reason = "Missing required field: ami_id"
        mock_validate.return_value = (mock_failed_stack, False)

        with pytest.raises(BadRequestException) as exc_info:
            virtual_desktop_controller.create_software_stack(
                body, user={"username": "clusteradmin"}
            )

        assert "Missing required field: ami_id" in str(exc_info.value)
        mock_is_active_admin.assert_called_once()
        mock_validate.assert_called_once()

    # Delete Software Stack Tests
    @patch(
        "api.controllers.virtual_desktop_controller.software_stacks.delete_software_stack"
    )
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_delete_software_stack_success(self, mock_is_active_admin, mock_delete):
        """Test successful deletion of software stack."""
        mock_is_active_admin.return_value = True
        mock_delete.return_value = None

        body = {"base_os": "amazonlinux2"}
        stack_id = "test-stack-123"

        result = virtual_desktop_controller.delete_software_stack(
            stack_id, body, user={"username": "clusteradmin"}
        )

        assert isinstance(result, DeleteSoftwareStackResponseContent)
        assert result.success is True
        mock_delete.assert_called_once_with("amazonlinux2", "test-stack-123")

    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_delete_software_stack_non_admin_raises_oauth_problem(
        self, mock_is_active_admin
    ):
        """Test that delete_software_stack raises OAuthProblem for non-admin users."""
        mock_is_active_admin.return_value = False

        body = {"base_os": "amazonlinux2"}
        stack_id = "test-stack-123"

        with pytest.raises(OAuthProblem) as exc_info:
            virtual_desktop_controller.delete_software_stack(
                stack_id, body, user={"username": "user1"}
            )

        assert "Unauthorized user" in str(exc_info.value)

    @patch(
        "api.controllers.virtual_desktop_controller.software_stacks.delete_software_stack"
    )
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_delete_software_stack_not_found_raises_not_found_exception(
        self, mock_is_active_admin, mock_delete
    ):
        """Test that delete_software_stack raises NotFoundException when software stack is not found."""
        mock_is_active_admin.return_value = True
        mock_delete.side_effect = SoftwareStackNotFound("Software stack not found")

        body = {"base_os": "amazonlinux2"}
        stack_id = "nonexistent-stack"

        with pytest.raises(NotFoundException) as exc_info:
            virtual_desktop_controller.delete_software_stack(
                stack_id, body, user={"username": "clusteradmin"}
            )

        assert "Software stack not found" in str(exc_info.value)

    @patch(
        "api.controllers.virtual_desktop_controller.software_stacks.delete_software_stack"
    )
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_delete_software_stack_generic_exception_raises_internal_service_exception(
        self, mock_is_active_admin, mock_delete
    ):
        """Test that delete_software_stack raises InternalServiceException for generic exceptions."""
        mock_is_active_admin.return_value = True
        mock_delete.side_effect = Exception("Database connection failed")

        body = {"base_os": "amazonlinux2"}
        stack_id = "test-stack-123"

        with pytest.raises(InternalServiceException) as exc_info:
            virtual_desktop_controller.delete_software_stack(
                stack_id, body, user={"username": "clusteradmin"}
            )

        assert "Database connection failed" in str(exc_info.value)

    # List Shared Permissions Tests
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    @patch(
        "api.controllers.virtual_desktop_controller.res_session_permissions.list_session_permissions"
    )
    @patch(
        "api.controllers.virtual_desktop_controller.VirtualDesktopSessionPermission.from_ddb_dict"
    )
    def test_list_shared_permissions_admin_success(
        self,
        mock_from_ddb_dict,
        mock_list_permissions,
        mock_is_admin,
    ):
        """Test successful list_shared_permissions for admin user."""
        mock_is_admin.return_value = True
        mock_permissions = [
            {"idea_session_id": "session-123", "actor_name": "user1"},
            {"idea_session_id": "session-456", "actor_name": "user1"},
        ]
        mock_list_permissions.return_value = (mock_permissions, None)
        mock_from_ddb_dict.return_value = Mock()

        result = virtual_desktop_controller.list_shared_permissions(
            username="user1",
            state="READY",
            user="clusteradmin",
            token_info={"username": "clusteradmin"},
        )

        assert isinstance(result, ListSharedPermissionsResponseContent)
        assert len(result.listing) == 2
        assert result.next_token is None
        mock_list_permissions.assert_called_once()

    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    @patch(
        "api.controllers.virtual_desktop_controller.res_session_permissions.list_session_permissions"
    )
    @patch(
        "api.controllers.virtual_desktop_controller.VirtualDesktopSessionPermission.from_ddb_dict"
    )
    def test_list_shared_permissions_non_admin_own_username_success(
        self,
        mock_from_ddb_dict,
        mock_list_permissions,
        mock_is_admin,
    ):
        """Test successful list_shared_permissions for non-admin user accessing own permissions."""
        mock_is_admin.return_value = False
        mock_permissions = [{"idea_session_id": "session-123", "actor_name": "user1"}]
        mock_list_permissions.return_value = (mock_permissions, None)
        mock_from_ddb_dict.return_value = Mock()

        result = virtual_desktop_controller.list_shared_permissions(
            username="user1",
            user="user1",
            token_info={"username": "user1"},
        )

        assert isinstance(result, ListSharedPermissionsResponseContent)
        assert len(result.listing) == 1
        mock_list_permissions.assert_called_once()

    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_list_shared_permissions_non_admin_other_user_raises_oauth_problem(
        self, mock_is_admin
    ):
        """Test that non-admin user cannot list shared permissions of other users."""
        mock_is_admin.return_value = False

        with pytest.raises(OAuthProblem) as exc_info:
            virtual_desktop_controller.list_shared_permissions(
                username="other_user",
                user="user1",
                token_info={"username": "user1"},
            )

        assert "Non admin user cannot list shared permissions of other users" in str(
            exc_info.value
        )

    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    @patch(
        "api.controllers.virtual_desktop_controller.res_session_permissions.list_session_permissions"
    )
    @patch(
        "api.controllers.virtual_desktop_controller.VirtualDesktopSessionPermission.from_ddb_dict"
    )
    def test_list_shared_permissions_no_username_defaults_to_current_user(
        self,
        mock_from_ddb_dict,
        mock_list_permissions,
        mock_is_admin,
    ):
        """Test list_shared_permissions without username parameter defaults to current user."""
        mock_is_admin.return_value = True
        mock_permissions = [{"idea_session_id": "session-123", "actor_name": "user1"}]
        mock_list_permissions.return_value = (mock_permissions, None)
        mock_from_ddb_dict.return_value = Mock()

        result = virtual_desktop_controller.list_shared_permissions(
            username=None,
            user="user1",
            token_info={"username": "user1"},
        )

        assert isinstance(result, ListSharedPermissionsResponseContent)
        assert len(result.listing) == 1
        call_args = mock_list_permissions.call_args
        assert call_args[1]["username"] == "user1"

    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    @patch(
        "api.controllers.virtual_desktop_controller.res_session_permissions.list_session_permissions"
    )
    @patch(
        "api.controllers.virtual_desktop_controller.VirtualDesktopSessionPermission.from_ddb_dict"
    )
    def test_list_shared_permissions_with_pagination(
        self,
        mock_from_ddb_dict,
        mock_list_permissions,
        mock_is_admin,
    ):
        """Test list_shared_permissions with pagination token."""
        mock_is_admin.return_value = True
        mock_permissions = [{"idea_session_id": "session-123", "actor_name": "user1"}]
        mock_list_permissions.return_value = (mock_permissions, "next_token_123")
        mock_from_ddb_dict.return_value = Mock()

        result = virtual_desktop_controller.list_shared_permissions(
            username="user1",
            next_token="current_token",
            user="user1",
            token_info={"username": "user1"},
        )

        assert isinstance(result, ListSharedPermissionsResponseContent)
        assert result.next_token == "next_token_123"
        mock_list_permissions.assert_called_once()

    # Update Permission Profile Tests
    @patch(
        "api.controllers.virtual_desktop_controller.UpdatePermissionProfileRequestContent.from_dict"
    )
    @patch(
        "api.controllers.virtual_desktop_controller.VirtualDesktopPermissionProfile.from_ddb_dict"
    )
    @patch(
        "api.controllers.virtual_desktop_controller.permission_profiles.get_permission_profile"
    )
    @patch(
        "api.controllers.virtual_desktop_controller.permission_profiles.update_permission_profile"
    )
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_update_permission_profile_success(
        self,
        mock_is_active_admin,
        mock_update_profile,
        mock_get_profile,
        mock_from_ddb_dict,
        mock_from_dict,
    ):
        """Test successful update of permission profile."""
        mock_is_active_admin.return_value = True
        existing_profile_dict = {
            "profile_id": "test-profile-123",
            "title": "Old Profile",
        }
        mock_get_profile.return_value = existing_profile_dict

        updated_profile_dict = {
            "profile_id": "test-profile-123",
            "title": "Updated Profile",
        }
        mock_update_profile.return_value = updated_profile_dict

        # Mock the profile object with to_ddb_dict method
        mock_profile_obj = Mock()
        mock_profile_obj.profile_id = "test-profile-123"
        mock_profile_obj.to_ddb_dict.return_value = updated_profile_dict

        # Mock the request object
        mock_request = Mock()
        mock_request.profile = mock_profile_obj
        mock_from_dict.return_value = mock_request

        mock_from_ddb_dict.return_value = VirtualDesktopPermissionProfile(
            profile_id="test-profile-123", title="Updated Profile"
        )

        body = self._get_permission_profile_body()
        body["profile"]["title"] = "Updated Profile"
        profile_id = "test-profile-123"

        result = virtual_desktop_controller.update_permission_profile(
            body, profile_id, user={"username": "clusteradmin"}
        )

        # Check that it returns the correct response type
        assert isinstance(result, UpdatePermissionProfileResponseContent)
        assert hasattr(result, "profile")
        mock_get_profile.assert_called_once_with(profile_id="test-profile-123")
        mock_profile_obj.to_ddb_dict.assert_called_once()
        mock_update_profile.assert_called_once()
        mock_from_ddb_dict.assert_called_once_with(updated_profile_dict)

    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_update_permission_profile_non_admin_raises_oauth_problem(
        self, mock_is_active_admin
    ):
        """Test that update_permission_profile raises OAuthProblem for non-admin users."""
        mock_is_active_admin.return_value = False

        body = self._get_permission_profile_body()
        profile_id = "test-profile-123"

        with pytest.raises(OAuthProblem) as exc_info:
            virtual_desktop_controller.update_permission_profile(
                body, profile_id, user={"username": "user1"}
            )

        assert "Unauthorized user" in str(exc_info.value)

    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_update_permission_profile_id_mismatch_raises_bad_request(
        self, mock_is_active_admin
    ):
        """Test that update_permission_profile raises BadRequestException when profile IDs don't match."""
        mock_is_active_admin.return_value = True

        body = self._get_permission_profile_body()
        body["profile"]["profile_id"] = "different-profile-456"
        profile_id = "test-profile-123"

        with pytest.raises(BadRequestException) as exc_info:
            virtual_desktop_controller.update_permission_profile(
                body, profile_id, user={"username": "clusteradmin"}
            )

        assert (
            "Profile ID: test-profile-123 does not match the permission profile to update: different-profile-456"
            in str(exc_info.value)
        )

    @patch(
        "api.controllers.virtual_desktop_controller.permission_profiles.get_permission_profile"
    )
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_update_permission_profile_not_found_raises_not_found_exception(
        self, mock_is_active_admin, mock_get_profile
    ):
        """Test that update_permission_profile raises NotFoundException when permission profile is not found."""
        mock_is_active_admin.return_value = True
        mock_get_profile.side_effect = PermissionProfileNotFound(
            "Permission profile not found"
        )

        body = self._get_permission_profile_body()
        body["profile"][
            "profile_id"
        ] = "nonexistent-profile"  # Match the profile_id parameter
        profile_id = "nonexistent-profile"

        with pytest.raises(NotFoundException) as exc_info:
            virtual_desktop_controller.update_permission_profile(
                body, profile_id, user={"username": "clusteradmin"}
            )

        assert "Profile ID: nonexistent-profile does not exist" in str(exc_info.value)

    # Permission Profile Tests
    @patch(
        "api.controllers.virtual_desktop_controller.VirtualDesktopPermissionProfile.from_ddb_dict"
    )
    @patch(
        "api.controllers.virtual_desktop_controller.permission_profiles.get_permission_profile"
    )
    @patch(
        "api.controllers.virtual_desktop_controller.permission_profiles.create_permission_profile"
    )
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    @patch(
        "api.controllers.virtual_desktop_controller.CreatePermissionProfileRequestContent.from_dict"
    )
    def test_create_permission_profile_admin_returns_correct_response_type(
        self,
        mock_from_dict,
        mock_is_active_admin,
        mock_create_profile,
        mock_get_profile,
        mock_from_ddb_dict,
    ):
        """Test that create_permission_profile returns CreatePermissionProfileResponseContent instance for admin."""
        body = self._get_permission_profile_body()

        mock_is_active_admin.return_value = True
        mock_get_profile.side_effect = PermissionProfileNotFound()

        profile_dict_to_create = {
            "profile_id": "test-profile-123",
            "title": "Test Permission Profile",
        }
        created_profile_dict = {
            "profile_id": "test-profile-123",
            "title": "Test Permission Profile",
        }
        mock_create_profile.return_value = created_profile_dict

        # Mock the profile object with to_ddb_dict method
        mock_profile_obj = Mock()
        mock_profile_obj.to_ddb_dict.return_value = profile_dict_to_create
        mock_from_ddb_dict.return_value = VirtualDesktopPermissionProfile(
            profile_id="test-profile-123", title="Test Permission Profile"
        )

        # Mock the request object
        mock_request = Mock()
        mock_request.profile = mock_profile_obj
        mock_from_dict.return_value = mock_request

        result = virtual_desktop_controller.create_permission_profile(
            body, user={"username": "clusteradmin"}
        )

        assert isinstance(result, CreatePermissionProfileResponseContent)
        assert hasattr(result, "profile")
        mock_profile_obj.to_ddb_dict.assert_called_once()
        mock_create_profile.assert_called_once_with(profile_dict_to_create)
        mock_from_ddb_dict.assert_called_once_with(created_profile_dict)

    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_create_permission_profile_non_admin_raises_oauth_problem(
        self, mock_is_active_admin
    ):
        """Test that create_permission_profile raises OAuthProblem for non-admin users."""
        body = self._get_permission_profile_body()

        mock_is_active_admin.return_value = False

        with pytest.raises(OAuthProblem) as exc_info:
            virtual_desktop_controller.create_permission_profile(
                body, user={"username": "user1"}
            )

        assert "Unauthorized user" in str(exc_info.value)
        mock_is_active_admin.assert_called_once()

    @patch(
        "api.controllers.virtual_desktop_controller.CreatePermissionProfileRequestContent.from_dict"
    )
    @patch(
        "api.controllers.virtual_desktop_controller.permission_profiles.get_permission_profile"
    )
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_create_permission_profile_duplicate_raises_bad_request(
        self, mock_is_active_admin, mock_get_profile, mock_from_dict
    ):
        """Test that create_permission_profile raises BadRequestException when profile already exists."""
        body = self._get_permission_profile_body()

        mock_is_active_admin.return_value = True
        mock_get_profile.return_value = {"profile_id": "test-profile-123"}

        # Mock the profile object with to_ddb_dict method
        mock_profile_obj = Mock()
        mock_profile_obj.profile_id = "test-profile-123"
        mock_profile_obj.to_ddb_dict.return_value = {"profile_id": "test-profile-123"}

        # Mock the request object
        mock_request = Mock()
        mock_request.profile = mock_profile_obj
        mock_from_dict.return_value = mock_request

        with pytest.raises(BadRequestException) as exc_info:
            virtual_desktop_controller.create_permission_profile(
                body, user={"username": "clusteradmin"}
            )

        assert "profile_id: test-profile-123 already exists." in str(exc_info.value)
        mock_is_active_admin.assert_called_once()
        mock_get_profile.assert_called_once()

    # List Software Stack Tests
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    @patch("api.controllers.virtual_desktop_controller.software_stacks")
    def test_list_software_stacks_admin_returns_correct_response_type(
        self, mock_software_stacks, mock_is_active_admin
    ):
        """Test that list_software_stacks returns ListSoftwareStacksResponseContent instance for admin."""
        mock_is_active_admin.return_value = True
        mock_software_stacks.list_software_stacks.return_value = (
            [
                {"stack_id": "stack1", "name": "Stack 1", "base_os": "amazonlinux2"},
                {"stack_id": "stack2", "name": "Stack 2", "base_os": "windows"},
            ],
            None,
        )

        result = virtual_desktop_controller.list_software_stacks()

        assert isinstance(result, ListSoftwareStacksResponseContent)
        assert hasattr(result, "listing")
        assert len(result.listing) == 2

    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    @patch("api.controllers.virtual_desktop_controller.software_stacks")
    def test_list_software_stacks_admin_with_filters(
        self, mock_software_stacks, mock_is_active_admin
    ):
        """Test that list_software_stacks applies filters correctly for admin."""
        mock_is_active_admin.return_value = True
        mock_software_stacks.list_software_stacks.return_value = (
            [
                {
                    "stack_id": "stack1",
                    "name": "Stack 1",
                    "base_os": "amazonlinux2",
                    "ami_id": "ami-123",
                    "gpu": "NO_GPU",
                    "projects": [],
                    "min_storage_value": 20,
                    "min_storage_unit": "GB",
                    "min_ram_value": 4,
                    "min_ram_unit": "GB",
                }
            ],
            None,
        )

        virtual_desktop_controller.list_software_stacks(
            base_os="amazonlinux2", software_stack_name="test"
        )

        mock_software_stacks.list_software_stacks.assert_called_once_with(
            project_id=None,
            base_os="amazonlinux2",
            name="test",
            next_token=None,
        )

    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    @patch("api.controllers.virtual_desktop_controller.software_stacks")
    def test_list_software_stacks_admin_no_filters(
        self, mock_software_stacks, mock_is_active_admin
    ):
        """Test that list_software_stacks works without filters for admin."""
        mock_is_active_admin.return_value = True
        mock_software_stacks.list_software_stacks.return_value = ([], None)

        virtual_desktop_controller.list_software_stacks()

        mock_software_stacks.list_software_stacks.assert_called_once_with(
            project_id=None,
            base_os=None,
            name=None,
            next_token=None,
        )

    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    @patch("api.controllers.virtual_desktop_controller.software_stacks")
    @patch("res.resources.projects.get_project")
    def test_list_software_stacks_admin_with_project_id(
        self, mock_get_project, mock_software_stacks, mock_is_active_admin
    ):
        """Test that admin can filter by project_id without enabled filter."""
        mock_is_active_admin.return_value = True
        mock_get_project.return_value = {
            "project_id": "project1",
            "name": "Project 1",
            "title": "Project 1",
        }
        mock_software_stacks.list_software_stacks.return_value = (
            [
                {
                    "stack_id": "stack1",
                    "name": "Stack 1",
                    "base_os": "amazonlinux2",
                    "ami_id": "ami-123",
                    "gpu": "NO_GPU",
                    "projects": ["project1"],
                    "min_storage_value": 20,
                    "min_storage_unit": "GB",
                    "min_ram_value": 4,
                    "min_ram_unit": "GB",
                }
            ],
            None,
        )

        virtual_desktop_controller.list_software_stacks(project_id="project1")

        expected_filter = {
            "projects": {
                "AttributeValueList": ["project1"],
                "ComparisonOperator": "CONTAINS",
            },
        }
        mock_software_stacks.list_software_stacks.assert_called_once_with(
            project_id="project1",
            base_os=None,
            name=None,
            next_token=None,
        )

    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    @patch("api.controllers.virtual_desktop_controller.software_stacks")
    @patch("res.resources.projects.get_project")
    def test_list_software_stacks_non_admin_with_project_id(
        self, mock_get_project, mock_software_stacks, mock_is_active_admin
    ):
        """Test that list_software_stacks works for non-admin with project_id."""
        mock_is_active_admin.return_value = False
        mock_get_project.return_value = {
            "project_id": "project1",
            "name": "Project 1",
            "title": "Project 1",
        }
        mock_software_stacks.list_software_stacks.return_value = (
            [
                {
                    "stack_id": "stack1",
                    "name": "Stack 1",
                    "base_os": "amazonlinux2",
                    "ami_id": "ami-123",
                    "gpu": "NO_GPU",
                    "projects": ["project1"],
                    "min_storage_value": 20,
                    "min_storage_unit": "GB",
                    "min_ram_value": 4,
                    "min_ram_unit": "GB",
                }
            ],
            None,
        )

        result = virtual_desktop_controller.list_software_stacks(project_id="project1")

        mock_software_stacks.list_software_stacks.assert_called_once_with(
            project_id="project1",
            base_os=None,
            name=None,
            next_token=None,
        )
        assert isinstance(result, ListSoftwareStacksResponseContent)

    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_list_software_stacks_non_admin_without_project_id_raises_bad_request(
        self, mock_is_active_admin
    ):
        """Test that non-admin users without project_id raises BadRequestException."""
        mock_is_active_admin.return_value = False

        with pytest.raises(BadRequestException) as exc_info:
            virtual_desktop_controller.list_software_stacks()

        assert "project_id is required field" in str(exc_info.value)

    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    @patch("api.controllers.virtual_desktop_controller.software_stacks")
    def test_list_software_stacks_returns_all_stacks(
        self, mock_software_stacks, mock_is_active_admin
    ):
        """Test that list_software_stacks returns all stacks from DynamoDB."""
        mock_is_active_admin.return_value = True
        mock_stacks = [
            {
                "stack_id": "stack1",
                "name": "Stack 1",
                "base_os": "amazonlinux2",
                "ami_id": "ami-123",
                "gpu": "NO_GPU",
                "projects": [],
                "min_storage_value": 20,
                "min_storage_unit": "GB",
                "min_ram_value": 4,
                "min_ram_unit": "GB",
            },
            {
                "stack_id": "stack2",
                "name": "Stack 2",
                "base_os": "windows",
                "ami_id": "ami-456",
                "gpu": "NO_GPU",
                "projects": [],
                "min_storage_value": 20,
                "min_storage_unit": "GB",
                "min_ram_value": 4,
                "min_ram_unit": "GB",
            },
        ]
        mock_software_stacks.list_software_stacks.return_value = (
            mock_stacks,
            None,
        )

        result = virtual_desktop_controller.list_software_stacks()

        assert len(result.listing) == 2
        assert result.listing[0].stack_id == "stack1"
        assert result.listing[1].stack_id == "stack2"

    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    @patch("api.controllers.virtual_desktop_controller.software_stacks")
    def test_list_software_stacks_returns_next_token(
        self, mock_software_stacks, mock_is_active_admin
    ):
        """Test that list_software_stacks returns next_token when pagination is needed."""
        mock_is_active_admin.return_value = True
        mock_software_stacks.list_software_stacks.return_value = (
            [
                {
                    "stack_id": "stack1",
                    "name": "Stack 1",
                    "min_storage_value": 20,
                    "min_storage_unit": "GB",
                    "min_ram_value": 4,
                    "min_ram_unit": "GB",
                }
            ],
            "next_page_token",
        )

        result = virtual_desktop_controller.list_software_stacks()

        assert len(result.listing) == 1
        assert result.next_token == "next_page_token"

    # Update Software Stack Tests
    @patch(
        "api.controllers.virtual_desktop_controller.software_stacks.update_software_stack"
    )
    @patch(
        "api.controllers.virtual_desktop_controller.VirtualDesktopSoftwareStack.from_ddb_dict"
    )
    @patch("api.controllers.virtual_desktop_controller.validate_software_stack_fields")
    @patch(
        "api.controllers.virtual_desktop_controller.software_stacks.get_software_stack_by_name"
    )
    @patch(
        "api.controllers.virtual_desktop_controller.software_stacks.get_software_stack"
    )
    @patch(
        "api.controllers.virtual_desktop_controller.UpdateSoftwareStackRequestContent.from_dict"
    )
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_update_software_stack_success(
        self,
        mock_is_active_admin,
        mock_from_dict,
        mock_get_stack,
        mock_get_by_name,
        mock_validate,
        mock_from_ddb_dict,
        mock_update,
    ):
        """Test successful update of software stack."""
        mock_is_active_admin.return_value = True

        # Mock request
        mock_request = Mock()
        mock_software_stack = Mock()
        mock_software_stack.base_os = "amazonlinux2"
        mock_software_stack.name = "updated-stack"

        # Mock the to_ddb_dict method to return the expected dictionary
        updated_stack_dict = {
            "stack_id": "test-stack-123",
            "name": "updated-stack",
            "version": 2,
        }
        mock_software_stack.to_ddb_dict.return_value = updated_stack_dict

        mock_request.software_stack = mock_software_stack
        mock_from_dict.return_value = mock_request

        # Mock existing stack
        existing_stack = {
            "created_on": "1234567890",
            "version": 1,
            "stack_id": "test-stack-123",
        }
        mock_get_stack.return_value = existing_stack

        # Mock name check (no conflict)
        mock_get_by_name.return_value = None

        # Mock validation
        mock_validate.return_value = (mock_software_stack, True)

        # Mock update result
        updated_stack = {
            "stack_id": "test-stack-123",
            "name": "updated-stack",
            "version": 2,
        }
        mock_update.return_value = updated_stack
        mock_from_ddb_dict.return_value = VirtualDesktopSoftwareStack(
            name="updated-stack", stack_id="test-stack-123"
        )

        body = {"software_stack": {"name": "updated-stack", "base_os": "amazonlinux2"}}
        stack_id = "test-stack-123"

        result = virtual_desktop_controller.update_software_stack(
            body, stack_id, user={"username": "clusteradmin"}
        )

        assert isinstance(result, UpdateSoftwareStackResponseContent)
        mock_update.assert_called_once_with(updated_stack_dict)
        mock_from_ddb_dict.assert_called_once_with(updated_stack)

    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_update_software_stack_non_admin_raises_oauth_problem(
        self, mock_is_active_admin
    ):
        """Test that update_software_stack raises OAuthProblem for non-admin users."""
        mock_is_active_admin.return_value = False

        body = {"software_stack": {"name": "test-stack"}}
        stack_id = "test-stack-123"

        with pytest.raises(OAuthProblem) as exc_info:
            virtual_desktop_controller.update_software_stack(
                body, stack_id, user={"username": "user1"}
            )

        assert "Unauthorized user" in str(exc_info.value)

    @patch(
        "api.controllers.virtual_desktop_controller.UpdateSoftwareStackRequestContent.from_dict"
    )
    @patch(
        "api.controllers.virtual_desktop_controller.software_stacks.get_software_stack"
    )
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_update_software_stack_not_found_raises_not_found_exception(
        self, mock_is_active_admin, mock_get_stack, mock_from_dict
    ):
        """Test that update_software_stack raises NotFoundException when software stack is not found."""
        mock_is_active_admin.return_value = True
        mock_get_stack.side_effect = Exception("Stack not found")

        mock_request = Mock()
        mock_software_stack = Mock()
        mock_software_stack.base_os = Mock()
        mock_software_stack.base_os.value = "amazonlinux2"
        mock_request.software_stack = mock_software_stack
        mock_from_dict.return_value = mock_request

        body = {"software_stack": {"name": "test-stack", "base_os": "amazonlinux2"}}
        stack_id = "nonexistent-stack"

        with pytest.raises(NotFoundException) as exc_info:
            virtual_desktop_controller.update_software_stack(
                body, stack_id, user={"username": "clusteradmin"}
            )

        assert (
            "Software stack with amazonlinux2 and nonexistent-stack not found"
            in str(exc_info.value)
        )

    @patch(
        "api.controllers.virtual_desktop_controller.software_stacks.get_software_stack_by_name"
    )
    @patch(
        "api.controllers.virtual_desktop_controller.software_stacks.get_software_stack"
    )
    @patch(
        "api.controllers.virtual_desktop_controller.UpdateSoftwareStackRequestContent.from_dict"
    )
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_update_software_stack_name_conflict_raises_bad_request(
        self, mock_is_active_admin, mock_from_dict, mock_get_stack, mock_get_by_name
    ):
        """Test that update_software_stack raises BadRequestException when name conflicts with another stack."""
        mock_is_active_admin.return_value = True

        mock_request = Mock()
        mock_software_stack = Mock()
        mock_software_stack.base_os = "amazonlinux2"
        mock_software_stack.name = "existing-name"
        mock_request.software_stack = mock_software_stack
        mock_from_dict.return_value = mock_request

        existing_stack = {
            "created_on": "1234567890",
            "version": 1,
            "stack_id": "test-stack-123",
        }
        mock_get_stack.return_value = existing_stack

        conflicting_stack = {"stack_id": "different-stack-456"}
        mock_get_by_name.return_value = conflicting_stack

        body = {"software_stack": {"name": "existing-name", "base_os": "amazonlinux2"}}
        stack_id = "test-stack-123"

        with pytest.raises(BadRequestException) as exc_info:
            virtual_desktop_controller.update_software_stack(
                body, stack_id, user={"username": "clusteradmin"}
            )

        assert 'Another Software stack with name "existing-name" already exists' in str(
            exc_info.value
        )

    @patch("api.controllers.virtual_desktop_controller.validate_software_stack_fields")
    @patch(
        "api.controllers.virtual_desktop_controller.software_stacks.get_software_stack_by_name"
    )
    @patch(
        "api.controllers.virtual_desktop_controller.software_stacks.get_software_stack"
    )
    @patch(
        "api.controllers.virtual_desktop_controller.UpdateSoftwareStackRequestContent.from_dict"
    )
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_update_software_stack_invalid_fields_raises_bad_request(
        self,
        mock_is_active_admin,
        mock_from_dict,
        mock_get_stack,
        mock_get_by_name,
        mock_validate,
    ):
        """Test that update_software_stack raises BadRequestException for invalid fields."""
        mock_is_active_admin.return_value = True

        mock_request = Mock()
        mock_software_stack = Mock()
        mock_software_stack.base_os = "amazonlinux2"
        mock_software_stack.name = "test-stack"
        mock_request.software_stack = mock_software_stack
        mock_from_dict.return_value = mock_request

        existing_stack = {
            "created_on": "1234567890",
            "version": 1,
            "stack_id": "test-stack-123",
        }
        mock_get_stack.return_value = existing_stack

        mock_get_by_name.return_value = None

        mock_failed_stack = Mock()
        mock_failed_stack.failure_reason = "Invalid AMI ID"
        mock_validate.return_value = (mock_failed_stack, False)

        body = {
            "software_stack": {
                "name": "test-stack",
                "base_os": "amazonlinux2",
                "ami_id": "invalid-ami",
            }
        }
        stack_id = "test-stack-123"

        with pytest.raises(BadRequestException) as exc_info:
            virtual_desktop_controller.update_software_stack(
                body, stack_id, user={"username": "clusteradmin"}
            )

        assert "Invalid software stack request: Invalid AMI ID" in str(exc_info.value)

    @patch(
        "api.controllers.virtual_desktop_controller.software_stacks.get_software_stack"
    )
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_get_software_stack_admin_returns_correct_response_type(
        self, mock_is_active_admin, mock_get_stack
    ):
        """Test that get_software_stack returns GetSoftwareStackResponseContent instance for admin."""
        mock_is_active_admin.return_value = True

        mock_stack = {
            "stack_id": "test-stack-123",
            "name": "Test Stack",
            "base_os": "amazonlinux2",
            "ami_id": "ami-12345678",
            "created_on": 1772060599000,
            "min_storage_value": 20,
            "min_storage_unit": "GB",
            "min_ram_value": 4,
            "min_ram_unit": "GB",
            "gpu": "NO_GPU",
            "projects": [],
        }
        mock_get_stack.return_value = mock_stack

        result = virtual_desktop_controller.get_software_stack(
            stack_id="test-stack-123",
            base_os="amazonlinux2",
            user={"username": "clusteradmin"},
        )

        assert isinstance(result, GetSoftwareStackResponseContent)
        assert hasattr(result, "software_stack")
        mock_get_stack.assert_called_once_with(
            base_os="amazonlinux2",
            stack_id="test-stack-123",
            get_project_details=True,
        )

    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_get_software_stack_empty_stack_id_raises_bad_request(
        self, mock_is_active_admin
    ):
        """Test that get_software_stack raises Exception for empty stack_id."""
        mock_is_active_admin.return_value = True

        with pytest.raises(Exception) as exc_info:
            virtual_desktop_controller.get_software_stack(
                stack_id="", base_os="amazonlinux2", user={"username": "clusteradmin"}
            )

        assert "Stack ID and Base OS required" in str(exc_info.value)

    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_get_software_stack_empty_base_os_raises_bad_request(
        self, mock_is_active_admin
    ):
        """Test that get_software_stack raises Exception for empty base_os."""
        mock_is_active_admin.return_value = True

        with pytest.raises(Exception) as exc_info:
            virtual_desktop_controller.get_software_stack(
                stack_id="test-stack-123", base_os="", user={"username": "clusteradmin"}
            )

        assert "Stack ID and Base OS required" in str(exc_info.value)

    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_get_software_stack_non_admin_raises_oauth_problem(
        self, mock_is_active_admin
    ):
        """Test that get_software_stack raises OAuthProblem for non-admin users."""
        mock_is_active_admin.return_value = False

        with pytest.raises(OAuthProblem) as exc_info:
            virtual_desktop_controller.get_software_stack(
                stack_id="test-stack-123",
                base_os="amazonlinux2",
                user={"username": "user1"},
            )

        assert "Unauthorized user" in str(exc_info.value)
        mock_is_active_admin.assert_called_once()

    @patch(
        "api.controllers.virtual_desktop_controller.software_stacks.get_software_stack"
    )
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_get_software_stack_not_found_raises_bad_request(
        self, mock_is_active_admin, mock_get_stack
    ):
        """Test that get_software_stack raises BadRequestException when software stack is not found."""
        mock_is_active_admin.return_value = True
        mock_get_stack.side_effect = SoftwareStackNotFound("Software stack not found")

        with pytest.raises(BadRequestException) as exc_info:
            virtual_desktop_controller.get_software_stack(
                stack_id="nonexistent-stack",
                base_os="amazonlinux2",
                user={"username": "clusteradmin"},
            )

        assert "Software stack not found" in str(exc_info.value)
        mock_get_stack.assert_called_once_with(
            base_os="amazonlinux2",
            stack_id="nonexistent-stack",
            get_project_details=True,
        )

    @patch(
        "api.controllers.virtual_desktop_controller.software_stacks.get_software_stack"
    )
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_get_software_stack_returns_formatted_stack(
        self, mock_is_active_admin, mock_get_stack
    ):
        """Test that get_software_stack returns properly formatted software stack."""
        mock_is_active_admin.return_value = True

        raw_stack = {
            "stack_id": "test-stack-123",
            "name": "Test Stack",
            "base_os": "amazonlinux2",
            "ami_id": "ami-12345678",
            "description": "Test Description",
            "created_on": 1772060599000,
            "updated_on": 1772060599000,
        }
        mock_get_stack.return_value = raw_stack

        result = virtual_desktop_controller.get_software_stack(
            stack_id="test-stack-123",
            base_os="amazonlinux2",
            user={"username": "clusteradmin"},
        )

        assert isinstance(result, GetSoftwareStackResponseContent)
        assert result.software_stack.stack_id == "test-stack-123"
        assert result.software_stack.name == "Test Stack"
        assert result.software_stack.base_os == "amazonlinux2"
        assert result.software_stack.created_on is not None
        assert "2026-02-25" in str(result.software_stack.created_on)
        assert result.software_stack.updated_on is not None
        assert "2026-02-25" in str(result.software_stack.updated_on)

    @patch(
        "api.controllers.virtual_desktop_controller.software_stacks.get_software_stack"
    )
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    @patch("res.resources.projects.get_project")
    def test_get_software_stack_with_all_fields(
        self, mock_get_project, mock_is_active_admin, mock_get_stack
    ):
        """Test that get_software_stack handles software stack with all optional fields."""
        mock_is_active_admin.return_value = True
        mock_get_project.return_value = {
            "project_id": "project1",
            "name": "Project 1",
            "title": "Project 1",
        }

        complete_stack = {
            "stack_id": "test-stack-123",
            "name": "Complete Test Stack",
            "base_os": "windows",
            "ami_id": "ami-87654321",
            "description": "Complete test description",
            "gpu": "NVIDIA",
            "min_ram_value": 8,
            "min_ram_unit": "GB",
            "min_storage_value": 100,
            "min_storage_unit": "GB",
            "projects": ["project1", "project2"],
            "enabled": True,
            "created_on": 1772060599000,
            "updated_on": 1772060599000,
        }

        mock_get_stack.return_value = complete_stack

        result = virtual_desktop_controller.get_software_stack(
            stack_id="test-stack-123",
            base_os="windows",
            user={"username": "clusteradmin"},
        )

        assert isinstance(result, GetSoftwareStackResponseContent)
        assert result.software_stack.stack_id == "test-stack-123"
        assert result.software_stack.name == "Complete Test Stack"
        assert result.software_stack.base_os == "windows"
        assert result.software_stack.ami_id == "ami-87654321"
        mock_get_stack.assert_called_once_with(
            base_os="windows",
            stack_id="test-stack-123",
            get_project_details=True,
        )

    @patch(
        "api.controllers.virtual_desktop_controller.software_stacks.get_software_stack"
    )
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_get_software_stack_with_disabled_stack(
        self, mock_is_active_admin, mock_get_stack
    ):
        """Test that admin can retrieve disabled software stacks."""
        mock_is_active_admin.return_value = True

        disabled_stack = {
            "stack_id": "test-disabled-stack",
            "name": "Disabled Stack",
            "base_os": "amazonlinux2",
            "ami_id": "ami-disabled123",
            "enabled": False,
            "min_ram_value": 4,
            "min_ram_unit": "GB",
            "min_storage_value": 20,
            "min_storage_unit": "GB",
        }

        mock_get_stack.return_value = disabled_stack

        result = virtual_desktop_controller.get_software_stack(
            stack_id="test-disabled-stack",
            base_os="amazonlinux2",
            user={"username": "clusteradmin"},
        )

        assert isinstance(result, GetSoftwareStackResponseContent)
        assert result.software_stack.enabled is False
        assert result.software_stack.stack_id == "test-disabled-stack"
        mock_get_stack.assert_called_once_with(
            base_os="amazonlinux2",
            stack_id="test-disabled-stack",
            get_project_details=True,
        )

    @patch(
        "api.controllers.virtual_desktop_controller.software_stacks.get_software_stack"
    )
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    @patch("res.resources.projects.get_project")
    def test_get_software_stack_with_project(
        self, mock_get_project, mock_is_active_admin, mock_get_stack
    ):
        """Test that admin can retrieve software stack with project associations."""
        mock_project = {
            "project_id": "proj-123",
            "name": "Project 123",
            "title": "Project 123",
        }
        mock_is_active_admin.return_value = True
        mock_get_project.return_value = mock_project

        stack_with_project = {
            "stack_id": "test-stack-with-project",
            "name": "Stack With Project",
            "base_os": "amazonlinux2",
            "ami_id": "ami-project123",
            "enabled": True,
            "min_ram_value": 4,
            "min_ram_unit": "GB",
            "min_storage_value": 20,
            "min_storage_unit": "GB",
            "projects": [mock_project],
        }

        mock_get_stack.return_value = stack_with_project

        result = virtual_desktop_controller.get_software_stack(
            stack_id="test-stack-with-project",
            base_os="amazonlinux2",
            user={"username": "clusteradmin"},
        )

        assert isinstance(result, GetSoftwareStackResponseContent)
        assert result.software_stack.stack_id == "test-stack-with-project"
        assert result.software_stack.projects is not None
        assert len(result.software_stack.projects) == 1
        project = result.software_stack.projects[0]
        assert project.project_id == "proj-123"
        mock_get_stack.assert_called_once_with(
            base_os="amazonlinux2",
            stack_id="test-stack-with-project",
            get_project_details=True,
        )

    @patch("res.resources.session_permissions.table_utils.get_item")
    def test_get_session_permission_success(self, mock_get_item):
        """Test get_session_permission returns permission successfully."""

        mock_get_item.return_value = {
            "idea_session_id": "session-123",
            "actor_name": "user1",
        }

        result = session_permissions.get_session_permission("session-123", "user1")

        assert result == {"idea_session_id": "session-123", "actor_name": "user1"}
        mock_get_item.assert_called_once()

    @patch("res.resources.session_permissions.table_utils.list_items_paginated")
    def test_list_session_permissions_paginated_success(self, mock_list_items):
        """Test list_session_permissions_paginated returns permissions successfully."""

        mock_permissions = [{"idea_session_id": "session-123", "actor_name": "user1"}]
        mock_list_items.return_value = (mock_permissions, None)

        result, next_token = session_permissions.list_session_permissions_paginated()

        assert result == mock_permissions
        assert next_token is None
        mock_list_items.assert_called_once()

    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    @patch(
        "api.controllers.virtual_desktop_controller.res_session_permissions.list_session_permissions_paginated"
    )
    @patch(
        "api.controllers.virtual_desktop_controller.VirtualDesktopSessionPermission.from_ddb_dict"
    )
    def test_controller_list_session_permissions_success(
        self, mock_convert_format, mock_list_paginated, mock_is_admin
    ):

        mock_is_admin.return_value = True
        mock_permissions = [{"idea_session_id": "session-123", "actor_name": "user1"}]
        mock_list_paginated.return_value = (mock_permissions, None)

        result = virtual_desktop_controller.list_session_permissions(
            res_session_id="session-123",
            user={"clusteradmin": "testuser"},
            token_info={},
        )

        assert result.listing is not None
        assert result.next_token is None
        mock_list_paginated.assert_called_once()
        mock_convert_format.assert_called_once()

    # Delete Permission Profile Tests
    @patch(
        "api.controllers.virtual_desktop_controller.permission_profiles.delete_permission_profile"
    )
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_delete_permission_profile_success(self, mock_is_active_admin, mock_delete):
        """Test successful deletion of permission profile."""
        mock_is_active_admin.return_value = True
        mock_delete.return_value = None

        profile_id = "test-profile-123"

        result = virtual_desktop_controller.delete_permission_profile(
            profile_id, user={"username": "clusteradmin"}
        )

        assert isinstance(result, DeletePermissionProfileResponseContent)
        assert result.success is True
        mock_delete.assert_called_once_with(profile_id)

    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_delete_permission_profile_non_admin_raises_oauth_problem(
        self, mock_is_active_admin
    ):
        """Test that delete_permission_profile raises OAuthProblem for non-admin users."""
        mock_is_active_admin.return_value = False

        profile_id = "test-profile-123"

        with pytest.raises(OAuthProblem) as exc_info:
            virtual_desktop_controller.delete_permission_profile(
                profile_id, user={"username": "user1"}
            )

        assert "Unauthorized user" in str(exc_info.value)

    @patch(
        "api.controllers.virtual_desktop_controller.permission_profiles.delete_permission_profile"
    )
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_delete_permission_profile_not_found_raises_not_found_exception(
        self, mock_is_active_admin, mock_delete
    ):
        """Test that delete_permission_profile raises NotFoundException when permission profile is not found."""
        mock_is_active_admin.return_value = True
        mock_delete.side_effect = PermissionProfileNotFound(
            "Permission profile not found"
        )

        profile_id = "nonexistent-profile"

        with pytest.raises(NotFoundException) as exc_info:
            virtual_desktop_controller.delete_permission_profile(
                profile_id, user={"username": "clusteradmin"}
            )

        assert "Permission profile not found" in str(exc_info.value)

    @patch(
        "api.controllers.virtual_desktop_controller.permission_profiles.delete_permission_profile"
    )
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_delete_permission_profile_generic_exception_raises_internal_service_exception(
        self, mock_is_active_admin, mock_delete
    ):
        """Test that delete_permission_profile raises InternalServiceException for generic exceptions."""
        mock_is_active_admin.return_value = True
        mock_delete.side_effect = Exception("Database connection failed")

        profile_id = "test-profile-123"

        with pytest.raises(InternalServiceException) as exc_info:
            virtual_desktop_controller.delete_permission_profile(
                profile_id, user={"username": "clusteradmin"}
            )

        assert "Database connection failed" in str(exc_info.value)

    # Update Session Permissions Tests
    @patch(
        "api.controllers.virtual_desktop_controller.VirtualDesktopSessionPermission.from_ddb_dict"
    )
    @patch(
        "datamodel.models.virtual_desktop_session_permission.VirtualDesktopSessionPermission.to_ddb_dict"
    )
    @patch(
        "api.controllers.virtual_desktop_controller.res_sessions.get_session_if_owner"
    )
    @patch(
        "api.controllers.virtual_desktop_controller.res_session_permissions.update_permissions_for_sessions"
    )
    @patch(
        "api.controllers.virtual_desktop_controller.res_session_permissions.get_session_permission"
    )
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_update_session_permissions_admin_success(
        self,
        mock_is_admin,
        mock_get_permission,
        mock_update_permissions,
        mock_get_session_if_owner,
        mock_to_ddb,
        mock_from_ddb,
    ):
        """Test that update_session_permissions works successfully for admin users."""
        body = self._get_update_session_permissions_body()

        mock_is_admin.return_value = True
        mock_get_session_if_owner.return_value = {
            "session_id": "session-123",
            "owner": "user1",
            "base_os": "amzn2023",
        }
        mock_get_permission.return_value = None
        mock_update_permissions.return_value = [
            {"idea_session_id": "session-123", "actor_name": "user1"}
        ]
        mock_to_ddb.return_value = {
            "idea_session_id": "session-123",
            "actor_name": "user1",
        }
        mock_permission_obj = Mock()
        mock_from_ddb.return_value = mock_permission_obj

        result = virtual_desktop_controller.update_session_permissions(
            body=body, user={"username": "clusteradmin"}, token_info={}
        )

        assert isinstance(result, UpdateSessionPermissionsResponseContent)
        mock_update_permissions.assert_called_once()
        args, _ = mock_update_permissions.call_args
        assert len(args[0]) == 1
        assert len(args[1]) == 0

    @patch(
        "api.controllers.virtual_desktop_controller.VirtualDesktopSessionPermission.from_ddb_dict"
    )
    @patch(
        "datamodel.models.virtual_desktop_session_permission.VirtualDesktopSessionPermission.to_ddb_dict"
    )
    @patch(
        "api.controllers.virtual_desktop_controller.res_sessions.get_session_if_owner"
    )
    @patch(
        "api.controllers.virtual_desktop_controller.res_session_permissions.update_permissions_for_sessions"
    )
    @patch(
        "api.controllers.virtual_desktop_controller.res_session_permissions.get_session_permission"
    )
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_update_session_permissions_non_admin_success(
        self,
        mock_is_admin,
        mock_get_permission,
        mock_update_permissions,
        mock_get_session_if_owner,
        mock_to_ddb,
        mock_from_ddb,
    ):
        """Test that update_session_permissions works for non-admin users with owned sessions."""
        body = self._get_update_session_permissions_body()

        mock_is_admin.return_value = False
        mock_get_session_if_owner.return_value = {
            "session_id": "session-123",
            "owner": "user1",
            "base_os": "amzn2023",
        }
        mock_get_permission.return_value = None
        mock_update_permissions.return_value = [
            {"idea_session_id": "session-123", "actor_name": "user1"}
        ]
        mock_to_ddb.return_value = {
            "idea_session_id": "session-123",
            "actor_name": "user1",
        }
        mock_permission_obj = Mock()
        mock_from_ddb.return_value = mock_permission_obj

        result = virtual_desktop_controller.update_session_permissions(
            body=body, user="user1", token_info={}
        )

        assert isinstance(result, UpdateSessionPermissionsResponseContent)
        mock_update_permissions.assert_called_once()
        args, _ = mock_update_permissions.call_args
        assert len(args[0]) == 1
        assert len(args[1]) == 0

    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_update_session_permissions_non_admin_unauthorized_session_raises_bad_request(
        self, mock_is_admin
    ):
        """Test that update_session_permissions raises BadRequestException for non-admin users with unowned sessions."""
        body = self._get_update_session_permissions_body()

        mock_is_admin.return_value = False

        with pytest.raises(BadRequestException) as exc_info:
            virtual_desktop_controller.update_session_permissions(
                body=body, user={"username": "different_user"}, token_info={}
            )

        assert (
            "INVALID PARAMS. Can update permission for session owned by user only"
            in str(exc_info.value)
        )

    @patch(
        "api.controllers.virtual_desktop_controller.validate_update_session_permission_request"
    )
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_update_session_permissions_invalid_request_raises_bad_request(
        self, mock_is_admin, mock_validate
    ):
        """Test that update_session_permissions raises BadRequestException for invalid requests."""
        body = self._get_update_session_permissions_body()

        mock_is_admin.return_value = True
        mock_validate.return_value = (False, Mock())

        with pytest.raises(BadRequestException):
            virtual_desktop_controller.update_session_permissions(
                body=body, user={"username": "clusteradmin"}, token_info={}
            )

        mock_validate.assert_called_once()

    @patch(
        "api.controllers.virtual_desktop_controller.res_session_permissions.get_session_permission"
    )
    @patch(
        "api.controllers.virtual_desktop_controller.validate_update_session_permission_request"
    )
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    @patch(
        "api.controllers.virtual_desktop_controller.UpdateSessionPermissionsRequestContent.from_dict"
    )
    def test_update_session_permissions_create_existing_permission_raises_bad_request(
        self, mock_from_dict, mock_is_admin, mock_validate, mock_get_permission
    ):
        """Test that creating an existing permission raises BadRequestException."""
        body = self._get_update_session_permissions_body()

        mock_request = Mock()
        mock_permission = Mock()
        mock_permission.idea_session_id = "session-123"
        mock_permission.actor_name = "user1"
        mock_request.create = [mock_permission]
        mock_request.delete = []
        mock_request.update = []
        mock_from_dict.return_value = mock_request

        mock_is_admin.return_value = True
        mock_validate.return_value = (True, mock_request)
        mock_get_permission.return_value = {
            "idea_session_id": "session-123",
            "actor_name": "user1",
        }  # Existing permission

        with pytest.raises(BadRequestException) as exc_info:
            virtual_desktop_controller.update_session_permissions(
                body=body, user={"username": "clusteradmin"}, token_info={}
            )

        assert (
            "Session permission with session_id session-123 and actor_name user1 already exists"
            in str(exc_info.value)
        )

    @patch(
        "api.controllers.virtual_desktop_controller.res_session_permissions.get_session_permission"
    )
    @patch(
        "api.controllers.virtual_desktop_controller.validate_update_session_permission_request"
    )
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    @patch(
        "api.controllers.virtual_desktop_controller.UpdateSessionPermissionsRequestContent.from_dict"
    )
    def test_update_session_permissions_update_nonexistent_permission_raises_bad_request(
        self, mock_from_dict, mock_is_admin, mock_validate, mock_get_permission
    ):
        """Test that updating a non-existent permission raises BadRequestException."""
        body = {
            "create": [],
            "update": [{"idea_session_id": "session-123", "actor_name": "user1"}],
            "delete": [],
        }

        mock_request = Mock()
        mock_permission = Mock()
        mock_permission.idea_session_id = "session-123"
        mock_permission.actor_name = "user1"
        mock_request.create = []
        mock_request.update = [mock_permission]
        mock_request.delete = []
        mock_from_dict.return_value = mock_request

        mock_is_admin.return_value = True
        mock_validate.return_value = (True, mock_request)

        mock_get_permission.side_effect = SessionPermissionsNotFound(
            "Session permission not found"
        )

        with pytest.raises(BadRequestException) as exc_info:
            virtual_desktop_controller.update_session_permissions(
                body=body, user={"username": "clusteradmin"}, token_info={}
            )

        assert (
            "Session permission with session_id session-123 and actor_name user1 does not exist"
            in str(exc_info.value)
        )

    @patch(
        "api.controllers.virtual_desktop_controller.res_session_permissions.get_session_permission"
    )
    @patch(
        "api.controllers.virtual_desktop_controller.validate_update_session_permission_request"
    )
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    @patch(
        "api.controllers.virtual_desktop_controller.UpdateSessionPermissionsRequestContent.from_dict"
    )
    def test_update_session_permissions_delete_nonexistent_permission_raises_bad_request(
        self, mock_from_dict, mock_is_admin, mock_validate, mock_get_permission
    ):
        """Test that deleting a non-existent permission raises BadRequestException."""
        body = {
            "create": [],
            "update": [],
            "delete": [{"idea_session_id": "session-123", "actor_name": "user1"}],
        }

        mock_request = Mock()
        mock_permission = Mock()
        mock_permission.idea_session_id = "session-123"
        mock_permission.actor_name = "user1"
        mock_request.create = []
        mock_request.update = []
        mock_request.delete = [mock_permission]
        mock_from_dict.return_value = mock_request

        mock_is_admin.return_value = True
        mock_validate.return_value = (True, mock_request)

        mock_get_permission.side_effect = SessionPermissionsNotFound(
            "Session permission not found"
        )

        with pytest.raises(BadRequestException) as exc_info:
            virtual_desktop_controller.update_session_permissions(
                body=body, user={"username": "clusteradmin"}, token_info={}
            )

        assert (
            "Session permission with session_id session-123 and actor_name user1 does not exist"
            in str(exc_info.value)
        )

    # List Sessions Tests
    @patch(
        "api.controllers.virtual_desktop_controller.VirtualDesktopSession.from_ddb_dict"
    )
    @patch("api.controllers.virtual_desktop_controller.res_sessions.list_sessions")
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_list_sessions_admin_success(
        self, mock_is_active_admin, mock_list_sessions, mock_from_ddb_dict
    ):
        """Test that list_sessions returns correct response for admin."""
        mock_is_active_admin.return_value = True
        mock_sessions = [
            {"session_id": "session1", "owner": "user1", "state": "READY"},
        ]
        mock_list_sessions.return_value = (mock_sessions, None)
        mock_from_ddb_dict.return_value = Mock()

        result = virtual_desktop_controller.list_sessions(
            state="READY", user={"username": "clusteradmin"}
        )

        assert isinstance(result, ListSessionsResponseContent)
        assert len(result.listing) == 1
        assert result.next_token is None
        mock_list_sessions.assert_called_once()

    @patch(
        "api.controllers.virtual_desktop_controller.VirtualDesktopSession.from_ddb_dict"
    )
    @patch("api.controllers.virtual_desktop_controller.res_sessions.list_sessions")
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_list_sessions_non_admin_success(
        self,
        mock_is_active_admin,
        mock_list_sessions,
        mock_from_ddb_dict,
    ):
        """Test that list_sessions returns correct response for non-admin."""
        mock_is_active_admin.return_value = False
        mock_sessions = [{"session_id": "session1", "owner": "user1"}]
        mock_list_sessions.return_value = (mock_sessions, None)
        mock_from_ddb_dict.return_value = Mock()

        result = virtual_desktop_controller.list_sessions(user="user1")

        assert isinstance(result, ListSessionsResponseContent)
        assert len(result.listing) == 1
        mock_list_sessions.assert_called_once()

    @patch(
        "api.controllers.virtual_desktop_controller.VirtualDesktopSession.from_ddb_dict"
    )
    @patch("api.controllers.virtual_desktop_controller.res_sessions.list_sessions")
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_list_sessions_with_pagination(
        self, mock_is_active_admin, mock_list_sessions, mock_from_ddb_dict
    ):
        """Test that list_sessions handles pagination correctly."""
        mock_is_active_admin.return_value = True
        mock_sessions = [{"session_id": "session1", "name": "Session 1"}]
        mock_list_sessions.return_value = (mock_sessions, "next_page_token")
        mock_from_ddb_dict.return_value = Mock()

        result = virtual_desktop_controller.list_sessions(
            next_token="current_token", user={"username": "clusteradmin"}
        )

        assert isinstance(result, ListSessionsResponseContent)
        assert len(result.listing) == 1
        assert result.next_token == "next_page_token"
        mock_list_sessions.assert_called_once()

    @patch(
        "api.controllers.virtual_desktop_controller.VirtualDesktopSession.from_ddb_dict"
    )
    @patch("api.controllers.virtual_desktop_controller.res_sessions.list_sessions")
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_list_sessions_returns_empty_list_when_no_sessions(
        self, mock_is_active_admin, mock_list_sessions, mock_from_ddb_dict
    ):
        """Test that list_sessions returns empty list when no sessions found."""
        mock_is_active_admin.return_value = True
        mock_list_sessions.return_value = ([], None)

        result = virtual_desktop_controller.list_sessions(
            user={"username": "clusteradmin"}
        )

        assert isinstance(result, ListSessionsResponseContent)
        assert len(result.listing) == 0
        assert result.next_token is None
        mock_from_ddb_dict.assert_not_called()

    # Get Session Tests
    @patch(
        "api.controllers.virtual_desktop_controller.VirtualDesktopSession.from_ddb_dict"
    )
    @patch("api.controllers.virtual_desktop_controller.res_sessions.get_session")
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_get_session_admin_success(
        self, mock_is_active_admin, mock_get_session, mock_from_ddb_dict
    ):
        """Test that admin can get any user's session."""
        mock_is_active_admin.return_value = True
        mock_session_dict = {
            "owner": "user1",
            "idea_session_id": "session-123",
            "name": "Test Session",
            "state": "READY",
        }
        mock_get_session.return_value = mock_session_dict
        mock_session_obj = Mock()
        mock_from_ddb_dict.return_value = mock_session_obj

        result = virtual_desktop_controller.get_session(
            "session-123", "user1", user="clusteradmin"
        )

        assert result.session == mock_session_obj
        mock_is_active_admin.assert_called_once_with("clusteradmin")
        mock_get_session.assert_called_once_with("user1", "session-123")
        mock_from_ddb_dict.assert_called_once_with(mock_session_dict)

    @patch(
        "api.controllers.virtual_desktop_controller.VirtualDesktopSession.from_ddb_dict"
    )
    @patch("api.controllers.virtual_desktop_controller.res_sessions.get_session")
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_get_session_non_admin_own_session_success(
        self, mock_is_active_admin, mock_get_session, mock_from_ddb_dict
    ):
        """Test that non-admin can get their own session."""
        mock_is_active_admin.return_value = False
        mock_session_dict = {
            "owner": "user1",
            "idea_session_id": "session-123",
            "name": "Test Session",
            "state": "READY",
        }
        mock_get_session.return_value = mock_session_dict
        mock_session_obj = Mock()
        mock_from_ddb_dict.return_value = mock_session_obj

        result = virtual_desktop_controller.get_session(
            "session-123", "user1", user="user1"
        )

        assert result.session == mock_session_obj
        mock_get_session.assert_called_once_with("user1", "session-123")
        mock_from_ddb_dict.assert_called_once_with(mock_session_dict)

    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_get_session_non_admin_other_user_raises_oauth_problem(
        self, mock_is_active_admin
    ):
        """Test that non-admin users cannot get other users' sessions."""
        mock_is_active_admin.return_value = False

        with pytest.raises(OAuthProblem) as exc_info:
            virtual_desktop_controller.get_session("session-123", "user2", user="user1")

        assert "Non admin user cannot get session info of other users" in str(
            exc_info.value
        )
        mock_is_active_admin.assert_called_once_with("user1")

    @patch("api.controllers.virtual_desktop_controller.res_sessions.get_session")
    @patch("api.controllers.virtual_desktop_controller.accounts.is_active_admin")
    def test_get_session_not_found_raises_bad_request(
        self, mock_is_active_admin, mock_get_session
    ):
        """Test that get_session raises BadRequestException when session is not found."""
        mock_is_active_admin.return_value = True
        mock_get_session.side_effect = UserSessionNotFound("Session not found")

        with pytest.raises(BadRequestException) as exc_info:
            virtual_desktop_controller.get_session(
                "nonexistent-session", "user1", user="clusteradmin"
            )

        assert (
            "Session with session_id nonexistent-session and owner user1 does not exist"
            in str(exc_info.value)
        )
        mock_get_session.assert_called_once_with("user1", "nonexistent-session")
