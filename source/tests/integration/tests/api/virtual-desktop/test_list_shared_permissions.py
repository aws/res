#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging

import pytest

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


class TestListSharedPermissions:

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_list_shared_permissions_with_valid_request(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            response = api_client.list_shared_permissions(username=admin_username)

            assert response is not None, "Response should not be None"
            assert response.listing is not None, "Response must contain 'listing' field"
            assert isinstance(response.listing, list), "Response listing must be a list"

            logger.info(
                f"Successfully retrieved {len(response.listing)} shared permissions"
            )

        except Exception as e:
            pytest.fail(f"Unexpected API error retrieving shared permissions: {str(e)}")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_list_shared_permissions_without_username(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            response = api_client.list_shared_permissions()

            assert response is not None, "Response should not be None"
            assert response.listing is not None, "Response must contain 'listing' field"
            assert isinstance(response.listing, list), "Response listing must be a list"

            logger.info(
                f"Successfully retrieved {len(response.listing)} shared permissions without username filter"
            )

        except Exception as e:
            pytest.fail(
                f"Unexpected API error retrieving shared permissions without username: {str(e)}"
            )

    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_list_shared_permissions_with_non_admin_user_own_permissions(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, non_admin)
            # Non-admin user requesting their own permissions should work
            response = api_client.list_shared_permissions(username=non_admin_username)

            assert response is not None, "Response should not be None"
            assert response.listing is not None, "Response must contain 'listing' field"
            assert isinstance(response.listing, list), "Response listing must be a list"

            logger.info(
                f"Non-admin user successfully retrieved their own shared permissions: {len(response.listing)} items"
            )

        except Exception as e:
            pytest.fail(
                f"Unexpected API error for non-admin user accessing own permissions: {str(e)}"
            )

    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_list_shared_permissions_with_non_admin_user_other_permissions(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, non_admin)
            # Non-admin user requesting other user's permissions should fail
            api_client.list_shared_permissions(username="other_user")
            pytest.fail(
                "Expected 403 error for non-admin user accessing other user's permissions"
            )
        except Exception as e:
            assert "401" in str(e)
            assert "Non admin user cannot list shared permissions of other users" in str(e.response.text)  # type: ignore
            logger.info(
                f"Listing other user's shared permissions via non-admin user correctly received 401 error: {str(e)}"
            )

    @pytest.mark.parametrize("inactive_username", ["user2"])
    def test_list_shared_permissions_with_inactive_user(
        self,
        region: str,
        res_environment: ResEnvironment,
        inactive_username: str,
        inactive_user: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, inactive_user)
            api_client.list_shared_permissions(username=inactive_username)
            pytest.fail("Expected error for inactive user")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "Inactive user" in e.response.text
            ), f"Unexpected error for inactive user: {str(e)}"
            logger.info(f"Inactive user correctly received 401 error: {str(e)}")

    def test_list_shared_permissions_with_nonexistent_user(
        self,
        res_environment: ResEnvironment,
        region: str,
    ) -> None:
        try:
            nonexistent_auth = ClientAuth(username="nonexistent_user_12345")
            api_client = ApiClient(res_environment, nonexistent_auth)
            api_client.list_shared_permissions(username="nonexistent_user_12345")
            pytest.fail("Expected 'User not found' error for non-existent user")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "User not found" in e.response.text
            ), f"Unexpected error for non-existent user: {str(e)}"
            logger.info(f"Non-existent user correctly received 401 error: {str(e)}")

    def test_list_shared_permissions_without_auth_token(
        self,
        res_environment: ResEnvironment,
        region: str,
    ) -> None:
        try:
            no_auth = ClientAuth(username="clusteradmin", auth_token=None)
            api_client = ApiClient(res_environment, no_auth)
            api_client.list_shared_permissions(username="clusteradmin")
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

    def test_list_shared_permissions_with_invalid_auth_token_in_prod(
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
            api_client.list_shared_permissions(username="clusteradmin")
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
