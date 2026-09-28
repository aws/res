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

from datamodel.models.backend.project import Project
from datamodel.models.backend.virtual_desktop_permission_profile import (
    VirtualDesktopPermissionProfile,
)
from datamodel.models.backend.virtual_desktop_software_stack import (
    VirtualDesktopSoftwareStack,
)

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
SOFTWARE_STACK_DB_AFFINITY_KEY = "affinity"
SOFTWARE_STACK_DB_TENANCY_KEY = "tenancy"
SOFTWARE_STACK_DB_HOST_ID_KEY = "host_id"
SOFTWARE_STACK_DB_HOST_RESOURCE_GROUP_ARN_KEY = "host_resource_group_arn"
SOFTWARE_STACK_DB_ALLOWED_INSTANCE_TYPES_KEY = "allowed_instance_types"
SOFTWARE_STACK_DB_VERSION_KEY = "version"

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


# Fields used to decide whether two software stacks / permission profiles
# represent the same resource for snapshot-apply purposes. List-valued fields
# (projects, allowed_instance_types, permissions) are compared as unordered
# sets — list order isn't stable across environments.

_SOFTWARE_STACK_SCALAR_COMPARE_FIELDS = (
    "name",
    "base_os",
    "description",
    "ami_id",
    "min_storage",
    "min_ram",
    "gpu",
    "placement",
)

_PERMISSION_PROFILE_SCALAR_COMPARE_FIELDS = (
    "profile_id",
    "title",
    "description",
)


def software_stacks_equal(
    a: VirtualDesktopSoftwareStack,
    b: VirtualDesktopSoftwareStack,
) -> bool:
    if not all(
        getattr(a, f) == getattr(b, f) for f in _SOFTWARE_STACK_SCALAR_COMPARE_FIELDS
    ):
        return False
    a_project_ids = sorted(p.project_id for p in (a.projects or []))
    b_project_ids = sorted(p.project_id for p in (b.projects or []))
    if a_project_ids != b_project_ids:
        return False
    a_instance_types = sorted(a.allowed_instance_types or [])
    b_instance_types = sorted(b.allowed_instance_types or [])
    return a_instance_types == b_instance_types


def permission_profiles_equal(
    a: VirtualDesktopPermissionProfile,
    b: VirtualDesktopPermissionProfile,
) -> bool:
    if not all(
        getattr(a, f) == getattr(b, f)
        for f in _PERMISSION_PROFILE_SCALAR_COMPARE_FIELDS
    ):
        return False
    # Compare permissions as a {key -> permission} map so order doesn't matter.
    a_perms = {p.key: p for p in (a.permissions or [])}
    b_perms = {p.key: p for p in (b.permissions or [])}
    return a_perms == b_perms


def rebuild_software_stack_projects_from_db_dict(
    software_stack: VirtualDesktopSoftwareStack,
    db_entry: dict,
) -> None:
    """Rebuild ``projects`` from the DB record's flat project-id list since
    ``from_ddb_dict`` doesn't hydrate them into ``Project`` objects."""
    software_stack.projects = [
        Project(project_id=pid)
        for pid in (db_entry.get(SOFTWARE_STACK_DB_PROJECTS_KEY) or [])
    ]
