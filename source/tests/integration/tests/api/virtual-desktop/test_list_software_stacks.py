#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
Integration tests for List Software Stacks API.

This module contains comprehensive tests for the list software stacks REST API
using the RES framework ResClient for proper API interaction.
"""

import logging

import pytest

from ideadatamodel import Project  # type: ignore

# Import RES framework components
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
from tests.integration.framework.utils.lambda_utils import set_backend_lambda_test_mode
from tests.integration.framework.utils.virtual_desktop import (
    get_software_stack_base_payload,
)

logger = logging.getLogger(__name__)


class TestListSoftwareStacks:
    """Test suite for the list software stacks endpoint."""

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_list_software_stacks_admin_returns_valid_response(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """
        Test successful retrieval of software stacks as admin.
        """
        try:
            api_client = ApiClient(res_environment, admin)
            response = api_client.list_software_stacks()

            # Verify we got a proper response
            assert response is not None, "Response should not be None"

            # Response must always have a listing field
            assert response.listing is not None, "Response must contain 'listing' field"
            assert isinstance(response.listing, list), "Listing should be a list"

            # Verify each stack has required fields
            for stack in response.listing:
                assert stack.stack_id is not None, "Stack must have stack_id"
                assert stack.name is not None, "Stack must have name"
                assert stack.base_os is not None, "Stack must have base_os"
                # Verify converted fields from DB format to API format
                assert stack.min_ram is not None, "Stack must have min_ram object"
                assert stack.min_ram.value is not None, "min_ram must have value"
                assert stack.min_ram.unit is not None, "min_ram must have unit"
                assert stack.projects is not None, "Stack must have projects list"
                assert isinstance(stack.projects, list), "projects should be a list"
                # Verify projects are converted to objects with project_id
                for project in stack.projects:
                    assert hasattr(
                        project, "project_id"
                    ), "Project must have project_id field"

            logger.info(
                f"Successfully retrieved {len(response.listing)} software stacks as admin"
            )

        except Exception as e:
            pytest.fail(f"Unexpected API error: {str(e)}")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_list_software_stacks_admin_with_base_os_filter(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """
        Test filtering software stacks by base_os as admin.
        """
        try:
            api_client = ApiClient(res_environment, admin)

            # Filter by amzn2023
            response = api_client.list_software_stacks(base_os="amzn2023")

            assert response is not None, "Response should not be None"
            assert response.listing is not None, "Response must contain 'listing' field"

            # Verify all returned stacks have the correct base_os
            for stack in response.listing:
                assert (
                    stack.base_os == "amzn2023"
                ), f"Stack {stack.stack_id} should have base_os 'amzn2023'"

            logger.info(
                f"Successfully filtered {len(response.listing)} software stacks by base_os"
            )

        except Exception as e:
            pytest.fail(f"Unexpected API error: {str(e)}")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_list_software_stacks_admin_with_name_filter(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """
        Test filtering software stacks by name as admin.
        """
        try:
            api_client = ApiClient(res_environment, admin)
            filter_name = "AL2023"

            # Filter by name substring
            filtered_response = api_client.list_software_stacks(
                software_stack_name=filter_name
            )

            assert filtered_response is not None, "Response should not be None"
            assert (
                filtered_response.listing is not None
            ), "Response must contain 'listing' field"

            # Verify all returned stacks contain the filter substring
            for stack in filtered_response.listing:
                assert (
                    filter_name.lower() in stack.name.lower()
                ), f"Stack {stack.name} should contain filter '{filter_name}'"

            logger.info(
                f"Successfully filtered {len(filtered_response.listing)} software stacks by name"
            )

        except Exception as e:
            pytest.fail(f"Unexpected API error: {str(e)}")

    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="test-stack-admin-project",
                    name="test-stack-admin-project",
                    description="RES integration test software stack admin filter project_id",
                    enable_budgets=False,
                ),
                ["home"],
                ["group_1"],
                ["clusteradmin"],
                "admin",
            )
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_list_software_stacks_admin_with_project_id_filter(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        project: Project,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """
        Test filtering software stacks by project_id as admin.
        """
        api_client = ApiClient(res_environment, admin)
        created_stack = None

        try:

            payload = get_software_stack_base_payload(
                region,
                name="test-stack-admin-project",
                projects=[{"project_id": project.project_id}],
            )

            request_content = CreateSoftwareStackRequestContent(**payload)
            create_response: CreateSoftwareStackResponseContent = (
                api_client.create_software_stack(request_content)
            )
            created_stack = create_response.software_stack

            # Filter by project_id
            filtered_response = api_client.list_software_stacks(
                project_id=project.project_id
            )

            assert filtered_response is not None, "Response should not be None"
            assert (
                filtered_response.listing is not None
            ), "Response must contain 'listing' field"

            # Verify exactly one stack is returned and it's the created one
            assert (
                len(filtered_response.listing) == 1
            ), f"Expected exactly 1 stack with project_id '{project.project_id}', got {len(filtered_response.listing)}"
            assert (
                filtered_response.listing[0].stack_id == created_stack.stack_id
            ), f"Expected stack {created_stack.stack_id}, got {filtered_response.listing[0].stack_id}"

            logger.info(
                f"Successfully filtered {len(filtered_response.listing)} software stacks by project_id"
            )

        except Exception as e:
            pytest.fail(f"Unexpected API error: {str(e)}")
        finally:
            if created_stack:
                try:
                    delete_request = DeleteSoftwareStackRequestContent(
                        base_os=created_stack.base_os
                    )
                    api_client.delete_software_stack(
                        created_stack.stack_id, delete_request
                    )
                except Exception as e:
                    logger.warning(f"Failed to delete test stack: {str(e)}")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_list_software_stacks_admin_with_name_and_base_os_filter(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """
        Test filtering software stacks by both name and base_os as admin.
        """
        api_client = ApiClient(res_environment, admin)
        created_stack = None

        try:
            test_name = "test-stack-name-baseos-filter"
            test_base_os = "amzn2023"
            payload = get_software_stack_base_payload(
                region,
                name=test_name,
                base_os=test_base_os,
                enabled=False,
            )

            request_content = CreateSoftwareStackRequestContent(**payload)
            create_response: CreateSoftwareStackResponseContent = (
                api_client.create_software_stack(request_content)
            )
            created_stack = create_response.software_stack

            # Filter by both name and base_os
            filtered_response = api_client.list_software_stacks(
                software_stack_name=test_name,
                base_os=test_base_os,
            )

            assert filtered_response is not None, "Response should not be None"
            assert (
                filtered_response.listing is not None
            ), "Response must contain 'listing' field"
            assert (
                len(filtered_response.listing) == 1
            ), f"Expected exactly 1 stack, got {len(filtered_response.listing)}"
            assert filtered_response.listing[0].stack_id == created_stack.stack_id
            assert (
                filtered_response.listing[0].enabled is False
            ), "Admin should be able to retrieve disabled stacks"

            logger.info(
                "Successfully filtered software stack by name and base_os as admin"
            )

        except Exception as e:
            pytest.fail(f"Unexpected API error: {str(e)}")
        finally:
            if created_stack:
                try:
                    delete_request = DeleteSoftwareStackRequestContent(
                        base_os=created_stack.base_os
                    )
                    api_client.delete_software_stack(
                        created_stack.stack_id, delete_request
                    )
                except Exception as e:
                    logger.warning(f"Failed to delete test stack: {str(e)}")

    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_list_software_stacks_non_admin_without_project_id_returns_bad_request(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        """
        Test that non-admin users without project_id get BadRequestException.
        """
        try:
            api_client = ApiClient(res_environment, non_admin)
            api_client.list_software_stacks()
            pytest.fail("Expected 400 error for non-admin without project_id")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert "project_id is required field" in e.response.text
            logger.info(
                "Non-admin without project_id correctly received BadRequestException"
            )

    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="test-stack-nonadmin-project-filter",
                    name="test-stack-nonadmin-project-filter",
                    description="RES integration test software stack non-admin filter project_id",
                    enable_budgets=False,
                ),
                ["home"],
                ["group_1"],
                ["clusteradmin"],
                "admin",
            )
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_list_software_stacks_non_admin_with_project_id_returns_valid_response(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        project: Project,
        admin_username: str,
        admin: ClientAuth,
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        """
        Test that non-admin users can access with project_id and only see enabled stacks.
        """
        admin_client = ApiClient(res_environment, admin)
        created_stack = None

        try:

            payload = get_software_stack_base_payload(
                region,
                name="test-stack-nonadmin-project-filter",
                projects=[{"project_id": project.project_id}],
                enabled=True,
            )

            request_content = CreateSoftwareStackRequestContent(**payload)
            create_response: CreateSoftwareStackResponseContent = (
                admin_client.create_software_stack(request_content)
            )
            created_stack = create_response.software_stack

            # Test as non-admin with the project_id
            api_client = ApiClient(res_environment, non_admin)
            response = api_client.list_software_stacks(project_id=project.project_id)

            assert response is not None, "Response should not be None"
            assert response.listing is not None, "Response must contain 'listing' field"

            # Verify exactly one stack is returned and it's the created one
            assert (
                len(response.listing) == 1
            ), f"Expected exactly 1 stack with project_id '{project.project_id}', got {len(response.listing)}"
            assert (
                response.listing[0].stack_id == created_stack.stack_id
            ), f"Expected stack {created_stack.stack_id}, got {response.listing[0].stack_id}"
            assert (
                response.listing[0].enabled is True
            ), "Non-admin user should only see enabled stacks"

            logger.info(
                "Successfully retrieved enabled software stack as non-admin with project_id"
            )

        except Exception as e:
            pytest.fail(f"Unexpected API error: {str(e)}")
        finally:
            if created_stack:
                try:
                    delete_request = DeleteSoftwareStackRequestContent(
                        base_os=created_stack.base_os
                    )
                    admin_client.delete_software_stack(
                        created_stack.stack_id, delete_request
                    )
                except Exception as e:
                    logger.warning(f"Failed to delete test stack: {str(e)}")

    def test_list_software_stacks_with_nonexistent_user_returns_user_not_found_error(
        self, res_environment: ResEnvironment
    ) -> None:
        """
        Test that non-existent users get proper 'User not found' error.
        """
        try:
            nonexistent_auth = ClientAuth(username="nonexistent_user_12345")
            api_client = ApiClient(res_environment, nonexistent_auth)
            api_client.list_software_stacks()
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
    def test_list_software_stacks_with_inactive_user_returns_inactive_user_error(
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
            api_client.list_software_stacks()
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

    def test_list_software_stacks_without_auth_token_returns_no_authorization_token_provided_error(
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
            api_client.list_software_stacks()
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
    def test_list_software_stacks_in_prod_with_invalid_auth_token_returns_unable_to_retrieve_username_error(
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
            api_client.list_software_stacks()
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
