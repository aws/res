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


class EnableUserdataWindowsCommandProgressEventListener(BaseVirtualDesktopControllerEventHandler):

    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        super().__init__(context, 'enable-userdata-windows-command-progress-event-listener')

    def _continue_software_stack_creation(self, session: VirtualDesktopSession, software_stack_id: str):
        software_stack = self.software_stack_db.get(stack_id=software_stack_id, base_os=session.base_os)
        response = self.controller_utils.create_image_for_instance_id(session.server.instance_id, software_stack.name, software_stack.description)
        software_stack.ami_id = Utils.get_value_as_string('ImageId', response, None)
        self.software_stack_db.update(software_stack)
        self.events_utils.publish_validate_software_stack_creation_event(
            software_stack_id=software_stack.stack_id,
            base_os=software_stack.base_os,
            idea_session_owner=session.owner,
            idea_session_id=session.idea_session_id,
            instance_id=session.server.instance_id
        )

    def handle_event(self, message_id: str, sender_id: str, event: VirtualDesktopEvent):
        if not self.is_sender_controller_role(sender_id):
            raise self.message_source_validation_failed(f'Corrupted sender_id: {sender_id}. Ignoring message')

        status = Utils.get_value_as_string('status', event.detail, '')
        _ = Utils.get_value_as_string('instance_id', event.detail, None)
        idea_session_id = Utils.get_value_as_string('idea_session_id', event.detail, None)
        idea_session_owner = Utils.get_value_as_string('idea_session_owner', event.detail, None)
        command_id = Utils.get_value_as_string('command_id', event.detail, None)
        software_stack_id = Utils.get_value_as_string('software_stack_id', event.detail, None)

        if status in {'Success', 'Failed'}:
            session = self.session_db.get_from_db(idea_session_owner=idea_session_owner, idea_session_id=idea_session_id)
            if status == 'Success':
                self.ssm_commands_db.delete(command_id=command_id)
                self._continue_software_stack_creation(session, software_stack_id)
            else:
                # FAILED
                session.state = VirtualDesktopSessionState.ERROR
                self.log_error(message_id=message_id, message=f'Session: {session.idea_session_id}:{session.name} moved to Error state')

            _ = self.server_db.update(session.server)
            _ = self.session_db.update(session)
        else:
            self.log_error(message_id=message_id, message=f'Ignoring message because state is {status} for idea_session_id: {idea_session_id}')
