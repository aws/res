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

import ideasdk.app
from ideasdk.auth import TokenService, TokenServiceOptions
from ideadatamodel import constants
from ideasdk.client.evdi_client import EvdiClient
from ideasdk.server import SocaServerOptions
from ideasdk.utils import GroupNameHelper
from ideasdk.client.vdc_client import SocaClientOptions, VirtualDesktopControllerClient

import ideaclustermanager
from ideaclustermanager.app.api.api_invoker import ClusterManagerApiInvoker
from ideaclustermanager.app.projects.projects_service import ProjectsService
from ideaclustermanager.app.accounts.accounts_service import AccountsService
from ideaclustermanager.app.adsync.adsync_service import ADSyncService
from ideaclustermanager.app.accounts.cognito_user_pool import CognitoUserPool, CognitoUserPoolOptions

from ideaclustermanager.app.accounts.ldapclient.ldap_client_factory import build_ldap_client
from ideaclustermanager.app.auth.api_authorization_service import ClusterManagerApiAuthorizationService
from ideaclustermanager.app.authz.roles_service import RolesService
from ideaclustermanager.app.authz.role_assignments_service import RoleAssignmentsService
from ideaclustermanager.app.accounts.ad_automation_agent import ADAutomationAgent
from ideaclustermanager.app.accounts.account_tasks import (
    SyncUserInDirectoryServiceTask,
    CreateUserHomeDirectoryTask,
    SyncGroupInDirectoryServiceTask
)
from ideaclustermanager.app.adsync.adsync_tasks import (
    SyncAllGroupsTask,
    SyncAllUsersTask,
    SyncFromAD
)
from ideaclustermanager.app.tasks.task_manager import TaskManager
from ideaclustermanager.app.web_portal import WebPortal
from ideaclustermanager.app.email_templates.email_templates_service import EmailTemplatesService
from ideaclustermanager.app.notifications.notifications_service import NotificationsService
from ideaclustermanager.app.snapshots.snapshots_service import SnapshotsService
from ideaclustermanager.app.shared_filesystem.shared_filesystem_service import SharedFilesystemService

from typing import Optional


class ClusterManagerApp(ideasdk.app.SocaApp):
    """
    cluster manager app
    """

    def __init__(self, context: ideaclustermanager.AppContext,
                 config_file: str,
                 env_file: str = None,
                 config_overrides_file: str = None,
                 validation_level: int = constants.CONFIG_LEVEL_CRITICAL,
                 **kwargs):

        api_path_prefix = context.config().get_string('cluster-manager.server.api_context_path', f'/{context.module_id()}')
        super().__init__(
            context=context,
            config_file=config_file,
            api_invoker=ClusterManagerApiInvoker(context=context),
            env_file=env_file,
            config_overrides_file=config_overrides_file,
            validation_level=validation_level,
            server_options=SocaServerOptions(
                api_path_prefixes=[
                    api_path_prefix
                ],
                enable_http_file_upload=True,
                enable_metrics=True
            ),
            **kwargs
        )
        self.context = context
        self.web_portal: Optional[WebPortal] = None

    def app_initialize(self):

        # group name helper
        self.context.group_name_helper = GroupNameHelper(self.context)
        administrators_group_name = self.context.group_name_helper.get_cluster_administrators_group()
        managers_group_name = self.context.group_name_helper.get_cluster_managers_group()

        # token service
        domain_url = self.context.config().get_string('identity-provider.cognito.domain_url', required=True)
        provider_url = self.context.config().get_string('identity-provider.cognito.provider_url', required=True)
        client_id = self.context.config().get_secret('cluster-manager.client_id', required=True)
        client_secret = self.context.config().get_secret('cluster-manager.client_secret', required=True)
        vdc_module_id = self.context.config().get_module_id(constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER)
        self.context.token_service = TokenService(
            context=self.context,
            options=TokenServiceOptions(
                cognito_user_pool_provider_url=provider_url,
                cognito_user_pool_domain_url=domain_url,
                client_id=client_id,
                client_secret=client_secret,
                client_credentials_scope=[
                    f'{vdc_module_id}/read',
                    f'{vdc_module_id}/write',
                ],
                administrators_group_name=administrators_group_name,
                managers_group_name=managers_group_name
            )
        )

        # cognito user pool
        user_pool_id = self.context.config().get_string('identity-provider.cognito.user_pool_id', required=True)
        self.context.user_pool = CognitoUserPool(
            context=self.context,
            options=CognitoUserPoolOptions(
                user_pool_id=user_pool_id,
                admin_group_name=administrators_group_name,
                client_id=client_id,
                client_secret=client_secret
            )
        )

        # accounts service
        ds_provider = self.context.config().get_string('directoryservice.provider', required=True)
        self.context.ldap_client = build_ldap_client(self.context)

        if ds_provider in {constants.DIRECTORYSERVICE_AWS_MANAGED_ACTIVE_DIRECTORY, constants.DIRECTORYSERVICE_ACTIVE_DIRECTORY}:
            self.context.ad_automation_agent = ADAutomationAgent(
                context=self.context,
                ldap_client=self.context.ldap_client
            )

        # task manager
        self.context.task_manager = TaskManager(
            context=self.context,
            tasks=[
                SyncUserInDirectoryServiceTask(self.context),
                SyncGroupInDirectoryServiceTask(self.context),
                CreateUserHomeDirectoryTask(self.context),
                SyncAllGroupsTask(self.context),
                SyncAllUsersTask(self.context),
                SyncFromAD(self.context)
            ]
        )

        # account service
        evdi_client = EvdiClient(self.context)
        self.context.accounts = AccountsService(
            context=self.context,
            ldap_client=self.context.ldap_client,
            user_pool=self.context.user_pool,
            task_manager=self.context.task_manager,
            evdi_client=evdi_client,
            token_service=self.context.token_service
        )

        # roles service
        self.context.roles = RolesService(
            context=self.context
        )

        # role assignments service
        self.context.role_assignments = RoleAssignmentsService(
            context=self.context
        )

        #api authorization service
        self.context.api_authorization_service = ClusterManagerApiAuthorizationService(accounts=self.context.accounts, roles=self.context.roles, role_assignments=self.context.role_assignments)

        # adsync service
        self.context.ad_sync = ADSyncService(
            context=self.context,
            task_manager=self.context.task_manager,
        )

        internal_endpoint = self.context.config().get_cluster_internal_endpoint()
        self.context.vdc_client = VirtualDesktopControllerClient(
                context=self.context,
                options=SocaClientOptions(
                    endpoint=f'{internal_endpoint}/{vdc_module_id}/api/v1',
                    enable_logging=False,
                    verify_ssl=False),
                token_service=self.context.token_service
            )

        self.context.snapshots = SnapshotsService(
            context=self.context
        )

        # projects service
        self.context.projects = ProjectsService(
            context=self.context,
            accounts_service=self.context.accounts,
            task_manager=self.context.task_manager,
            vdc_client=self.context.vdc_client
        )

        # email templates
        self.context.email_templates = EmailTemplatesService(
            context=self.context
        )

        # notifications
        self.context.notifications = NotificationsService(
            context=self.context,
            accounts=self.context.accounts,
            email_templates=self.context.email_templates
        )

        self.context.shared_filesystem = SharedFilesystemService(
            context=self.context
        )

        # web portal
        self.web_portal = WebPortal(
            context=self.context,
            server=self.server
        )
        self.web_portal.initialize()

    def app_start(self):
        if self.context.ad_automation_agent is not None:
            self.context.ad_automation_agent.start()

        self.context.task_manager.start()
        self.context.notifications.start()

        try:
            self.context.distributed_lock().acquire(key='initialize-defaults')
            self.context.accounts.create_defaults()
            self.context.roles.create_defaults()
            self.context.email_templates.create_defaults()
            self.context.ad_sync.sync_from_ad()  # submit ad_sync task after creation of defaults
        finally:
            self.context.distributed_lock().release(key='initialize-defaults')

    def app_stop(self):

        if self.context.ad_automation_agent is not None:
            self.context.ad_automation_agent.stop()

        if self.context.task_manager is not None:
            self.context.task_manager.stop()

        if self.context.notifications is not None:
            self.context.notifications.stop()
