#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
Cognito Pre-Signup trigger handler.

Validates that the username matches the RES username regex before allowing
registration. This prevents attackers from bypassing RES's application-level
validation by calling the Cognito SignUp API directly with usernames like
"clusteradmin@!" that would be truncated to "clusteradmin" by the authorizer.
"""

import logging
from typing import Any, Dict

from res.utils.auth_utils import validate_native_cognito_username  # type: ignore

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handle_event(event: Dict[str, Any], _: Any) -> Dict[str, Any]:
    """
    Cognito Pre Sign-up Lambda trigger.

    Rejects sign-up attempts where the username does not match the allowed
    pattern. This enforces the same validation that the RES UI applies,
    preventing bypass via direct Cognito API calls.
    """
    username = event.get("userName", "")
    trigger_source = event.get("triggerSource", "")

    # Only validate self-signup requests. Admin-created users and external
    # provider (SSO) users are managed through different flows.
    if trigger_source == "PreSignUp_SignUp":
        try:
            validate_native_cognito_username(username)
        except Exception:
            logger.warning(
                "Pre-signup validation rejected username: '%s' (trigger_source=%s)",
                username,
                trigger_source,
            )
            # Do not echo the username back in the exception message — Cognito
            # surfaces it to the caller, which could leak info about filtering.
            raise Exception(
                "Username must start with a lowercase letter and contain only "
                "lowercase letters, numbers, hyphens, and underscores (max 32 chars)."
            )

    return event
