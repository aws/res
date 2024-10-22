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
from abc import abstractmethod
from typing import Optional

import ideavirtualdesktopcontroller
from ideadatamodel import errorcodes
from ideadatamodel.exceptions import SocaException
from ideasdk.utils import Utils
from ideavirtualdesktopcontroller.app.app_protocols import VirtualDesktopQueueMessageHandlerProtocol
from ideavirtualdesktopcontroller.app.clients.dcv_broker_client.dcv_broker_client_utils import DCVBrokerClientUtils
from ideavirtualdesktopcontroller.app.clients.events_client.events_client import VirtualDesktopEvent
from ideavirtualdesktopcontroller.app.events.events_utils import EventsUtils
from ideavirtualdesktopcontroller.app.permission_profiles.virtual_desktop_permission_profile_db import VirtualDesktopPermissionProfileDB
from ideavirtualdesktopcontroller.app.schedules.virtual_desktop_schedule_db import VirtualDesktopScheduleDB
from ideavirtualdesktopcontroller.app.schedules.virtual_desktop_schedule_utils import VirtualDesktopScheduleUtils
from ideavirtualdesktopcontroller.app.servers.virtual_desktop_server_db import VirtualDesktopServerDB
from ideavirtualdesktopcontroller.app.servers.virtual_desktop_server_utils import VirtualDesktopServerUtils
from ideavirtualdesktopcontroller.app.session_permissions.virtual_desktop_session_permission_db import VirtualDesktopSessionPermissionDB
from ideavirtualdesktopcontroller.app.session_permissions.virtual_desktop_session_permission_utils import VirtualDesktopSessionPermissionUtils
from ideavirtualdesktopcontroller.app.sessions.virtual_desktop_session_counters_db import VirtualDesktopSessionCounterDB
from ideavirtualdesktopcontroller.app.sessions.virtual_desktop_session_db import VirtualDesktopSessionDB
from ideavirtualdesktopcontroller.app.sessions.virtual_desktop_session_utils import VirtualDesktopSessionUtils
from ideavirtualdesktopcontroller.app.software_stacks.virtual_desktop_software_stack_db import VirtualDesktopSoftwareStackDB
from ideavirtualdesktopcontroller.app.software_stacks.virtual_desktop_software_stack_utils import VirtualDesktopSoftwareStackUtils
from ideavirtualdesktopcontroller.app.ssm_commands.virtual_desktop_ssm_commands_db import VirtualDesktopSSMCommandsDB
from ideavirtualdesktopcontroller.app.ssm_commands.virtual_desktop_ssm_commands_utils import VirtualDesktopSSMCommandsUtils
from ideavirtualdesktopcontroller.app.virtual_desktop_controller_utils import VirtualDesktopControllerUtils


class BaseVirtualDesktopControllerEventHandler(VirtualDesktopQueueMessageHandlerProtocol):

    def __init__(self, context: ideavirtualdesktopcontroller.AppContext, logger_prefix: str):
        self.context = context
        self._logger = context.logger(logger_prefix)

        self.events_utils: EventsUtils = EventsUtils(context=self.context)
        self.controller_utils: VirtualDesktopControllerUtils = VirtualDesktopControllerUtils(context=self.context)
        self.software_stack_db: VirtualDesktopSoftwareStackDB = VirtualDesktopSoftwareStackDB(context=self.context)
        self.server_db: VirtualDesktopServerDB = VirtualDesktopServerDB(context=self.context)
        self.schedule_db: VirtualDesktopScheduleDB = VirtualDesktopScheduleDB(context=self.context)
        self.session_db: VirtualDesktopSessionDB = VirtualDesktopSessionDB(
            context=self.context,
            server_db=self.server_db,
            software_stack_db=self.software_stack_db,
            schedule_db=self.schedule_db)
        self.session_counter_db: VirtualDesktopSessionCounterDB = VirtualDesktopSessionCounterDB(context=self.context)
        self.ssm_commands_db: VirtualDesktopSSMCommandsDB = VirtualDesktopSSMCommandsDB(context=self.context)
        self.session_permissions_db: VirtualDesktopSessionPermissionDB = VirtualDesktopSessionPermissionDB(context=self.context)
        self.permission_profile_db: VirtualDesktopPermissionProfileDB = VirtualDesktopPermissionProfileDB(context=self.context)

        self.software_stack_utils: VirtualDesktopSoftwareStackUtils = VirtualDesktopSoftwareStackUtils(context=self.context, db=self.software_stack_db)
        self.server_utils: VirtualDesktopServerUtils = VirtualDesktopServerUtils(context=self.context, db=self.server_db)
        self.schedule_utils: VirtualDesktopScheduleUtils = VirtualDesktopScheduleUtils(context=self.context, db=self.schedule_db)
        self.ssm_commands_utils: VirtualDesktopSSMCommandsUtils = VirtualDesktopSSMCommandsUtils(context=self.context, db=self.ssm_commands_db)
        self.session_permission_utils: VirtualDesktopSessionPermissionUtils = VirtualDesktopSessionPermissionUtils(
            context=context,
            db=self.session_permissions_db,
            permission_profile_db=self.permission_profile_db
        )
        self.session_utils: VirtualDesktopSessionUtils = VirtualDesktopSessionUtils(
            context=self.context,
            db=self.session_db,
            session_permission_db=self.session_permissions_db,
            permission_profile_db=self.permission_profile_db
        )
        self.dcv_broker_client_utils: DCVBrokerClientUtils = DCVBrokerClientUtils(
            context=context,
            session_permission_utils=self.session_permission_utils,
        )

    @staticmethod
    def do_not_delete_message_exception(message: str):
        return SocaException(
            error_code=errorcodes.DO_NOT_DELETE_MESSAGE,
            message=message
        )

    @staticmethod
    def message_source_validation_failed(message: str):
        return SocaException(
            error_code=errorcodes.MESSAGE_SOURCE_VALIDATION_FAILED,
            message=message
        )

    def log_exception(self, message_id: str, exception: Exception):
        self._logger.exception(f'[msg-id: {message_id}] Exception: {exception}')

    def log_info(self, message_id: str, message: str):
        self._logger.info(f'[msg-id: {message_id}] {message}')

    def log_error(self, message_id: str, message: str):
        self._logger.error(f'[msg-id: {message_id}] {message}')

    def log_warning(self, message_id: str, message: str):
        self._logger.warning(f'[msg-id: {message_id}] {message}')

    def log_critical(self, message_id: str, message: str):
        self._logger.critical(f'[msg-id: {message_id}] {message}')

    def log_debug(self, message_id: str, message: str):
        self._logger.debug(f'[msg-id: {message_id}] {message}')

    @abstractmethod
    def handle_event(self, message_id: str, sender_id: str, event: VirtualDesktopEvent):
        ...

    @staticmethod
    def _retrieve_iam_role_id_from_sender(sender_id: str) -> Optional[str]:
        sender_id = sender_id.split(':')
        if Utils.is_empty(sender_id):
            return None
        return sender_id[0]

    @staticmethod
    def get_dcv_instance_id_from_sender_id(sender_id: str) -> Optional[str]:
        sender_id = sender_id.split(':')
        if Utils.is_empty(sender_id) or len(sender_id) < 2:
            return None
        return sender_id[1]

    def is_sender_dcv_host_role(self, sender_id: str) -> bool:
        sender_id = self._retrieve_iam_role_id_from_sender(sender_id)
        if Utils.is_empty(sender_id):
            return False
        return self.context.config().get_string('virtual-desktop-controller.dcv_host_role_id', required=True) == sender_id

    def is_sender_scheduled_event_lambda_role(self, sender_id: str) -> bool:
        sender_id = self._retrieve_iam_role_id_from_sender(sender_id)
        if Utils.is_empty(sender_id):
            return False
        return self.context.config().get_string('virtual-desktop-controller.scheduled_event_transformer_lambda_role_id', required=True) == sender_id

    def is_sender_dcv_broker_role(self, sender_id: str) -> bool:
        sender_id = self._retrieve_iam_role_id_from_sender(sender_id)
        if Utils.is_empty(sender_id):
            return False
        return self.context.config().get_string('virtual-desktop-controller.dcv_broker_role_id', required=True) == sender_id

    def is_sender_vdi_helper_lambda(self, sender_id: str) -> bool:
        sender_id = self._retrieve_iam_role_id_from_sender(sender_id)
        if not sender_id:
            return False
        return self.context.config().get_string('virtual-desktop-controller.vdi-helper-id', required=True) == sender_id


    def is_sender_controller_role(self, sender_id: str) -> bool:
        sender_id = self._retrieve_iam_role_id_from_sender(sender_id)
        if Utils.is_empty(sender_id):
            return False
        return self.context.config().get_string('virtual-desktop-controller.controller_iam_role_id', required=True) == sender_id
