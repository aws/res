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
from typing import Dict

import ideavirtualdesktopcontroller
from ideadatamodel import errorcodes
from ideadatamodel.exceptions import SocaException
from ideasdk.thread_pool.idea_thread import IdeaThread
from ideasdk.utils import Utils
from ideavirtualdesktopcontroller.app.clients.events_client.events_client import VirtualDesktopEventType, VirtualDesktopEvent
from ideavirtualdesktopcontroller.app.events.handlers.base_event_handler import BaseVirtualDesktopControllerEventHandler
from ideavirtualdesktopcontroller.app.events.handlers.db_entry_event_handlers.db_entry_created_event_handler import DbEntryCreatedEventHandler
from ideavirtualdesktopcontroller.app.events.handlers.db_entry_event_handlers.db_entry_deleted_event_handler import DbEntryDeletedEventHandler
from ideavirtualdesktopcontroller.app.events.handlers.db_entry_event_handlers.db_entry_updated_event_handler import DbEntryUpdatedEventHandler
from ideavirtualdesktopcontroller.app.events.handlers.dcv_broker_userdata_execution_complete_event_handler import DCVBrokerUserdataExecutionCompleteEventHandler
from ideavirtualdesktopcontroller.app.events.handlers.dcv_host_event_handlers.dcv_host_ready_event_handler import DCVHostReadyEventHandler
from ideavirtualdesktopcontroller.app.events.handlers.dcv_host_event_handlers.dcv_host_reboot_complete_event_handler import DCVHostRebootCompleteEventHandler
from ideavirtualdesktopcontroller.app.events.handlers.ec2_state_change_event_handler import EC2StateChangeEventHandler
from ideavirtualdesktopcontroller.app.events.handlers.idea_session_permissions_event_handlers.idea_session_permissions_enforce_event_handler import IDEASessionPermissionsEnforceEventHandler
from ideavirtualdesktopcontroller.app.events.handlers.idea_session_permissions_event_handlers.idea_session_permissions_update_event_handler import IDEASessionPermissionsUpdateEventHandler
from ideavirtualdesktopcontroller.app.events.handlers.idea_session_software_stack_update_event_handler import IDEASessionSoftwareStackUpdatedEventHandler
from ideavirtualdesktopcontroller.app.events.handlers.idea_session_state_event_handlers.idea_session_scheduled_resume_event_handler import IDEASessionScheduledResumeEventHandler
from ideavirtualdesktopcontroller.app.events.handlers.idea_session_state_event_handlers.idea_session_scheduled_stop_event_handler import IDEASessionScheduledStopEventHandler
from ideavirtualdesktopcontroller.app.events.handlers.idea_session_state_event_handlers.idea_session_terminate_event_handler import IDEASessionTerminateEventHandler
from ideavirtualdesktopcontroller.app.events.handlers.scheduled_event_handler import ScheduledEventHandler
from ideavirtualdesktopcontroller.app.events.handlers.ssm_commands_progress_event_handlers.disable_userdata_windows_command_progress_event_handler import DisableUserdataWindowsCommandProgressEventListener
from ideavirtualdesktopcontroller.app.events.handlers.ssm_commands_progress_event_handlers.enable_userdata_windows_command_progress_event_handler import EnableUserdataWindowsCommandProgressEventListener
from ideavirtualdesktopcontroller.app.events.handlers.ssm_commands_progress_event_handlers.idea_resume_session_command_progress_event_handler import IDEAResumeSessionCommandProgressEventHandler
from ideavirtualdesktopcontroller.app.events.handlers.ssm_commands_progress_event_handlers.idea_session_cpu_utilization_command_progress_event_handler import IDEASessionCPUUtilizationCommandProgressEventHandler
from ideavirtualdesktopcontroller.app.events.handlers.user_management_event_handlers.user_created_event_handler import UserCreatedEventHandler
from ideavirtualdesktopcontroller.app.events.handlers.user_management_event_handlers.user_disabled_event_handler import UserDisabledEventHandler
from ideavirtualdesktopcontroller.app.events.handlers.validate_dcv_session_event_handlers.validate_dcv_session_creation_event_handler import ValidateDCVSessionCreationEventHandler
from ideavirtualdesktopcontroller.app.events.handlers.validate_dcv_session_event_handlers.validate_dcv_session_deletion_event_handler import ValidateDCVSessionDeletionEventHandler
from ideavirtualdesktopcontroller.app.events.handlers.validate_software_stack_event_handler import ValidateSoftwareStackEventHandler


class EventsHandlerThread(IdeaThread):

    def __init__(self, context: ideavirtualdesktopcontroller.AppContext, thread_number: int, num_of_messages_to_retrieve_per_call: int, wait_time: int):
        self.context = context
        self._logger = context.logger(f'q-events-handler-thread-{thread_number}')
        self._is_running = False
        self.NUM_OF_MESSAGES = num_of_messages_to_retrieve_per_call
        self.EVENT_HANDLER_MAP: Dict[VirtualDesktopEventType, BaseVirtualDesktopControllerEventHandler] = {
            VirtualDesktopEventType.VALIDATE_SOFTWARE_STACK_CREATION_EVENT: ValidateSoftwareStackEventHandler(context=self.context),
            VirtualDesktopEventType.VALIDATE_DCV_SESSION_DELETION_EVENT: ValidateDCVSessionDeletionEventHandler(context=self.context),
            VirtualDesktopEventType.VALIDATE_DCV_SESSION_CREATION_EVENT: ValidateDCVSessionCreationEventHandler(context=self.context),
            VirtualDesktopEventType.IDEA_SESSION_SCHEDULED_RESUME_EVENT: IDEASessionScheduledResumeEventHandler(context=self.context),
            VirtualDesktopEventType.IDEA_SESSION_SCHEDULED_STOP_EVENT: IDEASessionScheduledStopEventHandler(context=self.context),
            VirtualDesktopEventType.IDEA_SESSION_TERMINATE_EVENT: IDEASessionTerminateEventHandler(context=self.context),
            VirtualDesktopEventType.IDEA_SESSION_PERMISSIONS_ENFORCE_EVENT: IDEASessionPermissionsEnforceEventHandler(context=self.context),
            VirtualDesktopEventType.IDEA_SESSION_PERMISSIONS_UPDATE_EVENT: IDEASessionPermissionsUpdateEventHandler(context=self.context),
            VirtualDesktopEventType.IDEA_SESSION_SOFTWARE_STACK_UPDATED_EVENT: IDEASessionSoftwareStackUpdatedEventHandler(context=self.context),
            VirtualDesktopEventType.EC2_INSTANCE_STATE_CHANGED_EVENT: EC2StateChangeEventHandler(context=self.context),
            VirtualDesktopEventType.DB_ENTRY_CREATED_EVENT: DbEntryCreatedEventHandler(context=self.context),
            VirtualDesktopEventType.DB_ENTRY_UPDATED_EVENT: DbEntryUpdatedEventHandler(context=self.context),
            VirtualDesktopEventType.DB_ENTRY_DELETED_EVENT: DbEntryDeletedEventHandler(context=self.context),
            VirtualDesktopEventType.DCV_HOST_READY_EVENT: DCVHostReadyEventHandler(context=self.context),
            VirtualDesktopEventType.DCV_HOST_REBOOT_COMPLETE_EVENT: DCVHostRebootCompleteEventHandler(context=self.context),
            VirtualDesktopEventType.DCV_BROKER_USERDATA_EXECUTION_COMPLETE_EVENT: DCVBrokerUserdataExecutionCompleteEventHandler(context=self.context),
            VirtualDesktopEventType.SCHEDULED_EVENT: ScheduledEventHandler(context=self.context),
            VirtualDesktopEventType.USER_DISABLED_EVENT: UserDisabledEventHandler(context=self.context),
            VirtualDesktopEventType.USER_CREATED_EVENT: UserCreatedEventHandler(context=self.context),
            VirtualDesktopEventType.IDEA_SESSION_RESUME_SESSION_COMMAND_PROGRESS_EVENT: IDEAResumeSessionCommandProgressEventHandler(context=self.context),
            VirtualDesktopEventType.ENABLE_USERDATA_WINDOWS_COMMAND_PROGRESS_EVENT: EnableUserdataWindowsCommandProgressEventListener(context=self.context),
            VirtualDesktopEventType.DISABLE_USERDATA_WINDOWS_COMMAND_PROGRESS_EVENT: DisableUserdataWindowsCommandProgressEventListener(context=self.context),
            VirtualDesktopEventType.IDEA_SESSION_CPU_UTILIZATION_COMMAND_PROGRESS_EVENT: IDEASessionCPUUtilizationCommandProgressEventHandler(context=self.context)
        }

        self.WAIT_TIME = wait_time

        super().__init__(thread_number=thread_number, target=self._monitor_queue)

    def _monitor_queue(self):
        while not self.exit.is_set():
            try:
                self.poll_and_process_queue()
                self.poll_and_process_db()
            except Exception as e:
                self._logger.exception(f'failed to process sqs queue: {e}')

    def poll_and_process_queue(self):
        response = self.context.aws().sqs().receive_message(
            AttributeNames=['All'],
            QueueUrl=self.context.config().get_string('virtual-desktop-controller.events_sqs_queue_url', required=True),
            MaxNumberOfMessages=self.NUM_OF_MESSAGES,
            # ENSURE LONG POLLING
            WaitTimeSeconds=self.WAIT_TIME
        )

        delete_message_info = []
        do_not_process_message_group_ids = set()
        for message in Utils.get_value_as_list('Messages', response, []):
            message_id = Utils.get_value_as_string('MessageId', message, None)
            self._logger.debug(f'[msg-id: {message_id}] processing message')
            message_group_id = Utils.get_value_as_string('MessageGroupId', Utils.get_value_as_dict('Attributes', message, {}), '')
            sender_id = Utils.get_value_as_string('SenderId', Utils.get_value_as_dict('Attributes', message, {}), '')
            md5checksum = Utils.get_value_as_string('MD5OfBody', message, None)

            message_body_str = Utils.get_value_as_string('Body', message, None)
            should_delete_message = False

            if not self._is_checksum_valid(md5checksum, message_body_str):
                self._logger.error(f'[msg-id: {message_id}] Invalid checksum. Ignoring message')
                should_delete_message = True
            else:
                message_body = Utils.from_json(message_body_str)
                event = VirtualDesktopEvent(**message_body)

                self._logger.info(f'[msg-id: {message_id}] Handling message of type {event.event_type}')
                if Utils.is_empty(event.event_type):
                    # There is some error. DO NOT PROCESS. IGNORE MESSAGE.
                    self._logger.error(f'Error in message {message_body}')
                    should_delete_message = True

                elif event.event_type not in self.EVENT_HANDLER_MAP:
                    self._logger.error(f'[msg-id: {message_id}] Invalid detail_type: {event.event_type}')
                    should_delete_message = True

                elif message_group_id not in do_not_process_message_group_ids:
                    try:
                        self.EVENT_HANDLER_MAP[event.event_type].handle_event(message_id, sender_id, event)
                        should_delete_message = True
                        self._logger.info(f'[msg-id: {message_id}] Message handled successfully')
                    except SocaException as e:
                        should_delete_message = False
                        if e.error_code == errorcodes.DO_NOT_DELETE_MESSAGE:
                            # We have raised this exception intentionally, no need to print stacktrace for the same.
                            # The intention is to force the message processing again since certain conditions are not met yet.
                            self.EVENT_HANDLER_MAP[event.event_type].log_info(message_id=message_id, message=f'{e.message}')
                        elif e.error_code == errorcodes.MESSAGE_SOURCE_VALIDATION_FAILED:
                            # We have raised this exception intentionally, no need to print stacktrace for the same.
                            # The error denotes that the message was not sent from the trusted source and needs to be ignored
                            should_delete_message = True
                            self.EVENT_HANDLER_MAP[event.event_type].log_info(message_id=message_id, message=f'{e.message}')
                        else:
                            self.EVENT_HANDLER_MAP[event.event_type].log_exception(message_id=message_id, exception=e)
                    except Exception as e:
                        should_delete_message = False
                        self._logger.exception(f'[msg-id: {message_id}] Error handling message. Error: {e}')
                elif message_group_id in do_not_process_message_group_ids:
                    self._logger.debug(f'[msg-id: {message_id}] Issue in handling message of type {event.event_type}. Because for prior errors in message_group_id: {message_group_id}. Will not delete the message')
                else:
                    self._logger.debug(f'[msg-id: {message_id}] Issue in handling message of type {event.event_type}. Will not delete the message')

            if should_delete_message:
                delete_message_info.append({
                    'Id': message_id,
                    'ReceiptHandle': Utils.get_value_as_string('ReceiptHandle', message, None)
                })
            else:
                # this message has not been processed because of error.
                # Any messages with this same message group id, SHOULD not be processed.
                do_not_process_message_group_ids.add(message_group_id)

        if len(delete_message_info) > 0:
            _ = self.context.aws().sqs().delete_message_batch(
                QueueUrl=self.context.config().get_string('virtual-desktop-controller.events_sqs_queue_url', required=True),
                Entries=delete_message_info
            )
            # self._logger.info(f'Delete message response {response}')

    @staticmethod
    def _is_checksum_valid(md5checksum: str, body: str) -> bool:
        return Utils.md5(body) == md5checksum

    def poll_and_process_db(self):
        pass
