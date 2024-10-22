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
import logging
import os
import uuid
from typing import Optional

import pytest

from ideadatamodel import (  # type: ignore
    CreateFileRequest,
    CreateSessionRequest,
    DeleteFilesRequest,
    DeleteSessionRequest,
    DownloadFilesRequest,
    GetModuleSettingsRequest,
    ListFilesRequest,
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
from tests.integration.framework.fixtures.session import session
from tests.integration.framework.fixtures.software_stack import software_stack
from tests.integration.framework.fixtures.users.admin import admin
from tests.integration.framework.fixtures.users.non_admin import non_admin
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.session_utils import (
    wait_for_session_connection_count,
)
from tests.integration.tests.config import TEST_SOFTWARE_STACKS

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
            )
        ],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "software_stack",
        [
            (
                software_stack,
                "project",
            )
            for software_stack in TEST_SOFTWARE_STACKS
        ],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "session",
        [
            (
                VirtualDesktopSession(
                    name="VirtualDesktop" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES integ test VDI session",
                    hibernation_enabled=False,
                ),
                "project",
                "software_stack",
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
