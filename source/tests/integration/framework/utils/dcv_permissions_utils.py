#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

import logging
import time
from typing import Dict, Optional, Set, Tuple

from tests.integration.framework.utils.vdi_command_utils import (
    OK_MARKER,
    command_succeeded,
    run_command,
)

logger = logging.getLogger(__name__)

DCV_PERMISSION_POLL_TIMEOUT = 120  # seconds
DCV_PERMISSION_POLL_INTERVAL = 10  # seconds

# DCV permissions file path on Linux VDIs (per-session directory)
_DCV_PERMISSIONS_PATH_TEMPLATE = "/etc/dcv/{dcv_session_id}/idea.perm"


def get_dcv_permissions_for_user(
    instance_id: str, dcv_session_id: str, username: str
) -> Tuple[Set[str], Set[str]]:
    """
    Read the DCV permissions file on the VDI and return (allowed, denied) features
    for the specified user.

    The permissions file at /etc/dcv/<session_id>/idea.perm has format:
        [aliases]
        <profile_id>-allow=feature1, feature2, ...
        <profile_id>-deny=feature3, feature4, ...
        [permissions]
        <username> allow <profile_id>-allow
        <username> deny <profile_id>-deny

    Returns two sets: (allowed_features, denied_features).
    Raises AssertionError if the file can't be read or user not found.
    """
    perm_path = _DCV_PERMISSIONS_PATH_TEMPLATE.format(dcv_session_id=dcv_session_id)
    output = run_command(instance_id, f"cat {perm_path}")
    assert command_succeeded(output), f"Failed to read {perm_path}: {output}"

    content = output.replace(OK_MARKER, "").strip()

    # Parse aliases
    aliases: Dict[str, Set[str]] = {}
    in_aliases = False
    in_permissions = False
    user_allow_alias: Optional[str] = None
    user_deny_alias: Optional[str] = None

    for line in content.splitlines():
        line = line.strip()
        if line == "[aliases]":
            in_aliases = True
            in_permissions = False
            continue
        elif line == "[permissions]":
            in_aliases = False
            in_permissions = True
            continue
        elif line.startswith("["):
            in_aliases = False
            in_permissions = False
            continue

        if in_aliases and "=" in line:
            alias_name, features_str = line.split("=", 1)
            features = {f.strip() for f in features_str.split(",") if f.strip()}
            aliases[alias_name.strip()] = features

        if in_permissions and line:
            parts = line.split()
            if len(parts) >= 3 and parts[0] == username:
                action = parts[1]  # "allow" or "deny"
                alias_ref = parts[2]
                if action == "allow":
                    user_allow_alias = alias_ref
                elif action == "deny":
                    user_deny_alias = alias_ref

    allowed = aliases.get(user_allow_alias, set()) if user_allow_alias else set()
    denied = aliases.get(user_deny_alias, set()) if user_deny_alias else set()

    return allowed, denied


def assert_dcv_permissions(
    instance_id: str,
    dcv_session_id: str,
    username: str,
    expected_allowed: Optional[Set[str]] = None,
    expected_denied: Optional[Set[str]] = None,
    timeout: int = DCV_PERMISSION_POLL_TIMEOUT,
) -> None:
    """
    Poll the DCV permissions file on the VDI until the user's permissions
    match expectations.

    Args:
        instance_id: EC2 instance ID of the VDI
        dcv_session_id: DCV session ID (used to locate the permissions file)
        username: The user whose permissions to check
        expected_allowed: Features that MUST be in the user's allow list
        expected_denied: Features that MUST be in the user's deny list
        timeout: Max time to wait for permissions to converge
    """
    expected_allowed = expected_allowed or set()
    expected_denied = expected_denied or set()

    start = time.time()
    last_allowed: Set[str] = set()
    last_denied: Set[str] = set()

    while time.time() - start < timeout:
        try:
            allowed, denied = get_dcv_permissions_for_user(
                instance_id, dcv_session_id, username
            )
            last_allowed = allowed
            last_denied = denied

            allowed_ok = expected_allowed.issubset(allowed)
            denied_ok = expected_denied.issubset(denied)

            if allowed_ok and denied_ok:
                logger.info(
                    f"DCV permissions match for {username}: "
                    f"allowed={allowed}, denied={denied}"
                )
                return
        except (AssertionError, ValueError):
            pass  # File not yet written or parse error

        time.sleep(DCV_PERMISSION_POLL_INTERVAL)

    # Build detailed failure message
    missing_allowed = expected_allowed - last_allowed
    missing_denied = expected_denied - last_denied
    assert False, (
        f"DCV permissions did not converge within {timeout}s for {username}. "
        f"Allowed: {last_allowed}. Denied: {last_denied}. "
        f"Missing from allowed: {missing_allowed}. "
        f"Missing from denied: {missing_denied}."
    )
