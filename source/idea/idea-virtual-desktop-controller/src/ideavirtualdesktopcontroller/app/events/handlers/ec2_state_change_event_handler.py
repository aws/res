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


class EC2StateChangeEventHandler(BaseVirtualDesktopControllerEventHandler):

    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        super().__init__(context, 'ec2-state-changed-handler')

    def _handle_stopping_events(self, message_id: str, event: VirtualDesktopEvent):
        state = Utils.get_value_as_string('state', event.detail, None)
        instance_id = Utils.get_value_as_string('instance_id', event.detail, None)
        self._logger.info(f'Handling {state} state event for instance-id: {instance_id}')

        idea_session_id = Utils.get_value_as_string('idea_session_id', event.detail, None)
        idea_session_owner = Utils.get_value_as_string('idea_session_owner', event.detail, None)
        session = self.session_db.get_from_db(idea_session_owner=idea_session_owner, idea_session_id=idea_session_id)
        if Utils.is_empty(session):
            self.log_error(message_id=message_id, message='Invalid RES Session. Should probably do some DB cleanup for instances.')
            return

        if session.state in {VirtualDesktopSessionState.STOPPED, VirtualDesktopSessionState.DELETING, VirtualDesktopSessionState.DELETED, VirtualDesktopSessionState.ERROR}:
            # Event ignored.
            self.log_info(message_id=message_id, message=f'RES Session {session.idea_session_id} in state {session.state}. Ignoring Event. NO=OP.')
            return
        elif session.state in {VirtualDesktopSessionState.PROVISIONING, VirtualDesktopSessionState.CREATING, VirtualDesktopSessionState.INITIALIZING, VirtualDesktopSessionState.RESUMING}:
            # In these states, the EC2 Instance STOPPED was not expected (it has stopped suddenly without warning). Hence error.
            self.log_error(message_id=message_id, message=f'RES Session {session.idea_session_id} in state {session.state}. Error.')
            session.state = VirtualDesktopSessionState.ERROR
        else:
            # was waiting for ec2 stopped/stopping event.
            server = self.server_db.get(instance_id=instance_id)
            if state == 'stopping':
                session.state = VirtualDesktopSessionState.STOPPING
                server.state = 'STOPPING'
            elif session.is_idle:
                session.state = VirtualDesktopSessionState.STOPPED_IDLE
                server.state = 'STOPPED_IDLE'
                _ = self.server_db.update(server)
            else:
                session.state = VirtualDesktopSessionState.STOPPED
                server.state = 'STOPPED'
                _ = self.server_db.update(server)

        _ = self.session_db.update(session)

    def _handle_running_event(self, message_id: str, event: VirtualDesktopEvent):
        instance_id = Utils.get_value_as_string('instance_id', event.detail, None)
        self._logger.info(f'Handling running state event for instance-id: {instance_id}')

        idea_session_id = Utils.get_value_as_string('idea_session_id', event.detail, None)
        idea_session_owner = Utils.get_value_as_string('idea_session_owner', event.detail, None)

        session = self.session_db.get_from_db(idea_session_owner=idea_session_owner, idea_session_id=idea_session_id)
        if Utils.is_empty(session):
            self.log_error(message_id=message_id, message='Invalid RES Session. Should probably do some DB cleanup for instances.')
            return

        if session.hibernation_enabled and session.state in {VirtualDesktopSessionState.RESUMING}:
            self.events_utils.publish_dcv_host_reboot_complete_event(
                instance_id=instance_id,
                idea_session_id=idea_session_id,
                idea_session_owner=idea_session_owner
            )
        
        session.is_idle = False
        _ = self.session_db.update(session)

        server = self.server_db.get(instance_id=instance_id)
        server.state = 'CREATED'
        _ = self.server_db.update(server)

    def handle_event(self, message_id: str, sender_id: str, event: VirtualDesktopEvent):
        if not self.is_sender_controller_role(sender_id):
            raise self.message_source_validation_failed(f'Corrupted sender_id: {sender_id}. Ignoring message')

        instance_id = Utils.get_value_as_string('instance_id', event.detail, None)
        state = Utils.get_value_as_string('state', event.detail, None)
        if Utils.is_empty(instance_id):
            self.log_error(message_id=message_id, message=f'Invalid Instance_id: {instance_id}')
            return

        if state in {'stopping', 'stopped'}:
            self._handle_stopping_events(message_id, event)
        elif state == 'running':
            self._handle_running_event(message_id, event)
        else:
            self.log_info(message_id=message_id, message=f'instance_id is {instance_id} state is {state}. NO=OP. Ignoring.')
