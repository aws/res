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
    CreatePermissionProfileRequestContent,
    CreatePermissionProfileResponseContent,
)
from tests.integration.framework.fixtures.fixture_request import FixtureRequest
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


class TestCreatePermissionProfile:
    """Test suite for the create permission profile endpoint."""

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_permission_profile_with_valid_request(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        api_client = ApiClient(res_environment, admin)
        created_profile_id = None

        try:
            payload: Dict[str, Any] = get_permission_profile_base_payload(
                "valid-test-profile"
            )
            request_content = CreatePermissionProfileRequestContent(**payload)
            response: CreatePermissionProfileResponseContent = (
                api_client.create_permission_profile(request_content)
            )

            assert response is not None
            assert hasattr(response, "profile")
            assert response.profile is not None

            profile = response.profile
            created_profile_id = profile.profile_id
            assert hasattr(profile, "profile_id") and profile.profile_id is not None
            assert hasattr(profile, "title") and profile.title is not None
            assert hasattr(profile, "description") and profile.description is not None
            assert hasattr(profile, "permissions") and profile.permissions is not None
            assert isinstance(profile.permissions, list)

            # Verify permissions structure
            for permission in profile.permissions:
                assert hasattr(permission, "key") and permission.key is not None
                assert hasattr(permission, "name") and permission.name is not None
                assert hasattr(permission, "enabled") and permission.enabled is not None

            logger.info(f"Created permission profile: {profile.profile_id}")

        except Exception as e:
            pytest.fail(f"Unexpected API error: {str(e)}")
        finally:
            # Cleanup
            if created_profile_id:
                try:
                    api_client.delete_permission_profile(created_profile_id)
                    logger.info(f"Cleaned up permission profile: {created_profile_id}")
                except Exception as cleanup_error:
                    logger.warning(
                        f"Failed to cleanup profile {created_profile_id}: {cleanup_error}"
                    )

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_permission_profile_empty_payload(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            payload: Dict[str, Any] = {}
            request_content = CreatePermissionProfileRequestContent(**payload)
            response: CreatePermissionProfileResponseContent = (
                api_client.create_permission_profile(request_content)
            )

            assert response is not None
            pytest.fail(f"Error failed to validate empty payload")
        except Exception as e:
            assert "400" in str(e)
            if hasattr(e, "response") and hasattr(e.response, "text"):
                assert "'profile' is a required property" in e.response.text
            else:
                assert "'profile' is a required property" in str(e)
            assert hasattr(e, "response") and e.response.status_code == 400

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_permission_profile_missing_required_fields(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            payload = {"profile": {"title": "Test Profile"}}

            request_content = CreatePermissionProfileRequestContent(**payload)
            response = api_client.create_permission_profile(request_content)
            pytest.fail("Expected 400 error for missing profile_id")
        except Exception as e:
            assert "400" in str(e)
            assert hasattr(e, "response")
            assert hasattr(e.response, "text")
            assert "'profile_id' is a required property" in e.response.text

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_permission_profile_duplicate_profile_id(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        api_client = ApiClient(res_environment, admin)
        profile_id = "duplicate-test-profile"
        created_profile_id = None

        try:
            # First request should succeed
            payload1 = get_permission_profile_base_payload(profile_id)
            request_content1 = CreatePermissionProfileRequestContent(**payload1)
            response1 = api_client.create_permission_profile(request_content1)
            assert response1 is not None
            assert hasattr(response1, "profile") and response1.profile is not None
            assert response1.profile.profile_id is not None
            created_profile_id = response1.profile.profile_id

            # Second request with same profile_id should fail
            try:
                payload2 = get_permission_profile_base_payload(profile_id)
                request_content2 = CreatePermissionProfileRequestContent(**payload2)
                api_client.create_permission_profile(request_content2)
                pytest.fail("Expected error for duplicate permission profile ID")
            except Exception as e:
                assert "400" in str(e)
                assert f"profile_id: {profile_id} already exists" in e.response.text
                logger.info(f"Correctly received duplicate profile_id error: {str(e)}")

            logger.info(f"Created permission profile for duplicate test: {profile_id}")

        finally:
            # Cleanup
            if created_profile_id:
                try:
                    api_client.delete_permission_profile(created_profile_id)
                    logger.info(f"Cleaned up permission profile: {created_profile_id}")
                except Exception as cleanup_error:
                    logger.warning(
                        f"Failed to cleanup profile {created_profile_id}: {cleanup_error}"
                    )

    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_create_permission_profile_with_non_admin_user(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, non_admin)
            payload = get_permission_profile_base_payload("non-admin-test")
            request_content = CreatePermissionProfileRequestContent(**payload)
            api_client.create_permission_profile(request_content)
            pytest.fail("Expected 401/403 error for non-admin user")
        except Exception as e:
            if "401" in str(e) or "403" in str(e):
                logger.info(f"Non-admin user correctly denied access: {str(e)}")
            else:
                pytest.fail(f"Unexpected API error: {str(e)}")

    @pytest.mark.parametrize("inactive_username", ["user2"])
    def test_create_permission_profile_with_inactive_user(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        inactive_username: str,
        inactive_user: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, inactive_user)
            payload = get_permission_profile_base_payload("inactive-user-test")
            request_content = CreatePermissionProfileRequestContent(**payload)
            api_client.create_permission_profile(request_content)
            pytest.fail("Expected error for inactive user")
        except Exception as e:
            assert "401" in str(e)
            logger.info(f"Correctly received inactive user error: {str(e)}")

    def test_create_permission_profile_with_nonexistent_user(
        self, res_environment: ResEnvironment, region: str
    ) -> None:
        try:
            nonexistent_auth = ClientAuth(username="nonexistent_user_12345")
            api_client = ApiClient(res_environment, nonexistent_auth)
            payload = get_permission_profile_base_payload("nonexistent-user-test")
            request_content = CreatePermissionProfileRequestContent(**payload)
            api_client.create_permission_profile(request_content)
            pytest.fail("Expected 'User not found' error for non-existent user")
        except Exception as e:
            assert "401" in str(e)
            logger.info(f"Non-existent user correctly received error: {str(e)}")

    def test_create_permission_profile_without_auth_token(
        self, res_environment: ResEnvironment, region: str
    ) -> None:
        try:
            no_auth = ClientAuth(username="user1", auth_token=None)
            api_client = ApiClient(res_environment, no_auth)
            payload = get_permission_profile_base_payload("no-auth-test")
            request_content = CreatePermissionProfileRequestContent(**payload)
            api_client.create_permission_profile(request_content)
            pytest.fail("Expected 'No authorization token provided' error")
        except Exception as e:
            assert "401" in str(e)
            logger.info(
                f"Request without auth token correctly received error: {str(e)}"
            )

    def test_create_permission_profile_with_invalid_auth_token_in_prod(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
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
            payload = get_permission_profile_base_payload("invalid-auth-test")
            request_content = CreatePermissionProfileRequestContent(**payload)
            api_client.create_permission_profile(request_content)
            pytest.fail(
                "Expected 'Unable to retrieve username' error for invalid auth token"
            )
        except Exception as e:
            assert "401" in str(e)
            logger.info(f"Invalid auth token correctly received error: {str(e)}")
        finally:
            set_backend_lambda_test_mode(region, environment_name, True)
