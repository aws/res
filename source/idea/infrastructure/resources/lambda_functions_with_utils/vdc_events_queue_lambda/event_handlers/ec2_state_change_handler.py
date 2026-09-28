#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict

from datamodel.models.backend.virtual_desktop_session_state import (  # type: ignore
    VirtualDesktopSessionState,
)
from res.exceptions import UserSessionNotFound  # type: ignore
from res.resources import sessions  # type: ignore
from res.utils import logging_utils  # type: ignore

logger = logging_utils.get_logger(__name__)

TERMINAL_STATES = {
    VirtualDesktopSessionState.STOPPED,
    VirtualDesktopSessionState.DELETING,
    VirtualDesktopSessionState.DELETED,
    VirtualDesktopSessionState.ERROR,
}
SETUP_STATES = {
    VirtualDesktopSessionState.PROVISIONING,
    VirtualDesktopSessionState.CREATING,
    VirtualDesktopSessionState.INITIALIZING,
    VirtualDesktopSessionState.RESUMING,
}


def handle(message_id: str, body: Dict[str, Any]) -> None:
    detail: Dict[str, Any] = body.get("detail", {})
    instance_id: str = detail.get("instance-id", "")
    state: str = detail.get("state", "")

    if not instance_id:
        logger.error(f"[msg-id: {message_id}] Missing instance-id in event detail.")
        return

    try:
        session = sessions.get_session_by_instance_id(instance_id)
    except UserSessionNotFound:
        logger.info(
            f"[msg-id: {message_id}] No RES session for instance {instance_id}. Ignoring."
        )
        return

    if not session:
        logger.error(
            f"[msg-id: {message_id}] Empty session record for instance {instance_id}."
        )
        return

    if state in ("stopping", "stopped"):
        _handle_stopping(message_id, session, state)
    elif state == "running":
        _handle_running(message_id, session)
    else:
        logger.info(
            f"[msg-id: {message_id}] instance={instance_id} state={state}. NO-OP."
        )


def _handle_stopping(message_id: str, session: Dict[str, Any], state: str) -> None:
    session_id: str = session.get("idea_session_id", "")
    current_state: str = session.get("state", "")

    if current_state in TERMINAL_STATES:
        # Event ignored.
        logger.info(
            f"[msg-id: {message_id}] Session {session_id} in state {current_state}. Ignoring."
        )
        return

    if current_state in SETUP_STATES:
        # In these states, the EC2 Instance STOPPED was not expected. Hence error.
        logger.error(
            f"[msg-id: {message_id}] Session {session_id} in state {current_state}. Unexpected stop."
        )
        new_state = VirtualDesktopSessionState.ERROR
    else:
        # Was waiting for ec2 stopped/stopping event.
        if state == "stopping":
            new_state = VirtualDesktopSessionState.STOPPING
        elif session.get("is_idle"):
            new_state = VirtualDesktopSessionState.STOPPED_IDLE
        else:
            new_state = VirtualDesktopSessionState.STOPPED

    owner: str = session.get("owner", "")
    sessions.update_session_state(owner=owner, session_id=session_id, state=new_state)
    logger.info(
        f"[msg-id: {message_id}] Session {session_id}: {current_state} -> {new_state}"
    )


def _handle_running(message_id: str, session: Dict[str, Any]) -> None:
    session_id: str = session.get("idea_session_id", "")
    session["is_idle"] = False
    sessions.update_session(new_session=session, old_session=None)
    logger.info(f"[msg-id: {message_id}] Session {session_id}: set is_idle=False")
