#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict, List, Tuple

from botocore.exceptions import ClientError
from res.resources import cluster_settings, permission_profiles
from res.resources import session_permissions as session_permissions_resource
from res.resources import sessions
from res.utils import logging_utils, ssm_utils

logger = logging_utils.get_logger("dcv")

# idea.perm is the established filename on deployed instances — kept for backward compatibility.
PERMISSIONS_FILENAME = "idea.perm"

_ADMIN_PROFILE_SETTING = "vdc.dcv_session.default_profiles.admin"
_PROFILE_METADATA_KEYS = {
    "profile_id",
    "title",
    "description",
    "created_on",
    "updated_on",
}


def _resolve_profile_permissions(profile_id: str) -> Dict[str, List[str]]:
    """Resolve a profile to its allow / deny alias values."""
    profile = permission_profiles.get_permission_profile(profile_id)
    allow: List[str] = []
    deny: List[str] = []
    if profile.get("builtin"):
        allow.append("builtin")
        return {"allow": allow, "deny": deny}

    for key, value in profile.items():
        if key in _PROFILE_METADATA_KEYS or not isinstance(value, bool):
            continue
        dcv_key = key.replace("_", "-")
        if value:
            allow.append(dcv_key)
        elif dcv_key != "builtin":
            deny.append(dcv_key)
    return {"allow": allow, "deny": deny}


def generate_permissions_content(
    session_id: str, admin_username: str, newline: str = "\n"
) -> str:
    """Generate DCV permissions file content for the session owner, admin, and guests.

    Args:
        session_id: RES (idea) session ID.
        admin_username: Admin user (e.g. 'clusteradmin' on Linux, 'Administrator' on Windows).
        newline: Line ending character(s) for the target platform.

    Returns:
        Permissions file content string.
    """
    admin_profile_id = cluster_settings.get_setting(_ADMIN_PROFILE_SETTING)

    # Collect all unique profiles needed (admin + guest profiles)
    profiles_needed = {admin_profile_id}
    guest_permissions: List[Dict[str, Any]] = []
    try:
        guest_permissions = session_permissions_resource.get_session_permission_by_id(
            session_id
        )
    except Exception as e:
        # No guest permissions found — initial creation or no sharing
        logger.info("No guest permissions for session %s: %s", session_id, e)

    for guest_perm in guest_permissions:
        profile_id = guest_perm.get("permission_profile_id")
        if profile_id:
            profiles_needed.add(profile_id)

    # Resolve allow/deny for each profile
    profile_cache = {pid: _resolve_profile_permissions(pid) for pid in profiles_needed}

    # Build permissions file content
    lines = ["[groups]", f"group:ideaadmin=user:{admin_username}", "[aliases]"]
    for profile_id, perms in profile_cache.items():
        if perms["allow"]:
            lines.append(f"{profile_id}-allow={', '.join(perms['allow'])}")
        if perms["deny"]:
            lines.append(f"{profile_id}-deny={', '.join(perms['deny'])}")

    lines.append("[permissions]")

    # Guest permissions
    for guest_perm in guest_permissions:
        actor_name = guest_perm.get("actor_name")
        profile_id = guest_perm.get("permission_profile_id")
        if not actor_name or not profile_id:
            continue
        if profile_cache[profile_id]["allow"]:
            lines.append(f"{actor_name} allow {profile_id}-allow")
        if profile_cache[profile_id]["deny"]:
            lines.append(f"{actor_name} deny {profile_id}-deny")

    # Admin permissions
    if profile_cache[admin_profile_id]["allow"]:
        lines.append(f"group:ideaadmin allow {admin_profile_id}-allow")
    if profile_cache[admin_profile_id]["deny"]:
        lines.append(f"group:ideaadmin deny {admin_profile_id}-deny")

    # Owner permissions (uses admin profile)
    if profile_cache[admin_profile_id]["allow"]:
        lines.append(f"%owner% allow {admin_profile_id}-allow")
    if profile_cache[admin_profile_id]["deny"]:
        lines.append(f"%owner% deny {admin_profile_id}-deny")

    return newline.join(lines) + newline


def _build_set_permissions_command(permissions_file_base64: str, base_os: str) -> str:
    """Build the shell command to write permissions and apply via dcv set-permissions.

    SECURITY: permissions_file_base64 is interpolated into the shell command string.
    The caller MUST validate it against BASE64_PATTERN before calling this function.
    That regex ([A-Za-z0-9+/=]) is the security boundary preventing shell injection.
    """
    if base_os == "windows":
        return (
            f'$sessionId = (& "C:\\Program Files\\NICE\\DCV\\Server\\bin\\dcv.exe" list-sessions --json | ConvertFrom-Json)[0].id; '
            f'New-Item -ItemType Directory -Path "C:\\Program Files\\NICE\\DCV\\$sessionId" -Force | Out-Null; '
            f'[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String("{permissions_file_base64}")) '
            f'| Set-Content -Path "C:\\Program Files\\NICE\\DCV\\$sessionId\\{PERMISSIONS_FILENAME}" -Encoding ASCII; '
            f'& "C:\\Program Files\\NICE\\DCV\\Server\\bin\\dcv.exe" set-permissions --session $sessionId --file "C:\\Program Files\\NICE\\DCV\\$sessionId\\{PERMISSIONS_FILENAME}"'
        )
    return (
        f"SESSION_ID=$(dcv list-sessions --json | python3 -c \"import sys,json; print(json.load(sys.stdin)[0]['id'])\"); "
        f"mkdir -p /etc/dcv/$SESSION_ID; "
        f'echo "{permissions_file_base64}" | base64 -d > /etc/dcv/$SESSION_ID/{PERMISSIONS_FILENAME}; '
        f"dcv set-permissions --session $SESSION_ID --file /etc/dcv/$SESSION_ID/{PERMISSIONS_FILENAME}"
    )


def _send_and_wait(
    ssm_permission_batches: Dict[Tuple[str, str], List[Dict[str, str]]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Send SSM commands per (base_os, permissions_file) group and wait for results.

    Returns (successful_list, unsuccessful_list).
    """
    unsuccessful_list: List[Dict[str, Any]] = []
    pending_commands: List[Dict[str, Any]] = []

    for (base_os, perm_file), batch_sessions in ssm_permission_batches.items():
        command = _build_set_permissions_command(perm_file, base_os)
        for i in range(0, len(batch_sessions), ssm_utils.SSM_DEFAULT_BATCH_SIZE):
            batch = batch_sessions[i : i + ssm_utils.SSM_DEFAULT_BATCH_SIZE]
            instance_ids = [s["instance_id"] for s in batch]
            try:
                cmd = ssm_utils.send_command(
                    instance_ids=instance_ids,
                    commands=[command],
                    base_os=base_os,
                )
                command_id = cmd["CommandId"]

                for session in batch:
                    pending_commands.append(
                        {
                            "session_id": session["session_id"],
                            "command_id": command_id,
                            "instance_id": session["instance_id"],
                        }
                    )
            except ClientError as e:
                error_msg = f"Failed to send SSM command: {e}"
                logger.error(error_msg)
                for session in batch:
                    unsuccessful_list.append(
                        {
                            "session_id": session["session_id"],
                            "failure_reason": error_msg,
                        }
                    )

    successful_list, wait_failures = ssm_utils.collect_command_results(pending_commands)
    unsuccessful_list.extend(wait_failures)
    return successful_list, unsuccessful_list


def _group_sessions_by_os_and_permissions(
    session_requests: List[Dict[str, Any]],
) -> Tuple[Dict[Tuple[str, str], List[Dict[str, str]]], List[Dict[str, Any]]]:
    """Look up sessions by RES session ID and group by (base_os, permissions_file).

    Reuses sessions.group_sessions_by_os for session lookup and validation,
    then sub-groups by permissions_file for batched SSM dispatch.

    Returns (ssm_permission_batches, unsuccessful_list).
    """
    session_ids = [r["session_id"] for r in session_requests]
    permissions_map = {r["session_id"]: r["permissions_file"] for r in session_requests}

    existing_sessions = sessions.get_sessions_by_ids(session_ids)
    session_map = {sid: existing_sessions.get(sid) for sid in session_ids}
    base_os_groups, unsuccessful_list = sessions.group_sessions_by_os(session_map)

    ssm_permission_batches: Dict[Tuple[str, str], List[Dict[str, str]]] = {}
    for os_key, sessions_list in base_os_groups.items():
        for session in sessions_list:
            session_id = session["session_id"]
            perm_file = permissions_map[session_id]
            ssm_permission_batches.setdefault((os_key, perm_file), []).append(session)

    return ssm_permission_batches, unsuccessful_list


def update_session_permissions(
    session_requests: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Update DCV session permissions via SSM.

    Expects pre-validated inputs (session_id and permissions_file present and valid).

    Args:
        session_requests: List of dicts with keys: session_id, permissions_file.
            session_id is the RES (idea) session ID.

    Returns (successful_list, unsuccessful_list) where:
      - successful: {"session_id": str}
      - unsuccessful: {"session_id": str, "failure_reason": str}
    """
    if not session_requests:
        return [], []

    ssm_permission_batches, unsuccessful_list = _group_sessions_by_os_and_permissions(
        session_requests
    )

    successful_list, send_unsuccessful = _send_and_wait(ssm_permission_batches)
    unsuccessful_list.extend(send_unsuccessful)

    return successful_list, unsuccessful_list
