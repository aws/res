#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Dict, Optional

import res.exceptions as exceptions
from res.utils import table_utils, time_utils

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

SESSIONS_TABLE_NAME = "vdc.controller.user-sessions"
SESSION_DB_HASH_KEY = "owner"
SESSION_DB_RANGE_KEY = "idea_session_id"
SESSION_DB_UPDATED_ON_KEY = "updated_on"
SESSION_DB_STATE_KEY = "state"
SESSION_DB_DCV_SESSION_ID_KEY = "dcv_session_id"
SESSION_DB_SCHEDULE_SUFFIX = "_schedule"


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
