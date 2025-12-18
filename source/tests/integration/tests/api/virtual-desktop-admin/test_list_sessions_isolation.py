# #  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# #
# #  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# #  with the License. A copy of the License is located at
# #
# #      http://www.apache.org/licenses/LICENSE-2.0
# #
# #  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# #  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# #  and limitations under the License.

import logging

import pytest

from ideadatamodel import (  # type: ignore
    CreateSessionRequest,
    CreateSoftwareStackRequest,
    ListSessionsRequest,
    Project,
    SocaMemory,
    SocaMemoryUnit,
    VirtualDesktopArchitecture,
    VirtualDesktopBaseOS,
    VirtualDesktopGPU,
    VirtualDesktopServer,
    VirtualDesktopSession,
    VirtualDesktopSoftwareStack,
)
from tests.integration.framework.client.res_client import ResClient
from tests.integration.framework.fixtures.fixture_request import FixtureRequest
from tests.integration.framework.fixtures.project import project
from tests.integration.framework.fixtures.res_environment import (
    ResEnvironment,
    res_environment,
)
from tests.integration.framework.fixtures.users import admin
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.ec2_utils import get_latest_x86_amzn2023_ami_id

logger = logging.getLogger(__name__)


class TestSessionIsolation:

    @pytest.mark.skip(
        reason="Temporarily disabled requires test user registration framework"
    )
    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="res-string-verification",
                    name="res-string-verification",
                    description="RES integ test for verifying username session security",
                    enable_budgets=False,
                ),
                ["home"],
                ["RESAdministrators", "group_1", "group_2"],
                ["user1", "user2"],
                "admin",
            )
        ],
        indirect=True,
    )
    def test_substring_vulnerability(
        self,
        request: FixtureRequest,
        res_environment: ResEnvironment,
        region: str,
        admin: ClientAuth,
        project: Project,
    ) -> None:

        api_invoker_type = request.config.getoption("--api-invoker-type")
        clusteradmin_client = ResClient(
            res_environment, ClientAuth(username="clusteradmin"), api_invoker_type
        )

        ami_id = get_latest_x86_amzn2023_ami_id(region)

        software_stack = VirtualDesktopSoftwareStack(
            name="Software-Stack-res-string-verification",
            description="Software-Stack for res string verification",
            base_os=VirtualDesktopBaseOS.AMAZON_LINUX2023,
            architecture=VirtualDesktopArchitecture.X86_64,
            gpu=VirtualDesktopGPU.NO_GPU,
            min_storage=SocaMemory(value=50, unit=SocaMemoryUnit.GB),
            min_ram=SocaMemory(value=4, unit=SocaMemoryUnit.GB),
            allowed_instance_types=["t3.medium", "t3.large"],
            projects=[project],
            ami_id=ami_id,
        )

        response_stack = clusteradmin_client.create_software_stack(
            CreateSoftwareStackRequest(software_stack=software_stack)
        )

        admin1_username = "admin1"
        test_username = "admi"

        test_user_client = ResClient(
            res_environment, ClientAuth(username=test_username), api_invoker_type
        )
        admin1_client = ResClient(
            res_environment, ClientAuth(username=admin1_username), api_invoker_type
        )

        admin1_client.create_session(
            CreateSessionRequest(
                session=VirtualDesktopSession(
                    name="VirtualDesktop-res-string-verification",
                    description="RES username string verification session",
                    hibernation_enabled=False,
                    owner=admin1_username,
                    project=project,
                    software_stack=response_stack.software_stack,
                    base_os=VirtualDesktopBaseOS.AMAZON_LINUX2023,
                    server=VirtualDesktopServer(
                        instance_type="t3.medium",
                        root_volume_size=SocaMemory(value=50, unit=SocaMemoryUnit.GB),
                    ),
                )
            )
        )

        admin1_sessions = admin1_client.list_sessions(ListSessionsRequest())
        test_user_sessions = test_user_client.list_sessions(ListSessionsRequest())

        assert len(admin1_sessions.listing) > 0, "No sessions found for admin1"

        for session in test_user_sessions.listing:
            if session.owner == admin1_username:
                pytest.fail(
                    f"VULNERABILITY: User 'admi' can see '{admin1_username}' session: {session.name}"
                )
