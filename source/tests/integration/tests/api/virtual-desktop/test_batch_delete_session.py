#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Dict, List

import pytest
from res.clients.api_client.res_api_client import ResApiClient  # type: ignore
from res.resources import sessions  # type: ignore

from ideadatamodel import Project  # type: ignore
from ideadatamodel.constants import PROJECT_OWNER_ROLE_ID  # type: ignore
from tests.integration.framework.client.api_client import ApiClient
from tests.integration.framework.fixtures.fixture_request import FixtureRequest
from tests.integration.framework.fixtures.project import project
from tests.integration.framework.fixtures.res_api_client import (
    res_api_client,
    res_api_client_read_only,
)
from tests.integration.framework.fixtures.res_environment import (
    ResEnvironment,
    res_environment,
)
from tests.integration.framework.fixtures.session_record import session_record
from tests.integration.framework.fixtures.users import admin, inactive_user, non_admin
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.lambda_utils import (
    set_backend_lambda_dry_mode,
    set_backend_lambda_test_mode,
)
from tests.integration.framework.utils.model_utils import get_backend_model_class

BatchDeleteSessionRequestContent = get_backend_model_class(
    "batch_delete_session_request_content", "BatchDeleteSessionRequestContent"
)
VirtualDesktopSession = get_backend_model_class(
    "virtual_desktop_session", "VirtualDesktopSession"
)
BatchOperationErrorCode = get_backend_model_class(
    "batch_operation_error_code", "BatchOperationErrorCode"
)

logger = logging.getLogger(__name__)


class TestBatchDeleteSession:

    def _build_request(self, session_records: List[Dict[str, Any]]) -> Any:
        """Build a BatchDeleteSessionRequestContent from session records."""
        session_list = [
            VirtualDesktopSession(
                idea_session_id=record[sessions.SESSION_DB_RANGE_KEY],
                owner=record[sessions.SESSION_DB_HASH_KEY],
                name=record.get("name", "test-session"),
                hibernation_enabled=False,
            )
            for record in session_records
        ]
        return BatchDeleteSessionRequestContent(sessions=session_list)

    @pytest.mark.parametrize(
        "session_record",
        [
            [
                {
                    "session_id": "test-batch-delete-admin-own",
                    sessions.SESSION_DB_HASH_KEY: "clusteradmin",
                },
                {
                    "session_id": "test-batch-delete-admin-other",
                    sessions.SESSION_DB_HASH_KEY: "user1",
                },
            ]
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_delete_session_with_admin_user(
        self,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        session_record: List[Dict[str, Any]],
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """Test that admin can delete both own and other user's sessions."""
        set_backend_lambda_dry_mode(region, environment_name, True)
        try:
            api_client = ApiClient(res_environment, admin)
            request_content = self._build_request(session_record)
            response = api_client.batch_delete_session(request_content)

            assert response is not None, "Response should not be None"
            assert (
                len(response.successful_list) == 2
            ), "Admin should successfully delete both sessions"
            successful_ids = {s.idea_session_id for s in response.successful_list}
            assert "test-batch-delete-admin-own" in successful_ids
            assert "test-batch-delete-admin-other" in successful_ids
            assert (
                len(response.unsuccessful_list) == 0
            ), "There should be no unsuccessful sessions"

        finally:
            set_backend_lambda_dry_mode(region, environment_name, False)

    @pytest.mark.parametrize(
        "session_record",
        [
            [
                {
                    "session_id": "test-batch-delete-user1-123",
                    sessions.SESSION_DB_HASH_KEY: "user1",
                }
            ]
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_batch_delete_session_with_non_admin_user(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        session_record: List[Dict[str, Any]],
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        """Test that non-admin can delete their own session."""
        set_backend_lambda_dry_mode(region, environment_name, True)
        try:
            api_client = ApiClient(res_environment, non_admin)
            request_content = self._build_request(session_record)
            response = api_client.batch_delete_session(request_content)

            assert response is not None, "Response should not be None"
            assert (
                len(response.successful_list) == 1
            ), "Should have 1 successful session"
            assert (
                response.successful_list[0].idea_session_id
                == "test-batch-delete-user1-123"
            )
            assert (
                len(response.unsuccessful_list) == 0
            ), "There should be no unsuccessful sessions"

        finally:
            set_backend_lambda_dry_mode(region, environment_name, False)

    def test_batch_delete_session_with_nonexistent_user(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
    ) -> None:
        try:
            nonexistent_auth = ClientAuth(username="nonexistent_user_12345")
            api_client = ApiClient(res_environment, nonexistent_auth)
            session_list = [
                VirtualDesktopSession(
                    idea_session_id="test-session-123",
                    owner="nonexistent_user_12345",
                    name="test-session",
                    hibernation_enabled=False,
                )
            ]
            request_content = BatchDeleteSessionRequestContent(sessions=session_list)
            api_client.batch_delete_session(request_content)
            pytest.fail("Expected 'User not found' error for non-existent user")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "User not found" in e.response.text
            ), f"Unexpected error for non-existent user: {str(e)}"

    @pytest.mark.parametrize("inactive_username", ["user2"])
    def test_batch_delete_session_with_inactive_user(
        self,
        region: str,
        res_environment: ResEnvironment,
        inactive_username: str,
        inactive_user: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, inactive_user)
            session_list = [
                VirtualDesktopSession(
                    idea_session_id="test-session-123",
                    owner=inactive_username,
                    name="test-session",
                    hibernation_enabled=False,
                )
            ]
            request_content = BatchDeleteSessionRequestContent(sessions=session_list)
            api_client.batch_delete_session(request_content)
            pytest.fail("Expected error for inactive user")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "Inactive user" in e.response.text
            ), f"Unexpected error for inactive user: {str(e)}"

    def test_batch_delete_session_without_auth_token(
        self,
        res_environment: ResEnvironment,
        region: str,
    ) -> None:
        try:
            no_auth = ClientAuth(username="clusteradmin", auth_token=None)
            api_client = ApiClient(res_environment, no_auth)
            session_list = [
                VirtualDesktopSession(
                    idea_session_id="test-session-123",
                    owner="clusteradmin",
                    name="test-session",
                    hibernation_enabled=False,
                )
            ]
            request_content = BatchDeleteSessionRequestContent(sessions=session_list)
            api_client.batch_delete_session(request_content)
            pytest.fail("Expected 'No authorization token provided' error")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "No authorization token provided" in e.response.text
            ), f"Unexpected error for request without auth token: {str(e)}"

    def test_batch_delete_session_with_invalid_auth_token(
        self,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
    ) -> None:
        set_backend_lambda_test_mode(region, environment_name, False)
        try:
            invalid_auth = ClientAuth(
                username="clusteradmin", auth_token="invalid_token_12345"
            )
            api_client = ApiClient(res_environment, invalid_auth)
            session_list = [
                VirtualDesktopSession(
                    idea_session_id="test-session-123",
                    owner="clusteradmin",
                    name="test-session",
                    hibernation_enabled=False,
                )
            ]
            request_content = BatchDeleteSessionRequestContent(sessions=session_list)
            api_client.batch_delete_session(request_content)
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
            set_backend_lambda_test_mode(region, environment_name, True)

    @pytest.mark.parametrize(
        "session_record",
        [
            [
                {
                    "session_id": "test-batch-delete-other-user-123",
                    sessions.SESSION_DB_HASH_KEY: "other_user",
                }
            ]
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_batch_delete_session_non_admin_other_users_session(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        session_record: List[Dict[str, Any]],
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        """Test that non-admin user without permission cannot delete another user's session."""
        api_client = ApiClient(res_environment, non_admin)
        request_content = self._build_request(session_record)
        response = api_client.batch_delete_session(request_content)

        assert response is not None, "Response should not be None"
        assert len(response.successful_list) == 0, "Should have no successful sessions"
        assert (
            len(response.unsuccessful_list) == 1
        ), "Should have 1 unsuccessful session"
        assert (
            response.unsuccessful_list[0].error_code
            == BatchOperationErrorCode.FORBIDDENEXCEPTION
        ), "Error code should be ForbiddenException"

        logger.info(
            "Non-admin correctly received ForbiddenException for other user's session"
        )

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="test-batch-delete-cross-user",
                    name="test-batch-delete-cross-user",
                    description="Cross-user permission test",
                    enable_budgets=False,
                ),
                ["home"],
                [],
                ["user1"],
                "admin",
                PROJECT_OWNER_ROLE_ID,
            )
        ],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "session_record",
        [
            [
                {
                    "session_id": "test-batch-delete-cross-user-123",
                    sessions.SESSION_DB_HASH_KEY: "other_user",
                    "project_fixture": True,
                }
            ]
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_batch_delete_session_non_admin_with_cross_user_permission(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        admin_username: str,  # required by project fixture
        project: Project,
        session_record: List[Dict[str, Any]],
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        """Test that non-admin with vdis.create_terminate_others_sessions can delete another user's session."""
        set_backend_lambda_dry_mode(region, environment_name, True)
        try:
            api_client = ApiClient(res_environment, non_admin)
            request_content = self._build_request(session_record)
            response = api_client.batch_delete_session(request_content)

            assert response is not None, "Response should not be None"
            assert (
                len(response.successful_list) == 1
            ), "Should have 1 successful session"
            assert (
                response.successful_list[0].idea_session_id
                == "test-batch-delete-cross-user-123"
            )
            assert (
                len(response.unsuccessful_list) == 0
            ), "There should be no unsuccessful sessions"

            logger.info(
                "Non-admin with cross-user permission successfully deleted other user's session"
            )
        finally:
            set_backend_lambda_dry_mode(region, environment_name, False)

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_delete_session_nonexistent_session(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """Test batch delete with a session ID that does not exist in DDB."""
        api_client = ApiClient(res_environment, admin)
        session_list = [
            VirtualDesktopSession(
                idea_session_id="nonexistent-session-999",
                owner="clusteradmin",
                name="Ghost Session",
                hibernation_enabled=False,
            )
        ]
        request_content = BatchDeleteSessionRequestContent(sessions=session_list)
        response = api_client.batch_delete_session(request_content)

        assert response is not None, "Response should not be None"
        assert len(response.successful_list) == 0, "Should have no successful sessions"
        assert (
            len(response.unsuccessful_list) == 1
        ), "Should have 1 unsuccessful session"
        assert (
            response.unsuccessful_list[0].error_code
            == BatchOperationErrorCode.BADREQUESTEXCEPTION
        ), f"Expected BadRequestException, got: {response.unsuccessful_list[0].error_code}"
        assert (
            "Session not found" in response.unsuccessful_list[0].message
        ), f"Expected 'Session not found', got: {response.unsuccessful_list[0].message}"

        logger.info(
            f"Non-existent session correctly returned in unsuccessful list: "
            f"{response.unsuccessful_list[0].message}"
        )

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_delete_session_empty_sessions_list(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """Test that an empty sessions list returns 400 (connexion validation)."""
        try:
            api_client = ApiClient(res_environment, admin)
            request_content = BatchDeleteSessionRequestContent(sessions=[])
            api_client.batch_delete_session(request_content)
            pytest.fail("Expected 400 error for empty sessions list")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "should be non-empty" in e.response.text
            ), f"Expected 'should be non-empty' validation error, got: {e.response.text}"

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_delete_session_missing_sessions_field(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """Test that a request without the sessions field returns 400."""
        try:
            api_client = ApiClient(res_environment, admin)
            request_content = BatchDeleteSessionRequestContent(sessions=None)
            api_client.batch_delete_session(request_content)
            pytest.fail("Expected 400 error for missing sessions field")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "is a required property" in e.response.text
            ), f"Expected 'is a required property' error, got: {e.response.text}"

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_delete_session_missing_idea_session_id(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """Test that a session without idea_session_id is returned in unsuccessfulList."""
        api_client = ApiClient(res_environment, admin)
        session_list = [
            VirtualDesktopSession(
                owner="clusteradmin",
                name="Missing ID Session",
                hibernation_enabled=False,
            )
        ]
        request_content = BatchDeleteSessionRequestContent(sessions=session_list)
        response = api_client.batch_delete_session(request_content)

        assert response is not None, "Response should not be None"
        assert len(response.successful_list) == 0, "Should have no successful sessions"
        assert (
            len(response.unsuccessful_list) == 1
        ), "Should have 1 unsuccessful session"
        assert (
            response.unsuccessful_list[0].error_code
            == BatchOperationErrorCode.BADREQUESTEXCEPTION
        ), f"Expected BadRequestException, got: {response.unsuccessful_list[0].error_code}"
        assert (
            "idea_session_id and session.owner are required"
            in response.unsuccessful_list[0].message
        ), f"Expected 'idea_session_id and session.owner are required', got: {response.unsuccessful_list[0].message}"

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_delete_session_missing_owner(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """Test that a session without owner is returned in unsuccessfulList."""
        api_client = ApiClient(res_environment, admin)
        session_list = [
            VirtualDesktopSession(
                idea_session_id="test-session-123",
                name="Missing Owner Session",
                hibernation_enabled=False,
            )
        ]
        request_content = BatchDeleteSessionRequestContent(sessions=session_list)
        response = api_client.batch_delete_session(request_content)

        assert response is not None, "Response should not be None"
        assert len(response.successful_list) == 0, "Should have no successful sessions"
        assert (
            len(response.unsuccessful_list) == 1
        ), "Should have 1 unsuccessful session"
        assert (
            response.unsuccessful_list[0].error_code
            == BatchOperationErrorCode.BADREQUESTEXCEPTION
        ), f"Expected BadRequestException, got: {response.unsuccessful_list[0].error_code}"
        assert (
            "owner are required" in response.unsuccessful_list[0].message
        ), f"Expected owner required message, got: {response.unsuccessful_list[0].message}"

    @pytest.mark.parametrize(
        "session_record",
        [
            [
                {
                    "session_id": "test-batch-delete-service-token",
                    sessions.SESSION_DB_HASH_KEY: "user1",
                }
            ]
        ],
        indirect=True,
    )
    def test_batch_delete_session_with_service_token(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        session_record: List[Dict[str, Any]],
        res_api_client: ResApiClient,
    ) -> None:
        """ResApiClient (service-token caller) deletes a session owned by another
        user. The backend should enforce_scope, set skip_user_authz=True, and
        bypass per-session ownership validation. DRY_RUN_ENABLED prevents the
        actual EC2 termination."""
        set_backend_lambda_dry_mode(region, environment_name, True)
        try:
            request_content = self._build_request(session_record)
            response = res_api_client.batch_delete_session(request_content)

            assert response is not None, "Response should not be None"
            assert (
                len(response.successful_list) == 1
            ), "Service-token caller should successfully delete the session"
            assert (
                response.successful_list[0].idea_session_id
                == "test-batch-delete-service-token"
            )
            assert len(response.unsuccessful_list) == 0
        finally:
            set_backend_lambda_dry_mode(region, environment_name, False)

    def test_batch_delete_session_with_service_token_read_only_scope_rejected(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        res_api_client_read_only: ResApiClient,
    ) -> None:
        """Service token without write scope must be rejected by enforce_scope
        before any session work happens."""
        try:
            session_list = [
                VirtualDesktopSession(
                    idea_session_id="test-session-readonly-rejected",
                    owner="user1",
                    name="test-session",
                    hibernation_enabled=False,
                )
            ]
            request_content = BatchDeleteSessionRequestContent(sessions=session_list)
            res_api_client_read_only.batch_delete_session(request_content)
            pytest.fail("Expected 401 for service token missing write scope")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "Insufficient scope" in e.response.text
            ), f"Unexpected error for service token missing write scope: {str(e)}"
