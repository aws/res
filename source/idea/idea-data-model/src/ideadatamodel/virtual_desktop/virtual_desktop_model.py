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

__all__ = (
    'VirtualDesktopSessionState',
    'VirtualDesktopSessionType',
    'VirtualDesktopServer',
    'VirtualDesktopSession',
    'VirtualDesktopApplicationProfile',
    'VirtualDesktopSessionScreenshot',
    'VirtualDesktopSessionConnectionInfo',
    'VirtualDesktopBaseOS',
    'VirtualDesktopGPU',
    'VirtualDesktopArchitecture',
    'VirtualDesktopSoftwareStack',
    'DayOfWeek',
    'VirtualDesktopScheduleType',
    'VirtualDesktopSchedule',
    'VirtualDesktopWeekSchedule',
    'VirtualDesktopPermission',
    'VirtualDesktopPermissionProfile',
    'VirtualDesktopSessionPermission',
    'VirtualDesktopSessionPermissionActorType',
    'VirtualDesktopSessionBatchResponsePayload'
)

from ideadatamodel import SocaBaseModel, SocaMemory, SocaBatchResponsePayload, Project, constants

from typing import Optional, List
from datetime import datetime
from enum import Enum


class VirtualDesktopSessionState(str, Enum):
    PROVISIONING = 'PROVISIONING'
    CREATING = 'CREATING'
    INITIALIZING = 'INITIALIZING'
    READY = 'READY'
    RESUMING = 'RESUMING'
    STOPPING = 'STOPPING'
    STOPPED = 'STOPPED'
    ERROR = 'ERROR'
    DELETING = 'DELETING'
    DELETED = 'DELETED'


class VirtualDesktopSessionType(str, Enum):
    CONSOLE = 'CONSOLE'
    VIRTUAL = 'VIRTUAL'


class VirtualDesktopGPU(str, Enum):
    NO_GPU = 'NO_GPU'
    NVIDIA = 'NVIDIA'
    AMD = 'AMD'


class VirtualDesktopArchitecture(str, Enum):
    X86_64 = 'x86_64'
    ARM64 = 'arm64'


class DayOfWeek(str, Enum):
    MONDAY = 'monday'
    TUESDAY = 'tuesday'
    WEDNESDAY = 'wednesday'
    THURSDAY = 'thursday'
    FRIDAY = 'friday'
    SATURDAY = 'saturday'
    SUNDAY = 'sunday'


class VirtualDesktopScheduleType(str, Enum):
    WORKING_HOURS = 'WORKING_HOURS'
    STOP_ALL_DAY = 'STOP_ALL_DAY'
    START_ALL_DAY = 'START_ALL_DAY'
    CUSTOM_SCHEDULE = 'CUSTOM_SCHEDULE'
    NO_SCHEDULE = 'NO_SCHEDULE'


class VirtualDesktopBaseOS(str, Enum):
    AMAZON_LINUX2 = constants.OS_AMAZONLINUX2
    RHEL8 = constants.OS_RHEL8
    RHEL9 = constants.OS_RHEL9
    UBUNTU2204 = constants.OS_UBUNTU2204
    WINDOWS = constants.OS_WINDOWS


class VirtualDesktopSessionPermissionActorType(str, Enum):
    USER = 'USER'
    GROUP = 'GROUP'


class VirtualDesktopSessionScreenshot(SocaBaseModel):
    image_type: Optional[str]
    image_data: Optional[str]
    dcv_session_id: Optional[str]
    idea_session_id: Optional[str]
    idea_session_owner: Optional[str]
    create_time: Optional[str]
    failure_reason: Optional[str]


class VirtualDesktopSessionConnectionInfo(SocaBaseModel):
    dcv_session_id: Optional[str]
    idea_session_id: Optional[str]
    idea_session_owner: Optional[str]
    endpoint: Optional[str]
    username: Optional[str]
    web_url_path: Optional[str]
    access_token: Optional[str]
    failure_reason: Optional[str]


class VirtualDesktopSoftwareStack(SocaBaseModel):
    stack_id: Optional[str]
    base_os: Optional[VirtualDesktopBaseOS]
    name: Optional[str]
    description: Optional[str]
    created_on: Optional[datetime]
    updated_on: Optional[datetime]
    ami_id: Optional[str]
    failure_reason: Optional[str]
    enabled: Optional[bool]
    min_storage: Optional[SocaMemory]
    min_ram: Optional[SocaMemory]
    architecture: Optional[VirtualDesktopArchitecture]
    gpu: Optional[VirtualDesktopGPU]
    projects: Optional[List[Project]] = []

    def __eq__(self, other):
        eq = True
        eq = eq and self.base_os == other.base_os
        eq = eq and self.name == other.name
        eq = eq and self.description == other.description
        eq = eq and self.ami_id == other.ami_id
        eq = eq and self.min_storage == other.min_storage
        eq = eq and self.min_ram == other.min_ram
        eq = eq and self.gpu == other.gpu

        self_project_ids = [project.project_id for project in self.projects] if self.projects else []
        other_project_ids = [project.project_id for project in other.projects] if other.projects else []
        eq = eq and len(self_project_ids) == len(other_project_ids)
        eq = eq and all(project_id in self_project_ids for project_id in other_project_ids)

        return eq


class VirtualDesktopServer(SocaBaseModel):
    server_id: Optional[str]
    idea_sesssion_id: Optional[str]
    idea_session_owner: Optional[str]
    instance_id: Optional[str]
    instance_type: Optional[str]
    private_ip: Optional[str]
    private_dns_name: Optional[str]
    public_ip: Optional[str]
    public_dns_name: Optional[str]
    availability: Optional[str]
    unavailability_reason: Optional[str]
    console_session_count: Optional[int]
    virtual_session_count: Optional[int]
    max_concurrent_sessions_per_user: Optional[int]
    max_virtual_sessions: Optional[int]
    state: Optional[str]
    locked: Optional[bool]

    instance_type: Optional[str]
    root_volume_size: Optional[SocaMemory]
    root_volume_iops: Optional[int]
    instance_profile_arn: Optional[str]
    security_groups: Optional[List[str]]
    subnet_id: Optional[str]
    key_pair_name: Optional[str]


class VirtualDesktopSchedule(SocaBaseModel):
    schedule_id: Optional[str]
    idea_session_id: Optional[str]
    idea_session_owner: Optional[str]
    day_of_week: Optional[DayOfWeek]
    start_up_time: Optional[str]
    shut_down_time: Optional[str]
    schedule_type: Optional[VirtualDesktopScheduleType]


class VirtualDesktopPermission(SocaBaseModel):
    key: Optional[str]
    name: Optional[str]
    description: Optional[str]
    enabled: Optional[bool]


class VirtualDesktopWeekSchedule(SocaBaseModel):
    monday: Optional[VirtualDesktopSchedule]
    tuesday: Optional[VirtualDesktopSchedule]
    wednesday: Optional[VirtualDesktopSchedule]
    thursday: Optional[VirtualDesktopSchedule]
    friday: Optional[VirtualDesktopSchedule]
    saturday: Optional[VirtualDesktopSchedule]
    sunday: Optional[VirtualDesktopSchedule]


class VirtualDesktopPermissionProfile(SocaBaseModel):
    profile_id: Optional[str]
    title: Optional[str]
    description: Optional[str]
    permissions: Optional[List[VirtualDesktopPermission]]
    created_on: Optional[datetime]
    updated_on: Optional[datetime]

    def __eq__(self, other):
        eq = True
        eq = eq and self.profile_id == other.profile_id
        eq = eq and self.title == other.title
        eq = eq and self.description == other.description

        self_permissions = self.permissions if self.permissions else []
        other_permissions = other.permissions if other.permissions else []
        eq = eq and len(self_permissions) == len(other_permissions)
        eq = eq and all(permission in self_permissions for permission in other_permissions)

        return eq

    def get_permission(self, permission_key: str) -> Optional[VirtualDesktopPermission]:
        if self.permissions is None:
            return None

        for permission in self.permissions:
            if permission.key == permission_key:
                return permission
        return None


class VirtualDesktopSessionPermission(SocaBaseModel):
    idea_session_id: Optional[str]
    idea_session_owner: Optional[str]
    idea_session_name: Optional[str]
    idea_session_instance_type: Optional[str]
    idea_session_state: Optional[VirtualDesktopSessionState]
    idea_session_base_os: Optional[VirtualDesktopBaseOS]
    idea_session_created_on: Optional[datetime]
    idea_session_hibernation_enabled: Optional[bool]
    idea_session_type: Optional[VirtualDesktopSessionType]
    permission_profile: Optional[VirtualDesktopPermissionProfile]
    actor_type: Optional[VirtualDesktopSessionPermissionActorType]
    actor_name: Optional[str]
    created_on: Optional[datetime]
    updated_on: Optional[datetime]
    expiry_date: Optional[datetime]

    failure_reason: Optional[str]


class VirtualDesktopSession(SocaBaseModel):
    dcv_session_id: Optional[str]
    idea_session_id: Optional[str]
    base_os: Optional[VirtualDesktopBaseOS]
    name: Optional[str]
    owner: Optional[str]
    type: Optional[VirtualDesktopSessionType]
    server: Optional[VirtualDesktopServer]
    created_on: Optional[datetime]
    updated_on: Optional[datetime]
    state: Optional[VirtualDesktopSessionState]
    description: Optional[str]
    software_stack: Optional[VirtualDesktopSoftwareStack]
    project: Optional[Project]
    schedule: Optional[VirtualDesktopWeekSchedule]
    connection_count: Optional[int]
    force: Optional[bool]
    hibernation_enabled: Optional[bool]
    is_launched_by_admin: Optional[bool]
    locked: Optional[bool]
    tags: Optional[list[dict]]

    # Transient field, to be used for API responses only.
    failure_reason: Optional[str]


class VirtualDesktopSessionBatchResponsePayload(SocaBatchResponsePayload):
    failed: Optional[List[VirtualDesktopSession]]
    success: Optional[List[VirtualDesktopSession]]


class VirtualDesktopApplicationProfile(SocaBaseModel):
    pass
