#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Dict, List, Optional

import res.exceptions as exceptions
from res.utils import table_utils

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

SESSION_PERMISSION_TABLE_NAME = "vdc.controller.session-permissions"
SESSION_PERMISSION_DB_HASH_KEY = "idea_session_id"
SESSION_PERMISSION_DB_RANGE_KEY = "actor_name"


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


def delete_session_permission(session_permission: Dict[str, Any]) -> None:
    """
    Delete session from DDB
    :param session_permission: session permission details
    :return None
    """
    if not session_permission.get(SESSION_PERMISSION_DB_HASH_KEY):
        raise Exception(f"{SESSION_PERMISSION_DB_HASH_KEY} not provided")

    if not session_permission.get(SESSION_PERMISSION_DB_RANGE_KEY):
        raise Exception(f"{SESSION_PERMISSION_DB_RANGE_KEY} not provided")

    table_utils.delete_item(
        SESSION_PERMISSION_TABLE_NAME,
        key={
            SESSION_PERMISSION_DB_HASH_KEY: session_permission[
                SESSION_PERMISSION_DB_HASH_KEY
            ],
            SESSION_PERMISSION_DB_RANGE_KEY: session_permission[
                SESSION_PERMISSION_DB_RANGE_KEY
            ],
        },
    )


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
