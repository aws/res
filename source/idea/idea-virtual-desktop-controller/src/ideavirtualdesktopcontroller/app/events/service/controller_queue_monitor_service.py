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
from threading import Thread, Event
from typing import Optional

import ideavirtualdesktopcontroller
from ideadatamodel import SocaEnvelope
from ideasdk.service import SocaService
from ideasdk.utils import Utils
from ideavirtualdesktopcontroller.app.events.events_utils import EventsUtils
from ideavirtualdesktopcontroller.app.servers.virtual_desktop_server_db import VirtualDesktopServerDB
from ideavirtualdesktopcontroller.app.ssm_commands.virtual_desktop_ssm_commands_db import VirtualDesktopSSMCommandsDB, VirtualDesktopSSMCommandType


class ControllerQueueMonitorService(SocaService):
    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        super().__init__(context)
        self.context = context
        self._is_running = False
        self._service_thread: Optional[Thread] = None
        self._exit = Event()
        self._logger = context.logger('controller-q-monitor-service')

        self._events_utils = EventsUtils(self.context)
        self._ssm_commands_db = VirtualDesktopSSMCommandsDB(self.context)
        self._server_db = VirtualDesktopServerDB(self.context)

    def _initialize(self):
        self._service_thread = Thread(
            name='controller-service-thread',
            target=self._monitor_controller_queue
        )
        self._service_thread.start()

    def _monitor_controller_queue(self):
        while not self._exit.is_set():
            try:
                self._poll_and_process_queue()
            except Exception as e:
                self._logger.exception(f'failed to process sqs queue: {e}')

    def _handle_user_disabled_event(self, _: str, message: SocaEnvelope):
        username = Utils.get_value_as_string('username', message.payload, None)
        if Utils.is_empty(username):
            return
        self._events_utils.publish_user_disabled_event(username=username)

    def _handle_scheduled_event(self, message_id: str, message_body: dict):
        detail_type = Utils.get_value_as_string('detail-type', message_body, None)
        if detail_type != 'Scheduled Event':
            self._logger.error(f'[msg-id: {message_id}] Invalid detail type from scheduled event.. {detail_type}')
            return

        self._logger.info(f'[msg-id: {message_id}] Publishing scheduled event message')
        self._events_utils.publish_scheduled_event(time=Utils.get_value_as_string('time', message_body))

    def _poll_and_process_queue(self):
        response = self.context.aws().sqs().receive_message(
            QueueUrl=self.context.config().get_string('virtual-desktop-controller.controller_sqs_queue_url', required=True),
            MaxNumberOfMessages=10,
            # ENSURE LONG POLLING
            WaitTimeSeconds=20
        )
        delete_message_info = []
        for message in Utils.get_value_as_list('Messages', response, []):
            message_id = Utils.get_value_as_string('MessageId', message, None)
            message_body = Utils.from_json(Utils.get_value_as_string('Body', message, None))
            topic_arn = Utils.get_value_as_string('TopicArn', message_body, None)
            if Utils.is_empty(topic_arn):
                event = SocaEnvelope(**message_body)
                if event.header.namespace == 'Accounts.UserDisabledEvent':
                    self._handle_user_disabled_event(message_id, event)
                else:
                    self._logger.error(f'Invalid message with header: {event.header} received. Not handling. NP=OP')
            else:
                # SNS event
                self._logger.info(f'[msg-id: {message_id}] Processing message from source SNS')
                if topic_arn == self.context.config().get_string('virtual-desktop-controller.ssm_commands_sns_topic_arn', required=True):
                    self._logger.info(f'[msg-id: {message_id}] Message is from SSM Commands Status Topic')
                    self._handle_ssm_commands(message_id, message_body)
                elif topic_arn == self.context.config().get_string('cluster.ec2.state_change_notifications_sns_topic_arn', required=True):
                    self._logger.info(f'[msg-id: {message_id}] Message is from Ec2 State Change Topic')
                    self._handle_ec2_state_change(message_id, message_body)
                else:
                    self._logger.error(f'[msg-id: {message_id}] Topic Arn not recognized: {topic_arn}. Not handling. NO=OP')

            delete_message_info.append({
                'Id': message_id,
                'ReceiptHandle': Utils.get_value_as_string('ReceiptHandle', message, None)
            })

        if len(delete_message_info) > 0:
            _ = self.context.aws().sqs().delete_message_batch(
                QueueUrl=self.context.config().get_string('virtual-desktop-controller.controller_sqs_queue_url', required=True),
                Entries=delete_message_info
            )

    def _handle_ec2_state_change(self, message_id: str, message_body):
        message = Utils.from_json(Utils.get_value_as_string('Message', message_body, ''))
        event = SocaEnvelope(**message)

        instance_id = Utils.get_value_as_string('instance-id', event.payload, None)
        server = self._server_db.get(instance_id=instance_id)
        if Utils.is_empty(server):
            self._logger.info(f'[msg-id: {message_id}] Invalid DCV Host Instance-ID {instance_id}. Ignoring Message')
            return

        state = Utils.get_value_as_string('state', event.payload, None)
        self._logger.info(f'[msg-id: {message_id}] Sending Ec2 state change message for instance id: {instance_id} for state {state}')
        self._events_utils.publish_ec2_state_updated_event(
            instance_id=instance_id,
            idea_session_id=server.idea_sesssion_id,
            idea_session_owner=server.idea_session_owner,
            state=state
        )

    def _handle_ssm_commands(self, message_id: str, message_body):
        message = Utils.from_json(Utils.get_value_as_string('Message', message_body, ''))
        command_id = Utils.get_value_as_string('commandId', message, None)

        status = Utils.get_value_as_string('status', message, None)
        if Utils.is_empty(command_id):
            self._logger.error(f'[msg-id: {message_id}] Invalid SSM Command ID: {command_id}')
            return

        ssm_command = self._ssm_commands_db.get(command_id=command_id)
        if Utils.is_empty(ssm_command):
            self._logger.error(f'[msg-id: {message_id}] Invalid SSM Command ID: {command_id}')
            return

        self._logger.info(f'[msg-id: {message_id}] Handling SSM Command message for command id {command_id}')

        if ssm_command.command_type == VirtualDesktopSSMCommandType.RESUME_SESSION:
            self._events_utils.publish_resume_session_command_status_event(
                idea_session_id=Utils.get_value_as_string('idea_session_id', ssm_command.additional_payload, ''),
                idea_session_owner=Utils.get_value_as_string('idea_session_owner', ssm_command.additional_payload, ''),
                command_id=command_id,
                instance_id=Utils.get_value_as_string('instance_id', ssm_command.additional_payload, ''),
                status=status
            )
        elif ssm_command.command_type == VirtualDesktopSSMCommandType.WINDOWS_ENABLE_USERDATA_EXECUTION:
            self._events_utils.publish_enable_userdata_windows_status_event(
                idea_session_id=Utils.get_value_as_string('idea_session_id', ssm_command.additional_payload, ''),
                idea_session_owner=Utils.get_value_as_string('idea_session_owner', ssm_command.additional_payload, ''),
                command_id=command_id,
                instance_id=Utils.get_value_as_string('instance_id', ssm_command.additional_payload, ''),
                status=status,
                software_stack_id=Utils.get_value_as_string('software_stack_id', ssm_command.additional_payload, ''),
            )
        elif ssm_command.command_type == VirtualDesktopSSMCommandType.WINDOWS_DISABLE_USERDATA_EXECUTION:
            self._events_utils.publish_disable_userdata_windows_status_event(
                idea_session_id=Utils.get_value_as_string('idea_session_id', ssm_command.additional_payload, ''),
                idea_session_owner=Utils.get_value_as_string('idea_session_owner', ssm_command.additional_payload, ''),
                command_id=command_id,
                instance_id=Utils.get_value_as_string('instance_id', ssm_command.additional_payload, ''),
                status=status
            )
        elif ssm_command.command_type == VirtualDesktopSSMCommandType.CPU_UTILIZATION_CHECK_STOP_SCHEDULED_SESSION:
            self._events_utils.publish_idea_session_cpu_utilization_command_status_event(
                idea_session_id=Utils.get_value_as_string('idea_session_id', ssm_command.additional_payload, ''),
                idea_session_owner=Utils.get_value_as_string('idea_session_owner', ssm_command.additional_payload, ''),
                command_id=command_id,
                instance_id=Utils.get_value_as_string('instance_id', ssm_command.additional_payload, ''),
                status=status
            )
        else:
            self._logger.error(f'[msg-id: {message_id}] Unsupported command type {ssm_command.command_type}. NO=OP')

    def start(self):
        if self._is_running:
            return
        self._initialize()
        self._is_running = True

    def stop(self):
        self._logger.info('stopping controller-q-monitor-service ...')
        self._exit.set()
        self._is_running = False
        self._service_thread.join()
