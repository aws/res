#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Optional, Tuple

from res.constants import DCV_CONNECTION_TOKEN_DB_USERNAME_KEY
from res.exceptions import SessionAccessDenied
from res.resources import session_permissions
from res.resources.dcv import session_token
from res.utils import logging_utils

logger = logging_utils.get_logger(__name__)

_AUTH_FAILED = "Authentication failed"


def validate_connection_token(
    connection_token: str, session_id: str
) -> Tuple[Optional[str], Optional[str]]:
    """Validate a DCV connection token and session access.

    Returns (username, None) on success, or (None, error_message) on failure.
    """
    token_record = session_token.lookup_connection_token(connection_token, session_id)
    if not token_record:
        logger.warning("Invalid or expired connection token for session %s", session_id)
        return None, _AUTH_FAILED

    username = token_record.get(DCV_CONNECTION_TOKEN_DB_USERNAME_KEY, "")
    if not username:
        return None, _AUTH_FAILED

    try:
        session_permissions.validate_session_access(session_id, username)
    except SessionAccessDenied:
        logger.warning(
            "Session access denied for user %s on session %s", username, session_id
        )
        return None, _AUTH_FAILED

    return username, None
