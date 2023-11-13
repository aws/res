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
from ideasdk.utils import Utils
from ideavirtualdesktopcontroller.app.clients.events_client.events_client import VirtualDesktopEvent
from ideavirtualdesktopcontroller.app.events.handlers.base_event_handler import BaseVirtualDesktopControllerEventHandler


class IDEASessionSoftwareStackUpdatedEventHandler(BaseVirtualDesktopControllerEventHandler):
    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        super().__init__(context, 'idea-session-software-stack-update-event-handler')

    def handle_event(self, message_id: str, sender_id: str, event: VirtualDesktopEvent):
        if not self.is_sender_controller_role(sender_id):
            raise self.message_source_validation_failed(f'Corrupted sender_id: {sender_id}. Ignoring message')

        idea_session_id = Utils.get_value_as_string('idea_session_id', event.detail, None)
        idea_session_owner = Utils.get_value_as_string('idea_session_owner', event.detail, None)
        new_software_stack = Utils.get_value_as_dict('new_software_stack', event.detail, {})

        if Utils.is_any_empty(idea_session_id, idea_session_owner, new_software_stack):
            self.log_error(message=message_id, message_id='Invalid message. NO=OP')
            return

        session = self.session_db.get_from_db(idea_session_id=idea_session_id, idea_session_owner=idea_session_owner)
        if Utils.is_empty(session):
            self.log_error(message=message_id, message_id='Invalid session details. NO=OP')
            return

        software_stack_id = Utils.get_value_as_string('stack_id', new_software_stack, None)
        if session.software_stack.stack_id != software_stack_id:
            self.log_error(message=message_id, message_id='Invalid session/software stack combination. NO=OP')
            return

        session.software_stack = self.software_stack_db.convert_db_dict_to_software_stack_object(new_software_stack)
        _ = self.session_db.update(session)
