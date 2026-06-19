#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
import os

import pytest

from ideadatamodel import (  # type: ignore
    Project,
    SocaMemory,
    SocaMemoryUnit,
    VirtualDesktopArchitecture,
    VirtualDesktopBaseOS,
    VirtualDesktopGPU,
    VirtualDesktopSoftwareStack,
)
from tests.integration.framework.client.api_client import (
    ApiClient,
    CreateSessionRequestContent,
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

logger = logging.getLogger(__name__)


class TestCreateSession:

    def _get_create_session_payload(self, **overrides):  # type: ignore
        """Helper method to create session request payload with optional overrides."""
        payload = {
            "session": {
                "name": "TestDesktopSession",
                "hibernation_enabled": False,
                "software_stack_id": "ss-base-windows-x86-64-base",
                "base_os": "windows",
                "server": {
                    "instance_type": "t3.2xlarge",
                    "root_volume_size": {"value": 50, "unit": "gb"},
                },
                "project": {"project_id": "d6c3e390-3ba8-4a8b-811c-7d0679dde168"},
            }
        }
        if overrides:
            payload["session"].update(overrides)
        return payload

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_session_request_with_dry_mode_as_admin(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """Test that admin can successfully create session in dry run mode."""
        from tests.integration.framework.utils.lambda_utils import (
            set_backend_lambda_dry_mode,
        )

        set_backend_lambda_dry_mode(region, environment_name, True)
        api_client = ApiClient(res_environment, admin)

        try:
            payload = self._get_create_session_payload()  # type: ignore
            response = api_client.create_session(CreateSessionRequestContent(**payload))
            assert response is not None
            assert hasattr(
                response, "session"
            ), "Response should have session attribute"
            session = response.session
            assert session is not None, "Session should not be None"
            # In dry run mode, the session should echo back the input values
            assert (
                session.name == payload["session"]["name"]
            ), "Session name should match input"
            assert (
                session.hibernation_enabled == payload["session"]["hibernation_enabled"]
            ), "Hibernation should match input"
            assert (
                session.base_os == payload["session"]["base_os"]
            ), "Base OS should match input"
            logger.info("Admin successfully created session in dry run mode")
        except Exception as e:
            pytest.fail(f"Unexpected API error while creating session: {str(e)}")
        finally:
            set_backend_lambda_dry_mode(region, environment_name, False)

    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_create_session_request_with_dry_run_mode_as_non_admin(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        """Test that non-admin user can successfully create session in dry run mode."""
        from tests.integration.framework.utils.lambda_utils import (
            set_backend_lambda_dry_mode,
        )

        set_backend_lambda_dry_mode(region, environment_name, True)
        api_client = ApiClient(res_environment, non_admin)

        try:
            payload = self._get_create_session_payload()  # type: ignore
            response = api_client.create_session(CreateSessionRequestContent(**payload))
            assert response is not None
            assert hasattr(
                response, "session"
            ), "Response should have session attribute"
            session = response.session
            assert session is not None, "Session should not be None"
            # In dry run mode, the session should echo back the input values
            assert (
                session.name == payload["session"]["name"]
            ), "Session name should match input"
            assert (
                session.hibernation_enabled == payload["session"]["hibernation_enabled"]
            ), "Hibernation should match input"
            assert (
                session.base_os == payload["session"]["base_os"]
            ), "Base OS should match input"
            logger.info("Non-admin user successfully created session in dry run mode")
        except Exception as e:
            pytest.fail(f"Unexpected API error while creating session: {str(e)}")
        finally:
            set_backend_lambda_dry_mode(region, environment_name, False)

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_session_missing_session(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            payload = self._get_create_session_payload()  # type: ignore
            del payload["session"]
            request_content = CreateSessionRequestContent(**payload)

            api_client.create_session(request_content)
            pytest.fail("Expected 400 error for missing session")
        except Exception as e:
            assert "400" in str(e)
            assert hasattr(e, "response")
            assert hasattr(e.response, "text")
            assert "'session' is a required property" in e.response.text

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_session_missing_server(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            payload = self._get_create_session_payload()  # type: ignore
            del payload["session"]["server"]
            request_content = CreateSessionRequestContent(**payload)

            api_client.create_session(request_content)
            pytest.fail("Expected 400 error for missing server")
        except Exception as e:
            assert "400" in str(e)
            assert hasattr(e, "response")
            assert hasattr(e.response, "text")
            assert "missing session.server.root_volume_size" in e.response.text

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_session_missing_software_stack_id(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            payload = self._get_create_session_payload()  # type: ignore
            del payload["session"]["software_stack_id"]

            request_content = CreateSessionRequestContent(**payload)
            api_client.create_session(request_content)
            pytest.fail("Expected 400 error for missing software_stack_id")
        except Exception as e:
            assert "400" in str(e)
            assert hasattr(e, "response")
            assert hasattr(e.response, "text")
            assert (
                "Invalid params: missing session.software_stack_id and/or session.base_os"
                in e.response.text
            )

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_session_missing_base_os(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            payload = self._get_create_session_payload()  # type: ignore
            del payload["session"]["base_os"]
            request_content = CreateSessionRequestContent(**payload)

            api_client.create_session(request_content)
            pytest.fail("Expected 400 error for missing base_os")
        except Exception as e:
            assert "400" in str(e)
            assert hasattr(e, "response")
            assert hasattr(e.response, "text")
            assert (
                "Invalid params: missing session.software_stack_id and/or session.base_os"
                in e.response.text
            )

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_session_missing_server_instance_type(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            payload = self._get_create_session_payload()  # type: ignore
            del payload["session"]["server"]["instance_type"]

            request_content = CreateSessionRequestContent(**payload)
            api_client.create_session(request_content)
            pytest.fail("Expected 400 error for missing instance_type")
        except Exception as e:
            assert "400" in str(e)
            assert hasattr(e, "response")
            assert hasattr(e.response, "text")
            assert (
                "Invalid params: missing session.server.instance_type"
                in e.response.text
            )

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_session_missing_server_root_volume_size(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            payload = self._get_create_session_payload()  # type: ignore
            del payload["session"]["server"]["root_volume_size"]

            request_content = CreateSessionRequestContent(**payload)
            api_client.create_session(request_content)
            pytest.fail("Expected 400 error for missing software_stack_id")
        except Exception as e:
            assert "400" in str(e)
            assert hasattr(e, "response")
            assert hasattr(e.response, "text")
            assert (
                "Invalid params: missing session.server.root_volume_size"
                in e.response.text
            )

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_session_missing_project(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            payload = self._get_create_session_payload()  # type: ignore
            del payload["session"]["project"]

            request_content = CreateSessionRequestContent(**payload)
            api_client.create_session(request_content)
            pytest.fail("Invalid params: missing - session.project.project_id")
        except Exception as e:
            assert "400" in str(e)
            assert hasattr(e, "response")
            assert hasattr(e.response, "text")
            assert (
                "Invalid params: missing - session.project.project_id"
                in e.response.text
            )

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_session_missing_project_id(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            payload = self._get_create_session_payload()  # type: ignore
            del payload["session"]["project"]["project_id"]

            request_content = CreateSessionRequestContent(**payload)
            api_client.create_session(request_content)
            pytest.fail("Expected 400 error for missing project_id")
        except Exception as e:
            assert "400" in str(e)
            assert hasattr(e, "response")
            assert hasattr(e.response, "text")
            assert "'project_id' is a required property" in e.response.text

    @pytest.mark.parametrize("inactive_username", ["user2"])
    def test_create_session_with_inactive_user_returns_inactive_user_error(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        inactive_username: str,
        inactive_user: ClientAuth,
    ) -> None:
        """Test that inactive users get proper 'Inactive user' error for create session endpoint."""
        try:
            api_client = ApiClient(res_environment, inactive_user)
            payload = self._get_create_session_payload()  # type: ignore
            request_content = CreateSessionRequestContent(**payload)

            api_client.create_session(request_content)
            pytest.fail("Expected 'Inactive user' error for inactive user")
        except Exception as e:
            if "401" in str(e):
                assert hasattr(e, "response"), "Response should exist in the exception"
                assert e.response is not None, "Response should not be None"

                response_content = e.response.text
                if "Inactive user" in response_content:
                    logger.info(
                        f"Inactive user correctly received 'Inactive user' error for create session endpoint: {e.response.text}"
                    )
                    return

            pytest.fail(f"Unexpected error for inactive user: {str(e)}")

    def test_create_session_with_nonexistent_user_returns_user_not_found_error(
        self, res_environment: ResEnvironment
    ) -> None:
        """Test that non-existent users get proper 'User not found' error for create session endpoint."""
        try:
            nonexistent_auth = ClientAuth(username="nonexistent_user_12345")
            api_client = ApiClient(res_environment, nonexistent_auth)
            payload = self._get_create_session_payload()  # type: ignore
            request_content = CreateSessionRequestContent(**payload)

            api_client.create_session(request_content)
            pytest.fail("Expected 'User not found' error for non-existent user")
        except Exception as e:
            if "401" in str(e):
                assert hasattr(e, "response"), "Response should exist in the exception"
                assert e.response is not None, "Response should not be None"

                response_content = e.response.text
                if "User not found" in response_content:
                    logger.info(
                        "Non-existent user correctly received 'User not found' error for create session endpoint"
                    )
                    return

            pytest.fail(f"Unexpected error for non-existent user: {str(e)}")

    def test_create_session_without_auth_token_returns_no_authorization_token_provided_error(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
    ) -> None:
        """Test that requests without auth tokens get proper 'No authorization token provided' error for create session endpoint."""
        try:
            no_auth = ClientAuth(username="user1", auth_token=None)
            api_client = ApiClient(res_environment, no_auth)
            payload = self._get_create_session_payload()  # type: ignore
            request_content = CreateSessionRequestContent(**payload)

            api_client.create_session(request_content)
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
                        "Request without auth token correctly received 'No authorization token provided' error for create session endpoint"
                    )
                    return

            pytest.fail(f"Unexpected error for request without auth token: {str(e)}")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_session_in_prod_with_invalid_auth_token_returns_unable_to_retrieve_username_error(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        admin: ClientAuth,
    ) -> None:
        """Test that requests with invalid auth tokens get proper error in production for create session endpoint."""
        from tests.integration.framework.utils.lambda_utils import (
            set_backend_lambda_test_mode,
        )

        set_backend_lambda_test_mode(region, environment_name, False)
        try:
            api_client = ApiClient(res_environment, admin)
            payload = self._get_create_session_payload()  # type: ignore
            request_content = CreateSessionRequestContent(**payload)

            api_client.create_session(request_content)
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
                        "Request with invalid auth token correctly received 'Unable to retrieve username' error for create session endpoint"
                    )
                    return

            pytest.fail(
                f"Unexpected error for request with invalid auth token: {str(e)}"
            )
        finally:
            set_backend_lambda_test_mode(region, environment_name, True)

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_session_missing_hibernation_enabled(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """Test that missing hibernation_enabled returns 400 error."""
        try:
            api_client = ApiClient(res_environment, admin)
            payload = self._get_create_session_payload()  # type: ignore
            del payload["session"]["hibernation_enabled"]
            request_content = CreateSessionRequestContent(**payload)

            api_client.create_session(request_content)
            pytest.fail("Expected 400 error for missing hibernation_enabled")
        except Exception as e:
            if isinstance(e, pytest.fail.Exception):
                raise
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "hibernation_enabled" in e.response.text
            ), f"Expected hibernation_enabled error, got: {e.response.text}"
            logger.info(
                f"Missing hibernation_enabled correctly received 400 error: {str(e)}"
            )

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="res-disabled-stack-test"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="res-disabled-stack-test"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="Test project for disabled stack validation",
                    enable_budgets=False,
                ),
                ["home"],
                ["RESAdministrators"],
                ["clusteradmin"],
                "admin",
            )
        ],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "software_stack",
        [
            (
                VirtualDesktopSoftwareStack(
                    name="res-integ-test-disabled-stack",
                    description="Disabled stack for testing",
                    base_os=VirtualDesktopBaseOS.AMAZON_LINUX2023,
                    architecture=VirtualDesktopArchitecture.X86_64,
                    min_storage=SocaMemory(value=50, unit=SocaMemoryUnit.GB),
                    min_ram=SocaMemory(value=4, unit=SocaMemoryUnit.GB),
                    gpu=VirtualDesktopGPU.NO_GPU,
                    allowed_instance_types=["t3", "m6a"],
                    enabled=False,
                ),
                "project",
                "admin",
            )
        ],
        indirect=True,
    )
    def test_create_session_with_disabled_software_stack(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        admin_username: str,
        admin: ClientAuth,
        project: "Project",
        software_stack: "VirtualDesktopSoftwareStack",
    ) -> None:
        """Test that creating a session with a disabled software stack returns 400."""
        api_client = ApiClient(res_environment, admin)

        try:
            payload = self._get_create_session_payload(  # type: ignore
                software_stack_id=software_stack.stack_id,
                base_os=software_stack.base_os.value,
                project={"project_id": project.project_id},
            )
            request_content = CreateSessionRequestContent(**payload)
            api_client.create_session(request_content)
            pytest.fail("Expected 400 error for disabled software stack")
        except Exception as e:
            if isinstance(e, pytest.fail.Exception):
                raise
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response")
            assert "not available" in e.response.text.lower()
            logger.info(f"Disabled software stack correctly rejected: {str(e)}")
