#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
from typing import Any, Dict, List, Optional, Tuple

from res.resources import sessions
from res.utils import ssm_utils

LINUX_DESCRIBE_SESSION_COMMAND = (
    "SESSION_ID=$(dcv list-sessions --json | python3 -c"
    " \"import sys,json; print(json.load(sys.stdin)[0]['id'])\") &&"
    " dcv describe-session $SESSION_ID --json"
)

WINDOWS_DESCRIBE_SESSION_COMMAND = (
    '$sessions = & "C:\\Program Files\\NICE\\DCV\\Server\\bin\\dcv.exe"'
    " list-sessions --json | ConvertFrom-Json;"
    " $sessionId = $sessions[0].id;"
    ' & "C:\\Program Files\\NICE\\DCV\\Server\\bin\\dcv.exe"'
    " describe-session $sessionId --json"
)


DESCRIBE_SESSION_COMMANDS = {
    "linux": LINUX_DESCRIBE_SESSION_COMMAND,
    "windows": WINDOWS_DESCRIBE_SESSION_COMMAND,
}


def _parse_describe_session_output(
    session_id: str, command_result: Dict[str, Any]
) -> Dict[str, Any]:
    """Parse a single ``dcv describe-session --json`` SSM result.

    Reads ``StandardOutputContent`` inline (no S3 round-trip).
    """
    output = command_result.get("StandardOutputContent", "")
    dcv_output = json.loads(output)
    if not isinstance(dcv_output, dict):
        raise ValueError(
            f"Expected dict from DCV output, got {type(dcv_output).__name__}"
        )
    return {
        "session_id": session_id,
        "num_of_connections": int(dcv_output.get("num-of-connections", 0)),
    }


def describe_sessions(
    session_map: Dict[str, Optional[Dict[str, Any]]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Describe DCV sessions via SSM and return per-session active connection counts.

    Groups validated sessions by OS, sends batched SSM commands (up to 50
    instances per call), and parses each host's `dcv describe-session` JSON
    output.

    Args:
        session_map: mapping of session_id -> session record (or None when
            the session was not found).

    Returns (successful_list, unsuccessful_list) where:
      - successful: {"session_id": str, "num_of_connections": int}
      - unsuccessful: {"session_id": str, "failure_reason": str}
    """
    os_groups, unsuccessful_list = sessions.group_sessions_by_os(session_map)
    pending_commands, send_failures = ssm_utils.send_command_to_os_groups(
        os_groups, DESCRIBE_SESSION_COMMANDS, output_to_s3=False
    )
    unsuccessful_list.extend(send_failures)
    successful_list, read_failures = ssm_utils.collect_command_results(
        pending_commands, _parse_describe_session_output
    )
    unsuccessful_list.extend(read_failures)
    return successful_list, unsuccessful_list
