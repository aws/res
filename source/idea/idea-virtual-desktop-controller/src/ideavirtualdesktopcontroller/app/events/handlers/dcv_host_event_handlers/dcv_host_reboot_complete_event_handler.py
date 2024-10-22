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
from ideadatamodel import VirtualDesktopSessionState
from ideasdk.utils import Utils
from ideavirtualdesktopcontroller.app.clients.events_client.events_client import VirtualDesktopEvent
from ideavirtualdesktopcontroller.app.events.handlers.base_event_handler import BaseVirtualDesktopControllerEventHandler
from ideavirtualdesktopcontroller.app.sessions.virtual_desktop_session_counters_db import VirtualDesktopSessionCounterType


class DCVHostRebootCompleteEventHandler(BaseVirtualDesktopControllerEventHandler):
    RESUME_REQUEST_COUNT_THRESHOLD = 6

    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        super().__init__(context, 'dcv-host-reboot-complete-handler')

    def handle_event(self, message_id: str, sender_id: str, event: VirtualDesktopEvent):
        sender_instance_id = self.get_dcv_instance_id_from_sender_id(sender_id)
        if Utils.is_empty(sender_instance_id):
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

        if session.server.instance_id != sender_instance_id:
            raise self.message_source_validation_failed(f'Corrupted sender_id: {sender_id}. Ignoring message')

        # if session is RESUMING/READY/STOPPED/STOPPED_IDLE/ERROR continue, else ignore
        if session.state not in {VirtualDesktopSessionState.RESUMING, VirtualDesktopSessionState.READY, VirtualDesktopSessionState.ERROR, VirtualDesktopSessionState.STOPPED, VirtualDesktopSessionState.STOPPED_IDLE}:
            self.log_error(message_id=message_id, message=f'RES session {session.idea_session_id}:{session.name} is in state: {session.state}. Not handling.')
            return

        self.log_info(message_id=message_id, message=f'RES session {session.idea_session_id}:{session.name} is in state {session.state}. Handling reboot complete event')

        # if session RESUMING -> this is user trying to resume session
        # if session READY -> the machine has been restarted that means the session was active but either AWS or the user did a reboot.
        # either case we need to treat as reboot and resume session, or it is a bogus message. Check with the broker for session state first.
        if session.state in {VirtualDesktopSessionState.READY}:
            self.log_info(message_id=message_id, message=f"RES session {session.idea_session_id}:{session.name} is state: {session.state}. Needs additional validations.")
            response = self.context.dcv_broker_client.describe_sessions([session])
            current_session_info = Utils.get_value_as_dict(session.dcv_session_id, Utils.get_value_as_dict("sessions", response, {}), {})
            state = Utils.get_value_as_string("state", current_session_info, None)
            if state == 'CREATING':
                # session is stable. not need to worry.
                self.log_info(message_id=message_id, message=f"RES session {session.idea_session_id}:{session.name} is stable with state: {state}. No need to handle event. Returning.")
                return
            elif state == 'READY':
                counter_db_entry = self.session_counter_db.get(session.idea_session_id, VirtualDesktopSessionCounterType.DCV_SESSION_RESUMED_COUNTER)
                if counter_db_entry.counter < self.RESUME_REQUEST_COUNT_THRESHOLD:
                    counter_db_entry.counter = counter_db_entry.counter + 1
                    self.session_counter_db.create_or_update(counter_db_entry)
                    raise self.do_not_delete_message_exception(f'RES session {session.idea_session_id}:{session.name} might stable with state: {state}. No need to handle event now. Resume request count: {counter_db_entry.counter}. Threshold: {self.RESUME_REQUEST_COUNT_THRESHOLD}')
                else:
                    # session is stable for sure.
                    self.session_counter_db.delete(counter_db_entry)
                    self.log_info(message_id=message_id, message=f"RES session {session.idea_session_id}:{session.name} is stable with state: {state}. No need to handle event.")
                    return

            self.log_warning(message_id=message_id, message=f"RES session {session.idea_session_id}:{session.name} is NOT stable with state: {state}. Handling.")
        else:
            self.log_info(message_id=message_id, message=f"RES session {session.idea_session_id}:{session.name} is state: {session.state}. Resuming Session.")

        session = self.context.dcv_broker_client.resume_session(session)

        if Utils.is_not_empty(session.failure_reason):
            # Error in resuming now. DO NOT PROCESS THE MESSAGE YET.
            raise self.do_not_delete_message_exception(f'Issue in resuming session: {session.failure_reason}. Will try again later')

        self.log_info(message_id=message_id, message=f"Submitted resume request for RES session {session.idea_session_id}:{session.name}.")

        if session.state is not VirtualDesktopSessionState.RESUMING:
            session.state = VirtualDesktopSessionState.RESUMING
            session = self.session_db.update(session)

        server = self.server_db.get(instance_id=session.server.instance_id)
        if server.state != 'CREATED':
            server.state = 'CREATED'
            self.server_db.update(server)
