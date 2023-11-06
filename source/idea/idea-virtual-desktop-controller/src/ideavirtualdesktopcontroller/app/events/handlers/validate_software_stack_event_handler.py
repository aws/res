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
    VirtualDesktopBaseOS
)
from ideasdk.utils import Utils
from ideavirtualdesktopcontroller.app.clients.events_client.events_client import VirtualDesktopEvent
from ideavirtualdesktopcontroller.app.events.handlers.base_event_handler import BaseVirtualDesktopControllerEventHandler


class ValidateSoftwareStackEventHandler(BaseVirtualDesktopControllerEventHandler):

    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        super().__init__(context, 'validate-software-stack-event-handler')

    def handle_event(self, message_id: str, sender_id: str, event: VirtualDesktopEvent):
        if not self.is_sender_controller_role(sender_id):
            raise self.message_source_validation_failed(f'Corrupted sender_id: {sender_id}. Ignoring message')

        software_stack_id = Utils.get_value_as_string('software_stack_id', event.detail, None)
        software_stack_base_os = VirtualDesktopBaseOS(Utils.get_value_as_string('software_stack_base_os', event.detail, None))
        idea_session_id = Utils.get_value_as_string('idea_session_id', event.detail, None)
        idea_session_owner = Utils.get_value_as_string('idea_session_owner', event.detail, None)
        instance_id = Utils.get_value_as_string('instance_id', event.detail, None)

        self.log_info(message_id=message_id, message=f'Handling software stack validation request for {software_stack_id}:{software_stack_base_os}')
        if Utils.is_empty(software_stack_id) or Utils.is_empty(software_stack_base_os):
            self.log_error(message_id=message_id, message=f'Invalid {software_stack_id}: {software_stack_base_os}')
            return

        software_stack_db_entry = self.software_stack_db.get(base_os=software_stack_base_os, stack_id=software_stack_id)
        if Utils.is_empty(software_stack_db_entry):
            self.log_error(message_id=message_id, message='Invalid Software Stack.')
            return

        response = self.controller_utils.describe_image_id(software_stack_db_entry.ami_id)
        status = Utils.get_value_as_string('State', response, None)
        if status == 'available':
            # AMI is ready to use
            software_stack_db_entry.enabled = True
            self.software_stack_db.update(software_stack_db_entry)
            if software_stack_base_os == VirtualDesktopBaseOS.WINDOWS:
                # disable userdata
                self.ssm_commands_utils.submit_ssm_command_to_disable_userdata_execution_on_windows(
                    instance_id=instance_id,
                    idea_session_id=idea_session_id,
                    idea_session_owner=idea_session_owner
                )
            else:
                session = self.session_db.get_from_db(idea_session_id=idea_session_id, idea_session_owner=idea_session_owner)
                session.server.locked = False
                session.locked = False
                _ = self.session_db.update(session)
                _ = self.server_db.update(session.server)
            return
        else:
            # AMI is not ready to use.
            raise self.do_not_delete_message_exception(f'AMI {software_stack_db_entry.ami_id} is not yet ready to use with status {status}')
