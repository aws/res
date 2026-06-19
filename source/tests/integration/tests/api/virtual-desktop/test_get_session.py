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
from tests.integration.framework.utils.lambda_utils import set_backend_lambda_test_mode

logger = logging.getLogger(__name__)


class TestGetSession:

    @pytest.mark.parametrize(
        "session_record",
        [
            [
                {
                    "session_id": "test-session-admin-123",
                    sessions.SESSION_DB_HASH_KEY: "clusteradmin",
                }
            ]
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_get_session_with_admin_user(
        self,
        region: str,
        res_environment: ResEnvironment,
        session_record: List[Dict[str, Any]],
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        record = session_record[0]
        api_client = ApiClient(res_environment, admin)
        response = api_client.get_session(
            res_session_id=record[sessions.SESSION_DB_RANGE_KEY],
            owner=record[sessions.SESSION_DB_HASH_KEY],
        )

        assert response is not None, "Response should not be None"
        assert response.session is not None, "Response must contain 'session' field"
        assert (
            response.session.idea_session_id == record[sessions.SESSION_DB_RANGE_KEY]
        ), "Session ID should match"
        assert (
            response.session.owner == record[sessions.SESSION_DB_HASH_KEY]
        ), "Owner should match"

        logger.info(
            f"Successfully retrieved session {record[sessions.SESSION_DB_RANGE_KEY]} for owner {record[sessions.SESSION_DB_HASH_KEY]}"
        )

    @pytest.mark.parametrize(
        "session_record",
        [
            [
                {
                    "session_id": "test-session-user1-123",
                    sessions.SESSION_DB_HASH_KEY: "user1",
                }
            ]
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_get_session_with_non_admin_user_own_session(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        session_record: List[Dict[str, Any]],
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        record = session_record[0]
        api_client = ApiClient(res_environment, non_admin)
        response = api_client.get_session(
            res_session_id=record[sessions.SESSION_DB_RANGE_KEY],
            owner=record[sessions.SESSION_DB_HASH_KEY],
        )

        assert response is not None, "Response should not be None"
        assert response.session is not None, "Response must contain 'session' field"
        assert (
            response.session.idea_session_id == record[sessions.SESSION_DB_RANGE_KEY]
        ), "Session ID should match"

        logger.info(
            f"Non-admin user successfully retrieved their own session: {record[sessions.SESSION_DB_RANGE_KEY]}"
        )

    @pytest.mark.parametrize(
        "session_record",
        [
            [
                {
                    "session_id": "test-session-other-123",
                    sessions.SESSION_DB_HASH_KEY: "other_user",
                }
            ]
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_get_session_with_non_admin_user_other_session(
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
            api_client.get_session(
                res_session_id=record[sessions.SESSION_DB_RANGE_KEY],
                owner=record[sessions.SESSION_DB_HASH_KEY],
            )
            pytest.fail(
                "Expected 401 error for non-admin user accessing other user's session"
            )
        except Exception as e:
            assert "401" in str(e)
            assert "Non admin user cannot get session info of other users" in str(
                e.response.text  # type: ignore
            )
            logger.info(
                f"Getting other user's session via non-admin user correctly received 401 error: {str(e)}"
            )

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_get_session_with_nonexistent_session(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            api_client.get_session(
                res_session_id="nonexistent-session-999", owner="clusteradmin"
            )
            pytest.fail("Expected 'does not exist' error for non-existent session")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "does not exist" in e.response.text
            ), f"Unexpected error for non-existent session: {str(e)}"
            logger.info(f"Non-existent session correctly received 400 error: {str(e)}")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_get_session_empty_required_property(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            api_client.get_session(res_session_id="test123", owner="")
            pytest.fail("Expected 'should be non-empty' error for missing property")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "should be non-empty" in e.response.text
            ), f"Unexpected error: {str(e)}"

    def test_get_session_with_nonexistent_user(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
    ) -> None:
        try:
            nonexistent_auth = ClientAuth(username="nonexistent_user_12345")
            api_client = ApiClient(res_environment, nonexistent_auth)
            api_client.get_session(
                res_session_id="test123",
                owner="nonexistent_user_12345",
            )
            pytest.fail("Expected 'User not found' error for non-existent user")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "User not found" in e.response.text
            ), f"Unexpected error for non-existent user: {str(e)}"
            logger.info(f"Non-existent user correctly received 401 error: {str(e)}")

    @pytest.mark.parametrize("inactive_username", ["user2"])
    def test_get_session_with_inactive_user(
        self,
        region: str,
        res_environment: ResEnvironment,
        inactive_username: str,
        inactive_user: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, inactive_user)
            api_client.get_session(
                res_session_id="test123",
                owner=inactive_username,
            )
            pytest.fail("Expected error for inactive user")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "Inactive user" in e.response.text
            ), f"Unexpected error for inactive user: {str(e)}"
            logger.info(f"Inactive user correctly received 401 error: {str(e)}")

    def test_get_session_without_auth_token(
        self,
        res_environment: ResEnvironment,
        region: str,
    ) -> None:
        try:
            no_auth = ClientAuth(username="clusteradmin", auth_token=None)
            api_client = ApiClient(res_environment, no_auth)
            api_client.get_session(
                res_session_id="test-session-123", owner="clusteradmin"
            )
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

    def test_get_session_with_invalid_auth_token_in_prod(
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
            api_client.get_session(
                res_session_id="test-session-123", owner="clusteradmin"
            )
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
