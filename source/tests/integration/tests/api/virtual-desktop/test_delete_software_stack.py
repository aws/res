#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Dict

import pytest

from tests.integration.framework.client.api_client import (
    ApiClient,
    CreateSoftwareStackRequestContent,
    CreateSoftwareStackResponseContent,
    DeleteSoftwareStackRequestContent,
)
from tests.integration.framework.fixtures.fixture_request import FixtureRequest
from tests.integration.framework.fixtures.project import project
from tests.integration.framework.fixtures.res_environment import (
    ResEnvironment,
    res_environment,
)
from tests.integration.framework.fixtures.users import admin, inactive_user, non_admin
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.virtual_desktop import (
    get_software_stack_base_payload,
)

logger = logging.getLogger(__name__)


class TestDeleteSoftwareStack:

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_delete_software_stack_with_valid_request(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            payload: Dict[str, Any] = get_software_stack_base_payload(
                region, name="test-software-stack-delete"
            )
            request_content = CreateSoftwareStackRequestContent(**payload)
            response: CreateSoftwareStackResponseContent = (
                api_client.create_software_stack(request_content)
            )
            try:
                delete_request = DeleteSoftwareStackRequestContent(
                    base_os=response.software_stack.base_os
                )
                response = api_client.delete_software_stack(
                    response.software_stack.stack_id, delete_request
                )
                logger.debug(response)
            except Exception as e:
                pytest.fail(
                    f"Unexpected API error while deleting softwarestack: {str(e)}"
                )
        except Exception as e:
            pytest.fail(f"Unexpected API error creating software stack: {str(e)}")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_delete_software_stack_missing_base_os(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:

            api_client = ApiClient(res_environment, admin)
            delete_request = DeleteSoftwareStackRequestContent(base_os=None)
            api_client.delete_software_stack("12345-test", delete_request)

            pytest.fail(f"Exeption should be raised when no base_os is provided")
        except Exception as e:
            assert "400" in str(e)
            assert hasattr(e, "response")
            assert hasattr(e.response, "text")
            assert "'base_os' is a required property" in e.response.text

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_delete_software_stack_invalid_software_stack_id(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            delete_request = DeleteSoftwareStackRequestContent(base_os="amzn2023")
            api_client.delete_software_stack("12345-test", delete_request)

            pytest.fail(f"Exception should be raised when software stack is not found")
        except Exception as e:
            assert "404" in str(e)
            print(f"Expected API error: {str(e)}")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_delete_software_stack_invalid_user(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            # Create a ClientAuth with the admin's token but a nonexistent username
            nonexistent_auth = ClientAuth(username="nonexistent_user_12345")
            api_client = ApiClient(res_environment, nonexistent_auth)
            delete_request = DeleteSoftwareStackRequestContent(base_os="amzn2023")
            api_client.delete_software_stack("12345-test", delete_request)

            pytest.fail(f"Exception should be raised when user is not found")
        except Exception as e:
            assert "401" in str(e)

    def test_delete_software_stack_with_invalid_auth_token_in_prod(
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

            delete_request = DeleteSoftwareStackRequestContent(base_os="amzn2023")
            api_client.delete_software_stack("test-stack-id", delete_request)
            pytest.fail("Expected 401 error for invalid auth token")
        except Exception as e:
            assert "401" in str(e)
            logger.info(f"Invalid auth token correctly received error: {str(e)}")
        finally:
            set_backend_lambda_test_mode(region, environment_name, True)
