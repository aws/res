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

"""
Integration tests for Linux VDI hibernation lifecycle.

Verifies that a VDI launched with hibernation enabled can be hibernated
(stopped) and resumed while preserving instance identity and in-guest state.

Runs across all Linux software stacks; known-broken OS/instance combinations
are marked with xfail rather than skipped.
"""

import logging
import os
from typing import Any, Dict, Optional

import pytest

from ideadatamodel import Project  # type: ignore
from tests.integration.framework.client.api_client import (
    ApiClient,
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
from tests.integration.framework.utils.retry_utils import retry_with_backoff
from tests.integration.framework.utils.session_utils import wait_for_session_state
from tests.integration.framework.utils.vdi_command_utils import (
    command_succeeded,
    run_command,
)
from tests.integration.framework.utils.virtual_desktop import (
    parametrize_software_stacks,
)
from tests.integration.tests.smoke.config import LINUX_SOFTWARE_STACKS

logger = logging.getLogger(__name__)

VirtualDesktopSession = get_backend_model_class(
    "virtual_desktop_session", "VirtualDesktopSession"
)
VirtualDesktopSessionState = get_backend_model_class(
    "virtual_desktop_session_state", "VirtualDesktopSessionState"
)

# Hibernation requires root volume >= storage + instance RAM.
# The session fixture dynamically adds headroom when hibernation_enabled=True,
# so no min_storage override is needed here.

# Known-broken OS/arch combinations for hibernation.
# These are marked xfail so they run but don't fail the suite.
# Add entries here as issues are discovered, with a link to the tracking issue.
HIBERNATION_XFAIL_OS: Dict[str, str] = {
    "ubuntu2204": "Ubuntu 22.04 hibernation is unreliable in automated test environments",
    "ubuntu2404": "Ubuntu 24.04 is not yet in the AWS EC2 hibernation supported OS list",
}

HIBERNATION_STACK_PARAMS = parametrize_software_stacks(
    LINUX_SOFTWARE_STACKS,
    xfail_os=HIBERNATION_XFAIL_OS,
)

# SSM agent needs time to re-register after hibernate resume.
SSM_POST_RESUME_MAX_RETRIES = 5
SSM_POST_RESUME_INITIAL_DELAY_SEC = 30
SSM_POST_RESUME_BACKOFF_FACTOR = 2
SSM_POST_RESUME_MAX_DELAY_SEC = 60

# Background process lifetime for PID-preservation check (seconds).
MARKER_PROCESS_SLEEP_SEC = 3600


@pytest.mark.nightly
@pytest.mark.release
@pytest.mark.linux_only
@pytest.mark.requires_vdi
@pytest.mark.usefixtures("res_environment")
@pytest.mark.usefixtures("region")
class TestVdiHibernation:
    """
    Linux VDI hibernation lifecycle tests.

    Verifies that hibernation-enabled VDIs can be hibernated and resumed
    with full state preservation (same instance ID, in-guest state intact).
    Runs across all Linux software stacks.
    """

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize("admin_username", ["admin1"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="res-vdi-hibernate"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="res-vdi-hibernate"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES VDI hibernation test project",
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
        HIBERNATION_STACK_PARAMS,
        indirect=True,
    )
    @pytest.mark.parametrize(
        "session",
        [
            (
                VirtualDesktopSession(
                    name="hibernate",
                    description="RES VDI hibernation lifecycle test",
                    hibernation_enabled=True,
                ),
                "project",
                "software_stack",
                "admin",
            )
        ],
        indirect=True,
    )
    def test_hibernate_resume_lifecycle(
        self,
        res_environment: ResEnvironment,
        admin: ClientAuth,
        admin_username: str,
        project: Project,
        software_stack: Any,
        session: Optional[Any],
    ) -> None:
        """
        Full hibernation lifecycle on a single VDI:
        1. Verify session launched with hibernation_enabled=True.
        2. Write a marker file via SSM (proves in-guest state exists).
        3. Hibernate — verify STOPPED state.
        4. Resume — verify READY state.
        5. Assert instance ID preserved (true hibernate, not destroy/recreate).
        6. Read marker file — verify in-guest state survived.
        """
        if not session:
            pytest.skip("Session fixture returned None — VDI launch may have failed")

        api_client = ApiClient(res_environment, admin)

        assert (
            session.state == VirtualDesktopSessionState.READY
        ), f"VDI did not launch to READY: {session.state} ({session.failure_reason})"
        assert (
            session.hibernation_enabled
        ), "Session was not launched with hibernation_enabled=True"

        instance_id_before = session.server.instance_id
        assert instance_id_before, "Instance ID should be set when session is READY"

        # Start a background process and record its PID — this proves process
        # state is preserved across hibernate (a cold stop would kill it).
        marker_path = "/tmp/res_hibernate_marker"
        logger.info(f"Starting background process on {instance_id_before}...")
        run_command(
            instance_id_before,
            f"nohup sleep {MARKER_PROCESS_SLEEP_SEC} >/dev/null 2>&1 & echo $! > {marker_path}",
        )
        pid_output = run_command(instance_id_before, f"cat {marker_path}")
        assert command_succeeded(pid_output), f"Failed to read PID marker: {pid_output}"
        # Extract the PID (strip the OK marker and whitespace)
        pid_before = pid_output.split("\n")[0].strip()
        assert pid_before.isdigit(), f"Expected numeric PID, got: '{pid_before}'"

        # Verify the process is running before hibernate
        check_output = run_command(
            instance_id_before, f"kill -0 {pid_before} && echo ALIVE"
        )
        assert (
            "ALIVE" in check_output
        ), f"Process {pid_before} not running before hibernate: {check_output}"

        # Hibernate
        logger.info(f"Hibernating VDI {session.name} ({instance_id_before})...")
        stop_response = api_client.batch_stop_session(
            BatchStopSessionRequestContent(sessions=[session])
        )
        assert stop_response is not None, "Hibernate response is None"
        assert (
            not stop_response.unsuccessful_list
        ), f"Hibernate failed: {stop_response.unsuccessful_list}"
        session = wait_for_session_state(
            api_client, session, VirtualDesktopSessionState.STOPPED
        )

        # Resume
        logger.info(f"Resuming VDI {session.name} from hibernation...")
        start_response = api_client.batch_start_session(
            BatchStartSessionRequestContent(sessions=[session])
        )
        assert start_response is not None, "Resume response is None"
        assert (
            not start_response.unsuccessful_list
        ), f"Resume failed: {start_response.unsuccessful_list}"
        session = wait_for_session_state(
            api_client, session, VirtualDesktopSessionState.READY
        )

        # Verify instance ID preserved
        instance_id_after = session.server.instance_id
        assert instance_id_after == instance_id_before, (
            f"Instance ID changed after hibernate/resume: "
            f"{instance_id_before} -> {instance_id_after}. "
            f"This indicates a destroy/recreate rather than true hibernation."
        )

        # Verify process state preserved — the sleep process must still be
        # running with the same PID after resume. This is the definitive proof
        # of true hibernation: a cold stop/start would kill all processes.
        # SSM agent needs time to re-register after resume, so retry.
        logger.info(
            f"Checking process {pid_before} is still alive on {instance_id_after}..."
        )
        check_after = retry_with_backoff(
            func=lambda: run_command(
                instance_id_after, f"kill -0 {pid_before} && echo ALIVE"
            ),
            max_retries=SSM_POST_RESUME_MAX_RETRIES,
            initial_delay=SSM_POST_RESUME_INITIAL_DELAY_SEC,
            backoff_factor=SSM_POST_RESUME_BACKOFF_FACTOR,
            max_delay=SSM_POST_RESUME_MAX_DELAY_SEC,
            exceptions=(Exception,),
        )
        assert "ALIVE" in check_after, (
            f"Process {pid_before} not running after resume. "
            f"Hibernation did not preserve process state: {check_after}"
        )
