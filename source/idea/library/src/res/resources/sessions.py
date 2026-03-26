#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict, List, Optional, Tuple

import res.exceptions as exceptions
from boto3.dynamodb.conditions import And, Attr, Or
from res.resources import accounts, projects
from res.utils import logging_utils, table_utils, time_utils
from res.utils.table_utils import FilterOperator

SESSIONS_TABLE_NAME = "vdc.controller.user-sessions"
SESSIONS_COUNTER_TABLE_NAME = "vdc.controller.user-sessions-counter"
SESSION_DB_HASH_KEY = "owner"
SESSION_DB_RANGE_KEY = SESSIONS_COUNTER_DB_HASH_KEY = "idea_session_id"
SESSIONS_COUNTER_DB_RANGE_KEY = "counter_type"
SESSION_DB_UPDATED_ON_KEY = "updated_on"
SESSION_DB_STATE_KEY = "state"
SESSION_DB_DCV_SESSION_ID_KEY = "dcv_session_id"
SESSION_DB_SCHEDULE_SUFFIX = "_schedule"
SESSION_DB_SERVER_KEY = "server"
SESSION_DB_PROJECT_KEY = "project"
SESSION_DB_PROJECT_ID_KEY = "project_id"
SESSION_DB_BASE_OS_KEY = "base_os"
SESSION_DB_NAME_KEY = "name"


logger = logging_utils.get_logger(SESSIONS_TABLE_NAME)


def get_session(owner: str, session_id: str) -> Optional[Dict[str, Any]]:
    """
    Get session from DDB
    :param owner: username of the session owner
    :param session_id: session_id of the VDI session
    :return user session
    """
    if not owner or not session_id:
        raise Exception("Owner and Session ID required")

    logger.info(
        f"Getting session for {SESSION_DB_HASH_KEY}: {owner} with {SESSION_DB_RANGE_KEY}: {session_id}"
    )

    session = table_utils.get_item(
        SESSIONS_TABLE_NAME,
        key={
            SESSION_DB_HASH_KEY: owner,
            SESSION_DB_RANGE_KEY: session_id,
        },
    )

    if not session:
        raise exceptions.UserSessionNotFound(
            f"Session not found: {session_id}",
        )
    return session


def update_session(session: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Update an existing session from DDB
    :param session: the session dict to update
    :return: returns updated user session
    """
    session[SESSION_DB_UPDATED_ON_KEY] = time_utils.current_time_ms()
    logger.info(
        f"Updating session for {SESSION_DB_HASH_KEY}: {session[SESSION_DB_HASH_KEY]}"
    )

    updated_session = table_utils.update_item(
        SESSIONS_TABLE_NAME,
        key={
            SESSION_DB_HASH_KEY: session[SESSION_DB_HASH_KEY],
            SESSION_DB_RANGE_KEY: session[SESSION_DB_RANGE_KEY],
        },
        item=session,
    )

    return updated_session


def delete_session(session: Dict[str, Any]) -> None:
    """
    Delete an existing session from DDB
    :param session: the session dict to delete
    :return: None
    """
    if not session.get(SESSION_DB_HASH_KEY):
        raise Exception(f"{SESSION_DB_HASH_KEY} not provided")

    if not session.get(SESSION_DB_RANGE_KEY):
        raise Exception(f"{SESSION_DB_RANGE_KEY} not provided")

    logger.info(
        f"Deleting session for {SESSION_DB_HASH_KEY}: {session[SESSION_DB_HASH_KEY]} with {SESSION_DB_RANGE_KEY}: {session[SESSION_DB_RANGE_KEY]}"
    )

    table_utils.delete_item(
        SESSIONS_TABLE_NAME,
        key={
            SESSION_DB_HASH_KEY: session[SESSION_DB_HASH_KEY],
            SESSION_DB_RANGE_KEY: session[SESSION_DB_RANGE_KEY],
        },
    )


def list_sessions_paginated(
    filter_expression: Any = None,
    next_token: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    List sessions with optional filtering and pagination
    :param filter_expression: Optional DynamoDB filter expression
    :param next_token: Pagination token
    :return: tuple of (list of sessions, next_token)
    """
    logger.info(f"Listing sessions with filter: {filter_expression}")
    return table_utils.list_items_paginated(
        SESSIONS_TABLE_NAME, filter_expression=filter_expression, next_token=next_token
    )


def list_sessions_for_user(
    username: str,
    project_ids: Optional[List[str]] = None,
    filter_expression: Any = None,
    next_token: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    List sessions owned by user or user has permission to manage
    :param username: Name of the user
    :param project_ids: Optional list of project IDs where user has permission to manage sessions
    :param filter_expression: Optional DynamoDB filter expression
    :param next_token: Pagination token
    :return: tuple of (list of sessions, next_token)
    """
    user_filter = Attr(SESSION_DB_HASH_KEY).eq(username)

    if project_ids:
        project_filter = Attr(
            f"{SESSION_DB_PROJECT_KEY}.{SESSION_DB_PROJECT_ID_KEY}"
        ).is_in(project_ids)
        access_filter = Or(user_filter, project_filter)
    else:
        access_filter = user_filter

    combined_filter = (
        And(filter_expression, access_filter) if filter_expression else access_filter
    )
    return list_sessions_paginated(
        filter_expression=combined_filter, next_token=next_token
    )


def list_sessions(
    user: str,
    state: Optional[str] = None,
    base_os: Optional[str] = None,
    session_name: Optional[str] = None,
    stack_id: Optional[str] = None,
    date_range_key: Optional[str] = None,
    after: Optional[str] = None,
    before: Optional[str] = None,
    next_token: Optional[str] = None,
    owner: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    List sessions with filtering based on user permissions
    :param user: Username
    :param state: Filter by state
    :param base_os: Filter by base OS
    :param session_name: Filter by session name
    :param stack_id: Filter by stack ID
    :param date_range_key: Date range key for filtering
    :param after: Start date for range filter
    :param before: End date for range filter
    :param next_token: Pagination token
    :param owner: Filter by owner
    :return: tuple of (list of sessions, next_token)
    """
    filter_expression = table_utils.construct_filter_expression(
        {
            SESSION_DB_HASH_KEY: owner,
            SESSION_DB_STATE_KEY: state,
            SESSION_DB_BASE_OS_KEY: (
                (FilterOperator.NE, "windows") if base_os == "linux" else base_os
            ),
            SESSION_DB_NAME_KEY: (FilterOperator.CONTAINS, session_name),
            "software_stack.stack_id": stack_id,
        },
        date_range_key,
        after,
        before,
    )

    if not accounts.is_active_admin(user):
        projects_to_manage_sessions = projects.list_user_manage_sessions_projects(user)
        return list_sessions_for_user(
            user,
            project_ids=projects_to_manage_sessions,
            filter_expression=filter_expression,
            next_token=next_token,
        )
    else:
        return list_sessions_paginated(
            filter_expression=filter_expression,
            next_token=next_token,
        )


def get_session_if_owner(
    username: str, res_session_id: str
) -> Optional[Dict[str, Any]]:
    try:
        session = get_session(username, res_session_id)
        return session
    except exceptions.UserSessionNotFound:
        return None
    except Exception as e:
        raise Exception(f"Failed to get user {username} session {res_session_id}")
