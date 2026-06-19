#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from unittest.mock import Mock, patch

from botocore.exceptions import ClientError
from res.resources.dcv import session_permissions

SESSION_ID_1 = "ses-111"
SESSION_ID_2 = "ses-222"
INSTANCE_ID_1 = "i-aaa"
PERMISSIONS_FILE_B64 = "cGVybWlzc2lvbnM="

PATCH_SESSIONS = "res.resources.dcv.session_permissions.sessions"
PATCH_SSM = "res.resources.dcv.session_permissions.ssm_utils"


# --- _build_set_permissions_command tests ---


def test_build_set_permissions_command_linux():
    cmd = session_permissions._build_set_permissions_command(
        PERMISSIONS_FILE_B64, "linux"
    )

    assert "dcv set-permissions" in cmd
    assert "base64 -d" in cmd
    assert "mkdir -p" in cmd
    assert PERMISSIONS_FILE_B64 in cmd
    assert "/etc/dcv/" in cmd
    assert "idea.perm" in cmd


def test_build_set_permissions_command_windows():
    cmd = session_permissions._build_set_permissions_command(
        PERMISSIONS_FILE_B64, "windows"
    )

    assert "dcv.exe" in cmd
    assert "set-permissions" in cmd
    assert "FromBase64String" in cmd
    assert PERMISSIONS_FILE_B64 in cmd
    assert "C:\\Program Files\\NICE\\DCV\\" in cmd
    assert "idea.perm" in cmd


# --- update_session_permissions tests ---


@patch(PATCH_SSM)
@patch(PATCH_SESSIONS)
def test_update_session_permissions_success(mock_sessions, mock_ssm):
    mock_sessions.group_sessions_by_os.return_value = (
        {"linux": [{"session_id": SESSION_ID_1, "instance_id": INSTANCE_ID_1}]},
        [],
    )
    mock_ssm.SSM_DEFAULT_BATCH_SIZE = 50
    mock_ssm.send_command.return_value = {"CommandId": "cmd-123"}
    mock_ssm.collect_command_results.return_value = (
        [{"session_id": SESSION_ID_1}],
        [],
    )

    successful, unsuccessful = session_permissions.update_session_permissions(
        [
            {
                "session_id": SESSION_ID_1,
                "permissions_file": PERMISSIONS_FILE_B64,
            }
        ]
    )

    assert len(successful) == 1
    assert len(unsuccessful) == 0
    assert successful[0]["session_id"] == SESSION_ID_1
    mock_ssm.send_command.assert_called_once()
    call_kwargs = mock_ssm.send_command.call_args.kwargs
    assert call_kwargs["instance_ids"] == [INSTANCE_ID_1]
    assert call_kwargs["base_os"] == "linux"
    assert len(call_kwargs["commands"]) == 1


@patch(PATCH_SSM)
@patch(PATCH_SESSIONS)
def test_update_session_permissions_session_not_found(mock_sessions, mock_ssm):
    mock_sessions.group_sessions_by_os.return_value = (
        {},
        [
            {
                "session_id": SESSION_ID_1,
                "failure_reason": "User session not found with session_id: ses-111",
            }
        ],
    )
    mock_ssm.SSM_DEFAULT_BATCH_SIZE = 50
    mock_ssm.collect_command_results.return_value = ([], [])

    successful, unsuccessful = session_permissions.update_session_permissions(
        [
            {
                "session_id": SESSION_ID_1,
                "permissions_file": PERMISSIONS_FILE_B64,
            }
        ]
    )

    assert len(successful) == 0
    assert len(unsuccessful) == 1
    assert "session not found" in unsuccessful[0]["failure_reason"].lower()
    mock_ssm.send_command.assert_not_called()


@patch(PATCH_SSM)
@patch(PATCH_SESSIONS)
def test_update_session_permissions_session_lookup_error(mock_sessions, mock_ssm):
    mock_sessions.get_sessions_by_ids.side_effect = RuntimeError("db error")

    import pytest

    with pytest.raises(RuntimeError, match="db error"):
        session_permissions.update_session_permissions(
            [
                {
                    "session_id": SESSION_ID_1,
                    "permissions_file": PERMISSIONS_FILE_B64,
                }
            ]
        )

    mock_sessions.group_sessions_by_os.assert_not_called()
    mock_ssm.send_command.assert_not_called()


@patch(PATCH_SSM)
@patch(PATCH_SESSIONS)
def test_update_session_permissions_no_instance_id(mock_sessions, mock_ssm):
    mock_sessions.group_sessions_by_os.return_value = (
        {},
        [
            {
                "session_id": SESSION_ID_1,
                "failure_reason": "No instance_id found for session with session_id: ses-111",
            }
        ],
    )
    mock_ssm.SSM_DEFAULT_BATCH_SIZE = 50
    mock_ssm.collect_command_results.return_value = ([], [])

    successful, unsuccessful = session_permissions.update_session_permissions(
        [
            {
                "session_id": SESSION_ID_1,
                "permissions_file": PERMISSIONS_FILE_B64,
            }
        ]
    )

    assert len(successful) == 0
    assert len(unsuccessful) == 1
    assert "No instance_id found" in unsuccessful[0]["failure_reason"]
    mock_ssm.send_command.assert_not_called()


@patch(PATCH_SSM)
@patch(PATCH_SESSIONS)
def test_update_session_permissions_ssm_failure(mock_sessions, mock_ssm):
    mock_sessions.group_sessions_by_os.return_value = (
        {"linux": [{"session_id": SESSION_ID_1, "instance_id": INSTANCE_ID_1}]},
        [],
    )
    mock_ssm.SSM_DEFAULT_BATCH_SIZE = 50
    mock_ssm.send_command.side_effect = ClientError(
        {"Error": {"Code": "InvalidInstanceId"}}, "SendCommand"
    )
    mock_ssm.collect_command_results.return_value = ([], [])

    successful, unsuccessful = session_permissions.update_session_permissions(
        [
            {
                "session_id": SESSION_ID_1,
                "permissions_file": PERMISSIONS_FILE_B64,
            }
        ]
    )

    assert len(successful) == 0
    assert len(unsuccessful) == 1
    assert "Failed to send SSM command" in unsuccessful[0]["failure_reason"]


@patch(PATCH_SSM)
@patch(PATCH_SESSIONS)
def test_update_session_permissions_mixed_results(mock_sessions, mock_ssm):
    mock_sessions.group_sessions_by_os.return_value = (
        {"linux": [{"session_id": SESSION_ID_1, "instance_id": INSTANCE_ID_1}]},
        [
            {
                "session_id": SESSION_ID_2,
                "failure_reason": "User session not found with session_id: ses-222",
            }
        ],
    )
    mock_ssm.SSM_DEFAULT_BATCH_SIZE = 50
    mock_ssm.send_command.return_value = {"CommandId": "cmd-123"}
    mock_ssm.collect_command_results.return_value = (
        [{"session_id": SESSION_ID_1}],
        [],
    )

    successful, unsuccessful = session_permissions.update_session_permissions(
        [
            {
                "session_id": SESSION_ID_1,
                "permissions_file": PERMISSIONS_FILE_B64,
            },
            {
                "session_id": SESSION_ID_2,
                "permissions_file": PERMISSIONS_FILE_B64,
            },
        ]
    )

    assert len(successful) == 1
    assert len(unsuccessful) == 1
    assert successful[0]["session_id"] == SESSION_ID_1
    assert unsuccessful[0]["session_id"] == SESSION_ID_2


@patch(PATCH_SSM)
@patch(PATCH_SESSIONS)
def test_update_session_permissions_empty_input(mock_sessions, mock_ssm):
    successful, unsuccessful = session_permissions.update_session_permissions([])

    assert len(successful) == 0
    assert len(unsuccessful) == 0
    mock_sessions.group_sessions_by_os.assert_not_called()
    mock_ssm.send_command.assert_not_called()


@patch(PATCH_SSM)
@patch(PATCH_SESSIONS)
def test_update_session_permissions_missing_id_passed_as_none(mock_sessions, mock_ssm):
    found_session = {"idea_session_id": SESSION_ID_1, "base_os": "linux"}
    mock_sessions.get_sessions_by_ids.return_value = {SESSION_ID_1: found_session}
    mock_sessions.group_sessions_by_os.return_value = ({}, [])
    mock_ssm.SSM_DEFAULT_BATCH_SIZE = 50
    mock_ssm.collect_command_results.return_value = ([], [])

    session_permissions.update_session_permissions(
        [
            {"session_id": SESSION_ID_1, "permissions_file": PERMISSIONS_FILE_B64},
            {"session_id": SESSION_ID_2, "permissions_file": PERMISSIONS_FILE_B64},
        ]
    )

    mock_sessions.group_sessions_by_os.assert_called_once_with(
        {SESSION_ID_1: found_session, SESSION_ID_2: None}
    )


@patch(PATCH_SSM)
@patch(PATCH_SESSIONS)
def test_update_session_permissions_groups_by_os_and_permissions(
    mock_sessions, mock_ssm
):
    """Sessions with different OS types result in separate SSM commands."""
    mock_sessions.group_sessions_by_os.return_value = (
        {
            "linux": [{"session_id": SESSION_ID_1, "instance_id": INSTANCE_ID_1}],
            "windows": [{"session_id": SESSION_ID_2, "instance_id": "i-bbb"}],
        },
        [],
    )
    mock_ssm.SSM_DEFAULT_BATCH_SIZE = 50
    mock_ssm.send_command.return_value = {"CommandId": "cmd-123"}
    mock_ssm.collect_command_results.return_value = (
        [{"session_id": SESSION_ID_1}, {"session_id": SESSION_ID_2}],
        [],
    )

    successful, unsuccessful = session_permissions.update_session_permissions(
        [
            {
                "session_id": SESSION_ID_1,
                "permissions_file": PERMISSIONS_FILE_B64,
            },
            {
                "session_id": SESSION_ID_2,
                "permissions_file": PERMISSIONS_FILE_B64,
            },
        ]
    )

    assert len(successful) == 2
    assert len(unsuccessful) == 0
    assert mock_ssm.send_command.call_count == 2
    call_os_values = sorted(
        call.kwargs["base_os"] for call in mock_ssm.send_command.call_args_list
    )
    assert call_os_values == ["linux", "windows"]


@patch(PATCH_SSM)
@patch(PATCH_SESSIONS)
def test_update_session_permissions_wait_for_command_failure_propagates(
    mock_sessions, mock_ssm
):
    """Failures surfaced by collect_command_results are returned in unsuccessful_list."""
    mock_sessions.group_sessions_by_os.return_value = (
        {"linux": [{"session_id": SESSION_ID_1, "instance_id": INSTANCE_ID_1}]},
        [],
    )
    mock_ssm.SSM_DEFAULT_BATCH_SIZE = 50
    mock_ssm.send_command.return_value = {"CommandId": "cmd-123"}
    mock_ssm.collect_command_results.return_value = (
        [],
        [
            {
                "session_id": SESSION_ID_1,
                "failure_reason": "SSM command for session_id: ses-111 failed to execute: timeout",
            }
        ],
    )

    successful, unsuccessful = session_permissions.update_session_permissions(
        [
            {
                "session_id": SESSION_ID_1,
                "permissions_file": PERMISSIONS_FILE_B64,
            }
        ]
    )

    assert len(successful) == 0
    assert len(unsuccessful) == 1
    assert "failed to execute" in unsuccessful[0]["failure_reason"]


class TestGeneratePermissionsContent:
    def _setup_common(self, monkeypatch, profiles, guest_perms):
        monkeypatch.setattr(
            "res.resources.cluster_settings.get_setting",
            lambda key: "admin-profile",
        )
        monkeypatch.setattr(
            "res.resources.permission_profiles.get_permission_profile",
            lambda pid: profiles[pid],
        )

        if isinstance(guest_perms, Exception):
            monkeypatch.setattr(
                "res.resources.session_permissions.get_session_permission_by_id",
                Mock(side_effect=guest_perms),
            )
        else:
            monkeypatch.setattr(
                "res.resources.session_permissions.get_session_permission_by_id",
                lambda sid: guest_perms,
            )

    def test_admin_only_builtin_profile(self, monkeypatch):
        self._setup_common(
            monkeypatch,
            profiles={
                "admin-profile": {"profile_id": "admin-profile", "builtin": True}
            },
            guest_perms=Exception("not found"),
        )

        result = session_permissions.generate_permissions_content(
            session_id="session-123", admin_username="clusteradmin"
        )

        assert "[groups]" in result
        assert "group:ideaadmin=user:clusteradmin" in result
        assert "[aliases]" in result
        assert "admin-profile-allow=builtin" in result
        assert "[permissions]" in result
        assert "group:ideaadmin allow admin-profile-allow" in result
        assert "%owner% allow admin-profile-allow" in result

    def test_with_guest_permissions(self, monkeypatch):
        self._setup_common(
            monkeypatch,
            profiles={
                "admin-profile": {"profile_id": "admin-profile", "builtin": True},
                "guest-profile": {
                    "profile_id": "guest-profile",
                    "display": True,
                    "clipboard_copy": True,
                    "clipboard_paste": False,
                },
            },
            guest_perms=[
                {"actor_name": "guest-user", "permission_profile_id": "guest-profile"}
            ],
        )

        result = session_permissions.generate_permissions_content(
            session_id="session-123", admin_username="clusteradmin"
        )

        assert "guest-profile-deny=clipboard-paste" in result
        assert "guest-user allow guest-profile-allow" in result
        # guest's deny aliases use the guest's own profile (regression for the AutoSDE bug)
        assert "guest-user deny guest-profile-deny" in result

    def test_windows_newline(self, monkeypatch):
        self._setup_common(
            monkeypatch,
            profiles={
                "admin-profile": {"profile_id": "admin-profile", "builtin": True}
            },
            guest_perms=Exception("none"),
        )

        result = session_permissions.generate_permissions_content(
            session_id="session-123", admin_username="Administrator", newline="\r\n"
        )

        assert "\r\n" in result
        assert result.endswith("\r\n")
