#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
Integration tests for Virtual Desktop Allowed Instance Type API.

This module contains comprehensive tests for the virtual desktop allowed instance type REST API
using the RES framework ResClient for proper API interaction.
"""

import logging

import pytest

# Import backend model classes using the utility function
from tests.integration.framework.utils.model_utils import get_backend_model_class

# Import backend model classes
ListAllowedInstanceTypesRequestContent = get_backend_model_class(
    "list_allowed_instance_types_request_content",
    "ListAllowedInstanceTypesRequestContent",
)
VirtualDesktopSoftwareStack = get_backend_model_class(
    "virtual_desktop_software_stack", "VirtualDesktopSoftwareStack"
)

# Import RES framework components
from tests.integration.framework.client.api_client import ApiClient
from tests.integration.framework.fixtures.fixture_request import FixtureRequest
from tests.integration.framework.fixtures.res_environment import (
    ResEnvironment,
    res_environment,
)
from tests.integration.framework.fixtures.users import admin, inactive_user, non_admin
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.ec2_utils import get_latest_x86_amzn2023_ami_id
from tests.integration.framework.utils.lambda_utils import set_backend_lambda_test_mode

logger = logging.getLogger(__name__)


class TestListAllowedInstanceTypes:
    """Test suite for the list allowed instance types endpoint with admin user."""

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_list_allowed_instance_types_returns_valid_response(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """
        Test successful retrieval of allowed instance types.
        """
        try:
            api_client = ApiClient(res_environment, admin)

            # Create request content object
            request_content = ListAllowedInstanceTypesRequestContent(
                hibernation_support=False, software_stack=None
            )

            response = api_client.list_allowed_instance_types(request_content)

            # Verify we got a proper response content object
            assert response is not None, "Response should not be None"
            assert hasattr(
                response, "listing"
            ), "Response should have listing attribute"
            assert isinstance(response.listing, list), "Listing should be a list"

            # Verify each item in the listing is a valid instance type
            for instance_type in response.listing:
                assert isinstance(
                    instance_type, (str, dict)
                ), f"Instance type '{instance_type}' should be a string or dict"

            logger.info(
                f"Successfully retrieved {len(response.listing)} allowed instance types"
            )

        except Exception as e:
            pytest.fail(f"Unexpected API error: {str(e)}")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_list_allowed_instance_types_with_hibernation_support_returns_valid_response(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """
        Test successful retrieval of allowed instance types with hibernation support.
        """
        try:
            api_client = ApiClient(res_environment, admin)

            # Create request content object with hibernation support
            request_content = ListAllowedInstanceTypesRequestContent(
                hibernation_support=True, software_stack=None
            )

            response = api_client.list_allowed_instance_types(request_content)

            # Verify we got a proper response content object
            assert response is not None, "Response should not be None"
            assert hasattr(
                response, "listing"
            ), "Response should have listing attribute"
            assert isinstance(response.listing, list), "Listing should be a list"

            # Verify each item in the listing is a valid instance type
            for instance_type in response.listing:
                assert isinstance(
                    instance_type, (str, dict)
                ), f"Instance type '{instance_type}' should be a string or dict"

            logger.info(
                f"Successfully retrieved {len(response.listing)} allowed instance types with hibernation support"
            )

        except Exception as e:
            pytest.fail(f"Unexpected API error: {str(e)}")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_list_allowed_instance_types_with_software_stack_returns_valid_response(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """
        Test successful retrieval of allowed instance types with hibernation support.
        """
        try:
            api_client = ApiClient(res_environment, admin)

            # Get latest AMI ID for the region
            ami_id = get_latest_x86_amzn2023_ami_id(region)

            # Create a VirtualDesktopSoftwareStack object for testing
            software_stack = VirtualDesktopSoftwareStack(
                name="test-stack",
                base_os="amzn2023",
                architecture="x86_64",
                gpu="NO_GPU",
                ami_id=ami_id,
                description="test stack description",
                min_storage={"value": 100, "unit": "gb"},
                min_ram={"value": 22, "unit": "gb"},
                placement={"tenancy": "default"},
                projects=[],
                allowed_instance_types=[],
            )

            # Create request content object with software stack
            request_content = ListAllowedInstanceTypesRequestContent(
                hibernation_support=False, software_stack=software_stack
            )

            response = api_client.list_allowed_instance_types(request_content)

            # Verify we got a proper response content object
            assert response is not None, "Response should not be None"
            assert hasattr(
                response, "listing"
            ), "Response should have listing attribute"
            assert isinstance(response.listing, list), "Listing should be a list"

            # Verify each item in the listing is a valid instance type
            for instance_type in response.listing:
                assert isinstance(
                    instance_type, (str, dict)
                ), f"Instance type '{instance_type}' should be a string or dict"

            logger.info(
                f"Successfully retrieved {len(response.listing)} allowed instance types with software stack"
            )

        except Exception as e:
            pytest.fail(f"Unexpected API error: {str(e)}")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_list_allowed_instance_types_without_software_stack_architecture_returns_valid_response(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """
        Test successful retrieval of allowed instance types without software stack architecture.
        """
        try:
            api_client = ApiClient(res_environment, admin)

            # Get latest AMI ID for the region
            ami_id = get_latest_x86_amzn2023_ami_id(region)

            # Create a VirtualDesktopSoftwareStack object for testing
            software_stack = VirtualDesktopSoftwareStack(
                name="test-stack",
                base_os="amzn2023",
                gpu="NO_GPU",
                ami_id=ami_id,
                description="test stack description",
                min_storage={"value": 100, "unit": "gb"},
                min_ram={"value": 22, "unit": "gb"},
                placement={"tenancy": "default"},
                projects=[],
                allowed_instance_types=[],
            )

            # Create request content object with software stack
            request_content = ListAllowedInstanceTypesRequestContent(
                hibernation_support=False, software_stack=software_stack
            )

            response = api_client.list_allowed_instance_types(request_content)

            # Verify we got a proper response content object
            assert response is not None, "Response should not be None"
            assert hasattr(
                response, "listing"
            ), "Response should have listing attribute"
            assert isinstance(response.listing, list), "Listing should be a list"

            # Verify each item in the listing is a valid instance type
            for instance_type in response.listing:
                assert isinstance(
                    instance_type, (str, dict)
                ), f"Instance type '{instance_type}' should be a string or dict"

            logger.info(
                f"Successfully retrieved {len(response.listing)} allowed instance types with software stack"
            )

        except Exception as e:
            pytest.fail(f"Unexpected API error: {str(e)}")

    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_list_allowed_instance_types_with_non_admin_user_returns_valid_response(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        """
        Test that non-admin users can successfully retrieve allowed instance types.
        """
        try:
            api_client = ApiClient(res_environment, non_admin)

            # Create request content object
            request_content = ListAllowedInstanceTypesRequestContent(
                hibernation_support=False, software_stack=None
            )

            response = api_client.list_allowed_instance_types(request_content)

            # Verify we got a proper response content object
            assert response is not None, "Response should not be None"
            assert hasattr(
                response, "listing"
            ), "Response should have listing attribute"
            assert isinstance(response.listing, list), "Listing should be a list"

            # Verify each item in the listing is a valid instance type
            for instance_type in response.listing:
                assert isinstance(
                    instance_type, (str, dict)
                ), f"Instance type '{instance_type}' should be a string or dict"

            logger.info(
                f"Non-admin user successfully retrieved {len(response.listing)} allowed instance types"
            )

        except Exception as e:
            pytest.fail(f"Unexpected API error for non-admin user: {str(e)}")

    def test_list_allowed_instance_types_with_nonexistent_user_returns_user_not_found_error(
        self, res_environment: ResEnvironment
    ) -> None:
        """
        Test that non-existent users get proper 'User not found' error for allowed instance type endpoint.
        This test verifies that the API properly validates user existence and returns appropriate error.
        """
        try:
            nonexistent_auth = ClientAuth(username="nonexistent_user_12345")
            api_client = ApiClient(res_environment, nonexistent_auth)

            # Create request content object
            request_content = ListAllowedInstanceTypesRequestContent(
                hibernation_support=False, software_stack=None
            )

            api_client.list_allowed_instance_types(request_content)
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
                        "Non-existent user correctly received 'User not found' error for allowed instance type endpoint"
                    )
                    return  # Test passes

            pytest.fail(f"Unexpected error for non-existent user: {str(e)}")

    @pytest.mark.parametrize("inactive_username", ["user2"])
    def test_list_allowed_instance_types_with_inactive_user_returns_inactive_user_error(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        inactive_username: str,
        inactive_user: ClientAuth,
    ) -> None:
        """
        Test that inactive users get proper 'Inactive user' error for allowed instance type endpoint.

        Inactive users should not be able to access any API endpoints and should
        receive appropriate error responses indicating their account status.
        """
        try:
            api_client = ApiClient(res_environment, inactive_user)

            # Create request content object
            request_content = ListAllowedInstanceTypesRequestContent(
                hibernation_support=False, software_stack=None
            )

            api_client.list_allowed_instance_types(request_content)
            pytest.fail("Expected 'Inactive user' error for inactive user")
        except Exception as e:
            # Check if it's a 401 error (which is expected for inactive users)
            if "401" in str(e):
                # For 401 errors, check the response content for appropriate messages
                assert hasattr(e, "response"), "Response should exist in the exception"
                assert e.response is not None, "Response should not be None"

                response_content = e.response.text
                if "Inactive user" in response_content:
                    logger.info(
                        f"Inactive user correctly received 'Inactive user' error for allowed instance type endpoint: {e.response.text}"
                    )
                    return  # Test passes

            pytest.fail(f"Unexpected error for inactive user: {str(e)}")

    def test_list_allowed_instance_types_without_auth_token_returns_no_authorization_token_provided_error(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
    ) -> None:
        """
        Test that requests without auth tokens get proper 'No authorization token provided' error for allowed instance type endpoint.

        Requests without proper authorization tokens should be rejected with appropriate
        error responses indicating missing or invalid authorization.
        """
        try:
            no_auth = ClientAuth(username="user1", auth_token=None)
            api_client = ApiClient(res_environment, no_auth)

            # Create request content object
            request_content = ListAllowedInstanceTypesRequestContent(
                hibernation_support=False, software_stack=None
            )

            api_client.list_allowed_instance_types(request_content)
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
                        f"Request without auth token correctly received 'No authorization token provided' error for allowed instance type endpoint: {e.response.text}"
                    )
                    return  # Test passes

            pytest.fail(f"Unexpected error for request without auth token: {str(e)}")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_list_allowed_instance_types_in_prod_with_invalid_auth_token_returns_unable_to_retrieve_username_error(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """
        Test that requests with invalid auth tokens get proper 'Unable to retrieve username' error for allowed instance type endpoint in production.

        Requests without proper authorization tokens should be rejected with appropriate
        error responses indicating missing or invalid authorization.
        """
        set_backend_lambda_test_mode(region, environment_name, False)
        try:
            api_client = ApiClient(res_environment, admin)

            # Create request content object
            request_content = ListAllowedInstanceTypesRequestContent(
                hibernation_support=False, software_stack=None
            )

            api_client.list_allowed_instance_types(request_content)
            pytest.fail(
                "Expected 'Unable to retrieve username' error for request with invalid auth token"
            )
        except Exception as e:
            # Check if it's a 401 error (which is expected for invalid auth tokens)
            if "401" in str(e):
                # For 401 errors, check the response content for appropriate messages
                assert hasattr(e, "response"), "Response should exist in the exception"
                assert e.response is not None, "Response should not be None"

                response_content = e.response.text
                if "Unable to retrieve username" in response_content:
                    logger.info(
                        f"Request with invalid auth token correctly received 'Unable to retrieve username' error for allowed instance type endpoint: {e.response.text}"
                    )
                    return  # Test passes

            pytest.fail(
                f"Unexpected error for request with invalid auth token: {str(e)}"
            )
        finally:
            set_backend_lambda_test_mode(region, environment_name, True)

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_list_allowed_instance_types_with_missing_ami_id_returns_bad_request_error(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """
        Test that missing ami_id in software stack returns 'ami_id' is a required property - 'software_stack' error.
        """
        try:
            api_client = ApiClient(res_environment, admin)

            # Create a software stack without ami_id
            software_stack_without_ami = VirtualDesktopSoftwareStack(
                name="test-stack",
                base_os="amzn2023",
                architecture="x86_64",
                gpu="NO_GPU",
                # Missing ami_id
                description="test stack description",
                min_storage={"value": 100, "unit": "gb"},
                min_ram={"value": 22, "unit": "gb"},
                placement={"tenancy": "default"},
                projects=[],
                allowed_instance_types=[],
            )

            # Create request content object
            request_content = ListAllowedInstanceTypesRequestContent(
                hibernation_support=False, software_stack=software_stack_without_ami
            )

            api_client.list_allowed_instance_types(request_content)
            pytest.fail("Expected BadRequestException for missing ami_id")
        except Exception as e:
            # Check if it's a 400 error with the specific message
            if "400" in str(e):
                assert hasattr(e, "response"), "Response should exist in the exception"
                assert e.response is not None, "Response should not be None"
                response_content = e.response.text

                if (
                    "'ami_id' is a required property - 'software_stack'"
                    in response_content
                ):
                    logger.info(
                        f"Missing ami_id correctly received BadRequestException: {str(e)}"
                    )
                    return  # Test passes

            pytest.fail(f"Unexpected error for missing ami_id: {str(e)}")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_list_allowed_instance_types_with_invalid_ami_id_returns_bad_request_error(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """
        Test that invalid ami_id returns 'Invalid software_stack.ami_id' error.
        """
        try:
            api_client = ApiClient(res_environment, admin)

            # Create a software stack with invalid ami_id
            software_stack_with_invalid_ami = VirtualDesktopSoftwareStack(
                name="test-stack",
                base_os="amzn2023",
                architecture="x86_64",
                gpu="NO_GPU",
                ami_id="ami-invalid123456789",  # Invalid AMI ID
                description="test stack description",
                min_storage={"value": 100, "unit": "gb"},
                min_ram={"value": 22, "unit": "gb"},
                placement={"tenancy": "default"},
                projects=[],
                allowed_instance_types=[],
            )

            # Create request content object
            request_content = ListAllowedInstanceTypesRequestContent(
                hibernation_support=False,
                software_stack=software_stack_with_invalid_ami,
            )

            api_client.list_allowed_instance_types(request_content)
            pytest.fail("Expected BadRequestException for invalid ami_id")
        except Exception as e:
            # Check if it's a 400 error with the specific message
            if "400" in str(e):
                assert hasattr(e, "response"), "Response should exist in the exception"
                assert e.response is not None, "Response should not be None"
                response_content = e.response.text

                if (
                    "Invalid software_stack.ami_id: ami-invalid123456789"
                    in response_content
                ):
                    logger.info(
                        f"Invalid ami_id correctly received BadRequestException: {str(e)}"
                    )
                    return  # Test passes

            pytest.fail(f"Unexpected error for invalid ami_id: {str(e)}")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_list_allowed_instance_types_with_ami_id_architecture_mismatch_returns_bad_request_error(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """
        Test that AMI ID with mismatched architecture returns architecture mismatch error.
        """
        # Get a real AMI ID (which will be x86_64)
        ami_id = get_latest_x86_amzn2023_ami_id(region)

        try:
            api_client = ApiClient(res_environment, admin)

            # Create a software stack with mismatched architecture
            software_stack_with_mismatch = VirtualDesktopSoftwareStack(
                name="test-stack",
                base_os="amzn2023",
                architecture="arm64",  # This won't match the x86_64 AMI
                gpu="NO_GPU",
                ami_id=ami_id,
                description="test stack description",
                min_storage={"value": 100, "unit": "gb"},
                min_ram={"value": 22, "unit": "gb"},
                placement={"tenancy": "default"},
                projects=[],
                allowed_instance_types=[],
            )

            # Create request content object
            request_content = ListAllowedInstanceTypesRequestContent(
                hibernation_support=False, software_stack=software_stack_with_mismatch
            )

            api_client.list_allowed_instance_types(request_content)
            pytest.fail("Expected BadRequestException for architecture mismatch")
        except Exception as e:
            # Check if it's a 400 error with the specific message
            if "400" in str(e):
                assert hasattr(e, "response"), "Response should exist in the exception"
                assert e.response is not None, "Response should not be None"
                response_content = e.response.text

                if (
                    f"Invalid software_stack.ami_id: {ami_id} with architecture: arm64"
                    in response_content
                ):
                    logger.info(
                        f"Architecture mismatch correctly received BadRequestException: {str(e)}"
                    )
                    return  # Test passes

            pytest.fail(f"Unexpected error for architecture mismatch: {str(e)}")
