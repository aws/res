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
Project management and role-assignment integration tests.

Covers project CRUD, enable/disable lifecycle, and role-assignment
add/list/remove via the cluster-manager API.
All tests are ``@dev`` — API-only, no VDI launch required.
"""

import logging
import uuid

import pytest

from ideadatamodel import (  # type: ignore
    BatchDeleteRoleAssignmentRequest,
    BatchPutRoleAssignmentRequest,
    CreateProjectRequest,
    DeleteProjectRequest,
    DeleteRoleAssignmentRequest,
    ListRoleAssignmentsRequest,
    Project,
    PutRoleAssignmentRequest,
)
from ideadatamodel.constants import (  # type: ignore
    PROJECT_MEMBER_ROLE_ID,
    PROJECT_ROLE_ASSIGNMENT_TYPE,
    ROLE_ASSIGNMENT_ACTOR_GROUP_TYPE,
    ROLE_ASSIGNMENT_ACTOR_USER_TYPE,
)
from tests.integration.framework.client.res_client import ResClient
from tests.integration.framework.fixtures.res_environment import (
    ResEnvironment,
    res_environment,
)
from tests.integration.framework.fixtures.users.admin import admin
from tests.integration.framework.fixtures.users.non_admin import non_admin
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.retry_utils import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_INITIAL_DELAY,
    DEFAULT_MAX_DELAY,
    DEFAULT_MAX_RETRIES,
    retry_with_backoff,
)

logger = logging.getLogger(__name__)

_RUN_ID = str(uuid.uuid4())[:6]


@pytest.mark.dev
@pytest.mark.usefixtures("res_environment")
@pytest.mark.usefixtures("region")
class TestProjectManagement:
    """Project CRUD and enable/disable via the cluster-manager API."""

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize("admin_username", ["admin1"])
    def test_project_create_enabled_by_default(
        self,
        request: pytest.FixtureRequest,
        res_environment: ResEnvironment,
        admin: ClientAuth,
        admin_username: str,
    ) -> None:
        """Create a project — it should be enabled by default."""
        api_invoker_type = request.config.getoption("--api-invoker-type")
        admin_client = ResClient(res_environment, admin, api_invoker_type)

        project_name = f"integ-create-{_RUN_ID}"
        project = Project(
            title=project_name,
            name=project_name,
            description="Verify project is enabled on creation",
            enable_budgets=False,
        )

        result = admin_client.create_project(
            CreateProjectRequest(project=project, filesystem_names=["home"])
        )
        created = result.project
        assert created is not None
        assert created.project_id is not None

        request.addfinalizer(
            lambda: admin_client.delete_project(
                DeleteProjectRequest(project_name=created.name)
            )
        )

        proj = admin_client.get_project(created.name)
        assert proj.project.enabled is True, "New project should be enabled by default"

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize("admin_username", ["admin1"])
    def test_project_disable_and_enable(
        self,
        request: pytest.FixtureRequest,
        res_environment: ResEnvironment,
        admin: ClientAuth,
        admin_username: str,
    ) -> None:
        """Disable a project, verify status, re-enable, verify status."""
        api_invoker_type = request.config.getoption("--api-invoker-type")
        admin_client = ResClient(res_environment, admin, api_invoker_type)

        project_name = f"integ-toggle-{_RUN_ID}"
        project = Project(
            title=project_name,
            name=project_name,
            description="Test project enable/disable toggle",
            enable_budgets=False,
        )
        result = admin_client.create_project(
            CreateProjectRequest(project=project, filesystem_names=["home"])
        )
        created = result.project
        assert created is not None

        def _cleanup() -> None:
            # Re-enable before delete (disabled projects may block deletion).
            try:
                admin_client.enable_project(created.name)
            except Exception:
                pass
            admin_client.delete_project(DeleteProjectRequest(project_name=created.name))

        request.addfinalizer(_cleanup)

        logger.info(f"Disabling project {created.name}...")
        admin_client.disable_project(created.name)

        def _check_disabled() -> None:
            proj = admin_client.get_project(created.name)
            assert proj.project.enabled is False, "Project should be disabled"

        retry_with_backoff(
            func=_check_disabled,
            max_retries=DEFAULT_MAX_RETRIES,
            initial_delay=DEFAULT_INITIAL_DELAY,
            backoff_factor=DEFAULT_BACKOFF_FACTOR,
            max_delay=DEFAULT_MAX_DELAY,
            exceptions=(AssertionError,),
        )

        logger.info(f"Re-enabling project {created.name}...")
        admin_client.enable_project(created.name)

        def _check_enabled() -> None:
            proj = admin_client.get_project(created.name)
            assert proj.project.enabled is True, "Project should be re-enabled"

        retry_with_backoff(
            func=_check_enabled,
            max_retries=DEFAULT_MAX_RETRIES,
            initial_delay=DEFAULT_INITIAL_DELAY,
            backoff_factor=DEFAULT_BACKOFF_FACTOR,
            max_delay=DEFAULT_MAX_DELAY,
            exceptions=(AssertionError,),
        )

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize("admin_username", ["admin1"])
    def test_project_delete(
        self,
        request: pytest.FixtureRequest,
        res_environment: ResEnvironment,
        admin: ClientAuth,
        admin_username: str,
    ) -> None:
        """Create and delete a project — verify it's gone."""
        api_invoker_type = request.config.getoption("--api-invoker-type")
        admin_client = ResClient(res_environment, admin, api_invoker_type)

        project_name = f"integ-del-{_RUN_ID}"
        project = Project(
            title=project_name,
            name=project_name,
            description="Test project deletion",
            enable_budgets=False,
        )
        result = admin_client.create_project(
            CreateProjectRequest(project=project, filesystem_names=["home"])
        )
        created = result.project
        assert created is not None

        admin_client.delete_project(DeleteProjectRequest(project_name=created.name))

        admin_client.get_project(
            created.name, should_succeed=False, expected_error_code="PROJECT_NOT_FOUND"
        )


@pytest.mark.dev
@pytest.mark.usefixtures("res_environment")
@pytest.mark.usefixtures("region")
class TestRoleAssignments:
    """Role-assignment CRUD for users and groups."""

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize("admin_username", ["admin1"])
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_user_role_assignment_add_list_remove(
        self,
        request: pytest.FixtureRequest,
        res_environment: ResEnvironment,
        admin: ClientAuth,
        admin_username: str,
        non_admin: ClientAuth,
        non_admin_username: str,
    ) -> None:
        """Add user to project, verify in list, remove, verify gone."""
        api_invoker_type = request.config.getoption("--api-invoker-type")
        admin_client = ResClient(res_environment, admin, api_invoker_type)

        project_name = f"integ-ura-{_RUN_ID}"
        result = admin_client.create_project(
            CreateProjectRequest(
                project=Project(
                    title=project_name,
                    name=project_name,
                    description="Role assignment user test",
                    enable_budgets=False,
                ),
                filesystem_names=["home"],
            )
        )
        created = result.project

        def _cleanup() -> None:
            try:
                admin_client.batch_delete_role_assignment(
                    BatchDeleteRoleAssignmentRequest(
                        items=[
                            DeleteRoleAssignmentRequest(
                                resource_id=created.project_id,
                                resource_type=PROJECT_ROLE_ASSIGNMENT_TYPE,
                                actor_id=non_admin_username,
                                actor_type=ROLE_ASSIGNMENT_ACTOR_USER_TYPE,
                                request_id="cleanup",
                            )
                        ]
                    )
                )
            except Exception:
                pass
            admin_client.delete_project(DeleteProjectRequest(project_name=created.name))

        request.addfinalizer(_cleanup)

        admin_client.batch_put_role_assignment(
            BatchPutRoleAssignmentRequest(
                items=[
                    PutRoleAssignmentRequest(
                        resource_id=created.project_id,
                        resource_type=PROJECT_ROLE_ASSIGNMENT_TYPE,
                        actor_id=non_admin_username,
                        actor_type=ROLE_ASSIGNMENT_ACTOR_USER_TYPE,
                        role_id=PROJECT_MEMBER_ROLE_ID,
                        request_id="test-add",
                    )
                ]
            )
        )

        assignments = admin_client.list_role_assignments(
            ListRoleAssignmentsRequest(
                resource_key=f"{created.project_id}:{PROJECT_ROLE_ASSIGNMENT_TYPE}"
            )
        )
        actor_ids = [item.actor_key for item in (assignments.items or [])]
        expected = f"{non_admin_username}:{ROLE_ASSIGNMENT_ACTOR_USER_TYPE}"
        assert expected in actor_ids, f"Expected {expected} in {actor_ids}"

        admin_client.batch_delete_role_assignment(
            BatchDeleteRoleAssignmentRequest(
                items=[
                    DeleteRoleAssignmentRequest(
                        resource_id=created.project_id,
                        resource_type=PROJECT_ROLE_ASSIGNMENT_TYPE,
                        actor_id=non_admin_username,
                        actor_type=ROLE_ASSIGNMENT_ACTOR_USER_TYPE,
                        request_id="test-remove",
                    )
                ]
            )
        )

        assignments = admin_client.list_role_assignments(
            ListRoleAssignmentsRequest(
                resource_key=f"{created.project_id}:{PROJECT_ROLE_ASSIGNMENT_TYPE}"
            )
        )
        actor_ids = [item.actor_key for item in (assignments.items or [])]
        assert expected not in actor_ids, f"User should be removed: {actor_ids}"

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize("admin_username", ["admin1"])
    def test_group_role_assignment_add_and_remove(
        self,
        request: pytest.FixtureRequest,
        res_environment: ResEnvironment,
        admin: ClientAuth,
        admin_username: str,
    ) -> None:
        """Add group to project, verify in list, remove, verify gone."""
        api_invoker_type = request.config.getoption("--api-invoker-type")
        admin_client = ResClient(res_environment, admin, api_invoker_type)

        project_name = f"integ-gra-{_RUN_ID}"
        result = admin_client.create_project(
            CreateProjectRequest(
                project=Project(
                    title=project_name,
                    name=project_name,
                    description="Role assignment group test",
                    enable_budgets=False,
                ),
                filesystem_names=["home"],
            )
        )
        created = result.project
        group_name = "group_1"

        def _cleanup() -> None:
            try:
                admin_client.batch_delete_role_assignment(
                    BatchDeleteRoleAssignmentRequest(
                        items=[
                            DeleteRoleAssignmentRequest(
                                resource_id=created.project_id,
                                resource_type=PROJECT_ROLE_ASSIGNMENT_TYPE,
                                actor_id=group_name,
                                actor_type=ROLE_ASSIGNMENT_ACTOR_GROUP_TYPE,
                                request_id="cleanup",
                            )
                        ]
                    )
                )
            except Exception:
                pass
            admin_client.delete_project(DeleteProjectRequest(project_name=created.name))

        request.addfinalizer(_cleanup)

        admin_client.batch_put_role_assignment(
            BatchPutRoleAssignmentRequest(
                items=[
                    PutRoleAssignmentRequest(
                        resource_id=created.project_id,
                        resource_type=PROJECT_ROLE_ASSIGNMENT_TYPE,
                        actor_id=group_name,
                        actor_type=ROLE_ASSIGNMENT_ACTOR_GROUP_TYPE,
                        role_id=PROJECT_MEMBER_ROLE_ID,
                        request_id="test-add-group",
                    )
                ]
            )
        )

        assignments = admin_client.list_role_assignments(
            ListRoleAssignmentsRequest(
                resource_key=f"{created.project_id}:{PROJECT_ROLE_ASSIGNMENT_TYPE}"
            )
        )
        actor_ids = [item.actor_key for item in (assignments.items or [])]
        expected = f"{group_name}:{ROLE_ASSIGNMENT_ACTOR_GROUP_TYPE}"
        assert expected in actor_ids, f"Expected {expected} in {actor_ids}"

        admin_client.batch_delete_role_assignment(
            BatchDeleteRoleAssignmentRequest(
                items=[
                    DeleteRoleAssignmentRequest(
                        resource_id=created.project_id,
                        resource_type=PROJECT_ROLE_ASSIGNMENT_TYPE,
                        actor_id=group_name,
                        actor_type=ROLE_ASSIGNMENT_ACTOR_GROUP_TYPE,
                        request_id="test-remove-group",
                    )
                ]
            )
        )

        assignments = admin_client.list_role_assignments(
            ListRoleAssignmentsRequest(
                resource_key=f"{created.project_id}:{PROJECT_ROLE_ASSIGNMENT_TYPE}"
            )
        )
        actor_ids = [item.actor_key for item in (assignments.items or [])]
        assert expected not in actor_ids, f"Group should be removed: {actor_ids}"
