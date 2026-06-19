#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
from typing import Any, Dict, List, Tuple

from res.resources import sessions
from res.utils import ssm_utils, time_utils

# Thumbnail size for dashboard preview.
# Matches the DCV Session Manager Broker configuration for
# session-screenshot-max-width and session-screenshot-max-height.
THUMBNAIL_MAX_WIDTH = 800
THUMBNAIL_MAX_HEIGHT = 600

LINUX_SCREENSHOT_COMMAND = (
    "SESSION_ID=$(dcv list-sessions --json | python3 -c"
    " \"import sys,json; print(json.load(sys.stdin)[0]['id'])\") &&"
    f" dcv get-screenshot --json --format png --max-width {THUMBNAIL_MAX_WIDTH} --max-height {THUMBNAIL_MAX_HEIGHT} --primary $SESSION_ID"
)

WINDOWS_SCREENSHOT_COMMAND = (
    '$sessions = & "C:\\Program Files\\NICE\\DCV\\Server\\bin\\dcv.exe"'
    " list-sessions --json | ConvertFrom-Json;"
    " $sessionId = $sessions[0].id;"
    ' & "C:\\Program Files\\NICE\\DCV\\Server\\bin\\dcv.exe"'
    f" get-screenshot --json --format png --max-width {THUMBNAIL_MAX_WIDTH} --max-height {THUMBNAIL_MAX_HEIGHT} --primary $sessionId"
)


SCREENSHOT_COMMANDS = {
    "linux": LINUX_SCREENSHOT_COMMAND,
    "windows": WINDOWS_SCREENSHOT_COMMAND,
}


def _parse_screenshot_output(
    session_id: str, command_result: Dict[str, Any]
) -> Dict[str, Any]:
    """Read a single ``dcv get-screenshot`` SSM result from S3 and decode it."""
    output = ssm_utils.read_command_output_from_s3(
        command_result.get("StandardOutputUrl", "")
    )
    dcv_output = json.loads(output)
    if not isinstance(dcv_output, dict):
        raise ValueError(
            f"Expected dict from DCV output, got {type(dcv_output).__name__}"
        )
    return {
        "session_id": session_id,
        "images": [
            {
                "format": dcv_output.get("format", "png"),
                "data": dcv_output.get("base64", ""),
                "created_on": time_utils.current_time_ms(),
                "primary": True,
            }
        ],
    }


def get_session_screenshots(
    session_ids: List[str],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Get screenshots for a list of DCV sessions.

    Groups sessions by OS, sends batched SSM commands (up to 50 instances
    per call), then waits and reads outputs from S3.

    Returns (successful_list, unsuccessful_list) where:
      - successful: {"session_id": str, "images": [{"format", "data", "created_on", "primary"}]}
      - unsuccessful: {"session_id": str, "failure_reason": str}
    """
    existing_sessions = sessions.get_sessions_by_ids(session_ids)
    session_map = {sid: existing_sessions.get(sid) for sid in session_ids}
    os_groups, unsuccessful_list = sessions.group_sessions_by_os(session_map)
    pending_commands, send_failures = ssm_utils.send_command_to_os_groups(
        os_groups, SCREENSHOT_COMMANDS
    )
    unsuccessful_list.extend(send_failures)
    successful_list, read_failures = ssm_utils.collect_command_results(
        pending_commands, _parse_screenshot_output
    )
    unsuccessful_list.extend(read_failures)
    return successful_list, unsuccessful_list
