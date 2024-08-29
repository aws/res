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
import os
from pathlib import Path
from typing import Optional

from ideadatamodel import constants
from ideasdk.auth import TokenService, ApiAuthorizationServiceBase
from ideasdk.client import NotificationsAsyncClient, ProjectsClient, AccountsClient, RolesClient, RoleAssignmentsClient
from ideasdk.context import SocaContext, SocaContextOptions
from ideasdk.service import SocaService
from ideasdk.utils import Utils, EnvironmentUtils
from ideavirtualdesktopcontroller.app.app_protocols import DCVClientProtocol
from ideavirtualdesktopcontroller.app.clients.events_client.events_client import EventsClient


class VirtualDesktopControllerAppContext(SocaContext):

    def __init__(self, options: SocaContextOptions):
        super().__init__(
            options=options
        )

        self.token_service: Optional[TokenService] = None
        self.api_authorization_service: Optional[ApiAuthorizationServiceBase] = None
        self.dcv_broker_client: Optional[DCVClientProtocol] = None
        self.event_queue_monitor_service: Optional[SocaService] = None
        self.controller_queue_monitor_service: Optional[SocaService] = None
        self.projects_client: Optional[ProjectsClient] = None
        self.roles_client: Optional[RolesClient] = None
        self.role_assignments_client: Optional[RoleAssignmentsClient] = None
        self.accounts_client: Optional[AccountsClient] = None

        self.notification_async_client: Optional[NotificationsAsyncClient] = None
        self.events_client: Optional[EventsClient] = None
        self.sessions_template_version: Optional[int] = None
        self.software_stack_template_version: Optional[int] = None
        self.session_permission_template_version: Optional[int] = None

    @staticmethod
    def env_app_deploy_dir() -> str:
        return EnvironmentUtils.idea_app_deploy_dir(required=True)

    def get_resources_dir(self) -> str:
        if Utils.is_true(EnvironmentUtils.idea_dev_mode(), False):
            # this is for debugging support on IDE.
            script_dir = Path(os.path.abspath(__file__))
            vdc_project_dir = script_dir.parent.parent.parent.parent
            return os.path.join(vdc_project_dir, 'resources')
        else:
            return os.path.join(self.env_app_deploy_dir(), constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER, 'resources')

    def get_bootstrap_dir(self) -> str:
        if Utils.is_true(EnvironmentUtils.idea_dev_mode(), False):
            script_dir = Path(os.path.abspath(__file__))
            idea_source_dir = script_dir.parent.parent.parent.parent.parent
            return os.path.join(idea_source_dir, 'idea-bootstrap')
        else:
            return os.path.join(self.get_resources_dir(), 'bootstrap')
