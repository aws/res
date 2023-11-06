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

from typing import Dict

import ideavirtualdesktopcontroller
from ideadatamodel import Notification
from ideasdk.utils import Utils
from ideavirtualdesktopcontroller.app.clients.events_client.events_client import VirtualDesktopEvent
from ideavirtualdesktopcontroller.app.events.handlers.db_entry_event_handlers.base_db_event_handler import BaseDBEventHandler


class DbEntryCreatedEventHandler(BaseDBEventHandler):
    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        super().__init__(context, 'db-entry-created-handler')

        self.DETAIL_TYPE_TYPE_DB_ENTRY_CREATED_HANDLER: Dict[str, ()] = {
            self.software_stack_db.table_name: self._handle_software_stack_created,
            self.schedule_db.table_name: self._handle_schedule_created,
            self.session_db.table_name: self._handle_user_session_created,
            self.server_db.table_name: self._handle_dcv_host_created,
            self.session_permissions_db.table_name: self._handle_session_permission_created,
            self.permission_profile_db.table_name: self._handle_permission_profile_created
        }

    def _handle_software_stack_created(self, _: str, __: str, new_value: dict, ___: str):
        software_stack = self.software_stack_db.convert_db_dict_to_software_stack_object(new_value)
        self.software_stack_utils.index_software_stack_entry_to_opensearch(software_stack)

    def _handle_user_session_created(self, _: str, __: str, new_value: dict, ___: str):
        session = self.session_db.convert_db_dict_to_session_object(new_value)
        self._notify_session_owner_of_state_update(session)
        self.session_utils.index_session_entry_to_opensearch(session=session)

    def _handle_permission_profile_created(self, _: str, __: str, ___: dict, table_name: str):
        self._logger.debug(f'created entry for {table_name} not handled. No=OP. Returning')

    def _handle_schedule_created(self, _: str, __: str, ___: dict, table_name: str):
        self._logger.debug(f'created entry for {table_name} not handled. No=OP. Returning')

    def _handle_dcv_host_created(self, _: str, __: str, ___: dict, table_name: str):
        self._logger.debug(f'created entry for {table_name} not handled. No=OP. Returning')

    def _handle_session_permission_created(self, _: str, __: str, new_value: dict, ___: str):
        session_permission = self.session_permissions_db.convert_db_dict_to_session_permission_object(new_value)
        self.session_permission_utils.index_session_permission_to_opensearch(session_permission=session_permission)

        notifications_enabled = self.context.config().get_bool('virtual-desktop-controller.dcv_session.notifications.session-shared.enabled', required=True)
        if not notifications_enabled:
            return

        self.context.notification_async_client.send_notification(Notification(
            username=session_permission.actor_name,
            template_name=self.context.config().get_string('virtual-desktop-controller.dcv_session.notifications.session-shared.email_template', required=True),
            params={
                'cluster_name': self.context.cluster_name(),
                'session_permission': session_permission,
                'url': f'{self.context.config().get_cluster_external_endpoint()}/#/home/shared-desktops',
                'formatted_expiry_date': session_permission.expiry_date.strftime("%B %d, %Y at %I:%M %p")
            }
        ))

    def handle_event(self, message_id: str, sender_id: str, event: VirtualDesktopEvent):
        if not self.is_sender_controller_role(sender_id):
            raise self.message_source_validation_failed(f'Corrupted sender_id: {sender_id}. Ignoring message')

        table_name = Utils.get_value_as_string('table_name', event.detail, None)
        hash_key = Utils.get_value_as_string('hash_key', event.detail, '')
        range_key = Utils.get_value_as_string('range_key', event.detail, '')
        new_value = Utils.get_value_as_dict('new_value', event.detail, {})
        self.log_info(message_id=message_id, message=f'table name = {table_name}')
        self.DETAIL_TYPE_TYPE_DB_ENTRY_CREATED_HANDLER[table_name](hash_key, range_key, new_value, table_name)
