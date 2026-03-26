#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Dict

import pytest

from tests.integration.framework.client.api_client import ApiClient
from tests.integration.framework.fixtures.fixture_request import FixtureRequest
from tests.integration.framework.fixtures.project import project
from tests.integration.framework.fixtures.res_environment import (
    ResEnvironment,
    res_environment,
)
from tests.integration.framework.fixtures.users import admin, inactive_user, non_admin
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.lambda_utils import set_backend_lambda_test_mode
from tests.integration.framework.utils.virtual_desktop import (
    get_software_stack_base_payload,
)

logger = logging.getLogger(__name__)


class TestListSessionPermissions:

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_session_permissions_with_valid_request(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            response = api_client.list_session_permissions(res_session_id="amzn2023")

            assert response is not None, "Response should not be None"
            assert response.listing is not None, "Response must contain 'listing' field"
            assert isinstance(response.listing, list), "Response listing must be a list"

            logger.info(
                f"Successfully filtered {len(response.listing)} session permissions by base_os"
            )

        except Exception as e:
            pytest.fail(
                f"Unexpected API error retreiving session permissions: {str(e)}"
            )

    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_list_session_permissions_with_non_admin_user(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, non_admin)
            api_client.list_session_permissions(res_session_id="amzn2023")
            pytest.fail("Expected 401/403 error for non-admin user")
        except Exception as e:
            if "400" in str(e):
                logger.info(
                    f"Only session owner can request to list_session_permissions for session: {str(e)}"
                )
            else:
                pytest.fail(f"Unexpected API error: {str(e)}")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_session_permissions_invalid_user(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            nonexistent_auth = ClientAuth(username="nonexistent_user_12345")
            api_client = ApiClient(res_environment, nonexistent_auth)
            response = api_client.list_session_permissions("idea-session-1234")
            pytest.fail("Expected 400 error missing a required field")
        except Exception as e:
            assert "401" in str(e)
            assert "Failed to check user state: User not found" in str(e.response.text)  # type: ignore

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_session_permissions_invalid_auth_token(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        environment_name: str,
        admin: ClientAuth,
    ) -> None:
        set_backend_lambda_test_mode(region, environment_name, False)
        try:
            api_client = ApiClient(res_environment, admin)
            api_client.list_session_permissions("idea-session-1234")
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
