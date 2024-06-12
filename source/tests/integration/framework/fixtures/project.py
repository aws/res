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
from tests.integration.framework.client.res_client import ResClient
from tests.integration.framework.fixtures.fixture_request import FixtureRequest
from tests.integration.framework.fixtures.res_environment import ResEnvironment
from tests.integration.framework.model.client_auth import ClientAuth


@pytest.fixture
def project(
    request: FixtureRequest, res_environment: ResEnvironment, admin: ClientAuth
) -> Project:
    """
    Fixture for setting up/tearing down the test project
    """
    project = request.param[0]
    filesystem_names = request.param[1]
    groups = request.param[2]
    create_project_request = CreateProjectRequest(
        project=project, filesystem_names=filesystem_names
    )

    api_invoker_type = request.config.getoption("--api-invoker-type")
    client = ResClient(res_environment, admin, api_invoker_type)
    project = client.create_project(create_project_request).project

    items = [
        PutRoleAssignmentRequest(
            resource_id=project.project_id,
            resource_type="project",
            actor_id=group,
            actor_type="group",
            role_id="project_member",
            request_id="test",
        )
        for group in groups
    ]
    client.batch_put_role_assignment(BatchPutRoleAssignmentRequest(items=items))

    def tear_down() -> None:
        items = [
            DeleteRoleAssignmentRequest(
                resource_id=project.project_id,
                resource_type="project",
                actor_id=group,
                actor_type="group",
                request_id="test",
            )
            for group in groups
        ]
        client.batch_delete_role_assignment(
            BatchDeleteRoleAssignmentRequest(items=items)
        )

        delete_project_request = DeleteProjectRequest(project_name=project.name)
        client.delete_project(delete_project_request)

    request.addfinalizer(tear_down)

    return project
