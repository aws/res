#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import os
from typing import Any, Dict

from res.resources import (  # type: ignore
    cluster_settings,
    sessions,
    software_stacks,
    ssm_commands,
    vdi_management,
)
from res.utils import logging_utils, ssm_utils  # type: ignore

logger = logging_utils.get_logger(__name__)

# SSM command types matching VirtualDesktopSSMCommandType values
WINDOWS_ENABLE_USERDATA = "WINDOWS_ENABLE_USERDATA_EXECUTION"
WINDOWS_DISABLE_USERDATA = "WINDOWS_DISABLE_USERDATA_EXECUTION"
DELETE_LOCK_FILES_LINUX = "DELETE_LOCK_FILES_LINUX_EXECUTION"
CPU_UTILIZATION_CHECK = "CPU_UTILIZATION_CHECK_STOP_SCHEDULED_SESSION"


def handle(message_id: str, body: Dict[str, Any]) -> None:
    """Process an SSM command status notification from SNS.

    The body is the SNS envelope with a 'Message' field containing the SSM notification JSON.
    """
    message_str = body.get("Message", "")
    if isinstance(message_str, str):
        try:
            message = json.loads(message_str) if message_str else {}
        except json.JSONDecodeError:
            logger.error(f"[msg-id: {message_id}] Malformed JSON in SNS Message field.")
            return
    else:
        message = message_str

    command_id = message.get("commandId", "")
    status = message.get("status", "")

    if not command_id:
        logger.error(f"[msg-id: {message_id}] Missing commandId in SSM notification.")
        return

    ssm_command = ssm_commands.get_ssm_command(command_id)
    if not ssm_command:
        logger.error(f"[msg-id: {message_id}] SSM command not found: {command_id}")
        return

    command_type = ssm_command.get("command_type", "")
    additional_payload = ssm_command.get("additional_payload", {})

    logger.info(
        f"[msg-id: {message_id}] SSM command {command_id} type={command_type} status={status}"
    )

    if status not in ("Success", "Failed"):
        logger.info(f"[msg-id: {message_id}] Ignoring intermediate status: {status}")
        return

    if command_type == WINDOWS_ENABLE_USERDATA:
        _handle_enable_userdata(message_id, command_id, status, additional_payload)
    elif command_type == WINDOWS_DISABLE_USERDATA:
        _handle_disable_userdata(message_id, command_id, status, additional_payload)
    elif command_type == DELETE_LOCK_FILES_LINUX:
        _handle_delete_lock_files(message_id, command_id, status, additional_payload)
    elif command_type == CPU_UTILIZATION_CHECK:
        _handle_cpu_utilization(message_id, command_id, status, additional_payload)
    else:
        logger.error(f"[msg-id: {message_id}] Unsupported command type: {command_type}")


def _handle_enable_userdata(
    message_id: str, command_id: str, status: str, payload: Dict[str, Any]
) -> None:
    idea_session_id = payload.get("idea_session_id", "")
    idea_session_owner = payload.get("idea_session_owner", "")
    software_stack_id = payload.get("software_stack_id", "")

    session = sessions.get_session(owner=idea_session_owner, session_id=idea_session_id)
    if not session:
        logger.error(f"[msg-id: {message_id}] Session not found: {idea_session_id}")
        return

    if status == "Success":
        ssm_commands.delete_ssm_command(command_id)
        _continue_software_stack_creation(session, software_stack_id)
    else:
        session["state"] = "ERROR"
        logger.error(f"[msg-id: {message_id}] Session {idea_session_id} moved to ERROR")

    sessions.update_session(new_session=session, old_session=None)


def _handle_disable_userdata(
    message_id: str, command_id: str, status: str, payload: Dict[str, Any]
) -> None:
    idea_session_id = payload.get("idea_session_id", "")
    idea_session_owner = payload.get("idea_session_owner", "")

    session = sessions.get_session(owner=idea_session_owner, session_id=idea_session_id)
    if not session:
        logger.error(f"[msg-id: {message_id}] Session not found: {idea_session_id}")
        return

    if status == "Success":
        ssm_commands.delete_ssm_command(command_id)
        session["locked"] = False
        server = session.get("server", {})
        server["locked"] = False
        session["server"] = server
    else:
        session["state"] = "ERROR"
        logger.error(f"[msg-id: {message_id}] Session {idea_session_id} moved to ERROR")

    sessions.update_session(new_session=session, old_session=None)


def _handle_delete_lock_files(
    message_id: str, command_id: str, status: str, payload: Dict[str, Any]
) -> None:
    idea_session_id = payload.get("idea_session_id", "")
    idea_session_owner = payload.get("idea_session_owner", "")
    software_stack_id = payload.get("software_stack_id", "")

    session = sessions.get_session(owner=idea_session_owner, session_id=idea_session_id)
    if not session:
        logger.error(f"[msg-id: {message_id}] Session not found: {idea_session_id}")
        return

    if status == "Success":
        ssm_commands.delete_ssm_command(command_id)
        _continue_software_stack_creation(session, software_stack_id)
    else:
        logger.error(
            f"[msg-id: {message_id}] Session {idea_session_id} lock file deletion failed"
        )

    if session.get("server"):
        sessions.update_session(new_session=session, old_session=None)


def _handle_cpu_utilization(
    message_id: str, command_id: str, status: str, payload: Dict[str, Any]
) -> None:
    idea_session_id = payload.get("idea_session_id", "")
    idea_session_owner = payload.get("idea_session_owner", "")
    instance_id = payload.get("instance_id", "")

    session = sessions.get_session(owner=idea_session_owner, session_id=idea_session_id)
    if not session:
        logger.error(f"[msg-id: {message_id}] Session not found: {idea_session_id}")
        return

    if status == "Success":
        ssm_output = ssm_utils.get_command_invocation(
            command_id=command_id, instance_id=instance_id
        )
        stdout = ssm_output.get("StandardOutputContent", "")
        try:
            output = json.loads(stdout) if stdout else {}
        except json.JSONDecodeError:
            logger.error(
                f"[msg-id: {message_id}] Invalid JSON in SSM output for command {command_id}"
            )
            return
        cpu_utilization_raw = output.get("CPUAveragePerformanceLast10Secs")
        if cpu_utilization_raw is None:
            logger.error(
                f"[msg-id: {message_id}] Missing CPUAveragePerformanceLast10Secs in SSM output for command {command_id}"
            )
            return
        cpu_utilization = float(cpu_utilization_raw)

        cpu_threshold = float(
            cluster_settings.get_setting("vdc.dcv_session.cpu_utilization_threshold")
        )
        if cpu_utilization < cpu_threshold:
            logger.info(
                f"[msg-id: {message_id}] CPU {cpu_utilization} < threshold {cpu_threshold}, stopping session"
            )
            success_list, fail_list = vdi_management.stop_sessions([session])
            if fail_list:
                raise Exception(
                    f"Error stopping session {idea_session_id}: {fail_list[0].get('failure_reason')}"
                )
        else:
            logger.info(
                f"[msg-id: {message_id}] CPU {cpu_utilization} >= threshold {cpu_threshold}, not stopping"
            )

        ssm_commands.delete_ssm_command(command_id)
    else:
        logger.error(
            f"[msg-id: {message_id}] CPU utilization check failed for session {idea_session_id}"
        )


def _continue_software_stack_creation(
    session: Dict[str, Any], software_stack_id: str
) -> None:
    """Create AMI from instance and publish validate event."""
    base_os = session.get("base_os", "")
    instance_id = session.get("server", {}).get("instance_id", "")
    queue_url = os.environ.get("EVENTS_QUEUE_URL", "")

    software_stacks.continue_software_stack_creation(
        software_stack_id=software_stack_id,
        base_os=base_os,
        instance_id=instance_id,
        session_id=session.get("idea_session_id", ""),
        owner=session.get("owner", ""),
        events_queue_url=queue_url,
    )
