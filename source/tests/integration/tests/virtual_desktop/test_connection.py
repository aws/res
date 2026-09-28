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

# DownloadFilesRequest goes through the ResClient SocaEnvelope path and Project
# through the cluster-manager API — both not yet migrated, so they stay ideadatamodel.
from ideadatamodel import DownloadFilesRequest, Project  # type: ignore
from tests.integration.framework.client.api_client import (
    ApiClient,
    GetSessionConnectionRequestContent,
)
from tests.integration.framework.client.res_client import ResClient
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
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.model_utils import get_backend_model_class
from tests.integration.framework.utils.vdi_command_utils import (
    command_succeeded,
    run_command,
)
from tests.integration.tests.smoke.config import AL2023_SOFTWARE_STACK

# Backend data-model classes (source/idea/data-model). The session APIs consume
# and return these.
VirtualDesktopSession = get_backend_model_class(
    "virtual_desktop_session", "VirtualDesktopSession"
)

logger = logging.getLogger(__name__)


@pytest.mark.nightly
@pytest.mark.requires_vdi
@pytest.mark.usefixtures("res_environment")
@pytest.mark.usefixtures("region")
class TestVdiConnection:
    """
    VDI Connection tests (doc "VDI Connection"): gateway routing for multiple
    VDIs and file download via file-browser API.
    """

    @pytest.mark.parametrize("admin_username", ["admin1"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="res-conn-routing"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="res-conn-routing" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES connection routing test project",
                    enable_budgets=False,
                ),
                ["home"],
                ["RESAdministrators"],
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
    def test_gateway_routing_two_vdis(
        self,
        request: pytest.FixtureRequest,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
        project: Project,
        software_stack: Any,
    ) -> None:
        """
        Two VDIs for the same user in the same project each get distinct
        connection-info (different web_url_path / dcv_session_id), confirming
        the gateway routes to the correct instance.
        """
        api_client = ApiClient(res_environment, admin)

        # Launch two VDIs from the same stack/project.
        # The project fixture returns a legacy (pydantic) Project; the new-model
        # session serializes `project` via to_dict(), which would drop it to {}
        # and lose project_id. Attach it by id instead.
        project_ref = {"project_id": project.project_id}

        session_a = VirtualDesktopSession(
            name="conn-a",
            description="routing test VDI A",
            hibernation_enabled=False,
        )
        session_a.project = project_ref
        session_a.base_os = software_stack.base_os
        session_a.software_stack_id = software_stack.stack_id

        session_b = VirtualDesktopSession(
            name="conn-b",
            description="routing test VDI B",
            hibernation_enabled=False,
        )
        session_b.project = project_ref
        session_b.base_os = software_stack.base_os
        session_b.software_stack_id = software_stack.stack_id

        vdi_a = create_session(session_a, software_stack, api_client)
        assert vdi_a, "VDI A was not created"
        request.addfinalizer(lambda: delete_session(api_client, vdi_a))

        vdi_b = create_session(session_b, software_stack, api_client)
        assert vdi_b, "VDI B was not created"
        request.addfinalizer(lambda: delete_session(api_client, vdi_b))

        # Get connection info for each via the backend Lambda API.
        admin_api_client = ApiClient(res_environment, admin)

        resp_a = admin_api_client.get_session_connection(
            GetSessionConnectionRequestContent(
                connection={
                    "idea_session_id": vdi_a.idea_session_id,
                    "idea_session_owner": admin_username,
                }
            )
        )
        resp_b = admin_api_client.get_session_connection(
            GetSessionConnectionRequestContent(
                connection={
                    "idea_session_id": vdi_b.idea_session_id,
                    "idea_session_owner": admin_username,
                }
            )
        )
        assert resp_a is not None and resp_a.connection is not None
        assert resp_b is not None and resp_b.connection is not None
        conn_a = resp_a.connection
        conn_b = resp_b.connection

        # Both must have valid routing info.
        assert conn_a.endpoint, f"VDI A missing endpoint: {conn_a}"
        assert conn_b.endpoint, f"VDI B missing endpoint: {conn_b}"
        assert conn_a.web_url_path, f"VDI A missing web_url_path: {conn_a}"
        assert conn_b.web_url_path, f"VDI B missing web_url_path: {conn_b}"

        # They must route to DIFFERENT instances.
        assert (
            vdi_a.server.instance_id != vdi_b.server.instance_id
        ), "Both VDIs ended up on the same instance"
        # Each connection gets a distinct token for its session.
        assert (
            conn_a.access_token != conn_b.access_token
        ), "Both connections returned the same access_token"

    @pytest.mark.parametrize("admin_username", ["admin1"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="res-conn-download"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="res-conn-download"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES file download test project",
                    enable_budgets=False,
                ),
                ["home"],
                ["RESAdministrators"],
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
                    name="conn-dl",
                    description="RES file download test VDI",
                    hibernation_enabled=False,
                ),
                "project",
                "software_stack",
                "admin",
            )
        ],
        indirect=True,
    )
    def test_large_file_download_via_file_browser(
        self,
        request: pytest.FixtureRequest,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
        project: Project,
        software_stack: Any,
        session: Optional[Any],
    ) -> None:
        """
        A file created on a VDI (via SSM) is downloadable through the
        file-browser API. Verifies the download path end-to-end.
        """
        assert session, "VDI session was not created"

        instance_id = session.server.instance_id
        user = session.owner
        test_file = f"/home/{user}/download_test_50m.bin"

        # Create a 50MB file on the VDI.
        output = run_command(
            instance_id, f"dd if=/dev/urandom of={test_file} bs=1M count=50 2>&1"
        )
        assert command_succeeded(output), f"Failed to create test file: {output}"

        # Download via file-browser API.
        api_invoker_type = request.config.getoption("--api-invoker-type")
        client = ResClient(res_environment, admin, api_invoker_type)
        download_response = client.download_files(
            request=DownloadFilesRequest(files=[test_file])
        )
        assert (
            download_response.download_url
        ), f"File browser returned no download URL for {test_file}"

        # Cleanup the file from the VDI.
        run_command(instance_id, f"rm -f {test_file}")
