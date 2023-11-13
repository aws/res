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
from ideadatamodel import ListSessionsRequest, SocaFilter, Notification, ListPermissionsRequest
from ideasdk.utils import Utils
from ideavirtualdesktopcontroller.app.clients.events_client.events_client import VirtualDesktopEvent
from ideavirtualdesktopcontroller.app.events.handlers.db_entry_event_handlers.base_db_event_handler import BaseDBEventHandler
from ideavirtualdesktopcontroller.app.session_permissions.constants import SESSION_PERMISSIONS_FILTER_PERMISSION_PROFILE_ID_KEY
from ideavirtualdesktopcontroller.app.sessions.constants import USER_SESSION_DB_FILTER_SOFTWARE_STACK_ID_KEY


class DbEntryUpdatedEventHandler(BaseDBEventHandler):
    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        super().__init__(context, 'db-entry-updated-handler')

        self.DETAIL_TYPE_TYPE_DB_ENTRY_UPDATED_HANDLER: Dict[str, ()] = {
            self.software_stack_db.table_name: self._handle_software_stack_updated,
            self.schedule_db.table_name: self._handle_schedule_updated,
            self.session_db.table_name: self._handle_user_session_updated,
            self.server_db.table_name: self._handle_dcv_host_updated,
            self.session_permissions_db.table_name: self._handle_session_permission_updated,
            self.permission_profile_db.table_name: self._handle_permission_profile_updated
        }

    def _handle_software_stack_updated(self, _: str, __: str, old_value: dict, new_value: dict, ___: str):
        new_software_stack = self.software_stack_db.convert_db_dict_to_software_stack_object(new_value)
        self.software_stack_utils.update_software_stack_entry_to_opensearch(new_software_stack)

        old_software_stack = self.software_stack_db.convert_db_dict_to_software_stack_object(old_value)
        if new_software_stack.name != old_software_stack.name or new_software_stack.description != old_software_stack.description:

            idea_session_info = set()
            request = ListSessionsRequest()
            request.add_filter(SocaFilter(
                key=USER_SESSION_DB_FILTER_SOFTWARE_STACK_ID_KEY,
                value=new_software_stack.stack_id
            ))
            response = self.session_db.list_from_index(request)
            for session in response.listing:
                idea_session_info.add((session.idea_session_id, session.owner))

            for entry in idea_session_info:
                self.events_utils.publish_idea_session_software_stack_updated_event(
                    idea_session_id=entry[0],
                    idea_session_owner=entry[1],
                    new_software_stack=new_value
                )

    def _handle_schedule_updated(self, _: str, __: str, ___: dict, ____: dict, table_name: str):
        self._logger.debug(f'updated entry for {table_name} not handled. No=OP. Returning')

    def _handle_user_session_updated(self, _: str, __: str, old_value: dict, new_value: dict, ___: str):
        new_session = self.session_db.convert_db_dict_to_session_object(new_value)
        self.session_utils.update_session_entry_to_opensearch(new_session)

        old_session = self.session_db.convert_db_dict_to_session_object(old_value)
        publish_permission_update_event = False
        if old_session.state != new_session.state:
            publish_permission_update_event = True
            self._notify_session_owner_of_state_update(new_session)

        if old_session.name != new_session.name:
            publish_permission_update_event = True

        if Utils.is_not_empty(old_session.server) and Utils.is_not_empty(new_session.server) and old_session.server.instance_type != new_session.server.instance_type:
            publish_permission_update_event = True

        if publish_permission_update_event:
            self.events_utils.publish_update_session_permissions_event(
                idea_session_id=new_session.idea_session_id,
                new_instance_type=None if Utils.is_empty(new_session.server) else new_session.server.instance_type,
                new_name=new_session.name,
                new_state=new_session.state
            )

    def _handle_dcv_host_updated(self, _: str, __: str, ___: dict, ____: dict, table_name: str):
        self._logger.debug(f'updated entry for {table_name} not handled. No=OP. Returning')

    def _handle_permission_profile_updated(self, _: str, __: str, old_value: dict, new_value: dict, ___: str):
        new_permission_profile = self.permission_profile_db.convert_db_dict_to_permission_profile_object(new_value)
        old_permission_profile = self.permission_profile_db.convert_db_dict_to_permission_profile_object(old_value)
        is_permission_updated = False

        for new_permission in new_permission_profile.permissions:
            for old_permission in old_permission_profile.permissions:
                if new_permission.key == old_permission.key and new_permission.enabled != old_permission.enabled:
                    is_permission_updated = True
                    break
            if is_permission_updated:
                break

        if is_permission_updated:
            response = self.session_permissions_db.list_from_index(ListPermissionsRequest(
                filters=[SocaFilter(
                    key=SESSION_PERMISSIONS_FILTER_PERMISSION_PROFILE_ID_KEY,
                    value=new_permission_profile.profile_id
                )]
            ))
            idea_session_info = set()
            for permission in response.listing:
                idea_session_info.add((permission.idea_session_id, permission.idea_session_owner))

            for idea_session in idea_session_info:
                self.events_utils.publish_enforce_session_permissions_event(
                    idea_session_id=idea_session[0],
                    idea_session_owner=idea_session[1]
                )

    def _handle_session_permission_updated(self, _: str, __: str, old_value: dict, new_value: dict, ___: str):
        new_session_permission = self.session_permissions_db.convert_db_dict_to_session_permission_object(new_value)
        self.session_permission_utils.update_session_entry_to_opensearch(new_session_permission)

        notifications_enabled = self.context.config().get_bool('virtual-desktop-controller.dcv_session.notifications.session-permission-updated.enabled', required=True)
        if not notifications_enabled:
            return

        old_session_permission = self.session_permissions_db.convert_db_dict_to_session_permission_object(old_value)
        if new_session_permission.permission_profile.profile_id != old_session_permission.permission_profile.profile_id or new_session_permission.expiry_date != old_session_permission.expiry_date:
            self.context.notification_async_client.send_notification(Notification(
                username=new_session_permission.actor_name,
                template_name=self.context.config().get_string('virtual-desktop-controller.dcv_session.notifications.session-permission-updated.email_template', required=True),
                params={
                    'cluster_name': self.context.cluster_name(),
                    'session_permission': new_session_permission,
                    'url': f'{self.context.config().get_cluster_external_endpoint()}/#/home/shared-desktops',
                    'formatted_expiry_date': new_session_permission.expiry_date.strftime("%B %d, %Y at %I:%M %p")
                }
            ))
        return

    def handle_event(self, message_id: str, sender_id: str, event: VirtualDesktopEvent):
        if not self.is_sender_controller_role(sender_id):
            raise self.message_source_validation_failed(f'Corrupted sender_id: {sender_id}. Ignoring message')

        table_name = Utils.get_value_as_string('table_name', event.detail, None)
        hash_key = Utils.get_value_as_string('hash_key', event.detail, '')
        range_key = Utils.get_value_as_string('range_key', event.detail, '')
        new_value = Utils.get_value_as_dict('new_value', event.detail, {})
        old_value = Utils.get_value_as_dict('old_value', event.detail, {})
        self.log_info(message_id=message_id, message=f'table name = {table_name}')
        self.DETAIL_TYPE_TYPE_DB_ENTRY_UPDATED_HANDLER[table_name](hash_key, range_key, old_value, new_value, table_name)
