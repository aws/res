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


class TestCreateSoftwareStack:

    @pytest.mark.skip(
        reason="Temporarily Skipping Test - While Adding DeleteSoftwareStack"
    )
    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_software_stack_with_valid_request(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            payload: Dict[str, Any] = get_software_stack_base_payload(region)
            request_content = CreateSoftwareStackRequestContent(**payload)
            response: CreateSoftwareStackResponseContent = (
                api_client.create_software_stack(request_content)
            )

            assert response is not None
            assert hasattr(response, "software_stack")
            assert response.software_stack is not None
            assert hasattr(response.software_stack, "stack_id")
            stack = response.software_stack
            assert hasattr(stack, "base_os") and stack.base_os is not None
            assert hasattr(stack, "name") and stack.name is not None
            assert hasattr(stack, "description") and stack.description is not None
            assert hasattr(stack, "ami_id") and stack.ami_id is not None

            # Assert min_storage structure
            assert hasattr(stack, "min_storage") and stack.min_storage is not None
            assert (
                hasattr(stack.min_storage, "value")
                and stack.min_storage.value is not None
            )
            assert (
                hasattr(stack.min_storage, "unit")
                and stack.min_storage.unit is not None
            )

            # Assert min_ram structure
            assert hasattr(stack, "min_ram") and stack.min_ram is not None
            assert hasattr(stack.min_ram, "value") and stack.min_ram.value is not None
            assert hasattr(stack.min_ram, "unit") and stack.min_ram.unit is not None

            # Assert other fields
            assert hasattr(stack, "gpu") and stack.gpu is not None
            assert hasattr(stack, "placement")
            assert (
                hasattr(stack.placement, "tenancy")
                and stack.placement.tenancy is not None
            )
            assert hasattr(stack, "allowed_instance_types")

            # Assert projects is a list
            assert hasattr(stack, "projects")
            assert isinstance(stack.projects, list)

            try:
                delete_request = DeleteSoftwareStackRequestContent(
                    base_os=stack.base_os
                )
                api_client.delete_software_stack(stack.stack_id, delete_request)
            except Exception as e:
                pytest.fail(
                    f"Unexpected API error while deleting softwarestack: {str(e)}"
                )
        except Exception as e:
            pytest.fail(f"Unexpected API error: {str(e)}")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_software_stack_empty_payload(
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
            request_content = CreateSoftwareStackRequestContent(**payload)
            response: CreateSoftwareStackResponseContent = (
                api_client.create_software_stack(request_content)
            )

            assert response is not None
            pytest.fail(f"Error failed to validate empty payload")
        except Exception as e:
            assert "400" in str(e)
            assert hasattr(e, "response") and e.response.status_code == 400

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_send_empty_body(
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
            request_content = CreateSoftwareStackRequestContent(**payload)
            response: CreateSoftwareStackResponseContent = (
                api_client.create_software_stack(request_content)
            )

            assert response is not None
            pytest.fail(f"Error failed to validate empty payload")
        except Exception as e:
            assert "400" in str(e)
            if hasattr(e, "response") and hasattr(e.response, "text"):
                assert "'software_stack' is a required property" in e.response.text
            else:
                assert "'software_stack' is a required property" in str(e)
            assert hasattr(e, "response") and e.response.status_code == 400

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_software_stack_with_empty_sofware_stack(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)

            payload: Dict[str, Any] = {"software_stack": {}}
            request_content = CreateSoftwareStackRequestContent(**payload)
            api_client.create_software_stack(request_content)
            pytest.fail("Expected 400 error for empty software stack")
        except Exception as e:
            assert "400" in str(e)
            assert hasattr(e, "response")
            assert hasattr(e.response, "text")
            assert "Bad Request" in e.response.text

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_software_stack_with_fake_ami(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            payload = get_software_stack_base_payload(
                region, name="basic-software-stack-fake-ami", ami_id="fake-ami-1234"
            )

            request_content = CreateSoftwareStackRequestContent(**payload)
            response = api_client.create_software_stack(request_content)
            pytest.fail("Expected 400 error for fake AMI ID, but request succeeded")
        except Exception as e:
            assert "400" in str(e)
            assert hasattr(e, "response")
            assert hasattr(e.response, "text")
            assert "Invalid software_stack.ami_id" in e.response.text

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_software_stack_with_invalid_os(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            payload = get_software_stack_base_payload(
                region, name="basic-software-stack-invalid-os", base_os="invalid-os"
            )
            request_content = CreateSoftwareStackRequestContent(**payload)
            api_client.create_software_stack(request_content)
            pytest.fail("Expected 400 error for invalid base_os")
        except Exception as e:
            assert "400 Client Error" in str(e)
            assert hasattr(e, "response") and e.response.status_code == 400
            response_content = e.response.text
            assert "Bad Request" in response_content
            logger.info(f"Correctly received validation error for invalid OS: {str(e)}")

    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_create_software_stack_with_non_admin_user(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, non_admin)
            payload = get_software_stack_base_payload(region)
            request_content = CreateSoftwareStackRequestContent(**payload)
            api_client.create_software_stack(request_content)
            pytest.fail("Expected 401/403 error for non-admin user")
        except Exception as e:
            if "401" in str(e) or "403" in str(e):
                logger.info(f"Non-admin user correctly denied access: {str(e)}")
            else:
                pytest.fail(f"Unexpected API error: {str(e)}")

    @pytest.mark.parametrize("inactive_username", ["user2"])
    def test_create_software_stack_with_inactive_user(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        inactive_username: str,
        inactive_user: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, inactive_user)
            payload = get_software_stack_base_payload(region)
            request_content = CreateSoftwareStackRequestContent(**payload)
            api_client.create_software_stack(request_content)
            pytest.fail("Expected error for inactive user")
        except Exception as e:
            assert "401" in str(e)
            logger.info(f"Correctly received inactive user error: {str(e)}")

    def test_create_software_stack_with_nonexistent_user(
        self, res_environment: ResEnvironment, region: str
    ) -> None:
        try:
            nonexistent_auth = ClientAuth(username="nonexistent_user_12345")
            api_client = ApiClient(res_environment, nonexistent_auth)
            payload = get_software_stack_base_payload(region)
            request_content = CreateSoftwareStackRequestContent(**payload)
            api_client.create_software_stack(request_content)
            pytest.fail("Expected 'User not found' error for non-existent user")
        except Exception as e:
            assert "401" in str(e)
            logger.info(f"Non-existent user correctly received error: {str(e)}")

    def test_create_software_stack_without_auth_token(
        self, res_environment: ResEnvironment, region: str
    ) -> None:
        try:
            no_auth = ClientAuth(username="user1", auth_token=None)
            api_client = ApiClient(res_environment, no_auth)
            payload = get_software_stack_base_payload(region)
            request_content = CreateSoftwareStackRequestContent(**payload)
            api_client.create_software_stack(request_content)
            pytest.fail("Expected 'No authorization token provided' error")
        except Exception as e:
            assert "401" in str(e)
            logger.info(
                f"Request without auth token correctly received error: {str(e)}"
            )

    @pytest.mark.skip(
        reason="Temporarily Skipping Test - While Adding DeleteSoftwareStack"
    )
    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_software_stack_duplicate_name(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        api_client = ApiClient(res_environment, admin)
        stack_name = "duplicate-test-stack"

        # First request should succeed
        payload1 = get_software_stack_base_payload(region, name=stack_name)
        request_content1 = CreateSoftwareStackRequestContent(**payload1)
        response1 = api_client.create_software_stack(request_content1)
        assert response1 is not None
        assert (
            hasattr(response1, "software_stack")
            and response1.software_stack is not None
        )
        assert response1.software_stack.stack_id is not None

        # Second request with same name should fail
        try:
            payload2 = get_software_stack_base_payload(region, name=stack_name)
            request_content2 = CreateSoftwareStackRequestContent(**payload2)
            api_client.create_software_stack(request_content2)
            pytest.fail("Expected error for duplicate software stack name")
        except Exception as e:
            assert "400" in str(e)
            assert (
                "Invalid software stack request: Software stack with name"
                in e.response.text
            )
            logger.info(f"Correctly received duplicate name error: {str(e)}")
        finally:
            try:
                if response1 and response1.software_stack:
                    delete_request = DeleteSoftwareStackRequestContent(
                        base_os=response1.software_stack.base_os
                    )
                    api_client.delete_software_stack(
                        response1.software_stack.stack_id, delete_request
                    )
            except Exception as e:
                pytest.fail(
                    f"Unexpected API error while deleting softwarestack: {str(e)}"
                )

    def test_create_software_stack_with_invalid_auth_token_in_prod(
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
            payload = get_software_stack_base_payload(region)
            request_content = CreateSoftwareStackRequestContent(**payload)
            api_client.create_software_stack(request_content)
            pytest.fail(
                "Expected 'Unable to retrieve username' error for invalid auth token"
            )
        except Exception as e:
            assert "401" in str(e)
            logger.info(f"Invalid auth token correctly received error: {str(e)}")
        finally:
            set_backend_lambda_test_mode(region, environment_name, True)
