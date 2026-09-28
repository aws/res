#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import base64
from typing import Any, Dict, List, Optional, Tuple

import res.exceptions as exceptions
from res.constants import CLUSTER_ADMINISTRATOR_USERNAME_KEY
from res.resources import cluster_settings, sessions
from res.utils import logging_utils, table_utils, time_utils
from res.utils.string_utils import validate_actor_name

SESSION_PERMISSION_TABLE_NAME = "vdc.controller.session-permissions"
SESSION_PERMISSION_DB_RANGE_KEY = "actor_name"
SESSION_PERMISSION_DB_CREATED_ON_KEY = "created_on"
SESSION_PERMISSION_DB_UPDATED_ON_KEY = "updated_on"
SESSION_PERMISSION_DB_HASH_KEY = "idea_session_id"
SESSION_PERMISSION_DB_SESSION_OWNER_KEY = "idea_session_owner"

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
        delete_session_permission(session_permission)


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


def _build_permission_filter(
    username: Optional[str] = None,
    session_id: Optional[str] = None,
    date_range_key: Optional[str] = None,
    after: Optional[str] = None,
    before: Optional[str] = None,
) -> Any:
    return table_utils.construct_filter_expression(
        {
            SESSION_PERMISSION_DB_RANGE_KEY: username,
            SESSION_PERMISSION_DB_HASH_KEY: session_id,
        },
        date_range_key,
        after,
        before,
    )


def list_session_permissions(
    username: Optional[str] = None,
    session_id: Optional[str] = None,
    date_range_key: Optional[str] = None,
    after: Optional[str] = None,
    before: Optional[str] = None,
    next_token: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    List session permissions with filtering on permission-table attributes only.
    :param username: Username to filter by (actor_name)
    :param session_id: Filter by session id
    :param date_range_key: Date range key for filtering
    :param after: Start date for range filter
    :param before: End date for range filter
    :param next_token: Pagination token
    :return: tuple of (list of session permissions, next_token)
    """
    return list_session_permissions_paginated(
        filter_expression=_build_permission_filter(
            username, session_id, date_range_key, after, before
        ),
        next_token=next_token,
    )


def list_all_session_permissions(
    username: Optional[str] = None,
    session_id: Optional[str] = None,
    date_range_key: Optional[str] = None,
    after: Optional[str] = None,
    before: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    List all session permissions by exhausting pagination.
    :param username: Username to filter by (actor_name)
    :param session_id: Filter by session id
    :param date_range_key: Date range key for filtering
    :param after: Start date for range filter
    :param before: End date for range filter
    :return: complete list of matching session permissions
    """
    filter_expression = _build_permission_filter(
        username, session_id, date_range_key, after, before
    )

    all_permissions: List[Dict[str, Any]] = []
    next_token = None
    while True:
        page, next_token = list_session_permissions_paginated(
            filter_expression=filter_expression,
            next_token=next_token,
        )
        all_permissions.extend(page)
        if not next_token:
            break

    return all_permissions


def enrich_and_filter_permissions_with_session_data(
    permissions: List[Dict[str, Any]],
    state: Optional[str] = None,
    base_os: Optional[str] = None,
    session_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Enrich session permissions with attributes from the user-sessions table
    and apply session-attribute filters in a single pass.

    Fetches session data (name, base_os, state, instance_type, session_type,
    hibernation_enabled) from the user-sessions table for each permission,
    then enriches and filters in one loop.

    Permissions whose session cannot be found are excluded from the result.

    :param permissions: Raw permission dicts from the session-permissions table
    :param state: Optional filter by session state
    :param base_os: Optional filter by base OS
    :param session_name: Optional substring filter by session name
    :return: Enriched and filtered permission dicts
    """
    owner_session_pairs = [
        (p["idea_session_owner"], p["idea_session_id"])
        for p in permissions
        if p.get("idea_session_owner") and p.get("idea_session_id")
    ]
    sessions_map = sessions.get_sessions_by_owner_and_ids(owner_session_pairs)

    result = []
    for permission in permissions:
        session = sessions_map.get(permission.get("idea_session_id"))
        if not session:
            continue

        session_state = session.get("state", "")
        session_base_os = session.get("base_os", "")
        session_name_value = session.get("name", "")

        if state and session_state != state:
            continue
        if base_os and session_base_os != base_os:
            continue
        if session_name and session_name not in session_name_value:
            continue

        enriched = {**permission}
        enriched["idea_session_name"] = session_name_value
        enriched["idea_session_base_os"] = session_base_os
        enriched["idea_session_state"] = session_state
        enriched["idea_session_instance_type"] = session.get("server", {}).get(
            "instance_type", ""
        )
        enriched["idea_session_type"] = session.get("session_type", "")
        enriched["idea_session_hibernation_enabled"] = session.get(
            "hibernation_enabled", False
        )
        result.append(enriched)

    return result


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
    return updated_session_permission


def delete_session_permission(
    session_permission: Dict[str, Any],
) -> None:
    """
    Delete a session permission
    :param session_permission: session permission to delete
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

    for idea_session_id, idea_session_owner in sessions_info:
        try:
            enforce_permissions_for_session(
                idea_session_id=idea_session_id,
                idea_session_owner=idea_session_owner,
            )
        except Exception:
            logger.exception(
                f"Failed to enforce permissions for session {idea_session_id}."
            )

    return permissions


def enforce_permissions_for_session(
    idea_session_id: str, idea_session_owner: str
) -> None:
    """Push the current permissions file to the DCV session manager for a READY session."""
    try:
        session = sessions.get_session(idea_session_owner, idea_session_id)
    except exceptions.UserSessionNotFound:
        logger.warning(
            f"No session found for {idea_session_id} owner {idea_session_owner}. "
            f"Skipping permissions enforce."
        )
        return

    state = session.get(sessions.SESSION_DB_STATE_KEY)
    if state != "READY":
        logger.info(
            f"Session {idea_session_id} in state {state}. Skipping permissions enforce."
        )
        return

    from res.clients.dcv_session_manager import dcv_session_manager_client
    from res.resources.dcv import session_permissions as dcv_session_permissions

    admin_username = cluster_settings.get_setting(CLUSTER_ADMINISTRATOR_USERNAME_KEY)
    permissions_content = dcv_session_permissions.generate_permissions_content(
        session_id=idea_session_id,
        admin_username=admin_username,
    )
    permissions_content_base_64 = (
        base64.b64encode(permissions_content.encode("utf-8")).decode("utf-8")
        if permissions_content
        else None
    )

    logger.info(
        f"Updating DCV session permissions for {idea_session_id} owner {idea_session_owner}"
    )
    dcv_session_manager_client.update_session_permissions(
        session_id=idea_session_id,
        owner=idea_session_owner,
        permissions_file=permissions_content_base_64,
    )


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
