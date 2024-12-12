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
from typing import Optional

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
    force_idle_session,
    wait_for_stopped_idle_session,
)
from tests.integration.tests.config import TEST_SOFTWARE_STACKS

VDC_SOFTWARE_STACKS = [
    TEST_SOFTWARE_STACKS[0],  # AL2
    TEST_SOFTWARE_STACKS[4],  # Windows
]

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("res_environment")
@pytest.mark.usefixtures("region")
class TestsVDC(object):
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
                    title="res-vdc-integ-test"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="res-vdc-integ-test"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES vdc integ test project",
                    enable_budgets=False,
                ),
                [],
                ["RESAdministrators", "group_1", "group_2"],
            )
        ],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "software_stack",
        [
            (
                software_stack,
                "project",
            )
            for software_stack in VDC_SOFTWARE_STACKS
        ],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "session",
        [
            (
                VirtualDesktopSession(
                    name="VirtualDesktop-vdc-integ-"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES vdc integ test VDI session",
                    hibernation_enabled=False,
                ),
                "project",
                "software_stack",
            )
        ],
        indirect=True,
    )
    def test_vdi_auto_stop(
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
        session: Optional[VirtualDesktopSession],
    ) -> None:
        """
        Deterministic end to end test for VDI Auto Stop feature:
        1. Create a project, software stack and virtual desktop session.
        2. Set the session to idle.
        3. Wait for the session to be stopped.
        3. Clean up the test project, software stack and virtual desktop session.
        """
        if not session:
            # VDI is not supported with the current configuration
            return

        logger.info(f"Starting stop idle integ test for {session.name}...")
        api_invoker_type = request.config.getoption("--api-invoker-type")
        client = ResClient(res_environment, non_admin, api_invoker_type)
        force_idle_session(region, session, res_environment._environment_name)
        wait_for_stopped_idle_session(client, session)
