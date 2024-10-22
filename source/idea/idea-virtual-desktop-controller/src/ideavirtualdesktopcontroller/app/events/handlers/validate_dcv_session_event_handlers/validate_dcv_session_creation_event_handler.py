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
from ideavirtualdesktopcontroller.app.sessions.virtual_desktop_session_counters_db import VirtualDesktopSessionCounterType


class ValidateDCVSessionCreationEventHandler(BaseVirtualDesktopControllerEventHandler):
    VALIDATION_REQUEST_THRESHOLD = 30
    SESSION_DELETED_THRESHOLD = 4

    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        super().__init__(context, 'validate-session-creation-handler')

    def handle_event(self, message_id: str, sender_id: str, event: VirtualDesktopEvent):
        if not self.is_sender_controller_role(sender_id):
            raise self.message_source_validation_failed(f'Corrupted sender_id: {sender_id}. Ignoring message')

        idea_session_id = Utils.get_value_as_string('idea_session_id', event.detail, None)
        idea_session_owner = Utils.get_value_as_string('idea_session_owner', event.detail, None)

        self.log_info(message_id=message_id, message=f'Received message from dcv-host for RES Session ID {idea_session_id}, {idea_session_owner}')
        if Utils.is_empty(idea_session_id) or Utils.is_empty(idea_session_owner):
            self.log_error(message_id=message_id, message=f'RES Session ID: {idea_session_id}, owner: {idea_session_owner}')
            return

        session = self.session_db.get_from_db(idea_session_owner=idea_session_owner, idea_session_id=idea_session_id)
        if Utils.is_empty(session):
            self.log_error(message_id=message_id, message='Invalid RES Session ID.')
            return

        counter_db_entry = self.session_counter_db.get(session.idea_session_id, VirtualDesktopSessionCounterType.VALIDATE_DCV_SESSION_CREATED_COUNTER)
        if session.state in {VirtualDesktopSessionState.DELETING, VirtualDesktopSessionState.DELETED}:
            # session is being deleted, stop validation.
            self.log_info(message_id=message_id, message=f'RES Session ID: {session.idea_session_id}:{session.name} is being deleted; state: {session.state}. Ignoring Validation.')
            self.session_counter_db.delete(counter_db_entry)
            return

        response = self.context.dcv_broker_client.describe_sessions([session])
        current_session_info = Utils.get_value_as_dict(session.dcv_session_id, Utils.get_value_as_dict("sessions", response, {}), {})
        state = Utils.get_value_as_string("state", current_session_info, None)

        should_delete_message = True
        should_not_delete_message_text = ''

        if state == 'READY':
            # session is stable.
            self.log_info(message_id=message_id, message=f'RES Session ID: {session.idea_session_id}:{session.name} is stable with state: {state}. Validation complete. Moving to ready state')
            session.state = VirtualDesktopSessionState.READY
            _ = self.session_db.update(session)
            self.session_counter_db.delete(counter_db_entry)
        elif counter_db_entry.counter > self.SESSION_DELETED_THRESHOLD and state == 'DELETED':
            # session creation failed. Error state.
            session.state = VirtualDesktopSessionState.ERROR
            session = self.session_db.update(session)
            self.log_error(message_id=message_id, message=f'RES Session ID: creation failed {session.idea_session_id}:{session.name} Validation ERROR. count: {counter_db_entry.counter}')
        elif state == 'UNKNOWN' or counter_db_entry.counter > self.VALIDATION_REQUEST_THRESHOLD:
            # error
            session.state = VirtualDesktopSessionState.ERROR
            session = self.session_db.update(session)
            self.log_error(message_id=message_id, message=f'RES Session ID: {session.idea_session_id}:{session.name} is not stable with state: {state}. Validation ERROR. count: {counter_db_entry.counter}')
        elif session.state is VirtualDesktopSessionState.STOPPING:
            self.log_error(message_id=message_id, message=f'RES Session ID: {session.idea_session_id}:{session.name} is currently stopping. IGNORING the validation')
        else:
            counter_db_entry.counter = counter_db_entry.counter + 1
            if session.state != VirtualDesktopSessionState.INITIALIZING:
                session.state = VirtualDesktopSessionState.INITIALIZING
                _ = self.session_db.update(session)
            self.session_counter_db.create_or_update(counter_db_entry)
            should_delete_message = False
            should_not_delete_message_text = f'RES Session ID: {session.idea_session_id}:{session.name} is not stable with state: {state}. {counter_db_entry.counter} times already validated. Will continue to validate'

        if not should_delete_message:
            raise self.do_not_delete_message_exception(should_not_delete_message_text)
