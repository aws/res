#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict, List, Optional, Tuple

import res.exceptions as exceptions
from res.clients.events import events_client
from res.resources import sessions
from res.utils import logging_utils, table_utils, time_utils
from res.utils.string_utils import validate_actor_name
from res.utils.table_utils import FilterOperator

SESSION_PERMISSION_TABLE_NAME = "vdc.controller.session-permissions"
SESSION_PERMISSION_DB_RANGE_KEY = "actor_name"
SESSION_PERMISSION_DB_CREATED_ON_KEY = "created_on"
SESSION_PERMISSION_DB_UPDATED_ON_KEY = "updated_on"
SESSION_PERMISSION_DB_HASH_KEY = "idea_session_id"
SESSION_PERMISSION_DB_SESSION_OWNER_KEY = "idea_session_owner"
SESSION_PERMISSION_DB_BASE_OS_KEY = "idea_session_base_os"
SESSION_PERMISSION_DB_STATE_KEY = "idea_session_state"
SESSION_PERMISSION_DB_NAME_KEY = "idea_session_name"

ACCESS_DENIED_MSG = "Session not found or access denied"

logger = logging_utils.get_logger(SESSION_PERMISSION_TABLE_NAME)


def get_session_permission(session_id: str, user: str) -> Optional[Dict[str, Any]]:
    """
    Get sessio permission from DDB
    :param owner: username of the session owner
    :param session_id: session_id of the VDI session
    :return user session
    """
    if not user or not session_id:
        raise Exception("Owner and Session ID required")

    logger.info(
        f"Getting session for {SESSION_PERMISSION_DB_HASH_KEY}: {session_id} for {SESSION_PERMISSION_DB_RANGE_KEY}: {user}"
    )

    session_permission = table_utils.get_item(
        SESSION_PERMISSION_TABLE_NAME,
        key={
            SESSION_PERMISSION_DB_HASH_KEY: session_id,
            SESSION_PERMISSION_DB_RANGE_KEY: user,
        },
    )

    if not session_permission:
        raise exceptions.SessionPermissionsNotFound(
            f"Session permission not found for {SESSION_PERMISSION_DB_HASH_KEY}: {session_id} for {SESSION_PERMISSION_DB_RANGE_KEY} : {user}"
        )

    return session_permission


def get_session_permission_by_id(session_id: str) -> List[Dict[str, Any]]:
    """
    Query session permission by session id
    :param session_id: session_id of the VDI session
    :return list of session permissions
    """
    session_permissions = table_utils.query(
        SESSION_PERMISSION_TABLE_NAME,
        attributes={SESSION_PERMISSION_DB_HASH_KEY: session_id},
    )

    if not session_permissions:
        raise exceptions.SessionPermissionsNotFound(
            f"Session permission not found for {SESSION_PERMISSION_DB_HASH_KEY}: {session_id}"
        )
    return session_permissions


def delete_session_permission_by_id(session_id: str) -> None:
    """
    Delete session permission for the session id
    :param session_id: session_id of the VDI session
    :return None
    """
    try:
        session_permissions = get_session_permission_by_id(session_id=session_id)
    except exceptions.SessionPermissionsNotFound as e:
        session_permissions = []

    for session_permission in session_permissions:
        delete_session_permission(session_permission, False)


def list_session_permissions_paginated(
    filter_expression: Any = None,
    next_token: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    List session permissions with optional filtering and pagination
    :param next_token: Pagination token
    :return: tuple of (list of session permissions, next_token)
    """
    logger.info(f"Listing session permissions with filter: {filter_expression}")
    return table_utils.list_items_paginated(
        SESSION_PERMISSION_TABLE_NAME,
        filter_expression=filter_expression,
        next_token=next_token,
    )


def list_session_permissions(
    username: Optional[str] = None,
    state: Optional[str] = None,
    base_os: Optional[str] = None,
    session_name: Optional[str] = None,
    session_id: Optional[str] = None,
    date_range_key: Optional[str] = None,
    after: Optional[str] = None,
    before: Optional[str] = None,
    next_token: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    List session permissions with filtering
    :param username: Username to filter by
    :param state: Filter by state
    :param base_os: Filter by base OS
    :param session_id: Filter by session id
    :param session_name: Filter by session name
    :param date_range_key: Date range key for filtering
    :param after: Start date for range filter
    :param before: End date for range filter
    :param next_token: Pagination token
    :return: tuple of (list of session permissions, next_token)
    """
    filter_expression = table_utils.construct_filter_expression(
        {
            SESSION_PERMISSION_DB_RANGE_KEY: username,
            SESSION_PERMISSION_DB_STATE_KEY: state,
            SESSION_PERMISSION_DB_BASE_OS_KEY: base_os,
            SESSION_PERMISSION_DB_NAME_KEY: (FilterOperator.CONTAINS, session_name),
            SESSION_PERMISSION_DB_HASH_KEY: session_id,
        },
        date_range_key,
        after,
        before,
    )

    return list_session_permissions_paginated(
        filter_expression=filter_expression,
        next_token=next_token,
    )


def create_session_permission(session_permission: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a session permission
    :param session_permission: session permission to create
    :return created session permission
    """
    if not session_permission:
        raise Exception("Session Permission required")

    session_id = session_permission[SESSION_PERMISSION_DB_HASH_KEY]
    actor_name = session_permission[SESSION_PERMISSION_DB_RANGE_KEY]
    validate_actor_name(actor_name)
    logger.info(
        f"Creating session permission with session_id {session_id} and actor_name {actor_name}."
    )

    current_time_ms = time_utils.current_time_ms()
    session_permission[SESSION_PERMISSION_DB_CREATED_ON_KEY] = current_time_ms
    session_permission[SESSION_PERMISSION_DB_UPDATED_ON_KEY] = current_time_ms

    created_session_permission = table_utils.create_item(
        SESSION_PERMISSION_TABLE_NAME,
        item=session_permission,
        attribute_names_to_check=[
            SESSION_PERMISSION_DB_RANGE_KEY,
            SESSION_PERMISSION_DB_HASH_KEY,
        ],
    )

    logger.info(
        f"Created session permission with session_id {session_id} and actor_name {actor_name}."
    )

    events_client.publish_create_event(
        created_session_permission[SESSION_PERMISSION_DB_HASH_KEY],
        created_session_permission[SESSION_PERMISSION_DB_RANGE_KEY],
        new_entry=created_session_permission,
        table_name=SESSION_PERMISSION_TABLE_NAME,
    )

    return created_session_permission


def update_session_permission(session_permission: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a session permission
    :param session_permission: session permission to update
    :return updated session permission
    """
    if not session_permission:
        raise Exception("Session Permission required")

    session_id = session_permission[SESSION_PERMISSION_DB_HASH_KEY]
    actor_name = session_permission[SESSION_PERMISSION_DB_RANGE_KEY]
    validate_actor_name(actor_name)
    logger.info(
        f"Updating session permission with session_id {session_id} and actor_name {actor_name}."
    )

    session_permission[SESSION_PERMISSION_DB_UPDATED_ON_KEY] = (
        time_utils.current_time_ms()
    )

    updated_session_permission = table_utils.update_item(
        SESSION_PERMISSION_TABLE_NAME,
        key={
            SESSION_PERMISSION_DB_HASH_KEY: session_id,
            SESSION_PERMISSION_DB_RANGE_KEY: actor_name,
        },
        item=session_permission,
    )
    events_client.publish_update_event(
        updated_session_permission[SESSION_PERMISSION_DB_HASH_KEY],
        updated_session_permission[SESSION_PERMISSION_DB_RANGE_KEY],
        old_entry=session_permission,
        new_entry=updated_session_permission,
        table_name=SESSION_PERMISSION_TABLE_NAME,
    )

    return updated_session_permission


def delete_session_permission(
    session_permission: Dict[str, Any], publish_event: bool = True
) -> None:
    """
    Delete a session permission
    :param session_permission: session permission to delete
    :param publish_event: whether to publish delete event, default to True
    """
    if not session_permission:
        raise Exception("Session Permission required")

    session_id = session_permission[SESSION_PERMISSION_DB_HASH_KEY]
    actor_name = session_permission[SESSION_PERMISSION_DB_RANGE_KEY]
    logger.info(
        f"Deleting session permission with session_id {session_id} and actor_name {actor_name}."
    )

    table_utils.delete_item(
        SESSION_PERMISSION_TABLE_NAME,
        key={
            SESSION_PERMISSION_DB_HASH_KEY: session_id,
            SESSION_PERMISSION_DB_RANGE_KEY: actor_name,
        },
    )

    if publish_event:
        events_client.publish_delete_event(
            session_permission[SESSION_PERMISSION_DB_HASH_KEY],
            session_permission[SESSION_PERMISSION_DB_RANGE_KEY],
            deleted_entry=session_permission,
            table_name=SESSION_PERMISSION_TABLE_NAME,
        )


def update_permissions_for_sessions(
    permission_to_create: List[Dict[str, Any]],
    permission_to_update: List[Dict[str, Any]],
    permission_to_delete: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    permissions = []
    sessions_info = set()
    for permission in permission_to_create:
        created_permission = create_session_permission(permission)
        permissions.append(created_permission)
        sessions_info.add(
            (
                permission[SESSION_PERMISSION_DB_HASH_KEY],
                permission[SESSION_PERMISSION_DB_SESSION_OWNER_KEY],
            )
        )
    for permission in permission_to_update:
        updated_permission = update_session_permission(permission)
        permissions.append(updated_permission)
        sessions_info.add(
            (
                permission[SESSION_PERMISSION_DB_HASH_KEY],
                permission[SESSION_PERMISSION_DB_SESSION_OWNER_KEY],
            )
        )
    for permission in permission_to_delete:
        delete_session_permission(permission)
        sessions_info.add(
            (
                permission[SESSION_PERMISSION_DB_HASH_KEY],
                permission[SESSION_PERMISSION_DB_SESSION_OWNER_KEY],
            )
        )

    for session_info in sessions_info:
        events_client.publish_enforce_session_permissions_event(
            idea_session_id=session_info[0], idea_session_owner=session_info[1]
        )

    return permissions


def validate_session_access(session_id: str, username: str) -> Dict[str, Any]:
    """Validate that a session exists and the user has access.

    Returns the session record on success.
    Raises SessionAccessDenied if the session doesn't exist or the user lacks access.
    """
    session_map = sessions.get_sessions_by_ids([session_id])
    session = session_map.get(session_id)
    if not session:
        raise exceptions.SessionAccessDenied(ACCESS_DENIED_MSG)

    owner = session.get("owner")
    if username != owner:
        try:
            get_session_permission(session_id, username)
        except exceptions.SessionPermissionsNotFound:
            raise exceptions.SessionAccessDenied(ACCESS_DENIED_MSG) from None

    return session
