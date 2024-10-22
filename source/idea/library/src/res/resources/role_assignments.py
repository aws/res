#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Dict, List, Optional

import res.constants as constants  # type: ignore
from res.resources import accounts, projects  # type: ignore
from res.utils import table_utils  # type: ignore

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

GSI_RESOURCE_KEY = "resource-key-index"
ROLE_ASSIGNMENTS_TABLE_NAME = "authz.role-assignments"


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
