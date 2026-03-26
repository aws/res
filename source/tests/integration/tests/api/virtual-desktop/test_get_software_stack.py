#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
Integration tests for Get Software Stack API.

This module contains comprehensive tests for the get software stack REST API
using the RES framework ResClient for proper API interaction.
"""

import logging

import pytest

from ideadatamodel import Project, VirtualDesktopSoftwareStack  # type: ignore

# Import RES framework components
from tests.integration.framework.client.api_client import (
    ApiClient,
    CreateSoftwareStackRequestContent,
    CreateSoftwareStackResponseContent,
    DeleteSoftwareStackRequestContent,
    GetSoftwareStackResponseContent,
)
from tests.integration.framework.fixtures.fixture_request import FixtureRequest
from tests.integration.framework.fixtures.project import project
from tests.integration.framework.fixtures.res_environment import (
    ResEnvironment,
    res_environment,
)
from tests.integration.framework.fixtures.software_stack import software_stack
from tests.integration.framework.fixtures.users import admin, inactive_user, non_admin
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.lambda_utils import set_backend_lambda_test_mode
from tests.integration.framework.utils.virtual_desktop import (
    get_software_stack_base_payload,
)
from tests.integration.tests.smoke.config import AL2023_SOFTWARE_STACK

logger = logging.getLogger(__name__)


class TestGetSoftwareStack:
    """Test suite for the get software stack endpoint."""

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="test-get-stack-project",
                    name="test-get-stack-project",
                    description="Test project for get software stack",
                    enable_budgets=False,
                ),
                ["home"],
                [],
                [],
                "admin",
            )
        ],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "software_stack",
        [(AL2023_SOFTWARE_STACK, "project", "admin")],
        indirect=True,
    )
    def test_get_software_stack_admin_returns_valid_response(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
        project: Project,
        software_stack: VirtualDesktopSoftwareStack,
    ) -> None:
        """
        Test successful retrieval of a specific software stack as admin.
        """
        api_client = ApiClient(res_environment, admin)

        response: GetSoftwareStackResponseContent = api_client.get_software_stack(
            stack_id=software_stack.stack_id, base_os=software_stack.base_os.value
        )

        # Verify we got a proper response
        assert response is not None, "Response should not be None"
        assert (
            response.software_stack is not None
        ), "Response must contain 'software_stack' field"

        stack = response.software_stack
        assert stack.stack_id == software_stack.stack_id, "Stack ID should match"
        assert stack.name == software_stack.name, "Stack name should match"
        assert stack.base_os == software_stack.base_os, "Base OS should match"

        # Verify required fields are present
        assert stack.min_ram is not None, "Stack must have min_ram object"
        assert stack.min_ram.value is not None, "min_ram must have value"
        assert stack.min_ram.unit is not None, "min_ram must have unit"
        assert stack.projects is not None, "Stack must have projects list"
        assert isinstance(stack.projects, list), "projects should be a list"

        logger.info(f"Successfully retrieved software stack {stack.stack_id} as admin")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_get_software_stack_admin_nonexistent_returns_bad_request(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """
        Test that getting a non-existent software stack returns BadRequestException.
        """
        try:
            api_client = ApiClient(res_environment, admin)
            api_client.get_software_stack(
                stack_id="nonexistent-stack-12345", base_os="amzn2023"
            )
            pytest.fail("Expected 400 error for non-existent software stack")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert e.response is not None, "Response should not be None"
            response_content = e.response.text
            assert (
                "Test Message" in response_content
                or "not found" in response_content.lower()
            ), f"Expected error message, got: {response_content}"

            logger.info(
                "Non-existent software stack correctly received BadRequestException"
            )

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_get_software_stack_with_empty_base_os_returns_error(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """
        Test that getting a software stack with empty base_os returns error.
        """
        try:
            api_client = ApiClient(res_environment, admin)
            api_client.get_software_stack(stack_id="test-stack-123", base_os="")
            pytest.fail("Expected error for empty base_os")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert e.response is not None, "Response should not be None"
            response_content = e.response.text
            assert (
                "Supported base operating systems for virtual desktops"
                in response_content
            ), f"Expected base OS validation error, got: {response_content}"
            logger.info("Empty base_os correctly received error")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_get_software_stack_with_null_base_os_returns_error(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """
        Test that getting a software stack with null/None base_os returns error.
        """
        try:
            api_client = ApiClient(res_environment, admin)
            api_client.get_software_stack(
                stack_id="test-stack-123", base_os=None  # type: ignore
            )
            pytest.fail("Expected error for null base_os")
        except Exception as e:
            assert any(
                code in str(e) for code in ["400", "404", "422"]
            ), f"Expected validation error, got: {str(e)}"
            logger.info("Null base_os correctly received error")

    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_get_software_stack_non_admin_returns_oauth_problem(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        """
        Test that non-admin users get OAuthProblem when trying to get software stack.
        """
        try:
            api_client = ApiClient(res_environment, non_admin)
            api_client.get_software_stack(stack_id="any-stack-id", base_os="amzn2023")
            pytest.fail("Expected OAuth error for non-admin user")
        except Exception as e:
            # OAuthProblem raises 401 Unauthorized
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert e.response is not None, "Response should not be None"
            response_content = e.response.text
            assert (
                "Test Message" in response_content
                or "unauthorized" in response_content.lower()
                or "permission" in response_content.lower()
            ), f"Expected authorization error message, got: {response_content}"
            logger.info("Non-admin user correctly received 401 Unauthorized error")

    def test_get_software_stack_with_nonexistent_user_returns_user_not_found_error(
        self, res_environment: ResEnvironment
    ) -> None:
        """
        Test that non-existent users get proper 'User not found' error.
        """
        try:
            nonexistent_auth = ClientAuth(username="nonexistent_user_12345")
            api_client = ApiClient(res_environment, nonexistent_auth)
            api_client.get_software_stack(stack_id="any-stack-id", base_os="amzn2023")
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
    def test_get_software_stack_with_inactive_user_returns_inactive_user_error(
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
            api_client.get_software_stack(stack_id="any-stack-id", base_os="amzn2023")
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

    def test_get_software_stack_without_auth_token_returns_no_authorization_token_provided_error(
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
            api_client.get_software_stack(stack_id="any-stack-id", base_os="amzn2023")
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
    def test_get_software_stack_in_prod_with_invalid_auth_token_returns_unable_to_retrieve_username_error(
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
            api_client.get_software_stack(stack_id="any-stack-id", base_os="amzn2023")
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
