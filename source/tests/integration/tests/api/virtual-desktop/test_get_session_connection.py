#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Dict, List

import pytest
from res.resources import session_permissions, sessions  # type: ignore
from res.utils import table_utils  # type: ignore

from tests.integration.framework.client.api_client import (
    ApiClient,
    GetSessionConnectionRequestContent,
    GetSessionConnectionResponseContent,
)
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

logger = logging.getLogger(__name__)


def _build_request(
    idea_session_id: str, idea_session_owner: str
) -> GetSessionConnectionRequestContent:
    return GetSessionConnectionRequestContent(
        **{
            "connection": {
                "idea-session-id": idea_session_id,
                "idea-session-owner": idea_session_owner,
            }
        }
    )


class TestGetSessionConnection:

    @pytest.mark.parametrize(
        "session_record",
        [
            [
                {
                    "session_id": "test-conn-admin-123",
                    sessions.SESSION_DB_HASH_KEY: "clusteradmin",
                    "state": "READY",
                }
            ]
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_get_session_connection_with_admin_user(
        self,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        session_record: List[Dict[str, Any]],
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        set_backend_lambda_dry_mode(region, environment_name, True)
        try:
            record = session_record[0]
            api_client = ApiClient(res_environment, admin)
            request_content = _build_request(
                idea_session_id=record[sessions.SESSION_DB_RANGE_KEY],
                idea_session_owner=record[sessions.SESSION_DB_HASH_KEY],
            )
            response = api_client.get_session_connection(request_content)

            assert response is not None, "Response should not be None"
            assert (
                response.connection is not None
            ), "Response must contain 'connection' field"
            assert (
                response.connection.idea_session_id
                == record[sessions.SESSION_DB_RANGE_KEY]
            ), "Session ID should match"
            assert (
                response.connection.idea_session_owner
                == record[sessions.SESSION_DB_HASH_KEY]
            ), "Session owner should match"
            logger.info(
                f"Admin successfully retrieved session connection for {record[sessions.SESSION_DB_RANGE_KEY]}"
            )
        finally:
            set_backend_lambda_dry_mode(region, environment_name, False)

    @pytest.mark.parametrize(
        "session_record",
        [
            [
                {
                    "session_id": "test-conn-user1-123",
                    sessions.SESSION_DB_HASH_KEY: "user1",
                    "state": "READY",
                }
            ]
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_get_session_connection_with_owner(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        session_record: List[Dict[str, Any]],
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        set_backend_lambda_dry_mode(region, environment_name, True)
        try:
            record = session_record[0]
            api_client = ApiClient(res_environment, non_admin)
            request_content = _build_request(
                idea_session_id=record[sessions.SESSION_DB_RANGE_KEY],
                idea_session_owner=record[sessions.SESSION_DB_HASH_KEY],
            )
            response = api_client.get_session_connection(request_content)

            assert response is not None, "Response should not be None"
            assert (
                response.connection is not None
            ), "Response must contain 'connection' field"
            assert (
                response.connection.idea_session_id
                == record[sessions.SESSION_DB_RANGE_KEY]
            ), "Session ID should match"
            assert (
                response.connection.idea_session_owner
                == record[sessions.SESSION_DB_HASH_KEY]
            ), "Session owner should match"
            logger.info(
                f"Session owner successfully retrieved connection for {record[sessions.SESSION_DB_RANGE_KEY]}"
            )
        finally:
            set_backend_lambda_dry_mode(region, environment_name, False)

    @pytest.mark.parametrize(
        "session_record",
        [
            [
                {
                    "session_id": "test-conn-shared-123",
                    sessions.SESSION_DB_HASH_KEY: "other_user",
                    "state": "READY",
                }
            ]
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_get_session_connection_with_shared_permission(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        session_record: List[Dict[str, Any]],
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        record = session_record[0]
        session_id = record[sessions.SESSION_DB_RANGE_KEY]

        permission_record = {
            session_permissions.SESSION_PERMISSION_DB_HASH_KEY: session_id,
            session_permissions.SESSION_PERMISSION_DB_RANGE_KEY: "user1",
        }
        table_utils.create_item(
            table_name=session_permissions.SESSION_PERMISSION_TABLE_NAME,
            item=permission_record,
        )

        def cleanup_permission() -> None:
            table_utils.delete_item(
                table_name=session_permissions.SESSION_PERMISSION_TABLE_NAME,
                key={
                    session_permissions.SESSION_PERMISSION_DB_HASH_KEY: session_id,
                    session_permissions.SESSION_PERMISSION_DB_RANGE_KEY: "user1",
                },
            )

        request.addfinalizer(cleanup_permission)

        set_backend_lambda_dry_mode(region, environment_name, True)
        try:
            api_client = ApiClient(res_environment, non_admin)
            request_content = _build_request(
                idea_session_id=session_id,
                idea_session_owner=record[sessions.SESSION_DB_HASH_KEY],
            )
            response = api_client.get_session_connection(request_content)

            assert response is not None, "Response should not be None"
            assert (
                response.connection is not None
            ), "Response must contain 'connection' field"
            assert (
                response.connection.idea_session_id == session_id
            ), "Session ID should match"
            logger.info(
                f"User with shared permission successfully retrieved connection for {session_id}"
            )
        finally:
            set_backend_lambda_dry_mode(region, environment_name, False)

    @pytest.mark.parametrize(
        "session_record",
        [
            [
                {
                    "session_id": "test-conn-unauth-123",
                    sessions.SESSION_DB_HASH_KEY: "other_user",
                    "state": "READY",
                }
            ]
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_get_session_connection_without_permission(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        session_record: List[Dict[str, Any]],
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        record = session_record[0]
        try:
            api_client = ApiClient(res_environment, non_admin)
            request_content = _build_request(
                idea_session_id=record[sessions.SESSION_DB_RANGE_KEY],
                idea_session_owner=record[sessions.SESSION_DB_HASH_KEY],
            )
            api_client.get_session_connection(request_content)
            pytest.fail(
                "Expected 401 error for non-admin user without permission to access other user's session"
            )
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "does not have permission" in e.response.text
            ), f"Unexpected error message: {e.response.text}"
            logger.info(
                f"User without permission correctly received 401 error: {str(e)}"
            )

    @pytest.mark.parametrize(
        "session_record",
        [
            [
                {
                    "session_id": "test-conn-notready-123",
                    sessions.SESSION_DB_HASH_KEY: "clusteradmin",
                    "state": "PROVISIONING",
                }
            ]
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_get_session_connection_session_not_ready(
        self,
        region: str,
        res_environment: ResEnvironment,
        session_record: List[Dict[str, Any]],
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        record = session_record[0]
        try:
            api_client = ApiClient(res_environment, admin)
            request_content = _build_request(
                idea_session_id=record[sessions.SESSION_DB_RANGE_KEY],
                idea_session_owner=record[sessions.SESSION_DB_HASH_KEY],
            )
            api_client.get_session_connection(request_content)
            pytest.fail("Expected 400 error for session not in READY state")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "not ready for connection" in e.response.text
            ), f"Unexpected error message: {e.response.text}"
            logger.info(f"Session not ready correctly received 400 error: {str(e)}")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_get_session_connection_nonexistent_session(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            request_content = _build_request(
                idea_session_id="nonexistent-session-999",
                idea_session_owner="clusteradmin",
            )
            api_client.get_session_connection(request_content)
            pytest.fail("Expected 400 error for non-existent session")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "does not exist" in e.response.text
            ), f"Unexpected error for non-existent session: {e.response.text}"
            logger.info(f"Non-existent session correctly received 400 error: {str(e)}")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_get_session_connection_missing_connection(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            request_content = GetSessionConnectionRequestContent(**{})
            api_client.get_session_connection(request_content)
            pytest.fail("Expected 400 error for missing connection field")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "connection" in e.response.text.lower()
            ), f"Unexpected error: {e.response.text}"

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_get_session_connection_missing_session_id(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            request_content = GetSessionConnectionRequestContent(
                **{
                    "connection": {
                        "idea-session-owner": "clusteradmin",
                    }
                }
            )
            api_client.get_session_connection(request_content)
            pytest.fail("Expected 400 error for missing idea-session-id")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            logger.info(f"Missing session ID correctly received 400 error: {str(e)}")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_get_session_connection_missing_session_owner(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            request_content = GetSessionConnectionRequestContent(
                **{
                    "connection": {
                        "idea-session-id": "test-session-123",
                    }
                }
            )
            api_client.get_session_connection(request_content)
            pytest.fail("Expected 400 error for missing idea-session-owner")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            logger.info(f"Missing session owner correctly received 400 error: {str(e)}")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_get_session_connection_empty_session_id(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        # Use raw=True to bypass client-side model validation (which rejects
        # empty strings). This tests server-side @length(min: 1) constraint.
        try:
            api_client = ApiClient(res_environment, admin)
            api_client.get_session_connection(
                {
                    "connection": {
                        "idea-session-id": "",
                        "idea-session-owner": "clusteradmin",
                    }
                },
                raw=True,
            )
            pytest.fail("Expected 400 error for empty idea-session-id")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            logger.info(f"Empty session ID correctly received 400 error: {str(e)}")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_get_session_connection_empty_session_owner(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        # Use raw=True to bypass client-side model validation (which rejects
        # empty strings). This tests server-side @length(min: 1) constraint.
        try:
            api_client = ApiClient(res_environment, admin)
            api_client.get_session_connection(
                {
                    "connection": {
                        "idea-session-id": "test-session-123",
                        "idea-session-owner": "",
                    }
                },
                raw=True,
            )
            pytest.fail("Expected 400 error for empty idea-session-owner")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            logger.info(f"Empty session owner correctly received 400 error: {str(e)}")

    def test_get_session_connection_with_nonexistent_user(
        self,
        region: str,
        res_environment: ResEnvironment,
    ) -> None:
        try:
            nonexistent_auth = ClientAuth(username="nonexistent_user_12345")
            api_client = ApiClient(res_environment, nonexistent_auth)
            request_content = _build_request(
                idea_session_id="test-session-123",
                idea_session_owner="nonexistent_user_12345",
            )
            api_client.get_session_connection(request_content)
            pytest.fail("Expected 'User not found' error for non-existent user")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "User not found" in e.response.text
            ), f"Unexpected error for non-existent user: {e.response.text}"
            logger.info(f"Non-existent user correctly received 401 error: {str(e)}")

    @pytest.mark.parametrize("inactive_username", ["user2"])
    def test_get_session_connection_with_inactive_user(
        self,
        region: str,
        res_environment: ResEnvironment,
        inactive_username: str,
        inactive_user: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, inactive_user)
            request_content = _build_request(
                idea_session_id="test-session-123",
                idea_session_owner=inactive_username,
            )
            api_client.get_session_connection(request_content)
            pytest.fail("Expected error for inactive user")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "Inactive user" in e.response.text
            ), f"Unexpected error for inactive user: {e.response.text}"
            logger.info(f"Inactive user correctly received 401 error: {str(e)}")

    def test_get_session_connection_without_auth_token(
        self,
        res_environment: ResEnvironment,
        region: str,
    ) -> None:
        try:
            no_auth = ClientAuth(username="clusteradmin", auth_token=None)
            api_client = ApiClient(res_environment, no_auth)
            request_content = _build_request(
                idea_session_id="test-session-123",
                idea_session_owner="clusteradmin",
            )
            api_client.get_session_connection(request_content)
            pytest.fail("Expected 'No authorization token provided' error")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "No authorization token provided" in e.response.text
            ), f"Unexpected error for request without auth token: {e.response.text}"
            logger.info(
                f"Request without auth token correctly received 401 error: {str(e)}"
            )

    def test_get_session_connection_with_invalid_auth_token_in_prod(
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
            request_content = _build_request(
                idea_session_id="test-session-123",
                idea_session_owner="clusteradmin",
            )
            api_client.get_session_connection(request_content)
            pytest.fail(
                "Expected 'Unable to retrieve username' error for invalid auth token"
            )
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "Unable to retrieve username" in e.response.text
            ), f"Unexpected error for request with invalid auth token: {e.response.text}"
            logger.info(
                "Request with invalid auth token correctly received 'Unable to retrieve username' error"
            )
        finally:
            set_backend_lambda_test_mode(region, environment_name, True)
