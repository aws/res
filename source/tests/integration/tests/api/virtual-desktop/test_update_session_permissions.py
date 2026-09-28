#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
Integration tests for Update Session Permission API.

This module contains comprehensive tests for the update session permission REST API
using the RES framework ResClient for proper API interaction.
"""

import logging
from typing import Any, Dict, List

import pytest
from res.resources import sessions  # type: ignore

from tests.integration.framework.client.api_client import (
    ApiClient,
    UpdateSessionPermissionsRequestContent,
    UpdateSessionPermissionsResponseContent,
)
from tests.integration.framework.fixtures.fixture_request import FixtureRequest
from tests.integration.framework.fixtures.res_environment import (
    ResEnvironment,
    res_environment,
)
from tests.integration.framework.fixtures.session_record import session_record
from tests.integration.framework.fixtures.users import admin, inactive_user, non_admin
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.virtual_desktop import (
    get_session_permission_base_payload,
)

logger = logging.getLogger(__name__)


class TestUpdateSessionPermissions:

    # ==================== 200 Golden Path Tests ====================

    @pytest.mark.parametrize(
        "session_record",
        [
            [
                {
                    "session_id": "test-update-perm-admin-session",
                    sessions.SESSION_DB_HASH_KEY: "clusteradmin",
                    "base_os": "amzn2023",
                }
            ]
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_update_session_permissions_create_with_admin_user(
        self,
        request: FixtureRequest,
        res_environment: ResEnvironment,
        session_record: List[Dict[str, Any]],
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        record = session_record[0]
        api_client = ApiClient(res_environment, admin)

        permission = get_session_permission_base_payload(
            idea_session_id=record[sessions.SESSION_DB_RANGE_KEY],
            idea_session_owner=record[sessions.SESSION_DB_HASH_KEY],
            actor_name="testactor-admin-create",
        )
        request_content = UpdateSessionPermissionsRequestContent(
            create=[permission], update=[], delete=[]
        )

        response: UpdateSessionPermissionsResponseContent = (
            api_client.update_session_permissions(request_content)
        )

        try:
            assert response is not None
            assert response.permissions is not None
            assert isinstance(response.permissions, list)
            assert len(response.permissions) == 1
            assert (
                response.permissions[0].idea_session_id
                == record[sessions.SESSION_DB_RANGE_KEY]
            )
            assert response.permissions[0].actor_name == "testactor-admin-create"
        finally:
            # Cleanup: delete the created permission
            delete_permission = get_session_permission_base_payload(
                idea_session_id=record[sessions.SESSION_DB_RANGE_KEY],
                idea_session_owner=record[sessions.SESSION_DB_HASH_KEY],
                actor_name="testactor-admin-create",
            )
            cleanup_request = UpdateSessionPermissionsRequestContent(
                create=[], update=[], delete=[delete_permission]
            )
            api_client.update_session_permissions(cleanup_request)

    @pytest.mark.parametrize(
        "session_record",
        [
            [
                {
                    "session_id": "test-update-perm-user1-session",
                    sessions.SESSION_DB_HASH_KEY: "user1",
                    "base_os": "amzn2023",
                }
            ]
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_update_session_permissions_create_with_non_admin_user_own_session(
        self,
        request: FixtureRequest,
        res_environment: ResEnvironment,
        session_record: List[Dict[str, Any]],
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        record = session_record[0]
        api_client = ApiClient(res_environment, non_admin)

        permission = get_session_permission_base_payload(
            idea_session_id=record[sessions.SESSION_DB_RANGE_KEY],
            idea_session_owner=record[sessions.SESSION_DB_HASH_KEY],
            actor_name="testactor-nonadmin-create",
        )
        request_content = UpdateSessionPermissionsRequestContent(
            create=[permission], update=[], delete=[]
        )

        response: UpdateSessionPermissionsResponseContent = (
            api_client.update_session_permissions(request_content)
        )

        try:
            assert response is not None
            assert response.permissions is not None
            assert isinstance(response.permissions, list)
            assert len(response.permissions) == 1
            assert (
                response.permissions[0].idea_session_id
                == record[sessions.SESSION_DB_RANGE_KEY]
            )
            assert response.permissions[0].actor_name == "testactor-nonadmin-create"
        finally:
            # Cleanup: delete the created permission
            delete_permission = get_session_permission_base_payload(
                idea_session_id=record[sessions.SESSION_DB_RANGE_KEY],
                idea_session_owner=record[sessions.SESSION_DB_HASH_KEY],
                actor_name="testactor-nonadmin-create",
            )
            cleanup_request = UpdateSessionPermissionsRequestContent(
                create=[], update=[], delete=[delete_permission]
            )
            api_client.update_session_permissions(cleanup_request)

    # ==================== 4xx Error Tests ====================

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_update_session_permissions_empty_payload(
        self,
        request: FixtureRequest,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            payload: Dict[str, Any] = {}
            request_content = UpdateSessionPermissionsRequestContent(**payload)

            response: UpdateSessionPermissionsResponseContent = (
                api_client.update_session_permissions(request_content)
            )
            assert response is not None
            pytest.fail(f"Error failed to validate empty payload")

        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert "Invalid request" in e.response.text, f"Unexpected error: {str(e)}"

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_update_session_permissions_missing_required_fields(
        self,
        request: FixtureRequest,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)

            # Create permission with missing required fields
            invalid_permission = {"actor_name": "testuser"}

            request_content = UpdateSessionPermissionsRequestContent(
                create=[invalid_permission], update=[], delete=[]
            )

            api_client.update_session_permissions(request_content)
            pytest.fail("Expected 400 error for missing required fields")

        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "'actor_type' is a required property" in e.response.text
            ), f"Unexpected error: {str(e)}"

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_update_session_permissions_invalid_session_id(
        self,
        request: FixtureRequest,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)

            # Create permission with invalid session ID
            invalid_permission = get_session_permission_base_payload(
                idea_session_id="invalid-session-id", actor_name="user1"
            )

            request_content = UpdateSessionPermissionsRequestContent(
                create=[invalid_permission], update=[], delete=[]
            )

            api_client.update_session_permissions(request_content)
            pytest.fail("Expected 400 error for invalid session ID")

        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert "Invalid session" in e.response.text, f"Unexpected error: {str(e)}"

    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_update_session_permissions_with_non_admin_user_not_own_session(
        self,
        request: FixtureRequest,
        res_environment: ResEnvironment,
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, non_admin)

            permission = get_session_permission_base_payload()
            request_content = UpdateSessionPermissionsRequestContent(
                create=[permission], update=[], delete=[]
            )

            api_client.update_session_permissions(request_content)
            pytest.fail(
                "Expected 400 error for non-admin user upating session not owned by self"
            )

        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "Can update permission for session owned by user only"
                in e.response.text
            ), f"Unexpected error: {str(e)}"

    @pytest.mark.parametrize("inactive_username", ["user2"])
    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_update_permission_profile_with_inactive_user(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        inactive_username: str,
        inactive_user: ClientAuth,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, inactive_user)
            permission = get_session_permission_base_payload()
            request_content = UpdateSessionPermissionsRequestContent(
                create=[permission], update=[], delete=[]
            )

            api_client.update_session_permissions(request_content)
            pytest.fail("Expected error for inactive user")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "Inactive user" in e.response.text
            ), f"Unexpected error for inactive user: {str(e)}"

    def test_update_session_permissions_nonexistent_user(
        self,
        request: FixtureRequest,
        res_environment: ResEnvironment,
    ) -> None:
        try:
            nonexistent_auth = ClientAuth(username="nonexistent_user_12345")
            api_client = ApiClient(res_environment, nonexistent_auth)

            permission = get_session_permission_base_payload()
            request_content = UpdateSessionPermissionsRequestContent(
                create=[permission], update=[], delete=[]
            )

            api_client.update_session_permissions(request_content)
            pytest.fail("Expected 'User not found' error for non-existent user")

        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "User not found" in e.response.text
            ), f"Unexpected error for non-existent user: {str(e)}"

    def test_update_session_permissions_without_auth_token(
        self, res_environment: ResEnvironment
    ) -> None:
        try:
            no_auth = ClientAuth(username="user1", auth_token=None)
            api_client = ApiClient(res_environment, no_auth)

            permission = get_session_permission_base_payload()
            request_content = UpdateSessionPermissionsRequestContent(
                create=[permission], update=[], delete=[]
            )

            api_client.update_session_permissions(request_content)
            pytest.fail("Expected 'No authorization token provided' error")

        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "No authorization token provided" in e.response.text
            ), f"Unexpected error for request without auth token: {str(e)}"

    def test_update_session_permissions_with_invalid_auth_token_in_prod(
        self,
        request: FixtureRequest,
        res_environment: ResEnvironment,
        environment_name: str,
    ) -> None:
        from tests.integration.framework.utils.lambda_utils import (
            set_backend_lambda_test_mode,
        )

        set_backend_lambda_test_mode(res_environment.region, environment_name, False)
        try:
            # Create ClientAuth with invalid token
            invalid_auth = ClientAuth(
                username="clusteradmin", auth_token="invalid_token_12345"
            )
            api_client = ApiClient(res_environment, invalid_auth)

            permission = get_session_permission_base_payload()
            request_content = UpdateSessionPermissionsRequestContent(
                create=[permission], update=[], delete=[]
            )

            api_client.update_session_permissions(request_content)
            pytest.fail(
                "Expected 'Unable to retrieve username' error for invalid auth token"
            )
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "Unable to retrieve username" in e.response.text
            ), f"Unexpected error for request with invalid auth token: {str(e)}"
        finally:
            set_backend_lambda_test_mode(res_environment.region, environment_name, True)

    # ==================== Shell Metacharacter Injection Tests ====================

    @pytest.mark.dev
    @pytest.mark.parametrize(
        "session_record",
        [
            [
                {
                    "session_id": "test-metachar-session",
                    sessions.SESSION_DB_HASH_KEY: "clusteradmin",
                    "base_os": "amzn2023",
                }
            ]
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    @pytest.mark.parametrize(
        "malicious_actor_name",
        [
            ";rm -rf /",
            "$(whoami)",
            "`id`",
            "user1 && echo pwned",
            "user1 | cat /etc/passwd",
            "user1 > /tmp/pwned",
            "user1\nnewcommand",
        ],
        ids=[
            "semicolon",
            "dollar_paren",
            "backtick",
            "double_ampersand",
            "pipe",
            "redirect",
            "newline",
        ],
    )
    def test_share_session_rejects_shell_metachar_in_actor_name(
        self,
        request: FixtureRequest,
        res_environment: ResEnvironment,
        session_record: List[Dict[str, Any]],
        admin_username: str,
        admin: ClientAuth,
        malicious_actor_name: str,
    ) -> None:
        """
        Verify that the API rejects actor_name values containing shell
        metacharacters before they reach the host via SSM commands.
        The actor_name flows into SSM commands that set DCV permissions,
        so the backend must validate server-side.
        """
        record = session_record[0]
        api_client = ApiClient(res_environment, admin)

        permission = get_session_permission_base_payload(
            idea_session_id=record[sessions.SESSION_DB_RANGE_KEY],
            idea_session_owner=record[sessions.SESSION_DB_HASH_KEY],
            actor_name=malicious_actor_name,
        )

        request_content = UpdateSessionPermissionsRequestContent(
            create=[permission], update=[], delete=[]
        )

        try:
            api_client.update_session_permissions(request_content)
            pytest.fail(f"Expected 400 error for actor_name: '{malicious_actor_name}'")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "Invalid request. No session permission modified." in e.response.text
            ), f"Expected rejection message, got: {e.response.text}"
