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

import os

import pytest
import yaml

from ideadatamodel import (  # type: ignore
    CreateSoftwareStackRequest,
    DeleteSoftwareStackRequest,
    ListSoftwareStackRequest,
    Project,
    SocaFilter,
    VirtualDesktopSoftwareStack,
)
from tests.integration.framework.client.res_client import ResClient
from tests.integration.framework.fixtures.fixture_request import FixtureRequest
from tests.integration.framework.fixtures.res_environment import ResEnvironment
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.tests.config import TEST_SOFTWARE_STACKS_GOVCLOUD


@pytest.fixture
def software_stack(
    request: FixtureRequest,
    res_environment: ResEnvironment,
) -> VirtualDesktopSoftwareStack:
    """
    Fixture for setting up/tearing down the test software stack
    """
    software_stack = request.param[0]
    project = request.getfixturevalue(request.param[1])
    admin = request.getfixturevalue(request.param[2])
    software_stack.projects = [project]

    api_invoker_type = request.config.getoption("--api-invoker-type")
    client = ResClient(res_environment, admin, api_invoker_type)

    if (
        res_environment.region == "us-gov-west-1"
        or res_environment.region == "us-gov-east-1"
    ) and (software_stack.name not in TEST_SOFTWARE_STACKS_GOVCLOUD):
        pytest.skip(f"Software stack: {software_stack.name} not supported in GovCloud")

    # If no AMI ID is provided, find AMI ID from VDI AMI config file
    if not software_stack.ami_id:
        software_stack.ami_id = get_ami_id(
            client, software_stack, res_environment.region
        )

    create_software_stack_request = CreateSoftwareStackRequest(
        software_stack=software_stack
    )
    software_stack = client.create_software_stack(
        create_software_stack_request
    ).software_stack

    def tear_down() -> None:
        delete_software_stack_request = DeleteSoftwareStackRequest(
            software_stack=software_stack
        )
        client.delete_software_stack(delete_software_stack_request)

    request.addfinalizer(tear_down)

    return software_stack


def get_ami_id(
    client: ResClient, software_stack: VirtualDesktopSoftwareStack, region: str
) -> str:
    """
    Retrieve AMI ID from base-software-stack-config.yaml
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
    except (KeyError, IndexError):
        raise ValueError(f"AMI IDs not found for {base_os}/{architecture} in {region}")
    pytest.skip(
        f"AMI ID not found for {base_os}/{architecture}/{gpu} in {region}, skipping."
    )
