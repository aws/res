#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
import os
from typing import Any, Dict, List

import pytest

# Project (and PROJECT_OWNER_ROLE_ID) still go through the not-yet-migrated
# cluster-manager API, so they stay ideadatamodel.
from ideadatamodel import (  # type: ignore
    BatchPutRoleAssignmentRequest,
    CreateProjectRequest,
    DeleteProjectRequest,
    Project,
    PutRoleAssignmentRequest,
    UpdateModuleSettingsRequest,
)
from ideadatamodel.constants import (  # type: ignore
    PROJECT_MEMBER_ROLE_ID,
    PROJECT_OWNER_ROLE_ID,
    PROJECT_ROLE_ASSIGNMENT_TYPE,
    ROLE_ASSIGNMENT_ACTOR_USER_TYPE,
)
from tests.integration.framework.client.api_client import ApiClient
from tests.integration.framework.client.res_client import ResClient
from tests.integration.framework.fixtures.project import project
from tests.integration.framework.fixtures.res_environment import (
    ResEnvironment,
    res_environment,
)
from tests.integration.framework.fixtures.software_stack import software_stack
from tests.integration.framework.fixtures.users import admin, inactive_user, non_admin
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.lambda_utils import (
    set_backend_lambda_dry_mode,
    set_backend_lambda_test_mode,
)
from tests.integration.framework.utils.model_utils import get_backend_model_class

BatchCreateSessionRequestContent = get_backend_model_class(
    "batch_create_session_request_content", "BatchCreateSessionRequestContent"
)
BatchCreateSessionResponseContent = get_backend_model_class(
    "batch_create_session_response_content", "BatchCreateSessionResponseContent"
)
VirtualDesktopSession = get_backend_model_class(
    "virtual_desktop_session", "VirtualDesktopSession"
)
BatchOperationErrorCode = get_backend_model_class(
    "batch_operation_error_code", "BatchOperationErrorCode"
)
VirtualDesktopSoftwareStack = get_backend_model_class(
    "virtual_desktop_software_stack", "VirtualDesktopSoftwareStack"
)
VirtualDesktopArchitecture = get_backend_model_class(
    "virtual_desktop_architecture", "VirtualDesktopArchitecture"
)
VirtualDesktopBaseOS = get_backend_model_class(
    "virtual_desktop_base_os", "VirtualDesktopBaseOs"
)
VirtualDesktopGPU = get_backend_model_class("virtual_desktop_gpu", "VirtualDesktopGpu")
ResMemory = get_backend_model_class("res_memory", "ResMemory")

logger = logging.getLogger(__name__)


def _set_smart_retry(
    res_environment: ResEnvironment,
    admin: ClientAuth,
    api_invoker_type: str,
    enabled: bool,
) -> None:
    """Flip vdc.dcv_session.smart_retry.enabled on the deployed environment."""
    admin_client = ResClient(res_environment, admin, api_invoker_type)
    admin_client.update_module_settings(
        request=UpdateModuleSettingsRequest(
            module_id="vdc",
            settings={"dcv_session": {"smart_retry": {"enabled": enabled}}},
        )
    )


class TestBatchCreateSession:

    def _get_session_payload(self, **overrides: Any) -> Dict[str, Any]:
        """Helper to build a single session dict for batch create."""
        payload = {
            "name": "TestBatchSession",
            "hibernation_enabled": False,
            "software_stack_id": "ss-base-windows-x86-64-base",
            "base_os": "windows",
            "server": {
                "instance_type": "t3.2xlarge",
                "root_volume_size": {"value": 50, "unit": "gb"},
            },
        }
        payload.update(overrides)
        return payload

    def _build_request(self, sessions_payloads: List[Dict[str, Any]]) -> Any:
        """Build a BatchCreateSessionRequestContent from a list of session dicts."""
        session_list = [VirtualDesktopSession.from_dict(s) for s in sessions_payloads]
        return BatchCreateSessionRequestContent(sessions=session_list)

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="test-batch-create-admin-dry"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="test-batch-create-admin-dry"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="Admin dry run test",
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
                    name="res-batch-create-admin-dry",
                    description="Stack for batch create admin dry run test",
                    base_os=VirtualDesktopBaseOS.AMZN2023,
                    architecture=VirtualDesktopArchitecture.X86_64,
                    min_storage=ResMemory(value=50, unit="gb"),
                    min_ram=ResMemory(value=4, unit="gb"),
                    gpu=VirtualDesktopGPU.NO_GPU,
                    allowed_instance_types=["t3", "m6a"],
                ),
                "project",
                "admin",
            )
        ],
        indirect=True,
    )
    def test_batch_create_session_with_dry_run_mode_as_admin(
        self,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        admin_username: str,
        admin: ClientAuth,
        project: "Project",
        software_stack: Any,
    ) -> None:
        """Test that admin can successfully batch create sessions in dry run mode."""
        set_backend_lambda_dry_mode(region, environment_name, True)
        try:
            api_client = ApiClient(res_environment, admin)
            sessions = [
                self._get_session_payload(
                    name="Session1",
                    project={"project_id": project.project_id},
                    software_stack_id=software_stack.stack_id,
                    base_os=software_stack.base_os.value,
                ),
                self._get_session_payload(
                    name="Session2",
                    project={"project_id": project.project_id},
                    software_stack_id=software_stack.stack_id,
                    base_os=software_stack.base_os.value,
                ),
            ]
            request_content = self._build_request(sessions)
            response = api_client.batch_create_session(request_content)

            assert response is not None, "Response should not be None"
            assert (
                len(response.successful_list) == 2
            ), f"Admin should successfully create both sessions in dry run, got unsuccessful: {[u.message for u in response.unsuccessful_list]}"
            assert (
                len(response.unsuccessful_list) == 0
            ), "There should be no unsuccessful sessions"
        finally:
            set_backend_lambda_dry_mode(region, environment_name, False)

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="test-batch-create-user-dry"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="test-batch-create-user-dry"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="Non-admin dry run test",
                    enable_budgets=False,
                ),
                ["home"],
                [],
                ["user1"],
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
                    name="res-batch-create-user-dry",
                    description="Stack for batch create non-admin dry run test",
                    base_os=VirtualDesktopBaseOS.AMZN2023,
                    architecture=VirtualDesktopArchitecture.X86_64,
                    min_storage=ResMemory(value=50, unit="gb"),
                    min_ram=ResMemory(value=4, unit="gb"),
                    gpu=VirtualDesktopGPU.NO_GPU,
                    allowed_instance_types=["t3", "m6a"],
                ),
                "project",
                "admin",
            )
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_batch_create_session_with_dry_run_mode_as_non_admin(
        self,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        admin_username: str,
        project: "Project",
        software_stack: Any,
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        """Test that non-admin user can successfully batch create sessions in dry run mode."""
        set_backend_lambda_dry_mode(region, environment_name, True)
        try:
            api_client = ApiClient(res_environment, non_admin)
            sessions = [
                self._get_session_payload(
                    name="NonAdminSession",
                    project={"project_id": project.project_id},
                    software_stack_id=software_stack.stack_id,
                    base_os=software_stack.base_os.value,
                )
            ]
            request_content = self._build_request(sessions)
            response = api_client.batch_create_session(request_content)

            assert response is not None, "Response should not be None"
            assert (
                len(response.successful_list) == 1
            ), f"Non-admin should successfully create session in dry run, got unsuccessful: {[u.message for u in response.unsuccessful_list]}"
            assert (
                len(response.unsuccessful_list) == 0
            ), "There should be no unsuccessful sessions"
        finally:
            set_backend_lambda_dry_mode(region, environment_name, False)

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_create_session_missing_software_stack_id(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """Test that sessions missing software_stack_id are returned in unsuccessful list."""
        api_client = ApiClient(res_environment, admin)
        payload = self._get_session_payload(project={"project_id": "any-project-id"})
        del payload["software_stack_id"]
        request_content = self._build_request([payload])
        response = api_client.batch_create_session(request_content)

        assert response is not None, "Response should not be None"
        assert len(response.successful_list) == 0, "Should have no successful sessions"
        assert (
            len(response.unsuccessful_list) == 1
        ), "Should have 1 unsuccessful session"
        assert (
            response.unsuccessful_list[0].error_code
            == BatchOperationErrorCode.BADREQUESTEXCEPTION
        )
        assert (
            "software_stack_id" in response.unsuccessful_list[0].message
        ), f"Expected software_stack_id error, got: {response.unsuccessful_list[0].message}"

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_create_session_missing_server(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """Test that sessions missing server are returned in unsuccessful list."""
        api_client = ApiClient(res_environment, admin)
        payload = self._get_session_payload(project={"project_id": "any-project-id"})
        del payload["server"]
        request_content = self._build_request([payload])
        response = api_client.batch_create_session(request_content)

        assert response is not None, "Response should not be None"
        assert len(response.successful_list) == 0, "Should have no successful sessions"
        assert (
            len(response.unsuccessful_list) == 1
        ), "Should have 1 unsuccessful session"
        assert (
            response.unsuccessful_list[0].error_code
            == BatchOperationErrorCode.BADREQUESTEXCEPTION
        )
        assert (
            "root_volume_size" in response.unsuccessful_list[0].message
        ), f"Expected server error, got: {response.unsuccessful_list[0].message}"

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_create_session_missing_project(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """Test that sessions missing project are returned in unsuccessful list."""
        api_client = ApiClient(res_environment, admin)
        payload = self._get_session_payload()
        # Don't include project at all
        request_content = self._build_request([payload])
        response = api_client.batch_create_session(request_content)

        assert response is not None, "Response should not be None"
        assert len(response.successful_list) == 0, "Should have no successful sessions"
        assert (
            len(response.unsuccessful_list) == 1
        ), "Should have 1 unsuccessful session"
        assert (
            response.unsuccessful_list[0].error_code
            == BatchOperationErrorCode.BADREQUESTEXCEPTION
        )
        assert (
            "project" in response.unsuccessful_list[0].message.lower()
        ), f"Expected project error, got: {response.unsuccessful_list[0].message}"

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_create_session_missing_hibernation_enabled(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """Test that sessions missing hibernation_enabled are returned in unsuccessful list."""
        api_client = ApiClient(res_environment, admin)
        payload = self._get_session_payload(project={"project_id": "any-project-id"})
        del payload["hibernation_enabled"]
        request_content = self._build_request([payload])
        response = api_client.batch_create_session(request_content)

        assert response is not None, "Response should not be None"
        assert len(response.successful_list) == 0, "Should have no successful sessions"
        assert (
            len(response.unsuccessful_list) == 1
        ), "Should have 1 unsuccessful session"
        assert (
            response.unsuccessful_list[0].error_code
            == BatchOperationErrorCode.BADREQUESTEXCEPTION
        )
        assert (
            "hibernation_enabled" in response.unsuccessful_list[0].message
        ), f"Expected hibernation_enabled error, got: {response.unsuccessful_list[0].message}"
        logger.info(
            "Missing hibernation_enabled correctly returned in unsuccessful list"
        )

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_create_session_empty_sessions_list(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """Test that an empty sessions list returns 400 from server-side validation."""
        try:
            api_client = ApiClient(res_environment, admin)
            # Send raw empty list - bypass client model validation if any
            request_content = BatchCreateSessionRequestContent(sessions=[])
            api_client.batch_create_session(request_content)
            pytest.fail("Expected error for empty sessions list")
        except (ValueError, Exception) as e:
            # Either client-side ValueError or server-side 400
            if isinstance(e, ValueError):
                pass  # Client-side validation caught it
            else:
                assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
                assert hasattr(e, "response"), "Response should exist in the exception"
                assert (
                    "should be non-empty" in e.response.text
                ), f"Expected 'should be non-empty' validation error, got: {e.response.text}"

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="test-batch-create-mixed"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="test-batch-create-mixed"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="Mixed valid/invalid test",
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
                    name="res-batch-create-mixed",
                    description="Stack for batch create mixed test",
                    base_os=VirtualDesktopBaseOS.AMZN2023,
                    architecture=VirtualDesktopArchitecture.X86_64,
                    min_storage=ResMemory(value=50, unit="gb"),
                    min_ram=ResMemory(value=4, unit="gb"),
                    gpu=VirtualDesktopGPU.NO_GPU,
                    allowed_instance_types=["t3", "m6a"],
                ),
                "project",
                "admin",
            )
        ],
        indirect=True,
    )
    def test_batch_create_session_mixed_valid_and_invalid(
        self,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        admin_username: str,
        admin: ClientAuth,
        project: "Project",
        software_stack: Any,
    ) -> None:
        """Test that a mix of valid and invalid sessions returns correct split."""
        set_backend_lambda_dry_mode(region, environment_name, True)
        try:
            api_client = ApiClient(res_environment, admin)
            valid_session = self._get_session_payload(
                name="ValidSession",
                project={"project_id": project.project_id},
                software_stack_id=software_stack.stack_id,
                base_os=software_stack.base_os.value,
            )
            invalid_session = self._get_session_payload(
                name="InvalidSession", project={"project_id": project.project_id}
            )
            del invalid_session["software_stack_id"]

            request_content = self._build_request([valid_session, invalid_session])
            response = api_client.batch_create_session(request_content)

            assert response is not None, "Response should not be None"
            assert (
                len(response.successful_list) == 1
            ), f"Should have 1 successful session, got unsuccessful: {[u.message for u in response.unsuccessful_list]}"
            assert (
                len(response.unsuccessful_list) == 1
            ), "Should have 1 unsuccessful session"
            assert (
                response.unsuccessful_list[0].error_code
                == BatchOperationErrorCode.BADREQUESTEXCEPTION
            )
        finally:
            set_backend_lambda_dry_mode(region, environment_name, False)

    def test_batch_create_session_with_nonexistent_user(
        self,
        res_environment: ResEnvironment,
    ) -> None:
        """Test that non-existent users get proper 'User not found' error."""
        try:
            nonexistent_auth = ClientAuth(username="nonexistent_user_12345")
            api_client = ApiClient(res_environment, nonexistent_auth)
            sessions = [self._get_session_payload(project={"project_id": "any"})]
            request_content = self._build_request(sessions)
            api_client.batch_create_session(request_content)
            pytest.fail("Expected 'User not found' error for non-existent user")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "User not found" in e.response.text
            ), f"Unexpected error for non-existent user: {str(e)}"

    @pytest.mark.parametrize("inactive_username", ["user2"])
    def test_batch_create_session_with_inactive_user(
        self,
        region: str,
        res_environment: ResEnvironment,
        inactive_username: str,
        inactive_user: ClientAuth,
    ) -> None:
        """Test that inactive users get proper 'Inactive user' error."""
        try:
            api_client = ApiClient(res_environment, inactive_user)
            sessions = [self._get_session_payload(project={"project_id": "any"})]
            request_content = self._build_request(sessions)
            api_client.batch_create_session(request_content)
            pytest.fail("Expected error for inactive user")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "Inactive user" in e.response.text
            ), f"Unexpected error for inactive user: {str(e)}"

    def test_batch_create_session_without_auth_token(
        self,
        res_environment: ResEnvironment,
    ) -> None:
        """Test that requests without auth tokens get proper error."""
        try:
            no_auth = ClientAuth(username="user1", auth_token=None)
            api_client = ApiClient(res_environment, no_auth)
            sessions = [self._get_session_payload(project={"project_id": "any"})]
            request_content = self._build_request(sessions)
            api_client.batch_create_session(request_content)
            pytest.fail("Expected 'No authorization token provided' error")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "No authorization token provided" in e.response.text
            ), f"Unexpected error: {str(e)}"

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_create_session_with_invalid_auth_token(
        self,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """Test that requests with invalid auth tokens get proper error in production."""
        set_backend_lambda_test_mode(region, environment_name, False)
        try:
            invalid_auth = ClientAuth(
                username="clusteradmin", auth_token="invalid_token_12345"
            )
            api_client = ApiClient(res_environment, invalid_auth)
            sessions = [self._get_session_payload(project={"project_id": "any"})]
            request_content = self._build_request(sessions)
            api_client.batch_create_session(request_content)
            pytest.fail(
                "Expected 'Unable to retrieve username' error for invalid auth token"
            )
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "Unable to retrieve username" in e.response.text
            ), f"Unexpected error: {str(e)}"
        finally:
            set_backend_lambda_test_mode(region, environment_name, True)

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="test-batch-create-no-project-access"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="test-batch-create-no-project-access"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="Project that user1 does not belong to",
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
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_batch_create_session_user_not_in_project(
        self,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        admin_username: str,
        project: "Project",
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        """Test that a user cannot create sessions in a project they don't belong to."""
        api_client = ApiClient(res_environment, non_admin)
        session = self._get_session_payload(
            name="NoAccessSession",
            project={"project_id": project.project_id},
        )

        request_content = self._build_request([session])
        response = api_client.batch_create_session(request_content)

        assert response is not None, "Response should not be None"
        assert len(response.successful_list) == 0, "Should have no successful sessions"
        assert (
            len(response.unsuccessful_list) == 1
        ), "Should have 1 unsuccessful session"
        assert (
            response.unsuccessful_list[0].error_code
            == BatchOperationErrorCode.BADREQUESTEXCEPTION
        )
        assert (
            "not authorized" in response.unsuccessful_list[0].message.lower()
        ), f"Expected project access error, got: {response.unsuccessful_list[0].message}"
        logger.info(
            "User correctly rejected from creating session in project they don't belong to"
        )

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="test-batch-create-no-cross-perm"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="test-batch-create-no-cross-perm"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="Non-admin without cross-user permission",
                    enable_budgets=False,
                ),
                ["home"],
                [],
                ["user1"],
                "admin",
            )
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_batch_create_session_non_admin_without_cross_user_permission(
        self,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        admin_username: str,
        project: "Project",
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        """Test that non-admin without vdis.create_terminate_others_sessions cannot create session for another user."""
        set_backend_lambda_dry_mode(region, environment_name, True)
        try:
            api_client = ApiClient(res_environment, non_admin)
            other_session = self._get_session_payload(
                name="OtherUserSession",
                owner="clusteradmin",
                project={"project_id": project.project_id},
            )

            request_content = self._build_request([other_session])
            response = api_client.batch_create_session(request_content)

            assert response is not None, "Response should not be None"
            assert (
                len(response.successful_list) == 0
            ), "Should have no successful sessions"
            assert (
                len(response.unsuccessful_list) == 1
            ), "Should have 1 unsuccessful session"
            assert (
                response.unsuccessful_list[0].error_code
                == BatchOperationErrorCode.BADREQUESTEXCEPTION
            )
            assert (
                "not authorized" in response.unsuccessful_list[0].message.lower()
            ), f"Expected authorization error, got: {response.unsuccessful_list[0].message}"
            logger.info(
                "Non-admin without permission correctly rejected for other user's session"
            )
        finally:
            set_backend_lambda_dry_mode(region, environment_name, False)

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="test-batch-create-cross-perm"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="test-batch-create-cross-perm"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="Non-admin with cross-user permission",
                    enable_budgets=False,
                ),
                ["home"],
                ["RESAdministrators"],
                ["user1", "clusteradmin"],
                "admin",
                PROJECT_OWNER_ROLE_ID,
            )
        ],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "software_stack",
        [
            (
                VirtualDesktopSoftwareStack(
                    name="res-batch-create-cross-perm",
                    description="Stack for cross-user permission test",
                    base_os=VirtualDesktopBaseOS.AMZN2023,
                    architecture=VirtualDesktopArchitecture.X86_64,
                    min_storage=ResMemory(value=50, unit="gb"),
                    min_ram=ResMemory(value=4, unit="gb"),
                    gpu=VirtualDesktopGPU.NO_GPU,
                    allowed_instance_types=["t3", "m6a"],
                ),
                "project",
                "admin",
            )
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_batch_create_session_non_admin_with_cross_user_permission(
        self,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        admin_username: str,
        project: "Project",
        software_stack: Any,
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        """Test that non-admin with vdis.create_terminate_others_sessions can create session for another user."""
        set_backend_lambda_dry_mode(region, environment_name, True)
        try:
            api_client = ApiClient(res_environment, non_admin)
            other_session = self._get_session_payload(
                name="CrossUserSession",
                owner="clusteradmin",
                project={"project_id": project.project_id},
                software_stack_id=software_stack.stack_id,
                base_os=software_stack.base_os.value,
            )

            request_content = self._build_request([other_session])
            response = api_client.batch_create_session(request_content)

            assert response is not None, "Response should not be None"
            assert (
                len(response.successful_list) == 1
            ), f"Should have 1 successful session, got unsuccessful: {[u.message for u in response.unsuccessful_list]}"
            assert (
                response.successful_list[0].name == "CrossUserSession"
            ), f"Expected CrossUserSession, got: {response.successful_list[0].name}"
            assert (
                len(response.unsuccessful_list) == 0
            ), "There should be no unsuccessful sessions"
            logger.info(
                "Non-admin with cross-user permission successfully created session for other user"
            )
        finally:
            set_backend_lambda_dry_mode(region, environment_name, False)

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_create_session_rejects_instance_type_when_smart_retry_enabled(
        self,
        request: Any,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """When smart retry is enabled, instance_type must not be set."""
        api_invoker_type = request.config.getoption("--api-invoker-type")
        _set_smart_retry(res_environment, admin, api_invoker_type, True)
        try:
            api_client = ApiClient(res_environment, admin)
            payload = self._get_session_payload(
                project={"project_id": "any-project-id"}
            )
            request_content = self._build_request([payload])
            response = api_client.batch_create_session(request_content)

            assert response is not None
            assert len(response.successful_list) == 0
            assert len(response.unsuccessful_list) == 1
            assert (
                response.unsuccessful_list[0].error_code
                == BatchOperationErrorCode.BADREQUESTEXCEPTION
            )
            assert "Smart Retry is enabled" in response.unsuccessful_list[0].message
        finally:
            _set_smart_retry(res_environment, admin, api_invoker_type, False)

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_create_session_rejects_subnet_id_when_smart_retry_enabled(
        self,
        request: Any,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """When smart retry is enabled, subnet_id must not be set."""
        api_invoker_type = request.config.getoption("--api-invoker-type")
        _set_smart_retry(res_environment, admin, api_invoker_type, True)
        try:
            api_client = ApiClient(res_environment, admin)
            payload = self._get_session_payload(
                project={"project_id": "any-project-id"}
            )
            del payload["server"]["instance_type"]
            payload["server"]["subnet_id"] = "subnet-00000000"
            request_content = self._build_request([payload])
            response = api_client.batch_create_session(request_content)

            assert response is not None
            assert len(response.successful_list) == 0
            assert len(response.unsuccessful_list) == 1
            assert (
                response.unsuccessful_list[0].error_code
                == BatchOperationErrorCode.BADREQUESTEXCEPTION
            )
            assert "Smart Retry is enabled" in response.unsuccessful_list[0].message
        finally:
            _set_smart_retry(res_environment, admin, api_invoker_type, False)

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="test-bc-hib-no-capable"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="test-bc-hib-no-capable"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="No hibernation-capable type reject",
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
                    name="res-batch-create-hibernation-no-capable",
                    description="Stack whose allowed_instance_types have no hibernation-capable type",
                    base_os=VirtualDesktopBaseOS.AMZN2023,
                    architecture=VirtualDesktopArchitecture.X86_64,
                    min_storage=ResMemory(value=50, unit="gb"),
                    min_ram=ResMemory(value=4, unit="gb"),
                    gpu=VirtualDesktopGPU.NVIDIA,
                    allowed_instance_types=["g4dn", "g5"],
                ),
                "project",
                "admin",
            )
        ],
        indirect=True,
    )
    def test_batch_create_session_rejects_hibernation_when_no_capable_type_under_smart_retry(
        self,
        request: Any,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
        project: "Project",
        software_stack: Any,
    ) -> None:
        """Under smart retry, reject hibernation requests when allowed_instance_types
        contains no hibernation-capable type."""
        api_invoker_type = request.config.getoption("--api-invoker-type")
        _set_smart_retry(res_environment, admin, api_invoker_type, True)
        try:
            api_client = ApiClient(res_environment, admin)
            payload = self._get_session_payload(
                hibernation_enabled=True,
                project={"project_id": project.project_id},
                software_stack_id=software_stack.stack_id,
                base_os=software_stack.base_os.value,
            )
            del payload["server"]["instance_type"]

            request_content = self._build_request([payload])
            response = api_client.batch_create_session(request_content)

            assert response is not None
            assert len(response.successful_list) == 0
            assert len(response.unsuccessful_list) == 1
            assert (
                response.unsuccessful_list[0].error_code
                == BatchOperationErrorCode.BADREQUESTEXCEPTION
            )
            assert (
                "No hibernation-capable instance type"
                in response.unsuccessful_list[0].message
            )
        finally:
            _set_smart_retry(res_environment, admin, api_invoker_type, False)

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="test-bc-hib-too-small"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="test-bc-hib-too-small"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="Root volume too small under smart retry",
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
                    name="res-batch-create-hibernation-too-small",
                    description="Stack with hibernation-capable allowed_instance_types",
                    base_os=VirtualDesktopBaseOS.AMZN2023,
                    architecture=VirtualDesktopArchitecture.X86_64,
                    min_storage=ResMemory(value=50, unit="gb"),
                    min_ram=ResMemory(value=4, unit="gb"),
                    gpu=VirtualDesktopGPU.NO_GPU,
                    allowed_instance_types=["t3", "m6a"],
                ),
                "project",
                "admin",
            )
        ],
        indirect=True,
    )
    def test_batch_create_session_rejects_hibernation_when_root_volume_too_small_under_smart_retry(
        self,
        request: Any,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
        project: "Project",
        software_stack: Any,
    ) -> None:
        """Under smart retry, reject hibernation requests when the requested root
        volume is smaller than what the smallest hibernation-capable type needs."""
        api_invoker_type = request.config.getoption("--api-invoker-type")
        _set_smart_retry(res_environment, admin, api_invoker_type, True)
        try:
            api_client = ApiClient(res_environment, admin)
            payload = self._get_session_payload(
                hibernation_enabled=True,
                project={"project_id": project.project_id},
                software_stack_id=software_stack.stack_id,
                base_os=software_stack.base_os.value,
            )
            del payload["server"]["instance_type"]
            payload["server"]["root_volume_size"] = {"value": 10, "unit": "gb"}

            request_content = self._build_request([payload])
            response = api_client.batch_create_session(request_content)

            assert response is not None
            assert len(response.successful_list) == 0
            assert len(response.unsuccessful_list) == 1
            assert (
                response.unsuccessful_list[0].error_code
                == BatchOperationErrorCode.BADREQUESTEXCEPTION
            )
            assert (
                "minimum required root volume size"
                in response.unsuccessful_list[0].message
            )
        finally:
            _set_smart_retry(res_environment, admin, api_invoker_type, False)

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="test-batch-create-disabled-proj"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="test-batch-create-disabled-proj"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="Disabled project session creation test",
                    enable_budgets=False,
                ),
                ["home"],
                ["RESAdministrators"],
                ["user1"],
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
                    name="res-batch-create-disabled-proj",
                    description="Stack for disabled project test",
                    base_os=VirtualDesktopBaseOS.AMZN2023,
                    architecture=VirtualDesktopArchitecture.X86_64,
                    min_storage=ResMemory(value=50, unit="gb"),
                    min_ram=ResMemory(value=4, unit="gb"),
                    gpu=VirtualDesktopGPU.NO_GPU,
                    allowed_instance_types=["t3", "m6a"],
                ),
                "project",
                "admin",
            )
        ],
        indirect=True,
    )
    def test_batch_create_session_disabled_project_rejected(
        self,
        request: Any,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
        non_admin_username: str,
        non_admin: ClientAuth,
        project: "Project",
        software_stack: Any,
    ) -> None:
        """Disabled project rejects session creation with 'is disabled' error."""
        api_invoker_type = request.config.getoption("--api-invoker-type")
        admin_client = ResClient(res_environment, admin, api_invoker_type)

        # Disable the project
        admin_client.disable_project(project.name)

        def _restore() -> None:
            try:
                admin_client.enable_project(project.name)
            except Exception:
                pass

        request.addfinalizer(_restore)

        # Attempt session creation as non-admin member
        non_admin_api = ApiClient(res_environment, non_admin)
        payload = self._get_session_payload(
            project={"project_id": project.project_id},
            software_stack_id=software_stack.stack_id,
            base_os=software_stack.base_os.value,
        )
        request_content = self._build_request([payload])
        response = non_admin_api.batch_create_session(request_content)

        assert response is not None, "Response should not be None"
        assert len(response.successful_list) == 0, "Should have no successful sessions"
        assert (
            len(response.unsuccessful_list) == 1
        ), "Should have 1 unsuccessful session"
        assert (
            response.unsuccessful_list[0].error_code
            == BatchOperationErrorCode.BADREQUESTEXCEPTION
        ), f"Expected BADREQUESTEXCEPTION, got: {response.unsuccessful_list[0].error_code}"
        expected_msg = f"Project {project.project_id} is disabled. Session creation is not allowed."
        assert (
            response.unsuccessful_list[0].message == expected_msg
        ), f"Expected '{expected_msg}', got: {response.unsuccessful_list[0].message}"
