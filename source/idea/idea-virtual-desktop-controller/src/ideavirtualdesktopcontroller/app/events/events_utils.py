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
from typing import Optional, Dict

import ideavirtualdesktopcontroller
from ideadatamodel import VirtualDesktopBaseOS, VirtualDesktopSessionState
from ideasdk.utils import Utils
from ideavirtualdesktopcontroller.app.clients.events_client.events_client import VirtualDesktopEventType, VirtualDesktopEvent


class EventsUtils:
    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        self.context = context

    def publish_user_disabled_event(self, username: str):
        self.context.events_client.publish_event(
            event=VirtualDesktopEvent(
                event_group_id=username,
                event_type=VirtualDesktopEventType.USER_DISABLED_EVENT,
                detail={
                    'username': username
                }
            )
        )

    def publish_dcv_host_reboot_complete_event(self, idea_session_id: str, idea_session_owner: str, instance_id: str):
        self.context.events_client.publish_event(
            event=VirtualDesktopEvent(
                event_group_id=idea_session_id,
                event_type=VirtualDesktopEventType.DCV_HOST_REBOOT_COMPLETE_EVENT,
                detail={
                    'idea_session_id': idea_session_id,
                    'idea_session_owner': idea_session_owner,
                    'instance_id': instance_id
                }
            )
        )

    def publish_scheduled_event(self, time: str):
        self.context.events_client.publish_event(
            event=VirtualDesktopEvent(
                event_group_id='SCHEDULED_EVENT',
                event_type=VirtualDesktopEventType.SCHEDULED_EVENT,
                detail={
                    'time': time
                }
            )
        )

    def publish_idea_session_software_stack_updated_event(self, idea_session_id: str, idea_session_owner: str, new_software_stack: Dict):
        self.context.events_client.publish_event(
            event=VirtualDesktopEvent(
                event_group_id=idea_session_id,
                event_type=VirtualDesktopEventType.IDEA_SESSION_SOFTWARE_STACK_UPDATED_EVENT,
                detail={
                    'idea_session_id': idea_session_id,
                    'idea_session_owner': idea_session_owner,
                    'new_software_stack': new_software_stack
                }
            )
        )

    def publish_update_session_permissions_event(self, idea_session_id: str, new_name: Optional[str], new_instance_type: Optional[str], new_state: Optional[VirtualDesktopSessionState]):
        self.context.events_client.publish_event(
            event=VirtualDesktopEvent(
                event_group_id=idea_session_id,
                event_type=VirtualDesktopEventType.IDEA_SESSION_PERMISSIONS_UPDATE_EVENT,
                detail={
                    'idea_session_id': idea_session_id,
                    'new_name': new_name,
                    'new_instance_type': new_instance_type,
                    'new_state': new_state,
                    'timestamp': Utils.current_time_ms()
                }
            )
        )

    def publish_enforce_session_permissions_event(self, idea_session_id: str, idea_session_owner: str):
        self.context.events_client.publish_event(
            event=VirtualDesktopEvent(
                event_group_id=idea_session_id,
                event_type=VirtualDesktopEventType.IDEA_SESSION_PERMISSIONS_ENFORCE_EVENT,
                detail={
                    'idea_session_id': idea_session_id,
                    'idea_session_owner': idea_session_owner,
                    'timestamp': Utils.current_time_ms()
                }
            )
        )

    def publish_ec2_state_updated_event(self, idea_session_id: str, idea_session_owner: str, instance_id: str, state: str):
        self.context.events_client.publish_event(
            event=VirtualDesktopEvent(
                event_group_id=idea_session_id,
                event_type=VirtualDesktopEventType.EC2_INSTANCE_STATE_CHANGED_EVENT,
                detail={
                    'idea_session_id': idea_session_id,
                    'idea_session_owner': idea_session_owner,
                    'instance_id': instance_id,
                    'state': state,
                    'timestamp': Utils.current_time_ms()
                }
            )
        )

    def publish_enable_userdata_windows_status_event(self, idea_session_id: str, idea_session_owner: str, instance_id: str, status: str, command_id: str, software_stack_id: str):
        self.context.events_client.publish_event(
            event=VirtualDesktopEvent(
                event_group_id=idea_session_id,
                event_type=VirtualDesktopEventType.ENABLE_USERDATA_WINDOWS_COMMAND_PROGRESS_EVENT,
                detail={
                    'idea_session_id': idea_session_id,
                    'idea_session_owner': idea_session_owner,
                    'instance_id': instance_id,
                    'status': status,
                    'command_id': command_id,
                    'software_stack_id': software_stack_id,
                    'timestamp': Utils.current_time_ms()
                }
            )
        )

    def publish_disable_userdata_windows_status_event(self, idea_session_id: str, idea_session_owner: str, instance_id: str, status: str, command_id: str):
        self.context.events_client.publish_event(
            event=VirtualDesktopEvent(
                event_group_id=idea_session_id,
                event_type=VirtualDesktopEventType.DISABLE_USERDATA_WINDOWS_COMMAND_PROGRESS_EVENT,
                detail={
                    'idea_session_id': idea_session_id,
                    'idea_session_owner': idea_session_owner,
                    'instance_id': instance_id,
                    'status': status,
                    'command_id': command_id,
                    'timestamp': Utils.current_time_ms()
                }
            )
        )

    def publish_resume_session_command_status_event(self, idea_session_id: str, idea_session_owner: str, instance_id: str, status: str, command_id: str):
        self.context.events_client.publish_event(
            event=VirtualDesktopEvent(
                event_group_id=idea_session_id,
                event_type=VirtualDesktopEventType.IDEA_SESSION_RESUME_SESSION_COMMAND_PROGRESS_EVENT,
                detail={
                    'idea_session_id': idea_session_id,
                    'idea_session_owner': idea_session_owner,
                    'instance_id': instance_id,
                    'status': status,
                    'command_id': command_id,
                    'timestamp': Utils.current_time_ms()
                }
            )
        )

    def publish_idea_session_cpu_utilization_command_status_event(self, idea_session_id: str, idea_session_owner: str, instance_id: str, status: str, command_id: str):
        self.context.events_client.publish_event(
            event=VirtualDesktopEvent(
                event_group_id=idea_session_id,
                event_type=VirtualDesktopEventType.IDEA_SESSION_CPU_UTILIZATION_COMMAND_PROGRESS_EVENT,
                detail={
                    'idea_session_id': idea_session_id,
                    'idea_session_owner': idea_session_owner,
                    'instance_id': instance_id,
                    'status': status,
                    'command_id': command_id,
                    'timestamp': Utils.current_time_ms()
                }
            )
        )

    def publish_validate_software_stack_creation_event(self, software_stack_id: str, base_os: VirtualDesktopBaseOS, idea_session_id: str, idea_session_owner: str, instance_id: str):
        self.context.events_client.publish_event(
            event=VirtualDesktopEvent(
                event_group_id=software_stack_id,
                event_type=VirtualDesktopEventType.VALIDATE_SOFTWARE_STACK_CREATION_EVENT,
                detail={
                    'idea_session_id': idea_session_id,
                    'idea_session_owner': idea_session_owner,
                    'instance_id': instance_id,
                    'software_stack_id': software_stack_id,
                    'software_stack_base_os': base_os,
                    'timestamp': Utils.current_time_ms()
                }
            )
        )

    def publish_validate_dcv_session_creation_event(self, idea_session_id: str, idea_session_owner: str):
        self.context.events_client.publish_event(
            event=VirtualDesktopEvent(
                event_group_id=idea_session_id,
                event_type=VirtualDesktopEventType.VALIDATE_DCV_SESSION_CREATION_EVENT,
                detail={
                    'idea_session_id': idea_session_id,
                    'idea_session_owner': idea_session_owner,
                    'timestamp': Utils.current_time_ms()
                }
            )
        )

    def publish_validate_dcv_session_deletion_event(self, idea_session_id: str, idea_session_owner: str):
        self.context.events_client.publish_event(
            event=VirtualDesktopEvent(
                event_group_id=idea_session_id,
                event_type=VirtualDesktopEventType.VALIDATE_DCV_SESSION_DELETION_EVENT,
                detail={
                    'idea_session_id': idea_session_id,
                    'idea_session_owner': idea_session_owner
                }
            )
        )

    def publish_idea_session_scheduled_resume_event(self, idea_session_id: str, idea_session_owner: str):
        self.context.events_client.publish_event(
            event=VirtualDesktopEvent(
                event_group_id=idea_session_id,
                event_type=VirtualDesktopEventType.IDEA_SESSION_SCHEDULED_RESUME_EVENT,
                detail={
                    'idea_session_id': idea_session_id,
                    'idea_session_owner': idea_session_owner
                }
            )
        )

    def publish_idea_session_scheduled_stop_event(self, idea_session_id: str, idea_session_owner: str):
        self.context.events_client.publish_event(
            event=VirtualDesktopEvent(
                event_group_id=idea_session_id,
                event_type=VirtualDesktopEventType.IDEA_SESSION_SCHEDULED_STOP_EVENT,
                detail={
                    'idea_session_id': idea_session_id,
                    'idea_session_owner': idea_session_owner
                }
            )
        )

    def publish_idea_session_terminate_event(self, idea_session_id: str, idea_session_owner: str, force: bool = False):
        self.context.events_client.publish_event(
            event=VirtualDesktopEvent(
                event_group_id=idea_session_id,
                event_type=VirtualDesktopEventType.IDEA_SESSION_TERMINATE_EVENT,
                detail={
                    'idea_session_id': idea_session_id,
                    'idea_session_owner': idea_session_owner,
                    'timestamp': Utils.current_time_ms(),
                    'force': force
                }
            )
        )
