#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from unittest.mock import MagicMock, patch

import res.exceptions as exceptions  # type: ignore
from res.resources import sessions as user_sessions  # type: ignore


@patch("res.resources.sessions.table_utils.update_item")
def test_transition_state_if_success_returns_updated(mock_update: MagicMock) -> None:
    mock_update.return_value = {"idea_session_id": "s1", "state": "STOPPING"}

    result = user_sessions.transition_session_state_if(
        owner="admin1",
        session_id="s1",
        new_state="STOPPING",
        expected_current_state="READY",
    )

    assert result == {"idea_session_id": "s1", "state": "STOPPING"}


@patch("res.resources.sessions.table_utils.update_item")
def test_transition_state_if_condition_failed_returns_none(
    mock_update: MagicMock,
) -> None:
    mock_update.side_effect = exceptions.ConditionalCheckFailed("rejected")

    result = user_sessions.transition_session_state_if(
        owner="admin1",
        session_id="s1",
        new_state="STOPPING",
        expected_current_state="READY",
    )

    assert result is None
