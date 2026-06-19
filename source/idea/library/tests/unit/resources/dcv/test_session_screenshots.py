#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
from unittest.mock import patch

from botocore.exceptions import ClientError
from res.resources.dcv import session_screenshots

SESSION_ID_1 = "ses-111"
SESSION_ID_2 = "ses-222"
INSTANCE_ID_1 = "i-aaa"
COMMAND_ID_1 = "cmd-111"
S3_URL = "https://s3.us-east-1.amazonaws.com/bucket/key/stdout"
DCV_OUTPUT = json.dumps({"format": "png", "base64": "iVBOR..."})

PATCH_SESSIONS = "res.resources.dcv.session_screenshots.sessions"
PATCH_SSM = "res.resources.dcv.session_screenshots.ssm_utils"


@patch(PATCH_SSM)
def test_parse_screenshot_output_success(mock_ssm):
    mock_ssm.read_command_output_from_s3.return_value = DCV_OUTPUT

    result = session_screenshots._parse_screenshot_output(
        SESSION_ID_1, {"StandardOutputUrl": S3_URL}
    )

    assert result["session_id"] == SESSION_ID_1
    assert result["images"][0]["format"] == "png"
    assert result["images"][0]["data"] == "iVBOR..."
    assert result["images"][0]["primary"] is True


@patch(PATCH_SSM)
def test_parse_screenshot_output_s3_read_failure_raises(mock_ssm):
    import pytest

    mock_ssm.read_command_output_from_s3.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey"}}, "GetObject"
    )

    with pytest.raises(ClientError):
        session_screenshots._parse_screenshot_output(
            SESSION_ID_1, {"StandardOutputUrl": S3_URL}
        )


@patch(PATCH_SSM)
def test_parse_screenshot_output_invalid_json_raises(mock_ssm):
    import json

    import pytest

    mock_ssm.read_command_output_from_s3.return_value = "not json"

    with pytest.raises(json.JSONDecodeError):
        session_screenshots._parse_screenshot_output(
            SESSION_ID_1, {"StandardOutputUrl": S3_URL}
        )


@patch(PATCH_SSM)
def test_parse_screenshot_output_non_dict_raises(mock_ssm):
    import pytest

    mock_ssm.read_command_output_from_s3.return_value = '["unexpected", "array"]'

    with pytest.raises(ValueError, match="Expected dict"):
        session_screenshots._parse_screenshot_output(
            SESSION_ID_1, {"StandardOutputUrl": S3_URL}
        )


@patch(PATCH_SSM)
@patch(PATCH_SESSIONS)
def test_get_session_screenshots_success(mock_sessions, mock_ssm):
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
        [{"session_id": SESSION_ID_1, "images": []}],
        [],
    )

    successful, unsuccessful = session_screenshots.get_session_screenshots(
        [SESSION_ID_1]
    )

    assert len(successful) == 1
    assert len(unsuccessful) == 0


@patch(PATCH_SSM)
@patch(PATCH_SESSIONS)
def test_get_session_screenshots_mixed_success_and_not_found(mock_sessions, mock_ssm):
    mock_sessions.group_sessions_by_os.return_value = (
        {"linux": [{"session_id": SESSION_ID_1, "instance_id": INSTANCE_ID_1}]},
        [{"session_id": SESSION_ID_2, "failure_reason": "not found"}],
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
        [{"session_id": SESSION_ID_1, "images": []}],
        [],
    )

    successful, unsuccessful = session_screenshots.get_session_screenshots(
        [SESSION_ID_1, SESSION_ID_2]
    )

    assert len(successful) == 1
    assert len(unsuccessful) == 1


@patch(PATCH_SSM)
@patch(PATCH_SESSIONS)
def test_get_session_screenshots_empty_input(mock_sessions, mock_ssm):
    mock_sessions.group_sessions_by_os.return_value = ({}, [])
    mock_ssm.send_command_to_os_groups.return_value = ([], [])
    mock_ssm.collect_command_results.return_value = ([], [])

    successful, unsuccessful = session_screenshots.get_session_screenshots([])

    assert len(successful) == 0
    assert len(unsuccessful) == 0


@patch(PATCH_SSM)
@patch(PATCH_SESSIONS)
def test_get_session_screenshots_missing_id_passed_as_none(mock_sessions, mock_ssm):
    found_session = {"idea_session_id": SESSION_ID_1, "base_os": "linux"}
    mock_sessions.get_sessions_by_ids.return_value = {SESSION_ID_1: found_session}
    mock_sessions.group_sessions_by_os.return_value = ({}, [])
    mock_ssm.send_command_to_os_groups.return_value = ([], [])
    mock_ssm.collect_command_results.return_value = ([], [])

    session_screenshots.get_session_screenshots([SESSION_ID_1, SESSION_ID_2])

    mock_sessions.group_sessions_by_os.assert_called_once_with(
        {SESSION_ID_1: found_session, SESSION_ID_2: None}
    )
