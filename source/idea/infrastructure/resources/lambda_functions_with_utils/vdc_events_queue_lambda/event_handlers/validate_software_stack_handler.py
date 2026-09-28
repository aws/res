#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict

from res import exceptions
from res.resources import sessions, software_stacks  # type: ignore
from res.resources.ssm_commands import send_ssm_command  # type: ignore
from res.utils import ec2_utils, logging_utils  # type: ignore

logger = logging_utils.get_logger(__name__)


class AMINotReady(Exception):
    """Raised when AMI is not yet available — triggers SQS redelivery via batchItemFailures."""

    pass


def handle(message_id: str, body: Dict[str, Any]) -> None:
    """Validate that a software stack's AMI is available.

    If the AMI is not ready, raises AMINotReady which causes the Lambda to report
    this message as a batch item failure — SQS will redeliver after the visibility timeout.
    """
    detail = body.get("detail", {})
    software_stack_id = detail.get("software_stack_id", "")
    base_os = detail.get("base_os", "")
    idea_session_id = detail.get("idea_session_id", "")
    idea_session_owner = detail.get("idea_session_owner", "")
    instance_id = detail.get("instance_id", "")

    if not software_stack_id or not base_os:
        logger.error(f"[msg-id: {message_id}] Invalid software_stack_id or base_os")
        return

    try:
        stack = software_stacks.get_software_stack(
            stack_id=software_stack_id, base_os=base_os
        )
    except exceptions.SoftwareStackNotFound:
        logger.error(
            f"[msg-id: {message_id}] Software stack not found: {software_stack_id}"
        )
        return

    ami_id = stack.get("ami_id", "")
    if not ami_id:
        logger.error(f"[msg-id: {message_id}] No AMI ID on stack {software_stack_id}")
        return

    image = ec2_utils.describe_image_id(ami_id)
    if not image:
        raise AMINotReady(f"AMI {ami_id} not found")

    ami_state = image.get("State", "")

    if ami_state == "available":
        # AMI is ready — enable the software stack
        software_stacks.update_software_stack(software_stack={**stack, "enabled": True})
        logger.info(
            f"[msg-id: {message_id}] AMI {ami_id} available, stack {software_stack_id} enabled"
        )

        if base_os == "windows":
            # Disable userdata execution on Windows
            send_ssm_command(
                instance_id=instance_id,
                commands=[
                    'Unregister-ScheduledTask -TaskName "Amazon Ec2 Launch - Instance Initialization" -Confirm:$False'
                ],
                base_os=base_os,
                command_type="WINDOWS_DISABLE_USERDATA_EXECUTION",
                additional_payload={
                    "idea_session_id": idea_session_id,
                    "idea_session_owner": idea_session_owner,
                    "instance_id": instance_id,
                },
            )
        else:
            # Linux — unlock the session
            session = sessions.get_session(
                owner=idea_session_owner, session_id=idea_session_id
            )
            if session:
                server = session.get("server", {})
                server["locked"] = False
                session["server"] = server
                session["locked"] = False
                sessions.update_session(new_session=session, old_session=None)
    else:
        # Check for terminal failure states that will never become available
        terminal_failure_states = ("failed", "error", "invalid", "deregistered")
        if ami_state in terminal_failure_states:
            logger.error(
                f"[msg-id: {message_id}] AMI {ami_id} is in terminal state: {ami_state}"
            )
            return

        # AMI not ready — raise to trigger redelivery
        raise AMINotReady(f"AMI {ami_id} state is {ami_state}, not yet available")
