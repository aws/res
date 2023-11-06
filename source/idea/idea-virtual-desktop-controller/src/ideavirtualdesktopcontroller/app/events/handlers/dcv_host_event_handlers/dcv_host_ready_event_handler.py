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
from ideadatamodel import VirtualDesktopSessionState, VirtualDesktopSession
from ideadatamodel import constants
from ideasdk.utils import Utils
from ideavirtualdesktopcontroller.app.clients.events_client.events_client import VirtualDesktopEvent
from ideavirtualdesktopcontroller.app.events.handlers.base_event_handler import BaseVirtualDesktopControllerEventHandler
from ideavirtualdesktopcontroller.app.sessions.virtual_desktop_session_counters_db import VirtualDesktopSessionCounterType


class DCVHostReadyEventHandler(BaseVirtualDesktopControllerEventHandler):
    SESSION_CREATION_THRESHOLD_COUNT = 30

    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        super().__init__(context, 'dcv-host-state-handler')

    def handle_event(self, message_id: str, sender_id: str, event: VirtualDesktopEvent):
        sender_instance_id = self.get_dcv_instance_id_from_sender_id(sender_id)
        if Utils.is_empty(sender_instance_id):
            raise self.message_source_validation_failed(f'Corrupted sender_id: {sender_id}. Ignoring message')

        idea_session_id = Utils.get_value_as_string('idea_session_id', event.detail, None)
        idea_session_owner = Utils.get_value_as_string('idea_session_owner', event.detail, None)

        self.log_info(message_id=message_id, message=f'Received message from dcv-host for RES Session ID: {idea_session_id}, {idea_session_owner}')
        if Utils.is_empty(idea_session_id) or Utils.is_empty(idea_session_owner):
            self.log_error(message_id=message_id, message=f'RES Session ID: {idea_session_id}, owner: {idea_session_owner}')
            return

        session = self.session_db.get_from_db(idea_session_owner=idea_session_owner, idea_session_id=idea_session_id)
        if Utils.is_empty(session):
            self.log_error(message_id=message_id, message='Invalid RES Session ID')
            return

        if session.server.instance_id != sender_instance_id:
            raise self.message_source_validation_failed(f'Corrupted sender_id: {sender_id}. Ignoring message')

        if session.state not in {VirtualDesktopSessionState.PROVISIONING, VirtualDesktopSessionState.CREATING}:
            self.log_info(message_id=message_id, message=f'RES Session ID: {session.idea_session_id} is currently in state {session.state}. Ignoring Event')
            return

        session = self._create_session(message_id, session)
        if session.state == VirtualDesktopSessionState.CREATING:
            self.log_info(message_id=message_id, message=f'handling dcv_host_ready. session state is {session.state}')
            raise self.do_not_delete_message_exception(f'Session state is {session.state}. Not handling now.')

        self.log_info(message_id=message_id, message=f'handling dcv_host_ready. session state is {session.state}')

    def _create_session(self, message_id: str, session: VirtualDesktopSession) -> VirtualDesktopSession:
        session_response = self.context.dcv_broker_client.create_session(session)
        counter_db_entry = self.session_counter_db.get(idea_session_id=session.idea_session_id, counter_type=VirtualDesktopSessionCounterType.DCV_SESSION_CREATION_REQUEST_ACCPETED_COUNTER)

        if Utils.is_empty(session_response.failure_reason):
            # success
            self.log_info(message_id=message_id, message=f'session request created for {session_response.owner} with name: {session_response.name} and dcv_session_id {session_response.dcv_session_id}')
            session.state = VirtualDesktopSessionState.INITIALIZING
            session.dcv_session_id = session_response.dcv_session_id
            session = self.session_db.update(session)
            self.controller_utils.create_tag(session.server.instance_id, constants.IDEA_TAG_DCV_SESSION_ID, session.dcv_session_id)

            self.events_utils.publish_validate_dcv_session_creation_event(
                idea_session_id=session.idea_session_id,
                idea_session_owner=session.owner
            )

            # clear the session_counter_db
            if not counter_db_entry.counter == 0:
                # counter exists and we need to delete it
                self.session_counter_db.delete(counter_db_entry)

        else:
            # we have failure. Check the count. Increment by 1. Error out at 'SESSION_CREATION_THRESHOLD_COUNT'
            update_db_entry = False
            self.log_info(message_id=message_id, message=f'session creation error: {session.failure_reason} current count is {counter_db_entry.counter}')
            if counter_db_entry.counter < self.SESSION_CREATION_THRESHOLD_COUNT:
                # we will try again soon
                if session.state != VirtualDesktopSessionState.CREATING:
                    session.state = VirtualDesktopSessionState.CREATING
                    update_db_entry = True
                counter_db_entry.counter = counter_db_entry.counter + 1
            else:
                # error out.
                session.dcv_session_id = ''
                session.state = VirtualDesktopSessionState.ERROR
                update_db_entry = True

            self.session_counter_db.create_or_update(counter_db_entry)
            if update_db_entry:
                session = self.session_db.update(session)

        return session
