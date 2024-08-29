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

# Note: The idea-virtual-desktop-controller module is not available in the cluster manager, so we have to
# duplicate the code for converting between Python dictionary and virtual desktop specific object here.

from ideadatamodel import (
    VirtualDesktopSoftwareStack,
    VirtualDesktopBaseOS,
    VirtualDesktopArchitecture,
    VirtualDesktopGPU,
    VirtualDesktopPermission,
    VirtualDesktopPermissionProfile,
    Project,
    SocaMemory,
    SocaMemoryUnit,
)

from ideasdk.utils.utils import Utils

from typing import Dict, Optional

SOFTWARE_STACK_DB_BASE_OS_KEY = "base_os"
SOFTWARE_STACK_DB_STACK_ID_KEY = "stack_id"
SOFTWARE_STACK_DB_NAME_KEY = "name"
SOFTWARE_STACK_DB_DESCRIPTION_KEY = "description"
SOFTWARE_STACK_DB_CREATED_ON_KEY = "created_on"
SOFTWARE_STACK_DB_UPDATED_ON_KEY = "updated_on"
SOFTWARE_STACK_DB_AMI_ID_KEY = "ami_id"
SOFTWARE_STACK_DB_ENABLED_KEY = "enabled"
SOFTWARE_STACK_DB_MIN_STORAGE_VALUE_KEY = "min_storage_value"
SOFTWARE_STACK_DB_MIN_STORAGE_UNIT_KEY = "min_storage_unit"
SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY = "min_ram_value"
SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY = "min_ram_unit"
SOFTWARE_STACK_DB_ARCHITECTURE_KEY = "architecture"
SOFTWARE_STACK_DB_GPU_KEY = "gpu"
SOFTWARE_STACK_DB_PROJECTS_KEY = "projects"
SOFTWARE_STACK_DB_PROJECT_ID_KEY = "project_id"
SOFTWARE_STACK_DB_PROJECT_NAME_KEY = "name"
SOFTWARE_STACK_DB_PROJECT_TITLE_KEY = "title"

PERMISSION_PROFILE_DB_HASH_KEY = "profile_id"
PERMISSION_PROFILE_DB_TITLE_KEY = "title"
PERMISSION_PROFILE_DB_DESCRIPTION_KEY = "description"
PERMISSION_PROFILE_DB_CREATED_ON_KEY = "created_on"
PERMISSION_PROFILE_DB_UPDATED_ON_KEY = "updated_on"

ROLE_ASSIGNMENT_DB_RESOURCE_KEY = "resource_key"
ROLE_ASSIGNMENT_DB_ACTOR_KEY = "actor_key"
ROLE_ASSIGNMENT_DB_RESOURCE_ID_KEY = "resource_id"
ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_KEY = "resource_type"
ROLE_ASSIGNMENT_DB_ACTOR_ID_KEY = "actor_id"
ROLE_ASSIGNMENT_DB_ACTOR_TYPE_KEY = "actor_type"
ROLE_ASSIGNMENT_DB_ROLD_ID_KEY = "role_id"
ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_PROJECT_VALUE = "project"
ROLE_ASSIGNMENT_DB_ACTOR_TYPE_USER_VALUE = "user"
ROLE_ASSIGNMENT_DB_ACTOR_TYPE_GROUP_VALUE = "group"
ROLE_ASSIGNMENT_DB_ROLD_ID_PROJECT_MEMBER_VALUE = "project_member"

ROLE_DB_ROLE_ID_KEY = "role_id"

PROJECT_DB_PROJECT_ID_KEY = "project_id"
PROJECT_DB_OLD_LDAP_GROUPS_KEY = "ldap_groups"
PROJECT_DB_OLD_USERS_KEY = "users"

def convert_db_dict_to_software_stack_object(
    db_entry: dict,
) -> Optional[VirtualDesktopSoftwareStack]:
    if Utils.is_empty(db_entry):
        return None

    software_stack = VirtualDesktopSoftwareStack(
        base_os=VirtualDesktopBaseOS(db_entry.get(SOFTWARE_STACK_DB_BASE_OS_KEY)),
        stack_id=db_entry.get(SOFTWARE_STACK_DB_STACK_ID_KEY),
        name=db_entry.get(SOFTWARE_STACK_DB_NAME_KEY),
        description=db_entry.get(SOFTWARE_STACK_DB_DESCRIPTION_KEY),
        created_on=Utils.to_datetime(db_entry.get(SOFTWARE_STACK_DB_CREATED_ON_KEY)),
        updated_on=Utils.to_datetime(db_entry.get(SOFTWARE_STACK_DB_UPDATED_ON_KEY)),
        ami_id=db_entry.get(SOFTWARE_STACK_DB_AMI_ID_KEY),
        enabled=db_entry.get(SOFTWARE_STACK_DB_ENABLED_KEY),
        min_storage=SocaMemory(
            value=db_entry.get(SOFTWARE_STACK_DB_MIN_STORAGE_VALUE_KEY),
            unit=SocaMemoryUnit(db_entry.get(SOFTWARE_STACK_DB_MIN_STORAGE_UNIT_KEY)),
        ),
        min_ram=SocaMemory(
            value=db_entry.get(SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY),
            unit=SocaMemoryUnit(db_entry.get(SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY)),
        ),
        architecture=VirtualDesktopArchitecture(
            db_entry.get(SOFTWARE_STACK_DB_ARCHITECTURE_KEY)
        ),
        gpu=VirtualDesktopGPU(db_entry.get(SOFTWARE_STACK_DB_GPU_KEY)),
        projects=[],
    )

    for project_id in db_entry.get(SOFTWARE_STACK_DB_PROJECTS_KEY, []):
        software_stack.projects.append(Project(project_id=project_id))

    return software_stack


def convert_software_stack_object_to_db_dict(
    software_stack: VirtualDesktopSoftwareStack,
) -> Dict:
    if Utils.is_empty(software_stack):
        return {}

    db_dict = {
        SOFTWARE_STACK_DB_BASE_OS_KEY: software_stack.base_os,
        SOFTWARE_STACK_DB_STACK_ID_KEY: software_stack.stack_id,
        SOFTWARE_STACK_DB_NAME_KEY: software_stack.name,
        SOFTWARE_STACK_DB_DESCRIPTION_KEY: software_stack.description,
        SOFTWARE_STACK_DB_CREATED_ON_KEY: Utils.to_milliseconds(
            software_stack.created_on
        ),
        SOFTWARE_STACK_DB_UPDATED_ON_KEY: Utils.to_milliseconds(
            software_stack.updated_on
        ),
        SOFTWARE_STACK_DB_AMI_ID_KEY: software_stack.ami_id,
        SOFTWARE_STACK_DB_ENABLED_KEY: software_stack.enabled,
        SOFTWARE_STACK_DB_MIN_STORAGE_VALUE_KEY: str(software_stack.min_storage.value),
        SOFTWARE_STACK_DB_MIN_STORAGE_UNIT_KEY: software_stack.min_storage.unit,
        SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY: str(software_stack.min_ram.value),
        SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY: software_stack.min_ram.unit,
        SOFTWARE_STACK_DB_ARCHITECTURE_KEY: software_stack.architecture,
        SOFTWARE_STACK_DB_GPU_KEY: software_stack.gpu,
    }

    project_ids = []
    if software_stack.projects:
        for project in software_stack.projects:
            project_ids.append(project.project_id)

    db_dict[SOFTWARE_STACK_DB_PROJECTS_KEY] = project_ids
    return db_dict


def convert_db_dict_to_permission_profile_object(
    db_dict: Dict, permission_types: list[VirtualDesktopPermission]
) -> Optional[VirtualDesktopPermissionProfile]:
    permission_profile = VirtualDesktopPermissionProfile(
        profile_id=db_dict.get(PERMISSION_PROFILE_DB_HASH_KEY, ""),
        title=db_dict.get(PERMISSION_PROFILE_DB_TITLE_KEY, ""),
        description=db_dict.get(PERMISSION_PROFILE_DB_DESCRIPTION_KEY, ""),
        permissions=[],
        created_on=Utils.to_datetime(
            db_dict.get(PERMISSION_PROFILE_DB_CREATED_ON_KEY, 0)
        ),
        updated_on=Utils.to_datetime(
            db_dict.get(PERMISSION_PROFILE_DB_UPDATED_ON_KEY, 0)
        ),
    )

    for permission_type in permission_types:
        permission_profile.permissions.append(
            VirtualDesktopPermission(
                key=permission_type.key,
                name=permission_type.name,
                description=permission_type.description,
                enabled=db_dict.get(permission_type.key, False),
            )
        )

    return permission_profile


def convert_permission_profile_object_to_db_dict(
    permission_profile: VirtualDesktopPermissionProfile,
    permission_types: list[VirtualDesktopPermission],
) -> Dict:
    db_dict = {
        PERMISSION_PROFILE_DB_HASH_KEY: permission_profile.profile_id,
        PERMISSION_PROFILE_DB_TITLE_KEY: permission_profile.title,
        PERMISSION_PROFILE_DB_DESCRIPTION_KEY: permission_profile.description,
        PERMISSION_PROFILE_DB_CREATED_ON_KEY: Utils.to_milliseconds(
            permission_profile.created_on
        ),
        PERMISSION_PROFILE_DB_UPDATED_ON_KEY: Utils.to_milliseconds(
            permission_profile.updated_on
        ),
    }

    for permission_type in permission_types:
        db_dict[permission_type.key] = False
        permission_entry = permission_profile.get_permission(permission_type.key)
        if Utils.is_not_empty(permission_entry):
            db_dict[permission_type.key] = permission_entry.enabled

    return db_dict
