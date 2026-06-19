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
    VirtualDesktopSessionState
)
from ideasdk.utils import Utils
from ideavirtualdesktopcontroller.app.clients.events_client.events_client import VirtualDesktopEvent
from ideavirtualdesktopcontroller.app.events.handlers.base_event_handler import BaseVirtualDesktopControllerEventHandler
from res.clients.dcv_session_manager import dcv_session_manager_client


class IDEASessionPermissionsEnforceEventHandler(BaseVirtualDesktopControllerEventHandler):

    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        super().__init__(context, 'idea-session-permissions-enforce-event-handler')

    def handle_event(self, message_id: str, sender_id: str, event: VirtualDesktopEvent):
        if not self.is_sender_controller_role(sender_id) and not self.is_sender_backend_lambda(sender_id):
            raise self.message_source_validation_failed(f'Corrupted sender_id: {sender_id}. Ignoring message')

        self.log_info(message_id=message_id, message=f'Received enforce permissions event: {event.detail}')

        idea_session_id = Utils.get_value_as_string('idea_session_id', event.detail, None)
        idea_session_owner = Utils.get_value_as_string('idea_session_owner', event.detail, None)
        session = self.session_db.get_from_db(idea_session_id=idea_session_id, idea_session_owner=idea_session_owner)
        if Utils.is_empty(session):
            self.log_error(message_id=message_id, message=f'No permissions found for RES Session ID: {idea_session_id}, owner: {idea_session_owner}')
            return

        if session.state not in {VirtualDesktopSessionState.READY, VirtualDesktopSessionState.RESUMING, VirtualDesktopSessionState.CREATING, VirtualDesktopSessionState.INITIALIZING}:
            self.log_info(message_id=message_id, message=f'Session {idea_session_id} in {session.state}. Ignoring enforce permission event. NO=OP')
            return

        if session.state in {VirtualDesktopSessionState.PROVISIONING, VirtualDesktopSessionState.STOPPING, VirtualDesktopSessionState.STOPPED, VirtualDesktopSessionState.STOPPED_IDLE, VirtualDesktopSessionState.ERROR, VirtualDesktopSessionState.DELETING, VirtualDesktopSessionState.PROVISIONING}:
            raise self.do_not_delete_message_exception(f'Session {idea_session_id} in {session.state}. Will handle later')

        # session is READY
        permissions_content = self.session_permission_utils.generate_permissions_for_session(session, True)
        permissions_content_base_64 = None if Utils.is_empty(permissions_content) else Utils.base64_encode(permissions_content)
        self.log_info(message_id=message_id, message=f'Sending UpdateSessionPermissions to DCV Lambda: session={session}')
        dcv_session_manager_client.update_session_permissions(
            session_id=idea_session_id,
            owner=session.owner,
            permissions_file=permissions_content_base_64
        )
