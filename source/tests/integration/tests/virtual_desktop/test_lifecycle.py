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
from typing import Any, Optional

import pytest

# The project fixture still returns a legacy (pydantic) Project — its create path
# goes through the not-yet-migrated cluster-manager API, so it stays ideadatamodel.
from ideadatamodel import Project  # type: ignore
from tests.integration.framework.client.api_client import (
    ApiClient,
    BatchRebootSessionRequestContent,
    BatchStartSessionRequestContent,
    BatchStopSessionRequestContent,
)
from tests.integration.framework.fixtures.project import project
from tests.integration.framework.fixtures.res_environment import (
    ResEnvironment,
    res_environment,
)
from tests.integration.framework.fixtures.session import session
from tests.integration.framework.fixtures.software_stack import software_stack
from tests.integration.framework.fixtures.users.admin import admin
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.model_utils import get_backend_model_class
from tests.integration.framework.utils.session_utils import wait_for_session_state
from tests.integration.tests.smoke.config import AL2023_SOFTWARE_STACK

logger = logging.getLogger(__name__)

# Backend data-model classes (source/idea/data-model). The session APIs consume
# and return these.
VirtualDesktopSession = get_backend_model_class(
    "virtual_desktop_session", "VirtualDesktopSession"
)
VirtualDesktopSessionState = get_backend_model_class(
    "virtual_desktop_session_state", "VirtualDesktopSessionState"
)


def _batch_session(session: Any) -> Any:
    """Minimal backend-model session reference for a batch operation."""
    return VirtualDesktopSession(
        idea_session_id=session.idea_session_id,
        owner=session.owner,
        name=session.name,
        hibernation_enabled=False,
    )


def _assert_batch_succeeded(response: Any, action: str) -> None:
    assert response is not None, f"{action}: response should not be None"
    assert (
        len(response.successful_list) == 1
    ), f"{action}: expected the session in successful_list, got {response}"
    assert (
        len(response.unsuccessful_list) == 0
    ), f"{action}: session in unsuccessful_list: {response.unsuccessful_list}"


@pytest.mark.nightly
@pytest.mark.requires_vdi
@pytest.mark.usefixtures("res_environment")
@pytest.mark.usefixtures("region")
class TestVdiLifecycle:
    """
    VDI lifecycle coverage (doc: "VDI Lifecycle").

    A single VDI is walked through the full lifecycle on one launch — launching a
    VDI is the expensive step, so create/stop/start/reboot are exercised
    sequentially on the same instance rather than relaunching per transition.
    """

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize("admin_username", ["admin1"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="res-vdi-lifecycle"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="res-vdi-lifecycle"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES VDI lifecycle test project",
                    enable_budgets=False,
                ),
                ["home"],
                ["RESAdministrators", "group_1", "group_2"],
                [],
                "admin",
            )
        ],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "software_stack",
        [(AL2023_SOFTWARE_STACK, "project", "admin")],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "session",
        [
            (
                VirtualDesktopSession(
                    name="life",
                    description="RES VDI lifecycle test session",
                    hibernation_enabled=False,
                ),
                "project",
                "software_stack",
                "admin",
            )
        ],
        indirect=True,
    )
    def test_stop_start_reboot_cycle(
        self,
        res_environment: ResEnvironment,
        admin: ClientAuth,
        admin_username: str,
        # project and software_stack are not read directly, but must be declared
        # so their indirect parametrization binds — the session fixture resolves
        # them at runtime via getfixturevalue.
        project: Project,
        software_stack: Any,
        session: Optional[Any],
    ) -> None:
        """
        Walk a single VDI through its lifecycle on one launch:
        1. Create — the session fixture launches the VDI and waits for READY.
        2. Stop  — batch stop, VDI reaches STOPPED.
        3. Start — batch start, VDI returns to READY.
        4. Reboot — batch reboot, VDI returns to READY on the same instance.
        """
        if not session:
            pytest.skip("Session fixture returned None — VDI launch may have failed")

        api_client = ApiClient(res_environment, admin)

        # The fixture already waited for READY; re-assert so a failed launch is
        # attributed to this test, not to fixture setup.
        assert (
            session.state == VirtualDesktopSessionState.READY
        ), f"VDI did not launch to READY: {session.state} ({session.failure_reason})"

        logger.info(f"Stopping VDI {session.name}...")
        stop_response = api_client.batch_stop_session(
            BatchStopSessionRequestContent(sessions=[_batch_session(session)])
        )
        _assert_batch_succeeded(stop_response, "stop")
        session = wait_for_session_state(
            api_client, session, VirtualDesktopSessionState.STOPPED
        )

        logger.info(f"Starting VDI {session.name}...")
        start_response = api_client.batch_start_session(
            BatchStartSessionRequestContent(sessions=[_batch_session(session)])
        )
        _assert_batch_succeeded(start_response, "start")
        session = wait_for_session_state(
            api_client, session, VirtualDesktopSessionState.READY
        )

        instance_id_before = session.server.instance_id
        logger.info(f"Rebooting VDI {session.name} ({instance_id_before})...")
        reboot_response = api_client.batch_reboot_session(
            BatchRebootSessionRequestContent(sessions=[_batch_session(session)])
        )
        _assert_batch_succeeded(reboot_response, "reboot")
        # The reboot handler sets the session to RESUMING before returning, so
        # wait for RESUMING first (confirms the reboot was processed) and then for
        # the return to READY. Waiting only for READY could match the pre-reboot
        # state and pass without the reboot happening.
        session = wait_for_session_state(
            api_client, session, VirtualDesktopSessionState.RESUMING
        )
        session = wait_for_session_state(
            api_client, session, VirtualDesktopSessionState.READY
        )
        # A reboot restarts the guest in place; the instance must not be replaced.
        assert session.server.instance_id == instance_id_before, (
            f"Reboot replaced the instance: {instance_id_before} -> "
            f"{session.server.instance_id}"
        )
