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

import logging
import os
import uuid
from typing import Any

import pytest
import yaml

from tests.integration.framework.client.api_client import (
    ApiClient,
    CreateSoftwareStackRequestContent,
    DeleteSoftwareStackRequestContent,
)
from tests.integration.framework.client.res_client import ResClient
from tests.integration.framework.fixtures.fixture_request import FixtureRequest
from tests.integration.framework.fixtures.res_environment import ResEnvironment
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.tests.smoke.config import TEST_SOFTWARE_STACKS_GOVCLOUD

logger = logging.getLogger(__name__)


@pytest.fixture
def software_stack(
    request: FixtureRequest,
    res_environment: ResEnvironment,
) -> Any:
    """
    Fixture for setting up/tearing down the test software stack
    """
    software_stack = request.param[0]
    project = request.getfixturevalue(request.param[1])
    admin = request.getfixturevalue(request.param[2])

    # Optional 4th element: fixture name whose value overrides ami_id.
    if len(request.param) > 3 and request.param[3]:
        software_stack.ami_id = request.getfixturevalue(request.param[3])
    # The project fixture still returns a legacy (pydantic) Project, which the new
    # OpenAPI-generated stack cannot serialize inside projects. Attach it by its
    # id so software_stack.to_dict() -> JSON stays encodable.
    software_stack.projects = [{"project_id": project.project_id}]

    api_client = ApiClient(res_environment, admin)
    api_invoker_type = request.config.getoption("--api-invoker-type")
    res_client = ResClient(res_environment, admin, api_invoker_type)

    if (
        res_environment.region == "us-gov-west-1"
        or res_environment.region == "us-gov-east-1"
    ) and (software_stack.name not in TEST_SOFTWARE_STACKS_GOVCLOUD):
        pytest.skip(f"Software stack: {software_stack.name} not supported in GovCloud")

    # Add unique short ID to stack name to avoid collisions in parallel test runs
    unique_id = str(uuid.uuid4())[:4]
    software_stack.name = f"{software_stack.name}-{unique_id}"

    # If no AMI ID is provided, find AMI ID from VDI AMI config file
    if not software_stack.ami_id:
        software_stack.ami_id = get_ami_id(
            res_client, software_stack, res_environment.region
        )

    payload = {"software_stack": software_stack.to_dict()}
    request_content = CreateSoftwareStackRequestContent(**payload)
    response = api_client.create_software_stack(request_content)

    def tear_down() -> None:
        delete_request = DeleteSoftwareStackRequestContent(
            base_os=response.software_stack.base_os  # type: ignore
        )
        api_client.delete_software_stack(
            response.software_stack.stack_id, delete_request  # type: ignore
        )

    request.addfinalizer(tear_down)

    # The response already deserializes into the new-model VirtualDesktopSoftwareStack.
    return response.software_stack  # type: ignore


def get_ami_id(client: ResClient, software_stack: Any, region: str) -> str:
    """
    Retrieve AMI ID from base-software-stack-config.yaml

    Prefers an exact gpu-manufacturer AMI match when present. Falls back to the
    first (base) AMI otherwise.
    """
    base_os = software_stack.base_os
    architecture = "x86-64" if software_stack.architecture == "x86_64" else "arm64"
    gpu = software_stack.gpu

    source_dir_path = os.path.join(os.path.dirname(__file__), "../../../../")
    ami_config_path = os.path.join(
        source_dir_path,
        "idea/infrastructure/resources/config/base-software-stack-config.yaml",
    )

    with open(ami_config_path, "r") as f:
        config = yaml.safe_load(f)
    try:
        ami_list = config.get(base_os, {}).get(architecture, {}).get(region, [])
        for ami_data in ami_list:
            if ami_data.get("gpu-manufacturer", "NO_GPU") == gpu:
                return str(ami_data["ami-id"])
        if ami_list:
            return str(ami_list[0]["ami-id"])
    except (KeyError, IndexError):
        raise ValueError(f"AMI IDs not found for {base_os}/{architecture} in {region}")
    pytest.skip(
        f"AMI ID not found for {base_os}/{architecture}/{gpu} in {region}, skipping."
    )
