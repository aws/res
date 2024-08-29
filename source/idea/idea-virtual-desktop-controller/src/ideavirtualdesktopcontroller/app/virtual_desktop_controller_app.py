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
from ideadatamodel import constants
from ideasdk.client import NotificationsAsyncClient, ProjectsClient, SocaClientOptions, AccountsClient, RolesClient, RoleAssignmentsClient
from ideasdk.utils import Utils, GroupNameHelper
from ideasdk.auth import TokenService, TokenServiceOptions
from ideasdk.server import SocaServerOptions

import ideavirtualdesktopcontroller
from ideavirtualdesktopcontroller.app.api import VirtualDesktopApiInvoker
from ideavirtualdesktopcontroller.app.clients.dcv_broker_client.dcv_broker_client import DCVBrokerClient
from ideavirtualdesktopcontroller.app.clients.events_client.events_client import EventsClient
from ideavirtualdesktopcontroller.app.events.service.controller_queue_monitor_service import ControllerQueueMonitorService
from ideavirtualdesktopcontroller.app.events.service.event_queue_monitoring_service import EventsQueueMonitoringService
from ideavirtualdesktopcontroller.app.permission_profiles.virtual_desktop_permission_profile_db import VirtualDesktopPermissionProfileDB
from ideavirtualdesktopcontroller.app.schedules.virtual_desktop_schedule_db import VirtualDesktopScheduleDB
from ideavirtualdesktopcontroller.app.servers.virtual_desktop_server_db import VirtualDesktopServerDB
from ideavirtualdesktopcontroller.app.session_permissions.virtual_desktop_session_permission_db import VirtualDesktopSessionPermissionDB
from ideavirtualdesktopcontroller.app.sessions.virtual_desktop_session_counters_db import VirtualDesktopSessionCounterDB
from ideavirtualdesktopcontroller.app.sessions.virtual_desktop_session_db import VirtualDesktopSessionDB
from ideavirtualdesktopcontroller.app.software_stacks.virtual_desktop_software_stack_db import VirtualDesktopSoftwareStackDB
from ideavirtualdesktopcontroller.app.ssm_commands.virtual_desktop_ssm_commands_db import VirtualDesktopSSMCommandsDB
from ideavirtualdesktopcontroller.app.auth.api_authorization_service import VdcApiAuthorizationService

import os
import yaml


class VirtualDesktopControllerApp(ideasdk.app.SocaApp):
    """
    virtual desktop app
    """

    def __init__(self, context: ideavirtualdesktopcontroller.AppContext,
                 config_file: str,
                 env_file: str = None,
                 config_overrides_file: str = None,
                 validation_level: int = constants.CONFIG_LEVEL_CRITICAL,
                 **kwargs):

        api_path_prefix = context.config().get_string('virtual-desktop-controller.server.api_context_path', f'/{context.module_id()}')
        super().__init__(
            context=context,
            config_file=config_file,
            api_invoker=VirtualDesktopApiInvoker(context=context),
            env_file=env_file,
            config_overrides_file=config_overrides_file,
            validation_level=validation_level,
            server_options=SocaServerOptions(
                api_path_prefixes=[api_path_prefix],
                enable_metrics=True
            ),
            **kwargs
        )
        self.context = context

    def app_initialize(self):
        self._initialize_clients()
        self._initialize_dbs()
        self._initialize_services()

    def _initialize_dbs(self):
        self._session_counter_db = VirtualDesktopSessionCounterDB(self.context).initialize()
        self._ssm_commands_db = VirtualDesktopSSMCommandsDB(self.context).initialize()
        self._server_db = VirtualDesktopServerDB(self.context).initialize()
        self._software_stack_db = VirtualDesktopSoftwareStackDB(self.context).initialize()
        self._schedule_db = VirtualDesktopScheduleDB(self.context).initialize()
        self._session_db = VirtualDesktopSessionDB(
            context=self.context,
            server_db=self._server_db,
            software_stack_db=self._software_stack_db,
            schedule_db=self._schedule_db
        ).initialize()
        self._permission_profile_db = VirtualDesktopPermissionProfileDB(self.context).initialize()
        self._session_permissions_db = VirtualDesktopSessionPermissionDB(self.context).initialize()

    def _initialize_clients(self):
        group_name_helper = GroupNameHelper(self.context)
        provider_url = self.context.config().get_string('identity-provider.cognito.provider_url', required=True)
        domain_url = self.context.config().get_string('identity-provider.cognito.domain_url', required=True)
        administrators_group_name = group_name_helper.get_cluster_administrators_group()
        managers_group_name = group_name_helper.get_cluster_managers_group()
        cluster_manager_module_id = self.context.config().get_module_id(constants.MODULE_CLUSTER_MANAGER)

        client_id = self.context.config().get_secret('virtual-desktop-controller.client_id', required=True)
        client_secret = self.context.config().get_secret('virtual-desktop-controller.client_secret', required=True)

        self.context.token_service = TokenService(
            context=self.context,
            options=TokenServiceOptions(
                cognito_user_pool_provider_url=provider_url,
                cognito_user_pool_domain_url=domain_url,
                client_id=client_id,
                client_secret=client_secret,
                client_credentials_scope=[
                    'dcv-session-manager/sm_scope',
                    f'{cluster_manager_module_id}/read'
                ],
                administrators_group_name=administrators_group_name,
                managers_group_name=managers_group_name
            )
        )

        internal_endpoint = self.context.config().get_cluster_internal_endpoint()
        self.context.projects_client = ProjectsClient(
            context=self.context,
            options=SocaClientOptions(
                endpoint=f'{internal_endpoint}/{cluster_manager_module_id}/api/v1',
                enable_logging=False,
                verify_ssl=False
            ),
            token_service=self.context.token_service
        )
        self.context.accounts_client = AccountsClient(
            context=self.context,
            options=SocaClientOptions(
                endpoint=f'{internal_endpoint}/{cluster_manager_module_id}/api/v1',
                enable_logging=False,
                verify_ssl=False
            ),
            token_service=self.context.token_service
        )
        self.context.roles_client = RolesClient(
            context=self.context,
            options=SocaClientOptions(
                endpoint=f'{internal_endpoint}/{cluster_manager_module_id}/api/v1',
                enable_logging=False,
                verify_ssl=False
            ),
            token_service=self.context.token_service
        )
        self.context.role_assignments_client = RoleAssignmentsClient(
            context=self.context,
            options=SocaClientOptions(
                endpoint=f'{internal_endpoint}/{cluster_manager_module_id}/api/v1',
                enable_logging=False,
                verify_ssl=False
            ),
            token_service=self.context.token_service
        )
        
        self.context.api_authorization_service = VdcApiAuthorizationService(
            accounts_client=self.context.accounts_client,
            token_service= self.context.token_service,
            roles_client=self.context.roles_client,
            role_assignments_client=self.context.role_assignments_client
        )

        self.context.notification_async_client = NotificationsAsyncClient(context=self.context)
        self.context.events_client = EventsClient(context=self.context)
        self.context.dcv_broker_client = DCVBrokerClient(context=self.context)

    def _initialize_services(self):
        self.context.event_queue_monitor_service = EventsQueueMonitoringService(context=self.context)
        self.context.controller_queue_monitor_service = ControllerQueueMonitorService(context=self.context)

    def app_start(self):
        self.context.event_queue_monitor_service.start()
        self.context.controller_queue_monitor_service.start()

    def app_stop(self):
        if Utils.is_not_empty(self.context.event_queue_monitor_service):
            self.context.event_queue_monitor_service.stop()

        if Utils.is_not_empty(self.context.controller_queue_monitor_service):
            self.context.controller_queue_monitor_service.stop()

        if Utils.is_not_empty(self.context.projects_client):
            self.context.projects_client.destroy()
