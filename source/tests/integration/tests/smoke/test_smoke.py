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
from typing import Any, Optional

import boto3
import pytest
from res.constants import CLUSTER_ADMIN_USERNAME  # type: ignore
from res.utils import auth_utils  # type: ignore
from res.utils import ssm_utils

# File-browser/module/user request types and Project still go through the
# not-yet-migrated cluster-manager API, so they stay ideadatamodel.
from ideadatamodel import (  # type: ignore
    CreateFileRequest,
    DeleteFilesRequest,
    DownloadFilesRequest,
    GetModuleSettingsRequest,
    GetUserRequest,
    ListEmailTemplatesRequest,
    ListFilesRequest,
    Project,
    ReadFileRequest,
    SaveFileRequest,
    TailFileRequest,
    UpdateModuleSettingsRequest,
)
from tests.integration.framework.client.api_client import (
    ApiClient,
    CreateSoftwareStackFromSessionRequestContent,
    DeleteSoftwareStackRequestContent,
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
    smart_retry_session,
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
from tests.integration.framework.utils.model_utils import get_backend_model_class
from tests.integration.framework.utils.session_utils import (
    wait_for_session_connection_count,
    wait_for_software_stack_to_be_active,
)
from tests.integration.framework.utils.sssd_utils import check_sssd_config_field
from tests.integration.tests.smoke.config import (
    AL2023_SOFTWARE_STACK,
    BASE_OS,
    LINUX_SOFTWARE_STACKS,
    MIN_LINUX_STORAGE,
    MIN_RAM,
    TEST_SOFTWARE_STACKS,
)

# Backend data-model classes (source/idea/data-model). The session/software-stack
# APIs consume and return these.
VirtualDesktopSession = get_backend_model_class(
    "virtual_desktop_session", "VirtualDesktopSession"
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

logger = logging.getLogger(__name__)


def _is_smoke_subset_stack(stack: Any) -> bool:
    """
    Whether a software stack belongs to the minimal per-commit smoke subset:
    the single AL2023 x86_64 OS. Matched on base_os + architecture (not object
    identity) so the selection survives config refactors that reconstruct the
    stack instead of referencing the AL2023_SOFTWARE_STACK constant.
    """
    return bool(
        stack.base_os == VirtualDesktopBaseOS.AMZN2023
        and stack.architecture == VirtualDesktopArchitecture.X86_64
    )


@pytest.mark.nightly
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
            pytest.param(
                (software_stack, "project", "admin"),
                # The single-OS AL2023 x86_64 entry is the minimal smoke subset.
                marks=(
                    [pytest.mark.smoke_subset]
                    if _is_smoke_subset_stack(software_stack)
                    else []
                ),
            )
            for software_stack in TEST_SOFTWARE_STACKS
        ],
        indirect=True,
        ids=[stack.name for stack in TEST_SOFTWARE_STACKS],  #
    )
    @pytest.mark.parametrize(
        "session",
        [
            (
                VirtualDesktopSession(
                    name="AD",
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
        software_stack: Any,
        session: Optional[Any],
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

        web_driver = ApiClient(res_environment, non_admin).join_session(
            session.idea_session_id, session.owner
        )
        wait_for_session_connection_count(session, 1)

        logger.info(f"leaving session {session.dcv_session_id}...")
        web_driver.quit()
        wait_for_session_connection_count(session, 0)

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
            pytest.param(
                (software_stack, "project", "cognito_admin"),
                # The single-OS AL2023 x86_64 entry is the minimal smoke subset.
                marks=(
                    [pytest.mark.smoke_subset]
                    if _is_smoke_subset_stack(software_stack)
                    else []
                ),
            )
            for software_stack in LINUX_SOFTWARE_STACKS
        ],
        indirect=True,
        ids=[stack.name for stack in LINUX_SOFTWARE_STACKS],
    )
    @pytest.mark.parametrize(
        "session",
        [
            (
                VirtualDesktopSession(
                    name="Cog",
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
        software_stack: Any,
        session: Optional[Any],
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

        web_driver = ApiClient(res_environment, cognito_admin).join_session(
            session.idea_session_id, session.owner
        )
        wait_for_session_connection_count(session, 1)

        logger.info(f"leaving session {session.dcv_session_id}...")
        web_driver.quit()
        wait_for_session_connection_count(session, 0)

    @pytest.mark.xdist_group("file_browser")
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

    @pytest.mark.xdist_group("file_browser")
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
    def test_file_browser_rejects_symlinks(
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
        Test that FileBrowser APIs reject symlink-based access attempts and
        that ListFiles skips symlinks and DeleteFiles removes only the symlink.
        """
        api_invoker_type = request.config.getoption("--api-invoker-type")
        admin_client = ResClient(res_environment, admin, api_invoker_type)
        non_admin_client = ResClient(res_environment, non_admin, api_invoker_type)

        admin_client.update_module_settings(
            request=UpdateModuleSettingsRequest(
                module_id="shared-storage",
                settings={"enable_file_browser": True},
            )
        )

        user_home = f"/home/{non_admin_username}"
        cluster_manager_instance_id = cluster_manager_instances(request.session)[0].get(
            "InstanceId", ""
        )

        def run_remote_command(commands: list[str]) -> str:
            result = ssm_utils.send_command(
                instance_ids=[cluster_manager_instance_id],
                commands=commands,
                base_os="linux",
                output_to_s3=False,
            )
            invocation = ssm_utils.wait_for_command(
                result["CommandId"], cluster_manager_instance_id
            )
            return str(invocation.get("StandardOutputContent", ""))

        test_id = str(uuid.uuid4())[:8]
        symlink_file = f"symlink_file_{test_id}.txt"
        symlink_dir = f"symlink_dir_{test_id}"
        regular_file = f"regular_file_{test_id}.txt"
        internal_link = f"internal_link_{test_id}.txt"

        try:
            run_remote_command(
                [
                    f"mkdir -p {user_home}",
                    f"chown {non_admin_username}: {user_home}",
                    f"echo 'regular content' > {user_home}/{regular_file}",
                    f"chown {non_admin_username}: {user_home}/{regular_file}",
                    f"ln -sf /etc/hostname {user_home}/{symlink_file}",
                    f"ln -sf /etc {user_home}/{symlink_dir}",
                ],
            )

            # Retry until the enable_file_browser setting is picked up by the cluster manager
            max_wait = 60
            poll_interval = 5
            start = time.time()
            while time.time() - start < max_wait:
                try:
                    non_admin_client.read_file(
                        request=ReadFileRequest(file=f"{user_home}/{symlink_file}"),
                        should_succeed=False,
                        expected_error_code="UNAUTHORIZED_ACCESS",
                    )
                    break
                except AssertionError as e:
                    if "DISABLED_FEATURE" in str(e):
                        time.sleep(poll_interval)
                    else:
                        raise
            else:
                pytest.fail("File browser config did not propagate within 60s")

            non_admin_client.tail_file(
                request=TailFileRequest(file=f"{user_home}/{symlink_file}"),
                should_succeed=False,
                expected_error_code="UNAUTHORIZED_ACCESS",
            )
            non_admin_client.save_file(
                request=SaveFileRequest(
                    file=f"{user_home}/{symlink_file}",
                    content=base64.b64encode(b"malicious").decode(),
                ),
                should_succeed=False,
                expected_error_code="UNAUTHORIZED_ACCESS",
            )
            non_admin_client.download_files(
                request=DownloadFilesRequest(files=[f"{user_home}/{symlink_file}"]),
                should_succeed=False,
                expected_error_code="UNAUTHORIZED_ACCESS",
            )
            non_admin_client.create_file(
                request=CreateFileRequest(
                    cwd=user_home,
                    filename=symlink_file,
                    is_folder=False,
                ),
                should_succeed=False,
                expected_error_code="INVALID_PARAMS",
            )

            non_admin_client.read_file(
                request=ReadFileRequest(file=f"{user_home}/{symlink_dir}/hostname"),
                should_succeed=False,
                expected_error_code="UNAUTHORIZED_ACCESS",
            )
            non_admin_client.tail_file(
                request=TailFileRequest(file=f"{user_home}/{symlink_dir}/hostname"),
                should_succeed=False,
                expected_error_code="UNAUTHORIZED_ACCESS",
            )
            non_admin_client.save_file(
                request=SaveFileRequest(
                    file=f"{user_home}/{symlink_dir}/hostname",
                    content=base64.b64encode(b"malicious").decode(),
                ),
                should_succeed=False,
                expected_error_code="UNAUTHORIZED_ACCESS",
            )
            non_admin_client.download_files(
                request=DownloadFilesRequest(
                    files=[f"{user_home}/{symlink_dir}/hostname"]
                ),
                should_succeed=False,
                expected_error_code="UNAUTHORIZED_ACCESS",
            )
            non_admin_client.create_file(
                request=CreateFileRequest(
                    cwd=f"{user_home}/{symlink_dir}/",
                    filename="newfile.txt",
                    is_folder=False,
                ),
                should_succeed=False,
                expected_error_code="UNAUTHORIZED_ACCESS",
            )

            list_response = non_admin_client.list_files(
                request=ListFilesRequest(cwd=user_home),
                should_succeed=True,
            )
            listed_names = [f.name for f in list_response.listing]
            assert (
                regular_file in listed_names
            ), f"Regular file {regular_file} should appear in listing"
            assert (
                symlink_file not in listed_names
            ), f"Symlink {symlink_file} should NOT appear in listing"
            assert (
                symlink_dir not in listed_names
            ), f"Symlink dir {symlink_dir} should NOT appear in listing"

            non_admin_client.delete_files(
                request=DeleteFilesRequest(files=[f"{user_home}/{symlink_file}"]),
                should_succeed=True,
            )
            non_admin_client.delete_files(
                request=DeleteFilesRequest(files=[f"{user_home}/{symlink_dir}/"]),
                should_succeed=True,
            )
            verify_output = run_remote_command(
                [
                    f"test -L {user_home}/{symlink_file} && echo FILE_LINK_EXISTS || echo FILE_LINK_GONE",
                    f"test -L {user_home}/{symlink_dir} && echo DIR_LINK_EXISTS || echo DIR_LINK_GONE",
                    "test -f /etc/hostname && echo TARGET_OK || echo TARGET_MISSING",
                    "test -d /etc && echo DIR_TARGET_OK || echo DIR_TARGET_MISSING",
                ],
            )
            assert "FILE_LINK_GONE" in verify_output
            assert "DIR_LINK_GONE" in verify_output
            assert "TARGET_OK" in verify_output
            assert "DIR_TARGET_OK" in verify_output

            internal_link = f"internal_link_{test_id}.txt"
            run_remote_command(
                [
                    f"ln -sf {user_home}/{regular_file} {user_home}/{internal_link}",
                    f"chown -h {non_admin_username}: {user_home}/{internal_link}",
                ],
            )

            non_admin_client.read_file(
                request=ReadFileRequest(file=f"{user_home}/{internal_link}"),
                should_succeed=True,
            )
            non_admin_client.tail_file(
                request=TailFileRequest(file=f"{user_home}/{internal_link}"),
                should_succeed=True,
            )

            list_response = non_admin_client.list_files(
                request=ListFilesRequest(cwd=user_home),
                should_succeed=True,
            )
            listed_names = [f.name for f in list_response.listing]
            assert (
                internal_link not in listed_names
            ), f"Internal symlink {internal_link} should NOT appear in listing"

            non_admin_client.delete_files(
                request=DeleteFilesRequest(files=[f"{user_home}/{internal_link}"]),
                should_succeed=True,
            )
            verify_output = run_remote_command(
                [
                    f"test -L {user_home}/{internal_link} && echo INTERNAL_LINK_EXISTS || echo INTERNAL_LINK_GONE",
                    f"test -f {user_home}/{regular_file} && echo REGULAR_FILE_OK || echo REGULAR_FILE_MISSING",
                ],
            )
            assert "INTERNAL_LINK_GONE" in verify_output
            assert "REGULAR_FILE_OK" in verify_output

        finally:
            run_remote_command(
                [
                    f"rm -f {user_home}/{symlink_file}",
                    f"rm -rf {user_home}/{symlink_dir}",
                    f"rm -f {user_home}/{regular_file}",
                    f"rm -f {user_home}/internal_link_{test_id}.txt",
                ],
            )

    @pytest.mark.smoke_subset
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
        api_client = ApiClient(res_environment, admin)
        for profile_id in ["admin_profile", "observer_profile"]:
            current_profile = api_client.get_permission_profile(
                profile_id=profile_id
            ).profile  # type: ignore
            assert current_profile is not None
            assert current_profile.profile_id == profile_id

    @pytest.mark.smoke_subset
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
        api_client = ApiClient(res_environment, admin)
        default_stack_count = 0
        stacks = api_client.list_software_stacks().listing  # type: ignore

        assert stacks is not None
        for stack in stacks:
            assert stack.base_os in BASE_OS
            assert stack.stack_id is not None
            assert stack.ami_id is not None
            stack_name = stack.name
            if not stack_name.startswith("res-integ-test-stack"):
                default_stack_count += 1
        assert default_stack_count > 0

    @pytest.mark.smoke_subset
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

    @pytest.mark.smoke_subset
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

    @pytest.mark.smoke_subset
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
        [(AL2023_SOFTWARE_STACK, "project", "admin")],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "session",
        [
            (
                VirtualDesktopSession(
                    name="sssd",
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
        software_stack: Any,
        session: Optional[Any],
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
            cluster_manager_instance_id,
            "linux",
            debug_level_key,
            debug_level_value,
        )
        check_sssd_config_field(
            vdi_instance_id,
            "linux",
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

        check_sssd_config_field(
            cluster_manager_instance_id,
            "linux",
            "debug_level",
            "",
        )
        check_sssd_config_field(vdi_instance_id, "linux", "debug_level", "")

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
        [
            (
                VirtualDesktopSoftwareStack(
                    name=f"res-integ-test-stack-creation-{VirtualDesktopBaseOS.AMZN2023.value}-{VirtualDesktopArchitecture.X86_64.value}",
                    description="RES integ test software stack creation",
                    base_os=VirtualDesktopBaseOS.AMZN2023,
                    architecture=VirtualDesktopArchitecture.X86_64,
                    min_storage=MIN_LINUX_STORAGE,
                    min_ram=MIN_RAM,
                    gpu=VirtualDesktopGPU.NO_GPU,
                    allowed_instance_types=["t3", "m6a"],
                ),
                "project",
                "admin",
            )
        ],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "session",
        [
            (
                VirtualDesktopSession(
                    name="stack",
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
        software_stack: Any,
        session: Optional[Any],
    ) -> None:
        """
        Test the AL2 software stack creation from a session workflow:
            Launch VDI -> connect to VDI -> create software stack ->
            -> launch new VDI with that software stack -> connect to VDI
        """
        if not session:
            # VDI is not supported with the current configuration
            return

        api_client = ApiClient(res_environment, admin)
        web_driver = api_client.join_session(session.idea_session_id, session.owner)
        wait_for_session_connection_count(session, 1)
        logger.info(f"leaving session {session.dcv_session_id}...")
        web_driver.quit()

        stack_name = (
            f"integ-test-created-software-stack-from-session-{str(uuid.uuid4())[:4]}"
        )
        software_stack_create_request = CreateSoftwareStackFromSessionRequestContent(
            session={
                "idea_session_id": session.idea_session_id,
                "owner": session.owner,
            },
            software_stack={
                "name": stack_name,
                "description": "integ-test-created-software-stack-from-session",
                "base_os": session.base_os.value,
                "min_storage": {
                    "value": software_stack.min_storage.value,
                    "unit": software_stack.min_storage.unit,
                },
                "min_ram": {"value": 2, "unit": "gb"},
                "ami_id": software_stack.ami_id,
                "gpu": (software_stack.gpu.value if software_stack.gpu else "NO_GPU"),
            },
        )

        logger.info(f"Creating software stack from session: {stack_name}")
        software_stack_create_response = api_client.create_software_stack_from_session(
            software_stack_create_request
        )
        logger.info(f"Software stack create response {software_stack_create_response}")
        new_software_stack = software_stack_create_response.software_stack  # type: ignore[attr-defined]
        new_session = None
        created_stack = None
        try:
            wait_for_software_stack_to_be_active(
                api_client=api_client,
                software_stack=software_stack_create_response.software_stack,  # type: ignore[attr-defined]
            )

            created_stack_response = api_client.get_software_stack(
                stack_id=new_software_stack.stack_id,
                base_os=software_stack.base_os.value,
            )
            if (
                created_stack_response is None
                or created_stack_response.software_stack is None
            ):
                raise Exception("Failed to get created software stack")
            created_stack = created_stack_response.software_stack

            project = created_stack.projects[0]
            project_dict = {
                "project_id": project.project_id,
                "name": project.name,
                "title": project.title,
            }

            logger.info(f"Creating session from software stack {created_stack.name}...")
            api_client = ApiClient(res_environment, admin)

            session_to_create = VirtualDesktopSession(
                name="integ-new-stack-sess",
                description="RES integ test VDI session new software stack",
                hibernation_enabled=False,
                software_stack_id=created_stack.stack_id,
                project=project_dict,
                base_os=created_stack.base_os,
            )

            new_session = create_session(
                session=session_to_create,
                software_stack=created_stack,
                api_client=api_client,
            )

            logger.info(f"Joining session {session.name}...")
            web_driver = api_client.join_session(
                new_session.idea_session_id, new_session.owner
            )

            logger.info(f"Connecting to dcv session {session.name}...")
            wait_for_session_connection_count(new_session, 1)

            logger.info(
                f"Leaving session {new_session.name} {new_session.dcv_session_id}..."
            )
            web_driver.quit()
            wait_for_session_connection_count(new_session, 0)
        finally:

            # Retrieve the created stack from the API to get the real AMI ID
            ami_to_deregister = ""
            try:
                fetched_stack = api_client.get_software_stack(
                    stack_id=new_software_stack.stack_id,
                    base_os=software_stack.base_os.value,
                )
                if fetched_stack and fetched_stack.software_stack:  # type: ignore
                    ami_to_deregister = fetched_stack.software_stack.ami_id or ""  # type: ignore
            except Exception as e:
                logger.warning(f"Failed to fetch created stack for AMI cleanup: {e}")

            if new_session:
                delete_session(
                    api_client=api_client,
                    session=new_session,
                )

            delete_request = DeleteSoftwareStackRequestContent(
                base_os=software_stack.base_os
            )
            api_client.delete_software_stack(
                stack_id=new_software_stack.stack_id, request_content=delete_request
            )

            logger.info(f"ami_to_deregister: {ami_to_deregister}")
            if ami_to_deregister:
                deregistered = deregister_ami(ami_to_deregister, region)
                if not deregistered:
                    logger.error(f"AMI {ami_to_deregister} could not be deregistered")


@pytest.mark.smart_retry
@pytest.mark.usefixtures("res_environment")
@pytest.mark.usefixtures("region")
class TestsSmartRetry(object):

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize("admin_username", ["admin1"])
    @pytest.mark.usefixtures("non_admin")
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="res-smart-retry-test"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="res-smart-retry-test"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES smart retry integ test project",
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
            (
                VirtualDesktopSoftwareStack(
                    name=f"res-smart-retry-stack-{VirtualDesktopBaseOS.AMZN2023.value}-{VirtualDesktopArchitecture.X86_64.value}",
                    description="RES smart retry integ test software stack",
                    base_os=VirtualDesktopBaseOS.AMZN2023,
                    architecture=VirtualDesktopArchitecture.X86_64,
                    min_storage=MIN_LINUX_STORAGE,
                    min_ram=MIN_RAM,
                    gpu=VirtualDesktopGPU.NO_GPU,
                    allowed_instance_types=["t3", "m6a"],
                ),
                "project",
                "admin",
            )
        ],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "smart_retry_session",
        [
            (
                VirtualDesktopSession(
                    name="SR",
                    description="RES smart retry integ test VDI session",
                    hibernation_enabled=False,
                ),
                "project",
                "software_stack",
                "non_admin",
            )
        ],
        indirect=True,
    )
    def test_smart_retry_vdi_launch_succeed(
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
        smart_retry_session: Optional[Any],
    ) -> None:
        """
        Test the VDI launch workflow with smart retry enabled:
        1. Enable smart retry on the environment.
        2. Create a session WITHOUT instance_type or subnet_id.
        3. Verify the session launches successfully (smart retry selects instance type and subnet).
        4. Join the session and verify connectivity.
        5. Clean up: delete session and disable smart retry.
        """
        if not smart_retry_session:
            return

        assert (
            smart_retry_session.server is not None
        ), "Session server info should be populated"
        assert (
            smart_retry_session.server.instance_type is not None
        ), "Smart retry should have selected an instance type"

        logger.info(
            f"Smart retry selected instance_type={smart_retry_session.server.instance_type}"
        )

        web_driver = ApiClient(res_environment, non_admin).join_session(
            smart_retry_session.idea_session_id, smart_retry_session.owner
        )
        wait_for_session_connection_count(smart_retry_session, 1)

        logger.info(f"leaving session {smart_retry_session.dcv_session_id}...")
        web_driver.quit()
        wait_for_session_connection_count(smart_retry_session, 0)
