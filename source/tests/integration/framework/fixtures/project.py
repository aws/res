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
    PROJECT_ROLE_ASSIGNMENT_TYPE,
    ROLE_ASSIGNMENT_ACTOR_GROUP_TYPE,
    ROLE_ASSIGNMENT_ACTOR_USER_TYPE,
)
from tests.integration.framework.client.res_client import ResClient
from tests.integration.framework.fixtures.fixture_request import FixtureRequest
from tests.integration.framework.fixtures.res_environment import ResEnvironment


@pytest.fixture
def project(request: FixtureRequest, res_environment: ResEnvironment) -> Project:
    """
    Fixture for setting up/tearing down the test project
    """
    project = request.param[0]
    filesystem_names = request.param[1]
    groups = request.param[2]
    users = request.param[3]
    admin = request.getfixturevalue(request.param[4])
    role_id = request.param[5] if len(request.param) > 5 else PROJECT_MEMBER_ROLE_ID
    create_project_request = CreateProjectRequest(
        project=project, filesystem_names=filesystem_names
    )

    api_invoker_type = request.config.getoption("--api-invoker-type")
    client = ResClient(res_environment, admin, api_invoker_type)
    project = client.create_project(create_project_request).project

    items = [
        PutRoleAssignmentRequest(
            resource_id=project.project_id,
            resource_type=PROJECT_ROLE_ASSIGNMENT_TYPE,
            actor_id=group,
            actor_type=ROLE_ASSIGNMENT_ACTOR_GROUP_TYPE,
            role_id=role_id,
            request_id="test",
        )
        for group in groups
    ]
    for user in users:
        items.append(
            PutRoleAssignmentRequest(
                resource_id=project.project_id,
                resource_type=PROJECT_ROLE_ASSIGNMENT_TYPE,
                actor_id=user,
                actor_type=ROLE_ASSIGNMENT_ACTOR_USER_TYPE,
                role_id=role_id,
                request_id="test",
            )
        )
    client.batch_put_role_assignment(BatchPutRoleAssignmentRequest(items=items))

    def tear_down() -> None:
        items = [
            DeleteRoleAssignmentRequest(
                resource_id=project.project_id,
                resource_type=PROJECT_ROLE_ASSIGNMENT_TYPE,
                actor_id=group,
                actor_type=ROLE_ASSIGNMENT_ACTOR_GROUP_TYPE,
                request_id="test",
            )
            for group in groups
        ]
        for user in users:
            items.append(
                DeleteRoleAssignmentRequest(
                    resource_id=project.project_id,
                    resource_type=PROJECT_ROLE_ASSIGNMENT_TYPE,
                    actor_id=user,
                    actor_type=ROLE_ASSIGNMENT_ACTOR_USER_TYPE,
                    request_id="test",
                )
            )

        client.batch_delete_role_assignment(
            BatchDeleteRoleAssignmentRequest(items=items)
        )

        delete_project_request = DeleteProjectRequest(project_name=project.name)
        client.delete_project(delete_project_request)

    request.addfinalizer(tear_down)

    return project
