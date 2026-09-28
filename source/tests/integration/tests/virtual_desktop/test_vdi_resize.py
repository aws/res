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

from ideadatamodel import Project  # type: ignore[import]
from tests.integration.framework.client.api_client import (
    ApiClient,
    BatchStartSessionRequestContent,
    BatchStopSessionRequestContent,
    ListAllowedInstanceTypesForSessionRequestContent,
    UpdateSessionRequestContent,
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

VirtualDesktopSession = get_backend_model_class(
    "virtual_desktop_session", "VirtualDesktopSession"
)
VirtualDesktopSessionState = get_backend_model_class(
    "virtual_desktop_session_state", "VirtualDesktopSessionState"
)


def _get_different_instance_type(
    api_client: ApiClient, session: Any, current_type: str
) -> str:
    """
    Get a different instance type from the allowed list for this session.
    Skips the test if no alternative type is available.
    """
    response = api_client.list_allowed_instance_types_for_session(
        ListAllowedInstanceTypesForSessionRequestContent(session=session)
    )
    allowed = response.listing or []  # type: ignore[attr-defined]

    for instance_type_info in allowed:
        candidate = instance_type_info.get("InstanceType", "")
        if candidate and candidate != current_type:
            return str(candidate)

    pytest.skip(
        f"No alternative instance type available (current: {current_type}). "
        f"Cannot test resize."
    )


@pytest.mark.nightly
@pytest.mark.requires_vdi
@pytest.mark.usefixtures("res_environment")
@pytest.mark.usefixtures("region")
class TestVdiResize:
    """
    VDI resize (instance type change) tests.

    test_resize_instance_type: stop → update instance type → start → verify new type.
    test_resize_while_running_rejected: attempt resize on READY session → expect error.
    """

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize("admin_username", ["admin1"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="res-vdi-resize" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="res-vdi-resize" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES VDI resize test project",
                    enable_budgets=False,
                ),
                [],
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
                    name="vdi-resize-" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES VDI resize test session",
                    hibernation_enabled=False,
                ),
                "project",
                "software_stack",
                "admin",
            )
        ],
        indirect=True,
    )
    def test_resize_instance_type(
        self,
        res_environment: ResEnvironment,
        admin: ClientAuth,
        admin_username: str,
        project: Project,
        software_stack: Any,
        session: Optional[Any],
    ) -> None:
        """
        Resize lifecycle: stop → update instance type → start → verify.

        1. Session starts READY with the initial instance type.
        2. Stop the session → wait for STOPPED.
        3. Update instance type to a different allowed type.
        4. Start the session → wait for READY.
        5. Verify the session's server.instance_type matches the new type.
        """
        if not session:
            pytest.fail("Session fixture returned None — VDI launch failed")

        api_client = ApiClient(res_environment, admin)
        original_type = session.server.instance_type

        # Pick a different instance type from the allowed list
        new_type = _get_different_instance_type(api_client, session, original_type)
        logger.info(f"Resize test: {session.name} from {original_type} to {new_type}")

        # Step 1: Stop
        logger.info(f"Stopping VDI {session.name}...")
        stop_response = api_client.batch_stop_session(
            BatchStopSessionRequestContent(sessions=[session])
        )
        assert stop_response.successful_list, f"Stop failed: {stop_response.unsuccessful_list}"  # type: ignore[attr-defined]
        session = wait_for_session_state(
            api_client, session, VirtualDesktopSessionState.STOPPED
        )

        # Step 2: Update instance type
        logger.info(f"Updating instance type to {new_type}...")
        update_response = api_client.update_session(
            session.idea_session_id,
            UpdateSessionRequestContent(
                session={
                    "idea_session_id": session.idea_session_id,
                    "owner": session.owner,
                    "server": {"instance_type": new_type},
                }
            ),
        )
        assert update_response is not None, "Update response should not be None"

        # Step 3: Start
        logger.info(f"Starting VDI {session.name} with new instance type...")
        start_response = api_client.batch_start_session(
            BatchStartSessionRequestContent(sessions=[session])
        )
        assert (
            start_response.successful_list
        ), f"Start failed: {start_response.unsuccessful_list}"
        session = wait_for_session_state(
            api_client, session, VirtualDesktopSessionState.READY
        )

        # Step 4: Verify
        assert session.server.instance_type == new_type, (
            f"Expected instance type {new_type}, " f"got {session.server.instance_type}"
        )
        logger.info(
            f"PASSED: VDI resized from {original_type} to "
            f"{session.server.instance_type} and reached READY."
        )

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize("admin_username", ["admin1"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="res-vdi-resize-reject"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="res-vdi-resize-reject"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES VDI resize rejection test project",
                    enable_budgets=False,
                ),
                [],
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
                    name="vdi-resize-rej-" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES VDI resize rejection test session",
                    hibernation_enabled=False,
                ),
                "project",
                "software_stack",
                "admin",
            )
        ],
        indirect=True,
    )
    def test_resize_while_running_rejected(
        self,
        res_environment: ResEnvironment,
        admin: ClientAuth,
        admin_username: str,
        project: Project,
        software_stack: Any,
        session: Optional[Any],
    ) -> None:
        """
        Attempt to resize a running VDI → expect rejection.

        The server should reject an instance type change while the session
        is in READY state (instance must be stopped first).
        """
        if not session:
            pytest.fail("Session fixture returned None — VDI launch failed")

        api_client = ApiClient(res_environment, admin)
        original_type = session.server.instance_type

        # Pick a different instance type
        new_type = _get_different_instance_type(api_client, session, original_type)
        logger.info(
            f"Attempting resize on running VDI {session.name}: "
            f"{original_type} → {new_type} (should be rejected)"
        )

        # Attempt resize while READY — should fail with 400
        with pytest.raises(Exception) as exc_info:
            api_client.update_session(
                session.idea_session_id,
                UpdateSessionRequestContent(
                    session={
                        "idea_session_id": session.idea_session_id,
                        "owner": session.owner,
                        "server": {"instance_type": new_type},
                    }
                ),
            )

        # Verify the server rejects resize on a running session
        assert hasattr(
            exc_info.value, "response"
        ), f"Expected HTTP error, got: {exc_info.value}"
        assert exc_info.value.response.status_code == 400, (
            f"Expected 400 for resize-while-running, "
            f"got {exc_info.value.response.status_code}: {exc_info.value}"
        )
        # Verify the error is specifically about resize-while-running
        error_body = exc_info.value.response.text
        assert (
            "Session must be stopped before changing instance type" in error_body
        ), f"Expected 'Session must be stopped' error, got: {error_body}"
        logger.info("PASSED: Resize while running correctly rejected with 400.")
