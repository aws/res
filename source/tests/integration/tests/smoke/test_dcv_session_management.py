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
import time
from typing import Any, Optional

import pytest
from res.constants import DCV_CONNECTION_TOKEN_VALIDITY_KEY  # type: ignore
from res.resources import cluster_settings  # type: ignore

# VirtualDesktopSessionConnection is used by _assert_connection_rejected
# and _get_connection_info to construct connection data for the Selenium browser.
from datamodel.models.virtual_desktop_session_connection import (  # type: ignore
    VirtualDesktopSessionConnection,
)
from ideadatamodel import Project  # type: ignore
from tests.integration.framework.client.api_client import (
    GetSessionConnectionRequestContent,
    ApiClient,
    UpdateSessionPermissionsRequestContent,
)
from tests.integration.framework.fixtures.fixture_request import FixtureRequest
from tests.integration.framework.fixtures.project import project
from tests.integration.framework.fixtures.res_environment import (
    ResEnvironment,
    res_environment,
)
from tests.integration.framework.fixtures.session import (
    create_session,
    delete_session,
    session,
)
from tests.integration.framework.fixtures.software_stack import software_stack
from tests.integration.framework.fixtures.users.admin import admin
from tests.integration.framework.fixtures.users.non_admin import non_admin
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.model_utils import get_backend_model_class
from tests.integration.framework.utils.session_utils import (
    wait_for_session_connection_count,
)
from tests.integration.framework.utils.virtual_desktop import (
    get_session_permission_base_payload,
)
from tests.integration.tests.smoke.config import AL2023_SOFTWARE_STACK

# Backend data-model classes (source/idea/data-model). The session APIs consume
# and return these.
VirtualDesktopSession = get_backend_model_class(
    "virtual_desktop_session", "VirtualDesktopSession"
)

logger = logging.getLogger(__name__)


def _assert_connection_rejected(
    connection_info: VirtualDesktopSessionConnection,
    expected_error: str,
    timeout: int = 60,
) -> None:
    """Connect to a session and verify the connection is rejected."""
    driver = ApiClient.connect_to_session(
        endpoint=connection_info.endpoint,
        web_url_path=connection_info.web_url_path,
        access_token=connection_info.access_token,
        idea_session_id=connection_info.idea_session_id,
    )
    try:
        deadline = time.time() + timeout
        all_messages: list[str] = []
        while time.time() < deadline:
            time.sleep(5)
            browser_logs = driver.get_log("browser")
            for entry in browser_logs:
                logger.info(f"Browser log [{entry['level']}]: {entry['message']}")
                all_messages.append(entry["message"])
            if any(expected_error in msg for msg in all_messages):
                return
        log_messages = " ".join(all_messages)
        assert (
            expected_error in log_messages
        ), f"Expected '{expected_error}' in browser logs within {timeout}s, got: {log_messages[:500]}"
    finally:
        driver.quit()


def _get_connection_info(
    api_client: ApiClient,
    idea_session_id: str,
    idea_session_owner: str,
) -> VirtualDesktopSessionConnection:
    """Get session connection info via the new backend Lambda API."""
    response = api_client.get_session_connection(
        GetSessionConnectionRequestContent(
            connection={
                "idea_session_id": idea_session_id,
                "idea_session_owner": idea_session_owner,
            }
        )
    )
    assert response is not None and response.connection is not None
    conn = response.connection
    return VirtualDesktopSessionConnection(
        idea_session_id=conn.idea_session_id,
        idea_session_owner=conn.idea_session_owner,
        endpoint=conn.endpoint,
        web_url_path=conn.web_url_path,
        access_token=conn.access_token,
    )


@pytest.mark.nightly
@pytest.mark.usefixtures("res_environment")
@pytest.mark.usefixtures("region")
class TestDcvSessionManagement:
    """
    Smoke test for DCV session management.
    """

    @pytest.mark.smoke_subset
    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize("admin_username", ["admin1"])
    @pytest.mark.usefixtures("non_admin")
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="res-access-ctrl-test"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="res-access-ctrl-test"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES access control test project",
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
                    name="acl",
                    description="RES access control test session",
                    hibernation_enabled=False,
                ),
                "project",
                "software_stack",
                "admin",
            )
        ],
        indirect=True,
    )
    def test_session_connection_access_control(
        self,
        request: FixtureRequest,
        region: str,
        admin: ClientAuth,
        admin_username: str,
        non_admin: ClientAuth,
        non_admin_username: str,
        res_environment: ResEnvironment,
        project: Project,
        software_stack: Any,
        session: Optional[Any],
    ) -> None:
        """
        Single test covering session connection token and access control scenarios:
        1. Valid token — session owner can connect to their session.
        2. No token — connection without a token is rejected.
        3. Expired token — a previously valid token is rejected after expiry.
        4. Wrong session — token issued for one session is rejected for a different session.
        5. Revoked permission — shared user's token is rejected after permission revocation.
        6. Unauthorized user — user without permission cannot obtain connection info.
        """
        if not session:
            pytest.skip(
                "Session fixture returned None — session creation may have failed"
            )

        admin_api_client = ApiClient(res_environment, admin)
        non_admin_api_client = ApiClient(res_environment, non_admin)

        # Get connection info as session owner (admin)
        valid_connection_info = _get_connection_info(
            admin_api_client, session.idea_session_id, session.owner
        )

        # 1. Valid token — session owner can connect
        driver = ApiClient.connect_to_session(
            endpoint=valid_connection_info.endpoint,
            web_url_path=valid_connection_info.web_url_path,
            access_token=valid_connection_info.access_token,
            idea_session_id=valid_connection_info.idea_session_id,
        )
        try:
            wait_for_session_connection_count(session, 1)
        finally:
            driver.quit()
        wait_for_session_connection_count(session, 0)

        # 2. No token — connection rejected
        no_token_info = VirtualDesktopSessionConnection(
            idea_session_id=session.idea_session_id,
            idea_session_owner=session.owner,
            endpoint=valid_connection_info.endpoint,
            web_url_path=valid_connection_info.web_url_path,
            access_token="",
        )
        logger.info("Attempting connection without a token...")
        _assert_connection_rejected(no_token_info, "Failed to communicate with server")

        # 3. Expired token — rejected after expiry
        original_validity = cluster_settings.get_setting(
            DCV_CONNECTION_TOKEN_VALIDITY_KEY
        )
        cluster_settings.update_setting(DCV_CONNECTION_TOKEN_VALIDITY_KEY, "0")
        try:
            expired_connection_info = _get_connection_info(
                admin_api_client, session.idea_session_id, session.owner
            )
        finally:
            # Restore original value; fall back to product default (1440 min = 24h)
            cluster_settings.update_setting(
                DCV_CONNECTION_TOKEN_VALIDITY_KEY,
                original_validity if original_validity is not None else "1440",
            )

        # Wait for the token TTL to pass (validity=0 expires at the same second)
        time.sleep(2)
        logger.info("Attempting connection with expired token...")
        _assert_connection_rejected(expired_connection_info, "Authentication failed")

        # 4. Wrong session — token rejected for a different session
        # Create a second session to test cross-session token rejection
        session2 = create_session(
            VirtualDesktopSession(
                name="acl2",
                description="Second session for token binding test",
                hibernation_enabled=False,
                project={"project_id": project.project_id},
                base_os=software_stack.base_os,
                software_stack_id=software_stack.stack_id,
            ),
            software_stack,
            admin_api_client,
        )
        try:
            assert session2, "Second session creation failed"
            # Get connection info for session2
            session2_connection_info = _get_connection_info(
                admin_api_client, session2.idea_session_id, session2.owner
            )

            # Use token from session1 but connect to session2's DCV session
            cross_session_info = VirtualDesktopSessionConnection(
                idea_session_id=session2.idea_session_id,
                idea_session_owner=session2.owner,
                endpoint=session2_connection_info.endpoint,
                web_url_path=session2_connection_info.web_url_path,
                access_token=valid_connection_info.access_token,  # token from session1
            )
            logger.info("Attempting connection with token from a different session...")
            _assert_connection_rejected(cross_session_info, "Authentication failed")
        finally:
            if session2:
                delete_session(
                    admin_api_client,
                    session2,
                )

        # 5. Revoked permission — token rejected after permission revocation
        # Share session with non_admin first
        permission_payload = get_session_permission_base_payload(
            idea_session_id=session.idea_session_id,
            idea_session_owner=session.owner,
            idea_session_name=session.name,
            actor_name=non_admin_username,
            idea_session_instance_type=session.server.instance_type,
            idea_session_state="READY",
            idea_session_base_os=(
                session.base_os.value
                if hasattr(session.base_os, "value")
                else session.base_os
            ),
            idea_session_hibernation_enabled=session.hibernation_enabled,
            idea_session_type="VIRTUAL",
            actor_type="USER",
            permission_profile={"profile_id": "admin_profile"},
        )
        admin_api_client.update_session_permissions(
            UpdateSessionPermissionsRequestContent(
                create=[permission_payload], update=[], delete=[]
            )
        )
        time.sleep(30)

        # Get a token as non_admin (shared user)
        non_admin_connection_info = _get_connection_info(
            non_admin_api_client, session.idea_session_id, session.owner
        )

        # Revoke permission
        admin_api_client.update_session_permissions(
            UpdateSessionPermissionsRequestContent(
                create=[],
                update=[],
                delete=[permission_payload],
            )
        )
        time.sleep(30)

        logger.info("Attempting connection with revoked permission...")
        _assert_connection_rejected(non_admin_connection_info, "Authentication failed")

        # 6. Unauthorized user — cannot obtain connection info
        with pytest.raises(Exception) as exc_info:
            _get_connection_info(
                non_admin_api_client, session.idea_session_id, session.owner
            )
        error = exc_info.value
        assert hasattr(error, "response"), f"Expected HTTPError with response, got: {error}"
        assert error.response.status_code == 401
        assert "does not have permission" in error.response.text
