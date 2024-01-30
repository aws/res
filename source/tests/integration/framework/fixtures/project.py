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
    CreateProjectRequest,
    DeleteProjectRequest,
    Project,
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
    create_project_request = CreateProjectRequest(
        project=project, filesystem_names=filesystem_names
    )

    client = ResClient(request, res_environment, admin)
    project = client.create_project(create_project_request).project

    def tear_down() -> None:
        delete_project_request = DeleteProjectRequest(project_name=project.name)
        client.delete_project(delete_project_request)

    request.addfinalizer(tear_down)

    return project
