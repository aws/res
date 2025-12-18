#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
Integration tests for Virtual Desktop Schedule Type API.

This module contains comprehensive tests for the virtual desktop schedule type REST API
using the RES framework ResClient for proper API interaction.
"""

import logging

import pytest

from tests.integration.framework.fixtures.fixture_request import FixtureRequest

# Import backend model classes using the utility function
from tests.integration.framework.utils.model_utils import get_backend_model_class

# Import backend model classes
VirtualDesktopScheduleType = get_backend_model_class(
    "virtual_desktop_schedule_type", "VirtualDesktopScheduleType"
)

# Import RES framework components
from tests.integration.framework.client.api_client import ApiClient
from tests.integration.framework.fixtures.res_environment import (
    ResEnvironment,
    res_environment,
)
from tests.integration.framework.fixtures.users import admin, inactive_user, non_admin
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.lambda_utils import set_backend_lambda_test_mode

logger = logging.getLogger(__name__)


class TestListScheduleTypes:
    """Test suite for the list schedule types endpoint."""

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_list_schedule_types_returns_valid_response(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """
        Test successful retrieval of schedule types.
        """
        try:
            api_client = ApiClient(res_environment, admin)
            response = api_client.list_schedule_types()

            # Verify we got a proper response content object
            assert response is not None, "Response should not be None"
            assert hasattr(
                response, "listing"
            ), "Response should have listing attribute"
            assert isinstance(response.listing, list), "Listing should be a list"

            # Verify each item in the listing is a valid VirtualDesktopScheduleType enum value
            valid_schedule_values = [
                schedule.value for schedule in VirtualDesktopScheduleType
            ]
            for schedule_item in response.listing:
                assert (
                    schedule_item in valid_schedule_values
                ), f"Schedule type '{schedule_item}' is not a valid VirtualDesktopScheduleType enum value. Valid values: {valid_schedule_values}"

            logger.info(
                f"Successfully retrieved {len(response.listing)} schedule types: {response.listing}"
            )

        except Exception as e:
            pytest.fail(f"Unexpected API error: {str(e)}")

    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_list_schedule_types_with_non_admin_user_returns_authorization_error(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        """
        Test that non-admin users get proper authorization error for schedule type endpoint.
        """
        try:
            api_client = ApiClient(res_environment, non_admin)
            api_client.list_schedule_types()
            pytest.fail("Expected authorization error for non-admin user")
        except Exception as e:
            # For 401 errors, we need to check the response content for "Unauthorized user"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert e.response is not None, "Response should not be None"

            response_content = e.response.text
            if "Unauthorized user" in response_content:
                logger.info(
                    "Non-admin user correctly received 'Unauthorized user' error for schedule type endpoint"
                )
                return  # Test passes

            pytest.fail(f"Unexpected error for non-admin user: {str(e)}")

    def test_list_schedule_types_with_nonexistent_user_returns_user_not_found_error(
        self, res_environment: ResEnvironment
    ) -> None:
        """
        Test that non-existent users get proper 'User not found' error for schedule type endpoint.
        This test verifies that the API properly validates user existence and returns appropriate error.
        """
        try:
            nonexistent_auth = ClientAuth(username="nonexistent_user_12345")
            api_client = ApiClient(res_environment, nonexistent_auth)
            api_client.list_schedule_types()
            pytest.fail("Expected 'User not found' error for non-existent user")
        except Exception as e:
            # Check if it's a 401 error (which is expected for non-existent users)
            if "401" in str(e):
                # For 401 errors, we need to check the response content for "User not found"
                assert hasattr(e, "response"), "Response should exist in the exception"
                assert e.response is not None, "Response should not be None"

                response_content = e.response.text
                if "User not found" in response_content:
                    logger.info(
                        "Non-existent user correctly received 'User not found' error for schedule type endpoint"
                    )
                    return  # Test passes

            pytest.fail(f"Unexpected error for non-existent user: {str(e)}")

    @pytest.mark.parametrize("inactive_username", ["user2"])
    def test_list_schedule_types_with_inactive_user_returns_inactive_user_error(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        inactive_username: str,
        inactive_user: ClientAuth,
    ) -> None:
        """
        Test that inactive users get proper 'Inactive user' error for schedule type endpoint.

        Inactive users should not be able to access any API endpoints and should
        receive appropriate error responses indicating their account status.
        """
        try:
            api_client = ApiClient(res_environment, inactive_user)
            api_client.list_schedule_types()
            pytest.fail("Expected 'Inactive user' error for inactive user")
        except Exception as e:
            # Check if it's a 401/403 error (which is expected for inactive users)
            if "401" in str(e):
                # For 401/403 errors, check the response content for appropriate messages
                # For 401 errors, check the response content for appropriate messages
                assert hasattr(e, "response"), "Response should exist in the exception"
                assert e.response is not None, "Response should not be None"

                response_content = e.response.text
                if "Inactive user" in response_content:
                    logger.info(
                        f"Inactive user correctly received 'Inactive user' error for schedule type endpoint: {e.response.text}"
                    )
                    return  # Test passes

            pytest.fail(f"Unexpected error for inactive user: {str(e)}")

    def test_list_schedule_types_without_auth_token_returns_no_authorization_token_provided_error(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
    ) -> None:
        """
        Test that requests without auth tokens get proper 'No authorization token provided' error for schedule type endpoint.

        Requests without proper authorization tokens should be rejected with appropriate
        error responses indicating missing or invalid authorization.
        """
        try:
            no_auth = ClientAuth(username="user1", auth_token=None)
            api_client = ApiClient(res_environment, no_auth)
            api_client.list_schedule_types()
            pytest.fail(
                "Expected 'No authorization token provided' error for request without auth token"
            )
        except Exception as e:
            # Check if it's a 401 error (which is expected for missing auth tokens)
            if "401" in str(e):
                # For 401 errors, check the response content for appropriate messages
                assert hasattr(e, "response"), "Response should exist in the exception"
                assert e.response is not None, "Response should not be None"

                response_content = e.response.text
                if "No authorization token provided" in response_content:
                    logger.info(
                        f"Request without auth token correctly received 'No authorization token provided' error for schedule type endpoint: {e.response.text}"
                    )
                    return  # Test passes

            pytest.fail(f"Unexpected error for request without auth token: {str(e)}")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_list_schedule_types_in_prod_with_invalid_auth_token_returns_unable_to_retrieve_username_error(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """
        Test that requests with invalid auth tokens get proper 'Unable to retrieve username' error for schedule type endpoint.

        Requests without proper authorization tokens should be rejected with appropriate
        error responses indicating missing or invalid authorization.
        """
        set_backend_lambda_test_mode(region, environment_name, False)
        try:
            api_client = ApiClient(res_environment, admin)
            api_client.list_schedule_types()
            pytest.fail(
                "Expected 'Unable to retrieve username' error for request with invalid auth token"
            )
        except Exception as e:
            # Check if it's a 401 error (which is expected for missing auth tokens)
            if "401" in str(e):
                # For 401 errors, check the response content for appropriate messages
                assert hasattr(e, "response"), "Response should exist in the exception"
                assert e.response is not None, "Response should not be None"

                response_content = e.response.text
                if "Unable to retrieve username" in response_content:
                    logger.info(
                        f"Request with invalid auth token correctly received 'Unable to retrieve username' error for schedule type endpoint: {e.response.text}"
                    )
                    return  # Test passes

            pytest.fail(
                f"Unexpected error for request with invalid auth token: {str(e)}"
            )
        finally:
            set_backend_lambda_test_mode(region, environment_name, True)
