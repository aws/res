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


class IDEAResumeSessionCommandProgressEventHandler(BaseVirtualDesktopControllerEventHandler):

    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        super().__init__(context, 'resume-session-command-progress-event-handler')

    def handle_event(self, message_id: str, sender_id: str, event: VirtualDesktopEvent):
        if not self.is_sender_controller_role(sender_id):
            raise self.message_source_validation_failed(f'Corrupted sender_id: {sender_id}. Ignoring message')

        status = Utils.get_value_as_string('status', event.detail, '')
        _ = Utils.get_value_as_string('instance_id', event.detail, None)
        idea_session_id = Utils.get_value_as_string('idea_session_id', event.detail, None)
        idea_session_owner = Utils.get_value_as_string('idea_session_owner', event.detail, None)
        command_id = Utils.get_value_as_string('command_id', event.detail, None)

        if status in {'Success', 'Failed'}:
            session = self.session_db.get_from_db(idea_session_owner=idea_session_owner, idea_session_id=idea_session_id)
            if status == 'Success':
                session.state = VirtualDesktopSessionState.INITIALIZING
                self.events_utils.publish_validate_dcv_session_creation_event(
                    idea_session_id=session.idea_session_id,
                    idea_session_owner=session.owner
                )
                self.log_info(message_id=message_id, message=f'Session: {session.idea_session_id}:{session.name} moved to Initializing state')
                self.ssm_commands_db.delete(command_id=command_id)
            else:
                # FAILED
                session.state = VirtualDesktopSessionState.ERROR
                self.log_error(message_id=message_id, message=f'Session: {session.idea_session_id}:{session.name} moved to Error state')

            _ = self.session_db.update(session)
        else:
            self.log_error(message_id=message_id, message=f'Ignoring message because state is {status} for RES Session ID: {idea_session_id}')
