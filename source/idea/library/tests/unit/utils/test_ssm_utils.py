#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError, WaiterError
from res.utils import ssm_utils

INSTANCE_ID = "i-1234567890abcdef0"
COMMAND_ID = "cmd-abc123"
SESSION_ID = "ses-12345"
REGION = "us-east-1"
ACCOUNT_ID = "123456789012"
CLUSTER_NAME = "test-env"
BUCKET_NAME = f"{CLUSTER_NAME}-ssm-command-output-{REGION}-{ACCOUNT_ID}"
S3_OUTPUT_URL = f"https://s3.{REGION}.amazonaws.com/{BUCKET_NAME}/dcv-session/{SESSION_ID}/{COMMAND_ID}/{INSTANCE_ID}/awsrunShellScript/0.awsrunShellScript/stdout"

_mock_ssm = MagicMock()
_mock_s3 = MagicMock()


@pytest.fixture(autouse=True)
def _setup(monkeypatch):
    _mock_ssm.reset_mock(side_effect=True)
    _mock_s3.reset_mock(side_effect=True)
    ssm_utils._get_ssm_output_bucket_name.cache_clear()
    monkeypatch.setattr(ssm_utils, "_get_ssm_client", lambda: _mock_ssm)
    monkeypatch.setattr(ssm_utils, "_get_s3_client", lambda: _mock_s3)
    monkeypatch.setattr(
        ssm_utils.cluster_settings,
        "get_setting",
        lambda key, **kwargs: BUCKET_NAME,
    )
    yield


class TestSendCommand:
    def test_linux_uses_shell_script(self):
        _mock_ssm.send_command.return_value = {"Command": {"CommandId": COMMAND_ID}}

        ssm_utils.send_command(
            instance_ids=[INSTANCE_ID],
            commands=["dcv get-screenshot --json"],
            base_os="linux",
        )

        call_kwargs = _mock_ssm.send_command.call_args[1]
        assert call_kwargs["DocumentName"] == "AWS-RunShellScript"

    def test_windows_uses_powershell(self):
        _mock_ssm.send_command.return_value = {"Command": {"CommandId": COMMAND_ID}}

        ssm_utils.send_command(
            instance_ids=[INSTANCE_ID],
            commands=["dcv get-screenshot --json"],
            base_os="windows",
        )

        call_kwargs = _mock_ssm.send_command.call_args[1]
        assert call_kwargs["DocumentName"] == "AWS-RunPowerShellScript"

    def test_s3_bucket(self):
        _mock_ssm.send_command.return_value = {"Command": {"CommandId": COMMAND_ID}}

        ssm_utils.send_command(
            instance_ids=[INSTANCE_ID],
            commands=["echo hi"],
            base_os="linux",
        )

        call_kwargs = _mock_ssm.send_command.call_args[1]
        assert call_kwargs["OutputS3BucketName"] == BUCKET_NAME

    def test_output_to_s3_false_omits_bucket(self):
        _mock_ssm.send_command.return_value = {"Command": {"CommandId": COMMAND_ID}}

        ssm_utils.send_command(
            instance_ids=[INSTANCE_ID],
            commands=["echo hi"],
            base_os="linux",
            output_to_s3=False,
        )

        call_kwargs = _mock_ssm.send_command.call_args[1]
        assert "OutputS3BucketName" not in call_kwargs

    def test_returns_command(self):
        expected = {"CommandId": COMMAND_ID, "Status": "Pending"}
        _mock_ssm.send_command.return_value = {"Command": expected}

        result = ssm_utils.send_command(
            instance_ids=[INSTANCE_ID],
            commands=["echo hi"],
            base_os="linux",
        )

        assert result == expected

    def test_custom_timeout(self):
        _mock_ssm.send_command.return_value = {"Command": {"CommandId": COMMAND_ID}}

        ssm_utils.send_command(
            instance_ids=[INSTANCE_ID],
            commands=["echo hi"],
            base_os="linux",
            timeout_seconds=120,
        )

        call_kwargs = _mock_ssm.send_command.call_args[1]
        assert call_kwargs["TimeoutSeconds"] == 120

    def test_propagates_client_error(self):
        _mock_ssm.send_command.side_effect = ClientError(
            {"Error": {"Code": "InvalidInstanceId"}}, "SendCommand"
        )

        with pytest.raises(ClientError):
            ssm_utils.send_command(
                instance_ids=[INSTANCE_ID],
                commands=["echo hi"],
                base_os="linux",
            )

    def test_multiple_instance_ids(self):
        _mock_ssm.send_command.return_value = {"Command": {"CommandId": COMMAND_ID}}

        ssm_utils.send_command(
            instance_ids=[INSTANCE_ID, "i-second"],
            commands=["echo hi"],
            base_os="linux",
        )

        call_kwargs = _mock_ssm.send_command.call_args[1]
        assert call_kwargs["InstanceIds"] == [INSTANCE_ID, "i-second"]


class TestSendCommandToOsGroups:
    LINUX_CMD = "dcv list-sessions && dcv get-screenshot"
    WINDOWS_CMD = "& dcv.exe list-sessions"
    COMMANDS = {"linux": LINUX_CMD, "windows": WINDOWS_CMD}

    def test_single_os_group(self):
        _mock_ssm.send_command.return_value = {"Command": {"CommandId": COMMAND_ID}}
        os_groups = {
            "linux": [
                {"session_id": "ses-1", "instance_id": INSTANCE_ID},
                {"session_id": "ses-2", "instance_id": "i-second"},
            ]
        }

        pending, unsuccessful = ssm_utils.send_command_to_os_groups(
            os_groups, self.COMMANDS
        )

        assert len(pending) == 2
        assert len(unsuccessful) == 0
        _mock_ssm.send_command.assert_called_once()
        call_kwargs = _mock_ssm.send_command.call_args[1]
        assert call_kwargs["InstanceIds"] == [INSTANCE_ID, "i-second"]
        assert call_kwargs["Parameters"]["commands"] == [self.LINUX_CMD]
        assert pending[0]["command_id"] == COMMAND_ID
        assert pending[1]["command_id"] == COMMAND_ID

    def test_windows_command_selection(self):
        _mock_ssm.send_command.return_value = {"Command": {"CommandId": COMMAND_ID}}
        os_groups = {"windows": [{"session_id": "ses-1", "instance_id": INSTANCE_ID}]}

        ssm_utils.send_command_to_os_groups(os_groups, self.COMMANDS)

        call_kwargs = _mock_ssm.send_command.call_args[1]
        assert call_kwargs["Parameters"]["commands"] == [self.WINDOWS_CMD]
        assert call_kwargs["DocumentName"] == "AWS-RunPowerShellScript"

    def test_client_error_marks_batch_unsuccessful(self):
        _mock_ssm.send_command.side_effect = ClientError(
            {"Error": {"Code": "InvalidInstanceId"}}, "SendCommand"
        )
        os_groups = {"linux": [{"session_id": "ses-1", "instance_id": INSTANCE_ID}]}

        pending, unsuccessful = ssm_utils.send_command_to_os_groups(
            os_groups, self.COMMANDS
        )

        assert len(pending) == 0
        assert len(unsuccessful) == 1
        assert "Failed to send SSM command batch" in unsuccessful[0]["failure_reason"]

    def test_custom_batch_size(self):
        _mock_ssm.send_command.return_value = {"Command": {"CommandId": COMMAND_ID}}
        os_groups = {
            "linux": [
                {"session_id": f"ses-{i}", "instance_id": f"i-{i}"} for i in range(3)
            ]
        }

        pending, unsuccessful = ssm_utils.send_command_to_os_groups(
            os_groups, self.COMMANDS, batch_size=2
        )

        assert len(pending) == 3
        assert len(unsuccessful) == 0
        assert _mock_ssm.send_command.call_count == 2

    def test_empty_os_groups(self):
        pending, unsuccessful = ssm_utils.send_command_to_os_groups({}, self.COMMANDS)

        assert len(pending) == 0
        assert len(unsuccessful) == 0
        _mock_ssm.send_command.assert_not_called()

    def test_output_to_s3_false_propagates(self):
        _mock_ssm.send_command.return_value = {"Command": {"CommandId": COMMAND_ID}}
        os_groups = {"linux": [{"session_id": "ses-1", "instance_id": INSTANCE_ID}]}

        ssm_utils.send_command_to_os_groups(
            os_groups, self.COMMANDS, output_to_s3=False
        )

        call_kwargs = _mock_ssm.send_command.call_args[1]
        assert "OutputS3BucketName" not in call_kwargs


class TestCollectCommandResults:
    """Generic per-command result collector used by SSM-based API handlers."""

    PENDING = [
        {
            "session_id": SESSION_ID,
            "command_id": COMMAND_ID,
            "instance_id": INSTANCE_ID,
        }
    ]

    def test_success_invokes_callback(self):
        mock_waiter = MagicMock()
        _mock_ssm.get_waiter.return_value = mock_waiter
        _mock_ssm.get_command_invocation.return_value = {
            "Status": "Success",
            "StandardOutputContent": "ok",
        }

        def on_success(sid, result):
            return {"session_id": sid, "output": result["StandardOutputContent"]}

        successful, unsuccessful = ssm_utils.collect_command_results(
            self.PENDING, on_success
        )

        assert len(successful) == 1
        assert len(unsuccessful) == 0
        assert successful[0] == {"session_id": SESSION_ID, "output": "ok"}

    def test_wait_failure_marks_unsuccessful(self):
        mock_waiter = MagicMock()
        mock_waiter.wait.side_effect = WaiterError("command_executed", "timeout", {})
        _mock_ssm.get_waiter.return_value = mock_waiter
        _mock_ssm.get_command_invocation.return_value = {"Status": "InProgress"}

        called = []

        def on_success(sid, result):
            called.append(sid)
            return {}

        successful, unsuccessful = ssm_utils.collect_command_results(
            self.PENDING, on_success
        )

        assert len(successful) == 0
        assert len(unsuccessful) == 1
        assert "failed to execute" in unsuccessful[0]["failure_reason"]
        assert called == []

    def test_non_success_status_marks_unsuccessful(self):
        mock_waiter = MagicMock()
        _mock_ssm.get_waiter.return_value = mock_waiter
        _mock_ssm.get_command_invocation.return_value = {"Status": "Failed"}

        called = []

        def on_success(sid, result):
            called.append(sid)
            return {}

        successful, unsuccessful = ssm_utils.collect_command_results(
            self.PENDING, on_success
        )

        assert len(successful) == 0
        assert len(unsuccessful) == 1
        assert "failed with status: Failed" in unsuccessful[0]["failure_reason"]
        assert called == []

    def test_callback_exception_marks_unsuccessful(self):
        mock_waiter = MagicMock()
        _mock_ssm.get_waiter.return_value = mock_waiter
        _mock_ssm.get_command_invocation.return_value = {"Status": "Success"}

        def on_success(sid, result):
            raise ValueError("bad output")

        successful, unsuccessful = ssm_utils.collect_command_results(
            self.PENDING, on_success
        )

        assert len(successful) == 0
        assert len(unsuccessful) == 1
        assert (
            "Failed to process SSM command output" in unsuccessful[0]["failure_reason"]
        )
        assert "bad output" in unsuccessful[0]["failure_reason"]

    def test_empty_pending_returns_empty(self):
        successful, unsuccessful = ssm_utils.collect_command_results(
            [], lambda s, r: {}
        )

        assert successful == []
        assert unsuccessful == []

    def test_default_on_success_returns_session_id_only(self):
        """When on_success is omitted, success entries default to {'session_id': sid}."""
        mock_waiter = MagicMock()
        _mock_ssm.get_waiter.return_value = mock_waiter
        _mock_ssm.get_command_invocation.return_value = {"Status": "Success"}

        successful, unsuccessful = ssm_utils.collect_command_results(self.PENDING)

        assert len(successful) == 1
        assert len(unsuccessful) == 0
        assert successful[0] == {"session_id": SESSION_ID}


class TestWaitForCommand:
    def test_returns_on_success(self):
        mock_waiter = MagicMock()
        _mock_ssm.get_waiter.return_value = mock_waiter
        _mock_ssm.get_command_invocation.return_value = {
            "Status": "Success",
            "StandardOutputUrl": S3_OUTPUT_URL,
        }

        result = ssm_utils.wait_for_command(COMMAND_ID, INSTANCE_ID)

        mock_waiter.wait.assert_called_once()
        assert result["Status"] == "Success"
        assert result["StandardOutputUrl"] == S3_OUTPUT_URL

    def test_waiter_config(self):
        mock_waiter = MagicMock()
        _mock_ssm.get_waiter.return_value = mock_waiter
        _mock_ssm.get_command_invocation.return_value = {"Status": "Success"}

        ssm_utils.wait_for_command(
            COMMAND_ID, INSTANCE_ID, max_wait_time=20, wait_interval=5
        )

        waiter_kwargs = mock_waiter.wait.call_args[1]
        assert waiter_kwargs["WaiterConfig"]["Delay"] == 5
        assert waiter_kwargs["WaiterConfig"]["MaxAttempts"] == 4

    def test_raises_timeout_when_still_in_progress(self):
        mock_waiter = MagicMock()
        mock_waiter.wait.side_effect = WaiterError("command_executed", "timeout", {})
        _mock_ssm.get_waiter.return_value = mock_waiter
        _mock_ssm.get_command_invocation.return_value = {"Status": "InProgress"}

        with pytest.raises(TimeoutError, match="timed out after"):
            ssm_utils.wait_for_command(COMMAND_ID, INSTANCE_ID)

    def test_raises_runtime_error_on_command_failure(self):
        mock_waiter = MagicMock()
        mock_waiter.wait.side_effect = WaiterError("command_executed", "failed", {})
        _mock_ssm.get_waiter.return_value = mock_waiter
        _mock_ssm.get_command_invocation.return_value = {"Status": "Failed"}

        with pytest.raises(RuntimeError, match="failed with status: Failed"):
            ssm_utils.wait_for_command(COMMAND_ID, INSTANCE_ID)


class TestReadCommandOutputFromS3:
    def test_reads_stdout_from_url(self):
        _mock_s3.get_object.return_value = {
            "Body": MagicMock(read=lambda: b'{"base64": "abc123"}')
        }

        result = ssm_utils.read_command_output_from_s3(S3_OUTPUT_URL)

        assert result == '{"base64": "abc123"}'
        call_kwargs = _mock_s3.get_object.call_args[1]
        assert call_kwargs["Bucket"] == BUCKET_NAME
        assert call_kwargs["Key"].endswith("/stdout")

    def test_raises_on_client_error(self):
        _mock_s3.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey"}}, "GetObject"
        )

        with pytest.raises(ClientError):
            ssm_utils.read_command_output_from_s3(S3_OUTPUT_URL)

    def test_raises_on_malformed_url_no_key(self):
        with pytest.raises(ValueError, match="Could not extract S3 key"):
            ssm_utils.read_command_output_from_s3(
                "https://s3.us-east-1.amazonaws.com/my-bucket"
            )

    def test_raises_on_empty_url(self):
        with pytest.raises(ValueError, match="Unrecognized S3 URL format"):
            ssm_utils.read_command_output_from_s3("")

    def test_reads_virtual_hosted_style_url(self):
        _mock_s3.get_object.return_value = {
            "Body": MagicMock(read=lambda: b'{"base64": "abc123"}')
        }
        url = f"https://{BUCKET_NAME}.s3.{REGION}.amazonaws.com/dcv-session/{SESSION_ID}/stdout"

        result = ssm_utils.read_command_output_from_s3(url)

        assert result == '{"base64": "abc123"}'
        call_kwargs = _mock_s3.get_object.call_args[1]
        assert call_kwargs["Bucket"] == BUCKET_NAME
        assert call_kwargs["Key"].endswith("/stdout")

    def test_raises_on_unrecognized_url_format(self):
        with pytest.raises(ValueError, match="Unrecognized S3 URL format"):
            ssm_utils.read_command_output_from_s3("https://example.com/some/path")
