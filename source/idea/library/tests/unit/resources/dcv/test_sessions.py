#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
from unittest.mock import patch

from res.resources.dcv import sessions as dcv_sessions

SESSION_ID_1 = "ses-111"
SESSION_ID_2 = "ses-222"
OWNER_1 = "alice"
INSTANCE_ID_1 = "i-aaa"
COMMAND_ID_1 = "cmd-111"
DCV_OUTPUT = json.dumps({"id": "console", "num-of-connections": 3})

PATCH_SESSIONS = "res.resources.dcv.sessions.sessions"
PATCH_SSM = "res.resources.dcv.sessions.ssm_utils"


def test_parse_describe_session_output_success():
    result = dcv_sessions._parse_describe_session_output(
        SESSION_ID_1, {"StandardOutputContent": DCV_OUTPUT}
    )

    assert result == {"session_id": SESSION_ID_1, "num_of_connections": 3}


def test_parse_describe_session_output_missing_field_defaults_to_zero():
    # DCV output without num-of-connections (e.g. older builds or partial output).
    result = dcv_sessions._parse_describe_session_output(
        SESSION_ID_1, {"StandardOutputContent": json.dumps({"id": "console"})}
    )

    assert result["num_of_connections"] == 0


def test_parse_describe_session_output_invalid_json_raises():
    import pytest

    with pytest.raises(json.JSONDecodeError):
        dcv_sessions._parse_describe_session_output(
            SESSION_ID_1, {"StandardOutputContent": "not json"}
        )


def test_parse_describe_session_output_non_dict_raises():
    import pytest

    with pytest.raises(ValueError, match="Expected dict"):
        dcv_sessions._parse_describe_session_output(
            SESSION_ID_1,
            {"StandardOutputContent": json.dumps(["unexpected", "array"])},
        )


@patch(PATCH_SSM)
@patch(PATCH_SESSIONS)
def test_describe_sessions_success(mock_sessions, mock_ssm):
    session_record = {
        "owner": OWNER_1,
        "idea_session_id": SESSION_ID_1,
        "server": {"instance_id": INSTANCE_ID_1},
        "base_os": "amazonlinux2023",
    }
    mock_sessions.group_sessions_by_os.return_value = (
        {"linux": [{"session_id": SESSION_ID_1, "instance_id": INSTANCE_ID_1}]},
        [],
    )
    mock_ssm.send_command_to_os_groups.return_value = (
        [
            {
                "session_id": SESSION_ID_1,
                "command_id": COMMAND_ID_1,
                "instance_id": INSTANCE_ID_1,
            }
        ],
        [],
    )
    mock_ssm.collect_command_results.return_value = (
        [{"session_id": SESSION_ID_1, "num_of_connections": 3}],
        [],
    )

    successful, unsuccessful = dcv_sessions.describe_sessions(
        {SESSION_ID_1: session_record}
    )

    assert len(successful) == 1
    assert len(unsuccessful) == 0
    assert successful[0]["session_id"] == SESSION_ID_1
    assert successful[0]["num_of_connections"] == 3
    # Helper does not look up sessions; caller is responsible.
    mock_sessions.get_session.assert_not_called()
    mock_sessions.group_sessions_by_os.assert_called_once_with(
        {SESSION_ID_1: session_record}
    )


@patch(PATCH_SSM)
@patch(PATCH_SESSIONS)
def test_describe_sessions_session_not_found(mock_sessions, mock_ssm):
    mock_sessions.group_sessions_by_os.return_value = (
        {},
        [
            {
                "session_id": SESSION_ID_1,
                "failure_reason": "User session not found with session_id: ses-111",
            }
        ],
    )
    mock_ssm.send_command_to_os_groups.return_value = ([], [])
    mock_ssm.collect_command_results.return_value = ([], [])

    successful, unsuccessful = dcv_sessions.describe_sessions({SESSION_ID_1: None})

    assert len(successful) == 0
    assert len(unsuccessful) == 1
    assert SESSION_ID_1 == unsuccessful[0]["session_id"]
    mock_sessions.group_sessions_by_os.assert_called_once_with({SESSION_ID_1: None})


@patch(PATCH_SSM)
@patch(PATCH_SESSIONS)
def test_describe_sessions_empty_input(mock_sessions, mock_ssm):
    mock_sessions.group_sessions_by_os.return_value = ({}, [])
    mock_ssm.send_command_to_os_groups.return_value = ([], [])
    mock_ssm.collect_command_results.return_value = ([], [])

    successful, unsuccessful = dcv_sessions.describe_sessions({})

    assert len(successful) == 0
    assert len(unsuccessful) == 0


@patch(PATCH_SSM)
@patch(PATCH_SESSIONS)
def test_describe_sessions_mixed_results(mock_sessions, mock_ssm):
    found_session = {
        "owner": OWNER_1,
        "idea_session_id": SESSION_ID_1,
        "server": {"instance_id": INSTANCE_ID_1},
        "base_os": "amazonlinux2023",
    }

    mock_sessions.group_sessions_by_os.return_value = (
        {"linux": [{"session_id": SESSION_ID_1, "instance_id": INSTANCE_ID_1}]},
        [
            {
                "session_id": SESSION_ID_2,
                "failure_reason": "User session not found with session_id: ses-222",
            }
        ],
    )
    mock_ssm.send_command_to_os_groups.return_value = (
        [
            {
                "session_id": SESSION_ID_1,
                "command_id": COMMAND_ID_1,
                "instance_id": INSTANCE_ID_1,
            }
        ],
        [],
    )
    mock_ssm.collect_command_results.return_value = (
        [{"session_id": SESSION_ID_1, "num_of_connections": 3}],
        [],
    )

    successful, unsuccessful = dcv_sessions.describe_sessions(
        {SESSION_ID_1: found_session, SESSION_ID_2: None}
    )

    assert len(successful) == 1
    assert len(unsuccessful) == 1
    assert successful[0]["session_id"] == SESSION_ID_1
    assert unsuccessful[0]["session_id"] == SESSION_ID_2
