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
from ideavirtualdesktopcontroller.app.clients.events_client.events_client import VirtualDesktopEvent
from ideavirtualdesktopcontroller.app.events.handlers.base_event_handler import BaseVirtualDesktopControllerEventHandler
from ideadatamodel import VirtualDesktopSession
from res.exceptions import SoftwareStackNotFound
from res.resources import software_stacks
from res.resources import sessions as user_sessions
from res.resources import servers

class DeleteLockFilesLinuxCommandProgressEventListener(BaseVirtualDesktopControllerEventHandler):

    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        super().__init__(context, 'delete-lock-files-linux-command-progress-event-listener')

    def _continue_software_stack_creation(self, session: dict, software_stack_id: str):
        try:
            software_stack_dict = software_stacks.get_software_stack(stack_id=software_stack_id, base_os=session.get('base_os'))
            software_stack = self.software_stack_db.convert_db_dict_to_software_stack_object(software_stack_dict)
        except SoftwareStackNotFound:
            software_stack = None 
        response = self.controller_utils.create_image_for_instance_id(session.get('server').get('instance_id'), software_stack.name, software_stack.description)
        software_stack.ami_id = response.get('ImageId')
        self.software_stack_db.update(software_stack)
        self.events_utils.publish_validate_software_stack_creation_event(
            software_stack_id=software_stack.stack_id,
            base_os=software_stack.base_os,
            idea_session_owner=session.get('owner'),
            idea_session_id=session.get('idea_session_id'),
            instance_id=session.get('server').get('instance_id')
        )

    def handle_event(self, message_id: str, sender_id: str, event: VirtualDesktopEvent):
        if not self.is_sender_controller_role(sender_id):
            raise self.message_source_validation_failed(f'Corrupted sender_id: {sender_id}. Ignoring message')

        status = event.detail.get('status', '')
        idea_session_id = event.detail.get('idea_session_id')
        idea_session_owner = event.detail.get('idea_session_owner')
        command_id = event.detail.get('command_id')
        software_stack_id = event.detail.get('software_stack_id')
        if status in {'Success', 'Failed'}:
            user_session = user_sessions.get_session(owner=idea_session_owner, session_id=idea_session_id)

            if status == 'Success':
                self.ssm_commands_db.delete(command_id=command_id)
                self._continue_software_stack_creation(user_session, software_stack_id)
            else:
                self.log_error(message_id=message_id, message=f'Session: {user_session.get("idea_session_id")}:{user_session.get("name")} moved to Error state')
            if user_sessions.SESSION_DB_SERVER_KEY in user_session:
                servers.update_server(user_session.get(user_sessions.SESSION_DB_SERVER_KEY))
        else:
            self.log_error(message_id=message_id, message=f'Ignoring message because state is {status} for RES Session ID: {idea_session_id}')
