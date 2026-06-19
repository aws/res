#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import copy
import os
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import boto3
import res.exceptions as exceptions
from boto3.dynamodb.conditions import And, Attr, Or
from res import constants
from res.clients.events import events_client
from res.constants import ENVIRONMENT_NAME_KEY
from res.resources import accounts, cluster_settings, projects, schedules
from res.utils import ec2_utils, logging_utils, table_utils, time_utils
from res.utils.table_utils import FilterOperator

SESSIONS_TABLE_NAME = "vdc.controller.user-sessions"
SESSIONS_COUNTER_TABLE_NAME = "vdc.controller.user-sessions-counter"
SESSION_DB_HASH_KEY = "owner"
SESSION_DB_RANGE_KEY = SESSIONS_COUNTER_DB_HASH_KEY = "idea_session_id"
SESSIONS_COUNTER_DB_RANGE_KEY = "counter_type"
SESSION_DB_UPDATED_ON_KEY = "updated_on"
SESSION_DB_CREATED_ON_KEY = "created_on"
SESSION_DB_STATE_KEY = "state"
SESSION_DB_DCV_SESSION_ID_KEY = "dcv_session_id"
SESSION_DB_SCHEDULE_SUFFIX = "_schedule"
SESSION_DB_SERVER_KEY = "server"
SESSION_DB_SERVER_INSTANCE_ID_KEY = "server_instance_id"
SESSION_DB_SERVER_NESTED_INSTANCE_ID_KEY = "instance_id"
GSI_SERVER_INSTANCE_ID = "server-instance-id-index"
SESSION_DB_PROJECT_KEY = "project"
SESSION_DB_PROJECT_ID_KEY = "project_id"
SESSION_DB_BASE_OS_KEY = "base_os"
SESSION_DB_DESCRIPTION_KEY = "description"
SESSION_DB_HIBERNATION_KEY = "hibernation_enabled"
SESSION_DB_STACK_KEY = "software_stack"
SESSION_DB_NAME_KEY = "name"
SESSION_DB_INSTANCE_TYPE_KEY = "instance_type"
SESSION_DB_LOCKED_KEY = "locked"
SESSION_DB_IS_IDLE_KEY = "is_idle"
SESSION_DB_PRIVATE_DNS_NAME_KEY = "private_dns_name"
CUSTOM_DNS_NAME_KEY = "vdc.dcv_connection_gateway.certificate.custom_dns_name"
EXTERNAL_NLB_DNS_NAME_KEY = "vdc.external_nlb.load_balancer_dns_name"

logger = logging_utils.get_logger(SESSIONS_TABLE_NAME)


class ScriptOSType(str, Enum):
    WINDOWS = "windows"
    LINUX = "linux"


class ScriptEventType(str, Enum):
    ON_VDI_START = "on_vdi_start"
    ON_VDI_CONFIGURED = "on_vdi_configured"
    RERUN_ON_REBOOT = "rerun_on_reboot"


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


def get_session_by_instance_id(instance_id: str) -> Optional[Dict[str, Any]]:
    """
    Get session by EC2 instance ID using the GSI.
    :param instance_id: EC2 instance ID
    :return: session dict or raises UserSessionNotFound
    """
    if not instance_id:
        raise Exception("instance_id is required")

    results = table_utils.query(
        SESSIONS_TABLE_NAME,
        attributes={SESSION_DB_SERVER_INSTANCE_ID_KEY: instance_id},
        index_name=GSI_SERVER_INSTANCE_ID,
    )

    if not results:
        raise exceptions.UserSessionNotFound(
            f"Session not found for instance_id: {instance_id}",
        )
    return results[0]


def _update_session_record(
    session: Dict[str, Any],
    publish_event: bool = False,
    old_session: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Update an existing session from DDB
    :param session: the session dict to update
    :return: returns updated user session
    """
    session[SESSION_DB_UPDATED_ON_KEY] = time_utils.current_time_ms()

    # Keep server_instance_id in sync with server.instance_id for GSI
    instance_id = session.get(SESSION_DB_SERVER_KEY, {}).get(
        SESSION_DB_SERVER_NESTED_INSTANCE_ID_KEY
    )
    if instance_id:
        session[SESSION_DB_SERVER_INSTANCE_ID_KEY] = instance_id

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

    if publish_event and old_session:
        logger.info("publishing event")
        events_client.publish_update_event(
            hash_key=session[SESSION_DB_HASH_KEY],
            range_key=session[SESSION_DB_RANGE_KEY],
            old_entry=old_session,
            new_entry=updated_session,
            table_name=SESSIONS_TABLE_NAME,
        )

    return updated_session


def update_session_state(
    owner: str, session_id: str, state: str, publish_event: bool = False
) -> Dict[str, Any]:
    """
    Update only the state of a session.
    :param owner: session owner
    :param session_id: session ID
    :param state: new state value
    :param publish_event: if True, fetch the existing session and publish a DDB
        update event so downstream consumers (e.g. session-permissions table) stay in sync.
    :return: updated session dict from DDB
    """
    if publish_event:
        old_session = get_session(owner=owner, session_id=session_id)
        new_session = {**old_session, SESSION_DB_STATE_KEY: state}
        return _update_session_record(
            new_session, publish_event=True, old_session=old_session
        )

    return table_utils.update_item(
        SESSIONS_TABLE_NAME,
        key={
            SESSION_DB_HASH_KEY: owner,
            SESSION_DB_RANGE_KEY: session_id,
        },
        item={
            SESSION_DB_STATE_KEY: state,
            SESSION_DB_UPDATED_ON_KEY: time_utils.current_time_ms(),
        },
    )


def update_session(
    new_session: Dict[str, Any], old_session: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Update an existing session. If old_session is provided, compares and updates
    name, description, instance_type, and schedule. If old_session is None,
    writes the session record directly.
    :param new_session: the session dict to update
    :param old_session: the existing session dict from DDB (optional)
    :return: returns updated user session
    """

    if old_session is None:
        return _update_session_record(new_session)

    session_to_update = copy.deepcopy(old_session)

    # Update session metadata
    update_tag = (
        session_to_update[SESSION_DB_NAME_KEY] != new_session[SESSION_DB_NAME_KEY]
    )
    session_to_update[SESSION_DB_NAME_KEY] = new_session[SESSION_DB_NAME_KEY]
    session_to_update[SESSION_DB_DESCRIPTION_KEY] = new_session[
        SESSION_DB_DESCRIPTION_KEY
    ]
    if new_session.get(SESSION_DB_STATE_KEY) is not None:
        session_to_update[SESSION_DB_STATE_KEY] = new_session[SESSION_DB_STATE_KEY]

    # Update instance type if changed
    instance_id = old_session.get(SESSION_DB_SERVER_KEY, {}).get(
        SESSION_DB_SERVER_NESTED_INSTANCE_ID_KEY
    )
    new_instance_type = new_session.get(SESSION_DB_SERVER_KEY, {}).get("instance_type")

    if instance_id and new_instance_type:
        old_instance_type = old_session.get(SESSION_DB_SERVER_KEY, {}).get(
            "instance_type"
        )

        if old_instance_type and old_instance_type != new_instance_type:
            ec2_utils.change_instance_type(
                instance_id=instance_id,
                instance_type_name=new_instance_type,
            )
            session_to_update[SESSION_DB_SERVER_KEY][
                "instance_type"
            ] = new_instance_type

    # Update schedule
    session_to_update = schedules.update_schedule_for_session(
        new_session, session_to_update
    )

    if session_to_update != old_session:
        _ = _update_session_record(session_to_update, True, old_session)

        tag_instance_id = session_to_update.get(SESSION_DB_SERVER_KEY, {}).get(
            SESSION_DB_SERVER_NESTED_INSTANCE_ID_KEY
        )
        if tag_instance_id and update_tag:
            ec2_utils.create_tag(
                tag_instance_id,
                "Name",
                f"{os.environ.get(ENVIRONMENT_NAME_KEY)}-{session_to_update[SESSION_DB_NAME_KEY]}-{session_to_update[SESSION_DB_HASH_KEY]}",
            )

    return session_to_update


def create_session(session: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Create session record in DDB
    :param session: the session dict to create
    :return: returns created session
    """

    current_time = time_utils.current_time_ms()
    session["created_on"] = current_time
    session["updated_on"] = current_time

    # Promote instance_id to top-level for GSI lookup
    instance_id = session.get(SESSION_DB_SERVER_KEY, {}).get(
        SESSION_DB_SERVER_NESTED_INSTANCE_ID_KEY
    )
    if instance_id:
        session[SESSION_DB_SERVER_INSTANCE_ID_KEY] = instance_id

    table_utils.create_item(SESSIONS_TABLE_NAME, item=session)

    events_client.publish_create_event(
        hash_key=session.get(SESSION_DB_HASH_KEY, session.get("owner")),
        range_key=session.get(SESSION_DB_RANGE_KEY, ""),
        new_entry=session,
        table_name=SESSIONS_TABLE_NAME,
    )

    return session


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


def get_current_project_session_count_for_user(
    username: str, project_id: Optional[str]
) -> int:
    count_request = {
        "Select": "COUNT",
        "KeyConditionExpression": "#owner = :username",
        "ExpressionAttributeNames": {"#owner": SESSION_DB_HASH_KEY},
        "ExpressionAttributeValues": {":username": username},
    }

    if project_id:
        count_request["FilterExpression"] = "#project.#project_id = :project_id"
        count_request["ExpressionAttributeNames"]["#project"] = "project"
        count_request["ExpressionAttributeNames"]["#project_id"] = "project_id"
        count_request["ExpressionAttributeValues"][":project_id"] = project_id

    response = table_utils.table(SESSIONS_TABLE_NAME).query(**count_request)
    return response.get("Count", 0)


def get_sessions_by_dcv_session_ids(
    session_ids: List[str],
) -> Dict[str, Dict[str, Any]]:
    """Look up sessions by DCV session_ids via full table scan.

    Returns a dict mapping DCV session_id -> session record.
    """
    if not session_ids:
        return {}

    items = table_utils.list_items(
        SESSIONS_TABLE_NAME,
        scan_filter={
            SESSION_DB_DCV_SESSION_ID_KEY: {
                "AttributeValueList": session_ids,
                "ComparisonOperator": "IN",
            }
        },
    )
    return {item[SESSION_DB_DCV_SESSION_ID_KEY]: item for item in items}


def get_sessions_by_ids(
    session_ids: List[str],
) -> Dict[str, Dict[str, Any]]:
    """Look up sessions by idea_session_id via full table scan.

    Returns a dict mapping idea_session_id -> session record.
    """
    if not session_ids:
        return {}

    items = table_utils.list_items(
        SESSIONS_TABLE_NAME,
        scan_filter={
            SESSION_DB_RANGE_KEY: {
                "AttributeValueList": session_ids,
                "ComparisonOperator": "IN",
            }
        },
    )
    return {item[SESSION_DB_RANGE_KEY]: item for item in items}


def group_sessions_by_os(
    session_map: Dict[str, Optional[Dict[str, Any]]],
) -> Tuple[Dict[str, List[Dict[str, str]]], List[Dict[str, Any]]]:
    """Group already-fetched sessions by OS type (windows or linux).

    The caller is responsible for fetching sessions and passing the resulting map.
    Missing entries are represented by ``None`` values and surfaced in ``unsuccessful_list``.

    Args:
        session_map: Mapping of RES session_id -> session record (or None
            when the session was not found).

    Returns (os_groups, unsuccessful_list) where os_groups maps OS key
    ("linux" or "windows") to a list of {"session_id", "instance_id"}.
    """
    os_groups: Dict[str, List[Dict[str, str]]] = {}
    unsuccessful_list: List[Dict[str, Any]] = []

    for session_id, session in session_map.items():
        if not session:
            error_msg = f"User session not found with session_id: {session_id}"
            logger.error(error_msg)
            unsuccessful_list.append(
                {"session_id": session_id, "failure_reason": error_msg}
            )
            continue
        instance_id = session.get(SESSION_DB_SERVER_KEY, {}).get(
            SESSION_DB_SERVER_NESTED_INSTANCE_ID_KEY
        )
        if not instance_id:
            error_msg = (
                f"No instance_id found for session with session_id: {session_id}"
            )
            logger.error(error_msg)
            unsuccessful_list.append(
                {"session_id": session_id, "failure_reason": error_msg}
            )
            continue
        base_os = session.get(SESSION_DB_BASE_OS_KEY)
        os_key = "windows" if base_os == "windows" else "linux"
        os_groups.setdefault(os_key, []).append(
            {"session_id": session_id, "instance_id": instance_id}
        )

    return os_groups, unsuccessful_list


def get_session_logins() -> List[str]:
    logins = []
    sso_enabled = cluster_settings.get_setting("identity-provider.cognito.sso_enabled")
    enable_native_user_login = cluster_settings.get_setting(
        "identity-provider.cognito.enable_native_user_login"
    )

    if sso_enabled:
        logins.append(constants.SSO_USER_IDP_TYPE)
    if enable_native_user_login:
        logins.append(constants.COGNITO_USER_IDP_TYPE)
    return logins


def get_session_connection(
    session_id: str, owner: str, username: str
) -> Dict[str, Any]:
    """Get connection information for a virtual desktop session.

    Calls the DCV session management API for connection data and constructs
    the endpoint URL from cluster settings.

    :param session_id: IDEA session ID
    :param owner: session owner username
    :param username: the authenticated user requesting the connection
    :return: dict with connection info in API response format (kebab-case keys)
    """
    from res.clients.dcv_session_manager import (  # lazy import to avoid test isolation issues
        dcv_session_manager_client,
    )

    connection_data = dcv_session_manager_client.get_session_connection_data(
        session_id=session_id,
        username=username,
    )

    # Build endpoint URL from cluster settings
    custom_dns = cluster_settings.get_setting(CUSTOM_DNS_NAME_KEY)
    if custom_dns:
        endpoint = f"https://{custom_dns}"
    else:
        nlb_dns = cluster_settings.get_setting(EXTERNAL_NLB_DNS_NAME_KEY)
        if not nlb_dns:
            raise exceptions.SettingNotFound(
                "No connection gateway endpoint configured"
            )
        endpoint = f"https://{nlb_dns}"

    return {
        "idea-session-id": session_id,
        "idea-session-owner": owner,
        "endpoint": endpoint,
        "web-url-path": connection_data["web_url_path"],
        "access-token": connection_data["access_token"],
    }
