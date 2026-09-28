#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from unittest.mock import patch

import pytest
from res.resources import ssm_commands


class TestSendSsmCommand:

    @patch("res.resources.ssm_commands.table_utils.create_item")
    @patch("res.utils.ssm_utils.send_command")
    @patch("res.resources.ssm_commands.cluster_settings.get_setting")
    def test_sends_command_with_notification(
        self, mock_get_setting, mock_send, mock_create_item
    ):
        mock_get_setting.side_effect = lambda key: {
            "vdc.ssm_commands_sns_topic_arn": "arn:aws:sns:us-east-1:123:topic",
            "vdc.ssm_commands_pass_role_arn": "arn:aws:iam::123:role/role",
        }.get(key)
        mock_send.return_value = {"CommandId": "cmd-123"}

        result = ssm_commands.send_ssm_command(
            instance_id="i-abc",
            commands=["echo hello"],
            base_os="amazonlinux2",
            command_type="DELETE_LOCK_FILES_LINUX_EXECUTION",
            additional_payload={"idea_session_id": "ses-1"},
        )

        assert result == "cmd-123"
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]
        assert call_kwargs["instance_ids"] == ["i-abc"]
        assert (
            call_kwargs["notification_config"]["NotificationArn"]
            == "arn:aws:sns:us-east-1:123:topic"
        )
        assert call_kwargs["service_role_arn"] == "arn:aws:iam::123:role/role"

        mock_create_item.assert_called_once()
        item = mock_create_item.call_args[1]["item"]
        assert item["command_id"] == "cmd-123"
        assert item["command_type"] == "DELETE_LOCK_FILES_LINUX_EXECUTION"
        assert item["additional_payload"]["idea_session_id"] == "ses-1"

    @patch("res.resources.ssm_commands.table_utils.create_item")
    @patch("res.utils.ssm_utils.send_command")
    @patch("res.resources.ssm_commands.cluster_settings.get_setting")
    def test_sends_command_without_notification_when_no_topic(
        self, mock_get_setting, mock_send, mock_create_item
    ):
        mock_get_setting.return_value = None
        mock_send.return_value = {"CommandId": "cmd-456"}

        ssm_commands.send_ssm_command(
            instance_id="i-abc",
            commands=["echo hello"],
            base_os="windows",
            command_type="WINDOWS_ENABLE_USERDATA_EXECUTION",
            additional_payload={},
        )

        call_kwargs = mock_send.call_args[1]
        assert call_kwargs["notification_config"] is None
        assert call_kwargs["service_role_arn"] is None


class TestCreateSsmCommand:

    @patch("res.resources.ssm_commands.table_utils.create_item")
    def test_stores_command_in_ddb(self, mock_create_item):
        mock_create_item.return_value = {"command_id": "cmd-789"}

        result = ssm_commands.create_ssm_command(
            command_id="cmd-789",
            command_type="DELETE_LOCK_FILES_LINUX_EXECUTION",
            additional_payload={"idea_session_id": "ses-1", "instance_id": "i-abc"},
        )

        assert result == {"command_id": "cmd-789"}
        mock_create_item.assert_called_once_with(
            table_name="vdc.controller.ssm-commands",
            item={
                "command_id": "cmd-789",
                "command_type": "DELETE_LOCK_FILES_LINUX_EXECUTION",
                "additional_payload": {
                    "idea_session_id": "ses-1",
                    "instance_id": "i-abc",
                },
            },
        )


class TestSubmitSsmCommandToGetCpuUtilization:

    @pytest.fixture
    def env(self, monkeypatch):
        monkeypatch.setenv("environment_name", "res-test")

    @patch("res.resources.ssm_commands.send_ssm_command")
    def test_linux_base_os_uses_shell_probe(self, mock_send, env):
        mock_send.return_value = "cmd-linux"

        result = ssm_commands.submit_ssm_command_to_get_cpu_utilization(
            instance_id="i-abc",
            idea_session_id="ses-1",
            idea_session_owner="user1",
            base_os="amazonlinux2",
        )

        assert result == "cmd-linux"
        call_kwargs = mock_send.call_args[1]
        assert call_kwargs["commands"] == ssm_commands._LINUX_CPU_PROBE
        assert call_kwargs["instance_id"] == "i-abc"
        assert call_kwargs["base_os"] == "amazonlinux2"
        assert (
            call_kwargs["command_type"]
            == ssm_commands.CPU_UTILIZATION_CHECK_STOP_SCHEDULED_SESSION
        )
        assert call_kwargs["additional_payload"] == {
            "idea_session_id": "ses-1",
            "idea_session_owner": "user1",
            "instance_id": "i-abc",
        }
        assert (
            call_kwargs["cloud_watch_log_group"]
            == "/res-test/vdc/dcv-session/ses-1/cpu-utilization"
        )
        assert (
            call_kwargs["output_s3_key_prefix"]
            == "/res-test/vdc/dcv-session/ses-1/cpu-utilization"
        )

    @patch("res.resources.ssm_commands.send_ssm_command")
    def test_windows_base_os_uses_powershell_probe(self, mock_send, env):
        mock_send.return_value = "cmd-win"

        ssm_commands.submit_ssm_command_to_get_cpu_utilization(
            instance_id="i-win",
            idea_session_id="ses-2",
            idea_session_owner="user2",
            base_os="windows",
        )

        call_kwargs = mock_send.call_args[1]
        assert call_kwargs["commands"] == ssm_commands._WINDOWS_CPU_PROBE
        assert call_kwargs["base_os"] == "windows"
