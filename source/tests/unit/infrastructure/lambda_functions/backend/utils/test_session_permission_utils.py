#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import sys
from unittest.mock import patch, Mock
import pytest

# Add the backend directory to Python path to match utils import context
backend_path = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "../../../../../idea/backend",
    )
)
sys.path.insert(0, backend_path)

from api import exceptions as api_exceptions
from res import exceptions as res_exceptions  # type: ignore
from api.utils import session_utils
from api.utils.session_permission_utils import _validate_actors_for_session_permission_requests
from res.exceptions import SoftwareStackNotFound
from res.resources import sessions as res_sessions
from res.resources import software_stacks

class TestValidateOwnerForCreate:
    """Test _validate_owner_for_create function."""

    @patch("api.utils.session_utils.role_assignments.get_user_permissions")
    def test_validate_owner_for_create_missing_project_id_fails(self, mock_get_permissions):
        """Test that missing project_id returns error."""
        mock_session = Mock()
        mock_session.project = Mock()
        mock_session.project.project_id = None
        mock_session.owner = "testuser"
        mock_get_permissions.return_value = set()
        
        message, is_valid = session_utils._validate_owner_for_create(mock_session, "testuser")
        
        # Function should fail when user doesn't have permissions
        assert is_valid is False
        assert "not authorized" in message.lower()

    @patch("api.utils.session_utils.role_assignments.get_user_permissions")
    def test_validate_owner_for_create_missing_owner_fails(self, mock_get_permissions):
        """Test that missing owner returns error."""
        mock_session = Mock()
        mock_session.project.project_id = "proj-123"
        mock_session.owner = None
        mock_get_permissions.return_value = set()
        
        message, is_valid = session_utils._validate_owner_for_create(mock_session, "testuser")
        
        # Function should fail when user doesn't have permissions
        assert is_valid is False
        assert "not authorized" in message.lower()

    @patch("api.utils.session_utils.role_assignments.get_user_permissions")
    def test_validate_owner_for_create_user_creating_own_session_with_permission(self, mock_get_permissions):
        """Test user creating session for themselves with proper permissions."""
        mock_session = Mock()
        mock_session.project.project_id = "proj-123"
        mock_session.owner = "testuser"
        mock_get_permissions.return_value = {"vdis.create_sessions"}
        
        message, is_valid = session_utils._validate_owner_for_create(mock_session, "testuser")
        
        assert is_valid is True
        assert message == ""
        mock_get_permissions.assert_called_once_with("testuser", "proj-123:project")

    @patch("api.utils.session_utils.role_assignments.get_user_permissions")
    def test_validate_owner_for_create_user_creating_own_session_without_permission(self, mock_get_permissions):
        """Test user creating session for themselves without permission fails."""
        mock_session = Mock()
        mock_session.project.project_id = "proj-123"
        mock_session.owner = "testuser"
        mock_get_permissions.return_value = set()
        
        message, is_valid = session_utils._validate_owner_for_create(mock_session, "testuser")
        
        assert is_valid is False
        assert "not authorized to create sessions for yourself" in message

    @patch("api.utils.session_utils.role_assignments.get_user_permissions")
    def test_validate_owner_for_create_user_creating_others_session_with_permission(self, mock_get_permissions):
        """Test user creating session for another user with proper permissions."""
        mock_session = Mock()
        mock_session.project.project_id = "proj-123"
        mock_session.owner = "otheruser"
        mock_get_permissions.return_value = {"vdis.create_terminate_others_sessions"}
        
        message, is_valid = session_utils._validate_owner_for_create(mock_session, "testuser")
        
        assert is_valid is True
        assert message == ""

    @patch("api.utils.session_utils.role_assignments.get_user_permissions")
    def test_validate_owner_for_create_user_creating_others_session_without_permission(self, mock_get_permissions):
        """Test user creating session for another user without permission fails."""
        mock_session = Mock()
        mock_session.project.project_id = "proj-123"
        mock_session.owner = "otheruser"
        mock_get_permissions.return_value = {"vdis.create_sessions"}
        
        message, is_valid = session_utils._validate_owner_for_create(mock_session, "testuser")
        
        assert is_valid is False
        assert "not authorized to create sessions for others" in message


class TestValidateCreateSessionRequest:
    
    @patch("api.utils.session_utils.validate_create_session_request")
    def test_validate_create_session_admin_succeed(self, mock_validate):
        """Test that admin-launched sessions skip user-specific validation."""
        mock_session = Mock()
        mock_session.owner = None
        mock_session.is_launched_by_admin = True
        mock_validate.return_value = (mock_session, True)
        
        result_session, is_valid = session_utils._validate_create_session_request(mock_session, "testuser")
        
        assert mock_session.owner == "testuser"
        assert is_valid is True
        mock_validate.assert_called_once_with(mock_session)

    @patch("api.utils.session_utils._validate_owner_for_create")
    def test_validate_create_session_request_invalid_owner_returns_fails(self, mock_validate_owner):
        """Test that invalid owner validation fails the request."""
        mock_session = Mock()
        mock_session.owner = "testuser"
        mock_session.is_launched_by_admin = False
        mock_session.failure_reason = None
        mock_validate_owner.return_value = ("User not authorized", False)
        
        result_session, is_valid = session_utils._validate_create_session_request(mock_session, "testuser")
        
        assert is_valid is False
        assert "User not authorized" in result_session.failure_reason

    @patch("api.utils.session_utils.accounts.get_user")
    @patch("api.utils.session_utils._validate_owner_for_create")
    @patch("api.utils.session_utils.constants")
    def test_validate_create_session_request_cognito_user_without_uid_fails(self, mock_constants, mock_validate_owner, mock_get_user):
        """Test that Cognito user without UID fails validation."""
        mock_constants.COGNITO_USER_IDP_TYPE = "cognito"
        mock_session = Mock()
        mock_session.owner = "testuser"
        mock_session.is_launched_by_admin = False
        mock_validate_owner.return_value = ("", True)
        mock_get_user.return_value = {"uid": None, "identity_source": "cognito"}
        
        result_session, is_valid = session_utils._validate_create_session_request(mock_session, "testuser")
        
        assert is_valid is False
        assert "unable to create an ID" in result_session.failure_reason

    @patch("api.utils.session_utils.accounts.get_user")
    @patch("api.utils.session_utils._validate_owner_for_create")
    @patch("api.utils.session_utils.constants")
    def test__validate_create_session_request_cognito_user_non_linux_session_fails(self, mock_constants, mock_validate_owner, mock_get_user):
        """Test that Cognito user cannot create non-Linux sessions."""
        mock_constants.SSO_USER_IDP_TYPE = "sso"
        mock_constants.SUPPORTED_LINUX_OS = ["linux"]
        mock_session = Mock()
        mock_session.owner = "testuser"
        mock_session.is_launched_by_admin = False
        mock_session.base_os = "windows"
        mock_validate_owner.return_value = ("", True)
        mock_get_user.return_value = {"uid": "123", "identity_source": "cognito"}
        
        result_session, is_valid = session_utils._validate_create_session_request(mock_session, "testuser")
        
        assert is_valid is False
        assert "not allowed to create non-Linux sessions" in result_session.failure_reason

    @patch("api.utils.session_utils.validate_create_session_request")
    @patch("api.utils.session_utils.cluster_settings.get_setting")
    @patch("api.utils.session_utils.res_projects._get_project_by_id")
    @patch("api.utils.session_utils.res_sessions.get_current_project_session_count_for_user")
    @patch("api.utils.session_utils.accounts.get_user")
    @patch("api.utils.session_utils._validate_owner_for_create")
    @patch("api.utils.session_utils.constants")
    def test__validate_create_session_request_session_count_exceeded_fails(self, mock_constants, mock_validate_owner, mock_get_user, 
                                          mock_get_count, mock_get_project, mock_get_setting, mock_validate):
        """Test that exceeding session count limit fails validation."""
        mock_constants.SSO_USER_IDP_TYPE = "sso"
        mock_constants.SUPPORTED_LINUX_OS = ["linux"]
        mock_session = Mock()
        mock_session.owner = "testuser"
        mock_session.is_launched_by_admin = False
        mock_session.base_os = "linux"
        mock_session.project.project_id = "proj-123"
        mock_validate_owner.return_value = ("", True)
        mock_get_user.return_value = {"uid": "123", "identity_source": "sso"}
        mock_get_count.return_value = 5
        mock_get_project.return_value = {"allowed_sessions_per_user": 5}
        
        result_session, is_valid = session_utils._validate_create_session_request(mock_session, "testuser")
        
        assert is_valid is False
        assert "exceeded the allowed number of sessions" in result_session.failure_reason

class TestValidateCreateSessionRequest:
    """Test validate_create_session_request function"""

    @patch("api.utils.session_utils.cluster_settings.get_setting")
    @patch("api.utils.session_utils.get_gpu_manufacturer")
    @patch("api.utils.session_utils.uuid4")
    def test_complete_create_session_request_generates_name_when_missing_succeed(self, mock_uuid, mock_get_gpu, mock_get_setting):
        """Test that missing session name is auto-generated."""
        mock_uuid.return_value = "generated-uuid"
        mock_get_gpu.return_value = None
        mock_get_setting.return_value = "mock-setting-value"
        
        mock_session = Mock()
        mock_session.name = None
        mock_session.type = "CONSOLE"
        mock_session.server = Mock()
        mock_session.server.root_volume_iops = 3000
        mock_session.server.instance_profile_arn = None
        mock_session.server.key_pair_name = None
        mock_session.server.security_groups = []
        mock_session.project.policy_arns = None
        mock_session.project.security_groups = None
        
        result = session_utils.complete_create_session_request(mock_session, "testuser")
        
        assert result.name == "generated-uuid"

    @patch("api.utils.session_utils.cluster_settings.get_setting")
    @patch("api.utils.session_utils.get_gpu_manufacturer")
    def test_sets_default_root_volume_iops_succeed(self, mock_get_gpu, mock_get_setting):
        """Test that default root volume IOPS is set to 3000."""
        mock_get_gpu.return_value = None
        mock_get_setting.return_value = "mock-setting-value"
        
        mock_session = Mock()
        mock_session.name = "test-session"
        mock_session.type = "CONSOLE"
        mock_session.server = Mock()
        mock_session.server.root_volume_iops = None
        mock_session.server.instance_profile_arn = None
        mock_session.server.key_pair_name = None
        mock_session.server.security_groups = []
        mock_session.project.policy_arns = None
        mock_session.project.security_groups = None
        
        result = session_utils.complete_create_session_request(mock_session, "testuser")
        
        assert result.server.root_volume_iops == 3000

    @patch("api.utils.session_utils.software_stacks.get_software_stack")
    @patch("api.utils.session_utils.res_projects.get_user_projects")
    def test_validate_create_session_request_missing_project_fails(self, mock_get_projects, mock_get_stack):
        """Test that missing project fails validation."""
        mock_session = Mock()
        mock_session.software_stack_id = "stack-123"
        mock_session.base_os = "linux"
        mock_session.project = None
        mock_session.owner = "testuser"
        mock_session.server = Mock()
        mock_session.server.root_volume_size = Mock()
        
        result_session, is_valid = session_utils.validate_create_session_request(mock_session)
        
        assert is_valid is False
        assert "missing" in result_session.failure_reason
        assert "project" in result_session.failure_reason.lower()

    @patch("api.utils.session_utils.VirtualDesktopSoftwareStack.from_ddb_dict")
    @patch("api.utils.session_utils.software_stacks.get_software_stack")
    @patch("api.utils.session_utils.res_projects.get_user_projects")
    def test_validate_create_session_request_missing_root_volume_size_fails(self, mock_get_projects, mock_get_stack, mock_from_ddb):
        """Test that missing root_volume_size fails validation."""
        mock_session = Mock()
        mock_session.software_stack_id = "stack-123"
        mock_session.base_os = "linux"
        mock_session.project.project_id = "proj-123"
        mock_session.owner = "testuser"
        mock_session.server = None
        
        mock_get_projects.return_value = [{"project_id": "proj-123"}]
        mock_software_stack = Mock()
        mock_software_stack.projects = [Mock(project_id="proj-123")]
        mock_from_ddb.return_value = mock_software_stack
        mock_get_stack.return_value = {"stack_id": "stack-123"}
        
        result_session, is_valid = session_utils.validate_create_session_request(mock_session)
        
        assert is_valid is False
        assert "root_volume_size" in result_session.failure_reason.lower()

    def test_validate_create_session_request_missing_software_stack_id_fails(self):
        """Test that missing software_stack_id fails validation."""
        mock_session = Mock()
        mock_session.software_stack_id = None
        mock_session.base_os = "linux"
        
        result_session, is_valid = session_utils.validate_create_session_request(mock_session)
        
        assert is_valid is False
        assert "missing session.software_stack_id and/or session.base_os" in result_session.failure_reason

    def test_validate_create_session_request_missing_base_os_fails(self):
        """Test that missing base_os fails validation."""
        mock_session = Mock()
        mock_session.software_stack_id = "stack-123"
        mock_session.base_os = None
        
        result_session, is_valid = session_utils.validate_create_session_request(mock_session)
        
        assert is_valid is False
        assert "missing session.software_stack_id and/or session.base_os" in result_session.failure_reason

    def test_validate_create_session_request_missing_hibernation_enabled_fails(self):
        """Test that missing hibernation_enabled fails validation."""
        mock_session = Mock()
        mock_session.hibernation_enabled = None

        result_session, is_valid = session_utils.validate_create_session_request(mock_session)

        assert is_valid is False
        assert "hibernation_enabled" in result_session.failure_reason

    @patch("api.utils.session_utils.res_projects.get_user_projects")
    def test_validate_create_session_request_user_not_in_project_fails(self, mock_get_projects):
        """Test that user not belonging to project fails validation."""
        mock_session = Mock()
        mock_session.software_stack_id = "stack-123"
        mock_session.base_os = "linux"
        mock_session.project.project_id = "proj-123"
        mock_session.owner = "testuser"
        mock_session.server.instance_profile_arn = None
        mock_get_projects.return_value = [{"project_id": "proj-456"}]
        
        result_session, is_valid = session_utils.validate_create_session_request(mock_session)
        
        assert is_valid is False
        assert "does not belong in the selected project" in result_session.failure_reason

    @patch("api.utils.session_utils.software_stacks.get_software_stack")
    @patch("api.utils.session_utils.res_projects.get_user_projects")
    def test_validate_create_session_request_invalid_software_stack_fails(self, mock_get_projects, mock_get_stack):
        """Test that invalid software stack fails validation."""
        mock_session = Mock()
        mock_session.software_stack_id = "stack-123"
        mock_session.base_os = "linux"
        mock_session.project.project_id = "proj-123"
        mock_session.owner = "testuser"
        mock_session.server.instance_profile_arn = None
        mock_get_projects.return_value = [{"project_id": "proj-123"}]
        mock_get_stack.side_effect = SoftwareStackNotFound("Stack not found")
        
        result_session, is_valid = session_utils.validate_create_session_request(mock_session)
        
        assert is_valid is False
        assert "Invalid session.software_stack.stack_id" in result_session.failure_reason

class TestValidateUpdateSessionRequest:
    """Test validate_update_session_request function"""

    @patch("api.utils.session_utils.ec2_utils.get_valid_instance_types_by_allowed_list")
    @patch("api.utils.session_utils.software_stacks.get_software_stack")
    def test_hibernation_enabled_instance_type_change_fails(self, mock_get_stack, mock_get_instance_types):
        """Test that changing instance type with hibernation enabled fails."""
        mock_session = Mock()
        mock_session.server.instance_type = "m5.large"
        
        old_session_dict = {
            res_sessions.SESSION_DB_HIBERNATION_KEY: True,
            res_sessions.SESSION_DB_SERVER_KEY: {"instance_type": "m5.xlarge"},
            res_sessions.SESSION_DB_RANGE_KEY: "session-123",
            res_sessions.SESSION_DB_STATE_KEY: "STOPPED",
            res_sessions.SESSION_DB_STACK_KEY: {
                res_sessions.SESSION_DB_BASE_OS_KEY: "linux",
                software_stacks.SOFTWARE_STACK_DB_RANGE_KEY: "stack-123"
            }
        }
        
        with pytest.raises(api_exceptions.BadRequestException) as exc_info:
            session_utils.validate_update_session_request(mock_session, old_session_dict)
        
        assert "Not allowed to change Instance type" in str(exc_info.value)
        assert "hibernation is enabled" in str(exc_info.value)

    @patch("api.utils.session_utils.ec2_utils.get_valid_instance_types_by_allowed_list")
    @patch("api.utils.session_utils.software_stacks.get_software_stack")
    def test_invalid_instance_type_fails(self, mock_get_stack, mock_get_instance_types):
        """Test that invalid instance type fails validation."""
        mock_session = Mock()
        mock_session.server.instance_type = "invalid.type"
        
        old_session_dict = {
            res_sessions.SESSION_DB_HIBERNATION_KEY: False,
            res_sessions.SESSION_DB_SERVER_KEY: {"instance_type": "m5.large"},
            res_sessions.SESSION_DB_STATE_KEY: "STOPPED",
            res_sessions.SESSION_DB_STACK_KEY: {
                res_sessions.SESSION_DB_BASE_OS_KEY: "linux",
                software_stacks.SOFTWARE_STACK_DB_RANGE_KEY: "stack-123"
            }
        }
        
        mock_get_stack.return_value = {
            software_stacks.SOFTWARE_STACK_DB_ALLOWED_INSTANCE_TYPES_KEY: ["m5.large", "m5.xlarge"]
        }
        mock_get_instance_types.return_value = {"m5.large": {}, "m5.xlarge": {}}
        
        with pytest.raises(api_exceptions.BadRequestException) as exc_info:
            session_utils.validate_update_session_request(mock_session, old_session_dict)
        
        assert "Invalid session instance type invalid.type" in str(exc_info.value)

    @patch("api.utils.session_utils.software_stacks.get_software_stack")
    def test_software_stack_not_found_fails(self, mock_get_stack):
        """Test that missing software stack fails validation."""
        mock_session = Mock()
        mock_session.server.instance_type = "m5.large"
        
        old_session_dict = {
            res_sessions.SESSION_DB_HIBERNATION_KEY: False,
            res_sessions.SESSION_DB_SERVER_KEY: {"instance_type": "m5.large"},
            res_sessions.SESSION_DB_STACK_KEY: {
                res_sessions.SESSION_DB_BASE_OS_KEY: "linux",
                software_stacks.SOFTWARE_STACK_DB_RANGE_KEY: "nonexistent-stack"
            }
        }
        
        mock_get_stack.side_effect = res_exceptions.SoftwareStackNotFound()
        
        with pytest.raises(api_exceptions.BadRequestException) as exc_info:
            session_utils.validate_update_session_request(mock_session, old_session_dict)
        
        assert "Software stack nonexistent-stack with base_os linux does not exist" in str(exc_info.value)


class TestValidateActorsForSessionPermissionRequests:
    """Tests for _validate_actors_for_session_permission_requests."""

    @staticmethod
    def _make_permission(actor_name):
        m = Mock()
        m.actor_name = actor_name
        return m

    def test_valid_unique_actors_succeed(self):
        perms = [self._make_permission("alice"), self._make_permission("bob")]
        is_valid, message = _validate_actors_for_session_permission_requests(perms)
        assert is_valid is True
        assert message == ""

    def test_duplicate_actors_fails(self):
        perms = [self._make_permission("alice"), self._make_permission("alice")]
        is_valid, message = _validate_actors_for_session_permission_requests(perms)
        assert is_valid is False
        assert "not unique" in message

    def test_invalid_actor_name_fails(self):
        perms = [self._make_permission("user;rm -rf /")]
        is_valid, message = _validate_actors_for_session_permission_requests(perms)
        assert is_valid is False
        assert "invalid characters" in message

    def test_mixed_invalid_and_duplicate_actors(self):
        perms = [
            self._make_permission("alice"),
            self._make_permission("alice"),
            self._make_permission("$(whoami)"),
        ]
        is_valid, message = _validate_actors_for_session_permission_requests(perms)
        assert is_valid is False
        assert "invalid characters" in message
        assert "not unique" in message

    def test_empty_list_fails(self):
        is_valid, message = _validate_actors_for_session_permission_requests([])
        assert is_valid is False

    def test_invalid_actor_not_reported_as_duplicate(self):
        perms = [
            self._make_permission("$(whoami)"),
            self._make_permission("$(whoami)"),
        ]
        is_valid, message = _validate_actors_for_session_permission_requests(perms)
        assert is_valid is False
        assert "invalid characters" in message
        assert "not unique" not in message
