#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import sys
import pytest
from unittest.mock import patch, Mock

# Add the backend directory to Python path to match utils import context
backend_path = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "../../../../../idea/backend",
    )
)
sys.path.insert(0, backend_path)

from api.utils import session_utils
from datamodel.models.backend.batch_operation_error_code import BatchOperationErrorCode
from datamodel.models.res_memory import ResMemory
from datamodel.models.virtual_desktop_gpu import VirtualDesktopGpu
from datamodel.models.virtual_desktop_session_type import VirtualDesktopSessionType
from res.exceptions import UserSessionNotFound


class TestValidateBatchStopSessions:
    """Tests for validate_batch_stop_sessions."""

    def _make_session(self, idea_session_id=None, owner=None):
        session = Mock()
        session.idea_session_id = idea_session_id
        session.owner = owner
        return session

    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_admin_all_sessions_validated(self, mock_is_admin, mock_get_session):
        mock_is_admin.return_value = True
        sessions = [self._make_session("s1", "user1"), self._make_session("s2", "user2")]

        validated, unsuccessful = session_utils.validate_batch_stop_sessions(sessions, "admin")

        assert len(validated) == 2
        assert len(unsuccessful) == 0
        mock_get_session.assert_not_called()

    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_non_admin_own_session_validated(self, mock_is_admin, mock_get_session):
        mock_is_admin.return_value = False
        mock_get_session.return_value = {"owner": "user1"}
        sessions = [self._make_session("s1", "user1")]

        validated, unsuccessful = session_utils.validate_batch_stop_sessions(sessions, "user1")

        assert len(validated) == 1
        assert len(unsuccessful) == 0
        mock_get_session.assert_called_once_with("user1", "s1")

    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_non_admin_other_user_session_rejected(self, mock_is_admin, mock_get_session):
        mock_is_admin.return_value = False
        mock_get_session.side_effect = UserSessionNotFound("not found")
        sessions = [self._make_session("s1", "other")]

        validated, unsuccessful = session_utils.validate_batch_stop_sessions(sessions, "user1")

        assert len(validated) == 0
        assert len(unsuccessful) == 1
        assert unsuccessful[0].error_code == BatchOperationErrorCode.FORBIDDENEXCEPTION

    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_missing_idea_session_id_added_to_unsuccessful(self, mock_is_admin, mock_get_session):
        mock_is_admin.return_value = True
        sessions = [self._make_session(None, "user1")]

        validated, unsuccessful = session_utils.validate_batch_stop_sessions(sessions, "admin")

        assert len(validated) == 0
        assert len(unsuccessful) == 1
        assert unsuccessful[0].error_code == BatchOperationErrorCode.BADREQUESTEXCEPTION

    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_unexpected_error_adds_to_unsuccessful(self, mock_is_admin, mock_get_session):
        mock_is_admin.return_value = False
        mock_get_session.side_effect = RuntimeError("DDB timeout")
        sessions = [self._make_session("s1", "user1")]

        validated, unsuccessful = session_utils.validate_batch_stop_sessions(sessions, "user1")

        assert len(validated) == 0
        assert len(unsuccessful) == 1
        assert unsuccessful[0].error_code == BatchOperationErrorCode.INTERNALSERVICEEXCEPTION

    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_mixed_valid_and_invalid_sessions(self, mock_is_admin, mock_get_session):
        mock_is_admin.return_value = False

        def side_effect(user, session_id):
            if session_id == "s1":
                return {"owner": "user1"}
            raise UserSessionNotFound("not found")

        mock_get_session.side_effect = side_effect
        sessions = [
            self._make_session("s1", "user1"),
            self._make_session("s2", "other"),
            self._make_session(None, "user1"),
        ]

        validated, unsuccessful = session_utils.validate_batch_stop_sessions(sessions, "user1")

        assert len(validated) == 1
        assert validated[0].idea_session_id == "s1"
        assert len(unsuccessful) == 2

    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_empty_sessions_list(self, mock_is_admin, mock_get_session):
        mock_is_admin.return_value = True

        validated, unsuccessful = session_utils.validate_batch_stop_sessions([], "admin")

        assert validated == []
        assert unsuccessful == []

    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_spoofed_owner_uses_authenticated_user_for_lookup(self, mock_is_admin, mock_get_session):
        mock_is_admin.return_value = False
        mock_get_session.side_effect = UserSessionNotFound("not found")
        sessions = [self._make_session("s1", "victim")]

        validated, unsuccessful = session_utils.validate_batch_stop_sessions(sessions, "attacker")

        mock_get_session.assert_called_once_with("attacker", "s1")
        assert len(unsuccessful) == 1
        assert unsuccessful[0].error_code == BatchOperationErrorCode.FORBIDDENEXCEPTION

    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_admin_override_takes_admin_path(self, mock_is_admin, mock_get_session):
        """is_app_client=True must validate every session without an admin lookup
        on the user, so service-token callers (where user is a Cognito client_id) succeed."""
        sessions = [self._make_session("s1", "user1"), self._make_session("s2", "user2")]

        validated, unsuccessful = session_utils.validate_batch_stop_sessions(
            sessions, "cm-client-id", is_app_client=True
        )

        assert len(validated) == 2
        assert len(unsuccessful) == 0
        mock_is_admin.assert_not_called()
        mock_get_session.assert_not_called()


class TestValidateBatchDeleteSessions:
    """Tests for validate_batch_delete_sessions."""

    def _make_session(self, idea_session_id=None, owner=None):
        session = Mock()
        session.idea_session_id = idea_session_id
        session.owner = owner
        return session

    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_admin_returns_ddb_session(self, mock_is_admin, mock_get_session):
        """Admin path returns VirtualDesktopSession model from DDB data, not client-provided session."""
        mock_is_admin.return_value = True
        ddb_data = {"owner": "user1", "idea_session_id": "s1", "project": {"project_id": "p1"}}
        mock_get_session.return_value = ddb_data
        sessions = [self._make_session("s1", "user1")]

        validated, unsuccessful = session_utils.validate_batch_delete_sessions(sessions, "admin")

        assert len(validated) == 1
        assert validated[0].idea_session_id == "s1"
        assert validated[0].owner == "user1"
        assert len(unsuccessful) == 0

    @patch("api.utils.session_utils.res_sessions.get_session_if_owner")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_owner_returns_ddb_session(self, mock_is_admin, mock_get_session_if_owner):
        """Own-session path returns VirtualDesktopSession model from DDB data."""
        mock_is_admin.return_value = False
        ddb_data = {"owner": "user1", "idea_session_id": "s1", "project": {"project_id": "p1"}}
        mock_get_session_if_owner.return_value = ddb_data
        sessions = [self._make_session("s1", "user1")]

        validated, unsuccessful = session_utils.validate_batch_delete_sessions(sessions, "user1")

        assert len(validated) == 1
        assert validated[0].idea_session_id == "s1"
        assert validated[0].owner == "user1"
        mock_get_session_if_owner.assert_called_once_with("user1", "s1")

    @patch("api.utils.session_utils.role_assignments.get_user_permissions")
    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.res_sessions.get_session_if_owner")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_non_owner_with_permission_returns_ddb_session(self, mock_is_admin, mock_get_session_if_owner, mock_get_session, mock_get_perms):
        """Cross-user path returns VirtualDesktopSession model from DDB data and uses DDB project_id for permission check."""
        mock_is_admin.return_value = False
        mock_get_session_if_owner.return_value = None
        ddb_data = {"owner": "other_user", "idea_session_id": "s1", "project": {"project_id": "p1"}}
        mock_get_session.return_value = ddb_data
        mock_get_perms.return_value = ["vdis.create_terminate_others_sessions"]
        sessions = [self._make_session("s1", "other_user")]

        validated, unsuccessful = session_utils.validate_batch_delete_sessions(sessions, "user1")

        assert len(validated) == 1
        assert validated[0].idea_session_id == "s1"
        assert validated[0].owner == "other_user"
        mock_get_perms.assert_called_once_with("user1", "p1:project")

    @patch("api.utils.session_utils.role_assignments.get_user_permissions")
    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.res_sessions.get_session_if_owner")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_permission_check_uses_ddb_project_not_client_provided(self, mock_is_admin, mock_get_session_if_owner, mock_get_session, mock_get_perms):
        """Permission check uses project_id from DDB, not from client request — prevents project spoofing."""
        mock_is_admin.return_value = False
        mock_get_session_if_owner.return_value = None
        # Client claims project A, but DDB says project B
        mock_get_session.return_value = {"owner": "other_user", "project": {"project_id": "real-project-B"}}
        mock_get_perms.return_value = []
        session = self._make_session("s1", "other_user")
        session.project = Mock()
        session.project.project_id = "spoofed-project-A"

        validated, unsuccessful = session_utils.validate_batch_delete_sessions([session], "user1")

        # Permission check must use DDB project_id, not client-provided
        mock_get_perms.assert_called_once_with("user1", "real-project-B:project")
        assert len(validated) == 0
        assert unsuccessful[0].error_code == BatchOperationErrorCode.FORBIDDENEXCEPTION

    @patch("api.utils.session_utils.role_assignments.get_user_permissions")
    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.res_sessions.get_session_if_owner")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_non_owner_without_permission_is_forbidden(self, mock_is_admin, mock_get_session_if_owner, mock_get_session, mock_get_perms):
        mock_is_admin.return_value = False
        mock_get_session_if_owner.return_value = None
        mock_get_session.return_value = {"owner": "other_user", "project": {"project_id": "p1"}}
        mock_get_perms.return_value = []
        sessions = [self._make_session("s1", "other_user")]

        validated, unsuccessful = session_utils.validate_batch_delete_sessions(sessions, "user1")

        assert len(validated) == 0
        assert len(unsuccessful) == 1
        assert unsuccessful[0].error_code == BatchOperationErrorCode.FORBIDDENEXCEPTION

    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_missing_session_id_and_owner(self, mock_is_admin):
        mock_is_admin.return_value = False
        sessions = [self._make_session(None, None)]

        validated, unsuccessful = session_utils.validate_batch_delete_sessions(sessions, "user1")

        assert len(validated) == 0
        assert len(unsuccessful) == 1
        assert unsuccessful[0].error_code == BatchOperationErrorCode.BADREQUESTEXCEPTION

    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_missing_owner_only(self, mock_is_admin):
        mock_is_admin.return_value = False
        sessions = [self._make_session("s1", None)]

        validated, unsuccessful = session_utils.validate_batch_delete_sessions(sessions, "user1")

        assert len(validated) == 0
        assert len(unsuccessful) == 1
        assert unsuccessful[0].error_code == BatchOperationErrorCode.BADREQUESTEXCEPTION

    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_missing_session_id_only(self, mock_is_admin):
        mock_is_admin.return_value = False
        sessions = [self._make_session(None, "user1")]

        validated, unsuccessful = session_utils.validate_batch_delete_sessions(sessions, "user1")

        assert len(validated) == 0
        assert len(unsuccessful) == 1
        assert unsuccessful[0].error_code == BatchOperationErrorCode.BADREQUESTEXCEPTION

    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.res_sessions.get_session_if_owner")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_cross_user_session_not_found_returns_forbidden(self, mock_is_admin, mock_get_session_if_owner, mock_get_session):
        """Cross-user session not found returns FORBIDDEN to avoid leaking existence."""
        mock_is_admin.return_value = False
        mock_get_session_if_owner.return_value = None
        mock_get_session.side_effect = UserSessionNotFound("not found")
        sessions = [self._make_session("s1", "other_user")]

        validated, unsuccessful = session_utils.validate_batch_delete_sessions(sessions, "user1")

        assert len(validated) == 0
        assert len(unsuccessful) == 1
        assert unsuccessful[0].error_code == BatchOperationErrorCode.FORBIDDENEXCEPTION

    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.res_sessions.get_session_if_owner")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_non_owner_session_without_project_in_ddb_returns_forbidden(self, mock_is_admin, mock_get_session_if_owner, mock_get_session):
        """Session exists in DDB but has no project — returns FORBIDDEN."""
        mock_is_admin.return_value = False
        mock_get_session_if_owner.return_value = None
        mock_get_session.return_value = {"owner": "other_user"}
        sessions = [self._make_session("s1", "other_user")]

        validated, unsuccessful = session_utils.validate_batch_delete_sessions(sessions, "user1")

        assert len(validated) == 0
        assert len(unsuccessful) == 1
        assert unsuccessful[0].error_code == BatchOperationErrorCode.FORBIDDENEXCEPTION

    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.res_sessions.get_session_if_owner")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_spoofed_owner_lookup_uses_authenticated_user_first(self, mock_is_admin, mock_get_session_if_owner, mock_get_session):
        """Non-admin own-session lookup always uses authenticated user, not client-provided owner."""
        mock_is_admin.return_value = False
        mock_get_session_if_owner.return_value = None
        mock_get_session.side_effect = UserSessionNotFound("not found")
        sessions = [self._make_session("s1", "victim")]

        validated, unsuccessful = session_utils.validate_batch_delete_sessions(sessions, "attacker")

        mock_get_session_if_owner.assert_called_once_with("attacker", "s1")
        assert len(validated) == 0
        assert len(unsuccessful) == 1
        assert unsuccessful[0].error_code == BatchOperationErrorCode.FORBIDDENEXCEPTION

    @patch("api.utils.session_utils.res_sessions.get_session_if_owner")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_mixed_sessions_partial_success(self, mock_is_admin, mock_get_session_if_owner):
        mock_is_admin.return_value = False
        ddb_data = {"owner": "user1", "idea_session_id": "s1", "project": {"project_id": "p1"}}

        def get_session_if_owner_side_effect(user, session_id):
            if session_id == "s1":
                return ddb_data
            return None

        mock_get_session_if_owner.side_effect = get_session_if_owner_side_effect
        sessions = [
            self._make_session("s1", "user1"),   # valid - own session
            self._make_session(None, None),       # invalid - missing fields
        ]

        validated, unsuccessful = session_utils.validate_batch_delete_sessions(sessions, "user1")

        assert len(validated) == 1
        assert validated[0].idea_session_id == "s1"
        assert len(unsuccessful) == 1

    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_empty_sessions_list(self, mock_is_admin, mock_get_session):
        mock_is_admin.return_value = True

        validated, unsuccessful = session_utils.validate_batch_delete_sessions([], "admin")

        assert validated == []
        assert unsuccessful == []

    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_admin_preserves_force_from_request(self, mock_is_admin, mock_get_session):
        """Force attribute from API request is preserved on validated session."""
        mock_is_admin.return_value = True
        mock_get_session.return_value = {"owner": "user1", "idea_session_id": "s1", "project": {"project_id": "p1"}}
        session = self._make_session("s1", "user1")
        session.force = True

        validated, _ = session_utils.validate_batch_delete_sessions([session], "admin")

        assert validated[0].force is True

    @patch("api.utils.session_utils.res_sessions.get_session_if_owner")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_owner_preserves_force_from_request(self, mock_is_admin, mock_get_session_if_owner):
        """Force attribute from API request is preserved on own-session path."""
        mock_is_admin.return_value = False
        mock_get_session_if_owner.return_value = {"owner": "user1", "idea_session_id": "s1", "project": {"project_id": "p1"}}
        session = self._make_session("s1", "user1")
        session.force = True

        validated, _ = session_utils.validate_batch_delete_sessions([session], "user1")

        assert validated[0].force is True

    @patch("api.utils.session_utils.role_assignments.get_user_permissions")
    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.res_sessions.get_session_if_owner")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_cross_user_preserves_force_from_request(self, mock_is_admin, mock_get_session_if_owner, mock_get_session, mock_get_perms):
        """Force attribute from API request is preserved on cross-user path."""
        mock_is_admin.return_value = False
        mock_get_session_if_owner.return_value = None
        mock_get_session.return_value = {"owner": "other_user", "idea_session_id": "s1", "project": {"project_id": "p1"}}
        mock_get_perms.return_value = ["vdis.create_terminate_others_sessions"]
        session = self._make_session("s1", "other_user")
        session.force = True

        validated, _ = session_utils.validate_batch_delete_sessions([session], "user1")

        assert validated[0].force is True

    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_admin_override_takes_admin_path(self, mock_is_admin, mock_get_session):
        """is_app_client=True must take the admin lookup path even when user
        is a Cognito client_id (service-token caller)."""
        mock_get_session.return_value = {
            "owner": "user1",
            "idea_session_id": "s1",
            "project": {"project_id": "p1"},
        }
        session = self._make_session("s1", "user1")
        session.force = True

        validated, unsuccessful = session_utils.validate_batch_delete_sessions(
            [session], "cm-client-id", is_app_client=True
        )

        assert len(validated) == 1
        assert len(unsuccessful) == 0
        # Admin path looks up via the client-provided owner, not the caller's uid
        mock_get_session.assert_called_once_with("user1", "s1")
        mock_is_admin.assert_not_called()


class TestValidateBatchStartSessions:
    """Tests for validate_batch_start_sessions."""

    def _make_session(self, idea_session_id=None, owner=None):
        session = Mock()
        session.idea_session_id = idea_session_id
        session.owner = owner
        return session

    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_admin_returns_ddb_session(self, mock_is_admin, mock_get_session):
        """Admin path returns VirtualDesktopSession model from DDB data, not client-provided session."""
        mock_is_admin.return_value = True
        ddb_data = {"owner": "user1", "idea_session_id": "s1", "state": "STOPPED", "project": {"project_id": "p1"}}
        mock_get_session.return_value = ddb_data
        sessions = [self._make_session("s1", "user1")]

        validated, unsuccessful = session_utils.validate_batch_start_sessions(sessions, "admin")

        assert len(validated) == 1
        assert validated[0].idea_session_id == "s1"
        assert validated[0].owner == "user1"
        assert len(unsuccessful) == 0

    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_admin_session_not_found(self, mock_is_admin, mock_get_session):
        mock_is_admin.return_value = True
        mock_get_session.side_effect = UserSessionNotFound("not found")
        sessions = [self._make_session("s1", "user1")]

        validated, unsuccessful = session_utils.validate_batch_start_sessions(sessions, "admin")

        assert len(validated) == 0
        assert len(unsuccessful) == 1
        assert unsuccessful[0].error_code == BatchOperationErrorCode.BADREQUESTEXCEPTION

    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_owner_returns_ddb_session(self, mock_is_admin, mock_get_session):
        """Own-session path returns VirtualDesktopSession model from DDB data."""
        mock_is_admin.return_value = False
        ddb_data = {"owner": "user1", "idea_session_id": "s1", "state": "STOPPED", "project": {"project_id": "p1"}}
        mock_get_session.return_value = ddb_data
        sessions = [self._make_session("s1", "user1")]

        validated, unsuccessful = session_utils.validate_batch_start_sessions(sessions, "user1")

        assert len(validated) == 1
        assert validated[0].idea_session_id == "s1"
        assert validated[0].owner == "user1"
        mock_get_session.assert_called_once_with("user1", "s1")

    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_non_owner_rejected_with_forbidden(self, mock_is_admin, mock_get_session):
        mock_is_admin.return_value = False
        mock_get_session.side_effect = UserSessionNotFound("not found")
        sessions = [self._make_session("s1", "other_user")]

        validated, unsuccessful = session_utils.validate_batch_start_sessions(sessions, "user1")

        assert len(validated) == 0
        assert len(unsuccessful) == 1
        assert unsuccessful[0].error_code == BatchOperationErrorCode.FORBIDDENEXCEPTION

    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_missing_session_id_and_owner(self, mock_is_admin):
        mock_is_admin.return_value = False
        sessions = [self._make_session(None, None)]

        validated, unsuccessful = session_utils.validate_batch_start_sessions(sessions, "user1")

        assert len(validated) == 0
        assert len(unsuccessful) == 1
        assert unsuccessful[0].error_code == BatchOperationErrorCode.BADREQUESTEXCEPTION

    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_missing_owner_only(self, mock_is_admin):
        mock_is_admin.return_value = False
        sessions = [self._make_session("s1", None)]

        validated, unsuccessful = session_utils.validate_batch_start_sessions(sessions, "user1")

        assert len(validated) == 0
        assert len(unsuccessful) == 1
        assert unsuccessful[0].error_code == BatchOperationErrorCode.BADREQUESTEXCEPTION

    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_unexpected_error_returns_internal_service_exception(self, mock_is_admin, mock_get_session):
        mock_is_admin.return_value = False
        mock_get_session.side_effect = RuntimeError("EC2 API failure")
        sessions = [self._make_session("s1", "user1")]

        validated, unsuccessful = session_utils.validate_batch_start_sessions(sessions, "user1")

        assert len(validated) == 0
        assert len(unsuccessful) == 1
        assert unsuccessful[0].error_code == BatchOperationErrorCode.INTERNALSERVICEEXCEPTION

    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_empty_sessions_list(self, mock_is_admin, mock_get_session):
        mock_is_admin.return_value = True

        validated, unsuccessful = session_utils.validate_batch_start_sessions([], "admin")

        assert validated == []
        assert unsuccessful == []

    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_mixed_sessions_partial_success(self, mock_is_admin, mock_get_session):
        mock_is_admin.return_value = False

        def get_session_side_effect(user, session_id):
            if session_id == "s1":
                return {"owner": "user1", "idea_session_id": "s1", "state": "STOPPED"}
            raise UserSessionNotFound("not found")

        mock_get_session.side_effect = get_session_side_effect
        sessions = [
            self._make_session("s1", "user1"),   # valid - own session
            self._make_session("s2", "user1"),   # invalid - not found
        ]

        validated, unsuccessful = session_utils.validate_batch_start_sessions(sessions, "user1")

        assert len(validated) == 1
        assert validated[0].idea_session_id == "s1"
        assert len(unsuccessful) == 1
        assert unsuccessful[0].error_code == BatchOperationErrorCode.FORBIDDENEXCEPTION

    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_spoofed_owner_lookup_uses_authenticated_user(self, mock_is_admin, mock_get_session):
        """Non-admin session lookup always uses authenticated user, not client-provided owner."""
        mock_is_admin.return_value = False
        mock_get_session.side_effect = UserSessionNotFound("not found")
        sessions = [self._make_session("s1", "victim")]

        validated, unsuccessful = session_utils.validate_batch_start_sessions(sessions, "attacker")

        mock_get_session.assert_called_once_with("attacker", "s1")
        assert len(unsuccessful) == 1
        assert unsuccessful[0].error_code == BatchOperationErrorCode.FORBIDDENEXCEPTION

    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_session_not_in_stopped_state_rejected(self, mock_is_admin, mock_get_session):
        """Session in READY state is rejected with BADREQUESTEXCEPTION."""
        mock_is_admin.return_value = True
        mock_get_session.return_value = {"owner": "user1", "idea_session_id": "s1", "state": "READY"}
        sessions = [self._make_session("s1", "user1")]

        validated, unsuccessful = session_utils.validate_batch_start_sessions(sessions, "admin")

        assert len(validated) == 0
        assert len(unsuccessful) == 1
        assert unsuccessful[0].error_code == BatchOperationErrorCode.BADREQUESTEXCEPTION
        assert "READY" in unsuccessful[0].message

    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_session_in_stopped_state_accepted(self, mock_is_admin, mock_get_session):
        """Session in STOPPED state passes validation."""
        mock_is_admin.return_value = True
        mock_get_session.return_value = {"owner": "user1", "idea_session_id": "s1", "state": "STOPPED"}
        sessions = [self._make_session("s1", "user1")]

        validated, unsuccessful = session_utils.validate_batch_start_sessions(sessions, "admin")

        assert len(validated) == 1
        assert len(unsuccessful) == 0

    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_session_in_stopped_idle_state_accepted(self, mock_is_admin, mock_get_session):
        """Session in STOPPED_IDLE state passes validation."""
        mock_is_admin.return_value = True
        mock_get_session.return_value = {"owner": "user1", "idea_session_id": "s1", "state": "STOPPED_IDLE"}
        sessions = [self._make_session("s1", "user1")]

        validated, unsuccessful = session_utils.validate_batch_start_sessions(sessions, "admin")

        assert len(validated) == 1
        assert len(unsuccessful) == 0

    @patch("api.utils.session_utils.res_sessions.get_session")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_app_client_takes_admin_path(self, mock_is_admin, mock_get_session):
        """is_app_client=True must look up the session by ``session.owner`` (not the
        authenticated user, which for service tokens is a Cognito client_id)."""
        mock_get_session.return_value = {
            "owner": "user1", "idea_session_id": "s1", "state": "STOPPED"
        }
        sessions = [self._make_session("s1", "user1")]

        validated, unsuccessful = session_utils.validate_batch_start_sessions(
            sessions, "vdc-client-id", is_app_client=True
        )

        assert len(validated) == 1
        assert len(unsuccessful) == 0
        mock_is_admin.assert_not_called()
        mock_get_session.assert_called_once_with("user1", "s1")


class TestValidateCreateSessionHibernation:
    """Tests for hibernation root volume size validation."""

    @patch("api.utils.session_utils.validate_attempt_subnets")
    @patch("api.utils.session_utils.dedicated_hosts_supported")
    @patch("api.utils.session_utils.get_gpu_manufacturer")
    @patch("api.utils.session_utils.get_instance_ram_in_mib")
    @patch("api.utils.session_utils.get_valid_instance_types_by_allowed_list")
    @patch("api.utils.session_utils.software_stacks.get_software_stack")
    @patch("api.utils.session_utils.res_projects.get_user_projects")
    @patch("api.utils.session_utils.cluster_settings.get_setting")
    def test_hibernation_min_root_volume_includes_ram(
        self,
        mock_get_setting,
        mock_get_user_projects,
        mock_get_software_stack,
        mock_get_valid_instance_types,
        mock_get_instance_ram,
        mock_get_gpu_manufacturer,
        mock_dedicated_hosts,
        mock_validate_subnets,
    ):
        """Test that min_root_volume adds instance RAM when hibernation is enabled."""
        mock_get_instance_ram.return_value = 16384.0  # 16 GiB
        mock_get_valid_instance_types.return_value = {"m6a.xlarge": {}}
        mock_get_setting.side_effect = lambda key: {
            "vdc.dcv_session.smart_retry.enabled": False,
            "vdc.dcv_session.max_root_volume_memory": 500,
        }.get(key)
        mock_get_gpu_manufacturer.return_value = VirtualDesktopGpu.NO_GPU
        mock_dedicated_hosts.return_value = False

        # Return a dict that from_ddb_dict can parse
        mock_get_software_stack.return_value = {
            "base_os": "amzn2023",
            "stack_id": "ss-test",
            "name": "Test Stack",
            "min_storage_value": "50.0",
            "min_storage_unit": "gb",
            "min_ram_value": "4.0",
            "min_ram_unit": "gb",
            "allowed_instance_types": ["m6a"],
            "projects": [{"project_id": "proj-1", "name": "proj-1"}],
        }
        mock_get_user_projects.return_value = [{"project_id": "proj-1"}]

        session = Mock()
        session.hibernation_enabled = True
        session.base_os = "amzn2023"
        session.software_stack_id = "ss-test"
        session.name = "test"
        session.owner = "testuser"
        session.type = None
        session.project = Mock()
        session.project.project_id = "proj-1"
        session.server = Mock()
        session.server.instance_type = "m6a.xlarge"
        session.server.root_volume_size = ResMemory(value=60.0, unit="gb")
        session.server.root_volume_iops = None
        session.server.instance_profile_arn = None
        session.server.security_groups = None
        session.server.subnet_id = None
        session.server.key_pair_name = None
        session.failure_reason = None

        mock_validate_subnets.return_value = (session, True)

        # min_storage (50 GB) + RAM (16384 MiB = 17.18 GB) = 67.18 GB minimum
        # root_volume_size is 60 GB which is less than 67.18 → should fail
        result_session, is_valid = session_utils.validate_create_session_request(session)

        assert not is_valid
        assert "root volume size" in result_session.failure_reason
        assert "less than the minimum" in result_session.failure_reason

    @patch("api.utils.session_utils.validate_attempt_subnets")
    @patch("api.utils.session_utils.dedicated_hosts_supported")
    @patch("api.utils.session_utils.get_gpu_manufacturer")
    @patch("api.utils.session_utils.get_instance_ram_in_mib")
    @patch("api.utils.session_utils.get_valid_instance_types_by_allowed_list")
    @patch("api.utils.session_utils.software_stacks.get_software_stack")
    @patch("api.utils.session_utils.res_projects.get_user_projects")
    @patch("api.utils.session_utils.cluster_settings.get_setting")
    def test_hibernation_min_root_volume_passes_with_enough_space(
        self,
        mock_get_setting,
        mock_get_user_projects,
        mock_get_software_stack,
        mock_get_valid_instance_types,
        mock_get_instance_ram,
        mock_get_gpu_manufacturer,
        mock_dedicated_hosts,
        mock_validate_subnets,
    ):
        """Test that validation passes when root volume is large enough for hibernation."""
        mock_get_instance_ram.return_value = 16384.0  # 16 GiB
        mock_get_valid_instance_types.return_value = {"m6a.xlarge": {}}
        mock_get_setting.side_effect = lambda key: {
            "vdc.dcv_session.smart_retry.enabled": False,
            "vdc.dcv_session.max_root_volume_memory": 500,
        }.get(key)
        mock_get_gpu_manufacturer.return_value = VirtualDesktopGpu.NO_GPU
        mock_dedicated_hosts.return_value = False

        mock_get_software_stack.return_value = {
            "base_os": "amzn2023",
            "stack_id": "ss-test",
            "name": "Test Stack",
            "min_storage_value": "50.0",
            "min_storage_unit": "gb",
            "min_ram_value": "4.0",
            "min_ram_unit": "gb",
            "allowed_instance_types": ["m6a"],
            "projects": [{"project_id": "proj-1", "name": "proj-1"}],
        }
        mock_get_user_projects.return_value = [{"project_id": "proj-1"}]

        session = Mock()
        session.hibernation_enabled = True
        session.base_os = "amzn2023"
        session.software_stack_id = "ss-test"
        session.name = "test"
        session.owner = "testuser"
        session.type = None
        session.project = Mock()
        session.project.project_id = "proj-1"
        session.server = Mock()
        session.server.instance_type = "m6a.xlarge"
        session.server.root_volume_size = ResMemory(value=100.0, unit="gb")
        session.server.root_volume_iops = None
        session.server.instance_profile_arn = None
        session.server.security_groups = None
        session.server.subnet_id = None
        session.server.key_pair_name = None
        session.failure_reason = None

        mock_validate_subnets.return_value = (session, True)

        # min_storage (50 GB) + RAM (16384 MiB = 17.18 GB) = 67.18 GB minimum
        # root_volume_size is 100 GB which is more than 67.18 → should pass
        result_session, is_valid = session_utils.validate_create_session_request(session)

        assert is_valid

    def _setup_windows_hibernation_mocks(
        self,
        ram_mib,
        instance_type,
        mock_get_setting,
        mock_get_user_projects,
        mock_get_software_stack,
        mock_get_valid_instance_types,
        mock_get_instance_ram,
        mock_get_gpu_manufacturer,
        mock_dedicated_hosts,
        mock_validate_subnets,
    ):
        """Build a session + configure mocks for Windows hibernation RAM-limit tests."""
        mock_get_instance_ram.return_value = ram_mib
        mock_get_valid_instance_types.return_value = {instance_type: {}}
        mock_get_setting.side_effect = lambda key: {
            "vdc.dcv_session.smart_retry.enabled": False,
            "vdc.dcv_session.max_root_volume_memory": 500,
        }.get(key)
        mock_get_gpu_manufacturer.return_value = VirtualDesktopGpu.NO_GPU
        mock_dedicated_hosts.return_value = False
        mock_get_software_stack.return_value = {
            "base_os": "windows",
            "stack_id": "ss-test",
            "name": "Test Stack",
            "min_storage_value": "50.0",
            "min_storage_unit": "gb",
            "min_ram_value": "4.0",
            "min_ram_unit": "gb",
            "allowed_instance_types": ["m6a"],
            "projects": [{"project_id": "proj-1", "name": "proj-1"}],
        }
        mock_get_user_projects.return_value = [{"project_id": "proj-1"}]

        session = Mock()
        session.hibernation_enabled = True
        session.base_os = "windows"
        session.software_stack_id = "ss-test"
        session.name = "test"
        session.owner = "testuser"
        session.type = None
        session.project = Mock()
        session.project.project_id = "proj-1"
        session.server = Mock()
        session.server.instance_type = instance_type
        session.server.root_volume_size = ResMemory(value=200.0, unit="gb")
        session.server.root_volume_iops = None
        session.server.instance_profile_arn = None
        session.server.security_groups = None
        session.server.subnet_id = None
        session.server.key_pair_name = None
        session.failure_reason = None

        mock_validate_subnets.return_value = (session, True)
        return session

    @patch("api.utils.session_utils.validate_attempt_subnets")
    @patch("api.utils.session_utils.dedicated_hosts_supported")
    @patch("api.utils.session_utils.get_gpu_manufacturer")
    @patch("api.utils.session_utils.get_instance_ram_in_mib")
    @patch("api.utils.session_utils.get_valid_instance_types_by_allowed_list")
    @patch("api.utils.session_utils.software_stacks.get_software_stack")
    @patch("api.utils.session_utils.res_projects.get_user_projects")
    @patch("api.utils.session_utils.cluster_settings.get_setting")
    def test_windows_hibernation_rejects_high_ram_instance(
        self,
        mock_get_setting,
        mock_get_user_projects,
        mock_get_software_stack,
        mock_get_valid_instance_types,
        mock_get_instance_ram,
        mock_get_gpu_manufacturer,
        mock_dedicated_hosts,
        mock_validate_subnets,
    ):
        """Windows hibernation must fail when instance RAM exceeds the 16 GiB limit."""
        session = self._setup_windows_hibernation_mocks(
            32768.0, "m6a.2xlarge",  # 32 GiB > 16 GiB limit
            mock_get_setting, mock_get_user_projects, mock_get_software_stack,
            mock_get_valid_instance_types, mock_get_instance_ram,
            mock_get_gpu_manufacturer, mock_dedicated_hosts, mock_validate_subnets,
        )

        result_session, is_valid = session_utils.validate_create_session_request(session)

        assert not is_valid
        assert "Hibernation" in result_session.failure_reason
        assert "RAM greater than" in result_session.failure_reason

    @patch("api.utils.session_utils.validate_attempt_subnets")
    @patch("api.utils.session_utils.dedicated_hosts_supported")
    @patch("api.utils.session_utils.get_gpu_manufacturer")
    @patch("api.utils.session_utils.get_instance_ram_in_mib")
    @patch("api.utils.session_utils.get_valid_instance_types_by_allowed_list")
    @patch("api.utils.session_utils.software_stacks.get_software_stack")
    @patch("api.utils.session_utils.res_projects.get_user_projects")
    @patch("api.utils.session_utils.cluster_settings.get_setting")
    def test_windows_hibernation_passes_below_ram_limit(
        self,
        mock_get_setting,
        mock_get_user_projects,
        mock_get_software_stack,
        mock_get_valid_instance_types,
        mock_get_instance_ram,
        mock_get_gpu_manufacturer,
        mock_dedicated_hosts,
        mock_validate_subnets,
    ):
        """Windows hibernation must pass when instance RAM is below the limit."""
        session = self._setup_windows_hibernation_mocks(
            8192.0, "m6a.large",  # 8 GiB, well under limit
            mock_get_setting, mock_get_user_projects, mock_get_software_stack,
            mock_get_valid_instance_types, mock_get_instance_ram,
            mock_get_gpu_manufacturer, mock_dedicated_hosts, mock_validate_subnets,
        )

        _, is_valid = session_utils.validate_create_session_request(session)

        assert is_valid


class TestValidateCreateSessionDisabledProject:
    """Tests for disabled project validation in create session."""

    @patch("api.utils.session_utils.cluster_settings.get_setting")
    @patch("api.utils.session_utils.res_projects.get_user_projects")
    def test_disabled_project_rejected(
        self,
        mock_get_user_projects,
        mock_get_setting,
    ):
        """Session creation fails when the user's project is disabled."""
        mock_get_setting.side_effect = lambda key: {
            "vdc.dcv_session.smart_retry.enabled": False,
        }.get(key)
        mock_get_user_projects.return_value = [
            {"project_id": "proj-disabled", "enabled": False}
        ]

        session = Mock()
        session.hibernation_enabled = False
        session.base_os = "amzn2023"
        session.software_stack_id = "ss-test"
        session.name = "test"
        session.owner = "testuser"
        session.type = None
        session.project = Mock()
        session.project.project_id = "proj-disabled"
        session.server = Mock()
        session.server.instance_type = "t3.medium"
        session.server.root_volume_size = ResMemory(value=50.0, unit="gb")
        session.server.instance_profile_arn = None
        session.failure_reason = None

        result_session, is_valid = session_utils.validate_create_session_request(session)

        assert not is_valid
        assert "is disabled" in result_session.failure_reason
        assert "proj-disabled" in result_session.failure_reason

    @patch("api.utils.session_utils.cluster_settings.get_setting")
    @patch("api.utils.session_utils.software_stacks.get_software_stack")
    @patch("api.utils.session_utils.res_projects.get_user_projects")
    @patch("api.utils.session_utils.get_valid_instance_types_by_allowed_list")
    @patch("api.utils.session_utils.get_instance_ram_in_mib")
    @patch("api.utils.session_utils.get_gpu_manufacturer")
    @patch("api.utils.session_utils.dedicated_hosts_supported")
    @patch("api.utils.session_utils.validate_attempt_subnets")
    def test_enabled_project_allowed(
        self,
        mock_validate_subnets,
        mock_dedicated_hosts,
        mock_get_gpu_manufacturer,
        mock_get_instance_ram,
        mock_get_valid_instance_types,
        mock_get_user_projects,
        mock_get_software_stack,
        mock_get_setting,
    ):
        """Session creation proceeds when the user's project is enabled."""
        mock_get_setting.side_effect = lambda key: {
            "vdc.dcv_session.smart_retry.enabled": False,
            "vdc.dcv_session.max_root_volume_memory": 500,
        }.get(key)
        mock_get_instance_ram.return_value = 8192.0
        mock_get_valid_instance_types.return_value = {"t3.medium": {}}
        mock_get_gpu_manufacturer.return_value = VirtualDesktopGpu.NO_GPU
        mock_dedicated_hosts.return_value = False
        mock_validate_subnets.return_value = (Mock(), True)

        mock_get_user_projects.return_value = [
            {"project_id": "proj-1", "enabled": True}
        ]
        mock_get_software_stack.return_value = {
            "base_os": "amzn2023",
            "stack_id": "ss-test",
            "name": "Test Stack",
            "min_storage_value": "50.0",
            "min_storage_unit": "gb",
            "min_ram_value": "4.0",
            "min_ram_unit": "gb",
            "allowed_instance_types": ["t3"],
            "projects": [{"project_id": "proj-1", "name": "proj-1"}],
        }

        session = Mock()
        session.hibernation_enabled = False
        session.base_os = "amzn2023"
        session.software_stack_id = "ss-test"
        session.name = "test"
        session.owner = "testuser"
        session.type = None
        session.project = Mock()
        session.project.project_id = "proj-1"
        session.server = Mock()
        session.server.instance_type = "t3.medium"
        session.server.root_volume_size = ResMemory(value=50.0, unit="gb")
        session.server.root_volume_iops = None
        session.server.instance_profile_arn = None
        session.server.security_groups = None
        session.server.subnet_id = None
        session.server.key_pair_name = None
        session.failure_reason = None
        session.tags = None

        mock_validate_subnets.return_value = (session, True)

        _, is_valid = session_utils.validate_create_session_request(session)

        assert is_valid


class TestValidateCreateSessionDisabledGroup:
    """Tests for disabled group validation in create session.

    When a user's only project access is through a disabled group,
    list_role_assignments_for_user_and_groups (called by get_user_projects)
    filters out that group's assignments. As a result, get_user_projects
    won't return the project, and validate_create_session_request rejects
    with 'does not belong'.
    """

    @patch("api.utils.session_utils.cluster_settings.get_setting")
    @patch("api.utils.session_utils.res_projects.get_user_projects")
    def test_disabled_group_only_access_rejected(
        self,
        mock_get_user_projects,
        mock_get_setting,
    ):
        """Session creation fails when user's only project access is through a disabled group."""
        mock_get_setting.side_effect = lambda key: {
            "vdc.dcv_session.smart_retry.enabled": False,
        }.get(key)
        # Simulates the result after role_assignments filters out disabled group
        mock_get_user_projects.return_value = []

        session = Mock()
        session.hibernation_enabled = False
        session.base_os = "amzn2023"
        session.software_stack_id = "ss-test"
        session.name = "test"
        session.owner = "testuser"
        session.type = None
        session.project = Mock()
        session.project.project_id = "proj-1"
        session.server = Mock()
        session.server.instance_type = "t3.medium"
        session.server.root_volume_size = ResMemory(value=50.0, unit="gb")
        session.server.instance_profile_arn = None
        session.failure_reason = None

        result_session, is_valid = session_utils.validate_create_session_request(session)

        assert not is_valid
        assert "does not belong" in result_session.failure_reason


class TestValidateCreateSessionSoftwareStackEnabled:
    """Tests for software stack enabled validation in create session."""

    @patch("api.utils.session_utils.cluster_settings.get_setting")
    @patch("api.utils.session_utils.software_stacks.get_software_stack")
    @patch("api.utils.session_utils.res_projects.get_user_projects")
    def test_disabled_software_stack_rejected(
        self,
        mock_get_user_projects,
        mock_get_software_stack,
        mock_get_setting,
    ):
        mock_get_setting.side_effect = lambda key: {
            "vdc.dcv_session.smart_retry.enabled": False,
        }.get(key)
        mock_get_user_projects.return_value = [{"project_id": "proj-1"}]
        mock_get_software_stack.return_value = {
            "base_os": "amzn2023",
            "stack_id": "ss-disabled",
            "name": "Disabled Stack",
            "enabled": False,
            "min_storage_value": "50.0",
            "min_storage_unit": "gb",
            "min_ram_value": "4.0",
            "min_ram_unit": "gb",
            "projects": [{"project_id": "proj-1", "name": "proj-1"}],
        }

        session = Mock()
        session.hibernation_enabled = False
        session.base_os = "amzn2023"
        session.software_stack_id = "ss-disabled"
        session.name = "test"
        session.owner = "testuser"
        session.type = None
        session.project = Mock()
        session.project.project_id = "proj-1"
        session.server = Mock()
        session.server.instance_type = "t3.medium"
        session.server.root_volume_size = ResMemory(value=50.0, unit="gb")
        session.server.instance_profile_arn = None
        session.failure_reason = None

        result_session, is_valid = session_utils.validate_create_session_request(session)

        assert not is_valid
        assert "not available" in result_session.failure_reason

    @patch("api.utils.session_utils.software_stacks.get_software_stack")
    @patch("api.utils.session_utils.res_projects.get_user_projects")
    @patch("api.utils.session_utils.cluster_settings.get_setting")
    @patch("api.utils.session_utils.get_valid_instance_types_by_allowed_list")
    @patch("api.utils.session_utils.get_instance_ram_in_mib")
    @patch("api.utils.session_utils.get_gpu_manufacturer")
    @patch("api.utils.session_utils.dedicated_hosts_supported")
    @patch("api.utils.session_utils.validate_attempt_subnets")
    def test_none_enabled_software_stack_allowed(
        self,
        mock_validate_subnets,
        mock_dedicated_hosts,
        mock_get_gpu_manufacturer,
        mock_get_instance_ram,
        mock_get_valid_instance_types,
        mock_get_setting,
        mock_get_user_projects,
        mock_get_software_stack,
    ):
        mock_get_user_projects.return_value = [{"project_id": "proj-1"}]
        mock_get_software_stack.return_value = {
            "base_os": "amzn2023",
            "stack_id": "ss-none-enabled",
            "name": "None Enabled Stack",
            "min_storage_value": "50.0",
            "min_storage_unit": "gb",
            "min_ram_value": "4.0",
            "min_ram_unit": "gb",
            "allowed_instance_types": ["t3"],
            "projects": [{"project_id": "proj-1", "name": "proj-1"}],
        }
        mock_get_setting.side_effect = lambda key: {
            "vdc.dcv_session.smart_retry.enabled": False,
            "vdc.dcv_session.max_root_volume_memory": 500,
        }.get(key)
        mock_get_valid_instance_types.return_value = {"t3.medium": {}}
        mock_get_instance_ram.return_value = 4096.0
        mock_get_gpu_manufacturer.return_value = VirtualDesktopGpu.NO_GPU
        mock_dedicated_hosts.return_value = False

        session = Mock()
        session.hibernation_enabled = False
        session.base_os = "amzn2023"
        session.software_stack_id = "ss-none-enabled"
        session.name = "test"
        session.owner = "testuser"
        session.type = None
        session.project = Mock()
        session.project.project_id = "proj-1"
        session.server = Mock()
        session.server.instance_type = "t3.medium"
        session.server.root_volume_size = ResMemory(value=50.0, unit="gb")
        session.server.root_volume_iops = None
        session.server.instance_profile_arn = None
        session.server.security_groups = None
        session.server.subnet_id = None
        session.server.key_pair_name = None
        session.failure_reason = None

        mock_validate_subnets.return_value = (session, True)

        result_session, is_valid = session_utils.validate_create_session_request(session)

        assert is_valid



class TestValidateCreateSessionSmartRetry:
    """Tests for smart_retry-specific validation branches in validate_create_session_request."""

    def _setup_smart_retry_mocks(
        self,
        mock_get_setting,
        mock_get_user_projects,
        mock_get_software_stack,
        mock_get_valid_instance_types,
        mock_get_instance_ram,
        mock_get_gpu_manufacturer,
        mock_dedicated_hosts,
        mock_validate_subnets,
        hibernation_enabled=False,
        instance_type=None,
        subnet_id=None,
        root_volume_gb=100.0,
        allowed_instance_types=None,
        valid_instance_types=None,
        ram_mib=8192.0,
    ):
        """Build a session + configure mocks for smart-retry tests."""
        mock_get_instance_ram.return_value = ram_mib
        mock_get_valid_instance_types.return_value = (
            valid_instance_types if valid_instance_types is not None else {"m6a.large": {}}
        )
        mock_get_setting.side_effect = lambda key: {
            "vdc.dcv_session.smart_retry.enabled": True,
            "vdc.dcv_session.max_root_volume_memory": 500,
        }.get(key)
        mock_get_gpu_manufacturer.return_value = VirtualDesktopGpu.NO_GPU
        mock_dedicated_hosts.return_value = False
        mock_get_software_stack.return_value = {
            "base_os": "amzn2023",
            "stack_id": "ss-test",
            "name": "Test Stack",
            "min_storage_value": "50.0",
            "min_storage_unit": "gb",
            "min_ram_value": "4.0",
            "min_ram_unit": "gb",
            "allowed_instance_types": allowed_instance_types or ["m6a"],
            "projects": [{"project_id": "proj-1", "name": "proj-1"}],
        }
        mock_get_user_projects.return_value = [{"project_id": "proj-1"}]

        session = Mock()
        session.hibernation_enabled = hibernation_enabled
        session.base_os = "amzn2023"
        session.software_stack_id = "ss-test"
        session.name = "test"
        session.owner = "testuser"
        session.type = None
        session.project = Mock()
        session.project.project_id = "proj-1"
        session.server = Mock()
        session.server.instance_type = instance_type
        session.server.root_volume_size = ResMemory(value=root_volume_gb, unit="gb")
        session.server.root_volume_iops = None
        session.server.instance_profile_arn = None
        session.server.security_groups = None
        session.server.subnet_id = subnet_id
        session.server.key_pair_name = None
        session.failure_reason = None

        mock_validate_subnets.return_value = (session, True)
        return session

    @patch("api.utils.session_utils.validate_attempt_subnets")
    @patch("api.utils.session_utils.dedicated_hosts_supported")
    @patch("api.utils.session_utils.get_gpu_manufacturer")
    @patch("api.utils.session_utils.get_instance_ram_in_mib")
    @patch("api.utils.session_utils.get_valid_instance_types_by_allowed_list")
    @patch("api.utils.session_utils.software_stacks.get_software_stack")
    @patch("api.utils.session_utils.res_projects.get_user_projects")
    @patch("api.utils.session_utils.cluster_settings.get_setting")
    def test_smart_retry_rejects_client_provided_instance_type(
        self,
        mock_get_setting,
        mock_get_user_projects,
        mock_get_software_stack,
        mock_get_valid_instance_types,
        mock_get_instance_ram,
        mock_get_gpu_manufacturer,
        mock_dedicated_hosts,
        mock_validate_subnets,
    ):
        """Smart retry must reject requests that pin instance_type — the retry loop chooses it."""
        session = self._setup_smart_retry_mocks(
            mock_get_setting, mock_get_user_projects, mock_get_software_stack,
            mock_get_valid_instance_types, mock_get_instance_ram,
            mock_get_gpu_manufacturer, mock_dedicated_hosts, mock_validate_subnets,
            instance_type="t3.medium",
        )

        result_session, is_valid = session_utils.validate_create_session_request(session)

        assert not is_valid
        assert "instance_type" in result_session.failure_reason
        assert "Smart Retry" in result_session.failure_reason

    @patch("api.utils.session_utils.validate_attempt_subnets")
    @patch("api.utils.session_utils.dedicated_hosts_supported")
    @patch("api.utils.session_utils.get_gpu_manufacturer")
    @patch("api.utils.session_utils.get_instance_ram_in_mib")
    @patch("api.utils.session_utils.get_valid_instance_types_by_allowed_list")
    @patch("api.utils.session_utils.software_stacks.get_software_stack")
    @patch("api.utils.session_utils.res_projects.get_user_projects")
    @patch("api.utils.session_utils.cluster_settings.get_setting")
    def test_smart_retry_rejects_client_provided_subnet_id(
        self,
        mock_get_setting,
        mock_get_user_projects,
        mock_get_software_stack,
        mock_get_valid_instance_types,
        mock_get_instance_ram,
        mock_get_gpu_manufacturer,
        mock_dedicated_hosts,
        mock_validate_subnets,
    ):
        """Smart retry must reject requests that pin subnet_id — the retry loop chooses it."""
        session = self._setup_smart_retry_mocks(
            mock_get_setting, mock_get_user_projects, mock_get_software_stack,
            mock_get_valid_instance_types, mock_get_instance_ram,
            mock_get_gpu_manufacturer, mock_dedicated_hosts, mock_validate_subnets,
            subnet_id="subnet-aaa",
        )

        result_session, is_valid = session_utils.validate_create_session_request(session)

        assert not is_valid
        assert "subnet_id" in result_session.failure_reason
        assert "Smart Retry" in result_session.failure_reason

    @patch("api.utils.session_utils.validate_attempt_subnets")
    @patch("api.utils.session_utils.dedicated_hosts_supported")
    @patch("api.utils.session_utils.get_gpu_manufacturer")
    @patch("api.utils.session_utils.get_instance_ram_in_mib")
    @patch("api.utils.session_utils.get_valid_instance_types_by_allowed_list")
    @patch("api.utils.session_utils.software_stacks.get_software_stack")
    @patch("api.utils.session_utils.res_projects.get_user_projects")
    @patch("api.utils.session_utils.cluster_settings.get_setting")
    def test_smart_retry_accepts_missing_instance_type(
        self,
        mock_get_setting,
        mock_get_user_projects,
        mock_get_software_stack,
        mock_get_valid_instance_types,
        mock_get_instance_ram,
        mock_get_gpu_manufacturer,
        mock_dedicated_hosts,
        mock_validate_subnets,
    ):
        """Under smart retry the client MUST NOT set instance_type — validator skips the check."""
        session = self._setup_smart_retry_mocks(
            mock_get_setting, mock_get_user_projects, mock_get_software_stack,
            mock_get_valid_instance_types, mock_get_instance_ram,
            mock_get_gpu_manufacturer, mock_dedicated_hosts, mock_validate_subnets,
        )

        _, is_valid = session_utils.validate_create_session_request(session)

        assert is_valid

    @patch("api.utils.session_utils.validate_attempt_subnets")
    @patch("api.utils.session_utils.dedicated_hosts_supported")
    @patch("api.utils.session_utils.get_gpu_manufacturer")
    @patch("api.utils.session_utils.get_instance_ram_in_mib")
    @patch("api.utils.session_utils.get_valid_instance_types_by_allowed_list")
    @patch("api.utils.session_utils.software_stacks.get_software_stack")
    @patch("api.utils.session_utils.res_projects.get_user_projects")
    @patch("api.utils.session_utils.cluster_settings.get_setting")
    def test_smart_retry_hibernation_rejects_stack_with_no_hibernation_capable_type(
        self,
        mock_get_setting,
        mock_get_user_projects,
        mock_get_software_stack,
        mock_get_valid_instance_types,
        mock_get_instance_ram,
        mock_get_gpu_manufacturer,
        mock_dedicated_hosts,
        mock_validate_subnets,
    ):
        """If none of allowed_instance_types support hibernation, reject at API layer."""
        session = self._setup_smart_retry_mocks(
            mock_get_setting, mock_get_user_projects, mock_get_software_stack,
            mock_get_valid_instance_types, mock_get_instance_ram,
            mock_get_gpu_manufacturer, mock_dedicated_hosts, mock_validate_subnets,
            hibernation_enabled=True,
            allowed_instance_types=["t2"],
            valid_instance_types={},
        )

        result_session, is_valid = session_utils.validate_create_session_request(session)

        assert not is_valid
        assert "No hibernation-capable instance type" in result_session.failure_reason

    @patch("api.utils.session_utils.validate_attempt_subnets")
    @patch("api.utils.session_utils.dedicated_hosts_supported")
    @patch("api.utils.session_utils.get_gpu_manufacturer")
    @patch("api.utils.session_utils.get_instance_ram_in_mib")
    @patch("api.utils.session_utils.get_valid_instance_types_by_allowed_list")
    @patch("api.utils.session_utils.software_stacks.get_software_stack")
    @patch("api.utils.session_utils.res_projects.get_user_projects")
    @patch("api.utils.session_utils.cluster_settings.get_setting")
    def test_smart_retry_hibernation_rejects_root_volume_too_small_for_smallest_type(
        self,
        mock_get_setting,
        mock_get_user_projects,
        mock_get_software_stack,
        mock_get_valid_instance_types,
        mock_get_instance_ram,
        mock_get_gpu_manufacturer,
        mock_dedicated_hosts,
        mock_validate_subnets,
    ):
        """Root volume must hold at least the smallest hibernation-capable type's RAM."""
        # 50 GB min_storage + ~8.59 GB (8192 MiB) → ~58.59 GB minimum. 55 GB fails.
        session = self._setup_smart_retry_mocks(
            mock_get_setting, mock_get_user_projects, mock_get_software_stack,
            mock_get_valid_instance_types, mock_get_instance_ram,
            mock_get_gpu_manufacturer, mock_dedicated_hosts, mock_validate_subnets,
            hibernation_enabled=True,
            root_volume_gb=55.0,
            valid_instance_types={"m6a.large": {}, "m6a.xlarge": {}},
            ram_mib=8192.0,
        )

        result_session, is_valid = session_utils.validate_create_session_request(session)

        assert not is_valid
        assert "root volume size" in result_session.failure_reason
        assert "smallest hibernation-capable" in result_session.failure_reason

    @patch("api.utils.session_utils.validate_attempt_subnets")
    @patch("api.utils.session_utils.dedicated_hosts_supported")
    @patch("api.utils.session_utils.get_gpu_manufacturer")
    @patch("api.utils.session_utils.get_instance_ram_in_mib")
    @patch("api.utils.session_utils.get_valid_instance_types_by_allowed_list")
    @patch("api.utils.session_utils.software_stacks.get_software_stack")
    @patch("api.utils.session_utils.res_projects.get_user_projects")
    @patch("api.utils.session_utils.cluster_settings.get_setting")
    def test_smart_retry_hibernation_passes_when_root_volume_holds_smallest_type_ram(
        self,
        mock_get_setting,
        mock_get_user_projects,
        mock_get_software_stack,
        mock_get_valid_instance_types,
        mock_get_instance_ram,
        mock_get_gpu_manufacturer,
        mock_dedicated_hosts,
        mock_validate_subnets,
    ):
        """Root volume >= min_storage + smallest hibernation-capable type's RAM passes."""
        # 50 GB min_storage + ~8.59 GB RAM = ~58.59 GB minimum; 100 GB passes.
        session = self._setup_smart_retry_mocks(
            mock_get_setting, mock_get_user_projects, mock_get_software_stack,
            mock_get_valid_instance_types, mock_get_instance_ram,
            mock_get_gpu_manufacturer, mock_dedicated_hosts, mock_validate_subnets,
            hibernation_enabled=True,
            root_volume_gb=100.0,
            valid_instance_types={"m6a.large": {}},
            ram_mib=8192.0,
        )

        _, is_valid = session_utils.validate_create_session_request(session)

        assert is_valid


class TestCompleteCreateSessionRequest:
    """Tests for complete_create_session_request."""

    @patch("api.utils.session_utils.cluster_settings.get_setting")
    def test_defaults_session_type_to_console(self, mock_get_setting):
        """Post-migration the session type is always CONSOLE (VIRTUAL is rejected upstream)."""
        mock_get_setting.side_effect = lambda key: {
            "vdc.dcv_host_instance_profile_arn": "arn:aws:iam::123:instance-profile/vdi-host",
            "vdc.dcv_host_security_group_id": "sg-123",
            "vdc.dcv_session.additional_security_groups": [],
            "cluster.network.ssh_key_pair": "test-key",
        }.get(key)

        session = Mock()
        session.name = "test"
        session.type = None
        session.server = Mock()
        session.server.root_volume_iops = None
        session.server.key_pair_name = None
        session.server.security_groups = None
        session.project = Mock()
        session.project.name = "proj-1"
        session.project.policy_arns = None
        session.project.security_groups = None

        result = session_utils.complete_create_session_request(session, "user1")

        assert result.type == VirtualDesktopSessionType.CONSOLE
        assert result.server.key_pair_name == "test-key"

    @patch("api.utils.session_utils.cluster_settings.get_setting")
    def test_key_pair_defaults_from_cluster_settings_when_not_provided(self, mock_get_setting):
        """When session.server.key_pair_name is None, it should default from cluster settings."""
        mock_get_setting.side_effect = lambda key: {
            "vdc.dcv_host_instance_profile_arn": "arn:aws:iam::123:instance-profile/vdi-host",
            "vdc.dcv_host_security_group_id": "sg-123",
            "vdc.dcv_session.additional_security_groups": [],
            "cluster.network.ssh_key_pair": "my-keypair",
        }.get(key)

        session = Mock()
        session.name = "test"
        session.type = None
        session.server = Mock()
        session.server.root_volume_iops = None
        session.server.key_pair_name = None
        session.server.security_groups = None
        session.project = Mock()
        session.project.name = "proj-1"
        session.project.policy_arns = None
        session.project.security_groups = None

        result = session_utils.complete_create_session_request(session, "user1")

        assert result.server.key_pair_name == "my-keypair"

    @patch("api.utils.session_utils.cluster_settings.get_setting")
    def test_key_pair_not_overridden_when_already_set(self, mock_get_setting):
        """When session.server.key_pair_name is already set, it should NOT be overridden."""
        mock_get_setting.side_effect = lambda key: {
            "vdc.dcv_host_instance_profile_arn": "arn:aws:iam::123:instance-profile/vdi-host",
            "vdc.dcv_host_security_group_id": "sg-123",
            "vdc.dcv_session.additional_security_groups": [],
            "cluster.network.ssh_key_pair": "cluster-default-key",
        }.get(key)

        session = Mock()
        session.name = "test"
        session.type = None
        session.server = Mock()
        session.server.root_volume_iops = None
        session.server.key_pair_name = "user-provided-key"
        session.server.security_groups = None
        session.project = Mock()
        session.project.name = "proj-1"
        session.project.policy_arns = None
        session.project.security_groups = None

        result = session_utils.complete_create_session_request(session, "user1")

        assert result.server.key_pair_name == "user-provided-key"


class TestValidateBatchCreateSessions:
    """Tests for validate_batch_create_sessions."""

    def _make_session(self, owner=None, failure_reason=None, project_id=None):
        session = Mock()
        session.owner = owner
        session.failure_reason = failure_reason
        if project_id:
            session.project = Mock()
            session.project.project_id = project_id
        else:
            session.project = None
        return session

    @patch("api.utils.session_utils._validate_create_session_request")
    def test_all_sessions_valid(self, mock_validate):
        sessions = [self._make_session("user1"), self._make_session("user2")]
        mock_validate.side_effect = [(sessions[0], True), (sessions[1], True)]

        validated, unsuccessful = session_utils.validate_batch_create_sessions(sessions, "admin")

        assert len(validated) == 2
        assert len(unsuccessful) == 0

    @patch("api.utils.session_utils._validate_create_session_request")
    def test_all_sessions_invalid(self, mock_validate):
        s1 = self._make_session("user1")
        s1.failure_reason = "missing field"
        s2 = self._make_session("user2")
        s2.failure_reason = "bad project"
        mock_validate.side_effect = [(s1, False), (s2, False)]

        validated, unsuccessful = session_utils.validate_batch_create_sessions([s1, s2], "admin")

        assert len(validated) == 0
        assert len(unsuccessful) == 2
        assert unsuccessful[0].error_code == BatchOperationErrorCode.BADREQUESTEXCEPTION
        assert unsuccessful[0].message == "missing field"

    @patch("api.utils.session_utils._validate_create_session_request")
    def test_mixed_valid_and_invalid(self, mock_validate):
        s1 = self._make_session("user1")
        s2 = self._make_session("user2")
        s2.failure_reason = "invalid instance type"
        mock_validate.side_effect = [(s1, True), (s2, False)]

        validated, unsuccessful = session_utils.validate_batch_create_sessions([s1, s2], "admin")

        assert len(validated) == 1
        assert len(unsuccessful) == 1

    @patch("api.utils.session_utils._validate_create_session_request")
    def test_owner_defaults_to_user_when_none(self, mock_validate):
        session = self._make_session(owner=None)
        mock_validate.return_value = (session, True)

        session_utils.validate_batch_create_sessions([session], "caller_user")

        assert session.owner == "caller_user"

    @patch("api.utils.session_utils._validate_create_session_request")
    def test_pending_count_increments_for_same_owner_and_project(self, mock_validate):
        """Verify that validated sessions in the same batch increment pending_count to prevent limit bypass."""
        s1 = self._make_session("user1", project_id="proj-1")
        s2 = self._make_session("user1", project_id="proj-1")
        s3 = self._make_session("user1", project_id="proj-1")
        mock_validate.side_effect = [(s1, True), (s2, True), (s3, True)]

        session_utils.validate_batch_create_sessions([s1, s2, s3], "user1")

        calls = mock_validate.call_args_list
        assert calls[0].kwargs["pending_count"] == 0
        assert calls[1].kwargs["pending_count"] == 1
        assert calls[2].kwargs["pending_count"] == 2

    @patch("api.utils.session_utils._validate_create_session_request")
    def test_pending_count_independent_across_projects(self, mock_validate):
        """Verify pending_count is tracked per (owner, project) independently."""
        s1 = self._make_session("user1", project_id="proj-1")
        s2 = self._make_session("user1", project_id="proj-2")
        mock_validate.side_effect = [(s1, True), (s2, True)]

        session_utils.validate_batch_create_sessions([s1, s2], "user1")

        calls = mock_validate.call_args_list
        assert calls[0].kwargs["pending_count"] == 0
        assert calls[1].kwargs["pending_count"] == 0

    @patch("api.utils.session_utils._validate_create_session_request")
    def test_failed_session_does_not_increment_pending_count(self, mock_validate):
        """Verify a failed session doesn't inflate pending_count for subsequent sessions."""
        s1 = self._make_session("user1", project_id="proj-1")
        s2 = self._make_session("user1", project_id="proj-1", failure_reason="bad instance type")
        s3 = self._make_session("user1", project_id="proj-1")
        mock_validate.side_effect = [(s1, True), (s2, False), (s3, True)]

        validated, unsuccessful = session_utils.validate_batch_create_sessions([s1, s2, s3], "user1")

        calls = mock_validate.call_args_list
        assert calls[0].kwargs["pending_count"] == 0
        assert calls[1].kwargs["pending_count"] == 1
        assert calls[2].kwargs["pending_count"] == 1  # NOT 2 — failed session didn't increment
        assert len(validated) == 2
        assert len(unsuccessful) == 1

    @patch("api.utils.session_utils.validate_create_session_request")
    @patch("api.utils.session_utils.accounts.is_active_admin")
    def test_app_client_skips_owner_validation(self, mock_is_admin, mock_validate_request):
        """is_app_client=True takes the admin path without calling is_active_admin."""
        session = self._make_session("other_user", project_id="proj-1")
        mock_validate_request.return_value = (session, True)

        session_utils.validate_batch_create_sessions([session], "caller_user", is_app_client=True)

        mock_is_admin.assert_not_called()
        mock_validate_request.assert_called_once()


class TestValidateAttemptSubnets:
    """Tests for validate_attempt_subnets subnet_id validation."""

    @patch("api.utils.session_utils.cluster_settings.get_setting")
    def test_valid_subnet_in_vdi_subnets_accepted(self, mock_get_setting):
        """Test that a user-provided subnet_id in configured VDI subnets is accepted."""
        mock_get_setting.side_effect = lambda key: {
            "vdc.dcv_session.network.private_subnets": ["subnet-aaa", "subnet-bbb"],
            "cluster.network.private_subnets": ["subnet-ccc"],
        }.get(key)

        session = Mock()
        session.server = Mock()
        session.server.subnet_id = "subnet-aaa"
        session.failure_reason = None

        result_session, is_valid = session_utils.validate_attempt_subnets(session)

        assert is_valid is True

    @patch("api.utils.session_utils.cluster_settings.get_setting")
    def test_valid_subnet_in_cluster_subnets_accepted(self, mock_get_setting):
        """Test that a user-provided subnet_id in cluster private subnets is accepted."""
        mock_get_setting.side_effect = lambda key: {
            "vdc.dcv_session.network.private_subnets": ["subnet-aaa"],
            "cluster.network.private_subnets": ["subnet-ccc", "subnet-ddd"],
        }.get(key)

        session = Mock()
        session.server = Mock()
        session.server.subnet_id = "subnet-ccc"
        session.failure_reason = None

        result_session, is_valid = session_utils.validate_attempt_subnets(session)

        assert is_valid is True

    @patch("api.utils.session_utils.cluster_settings.get_setting")
    def test_invalid_subnet_rejected(self, mock_get_setting):
        """Test that a user-provided subnet_id NOT in allowed subnets is rejected."""
        mock_get_setting.side_effect = lambda key: {
            "vdc.dcv_session.network.private_subnets": ["subnet-aaa", "subnet-bbb"],
            "cluster.network.private_subnets": ["subnet-ccc"],
        }.get(key)

        session = Mock()
        session.server = Mock()
        session.server.subnet_id = "subnet-unauthorized"
        session.failure_reason = None

        result_session, is_valid = session_utils.validate_attempt_subnets(session)

        assert is_valid is False
        assert "subnet-unauthorized" in result_session.failure_reason
        assert "not authorized for this environment" in result_session.failure_reason

    @patch("api.utils.session_utils.cluster_settings.get_setting")
    def test_invalid_subnet_rejected_when_no_subnets_configured(self, mock_get_setting):
        """Test that a user-provided subnet_id is rejected when no subnets are configured."""
        mock_get_setting.side_effect = lambda key: {
            "vdc.dcv_session.network.private_subnets": None,
            "cluster.network.private_subnets": None,
        }.get(key)

        session = Mock()
        session.server = Mock()
        session.server.subnet_id = "subnet-xyz"
        session.failure_reason = None

        result_session, is_valid = session_utils.validate_attempt_subnets(session)

        assert is_valid is False
        assert "subnet-xyz" in result_session.failure_reason
        assert "not authorized for this environment" in result_session.failure_reason

    @patch("api.utils.session_utils.cluster_settings.get_setting")
    def test_no_subnet_provided_uses_vdi_subnets(self, mock_get_setting):
        """Test that when no subnet_id is provided, configured VDI subnets are used."""
        mock_get_setting.side_effect = lambda key: {
            "vdc.dcv_session.network.private_subnets": ["subnet-aaa", "subnet-bbb"],
            "cluster.network.private_subnets": ["subnet-ccc"],
        }.get(key)

        session = Mock()
        session.server = Mock()
        session.server.subnet_id = None
        session.failure_reason = None

        result_session, is_valid = session_utils.validate_attempt_subnets(session)

        assert is_valid is True

    @patch("api.utils.session_utils.cluster_settings.get_setting")
    def test_no_subnet_provided_falls_back_to_cluster_subnets(self, mock_get_setting):
        """Test that when no subnet_id and no VDI subnets, cluster subnets are used."""
        mock_get_setting.side_effect = lambda key: {
            "vdc.dcv_session.network.private_subnets": None,
            "cluster.network.private_subnets": ["subnet-ccc", "subnet-ddd"],
        }.get(key)

        session = Mock()
        session.server = Mock()
        session.server.subnet_id = None
        session.failure_reason = None

        result_session, is_valid = session_utils.validate_attempt_subnets(session)

        assert is_valid is True
