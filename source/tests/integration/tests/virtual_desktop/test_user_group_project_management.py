#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

"""
VDI session-creation denial tests for user/group/project access control.

Covers scenarios where session creation should be rejected:
- Disabled group member cannot create a session
- Disabled project blocks session creation
- Non-member cannot create a session
- Permission-profile on-behalf (owner vs member)

All tests are ``@nightly`` — they exercise VDI session creation endpoints.
"""

import logging
import os
import uuid
from typing import Any, Dict

import pytest

from ideadatamodel import (  # type: ignore
    BatchDeleteRoleAssignmentRequest,
    BatchPutRoleAssignmentRequest,
    CreateProjectRequest,
    DeleteProjectRequest,
    DeleteRoleAssignmentRequest,
    Project,
    PutRoleAssignmentRequest,
)
from ideadatamodel.constants import (  # type: ignore
    PROJECT_MEMBER_ROLE_ID,
    PROJECT_OWNER_ROLE_ID,
    PROJECT_ROLE_ASSIGNMENT_TYPE,
    ROLE_ASSIGNMENT_ACTOR_GROUP_TYPE,
    ROLE_ASSIGNMENT_ACTOR_USER_TYPE,
)
from tests.integration.framework.client.api_client import (
    ApiClient,
    BatchCreateSessionRequestContent,
)
from tests.integration.framework.client.res_client import ResClient
from tests.integration.framework.fixtures.project import project
from tests.integration.framework.fixtures.res_environment import (
    ResEnvironment,
    res_environment,
)
from tests.integration.framework.fixtures.software_stack import software_stack
from tests.integration.framework.fixtures.users.admin import admin
from tests.integration.framework.fixtures.users.non_admin import non_admin
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.model_utils import get_backend_model_class
from tests.integration.framework.utils.retry_utils import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_INITIAL_DELAY,
    DEFAULT_MAX_DELAY,
    DEFAULT_MAX_RETRIES,
    retry_with_backoff,
)
from tests.integration.tests.smoke.config import AL2023_SOFTWARE_STACK

logger = logging.getLogger(__name__)

VirtualDesktopSession = get_backend_model_class(
    "virtual_desktop_session", "VirtualDesktopSession"
)
BatchOperationErrorCode = get_backend_model_class(
    "batch_operation_error_code", "BatchOperationErrorCode"
)

_RUN_ID = str(uuid.uuid4())[:6]


@pytest.mark.nightly
@pytest.mark.usefixtures("res_environment")
@pytest.mark.usefixtures("region")
class TestGroupSessionDenial:
    """Disabled group blocks session creation for its members."""

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize("admin_username", ["admin1"])
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="integ-gdis" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="integ-gdis" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="Group disable access test",
                    enable_budgets=False,
                ),
                ["home"],
                ["group_1"],
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
    # TODO: This test disables group_1 globally, which causes parallel tests that
    # depend on group_1 membership (e.g., test_end_to_end_succeed) to fail with
    # "not authorized to create sessions" or "does not belong in the selected project".
    # It cannot run in parallel with other tests that use group_1 for VDI session creation.
    @pytest.mark.skip(
        reason="Disables group_1 globally; unsafe to run in parallel with other VDI tests"
    )
    def test_disabled_group_member_cannot_create_session(
        self,
        request: pytest.FixtureRequest,
        res_environment: ResEnvironment,
        admin: ClientAuth,
        admin_username: str,
        non_admin: ClientAuth,
        non_admin_username: str,
        project: Project,
        software_stack: Any,
    ) -> None:
        """
        Disable a group → member of that group cannot create a session
        in a project where only that group has access.
        """
        api_invoker_type = request.config.getoption("--api-invoker-type")
        admin_client = ResClient(res_environment, admin, api_invoker_type)

        group_name = "group_1"  # user1 is a member of group_1

        def _reenable_group() -> None:
            try:
                admin_client.enable_group(group_name)
            except Exception:
                pass

        request.addfinalizer(_reenable_group)

        logger.info(f"Disabling group {group_name}...")
        admin_client.disable_group(group_name)

        def _check_group_disabled() -> None:
            result = admin_client.get_group(group_name)
            assert not result.group.enabled, "Group should be disabled"

        retry_with_backoff(
            func=_check_group_disabled,
            max_retries=DEFAULT_MAX_RETRIES,
            initial_delay=DEFAULT_INITIAL_DELAY,
            backoff_factor=DEFAULT_BACKOFF_FACTOR,
            max_delay=DEFAULT_MAX_DELAY,
            exceptions=(AssertionError,),
        )

        non_admin_api = ApiClient(res_environment, non_admin)
        session_request = BatchCreateSessionRequestContent(
            sessions=[
                VirtualDesktopSession(
                    name=f"grp-deny-{_RUN_ID}",
                    description="Session by member of disabled group",
                    owner=non_admin_username,
                    hibernation_enabled=False,
                    software_stack_id=software_stack.stack_id,
                    base_os=software_stack.base_os,
                    server={
                        "instance_type": "t3.medium",
                        "root_volume_size": {
                            "value": software_stack.min_storage.value,
                            "unit": software_stack.min_storage.unit,
                        },
                    },
                    project={"project_id": project.project_id},
                )
            ]
        )

        response = non_admin_api.batch_create_session(session_request)
        logger.info(
            f"Batch create response: successful={response.successful_list}, "  # type: ignore[attr-defined]
            f"unsuccessful={response.unsuccessful_list}"  # type: ignore[attr-defined]
        )
        assert response is not None
        assert (
            response.unsuccessful_list
        ), "Disabled group member should not be able to create a session"
        failure = response.unsuccessful_list[0]
        assert (
            failure.error_code == BatchOperationErrorCode.BADREQUESTEXCEPTION
        ), f"Expected BADREQUESTEXCEPTION, got: {failure.error_code}"
        failure_msg = failure.message.lower()
        assert (
            "does not belong" in failure_msg
            or "is not part of" in failure_msg
            or "not authorized to create sessions" in failure_msg
        ), f"Expected access denied message, got: {failure.message}"


@pytest.mark.nightly
@pytest.mark.usefixtures("res_environment")
@pytest.mark.usefixtures("region")
class TestProjectSessionDenial:
    """Non-membership blocks session creation."""

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize("admin_username", ["admin1"])
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="integ-nonm" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="integ-nonm" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="Non-member access denial test",
                    enable_budgets=False,
                ),
                ["home"],
                ["RESAdministrators"],  # Only admins — user1 is NOT a member
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
    def test_non_member_cannot_create_session(
        self,
        request: pytest.FixtureRequest,
        res_environment: ResEnvironment,
        admin: ClientAuth,
        admin_username: str,
        non_admin: ClientAuth,
        non_admin_username: str,
        project: Project,
        software_stack: Any,
    ) -> None:
        """User not in project cannot create a session in that project."""
        non_admin_api = ApiClient(res_environment, non_admin)
        session_request = BatchCreateSessionRequestContent(
            sessions=[
                VirtualDesktopSession(
                    name=f"nonm-{_RUN_ID}",
                    description="Session by non-member (should fail)",
                    owner=non_admin_username,
                    hibernation_enabled=False,
                    software_stack_id=software_stack.stack_id,
                    base_os=software_stack.base_os,
                    server={
                        "instance_type": "t3.medium",
                        "root_volume_size": {
                            "value": software_stack.min_storage.value,
                            "unit": software_stack.min_storage.unit,
                        },
                    },
                    project={"project_id": project.project_id},
                )
            ]
        )

        response = non_admin_api.batch_create_session(session_request)
        logger.info(
            f"Batch create response: successful={response.successful_list}, "  # type: ignore[attr-defined]
            f"unsuccessful={response.unsuccessful_list}"  # type: ignore[attr-defined]
        )
        assert response is not None
        assert (
            response.unsuccessful_list
        ), "Non-member should not be able to create a session in this project"
        failure = response.unsuccessful_list[0]
        assert (
            failure.error_code == BatchOperationErrorCode.BADREQUESTEXCEPTION
        ), f"Expected BADREQUESTEXCEPTION, got: {failure.error_code}"
        assert (
            "not authorized to create sessions" in failure.message.lower()
        ), f"Expected 'not authorized to create sessions' in message, got: {failure.message}"


@pytest.mark.nightly
@pytest.mark.usefixtures("res_environment")
@pytest.mark.usefixtures("region")
class TestPermissionProfileOnBehalf:
    """
    Permission-profile on-behalf: PROJECT_OWNER can create sessions for others;
    PROJECT_MEMBER cannot.
    """

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize("admin_username", ["admin1"])
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="integ-behalf" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="integ-behalf" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="On-behalf permission test",
                    enable_budgets=False,
                ),
                ["home"],
                [],  # No groups — we assign users manually with specific roles
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
    def test_project_owner_can_create_session_for_member(
        self,
        request: pytest.FixtureRequest,
        res_environment: ResEnvironment,
        admin: ClientAuth,
        admin_username: str,
        non_admin: ClientAuth,
        non_admin_username: str,
        project: Project,
        software_stack: Any,
    ) -> None:
        """
        PROJECT_OWNER can create a session on behalf of a member.

        The request should pass the authz check (may fail later for infra
        reasons like missing software stack — that's acceptable for this test).
        """
        api_invoker_type = request.config.getoption("--api-invoker-type")
        admin_client = ResClient(res_environment, admin, api_invoker_type)

        # Assign admin as OWNER, non_admin as MEMBER
        admin_client.batch_put_role_assignment(
            BatchPutRoleAssignmentRequest(
                items=[
                    PutRoleAssignmentRequest(
                        resource_id=project.project_id,
                        resource_type=PROJECT_ROLE_ASSIGNMENT_TYPE,
                        actor_id=admin_username,
                        actor_type=ROLE_ASSIGNMENT_ACTOR_USER_TYPE,
                        role_id=PROJECT_OWNER_ROLE_ID,
                        request_id="owner",
                    ),
                    PutRoleAssignmentRequest(
                        resource_id=project.project_id,
                        resource_type=PROJECT_ROLE_ASSIGNMENT_TYPE,
                        actor_id=non_admin_username,
                        actor_type=ROLE_ASSIGNMENT_ACTOR_USER_TYPE,
                        role_id=PROJECT_MEMBER_ROLE_ID,
                        request_id="member",
                    ),
                ]
            )
        )

        def _cleanup_roles() -> None:
            try:
                admin_client.batch_delete_role_assignment(
                    BatchDeleteRoleAssignmentRequest(
                        items=[
                            DeleteRoleAssignmentRequest(
                                resource_id=project.project_id,
                                resource_type=PROJECT_ROLE_ASSIGNMENT_TYPE,
                                actor_id=admin_username,
                                actor_type=ROLE_ASSIGNMENT_ACTOR_USER_TYPE,
                                request_id="c1",
                            ),
                            DeleteRoleAssignmentRequest(
                                resource_id=project.project_id,
                                resource_type=PROJECT_ROLE_ASSIGNMENT_TYPE,
                                actor_id=non_admin_username,
                                actor_type=ROLE_ASSIGNMENT_ACTOR_USER_TYPE,
                                request_id="c2",
                            ),
                        ]
                    )
                )
            except Exception:
                pass

        request.addfinalizer(_cleanup_roles)

        api_client = ApiClient(res_environment, admin)
        session_request = BatchCreateSessionRequestContent(
            sessions=[
                VirtualDesktopSession(
                    name=f"behalf-{_RUN_ID}",
                    description="On-behalf by owner",
                    owner=non_admin_username,
                    hibernation_enabled=False,
                    software_stack_id=software_stack.stack_id,
                    base_os=software_stack.base_os,
                    server={
                        "instance_type": "t3.medium",
                        "root_volume_size": {
                            "value": software_stack.min_storage.value,
                            "unit": software_stack.min_storage.unit,
                        },
                    },
                    project={"project_id": project.project_id},
                )
            ]
        )

        response = api_client.batch_create_session(session_request)
        logger.info(
            f"Batch create response: successful={response.successful_list}, "  # type: ignore[attr-defined]
            f"unsuccessful={response.unsuccessful_list}"  # type: ignore[attr-defined]
        )
        assert response is not None
        # Owner should pass the authorization check. The session may still
        # fail for infra reasons (missing software stack) but NOT for
        # permission reasons.
        if response.unsuccessful_list:
            failure_msg = response.unsuccessful_list[0].message.lower()
            assert (
                "permission" not in failure_msg
                and "unauthorized" not in failure_msg
                and "not authorized" not in failure_msg
            ), f"Owner should have permission for on-behalf, got: {response.unsuccessful_list[0].message}"

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize("admin_username", ["admin1"])
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="integ-member" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="integ-member" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="Member on-behalf denial test",
                    enable_budgets=False,
                ),
                ["home"],
                [],  # No groups — we assign users manually with specific roles
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
    def test_project_member_cannot_create_session_for_others(
        self,
        request: pytest.FixtureRequest,
        res_environment: ResEnvironment,
        admin: ClientAuth,
        admin_username: str,
        non_admin: ClientAuth,
        non_admin_username: str,
        project: Project,
        software_stack: Any,
    ) -> None:
        """
        PROJECT_MEMBER cannot create a session on behalf of another user.
        The API should reject it.
        """
        api_invoker_type = request.config.getoption("--api-invoker-type")
        admin_client = ResClient(res_environment, admin, api_invoker_type)

        # Assign both as MEMBER (not owner)
        admin_client.batch_put_role_assignment(
            BatchPutRoleAssignmentRequest(
                items=[
                    PutRoleAssignmentRequest(
                        resource_id=project.project_id,
                        resource_type=PROJECT_ROLE_ASSIGNMENT_TYPE,
                        actor_id=admin_username,
                        actor_type=ROLE_ASSIGNMENT_ACTOR_USER_TYPE,
                        role_id=PROJECT_MEMBER_ROLE_ID,
                        request_id="m1",
                    ),
                    PutRoleAssignmentRequest(
                        resource_id=project.project_id,
                        resource_type=PROJECT_ROLE_ASSIGNMENT_TYPE,
                        actor_id=non_admin_username,
                        actor_type=ROLE_ASSIGNMENT_ACTOR_USER_TYPE,
                        role_id=PROJECT_MEMBER_ROLE_ID,
                        request_id="m2",
                    ),
                ]
            )
        )

        def _cleanup_roles() -> None:
            try:
                admin_client.batch_delete_role_assignment(
                    BatchDeleteRoleAssignmentRequest(
                        items=[
                            DeleteRoleAssignmentRequest(
                                resource_id=project.project_id,
                                resource_type=PROJECT_ROLE_ASSIGNMENT_TYPE,
                                actor_id=admin_username,
                                actor_type=ROLE_ASSIGNMENT_ACTOR_USER_TYPE,
                                request_id="c1",
                            ),
                            DeleteRoleAssignmentRequest(
                                resource_id=project.project_id,
                                resource_type=PROJECT_ROLE_ASSIGNMENT_TYPE,
                                actor_id=non_admin_username,
                                actor_type=ROLE_ASSIGNMENT_ACTOR_USER_TYPE,
                                request_id="c2",
                            ),
                        ]
                    )
                )
            except Exception:
                pass

        request.addfinalizer(_cleanup_roles)

        non_admin_api = ApiClient(res_environment, non_admin)
        session_request = BatchCreateSessionRequestContent(
            sessions=[
                VirtualDesktopSession(
                    name=f"behalf-deny-{_RUN_ID}",
                    description="On-behalf by member (should fail)",
                    owner=admin_username,
                    hibernation_enabled=False,
                    software_stack_id=software_stack.stack_id,
                    base_os=software_stack.base_os,
                    server={
                        "instance_type": "t3.medium",
                        "root_volume_size": {
                            "value": software_stack.min_storage.value,
                            "unit": software_stack.min_storage.unit,
                        },
                    },
                    project={"project_id": project.project_id},
                )
            ]
        )

        response = non_admin_api.batch_create_session(session_request)
        logger.info(
            f"Batch create response: successful={response.successful_list}, "  # type: ignore[attr-defined]
            f"unsuccessful={response.unsuccessful_list}"  # type: ignore[attr-defined]
        )
        assert response is not None
        assert (
            response.unsuccessful_list
        ), "PROJECT_MEMBER should not be able to create sessions for others"
        failure = response.unsuccessful_list[0]
        assert (
            failure.error_code == BatchOperationErrorCode.BADREQUESTEXCEPTION
        ), f"Expected BADREQUESTEXCEPTION, got: {failure.error_code}"
        assert (
            "not authorized to create sessions for others" in failure.message.lower()
        ), f"Expected 'not authorized to create sessions for others' in message, got: {failure.message}"
