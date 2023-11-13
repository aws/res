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

import ideavirtualdesktopcontroller
from ideadatamodel import (
    VirtualDesktopSessionState,
    VirtualDesktopSession
)
from ideasdk.utils import Utils

from ideavirtualdesktopcontroller.app.clients.events_client.events_client import VirtualDesktopEvent
from ideavirtualdesktopcontroller.app.events.handlers.base_event_handler import BaseVirtualDesktopControllerEventHandler


class ValidateDCVSessionDeletionEventHandler(BaseVirtualDesktopControllerEventHandler):

    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        super().__init__(context, 'validate-dcv-session-deletion-handler')

    def _continue_stop_session(self, message_id: str, session: VirtualDesktopSession):
        if session.hibernation_enabled:
            self.log_debug(message_id=message_id, message=f'Continuing to hibernate session... {session.idea_session_id}:{session.name}')
            self.server_utils.stop_or_hibernate_servers(servers_to_hibernate=[session.server])
        else:
            self.log_debug(message_id=message_id, message=f'Continuing to stop session... {session.idea_session_id}:{session.name}')
            self.server_utils.stop_or_hibernate_servers(servers_to_stop=[session.server])

    def _continue_delete_session(self, message_id: str, session: VirtualDesktopSession):
        self.log_debug(message_id=message_id, message=f'Continuing to delete session... {session.idea_session_id}:{session.name}')
        self.schedule_utils.delete_schedules_for_session(session)
        self.session_permission_utils.delete_permissions_for_session(session)
        # delete session entry
        self.session_db.delete(session)
        self.server_utils.terminate_dcv_hosts([session.server])

    def handle_event(self, message_id: str, sender_id: str, event: VirtualDesktopEvent):
        if not self.is_sender_controller_role(sender_id):
            raise self.message_source_validation_failed(f'Corrupted sender_id: {sender_id}. Ignoring message')

        idea_session_id = Utils.get_value_as_string('idea_session_id', event.detail, None)
        idea_session_owner = Utils.get_value_as_string('idea_session_owner', event.detail, None)

        self.log_info(message_id=message_id, message=f'Received session stop validation message for RES Session ID: {idea_session_id}, {idea_session_owner}')
        if Utils.is_empty(idea_session_id) or Utils.is_empty(idea_session_owner):
            self.log_error(message_id=message_id, message=f'RES Session ID: {idea_session_id}, owner: {idea_session_owner}')
            return

        session = self.session_db.get_from_db(idea_session_owner=idea_session_owner, idea_session_id=idea_session_id)
        if Utils.is_empty(session):
            self.log_error(message_id=message_id, message='Invalid RES Session ID.')
            return

        if session.state not in {VirtualDesktopSessionState.STOPPING, VirtualDesktopSessionState.DELETING}:
            self.log_info(message_id=message_id, message=f'RES Session ID: {session.idea_session_id} in state {session.state}. NO=OP. Returning.')
            return

        response = self.context.dcv_broker_client.describe_sessions([session])
        current_session_info = Utils.get_value_as_dict(session.dcv_session_id, Utils.get_value_as_dict("sessions", response, {}), {})
        state = Utils.get_value_as_string("state", current_session_info, None)

        if Utils.is_empty(state) or state == 'DELETED':
            # session is deleted. We can continue.
            self.log_info(message_id=message_id, message=f'RES Session ID: {session.idea_session_id}:{session.name} is deleted with state: {state}. Validation complete.')
            if session.state is VirtualDesktopSessionState.DELETING:
                self._continue_delete_session(message_id, session)
            elif session.state is VirtualDesktopSessionState.STOPPING:
                self._continue_stop_session(message_id, session)
            else:
                self.log_info(message_id=message_id, message=f'State not being handled: {session.state}. Will not handle.')
        else:
            raise self.do_not_delete_message_exception(f'RES Session ID: {session.idea_session_id}:{session.name} is not deleted with state: {state}. Not doing anything will try again.')
