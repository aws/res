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


class IDEASessionPermissionsUpdateEventHandler(BaseVirtualDesktopControllerEventHandler):

    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        super().__init__(context, 'idea-session-permissions-update-event-handler')

    def handle_event(self, message_id: str, sender_id: str, event: VirtualDesktopEvent):
        if not self.is_sender_controller_role(sender_id):
            raise self.message_source_validation_failed(f'Corrupted sender_id: {sender_id}. Ignoring message')

        idea_session_id = Utils.get_value_as_string('idea_session_id', event.detail, None)
        new_name = Utils.get_value_as_string('new_name', event.detail, None)
        new_instance_type = Utils.get_value_as_string('new_instance_type', event.detail, None)
        new_state = Utils.get_value_as_string('new_state', event.detail, None)

        session_permissions = self.session_permissions_db.get_for_session(idea_session_id=idea_session_id)
        if Utils.is_empty(session_permissions):
            self.log_error(message_id=message_id, message=f'No permissions found for RES Session ID: {idea_session_id}')
            return

        for session_permission in session_permissions:
            is_updated = False
            if Utils.is_not_empty(new_name):
                session_permission.idea_session_name = new_name
                is_updated = True
            if Utils.is_not_empty(new_instance_type):
                session_permission.idea_session_instance_type = new_instance_type
                is_updated = True
            if Utils.is_not_empty(new_state):
                session_permission.idea_session_state = VirtualDesktopSessionState(new_state)
                is_updated = True

            if is_updated:
                self.session_permissions_db.update(session_permission)
