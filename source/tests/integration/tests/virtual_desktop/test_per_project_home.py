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
from uuid import uuid4

import pytest

from ideadatamodel import Project  # type: ignore[import]
from tests.integration.framework.client.api_client import ApiClient
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
from tests.integration.framework.utils.vdi_command_utils import (
    command_succeeded,
    run_command,
)
from tests.integration.tests.smoke.config import AL2023_SOFTWARE_STACK

VirtualDesktopSession = get_backend_model_class(
    "virtual_desktop_session", "VirtualDesktopSession"
)

logger = logging.getLogger(__name__)


@pytest.mark.nightly
@pytest.mark.requires_vdi
@pytest.mark.usefixtures("res_environment")
@pytest.mark.usefixtures("region")
class TestPerProjectHomeDirectory:
    """
    End-to-end tests verifying per-project home directory mount behavior:
    - EFS shared home: file written on VDI #1 is visible on VDI #2 (shared NFS)
    - EBS local home: file written on VDI #1 is NOT visible on VDI #2 (isolated)
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
                    title="res-efs-home" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="res-efs-home" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES EFS shared home test project",
                    enable_budgets=False,
                ),
                ["home"],  # filesystem_names — "home" attaches EFS shared storage
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
                    name="vdi-efs-home-1-" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES EFS home test VDI #1",
                    hibernation_enabled=False,
                ),
                "project",
                "software_stack",
                "admin",
            )
        ],
        indirect=True,
    )
    def test_efs_shared_home(
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
        Verify EFS shared home: write a file on VDI #1, launch VDI #2 in the
        same project, verify the file is visible (shared NFS).
        """
        if not session:
            pytest.fail("Session fixture returned None — VDI launch failed")

        logger.info(f"Starting EFS shared home test for {session.name}...")
        instance_id_1 = session.server.instance_id
        api_client = ApiClient(res_environment, admin)

        # Verify /home is NFS (EFS)
        output = run_command(instance_id_1, "df -T /home | tail -1")
        assert command_succeeded(output), f"df command failed: {output}"
        assert "nfs4" in output, f"Expected NFS mount for EFS home, got: {output}"
        logger.info(f"VDI #1: EFS mount verified: {output.strip()}")

        # Write a marker file on VDI #1
        marker = f"efs-test-{uuid4().hex[:8]}"
        marker_path = f"/home/{admin_username}/{marker}"
        run_command(instance_id_1, f"echo '{marker}' > {marker_path}")

        # Launch VDI #2 in the same project
        session_2 = create_session(
            VirtualDesktopSession(
                name="vdi-efs-home-2-" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                description="RES EFS home test VDI #2",
                hibernation_enabled=False,
                project={"project_id": project.project_id},
                base_os=software_stack.base_os,
                software_stack_id=software_stack.stack_id,
            ),
            software_stack,
            api_client,
        )
        try:
            assert session_2, "Failed to create VDI #2"
            instance_id_2 = session_2.server.instance_id

            # Verify the marker file is visible on VDI #2 (shared EFS)
            output = run_command(instance_id_2, f"cat {marker_path}")
            assert command_succeeded(output), f"cat failed on VDI #2: {output}"
            assert (
                marker in output
            ), f"Marker file not visible on VDI #2 (expected shared EFS). Output: {output}"
            logger.info("EFS shared home PASSED: file visible across VDIs.")
        finally:
            # Cleanup marker and VDI #2
            run_command(instance_id_1, f"rm -f {marker_path}")
            if session_2:
                delete_session(api_client, session_2)

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize("admin_username", ["admin1"])
    @pytest.mark.usefixtures("non_admin")
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="res-ebs-home" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="res-ebs-home" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES EBS local home test project",
                    enable_budgets=False,
                ),
                [],  # filesystem_names — empty means no shared storage (EBS local)
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
                    name="vdi-ebs-home-1-" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES EBS home test VDI #1",
                    hibernation_enabled=False,
                ),
                "project",
                "software_stack",
                "admin",
            )
        ],
        indirect=True,
    )
    def test_ebs_local_home(
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
        Verify EBS isolation: write a file on VDI #1, launch VDI #2 in the
        same project, verify the file is NOT visible (isolated EBS).
        """
        if not session:
            pytest.fail("Session fixture returned None — VDI launch failed")

        logger.info(f"Starting EBS local home test for {session.name}...")
        instance_id_1 = session.server.instance_id
        api_client = ApiClient(res_environment, admin)

        # Verify /home is NOT NFS (local EBS)
        output = run_command(instance_id_1, "df -T /home | tail -1")
        assert command_succeeded(output), f"df command failed: {output}"
        assert "nfs4" not in output, f"Expected local EBS mount, but got NFS: {output}"
        logger.info(f"VDI #1: EBS local mount verified: {output.strip()}")

        # Write a marker file on VDI #1
        marker = f"ebs-test-{uuid4().hex[:8]}"
        marker_path = f"/home/{admin_username}/{marker}"
        run_command(instance_id_1, f"echo '{marker}' > {marker_path}")

        # Launch VDI #2 in the same project
        session_2 = create_session(
            VirtualDesktopSession(
                name="vdi-ebs-home-2-" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                description="RES EBS home test VDI #2",
                hibernation_enabled=False,
                project={"project_id": project.project_id},
                base_os=software_stack.base_os,
                software_stack_id=software_stack.stack_id,
            ),
            software_stack,
            api_client,
        )
        try:
            assert session_2, "Failed to create VDI #2"
            instance_id_2 = session_2.server.instance_id

            # Verify the marker file is NOT visible on VDI #2 (isolated EBS)
            output = run_command(instance_id_2, f"cat {marker_path}")
            # The file should not exist — command should fail or return empty
            assert marker not in output, (
                f"Marker file should NOT be visible on VDI #2 (expected EBS isolation). "
                f"Output: {output}"
            )
            logger.info("EBS isolation PASSED: file NOT visible across VDIs.")
        finally:
            if session_2:
                delete_session(api_client, session_2)
