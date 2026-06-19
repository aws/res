#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict, List, Optional

import res.constants as constants  # type: ignore
import res.exceptions as exceptions  # type: ignore
from res.resources import accounts, projects  # type: ignore
from res.utils import logging_utils, table_utils, time_utils  # type: ignore

ROLES_TABLE_NAME = "authz.roles"
ROLES_DB_HASH_KEY = "role_id"
ROLES_DB_CREATED_ON_KEY = "created_on"
ROLES_DB_UPDATED_ON_KEY = "updated_on"
PROJECT_MEMBER_ROLE_ID = "project_member"
PROJECT_OWNER_ROLE_ID = "project_owner"
PROJECT_MEMBER_ROLE_NAME = "Project Member"
PROJECT_OWNER_ROLE_NAME = "Project Owner"

logger = logging_utils.get_logger(ROLES_TABLE_NAME)


def is_roles_table_empty() -> bool:
    """
    Check if authz roles DDB is empty
    :return whether permission profile DDB is empty
    """
    return table_utils.is_table_empty(ROLES_TABLE_NAME)


def create_role(role: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a role
    :param role: role to create
    :return: created role
    """
    if not role:
        raise Exception("Permission profile required")

    role_id = role.get("role_id")
    if not role_id or not role_id.strip():
        raise Exception("profile_id is required")

    try:
        if get_role(role_id):
            raise Exception(f"role_id: {role_id} already exists.")
    except exceptions.RoleNotFound:
        pass

    current_time_ms = time_utils.current_time_ms()
    role[ROLES_DB_CREATED_ON_KEY] = current_time_ms
    role[ROLES_DB_UPDATED_ON_KEY] = current_time_ms

    created_role = table_utils.create_item(table_name=ROLES_TABLE_NAME, item=role)

    logger.info(f"Created role {role_id} successfully")
    return created_role


def get_role(role_id: str) -> Optional[Dict[str, Any]]:
    """
    Get role from DDB
    :param role_id: role_id of the role
    :return role
    """
    if not role_id:
        raise Exception("Role ID required")

    logger.info(f"Getting role for {ROLES_DB_HASH_KEY}: {role_id}")

    role = table_utils.get_item(
        ROLES_TABLE_NAME,
        key={
            ROLES_DB_HASH_KEY: role_id,
        },
    )

    if not role:
        raise exceptions.RoleNotFound(
            f"Role not found for {ROLES_DB_HASH_KEY}: {role_id}"
        )

    return role


def get_roles_batch(role_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Get multiple roles from DDB
    :param role_ids: list of role IDs
    :return: dict mapping role_id to role data
    """
    if not role_ids:
        return {}

    roles_dict = {}
    for role_id in role_ids:
        try:
            role = get_role(role_id)
            if role:
                roles_dict[role_id] = role
        except exceptions.RoleNotFound:
            logger.debug(f"Role {role_id} not found, skipping")
            continue

    return roles_dict


def filter_roles_with_manage_sessions_permission(role_ids: set) -> set:
    """
    Filter roles that have permission to manage other user sessions
    :param role_ids: set of role IDs to check
    :return: set of role IDs with manage sessions permission
    """
    manage_sessions_role_ids = set()
    for role_id in role_ids:
        role = get_role(role_id)
        if role.get("vdis", {}).get("create_terminate_others_sessions", False):
            manage_sessions_role_ids.add(role_id)
    return manage_sessions_role_ids
