#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict
from unittest.mock import MagicMock, patch

from res.resources import vdi_management


def _session(
    session_id: str, instance_id: str, is_idle: bool = False
) -> Dict[str, Any]:
    return {
        "idea_session_id": session_id,
        "owner": "admin1",
        "name": f"vdi-{session_id}",
        "state": "READY",
        "is_idle": is_idle,
        "hibernation_enabled": False,
        "server": {"instance_id": instance_id},
    }


@patch("res.resources.vdi_management.hibernate_servers")
@patch("res.resources.vdi_management.stop_servers")
@patch(
    "res.resources.vdi_management.user_sessions.transition_session_state_if",
    return_value={"idea_session_id": "s1", "state": "STOPPING"},
)
@patch("res.resources.vdi_management.validate_sessions_to_delete")
def test_stop_sessions_transition_wins_issues_stop(
    _mock_validate: MagicMock,
    mock_transition: MagicMock,
    mock_stop_servers: MagicMock,
    _mock_hibernate: MagicMock,
) -> None:
    # READY -> STOPPING transition succeeds -> the instance is stopped, and the
    # idle flag is persisted atomically so the stop finalizes as STOPPED_IDLE.
    vdi_management.stop_sessions([_session("s1", "i-1", is_idle=True)])

    mock_stop_servers.assert_called_once_with([{"instance_id": "i-1"}])
    # The full session (incl. is_idle) is persisted so the stop finalizes as
    # STOPPED_IDLE.
    _, kwargs = mock_transition.call_args
    assert kwargs["session"]["is_idle"] is True


@patch("res.resources.vdi_management.hibernate_servers")
@patch("res.resources.vdi_management.stop_servers")
@patch(
    "res.resources.vdi_management.user_sessions.transition_session_state_if",
    return_value=None,
)
@patch("res.resources.vdi_management.validate_sessions_to_delete")
def test_stop_sessions_transition_lost_skips_redundant_stop(
    _mock_validate: MagicMock,
    _mock_transition: MagicMock,
    mock_stop_servers: MagicMock,
    _mock_hibernate: MagicMock,
) -> None:
    # A concurrent stop already transitioned it (returns None) -> no stop issued.
    vdi_management.stop_sessions([_session("s1", "i-1")])

    mock_stop_servers.assert_called_once_with([])
