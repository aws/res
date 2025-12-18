#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
Integration tests for List Permission Profiles API.

This module contains comprehensive tests for the list permission profiles REST API
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


class TestListPermissionProfiles:
    """Test suite for the list permission profiles endpoint."""

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_list_permission_profiles_returns_valid_response(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """
        Test successful retrieval of permission profiles.
        """
        try:
            api_client = ApiClient(res_environment, admin)
            response = api_client.list_permission_profiles()

            # Verify we got a proper response
            assert response is not None, "Response should not be None"

            # Response must always have a listing field
            assert response.listing is not None, "Response must contain 'listing' field"
            assert isinstance(response.listing, list), "Listing should be a list"

            # Verify each profile has required fields
            for profile in response.listing:
                assert profile.profile_id is not None, "Profile must have profile_id"
                assert profile.title is not None, "Profile must have title"
                assert profile.permissions is not None, "Profile must have permissions"
                assert isinstance(
                    profile.permissions, list
                ), "Permissions should be a list"

            logger.info(
                f"Successfully retrieved {len(response.listing)} permission profiles"
            )

        except Exception as e:
            pytest.fail(f"Unexpected API error: {str(e)}")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_list_permission_profiles_with_filter_returns_filtered_results(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """
        Test filtering permission profiles by profile_id substring.
        """
        try:
            api_client = ApiClient(res_environment, admin)
            # First get all profiles
            all_response = api_client.list_permission_profiles()
            all_profiles = all_response.listing if all_response.listing else []  # type: ignore

            if len(all_profiles) == 0:
                pytest.skip("No profiles available to test filtering")

            # Get the first profile's ID and use part of it as filter
            first_profile_id = all_profiles[0].profile_id
            filter_substring = (
                first_profile_id[:5] if len(first_profile_id) >= 5 else first_profile_id
            )

            # Filter by substring
            filtered_response = api_client.list_permission_profiles(
                profile_id=filter_substring
            )
            filtered_profiles = (
                filtered_response.listing if filtered_response.listing else []  # type: ignore
            )

            # Verify all returned profiles contain the filter substring
            for profile in filtered_profiles:
                assert (
                    filter_substring.lower() in profile.profile_id.lower()
                ), f"Profile {profile.profile_id} should contain filter '{filter_substring}'"

            logger.info(
                f"Successfully filtered profiles: {len(filtered_profiles)} profiles contain '{filter_substring}'"
            )

        except Exception as e:
            pytest.fail(f"Unexpected API error: {str(e)}")

    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_list_permission_profiles_with_non_admin_user_returns_authorization_error(
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
            api_client.list_permission_profiles()
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

    def test_list_permission_profiles_with_nonexistent_user_returns_user_not_found_error(
        self, res_environment: ResEnvironment
    ) -> None:
        """
        Test that non-existent users get proper 'User not found' error.
        """
        try:
            nonexistent_auth = ClientAuth(username="nonexistent_user_12345")
            api_client = ApiClient(res_environment, nonexistent_auth)
            api_client.list_permission_profiles()
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
    def test_list_permission_profiles_with_inactive_user_returns_inactive_user_error(
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
            api_client.list_permission_profiles()
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

    def test_list_permission_profiles_without_auth_token_returns_no_authorization_token_provided_error(
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
            api_client.list_permission_profiles()
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
    def test_list_permission_profiles_in_prod_with_invalid_auth_token_returns_unable_to_retrieve_username_error(
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
            api_client.list_permission_profiles()
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
