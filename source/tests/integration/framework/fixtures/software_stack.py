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


@pytest.fixture
def software_stack(
    request: FixtureRequest,
    res_environment: ResEnvironment,
    admin: ClientAuth,
) -> VirtualDesktopSoftwareStack:
    """
    Fixture for setting up/tearing down the test software stack
    """
    software_stack = request.param[0]
    project = request.getfixturevalue(request.param[1])
    software_stack.projects = [project]

    client = ResClient(request, res_environment, admin)

    if not software_stack.ami_id:
        base_os = software_stack.base_os
        architecture = software_stack.architecture
        gpu = software_stack.gpu
        assert (
            base_os and architecture and gpu
        ), f"Either provide an AMI ID or (base OS + architecture + GPU) of the software stack"

        list_software_stacks_request = ListSoftwareStackRequest(
            filters=[
                SocaFilter(
                    key="base_os",
                    eq=base_os,
                ),
                SocaFilter(
                    key="architecture",
                    eq=architecture,
                ),
                SocaFilter(
                    key="gpu",
                    eq=gpu,
                ),
            ]
        )
        list_software_stacks_response = client.list_software_stacks(
            list_software_stacks_request
        )
        existing_software_stacks = (
            list_software_stacks_response.listing
            if list_software_stacks_response.listing
            else []
        )
        assert (
            len(existing_software_stacks) > 0
        ), f"Failed to find existing software stacks with base OS {base_os}, architecture {architecture} and GPU {gpu}"
        # If no AMI ID is provided, use the AMI ID of an existing software stack that has the same base OS, architecture and GPU.
        software_stack.ami_id = existing_software_stacks[0].ami_id

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
