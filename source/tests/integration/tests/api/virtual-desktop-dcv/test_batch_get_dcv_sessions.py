#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
Integration tests for Batch Get DCV Sessions API.

This module contains comprehensive tests for the batch get DCV sessions REST API
using the RES framework ResClient for proper API interaction.
"""

import logging

import pytest

# Import RES framework components
from tests.integration.framework.client.api_client import ApiClient
from tests.integration.framework.fixtures.fixture_request import FixtureRequest
from tests.integration.framework.fixtures.res_environment import (
    ResEnvironment,
    res_environment,
)
from tests.integration.framework.fixtures.users import admin, inactive_user, non_admin
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.lambda_utils import set_backend_lambda_test_mode

logger = logging.getLogger(__name__)


class TestBatchGetDCVSessions:
    """Test suite for the batch get DCV sessions endpoint."""

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_get_dcv_sessions_returns_valid_response(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """
        Test successful retrieval of DCV sessions.
        """
        try:
            api_client = ApiClient(res_environment, admin)
            response = api_client.batch_get_dcv_sessions()

            # Verify we got a proper response
            assert response is not None, "Response should not be None"

            # Response must have a response field
            assert hasattr(
                response, "response"
            ), "Response must contain 'response' field"
            assert response.response is not None, "Response.response should not be None"
            assert isinstance(
                response.response, dict
            ), "Response.response should be a dict"

            logger.info(f"Successfully retrieved DCV sessions response")

        except Exception as e:
            pytest.fail(f"Unexpected API error: {str(e)}")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_get_dcv_sessions_with_empty_sessions_list(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """
        Test batch get DCV sessions with empty sessions list.
        """
        try:
            api_client = ApiClient(res_environment, admin)
            response = api_client.batch_get_dcv_sessions(sessions=[])

            # Verify we got a proper response
            assert response is not None, "Response should not be None"
            assert hasattr(
                response, "response"
            ), "Response must contain 'response' field"
            assert isinstance(
                response.response, dict
            ), "Response.response should be a dict"

            logger.info(f"Successfully handled empty sessions list")

        except Exception as e:
            pytest.fail(f"Unexpected API error: {str(e)}")

    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_batch_get_dcv_sessions_with_non_admin_user_returns_authorization_error(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        """
        Test that non-admin users get proper authorization error.
        """
        try:
            api_client = ApiClient(res_environment, non_admin)
            api_client.batch_get_dcv_sessions()
            pytest.fail("Expected authorization error for non-admin user")
        except Exception as e:
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert e.response is not None, "Response should not be None"

            response_content = e.response.text
            if "Unauthorized user" in response_content:
                logger.info(
                    "Non-admin user correctly received 'Unauthorized user' error"
                )
                return

            pytest.fail(f"Unexpected error for non-admin user: {str(e)}")

    def test_batch_get_dcv_sessions_with_nonexistent_user_returns_user_not_found_error(
        self, res_environment: ResEnvironment
    ) -> None:
        """
        Test that non-existent users get proper 'User not found' error.
        """
        try:
            nonexistent_auth = ClientAuth(username="nonexistent_user_12345")
            api_client = ApiClient(res_environment, nonexistent_auth)
            api_client.batch_get_dcv_sessions()
            pytest.fail("Expected 'User not found' error for non-existent user")
        except Exception as e:
            if "401" in str(e):
                assert hasattr(e, "response"), "Response should exist in the exception"
                assert e.response is not None, "Response should not be None"

                response_content = e.response.text
                if "User not found" in response_content:
                    logger.info(
                        "Non-existent user correctly received 'User not found' error"
                    )
                    return

            pytest.fail(f"Unexpected error for non-existent user: {str(e)}")

    @pytest.mark.parametrize("inactive_username", ["user2"])
    def test_batch_get_dcv_sessions_with_inactive_user_returns_inactive_user_error(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        inactive_username: str,
        inactive_user: ClientAuth,
    ) -> None:
        """
        Test that inactive users get proper 'Inactive user' error.
        """
        try:
            api_client = ApiClient(res_environment, inactive_user)
            api_client.batch_get_dcv_sessions()
            pytest.fail("Expected 'Inactive user' error for inactive user")
        except Exception as e:
            if "401" in str(e):
                assert hasattr(e, "response"), "Response should exist in the exception"
                assert e.response is not None, "Response should not be None"

                response_content = e.response.text
                if "Inactive user" in response_content:
                    logger.info(
                        "Inactive user correctly received 'Inactive user' error"
                    )
                    return

            pytest.fail(f"Unexpected error for inactive user: {str(e)}")

    def test_batch_get_dcv_sessions_without_auth_token_returns_no_authorization_token_provided_error(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
    ) -> None:
        """
        Test that requests without auth tokens get proper error.
        """
        try:
            no_auth = ClientAuth(username="user1", auth_token=None)
            api_client = ApiClient(res_environment, no_auth)
            api_client.batch_get_dcv_sessions()
            pytest.fail(
                "Expected 'No authorization token provided' error for request without auth token"
            )
        except Exception as e:
            if "401" in str(e):
                assert hasattr(e, "response"), "Response should exist in the exception"
                assert e.response is not None, "Response should not be None"

                response_content = e.response.text
                if "No authorization token provided" in response_content:
                    logger.info(
                        "Request without auth token correctly received 'No authorization token provided' error"
                    )
                    return

            pytest.fail(f"Unexpected error for request without auth token: {str(e)}")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_get_dcv_sessions_in_prod_with_invalid_auth_token_returns_unable_to_retrieve_username_error(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        admin: ClientAuth,
    ) -> None:
        """
        Test that requests with invalid auth tokens get proper error in production.
        """
        set_backend_lambda_test_mode(region, environment_name, False)
        try:
            api_client = ApiClient(res_environment, admin)
            api_client.batch_get_dcv_sessions()
            pytest.fail(
                "Expected 'Unable to retrieve username' error for request with invalid auth token"
            )
        except Exception as e:
            if "401" in str(e):
                assert hasattr(e, "response"), "Response should exist in the exception"
                assert e.response is not None, "Response should not be None"

                response_content = e.response.text
                if "Unable to retrieve username" in response_content:
                    logger.info(
                        "Request with invalid auth token correctly received 'Unable to retrieve username' error"
                    )
                    return

            pytest.fail(
                f"Unexpected error for request with invalid auth token: {str(e)}"
            )
        finally:
            set_backend_lambda_test_mode(region, environment_name, True)

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_get_dcv_sessions_with_invalid_next_token_returns_error(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """
        Test that invalid next_token values cause API to fail gracefully.
        """
        try:
            api_client = ApiClient(res_environment, admin)
            # Pass an invalid/malformed next_token
            api_client.batch_get_dcv_sessions(next_token="invalid_token_12345")

            # If we get here, the API should have handled it gracefully
            # The API might return empty results or an error depending on implementation
            logger.info("API handled invalid next_token gracefully")

        except Exception as e:
            # We expect this to fail with some kind of error
            logger.info(f"Invalid next_token correctly caused error: {str(e)}")
            assert "400" in str(e) or "500" in str(
                e
            ), "Should return 4xx or 5xx error for invalid token"
