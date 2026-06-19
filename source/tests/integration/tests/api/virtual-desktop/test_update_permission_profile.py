#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
Integration tests for Create Permission Profile API.

This module contains comprehensive tests for the create permission profile REST API
using the RES framework ResClient for proper API interaction.
"""

import logging
from typing import Any, Dict

import pytest

# Import RES framework components
from tests.integration.framework.client.api_client import (
    ApiClient,
    UpdatePermissionProfileRequestContent,
    UpdatePermissionProfileResponseContent,
)
from tests.integration.framework.fixtures.fixture_request import FixtureRequest
from tests.integration.framework.fixtures.permission_profile import permission_profile
from tests.integration.framework.fixtures.res_environment import (
    ResEnvironment,
    res_environment,
)
from tests.integration.framework.fixtures.users import admin, inactive_user, non_admin
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.virtual_desktop import (
    get_permission_profile_base_payload,
)

logger = logging.getLogger(__name__)

TEST_PROFILE_ID = "test-profile-id"


class TestUpdatePermissionProfile:
    """Test suite for the create permission profile endpoint."""

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    @pytest.mark.parametrize(
        "permission_profile", [(TEST_PROFILE_ID, {}, "admin")], indirect=True
    )
    def test_update_permission_profile_with_valid_request(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
        permission_profile: Any,
    ) -> None:
        api_client = ApiClient(res_environment, admin)

        try:
            payload: Dict[str, Any] = get_permission_profile_base_payload(
                TEST_PROFILE_ID
            )
            payload["profile"]["title"] = "Updated Test Permission Profile"
            request_content = UpdatePermissionProfileRequestContent(**payload)
            response: UpdatePermissionProfileResponseContent = (
                api_client.update_permission_profile(TEST_PROFILE_ID, request_content)
            )

            assert response is not None
            assert hasattr(response, "profile")
            assert response.profile is not None

            profile = response.profile
            assert profile.profile_id == TEST_PROFILE_ID
            assert profile.title == "Updated Test Permission Profile"
            assert profile.description == payload["profile"]["description"]
            assert isinstance(profile.permissions, list)
            assert len(profile.permissions) == len(payload["profile"]["permissions"])

            # Verify permissions structure
            for index, permission in enumerate(profile.permissions):
                assert permission.key == payload["profile"]["permissions"][index]["key"]
                assert (
                    permission.name == payload["profile"]["permissions"][index]["name"]
                )
                assert (
                    permission.enabled
                    == payload["profile"]["permissions"][index]["enabled"]
                )

            logger.info(f"Updated permission profile: {profile.profile_id}")

        except Exception as e:
            pytest.fail(f"Unexpected API error: {str(e)}")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    @pytest.mark.parametrize(
        "permission_profile", [(TEST_PROFILE_ID, {}, "admin")], indirect=True
    )
    def test_update_permission_profile_empty_payload(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
        permission_profile: Any,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            payload: Dict[str, Any] = {}
            request_content = UpdatePermissionProfileRequestContent(**payload)
            response: UpdatePermissionProfileResponseContent = (
                api_client.update_permission_profile(TEST_PROFILE_ID, request_content)
            )

            assert response is not None
            pytest.fail(f"Error failed to validate empty payload")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "'profile' is a required property" in e.response.text
            ), f"Unexpected error: {str(e)}"

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    @pytest.mark.parametrize(
        "permission_profile", [(TEST_PROFILE_ID, {}, "admin")], indirect=True
    )
    def test_update_permission_profile_missing_required_fields(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
        permission_profile: Any,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            payload = {"profile": {"title": "Test Profile"}}

            request_content = UpdatePermissionProfileRequestContent(**payload)
            response = api_client.update_permission_profile(
                TEST_PROFILE_ID, request_content
            )
            pytest.fail("Expected 400 error for missing profile_id")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "'profile_id' is a required property" in e.response.text
            ), f"Unexpected error: {str(e)}"

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    @pytest.mark.parametrize(
        "permission_profile", [(TEST_PROFILE_ID, {}, "admin")], indirect=True
    )
    def test_update_permission_profile_mismatched_profile_id(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
        permission_profile: Any,
    ) -> None:
        api_client = ApiClient(res_environment, admin)

        try:
            payload = get_permission_profile_base_payload("another-test-profile")
            request_content = UpdatePermissionProfileRequestContent(**payload)
            _response = api_client.update_permission_profile(
                TEST_PROFILE_ID, request_content
            )
            pytest.fail("Expected error for mismatched permission profile ID")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                f"Profile ID: {TEST_PROFILE_ID} does not match the permission profile to update: another-test-profile"
                in e.response.text
            ), f"Unexpected error: {str(e)}"

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    @pytest.mark.parametrize(
        "permission_profile", [(TEST_PROFILE_ID, {}, "admin")], indirect=True
    )
    def test_update_permission_profile_nonexistent_profile_id(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
        permission_profile: Any,
    ) -> None:
        api_client = ApiClient(res_environment, admin)

        try:
            payload = get_permission_profile_base_payload("another-test-profile")
            request_content = UpdatePermissionProfileRequestContent(**payload)
            _response = api_client.update_permission_profile(
                "another-test-profile", request_content
            )
            pytest.fail("Expected error for nonexistent permission profile ID")
        except Exception as e:
            assert "404" in str(e), f"Expected 404 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "Profile ID: another-test-profile does not exist" in e.response.text
            ), f"Unexpected error: {str(e)}"

    @pytest.mark.parametrize("non_admin_username", ["user1"])
    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    @pytest.mark.parametrize(
        "permission_profile", [(TEST_PROFILE_ID, {}, "admin")], indirect=True
    )
    def test_update_permission_profile_with_non_admin_user(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        non_admin_username: str,
        non_admin: ClientAuth,
        admin_username: str,
        admin: ClientAuth,
        permission_profile: Any,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, non_admin)
            payload = get_permission_profile_base_payload(TEST_PROFILE_ID)
            request_content = UpdatePermissionProfileRequestContent(**payload)
            api_client.update_permission_profile(TEST_PROFILE_ID, request_content)
            pytest.fail("Expected 401/403 error for non-admin user")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert "Unauthorized user" in e.response.text, f"Unexpected error: {str(e)}"

    @pytest.mark.parametrize("inactive_username", ["user2"])
    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    @pytest.mark.parametrize(
        "permission_profile", [(TEST_PROFILE_ID, {}, "admin")], indirect=True
    )
    def test_update_permission_profile_with_inactive_user(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        inactive_username: str,
        inactive_user: ClientAuth,
        admin_username: str,
        admin: ClientAuth,
        permission_profile: Any,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, inactive_user)
            payload = get_permission_profile_base_payload(TEST_PROFILE_ID)
            request_content = UpdatePermissionProfileRequestContent(**payload)
            api_client.update_permission_profile(TEST_PROFILE_ID, request_content)
            pytest.fail("Expected error for inactive user")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "Inactive user" in e.response.text
            ), f"Unexpected error for inactive user: {str(e)}"

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    @pytest.mark.parametrize(
        "permission_profile", [(TEST_PROFILE_ID, {}, "admin")], indirect=True
    )
    def test_update_permission_profile_with_nonexistent_user(
        self,
        res_environment: ResEnvironment,
        region: str,
        admin_username: str,
        admin: ClientAuth,
        permission_profile: Any,
    ) -> None:
        try:
            nonexistent_auth = ClientAuth(username="nonexistent_user_12345")
            api_client = ApiClient(res_environment, nonexistent_auth)
            payload = get_permission_profile_base_payload(TEST_PROFILE_ID)
            request_content = UpdatePermissionProfileRequestContent(**payload)
            api_client.update_permission_profile(TEST_PROFILE_ID, request_content)
            pytest.fail("Expected 'User not found' error for non-existent user")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "User not found" in e.response.text
            ), f"Unexpected error for non-existent user: {str(e)}"

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    @pytest.mark.parametrize(
        "permission_profile", [(TEST_PROFILE_ID, {}, "admin")], indirect=True
    )
    def test_update_permission_profile_without_auth_token(
        self,
        res_environment: ResEnvironment,
        region: str,
        admin_username: str,
        admin: ClientAuth,
        permission_profile: Any,
    ) -> None:
        try:
            no_auth = ClientAuth(username="user1", auth_token=None)
            api_client = ApiClient(res_environment, no_auth)
            payload = get_permission_profile_base_payload(TEST_PROFILE_ID)
            request_content = UpdatePermissionProfileRequestContent(**payload)
            api_client.update_permission_profile(TEST_PROFILE_ID, request_content)
            pytest.fail("Expected 'No authorization token provided' error")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "No authorization token provided" in e.response.text
            ), f"Unexpected error for request without auth token: {str(e)}"

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    @pytest.mark.parametrize(
        "permission_profile", [(TEST_PROFILE_ID, {}, "admin")], indirect=True
    )
    def test_update_permission_profile_with_invalid_auth_token_in_prod(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        admin_username: str,
        admin: ClientAuth,
        permission_profile: Any,
    ) -> None:
        from tests.integration.framework.utils.lambda_utils import (
            set_backend_lambda_test_mode,
        )

        set_backend_lambda_test_mode(region, environment_name, False)
        try:
            # Create ClientAuth with invalid token
            invalid_auth = ClientAuth(
                username="clusteradmin", auth_token="invalid_token_12345"
            )
            api_client = ApiClient(res_environment, invalid_auth)
            payload = get_permission_profile_base_payload(TEST_PROFILE_ID)
            request_content = UpdatePermissionProfileRequestContent(**payload)
            api_client.update_permission_profile(TEST_PROFILE_ID, request_content)
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
