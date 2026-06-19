#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict, List, Optional

import res.constants as constants  # type: ignore
from res.resources import accounts, projects, roles  # type: ignore
from res.utils import logging_utils, table_utils  # type: ignore

GSI_RESOURCE_KEY = "resource-key-index"
GSI_RESOURCE_KEY_HASH_KEY = ROLE_ASSIGNMENTS_DB_RANGE_KEY = "resource_key"
ROLE_ASSIGNMENTS_RESOURCE_ID_KEY = "resource_id"
ROLE_ASSIGNMENTS_RESOURCE_TYPE_KEY = "resource_type"
ROLE_ASSIGNMENTS_ROLE_ID_KEY = "role_id"
GSI_RESOURCE_KEY_RANGE_KEY = ROLE_ASSIGNMENTS_DB_HASH_KEY = "actor_key"
ROLE_ASSIGNMENTS_TABLE_NAME = "authz.role-assignments"
PERMISSION_CATEGORIES = ["vdis", "projects"]

logger = logging_utils.get_logger(ROLE_ASSIGNMENTS_TABLE_NAME)


def delete_role_assignment(role_assignment: Dict[str, str]) -> None:
    """
    Perform validations on the incoming actor/resource types
    :param actor_key:
    :param resource_key:
    """
    if not role_assignment.get("actor_key"):
        raise Exception("actor_key is required")
    if not role_assignment.get("resource_key"):
        raise Exception("resource_key is required")

    table_utils.delete_item(
        ROLE_ASSIGNMENTS_TABLE_NAME,
        key={
            "actor_key": role_assignment["actor_key"],
            "resource_key": role_assignment["resource_key"],
        },
    )
    logger.info(
        f"deleted role assignment of actor {role_assignment['actor_key']} to resource {role_assignment['resource_key']}"
    )


def get_role_assignment(actor_key: str, resource_key: str) -> Optional[Dict[str, Any]]:
    """
    Get role assignment for a given actor key and resource key
    :param actor_key:
    :param resource_key:
    :return role assignment
    """
    if not actor_key or not resource_key:
        raise Exception(
            "Either actor_key or resource_key is not provided",
        )

    _verify_actor_exists(*actor_key.split(":"))
    _verify_resource_exists(*resource_key.split(":"))

    logger.debug(
        f"get_role_assignments() - actor: {actor_key} resource: {resource_key}"
    )

    if not actor_key:
        raise Exception("actor_key is required")
    if not resource_key:
        raise Exception("resource_key is required")

    role_assignment: Optional[Dict[str, Any]] = table_utils.get_item(
        ROLE_ASSIGNMENTS_TABLE_NAME,
        key={"actor_key": actor_key, "resource_key": resource_key},
    )

    return role_assignment


def _verify_actor_exists(actor_id: str, actor_type: str) -> None:
    if not actor_id:
        raise Exception("actor_id is required")
    if not actor_type:
        raise Exception("actor_type is required")

    if actor_type == constants.ROLE_ASSIGNMENT_ACTOR_USER_TYPE:
        accounts.get_user(actor_id)
    elif actor_type == constants.ROLE_ASSIGNMENT_ACTOR_GROUP_TYPE:
        accounts.get_group(actor_id)


def _verify_resource_exists(resource_id: str, resource_type: str) -> None:
    if not resource_id:
        raise Exception("resource_id is required")
    if not resource_type:
        raise Exception("resource_type is required")

    if resource_type == "project":
        projects.get_project(project_id=resource_id)


def list_role_assignments(
    actor_key: str = "", resource_key: str = "", role_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List all role assignments by actor key, resource key or role ID.
    :param actor_key:
    :param resource_key:
    :param role_id:
    :return role assignments
    """
    if not actor_key and not resource_key:
        raise Exception("Either actor_key or resource_key is required")

    if resource_key:
        resource_type = (
            resource_key.split(":")[1] if len(resource_key.split(":")) == 2 else ""
        )
        if resource_type not in constants.VALID_ROLE_ASSIGNMENT_RESOURCE_TYPES:
            raise Exception(
                constants.INVALID_ROLE_ASSIGNMENT_RESOURCE_TYPE,
            )

    logger.info(
        f"list role assignments for {resource_key if not actor_key else actor_key}"
    )

    role_assignments: List[Dict[str, Any]] = []

    if actor_key and resource_key:
        role_assignment = get_role_assignment(actor_key, resource_key)
        if role_assignment:
            role_assignments.append(role_assignment)
    else:
        if actor_key:
            role_assignments = table_utils.query(
                ROLE_ASSIGNMENTS_TABLE_NAME, {"actor_key": actor_key}
            )
        elif resource_key:
            role_assignments = table_utils.query(
                ROLE_ASSIGNMENTS_TABLE_NAME,
                {"resource_key": resource_key},
                index_name=GSI_RESOURCE_KEY,
            )
        elif role_id:
            # This helps list all assignments for a role in the system
            # ToDo: update table to use a new GSI for role_id
            role_assignments = table_utils.scan(
                ROLE_ASSIGNMENTS_TABLE_NAME, {"role_id": role_id}
            )

    return role_assignments


def get_user_permissions(username: str, resource_key: str) -> set:
    """
    Resolve a user's effective permissions for a given resource.

    Flow:
    1. Get all role assignments for the user and their groups
    2. Filter to assignments matching the resource_key (e.g., "project-id:project")
    3. Collect the role_ids from those matching assignments
    4. Batch-fetch the role definitions
    5. Extract enabled permissions from each role's "vdis" and "projects" categories
    6. Return a flat set (e.g., {"vdis.create_sessions", "vdis.create_terminate_others_sessions"})
    """
    # Step 1-3: Find role_ids assigned to this user for the given resource
    role_ids = []
    list_role_assignments = list_role_assignments_for_user_and_groups(username)
    for item in list_role_assignments:
        if item.get(ROLE_ASSIGNMENTS_DB_RANGE_KEY) == resource_key:
            role_ids.append(item.get(ROLE_ASSIGNMENTS_ROLE_ID_KEY))

    # Step 4-6: Resolve roles into a flat permission set
    permissions = set()
    if role_ids:
        roles_data = roles.get_roles_batch(role_ids)
        for role in roles_data.values():
            for category in PERMISSION_CATEGORIES:
                if role.get(category):
                    for key, value in role[category].items():
                        if value:
                            permissions.add(f"{category}.{key}")
    return permissions


def list_role_assignments_for_user_and_groups(username: str) -> List[Dict[str, Any]]:
    """
    List all role assignments for a user and their groups
    :param username: username to get assignments for
    :return: combined list of role assignments
    """
    user = accounts.get_user(username)
    groups = user.get("additional_groups", [])

    assignments = []
    assignments.extend(list_role_assignments(actor_key=f"{username}:user"))
    for group in groups:
        assignments.extend(list_role_assignments(actor_key=f"{group}:group"))

    return assignments
