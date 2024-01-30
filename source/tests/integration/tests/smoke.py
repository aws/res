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

import pytest

from ideadatamodel import (  # type: ignore
    CreateSessionRequest,
    DeleteSessionRequest,
    Project,
    SocaMemory,
    SocaMemoryUnit,
    UpdateSessionRequest,
    VirtualDesktopArchitecture,
    VirtualDesktopBaseOS,
    VirtualDesktopGPU,
    VirtualDesktopSchedule,
    VirtualDesktopScheduleType,
    VirtualDesktopServer,
    VirtualDesktopSession,
    VirtualDesktopSoftwareStack,
    VirtualDesktopWeekSchedule,
)
from tests.integration.framework.client.res_client import ResClient
from tests.integration.framework.fixtures.fixture_request import FixtureRequest
from tests.integration.framework.fixtures.project import project
from tests.integration.framework.fixtures.res_environment import (
    ResEnvironment,
    res_environment,
)
from tests.integration.framework.fixtures.session import session
from tests.integration.framework.fixtures.software_stack import software_stack
from tests.integration.framework.fixtures.users.admin import admin
from tests.integration.framework.fixtures.users.non_admin import non_admin
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.session_utils import (
    wait_for_session_connection_count,
)

logger = logging.getLogger(__name__)
MIN_STORAGE = SocaMemory(value=10, unit=SocaMemoryUnit.GB)
MIN_RAM = SocaMemory(value=4, unit=SocaMemoryUnit.GB)


@pytest.mark.usefixtures("res_environment")
@pytest.mark.usefixtures("region")
class TestsSmoke(object):
    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize(
        "admin_username",
        [
            "admin1",
        ],
    )
    @pytest.mark.usefixtures("non_admin")
    @pytest.mark.parametrize(
        "non_admin_username",
        [
            "user1",
        ],
    )
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="res-integ-test",
                    name="res-integ-test",
                    description="RES integ test project",
                    enable_budgets=False,
                    ldap_groups=["RESAdministrators", "group_1", "group_2"],
                ),
                [],
            )
        ],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "software_stack",
        [
            (
                VirtualDesktopSoftwareStack(
                    name="res-integ-test-stack",
                    description="RES integ test software stack",
                    base_os=VirtualDesktopBaseOS.AMAZON_LINUX2,
                    architecture=VirtualDesktopArchitecture.X86_64,
                    min_storage=MIN_STORAGE,
                    min_ram=MIN_RAM,
                    gpu=VirtualDesktopGPU.NO_GPU,
                ),
                "project",
            )
        ],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "session",
        [
            (
                VirtualDesktopSession(
                    base_os=VirtualDesktopBaseOS.AMAZON_LINUX2,
                    name="VirtualDesktop1",
                    server=VirtualDesktopServer(
                        instance_type="t3.medium", root_volume_size=MIN_STORAGE
                    ),
                    description="VirtualDesktop1",
                    hibernation_enabled=False,
                ),
                "project",
                "software_stack",
            )
        ],
        indirect=True,
    )
    def test_end_to_end_succeed(
        self,
        request: FixtureRequest,
        region: str,
        admin: ClientAuth,
        admin_username: str,
        non_admin: ClientAuth,
        non_admin_username: str,
        res_environment: ResEnvironment,
        project: Project,
        software_stack: VirtualDesktopSoftwareStack,
        session: VirtualDesktopSession,
    ) -> None:
        """
        Test the end to end workflow:
        1. Create a project, software stack and virtual desktop session.
        2. Join the virtual desktop session from a headless web browser and close it.
        3. Clean up the test project, software stack and virtual desktop session.
        """
        client = ResClient(request, res_environment, non_admin)
        web_driver = client.join_session(session)
        wait_for_session_connection_count(region, session, 1)

        logger.info(f"leaving session {session.dcv_session_id}...")
        web_driver.quit()
        wait_for_session_connection_count(region, session, 0)
