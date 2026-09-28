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
from typing import Any, Dict, Optional

import pytest

from ideadatamodel import Project  # type: ignore[import]
from tests.integration.framework.client.api_client import (
    ApiClient,
    GetSessionConnectionRequestContent,
    UpdateSessionPermissionsRequestContent,
)
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
from tests.integration.framework.utils.dcv_permissions_utils import (
    assert_dcv_permissions,
)
from tests.integration.framework.utils.model_utils import get_backend_model_class
from tests.integration.framework.utils.virtual_desktop import (
    get_session_permission_base_payload,
)
from tests.integration.tests.smoke.config import AL2023_SOFTWARE_STACK

VirtualDesktopSession = get_backend_model_class(
    "virtual_desktop_session", "VirtualDesktopSession"
)

logger = logging.getLogger(__name__)

# Default profiles seeded at deploy time
ADMIN_PROFILE_ID = "admin_profile"
OBSERVER_PROFILE_ID = "observer_profile"

PERMISSION_PROPAGATION_TIMEOUT = 120  # seconds
PERMISSION_POLL_INTERVAL = 10  # seconds


def _wait_for_connection_allowed(
    api_client: ApiClient, session: Any, timeout: int = PERMISSION_PROPAGATION_TIMEOUT
) -> Any:
    """Poll get_session_connection until it succeeds (permission propagated)."""
    start = time.time()
    last_error: Optional[Exception] = None
    while time.time() - start < timeout:
        try:
            response = api_client.get_session_connection(
                GetSessionConnectionRequestContent(
                    connection={
                        "idea_session_id": session.idea_session_id,
                        "idea_session_owner": session.owner,
                    }
                )
            )
            if response and response.connection and response.connection.access_token:  # type: ignore[attr-defined]
                return response
        except (OSError, ValueError) as e:
            last_error = e
        except Exception as e:
            # Only retry on HTTP-style errors (have a response attribute)
            if hasattr(e, "response"):
                last_error = e
            else:
                assert False, f"Unexpected exception while polling connection: {e}"
        time.sleep(PERMISSION_POLL_INTERVAL)
    assert False, f"Connection not allowed within {timeout}s. Last error: {last_error}"


def _wait_for_connection_denied(
    api_client: ApiClient, session: Any, timeout: int = PERMISSION_PROPAGATION_TIMEOUT
) -> None:
    """Poll get_session_connection until it fails with 401 (permission revoked)."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            api_client.get_session_connection(
                GetSessionConnectionRequestContent(
                    connection={
                        "idea_session_id": session.idea_session_id,
                        "idea_session_owner": session.owner,
                    }
                )
            )
        except Exception as e:
            if hasattr(e, "response") and e.response.status_code == 401:
                return
            # Non-HTTP exceptions are unexpected — fail immediately with context
            if not hasattr(e, "response"):
                assert False, f"Unexpected exception while polling connection: {e}"
        time.sleep(PERMISSION_POLL_INTERVAL)
    assert False, f"Connection not denied within {timeout}s"


def _build_permission_payload(
    session: Any, actor_name: str, profile_id: str
) -> Dict[str, Any]:
    """Build a permission payload for sharing a session."""
    return get_session_permission_base_payload(
        idea_session_id=session.idea_session_id,
        idea_session_owner=session.owner,
        idea_session_name=session.name,
        actor_name=actor_name,
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
        permission_profile={"profile_id": profile_id},
    )


@pytest.mark.nightly
@pytest.mark.requires_vdi
@pytest.mark.usefixtures("res_environment")
@pytest.mark.usefixtures("region")
class TestVdiSharing:
    """
    End-to-end VDI sharing tests. Each test gets its own VDI and runs
    independently in parallel.
    """

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize("admin_username", ["admin1"])
    @pytest.mark.usefixtures("non_admin")
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="res-share-grant" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="res-share-grant" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES sharing test: grant",
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
                    name="vdi-share-grant-" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES VDI sharing: grant",
                    hibernation_enabled=False,
                ),
                "project",
                "software_stack",
                "admin",
            )
        ],
        indirect=True,
    )
    def test_share_grant_allows_connection(
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
        """Grant sharing → non-admin can obtain connection info."""
        if not session:
            pytest.fail("Session fixture returned None — VDI launch failed")

        admin_api_client = ApiClient(res_environment, admin)
        non_admin_api_client = ApiClient(res_environment, non_admin)

        payload = _build_permission_payload(
            session, non_admin_username, ADMIN_PROFILE_ID
        )
        admin_api_client.update_session_permissions(
            UpdateSessionPermissionsRequestContent(
                create=[payload], update=[], delete=[]
            )
        )

        response = _wait_for_connection_allowed(non_admin_api_client, session)
        assert response.connection.access_token, "Expected a valid access token"
        logger.info("PASSED: Non-admin obtained connection info after share-grant.")

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize("admin_username", ["admin1"])
    @pytest.mark.usefixtures("non_admin")
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="res-share-observer"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="res-share-observer"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES sharing test: observer",
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
                    name="vdi-share-observer-"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES VDI sharing: observer",
                    hibernation_enabled=False,
                ),
                "project",
                "software_stack",
                "admin",
            )
        ],
        indirect=True,
    )
    def test_share_observer_permissions(
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
        """Share with observer_profile → verify view-only DCV permissions on disk."""
        if not session:
            pytest.fail("Session fixture returned None — VDI launch failed")

        admin_api_client = ApiClient(res_environment, admin)
        non_admin_api_client = ApiClient(res_environment, non_admin)
        instance_id = session.server.instance_id
        dcv_session_id = session.dcv_session_id

        payload = _build_permission_payload(
            session, non_admin_username, OBSERVER_PROFILE_ID
        )
        admin_api_client.update_session_permissions(
            UpdateSessionPermissionsRequestContent(
                create=[payload], update=[], delete=[]
            )
        )
        _wait_for_connection_allowed(non_admin_api_client, session)

        assert_dcv_permissions(
            instance_id,
            dcv_session_id,
            non_admin_username,
            expected_allowed={"display"},
            expected_denied={"keyboard", "mouse", "clipboard-copy"},
        )
        logger.info("PASSED: Observer permissions enforced in DCV permissions file.")

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize("admin_username", ["admin1"])
    @pytest.mark.usefixtures("non_admin")
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="res-share-expand"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="res-share-expand" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES sharing test: expand",
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
                    name="vdi-share-expand-"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES VDI sharing: expand",
                    hibernation_enabled=False,
                ),
                "project",
                "software_stack",
                "admin",
            )
        ],
        indirect=True,
    )
    def test_share_expand_to_admin(
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
        """Grant observer → expand to admin_profile → verify builtin permissions."""
        if not session:
            pytest.fail("Session fixture returned None — VDI launch failed")

        admin_api_client = ApiClient(res_environment, admin)
        non_admin_api_client = ApiClient(res_environment, non_admin)
        instance_id = session.server.instance_id
        dcv_session_id = session.dcv_session_id

        # Grant observer first
        observer_payload = _build_permission_payload(
            session, non_admin_username, OBSERVER_PROFILE_ID
        )
        admin_api_client.update_session_permissions(
            UpdateSessionPermissionsRequestContent(
                create=[observer_payload], update=[], delete=[]
            )
        )
        _wait_for_connection_allowed(non_admin_api_client, session)

        # Expand to admin
        admin_payload = _build_permission_payload(
            session, non_admin_username, ADMIN_PROFILE_ID
        )
        admin_api_client.update_session_permissions(
            UpdateSessionPermissionsRequestContent(
                create=[], update=[admin_payload], delete=[]
            )
        )

        assert_dcv_permissions(
            instance_id,
            dcv_session_id,
            non_admin_username,
            expected_allowed={"builtin"},
        )
        logger.info("PASSED: Permissions expanded to admin (builtin).")

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize("admin_username", ["admin1"])
    @pytest.mark.usefixtures("non_admin")
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="res-share-revoke"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="res-share-revoke" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES sharing test: revoke",
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
                    name="vdi-share-revoke-"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES VDI sharing: revoke",
                    hibernation_enabled=False,
                ),
                "project",
                "software_stack",
                "admin",
            )
        ],
        indirect=True,
    )
    def test_share_revoke_denies_connection(
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
        """Grant sharing → revoke → non-admin connection denied."""
        if not session:
            pytest.fail("Session fixture returned None — VDI launch failed")

        admin_api_client = ApiClient(res_environment, admin)
        non_admin_api_client = ApiClient(res_environment, non_admin)

        payload = _build_permission_payload(
            session, non_admin_username, ADMIN_PROFILE_ID
        )
        admin_api_client.update_session_permissions(
            UpdateSessionPermissionsRequestContent(
                create=[payload], update=[], delete=[]
            )
        )
        _wait_for_connection_allowed(non_admin_api_client, session)

        # Revoke
        admin_api_client.update_session_permissions(
            UpdateSessionPermissionsRequestContent(
                create=[], update=[], delete=[payload]
            )
        )
        _wait_for_connection_denied(non_admin_api_client, session)
        logger.info("PASSED: Non-admin denied after share revocation.")
