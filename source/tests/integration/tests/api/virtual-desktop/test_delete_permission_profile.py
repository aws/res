#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Dict

import pytest

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


class TestDeletePermissionProfile:

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_delete_permission_profile_invalid_profile_id(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            api_client.delete_permission_profile("invalid-profile-id")

            pytest.fail(
                f"Exception should be raised when permission profile is not found"
            )
        except Exception as e:
            assert "404" in str(e)
            print(f"Expected API error: {str(e)}")

    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_delete_permission_profile_with_non_admin_user(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, non_admin)
            api_client.delete_permission_profile("test-permission-profile-delete")
            pytest.fail("Expected 401/403 error for non-admin user")
        except Exception as e:
            if "401" in str(e) or "403" in str(e):
                logger.info(f"Non-admin user correctly denied access: {str(e)}")
            else:
                pytest.fail(f"Unexpected API error: {str(e)}")

    def test_delete_permission_profile_with_invalid_auth_token_in_prod(
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
            invalid_auth = ClientAuth(
                username="clusteradmin", auth_token="invalid_token_12345"
            )
            api_client = ApiClient(res_environment, invalid_auth)

            api_client.delete_permission_profile("test-profile-id")
            pytest.fail("Expected 401 error for invalid auth token")
        except Exception as e:
            assert "401" in str(e)
            logger.info(f"Invalid auth token correctly received error: {str(e)}")
        finally:
            set_backend_lambda_test_mode(region, environment_name, True)
