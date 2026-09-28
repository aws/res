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

import json
import logging
import re
import time
from typing import Any, Optional

from res.resources import cluster_settings  # type: ignore[import]
from res.utils import ssm_utils  # type: ignore[import]

from tests.integration.framework.client.api_client import (
    ApiClient,
    DeleteSoftwareStackRequestContent,
)
from tests.integration.framework.utils.model_utils import get_backend_model_class

logger = logging.getLogger(__name__)

INSUFFICIENT_CAPACITY_PATTERNS = (
    re.compile(r"InsufficientInstanceCapacity", re.IGNORECASE),
    re.compile(
        r"We currently do not have sufficient .+ capacity",
        re.IGNORECASE,
    ),
)


def is_insufficient_capacity(message: Optional[str]) -> bool:
    """Return True if ``message`` matches a known EC2 insufficient-capacity error."""
    if not message:
        return False
    return any(pattern.search(message) for pattern in INSUFFICIENT_CAPACITY_PATTERNS)


# Backend data-model classes (source/idea/data-model). The session APIs consume
# and return these.
VirtualDesktopSessionState = get_backend_model_class(
    "virtual_desktop_session_state", "VirtualDesktopSessionState"
)
VirtualDesktopBaseOS = get_backend_model_class(
    "virtual_desktop_base_os", "VirtualDesktopBaseOs"
)

SESSION_COMPLETE_STATES = [
    VirtualDesktopSessionState.READY,
    VirtualDesktopSessionState.ERROR,
    VirtualDesktopSessionState.STOPPED,
    VirtualDesktopSessionState.DELETED,
]
# AWS credentials on CodeBuild expires in an hour.
# Make sure to leave enough time for the test setup and cleanup when running in the code pipeline.
MAX_WAITING_TIME_FOR_LAUNCHING_SESSION_IN_SEC = 3600
MAX_WAITING_TIME_FOR_DELETING_SESSION_IN_SEC = 300
MAX_WAITING_TIME_FOR_STOPPING_IDLE_SESSION_IN_SEC = 1200
MAX_WAITING_TIME_FOR_SESSION_STATE_IN_SEC = 1200
MAX_WAITING_TIME_FOR_SESSION_CONNECTION_COUNT_IN_SEC = 300
MAX_WAITING_TIME_FOR_AMI_CREATION = 900

# Max seconds to wait for the idle config file to be created by the VDI bootstrap.
# The bootstrap writes the default idle config during instance initialization;
# we must wait for it to exist before overwriting with forced idle settings.
MAX_WAITING_TIME_FOR_IDLE_CONFIG_FILE_IN_SEC = 300


def wait_for_launching_session(api_client: ApiClient, session: Any) -> Any:
    start_time = time.time()
    while time.time() - start_time < MAX_WAITING_TIME_FOR_LAUNCHING_SESSION_IN_SEC:
        get_session_info_response = api_client.get_session(
            session.idea_session_id, session.owner
        )
        # The response already deserializes into the new-model session with nested
        # types coerced (server, project, ...). Rebuilding via the constructor
        # would leave nested values as plain dicts (no attribute access).
        session = get_session_info_response.session  # type: ignore
        session_state = session.state

        if session_state in SESSION_COMPLETE_STATES:
            assert (
                session_state == VirtualDesktopSessionState.READY
            ), f"Session {session.name} is in an unexpected state {session_state}: {session.failure_reason}"

            return session

        logger.debug(f"session state: {session_state}")
        time.sleep(30)

    assert (
        False
    ), f"Failed to launch session {session.name} within {MAX_WAITING_TIME_FOR_LAUNCHING_SESSION_IN_SEC} seconds"


def wait_for_deleting_session(api_client: ApiClient, session: Any) -> None:
    start_time = time.time()
    while time.time() - start_time < MAX_WAITING_TIME_FOR_DELETING_SESSION_IN_SEC:
        list_sessions_response = api_client.list_sessions()
        existing_sessions = list_sessions_response.listing  # type: ignore

        if existing_sessions and any(
            existing_session.idea_session_id == session.idea_session_id
            for existing_session in existing_sessions
        ):
            logger.debug(f"session {session.idea_session_id} is still available")
            time.sleep(30)
        else:
            return

    assert (
        False
    ), f"Failed to delete session {session.dcv_session_id} within {MAX_WAITING_TIME_FOR_DELETING_SESSION_IN_SEC} seconds"


def wait_for_stopped_idle_session(api_client: ApiClient, session: Any) -> None:
    start_time = time.time()
    while time.time() - start_time < MAX_WAITING_TIME_FOR_STOPPING_IDLE_SESSION_IN_SEC:
        get_session_info_response = api_client.get_session(
            session.idea_session_id, session.owner
        )
        session = get_session_info_response.session  # type: ignore
        session_state = session.state

        if session_state == VirtualDesktopSessionState.STOPPED_IDLE:
            return

        logger.debug(f"session state: {session_state}")
        time.sleep(30)

    assert (
        False
    ), f"Failed to stop idle session {session.name} within {MAX_WAITING_TIME_FOR_STOPPING_IDLE_SESSION_IN_SEC} seconds"


# Terminal states a session cannot recover from. If a session reaches one of
# these while waiting for a different state, it will never reach the target, so
# we fail fast instead of polling until timeout.
SESSION_UNRECOVERABLE_STATES = [
    VirtualDesktopSessionState.ERROR,
    VirtualDesktopSessionState.DELETED,
]


def wait_for_session_state(
    api_client: ApiClient,
    session: Any,
    expected_state: str,
    timeout: int = MAX_WAITING_TIME_FOR_SESSION_STATE_IN_SEC,
) -> Any:
    """Poll a session until it reaches ``expected_state``.

    Fails fast if the session reaches an unrecoverable terminal state that is
    not the one we are waiting for. Returns the refreshed backend-model session
    so callers can read its updated fields.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        get_session_info_response = api_client.get_session(
            session.idea_session_id, session.owner
        )
        session = get_session_info_response.session  # type: ignore
        session_state = session.state

        if session_state == expected_state:
            return session

        if (
            session_state in SESSION_UNRECOVERABLE_STATES
            and session_state != expected_state
        ):
            assert False, (
                f"Session {session.name} reached unrecoverable state "
                f"{session_state} while waiting for {expected_state}: "
                f"{session.failure_reason}"
            )

        logger.debug(f"session state: {session_state}")
        time.sleep(30)

    assert False, (
        f"Session {session.name} did not reach {expected_state} within "
        f"{timeout} seconds"
    )


"""
Force the auto stop script to run on a session by setting the idle config to an idle timeout threshold of 0
LINUX: Overwrites the existing idle config file
WINDOWS: Writes a new idle config file due to a race condition where the Idle_Config file is typically not created before the integ test runs
"""


def force_idle_session(session: Any, transition_state: str = "Stop") -> None:
    """Force idle detection by writing the idle config to the VDI instance.

    Args:
        session: The session object (must have server.instance_id, base_os, name)
        transition_state: "Stop" for idle-stop or "Terminate" for idle-terminate
    """
    logger.info(
        f"Setting {session.name} session config to idle "
        f"(transition_state={transition_state})..."
    )
    forced_idle_cpu_threshold = 100
    forced_idle_timeout = 0
    base_os = "windows" if session.base_os == VirtualDesktopBaseOS.WINDOWS else "linux"
    if base_os == "linux":
        linux_idle_config_path = "/opt/idea/.idle_config.json"
        vdi_helper_api_url = cluster_settings.get_setting(
            "vdc.vdi_helper_api_gateway_url"
        )
        idle_config = json.dumps(
            {
                "idle_cpu_threshold": forced_idle_cpu_threshold,
                "idle_timeout": forced_idle_timeout,
                "vdi_helper_api_url": vdi_helper_api_url,
                "transition_state": transition_state,
            }
        )
        commands = [
            "sudo su -",
            f"timeout={MAX_WAITING_TIME_FOR_IDLE_CONFIG_FILE_IN_SEC}; elapsed=0; while [ ! -f {linux_idle_config_path} ]; do sleep 1; elapsed=$((elapsed+1)); if [ $elapsed -ge $timeout ]; then echo 'Timed out waiting for {linux_idle_config_path}' >&2; exit 1; fi; done",
            f"cat > {linux_idle_config_path} << 'IDLE_EOF'\n{idle_config}\nIDLE_EOF",
        ]
    else:
        windows_idle_config_path = r"C:\IDEA\Idle_Config.json"
        vdi_helper_api_url = cluster_settings.get_setting(
            "vdc.vdi_helper_api_gateway_url"
        )
        commands = [
            f"$timeout = {MAX_WAITING_TIME_FOR_IDLE_CONFIG_FILE_IN_SEC}; $elapsed = 0; while (-not (Test-Path '{windows_idle_config_path}')) {{ Start-Sleep -Seconds 1; $elapsed++; if ($elapsed -ge $timeout) {{ throw 'Timed out waiting for {windows_idle_config_path}' }} }}",
            "$idle_config = New-Object PSObject",
            f"$idle_config | Add-Member -MemberType NoteProperty -Name 'idle_cpu_threshold' -Value '{forced_idle_cpu_threshold}'",
            f"$idle_config | Add-Member -MemberType NoteProperty -Name 'idle_timeout' -Value '{forced_idle_timeout}'",
            f"$idle_config | Add-Member -MemberType NoteProperty -Name 'vdi_helper_api_url' -Value '{vdi_helper_api_url}'",
            f"$idle_config | Add-Member -MemberType NoteProperty -Name 'transition_state' -Value '{transition_state}'",
            f"$idle_config | ConvertTo-Json | Set-Content -Path '{windows_idle_config_path}' -Encoding UTF8",
        ]

    instance_id = session.server.instance_id
    result = ssm_utils.send_command(
        instance_ids=[instance_id],
        commands=commands,
        base_os=base_os,
        output_to_s3=False,
    )
    ssm_utils.wait_for_command(result["CommandId"], instance_id)


def force_idle_session_terminate(session: Any) -> None:
    """Force idle detection with transition_state=Terminate (session deleted, not stopped)."""
    force_idle_session(session, transition_state="Terminate")


MAX_WAITING_TIME_FOR_DELETED_IDLE_SESSION_IN_SEC = 1200


def wait_for_deleted_idle_session(api_client: ApiClient, session: Any) -> None:
    """Poll until a session reaches DELETED state (used for terminate-on-idle)."""
    start_time = time.time()
    while time.time() - start_time < MAX_WAITING_TIME_FOR_DELETED_IDLE_SESSION_IN_SEC:
        list_sessions_response = api_client.list_sessions()
        existing_sessions = list_sessions_response.listing or []  # type: ignore[attr-defined]

        if not any(
            s.idea_session_id == session.idea_session_id for s in existing_sessions
        ):
            return

        for s in existing_sessions:
            if (
                s.idea_session_id == session.idea_session_id
                and s.state == VirtualDesktopSessionState.DELETED
            ):
                return

        logger.debug(f"session {session.idea_session_id} still exists, waiting...")
        time.sleep(30)

    assert False, (
        f"Session {session.name} was not deleted within "
        f"{MAX_WAITING_TIME_FOR_DELETED_IDLE_SESSION_IN_SEC} seconds"
    )


def wait_for_session_connection_count(session: Any, count: int) -> None:
    start_time = time.time()
    while (
        time.time() - start_time < MAX_WAITING_TIME_FOR_SESSION_CONNECTION_COUNT_IN_SEC
    ):
        base_os = (
            "windows" if session.base_os == VirtualDesktopBaseOS.WINDOWS else "linux"
        )
        dcv_session_info = describe_dcv_session(
            session.server.instance_id, session.dcv_session_id, base_os
        )

        num_of_connections = dcv_session_info["num-of-connections"]
        if num_of_connections is not None and num_of_connections == count:
            return

        logger.debug(f"num of connections: {num_of_connections}")
        time.sleep(30)

    assert (
        False
    ), f"Failed to reach session connection count {count} within {MAX_WAITING_TIME_FOR_SESSION_CONNECTION_COUNT_IN_SEC} seconds"


def wait_for_software_stack_to_be_active(
    api_client: ApiClient, software_stack: Any
) -> None:
    start_time = time.time()
    while time.time() - start_time < MAX_WAITING_TIME_FOR_AMI_CREATION:
        response = api_client.get_software_stack(
            stack_id=software_stack.stack_id, base_os=software_stack.base_os.value
        )
        if (
            response is not None
            and response.software_stack is not None
            and response.software_stack.enabled
        ):
            return
        time.sleep(30)
    api_client.delete_software_stack(
        stack_id=software_stack.stack_id,
        request_content=DeleteSoftwareStackRequestContent(
            base_os=software_stack.base_os
        ),
    )
    assert (
        False
    ), f"Failed to create software stack {software_stack.stack_id} within {MAX_WAITING_TIME_FOR_AMI_CREATION} seconds"


def describe_dcv_session(
    server_instance_id: str,
    dcv_session_id: str,
    base_os: str,
) -> Any:
    if base_os == "windows":
        commands = [
            rf'&"C:\Program Files\NICE\DCV\Server\bin\dcv.exe" describe-session {dcv_session_id} -j'
        ]
    else:
        commands = [f"sudo dcv describe-session {dcv_session_id} -j"]

    result = ssm_utils.send_command(
        instance_ids=[server_instance_id],
        commands=commands,
        base_os=base_os,
        output_to_s3=False,
    )
    invocation = ssm_utils.wait_for_command(result["CommandId"], server_instance_id)
    output = invocation.get("StandardOutputContent", "")

    try:
        dcv_session_info = json.loads(output)
    except json.JSONDecodeError as e:
        assert False, e

    return dcv_session_info
