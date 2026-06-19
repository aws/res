#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Dict, List

import pytest
from res.resources import sessions  # type: ignore

from tests.integration.framework.client.api_client import ApiClient
from tests.integration.framework.fixtures.fixture_request import FixtureRequest
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

BatchStartSessionRequestContent = get_backend_model_class(
    "batch_start_session_request_content", "BatchStartSessionRequestContent"
)
VirtualDesktopSession = get_backend_model_class(
    "virtual_desktop_session", "VirtualDesktopSession"
)
BatchOperationErrorCode = get_backend_model_class(
    "batch_operation_error_code", "BatchOperationErrorCode"
)

logger = logging.getLogger(__name__)


class TestBatchStartSession:

    def _build_request(self, session_records: List[Dict[str, Any]]) -> Any:
        """Build a BatchStartSessionRequestContent from session records."""
        session_list = [
            VirtualDesktopSession(
                idea_session_id=record[sessions.SESSION_DB_RANGE_KEY],
                owner=record[sessions.SESSION_DB_HASH_KEY],
                name=record.get("name", "test-session"),
                hibernation_enabled=False,
            )
            for record in session_records
        ]
        return BatchStartSessionRequestContent(sessions=session_list)

    @pytest.mark.parametrize(
        "session_record",
        [
            [
                {
                    "session_id": "test-batch-start-admin-own",
                    sessions.SESSION_DB_HASH_KEY: "clusteradmin",
                    "state": "STOPPED",
                },
                {
                    "session_id": "test-batch-start-admin-other",
                    sessions.SESSION_DB_HASH_KEY: "user1",
                    "state": "STOPPED",
                },
            ]
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_start_session_with_admin_user(
        self,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        session_record: List[Dict[str, Any]],
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """Test that admin can start both own and other user's sessions."""
        set_backend_lambda_dry_mode(region, environment_name, True)
        try:
            api_client = ApiClient(res_environment, admin)
            request_content = self._build_request(session_record)
            response = api_client.batch_start_session(request_content)

            assert response is not None, "Response should not be None"
            assert (
                len(response.successful_list) == 2
            ), "Admin should successfully start both sessions"
            successful_ids = {s.idea_session_id for s in response.successful_list}
            assert "test-batch-start-admin-own" in successful_ids
            assert "test-batch-start-admin-other" in successful_ids
            assert (
                len(response.unsuccessful_list) == 0
            ), "There should be no unsuccessful sessions"

            logger.info("Admin successfully started both own and other user's sessions")
        finally:
            set_backend_lambda_dry_mode(region, environment_name, False)

    @pytest.mark.parametrize(
        "session_record",
        [
            [
                {
                    "session_id": "test-batch-start-user1-123",
                    sessions.SESSION_DB_HASH_KEY: "user1",
                    "state": "STOPPED",
                }
            ]
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_batch_start_session_with_non_admin_user(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        session_record: List[Dict[str, Any]],
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        """Test that non-admin can start their own session."""
        set_backend_lambda_dry_mode(region, environment_name, True)
        try:
            api_client = ApiClient(res_environment, non_admin)
            request_content = self._build_request(session_record)
            response = api_client.batch_start_session(request_content)

            assert response is not None, "Response should not be None"
            assert (
                len(response.successful_list) == 1
            ), "Should have 1 successful session"
            assert (
                response.successful_list[0].idea_session_id
                == "test-batch-start-user1-123"
            )
            assert (
                len(response.unsuccessful_list) == 0
            ), "There should be no unsuccessful sessions"

            logger.info("Non-admin user successfully started their own session")
        finally:
            set_backend_lambda_dry_mode(region, environment_name, False)

    def test_batch_start_session_with_nonexistent_user(
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
            request_content = BatchStartSessionRequestContent(sessions=session_list)
            api_client.batch_start_session(request_content)
            pytest.fail("Expected 'User not found' error for non-existent user")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "User not found" in e.response.text
            ), f"Unexpected error for non-existent user: {str(e)}"
            logger.info(f"Non-existent user correctly received 401 error: {str(e)}")

    @pytest.mark.parametrize("inactive_username", ["user2"])
    def test_batch_start_session_with_inactive_user(
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
            request_content = BatchStartSessionRequestContent(sessions=session_list)
            api_client.batch_start_session(request_content)
            pytest.fail("Expected error for inactive user")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "Inactive user" in e.response.text
            ), f"Unexpected error for inactive user: {str(e)}"
            logger.info(f"Inactive user correctly received 401 error: {str(e)}")

    def test_batch_start_session_without_auth_token(
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
            request_content = BatchStartSessionRequestContent(sessions=session_list)
            api_client.batch_start_session(request_content)
            pytest.fail("Expected 'No authorization token provided' error")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "No authorization token provided" in e.response.text
            ), f"Unexpected error for request without auth token: {str(e)}"
            logger.info(
                f"Request without auth token correctly received 401 error: {str(e)}"
            )

    def test_batch_start_session_with_invalid_auth_token(
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
            request_content = BatchStartSessionRequestContent(sessions=session_list)
            api_client.batch_start_session(request_content)
            pytest.fail(
                "Expected 'Unable to retrieve username' error for invalid auth token"
            )
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "Unable to retrieve username" in e.response.text
            ), f"Unexpected error for request with invalid auth token: {str(e)}"
            logger.info(
                "Request with invalid auth token correctly received 'Unable to retrieve username' error"
            )
        finally:
            set_backend_lambda_test_mode(region, environment_name, True)

    @pytest.mark.parametrize(
        "session_record",
        [
            [
                {
                    "session_id": "test-batch-start-other-user-123",
                    sessions.SESSION_DB_HASH_KEY: "other_user",
                    "state": "STOPPED",
                }
            ]
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_batch_start_session_non_admin_other_users_session(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        session_record: List[Dict[str, Any]],
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        """Test that non-admin user cannot start another user's session."""
        api_client = ApiClient(res_environment, non_admin)
        request_content = self._build_request(session_record)
        response = api_client.batch_start_session(request_content)

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
    def test_batch_start_session_nonexistent_session(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """Test batch start with a session ID that does not exist in DDB."""
        api_client = ApiClient(res_environment, admin)
        session_list = [
            VirtualDesktopSession(
                idea_session_id="nonexistent-session-999",
                owner="clusteradmin",
                name="Ghost Session",
                hibernation_enabled=False,
            )
        ]
        request_content = BatchStartSessionRequestContent(sessions=session_list)
        response = api_client.batch_start_session(request_content)

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

    @pytest.mark.parametrize(
        "session_record",
        [
            [
                {
                    "session_id": "test-batch-start-wrong-state",
                    sessions.SESSION_DB_HASH_KEY: "clusteradmin",
                    "state": "READY",
                }
            ]
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_start_session_not_in_stopped_state(
        self,
        region: str,
        res_environment: ResEnvironment,
        session_record: List[Dict[str, Any]],
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """Test that starting a session not in STOPPED/STOPPED_IDLE state fails."""
        api_client = ApiClient(res_environment, admin)
        request_content = self._build_request(session_record)
        response = api_client.batch_start_session(request_content)

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
            "READY" in response.unsuccessful_list[0].message
        ), f"Expected state in message, got: {response.unsuccessful_list[0].message}"

        logger.info(
            "Session not in STOPPED state correctly returned in unsuccessful list"
        )

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_start_session_empty_sessions_list(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """Test that an empty sessions list returns 400 (connexion validation)."""
        try:
            api_client = ApiClient(res_environment, admin)
            request_content = BatchStartSessionRequestContent(sessions=[])
            api_client.batch_start_session(request_content)
            pytest.fail("Expected 400 error for empty sessions list")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            logger.info(f"Empty sessions list correctly received 400 error: {str(e)}")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_start_session_missing_sessions_field(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """Test that a request without the sessions field returns 400."""
        try:
            api_client = ApiClient(res_environment, admin)
            request_content = BatchStartSessionRequestContent(sessions=None)
            api_client.batch_start_session(request_content)
            pytest.fail("Expected 400 error for missing sessions field")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            logger.info(
                f"Missing sessions field correctly received 400 error: {str(e)}"
            )

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_start_session_missing_idea_session_id(
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
        request_content = BatchStartSessionRequestContent(sessions=session_list)
        response = api_client.batch_start_session(request_content)

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

        logger.info("Missing idea_session_id correctly returned in unsuccessful list")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_start_session_missing_owner(
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
        request_content = BatchStartSessionRequestContent(sessions=session_list)
        response = api_client.batch_start_session(request_content)

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

        logger.info("Missing owner correctly returned in unsuccessful list")

    @pytest.mark.parametrize(
        "session_record",
        [
            [
                {
                    "session_id": "test-batch-start-stopped-idle",
                    sessions.SESSION_DB_HASH_KEY: "clusteradmin",
                    "state": "STOPPED_IDLE",
                }
            ]
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_start_session_stopped_idle_state(
        self,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        session_record: List[Dict[str, Any]],
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """Test that a session in STOPPED_IDLE state can be started."""
        set_backend_lambda_dry_mode(region, environment_name, True)
        try:
            api_client = ApiClient(res_environment, admin)
            request_content = self._build_request(session_record)
            response = api_client.batch_start_session(request_content)

            assert response is not None, "Response should not be None"
            assert (
                len(response.successful_list) == 1
            ), "Should have 1 successful session"
            assert (
                response.successful_list[0].idea_session_id
                == "test-batch-start-stopped-idle"
            )
            assert (
                len(response.unsuccessful_list) == 0
            ), "There should be no unsuccessful sessions"

            logger.info("Session in STOPPED_IDLE state successfully started")
        finally:
            set_backend_lambda_dry_mode(region, environment_name, False)
