# #  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# #
# #  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# #  with the License. A copy of the License is located at
# #
# #      http://www.apache.org/licenses/LICENSE-2.0
# #
# #  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# #  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# #  and limitations under the License.

import logging

import pytest

from ideadatamodel import Project  # type: ignore
from tests.integration.framework.client.api_client import (
    ApiClient,
    BatchCreateSessionRequestContent,
    CreateSoftwareStackRequestContent,
)
from tests.integration.framework.fixtures.project import project
from tests.integration.framework.fixtures.res_environment import (
    ResEnvironment,
    res_environment,
)
from tests.integration.framework.fixtures.users import admin
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.ec2_utils import get_latest_x86_amzn2023_ami_id
from tests.integration.framework.utils.model_utils import get_backend_model_class

VirtualDesktopSession_ = get_backend_model_class(
    "virtual_desktop_session", "VirtualDesktopSession"
)
VirtualDesktopBaseOs = get_backend_model_class(
    "virtual_desktop_base_os", "VirtualDesktopBaseOs"
)
VirtualDesktopGpu = get_backend_model_class("virtual_desktop_gpu", "VirtualDesktopGpu")
VirtualDesktopArchitecture = get_backend_model_class(
    "virtual_desktop_architecture", "VirtualDesktopArchitecture"
)

logger = logging.getLogger(__name__)


class TestListSessionsCustom:

    @pytest.mark.skip(reason="Temporarily Skipping Test")
    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="res-string-verification",
                    name="res-string-verification",
                    description="RES integ test for verifying username session security",
                    enable_budgets=False,
                ),
                ["home"],
                ["RESAdministrators", "group_1", "group_2"],
                ["user1", "user2"],
                "admin",
            )
        ],
        indirect=True,
    )
    def test_substring_vulnerability(
        self,
        res_environment: ResEnvironment,
        region: str,
        admin: ClientAuth,
        project: Project,
    ) -> None:

        ami_id = get_latest_x86_amzn2023_ami_id(region)

        clusteradmin_api_client = ApiClient(
            res_environment, ClientAuth(username="clusteradmin")
        )

        software_stack_request = CreateSoftwareStackRequestContent(
            software_stack={
                "name": "Software-Stack-res-string-verification",
                "description": "Software-Stack for res string verification",
                "base_os": VirtualDesktopBaseOs.AMZN2023,
                "architecture": VirtualDesktopArchitecture.X86_64,
                "gpu": VirtualDesktopGpu.NO_GPU,
                "min_storage": {"value": 50, "unit": "gb"},
                "min_ram": {"value": 4, "unit": "gb"},
                "allowed_instance_types": ["t3.medium", "t3.large"],
                "projects": [{"project_id": project.project_id}],
                "ami_id": ami_id,
            }
        )

        response_stack = clusteradmin_api_client.create_software_stack(
            software_stack_request
        )

        admin1_username = "admin1"
        test_username = "admi"

        test_user_client = ApiClient(
            res_environment, ClientAuth(username=test_username)
        )

        admin1_api_client = ApiClient(
            res_environment, ClientAuth(username=admin1_username)
        )

        session = VirtualDesktopSession_.from_dict(
            {
                "name": "VirtualDesktop-res-string-verification",
                "description": "RES username string verification session",
                "hibernation_enabled": False,
                "owner": admin1_username,
                "base_os": VirtualDesktopBaseOs.AMZN2023,
                "software_stack_id": response_stack.software_stack.stack_id,  # type: ignore[attr-defined]
                "project": {"project_id": project.project_id},
                "server": {
                    "instance_type": "t3.medium",
                    "root_volume_size": {"value": 50, "unit": "gb"},
                },
            }
        )

        admin1_api_client.batch_create_session(
            BatchCreateSessionRequestContent(sessions=[session])
        )

        admin1_sessions = admin1_api_client.list_sessions()
        test_user_sessions = test_user_client.list_sessions()

        assert len(admin1_sessions.listing) > 0, "No sessions found for admin1"  # type: ignore

        for session in test_user_sessions.listing:  # type: ignore
            if session.owner == admin1_username:
                pytest.fail(
                    f"VULNERABILITY: User 'admi' can see '{admin1_username}' session: {session.name}"
                )
