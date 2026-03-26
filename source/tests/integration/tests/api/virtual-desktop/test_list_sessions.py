#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
Integration tests for List Sessions API.

This module contains comprehensive tests for the list sessions REST API
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


class TestListSessions:

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_list_sessions_with_valid_request(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            response = api_client.list_sessions(base_os="amzn2023")

            assert response is not None, "Response should not be None"
            assert response.listing is not None, "Response must contain 'listing' field"
            assert isinstance(response.listing, list), "Listing should be a list"

            logger.info(
                f"Successfully filtered {len(response.listing)} sessions by base_os"
            )

        except Exception as e:
            pytest.fail(f"Unexpected API error retreiving sessions: {str(e)}")

            assert "401" in str(e)
            assert "Failed to check user state: User not found" in str(e.response.text)

    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_list_sessions_with_non_admin_user_own_session(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, non_admin)
            response = api_client.list_sessions()

            assert response is not None, "Response should not be None"
            assert response.listing is not None, "Response must contain 'listing' field"
            assert isinstance(response.listing, list), "Listing should be a list"

            logger.info(
                f"Non-admin user successfully retrieved their own sessions: {len(response.listing)} items"
            )

        except Exception as e:
            pytest.fail(
                f"Unexpected API error for non-admin user accessing own sessions: {str(e)}"
            )

    @pytest.mark.parametrize("inactive_username", ["user2"])
    def test_list_sessions_with_inactive_user(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        inactive_username: str,
        inactive_user: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, inactive_user)
            api_client.list_sessions()
            pytest.fail("Expected error for inactive user")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "Inactive user" in e.response.text
            ), f"Unexpected error for inactive user: {str(e)}"
            logger.info(f"Inactive user correctly received 401 error: {str(e)}")

    def test_list_sessions_with_nonexistent_user(
        self,
        res_environment: ResEnvironment,
        region: str,
    ) -> None:
        try:
            nonexistent_auth = ClientAuth(username="nonexistent_user_12345")
            api_client = ApiClient(res_environment, nonexistent_auth)
            api_client.list_sessions()
            pytest.fail("Expected 'User not found' error for non-existent user")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "User not found" in e.response.text
            ), f"Unexpected error for non-existent user: {str(e)}"
            logger.info(f"Non-existent user correctly received 401 error: {str(e)}")

    def test_list_sessions_without_auth_token(
        self,
        res_environment: ResEnvironment,
        region: str,
    ) -> None:
        try:
            no_auth = ClientAuth(username="clusteradmin", auth_token=None)
            api_client = ApiClient(res_environment, no_auth)
            api_client.list_sessions()
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

    def test_list_sessions_with_invalid_auth_token_in_prod(
        self,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
    ) -> None:
        set_backend_lambda_test_mode(region, environment_name, False)
        try:
            # Create ClientAuth with invalid token
            invalid_auth = ClientAuth(
                username="clusteradmin", auth_token="invalid_token_12345"
            )
            api_client = ApiClient(res_environment, invalid_auth)
            api_client.list_sessions()
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

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_list_sessions_with_owner_filter(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """
        Test that a user can list sessions of a different owner using the owner filter.
        This tests the new 'owner' parameter that allows admins to view sessions of other users.
        """
        try:
            api_client = ApiClient(res_environment, admin)

            # List sessions with owner filter for a different user
            # Using 'user1' as the target owner
            response = api_client.list_sessions(owner="user1")

            assert response is not None, "Response should not be None"
            assert response.listing is not None, "Response must contain 'listing' field"
            assert isinstance(response.listing, list), "Listing should be a list"

            # Verify that all returned sessions belong to the specified owner
            for session in response.listing:
                assert (
                    session.owner == "user1"
                ), f"Expected owner 'user1' but got '{session.owner}'"

            logger.info(
                f"Admin successfully retrieved {len(response.listing)} sessions for owner 'user1'"
            )

        except Exception as e:
            pytest.fail(
                f"Unexpected API error when admin lists sessions by owner: {str(e)}"
            )
