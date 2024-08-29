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
from ideasdk.context import SocaContext, SocaContextOptions
from ideasdk.auth import TokenService, ApiAuthorizationServiceBase
from ideasdk.utils import GroupNameHelper
from ideasdk.client.vdc_client import AbstractVirtualDesktopControllerClient

from ideaclustermanager.app.authz.role_assignments_service import RoleAssignmentsService
from ideaclustermanager.app.authz.roles_service import RolesService
from ideaclustermanager.app.projects.projects_service import ProjectsService
from ideaclustermanager.app.accounts.accounts_service import AccountsService
from ideaclustermanager.app.adsync.adsync_service import ADSyncService
from ideaclustermanager.app.snapshots.snapshots_service import SnapshotsService
from ideaclustermanager.app.accounts.cognito_user_pool import CognitoUserPool
from ideaclustermanager.app.accounts.ldapclient import OpenLDAPClient, ActiveDirectoryClient
from ideaclustermanager.app.accounts.ad_automation_agent import ADAutomationAgent
from ideaclustermanager.app.email_templates.email_templates_service import EmailTemplatesService
from ideaclustermanager.app.notifications.notifications_service import NotificationsService
from ideaclustermanager.app.shared_filesystem.shared_filesystem_service import SharedFilesystemService
from ideaclustermanager.app.tasks.task_manager import TaskManager

from typing import Optional, Union


class ClusterManagerAppContext(SocaContext):

    def __init__(self, options: SocaContextOptions):
        super().__init__(
            options=options
        )

        self.token_service: Optional[TokenService] = None
        self.api_authorization_service: Optional[ApiAuthorizationServiceBase] = None
        self.roles: Optional[RolesService] = None
        self.role_assignments: Optional[RoleAssignmentsService] = None
        self.projects: Optional[ProjectsService] = None
        self.user_pool: Optional[CognitoUserPool] = None
        self.ldap_client: Optional[Union[OpenLDAPClient, ActiveDirectoryClient]] = None
        self.accounts: Optional[AccountsService] = None
        self.task_manager: Optional[TaskManager] = None
        self.ad_automation_agent: Optional[ADAutomationAgent] = None
        self.email_templates: Optional[EmailTemplatesService] = None
        self.notifications: Optional[NotificationsService] = None
        self.group_name_helper: Optional[GroupNameHelper] = None
        self.snapshots: Optional[SnapshotsService] = None
        self.ad_sync: Optional[ADSyncService] = None
        self.vdc_client: Optional[AbstractVirtualDesktopControllerClient] = None
        self.shared_filesystem: Optional[SharedFilesystemService]
