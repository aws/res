#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import secrets
import time
from typing import Any, Dict, Optional

from res.constants import (
    DCV_CONNECTION_TOKEN_DB_HASH_KEY,
    DCV_CONNECTION_TOKEN_DB_SESSION_ID_KEY,
    DCV_CONNECTION_TOKEN_DB_TTL_KEY,
    DCV_CONNECTION_TOKEN_DB_USERNAME_KEY,
    DCV_CONNECTION_TOKEN_TABLE_NAME,
    DCV_CONNECTION_TOKEN_VALIDITY_KEY,
)
from res.resources import cluster_settings
from res.utils import logging_utils, table_utils

logger = logging_utils.get_logger("dcv")

TOKEN_LENGTH = 32
DEFAULT_CONNECTION_TOKEN_VALIDITY_MINUTES = 1440  # 1 day


def _get_token_expiry_seconds() -> int:
    validity_minutes = cluster_settings.get_setting(DCV_CONNECTION_TOKEN_VALIDITY_KEY)
    if validity_minutes:
        return int(validity_minutes) * 60
    return DEFAULT_CONNECTION_TOKEN_VALIDITY_MINUTES * 60


def generate_connection_token(username: str, session_id: str) -> str:
    """Generate a random bearer token for a DCV session and store it in DynamoDB."""
    auth_token = secrets.token_urlsafe(TOKEN_LENGTH)
    expiration_time = int(time.time()) + _get_token_expiry_seconds()

    table_utils.create_item(
        DCV_CONNECTION_TOKEN_TABLE_NAME,
        item={
            DCV_CONNECTION_TOKEN_DB_HASH_KEY: auth_token,
            DCV_CONNECTION_TOKEN_DB_SESSION_ID_KEY: session_id,
            DCV_CONNECTION_TOKEN_DB_USERNAME_KEY: username,
            DCV_CONNECTION_TOKEN_DB_TTL_KEY: expiration_time,
        },
    )

    return auth_token


def lookup_connection_token(
    auth_token: str, session_id: str
) -> Optional[Dict[str, Any]]:
    """Look up a connection token in DynamoDB.

    Returns the token record if found, valid, and matches the session_id.
    Returns None otherwise.
    """
    item = table_utils.get_item(
        DCV_CONNECTION_TOKEN_TABLE_NAME,
        key={DCV_CONNECTION_TOKEN_DB_HASH_KEY: auth_token},
    )

    if not item:
        return None

    if item.get(DCV_CONNECTION_TOKEN_DB_SESSION_ID_KEY) != session_id:
        return None

    expiration_time = int(item.get(DCV_CONNECTION_TOKEN_DB_TTL_KEY, 0))
    if expiration_time < int(time.time()):
        return None

    return item
