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

import base64
import json
import logging
import os
import time
import uuid
from typing import Optional

import pytest
from res.constants import CLUSTER_ADMIN_USERNAME  # type: ignore
from res.resources import software_stacks  # type: ignore
from res.utils import auth_utils  # type: ignore

from ideadatamodel import (  # type: ignore
    CreateFileRequest,
    CreateSessionRequest,
    CreateSoftwareStackFromSessionRequest,
    DeleteFilesRequest,
    DeleteSessionRequest,
    DeleteSoftwareStackRequest,
    DownloadFilesRequest,
    GetModuleSettingsRequest,
    GetPermissionProfileRequest,
    GetSoftwareStackInfoRequest,
    GetUserRequest,
    ListEmailTemplatesRequest,
    ListFilesRequest,
    ListSoftwareStackRequest,
    Project,
    ReadFileRequest,
    SaveFileRequest,
    SocaMemory,
    SocaMemoryUnit,
    TailFileRequest,
    UpdateModuleSettingsRequest,
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
from tests.integration.framework.fixtures.session import (
    create_session,
    delete_session,
    session,
)
from tests.integration.framework.fixtures.software_stack import software_stack
from tests.integration.framework.fixtures.users.admin import admin
from tests.integration.framework.fixtures.users.cognito_admin import cognito_admin
from tests.integration.framework.fixtures.users.non_admin import non_admin
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.ec2_utils import (
    cluster_manager_instances,
    deregister_ami,
)
from tests.integration.framework.utils.remote_command_runner import EC2InstancePlatform
from tests.integration.framework.utils.session_utils import (
    wait_for_session_connection_count,
    wait_for_software_stack_to_be_active,
)
from tests.integration.framework.utils.sssd_utils import check_sssd_config_field
from tests.integration.tests.config import (
    AL2_SOFTWARE_STACK,
    LINUX_SOFTWARE_STACKS,
    TEST_SOFTWARE_STACKS,
)

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("res_environment")
@pytest.mark.usefixtures("region")
class TestsSmoke(object):
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
                    title="res-integ-test" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="res-integ-test" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES integ test project",
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
        [
            (software_stack, "project", "admin")
            for software_stack in TEST_SOFTWARE_STACKS
        ],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "session",
        [
            (
                VirtualDesktopSession(
                    name="ADVirtualDesktop" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES integ test VDI session",
                    hibernation_enabled=False,
                ),
                "project",
                "software_stack",
                "non_admin",
            )
        ],
        indirect=True,
    )
    def test_end_to_end_succeed(
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
        Test the end to end workflow:
        1. Create a project, software stack and virtual desktop session.
        2. Join the virtual desktop session from a headless web browser and close it.
        3. Clean up the test project, software stack and virtual desktop session.
        """
        if not session:
            # VDI is not supported with the current configuration
            return

        api_invoker_type = request.config.getoption("--api-invoker-type")
        client = ResClient(res_environment, non_admin, api_invoker_type)
        web_driver = client.join_session(session)
        wait_for_session_connection_count(region, session, 1)

        logger.info(f"leaving session {session.dcv_session_id}...")
        web_driver.quit()
        wait_for_session_connection_count(region, session, 0)

    @pytest.mark.usefixtures("cognito_admin")
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="res-cognito-integ-test"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="res-cognito-integ-test"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES cognito integ test project",
                    enable_budgets=False,
                ),
                ["home"],
                [],
                ["clusteradmin"],
                "cognito_admin",
            )
        ],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "software_stack",
        [
            (software_stack, "project", "cognito_admin")
            for software_stack in LINUX_SOFTWARE_STACKS
            # for software_stack in [AL2_SOFTWARE_STACK]
        ],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "session",
        [
            (
                VirtualDesktopSession(
                    name="CognitoVirtualDesktop"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES integ test VDI session",
                    hibernation_enabled=False,
                ),
                "project",
                "software_stack",
                "cognito_admin",
            )
        ],
        indirect=True,
    )
    def test_cognito_end_to_end_succeed(
        self,
        request: FixtureRequest,
        region: str,
        cognito_admin: ClientAuth,
        res_environment: ResEnvironment,
        project: Project,
        software_stack: VirtualDesktopSoftwareStack,
        session: Optional[VirtualDesktopSession],
    ) -> None:
        """
        Test the end to end workflow:
        1. Create a project, software stack and virtual desktop session.
        2. Join the virtual desktop session from a headless web browser and close it.
        3. Clean up the test project, software stack and virtual desktop session.
        """
        if not session:
            # VDI is not supported with the current configuration
            return

        api_invoker_type = request.config.getoption("--api-invoker-type")
        client = ResClient(res_environment, cognito_admin, api_invoker_type)
        web_driver = client.join_session(session)
        wait_for_session_connection_count(region, session, 1)

        logger.info(f"leaving session {session.dcv_session_id}...")
        web_driver.quit()
        wait_for_session_connection_count(region, session, 0)

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
    def test_file_browser_succeed(
        self,
        request: FixtureRequest,
        region: str,
        admin: ClientAuth,
        admin_username: str,
        non_admin: ClientAuth,
        non_admin_username: str,
        res_environment: ResEnvironment,
    ) -> None:
        """
        Test the end to end workflow for file browser:
        """
        test_unique_id = str(uuid.uuid4())
        test_dir_name = "smoke-test_" + test_unique_id
        test_file_name = "test-file_" + test_unique_id + ".txt"
        for test_enable_file_browser_value in [True, False]:
            api_invoker_type = request.config.getoption("--api-invoker-type")
            admin_client = ResClient(res_environment, admin, api_invoker_type)
            non_admin_client = ResClient(res_environment, non_admin, api_invoker_type)

            original_settings = admin_client.get_module_settings(
                request=GetModuleSettingsRequest(module_id="shared-storage")
            )
            original_file_browser_value = original_settings.settings[
                "enable_file_browser"
            ]
            admin_client.update_module_settings(
                request=UpdateModuleSettingsRequest(
                    module_id="shared-storage",
                    settings={"enable_file_browser": test_enable_file_browser_value},
                )
            )
            updated_file_browser_value = admin_client.get_module_settings(
                request=GetModuleSettingsRequest(module_id="shared-storage")
            )
            assert (
                updated_file_browser_value.settings["enable_file_browser"]
                == test_enable_file_browser_value
            )
            list_files_response = non_admin_client.list_files(
                request=ListFilesRequest(
                    cwd=f"/home/{non_admin_username}",
                ),
                should_succeed=test_enable_file_browser_value,
            )
            non_admin_client.create_file(
                request=CreateFileRequest(
                    cwd=f"/home/{non_admin_username}",
                    filename=test_dir_name,
                    is_folder=True,
                ),
                should_succeed=test_enable_file_browser_value,
            )
            non_admin_client.create_file(
                request=CreateFileRequest(
                    cwd=f"/home/{non_admin_username}/{test_dir_name}/",
                    filename=test_file_name,
                    is_folder=False,
                ),
                should_succeed=test_enable_file_browser_value,
            )
            non_admin_client.save_file(
                request=SaveFileRequest(
                    file=f"/home/{non_admin_username}/{test_dir_name}/{test_file_name}",
                    content=base64.b64encode(str.encode("%CONTENT%")),
                ),
                should_succeed=test_enable_file_browser_value,
            )
            read_file_response = non_admin_client.read_file(
                request=ReadFileRequest(
                    file=f"/home/{non_admin_username}/{test_dir_name}/{test_file_name}"
                ),
                should_succeed=test_enable_file_browser_value,
            )
            tail_file_response = non_admin_client.tail_file(
                request=TailFileRequest(
                    file=f"/home/{non_admin_username}/{test_dir_name}/{test_file_name}"
                ),
                should_succeed=test_enable_file_browser_value,
            )
            download_files_response = non_admin_client.download_files(
                request=DownloadFilesRequest(
                    files=[
                        f"/home/{non_admin_username}/{test_dir_name}/{test_file_name}"
                    ]
                ),
                should_succeed=test_enable_file_browser_value,
            )
            non_admin_client.delete_files(
                request=DeleteFilesRequest(
                    files=[f"/home/{non_admin_username}/idea_downloads/"]
                ),
                should_succeed=test_enable_file_browser_value,
            )
            non_admin_client.delete_files(
                request=DeleteFilesRequest(
                    files=[f"/home/{non_admin_username}/{test_dir_name}/"]
                ),
                should_succeed=test_enable_file_browser_value,
            )
            admin_client.update_module_settings(
                request=UpdateModuleSettingsRequest(
                    module_id="shared-storage",
                    settings={"enable_file_browser": original_file_browser_value},
                )
            )
            if test_enable_file_browser_value:
                assert list_files_response.listing is not None
                assert (
                    read_file_response.file
                    == f"/home/{non_admin_username}/{test_dir_name}/{test_file_name}"
                )
                assert read_file_response.content_type == "text/plain"
                assert (
                    base64.b64decode(read_file_response.content).decode("utf-8")
                    == "%CONTENT%"
                )
                assert (
                    tail_file_response.file
                    == f"/home/{non_admin_username}/{test_dir_name}/{test_file_name}"
                )
                assert tail_file_response.next_token is not None
                assert tail_file_response.lines is not None
                assert download_files_response.download_url is not None

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize(
        "admin_username",
        [
            "admin1",
        ],
    )
    def test_permission_profiles_table_populated(
        self,
        request: FixtureRequest,
        admin: ClientAuth,
        admin_username: str,
        res_environment: ResEnvironment,
    ) -> None:
        """
        Test permission profiles table has been populated with default values
        """
        api_invoker_type = request.config.getoption("--api-invoker-type")
        admin_client = ResClient(res_environment, admin, api_invoker_type)

        for profile_id in ["admin_profile", "observer_profile"]:
            current_profile = admin_client.get_permission_profile(
                request=GetPermissionProfileRequest(profile_id=profile_id)
            ).profile
            assert current_profile is not None
            assert current_profile.profile_id == profile_id

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize(
        "admin_username",
        [
            "admin1",
        ],
    )
    def test_software_stacks_table_populated(
        self,
        request: FixtureRequest,
        admin: ClientAuth,
        admin_username: str,
        res_environment: ResEnvironment,
    ) -> None:
        """
        Test software stacks table has been populated with default values
        """
        api_invoker_type = request.config.getoption("--api-invoker-type")
        admin_client = ResClient(res_environment, admin, api_invoker_type)

        default_stack_count = 0
        stacks = admin_client.list_software_stacks(
            request=ListSoftwareStackRequest()
        ).listing

        assert stacks is not None
        for stack in stacks:
            assert stack.base_os in software_stacks.BASE_OS
            assert stack.stack_id is not None
            assert stack.ami_id is not None
            stack_name = stack.name
            if not stack_name.startswith("res-integ-test-stack"):
                default_stack_count += 1
        assert default_stack_count > 0

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize(
        "admin_username",
        [
            "admin1",
        ],
    )
    def test_users_table_populated(
        self,
        request: FixtureRequest,
        admin: ClientAuth,
        admin_username: str,
        res_environment: ResEnvironment,
    ) -> None:
        """
        Test users table has been populated with clusteradmin

        """
        api_invoker_type = request.config.getoption("--api-invoker-type")
        admin_client = ResClient(res_environment, admin, api_invoker_type)

        current_clusteradmin = admin_client.get_user(
            request=GetUserRequest(username=CLUSTER_ADMIN_USERNAME)
        ).user
        assert current_clusteradmin is not None
        assert current_clusteradmin.uid == auth_utils.COGNITO_MIN_ID_INCLUSIVE
        assert current_clusteradmin.enabled == True

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize(
        "admin_username",
        [
            "admin1",
        ],
    )
    def test_email_templates_table_populated(
        self,
        request: FixtureRequest,
        admin: ClientAuth,
        res_environment: ResEnvironment,
    ) -> None:
        """
        Test email templates table has been populated with default values
        """
        api_invoker_type = request.config.getoption("--api-invoker-type")
        admin_client = ResClient(res_environment, admin, api_invoker_type)

        email_templates_list = admin_client.list_email_templates(
            request=ListEmailTemplatesRequest()
        ).listing
        default_template_names = [
            "virtual-desktop-controller.session-provisioning",
            "virtual-desktop-controller.session-creating",
            "virtual-desktop-controller.session-initializing",
            "virtual-desktop-controller.session-resuming",
            "virtual-desktop-controller.session-ready",
            "virtual-desktop-controller.session-stopping",
            "virtual-desktop-controller.session-stopped",
            "virtual-desktop-controller.session-deleting",
            "virtual-desktop-controller.session-error",
            "virtual-desktop-controller.session-deleted",
            "virtual-desktop-controller.session-shared",
            "virtual-desktop-controller.session-permission-updated",
            "virtual-desktop-controller.session-permission-expired",
        ]
        returned_template_names = [template.name for template in email_templates_list]
        for name in default_template_names:
            assert name in returned_template_names
        assert len(returned_template_names) == 13

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize(
        "admin_username",
        [
            "admin1",
        ],
    )
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="res-integ-test-soft-stack",
                    name="res-integ-test-soft-stack",
                    description="RES integ test project software stack",
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
        [(AL2_SOFTWARE_STACK, "project", "admin")],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "session",
        [
            (
                VirtualDesktopSession(
                    name="VirtualDesktop-soft-stack",
                    description="RES integ test VDI session",
                    hibernation_enabled=False,
                ),
                "project",
                "software_stack",
                "admin",
            )
        ],
        indirect=True,
    )
    def test_software_stack_creation(
        self,
        request: FixtureRequest,
        region: str,
        admin: ClientAuth,
        res_environment: ResEnvironment,
        project: Project,
        software_stack: VirtualDesktopSoftwareStack,
        session: Optional[VirtualDesktopSession],
    ) -> None:
        """
        Test the AL2 software stack creation from a session workflow:
            Launch VDI -> connect to VDI -> create software stack ->
            -> launch new VDI with that software stack -> connect to VDI
        """
        if not session:
            # VDI is not supported with the current configuration
            return

        api_invoker_type = request.config.getoption("--api-invoker-type")
        client = ResClient(res_environment, admin, api_invoker_type)
        web_driver = client.join_session(session)
        wait_for_session_connection_count(region, session, 1)
        logger.info(f"leaving session {session.dcv_session_id}...")
        web_driver.quit()

        new_software_stack = VirtualDesktopSoftwareStack(
            name="integ-test-created-software-stack-from-session",
            projects=[project],
            base_os=session.base_os,
            min_storage=session.software_stack.min_storage,
        )
        logger.info(f"New software stack {new_software_stack}")
        software_stack_create_request = CreateSoftwareStackFromSessionRequest(
            session=session,
            new_software_stack=new_software_stack,
        )

        software_stack_create_response = client.create_software_stack_from_session(
            request=software_stack_create_request
        )
        logger.info(f"Software stack create response {software_stack_create_response}")
        new_software_stack = software_stack_create_response.software_stack
        wait_for_software_stack_to_be_active(
            client=client, software_stack=software_stack_create_response.software_stack
        )
        created_stack = client.get_software_stack(
            request=GetSoftwareStackInfoRequest(
                stack_id=new_software_stack.stack_id, base_os=software_stack.base_os
            )
        ).software_stack
        logger.info(f"Created stack {created_stack}")
        try:
            logger.info(f"Creating session from software stack {created_stack.name}...")
            new_session = create_session(
                session=VirtualDesktopSession(
                    name="integ-test-created-session-from-created-software-stack",
                    description="RES integ test VDI session new software stack",
                    hibernation_enabled=False,
                    software_stack=created_stack,
                    project=project,
                ),
                software_stack=created_stack,
                client=client,
            )
            logger.info(f"Joining session {session.name}...")
            web_driver = client.join_session(new_session)

            logger.info(f"Connecting to dcv session {session.name}...")
            wait_for_session_connection_count(region, new_session, 1)

            logger.info(
                f"Leaving session {new_session.name} {new_session.dcv_session_id}..."  # type: ignore
            )
            web_driver.quit()
            wait_for_session_connection_count(region, new_session, 0)
        finally:
            delete_session(
                client=client,
                session=new_session,
            )
            client.delete_software_stack(
                request=DeleteSoftwareStackRequest(software_stack=created_stack)
            )
            deregistered = deregister_ami(created_stack.ami_id)
            if not deregistered:
                logger.error(f"AMI {created_stack.ami_id} could not be deregistered")

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize(
        "admin_username",
        [
            "admin1",
        ],
    )
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="res-integ-test-sssd-config-update",
                    name="res-integ-test-sssd-config-update",
                    description="RES integ test SSSD config update",
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
        [(AL2_SOFTWARE_STACK, "project", "admin")],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "session",
        [
            (
                VirtualDesktopSession(
                    name="VirtualDesktop-sssd-config-update",
                    description="RES integ test VDI session",
                    hibernation_enabled=False,
                ),
                "project",
                "software_stack",
                "admin",
            )
        ],
        indirect=True,
    )
    def test_additional_configs_update(
        self,
        request: FixtureRequest,
        region: str,
        admin: ClientAuth,
        res_environment: ResEnvironment,
        project: Project,
        software_stack: VirtualDesktopSoftwareStack,
        session: Optional[VirtualDesktopSession],
    ) -> None:
        """
        Test the end to end workflow for updating additional sssd configs:
        """

        if not session:
            # VDI is not supported with the current configuration
            return

        api_invoker_type = request.config.getoption("--api-invoker-type")
        admin_client = ResClient(res_environment, admin, api_invoker_type)
        debug_level_key = "debug_level"
        debug_level_value = "0xfff0"

        cluster_manager_instance_id = cluster_manager_instances(request.session)[0].get(
            "InstanceId", ""
        )
        vdi_instance_id = session.server.instance_id

        # Update additional_sssd_configs with debug_level = 0xfff0
        admin_client.update_module_settings(
            request=UpdateModuleSettingsRequest(
                module_id="directoryservice",
                settings={
                    "sssd": {
                        "additional_sssd_configs": json.dumps(
                            {debug_level_key: debug_level_value}
                        )
                    }
                },
            )
        )
        time.sleep(20)

        check_sssd_config_field(
            region,
            cluster_manager_instance_id,
            EC2InstancePlatform.LINUX,
            debug_level_key,
            debug_level_value,
        )
        check_sssd_config_field(
            region,
            vdi_instance_id,
            EC2InstancePlatform.LINUX,
            debug_level_key,
            debug_level_value,
        )

        # Update additional_sssd_configs back to empty
        admin_client.update_module_settings(
            request=UpdateModuleSettingsRequest(
                module_id="directoryservice",
                settings={"sssd": {"additional_sssd_configs": json.dumps({})}},
            )
        )
        time.sleep(20)

        check_sssd_config_field(
            region,
            cluster_manager_instance_id,
            EC2InstancePlatform.LINUX,
            "debug_level",
            "",
        )
        check_sssd_config_field(
            region, vdi_instance_id, EC2InstancePlatform.LINUX, "debug_level", ""
        )
