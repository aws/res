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
SSM Parameter as AMI ID integration tests.

Covers software-stack registration using a public AWS Systems Manager
parameter as the AMI ID (instead of a raw ``ami-*`` value), e.g.
/aws/service/ami-amazon-linux-latest/...

The test launches a VDI to READY to verify end-to-end functionality.
"""

import logging
import os
from typing import Any, Optional

import boto3
import pytest

from ideadatamodel import Project  # type: ignore
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

logger = logging.getLogger(__name__)

VirtualDesktopSession = get_backend_model_class(
    "virtual_desktop_session", "VirtualDesktopSession"
)
VirtualDesktopSessionState = get_backend_model_class(
    "virtual_desktop_session_state", "VirtualDesktopSessionState"
)
VirtualDesktopSoftwareStack = get_backend_model_class(
    "virtual_desktop_software_stack", "VirtualDesktopSoftwareStack"
)
VirtualDesktopArchitecture = get_backend_model_class(
    "virtual_desktop_architecture", "VirtualDesktopArchitecture"
)
VirtualDesktopBaseOS = get_backend_model_class(
    "virtual_desktop_base_os", "VirtualDesktopBaseOs"
)
VirtualDesktopGPU = get_backend_model_class("virtual_desktop_gpu", "VirtualDesktopGpu")
ResMemory = get_backend_model_class("res_memory", "ResMemory")

MIN_STORAGE = ResMemory(value=50, unit="gb")
MIN_RAM = ResMemory(value=4, unit="gb")

# Public SSM parameter for the latest AL2023 x86_64 AMI
PUBLIC_SSM_PARAMETER_PATH = (
    "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-6.1-x86_64"
)


@pytest.fixture
def public_ssm_parameter(res_environment: ResEnvironment) -> str:
    """Return the public SSM parameter ARN for the latest AL2023 AMI."""
    region = res_environment.region
    partition = boto3.session.Session().get_partition_for_region(region)
    return f"arn:{partition}:ssm:{region}::parameter{PUBLIC_SSM_PARAMETER_PATH}"


@pytest.mark.nightly
@pytest.mark.requires_vdi
@pytest.mark.usefixtures("res_environment")
@pytest.mark.usefixtures("region")
class TestSsmParameterAmi:
    """
    Software-stack registration using a public SSM parameter as AMI ID.
    Verifies that the public SSM parameter resolves correctly and the
    resulting VDI launches to READY.
    """

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize("admin_username", ["admin1"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="res-ssm-public" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="res-ssm-public" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="SSM public parameter AMI test project",
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
        [
            (
                VirtualDesktopSoftwareStack(
                    name="res-ssm-public",
                    description="SSM public parameter AMI test stack",
                    base_os=VirtualDesktopBaseOS.AMZN2023,
                    architecture=VirtualDesktopArchitecture.X86_64,
                    min_storage=MIN_STORAGE,
                    min_ram=MIN_RAM,
                    gpu=VirtualDesktopGPU.NO_GPU,
                    allowed_instance_types=["t3", "m6a"],
                ),
                "project",
                "admin",
                "public_ssm_parameter",
            )
        ],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "session",
        [
            (
                VirtualDesktopSession(
                    name="ssm-pub",
                    description="VDI from public SSM parameter stack",
                    hibernation_enabled=False,
                ),
                "project",
                "software_stack",
                "admin",
            )
        ],
        indirect=True,
    )
    def test_public_ssm_parameter_stack_launches_vdi(
        self,
        res_environment: ResEnvironment,
        admin: ClientAuth,
        admin_username: str,
        # project and software_stack are not read directly, but must be declared
        # so their indirect parametrization binds — the session fixture resolves
        # them at runtime via getfixturevalue.
        project: Any,
        software_stack: Any,
        session: Optional[Any],
    ) -> None:
        """
        Register a software stack using a public SSM parameter ARN as the AMI ID.
        Launch a VDI and verify it reaches READY state.
        """
        assert session is not None, "Session creation returned None"
        assert session.state == VirtualDesktopSessionState.READY, (
            f"Public SSM parameter VDI did not reach READY state: {session.state} "
            f"({session.failure_reason})"
        )
        logger.info(
            f"Public SSM parameter VDI launched successfully: "
            f"session={session.idea_session_id}, instance={session.server.instance_id}"
        )
