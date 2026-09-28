#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
from unittest.mock import patch

from idea.infrastructure.resources.lambda_functions_with_utils.vdc_events_queue_lambda.handler import (
    handler,
)


def _sqs_record(message_id: str, body: dict) -> dict:
    return {"messageId": message_id, "body": json.dumps(body)}


def test_handler_discards_missing_event_type():
    event = {"Records": [_sqs_record("msg-1", {"detail": {"instance-id": "i-abc"}})]}
    result = handler(event, None)
    assert result == {"batchItemFailures": []}


def test_handler_discards_unhandled_event_type():
    event = {
        "Records": [_sqs_record("msg-2", {"event_type": "UNKNOWN_EVENT", "detail": {}})]
    }
    result = handler(event, None)
    assert result == {"batchItemFailures": []}


def test_handler_reports_failure_on_exception():
    event = {"Records": [{"messageId": "msg-3", "body": "invalid json{{{"}]}
    result = handler(event, None)
    assert result == {"batchItemFailures": [{"itemIdentifier": "msg-3"}]}


def test_handler_partial_batch_failure():
    """One record succeeds (discarded as unhandled), one fails — only the failed one is reported."""
    event = {
        "Records": [
            _sqs_record("msg-ok", {"event_type": "SOME_EVENT", "detail": {}}),
            {"messageId": "msg-bad", "body": "not json"},
        ]
    }
    result = handler(event, None)
    assert result == {"batchItemFailures": [{"itemIdentifier": "msg-bad"}]}


@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_events_queue_lambda.event_handlers.ec2_state_change_handler.sessions"
)
def test_ec2_state_change_updates_session_to_stopped(mock_sessions):
    mock_sessions.get_session_by_instance_id.return_value = {
        "idea_session_id": "s-1",
        "owner": "user1",
        "state": "READY",
        "is_idle": False,
    }
    event = {
        "Records": [
            _sqs_record(
                "msg-5",
                {
                    "event_type": "EC2_INSTANCE_STATE_CHANGED_EVENT",
                    "detail": {"instance-id": "i-abc", "state": "stopped"},
                },
            )
        ]
    }
    result = handler(event, None)
    assert result == {"batchItemFailures": []}
    mock_sessions.update_session_state.assert_called_once_with(
        owner="user1", session_id="s-1", state="STOPPED"
    )


@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_events_queue_lambda.event_handlers.ec2_state_change_handler.sessions"
)
def test_ec2_state_change_stopped_idle(mock_sessions):
    mock_sessions.get_session_by_instance_id.return_value = {
        "idea_session_id": "s-2",
        "owner": "user1",
        "state": "READY",
        "is_idle": True,
    }
    event = {
        "Records": [
            _sqs_record(
                "msg-6",
                {
                    "event_type": "EC2_INSTANCE_STATE_CHANGED_EVENT",
                    "detail": {"instance-id": "i-abc", "state": "stopped"},
                },
            )
        ]
    }
    result = handler(event, None)
    assert result == {"batchItemFailures": []}
    mock_sessions.update_session_state.assert_called_once_with(
        owner="user1", session_id="s-2", state="STOPPED_IDLE"
    )


@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_events_queue_lambda.event_handlers.ec2_state_change_handler.sessions"
)
def test_ec2_state_change_unexpected_stop_sets_error(mock_sessions):
    mock_sessions.get_session_by_instance_id.return_value = {
        "idea_session_id": "s-3",
        "owner": "user1",
        "state": "PROVISIONING",
        "is_idle": False,
    }
    event = {
        "Records": [
            _sqs_record(
                "msg-7",
                {
                    "event_type": "EC2_INSTANCE_STATE_CHANGED_EVENT",
                    "detail": {"instance-id": "i-abc", "state": "stopped"},
                },
            )
        ]
    }
    result = handler(event, None)
    assert result == {"batchItemFailures": []}
    mock_sessions.update_session_state.assert_called_once_with(
        owner="user1", session_id="s-3", state="ERROR"
    )


@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_events_queue_lambda.event_handlers.ec2_state_change_handler.sessions"
)
def test_ec2_state_change_ignores_terminal_state(mock_sessions):
    mock_sessions.get_session_by_instance_id.return_value = {
        "idea_session_id": "s-4",
        "owner": "user1",
        "state": "STOPPED",
        "is_idle": False,
    }
    event = {
        "Records": [
            _sqs_record(
                "msg-8",
                {
                    "event_type": "EC2_INSTANCE_STATE_CHANGED_EVENT",
                    "detail": {"instance-id": "i-abc", "state": "stopped"},
                },
            )
        ]
    }
    result = handler(event, None)
    assert result == {"batchItemFailures": []}
    mock_sessions.update_session_state.assert_not_called()


@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_events_queue_lambda.event_handlers.ec2_state_change_handler.sessions"
)
def test_ec2_state_change_running_clears_idle(mock_sessions):
    mock_sessions.get_session_by_instance_id.return_value = {
        "idea_session_id": "s-5",
        "owner": "user1",
        "state": "READY",
        "is_idle": True,
    }
    event = {
        "Records": [
            _sqs_record(
                "msg-9",
                {
                    "event_type": "EC2_INSTANCE_STATE_CHANGED_EVENT",
                    "detail": {"instance-id": "i-abc", "state": "running"},
                },
            )
        ]
    }
    result = handler(event, None)
    assert result == {"batchItemFailures": []}
    mock_sessions.update_session.assert_called_once()
    call_args = mock_sessions.update_session.call_args
    assert call_args[1]["new_session"]["is_idle"] is False


@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_events_queue_lambda.event_handlers.ec2_state_change_handler.sessions"
)
def test_ec2_state_change_ignores_non_res_instance(mock_sessions):
    from res.exceptions import UserSessionNotFound

    mock_sessions.get_session_by_instance_id.side_effect = UserSessionNotFound(
        "not found"
    )
    event = {
        "Records": [
            _sqs_record(
                "msg-10",
                {
                    "event_type": "EC2_INSTANCE_STATE_CHANGED_EVENT",
                    "detail": {"instance-id": "i-unknown", "state": "running"},
                },
            )
        ]
    }
    result = handler(event, None)
    assert result == {"batchItemFailures": []}


# --- SSM Commands Handler Tests ---


@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_events_queue_lambda.event_handlers.ssm_commands_handler.ssm_commands"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_events_queue_lambda.event_handlers.ssm_commands_handler.sessions"
)
def test_ssm_handler_routes_sns_notification(mock_sessions, mock_ssm_commands):
    """SNS messages (Type: Notification) route to ssm_commands_handler."""
    mock_ssm_commands.get_ssm_command.return_value = {
        "command_type": "WINDOWS_DISABLE_USERDATA_EXECUTION",
        "additional_payload": {"idea_session_id": "s1", "idea_session_owner": "u1"},
    }
    mock_sessions.get_session.return_value = {
        "idea_session_id": "s1",
        "owner": "u1",
        "server": {"locked": True},
    }
    event = {
        "Records": [
            _sqs_record(
                "msg-sns",
                {
                    "Type": "Notification",
                    "Message": json.dumps({"commandId": "cmd-1", "status": "Success"}),
                },
            )
        ]
    }
    result = handler(event, None)
    assert result == {"batchItemFailures": []}
    mock_ssm_commands.delete_ssm_command.assert_called_once_with("cmd-1")


@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_events_queue_lambda.event_handlers.ssm_commands_handler.ssm_commands"
)
def test_ssm_handler_ignores_intermediate_status(mock_ssm_commands):
    """SSM notifications with non-terminal status are ignored."""
    mock_ssm_commands.get_ssm_command.return_value = {
        "command_type": "WINDOWS_DISABLE_USERDATA_EXECUTION",
        "additional_payload": {},
    }
    event = {
        "Records": [
            _sqs_record(
                "msg-int",
                {
                    "Type": "Notification",
                    "Message": json.dumps(
                        {"commandId": "cmd-2", "status": "InProgress"}
                    ),
                },
            )
        ]
    }
    result = handler(event, None)
    assert result == {"batchItemFailures": []}
    mock_ssm_commands.delete_ssm_command.assert_not_called()


@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_events_queue_lambda.event_handlers.ssm_commands_handler.ssm_commands"
)
def test_ssm_handler_missing_command_discards(mock_ssm_commands):
    """Unknown command_id is discarded (not retried)."""
    mock_ssm_commands.get_ssm_command.return_value = None
    event = {
        "Records": [
            _sqs_record(
                "msg-unk",
                {
                    "Type": "Notification",
                    "Message": json.dumps(
                        {"commandId": "cmd-unknown", "status": "Success"}
                    ),
                },
            )
        ]
    }
    result = handler(event, None)
    assert result == {"batchItemFailures": []}


@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_events_queue_lambda.event_handlers.ssm_commands_handler.sessions"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_events_queue_lambda.event_handlers.ssm_commands_handler.ssm_commands"
)
def test_ssm_handler_sets_error_on_failure(mock_ssm_commands, mock_sessions):
    """Failed SSM command sets session state to ERROR."""
    mock_ssm_commands.get_ssm_command.return_value = {
        "command_type": "WINDOWS_ENABLE_USERDATA_EXECUTION",
        "additional_payload": {
            "idea_session_id": "s1",
            "idea_session_owner": "u1",
            "software_stack_id": "ss1",
        },
    }
    mock_sessions.get_session.return_value = {
        "idea_session_id": "s1",
        "owner": "u1",
        "state": "READY",
    }
    event = {
        "Records": [
            _sqs_record(
                "msg-fail",
                {
                    "Type": "Notification",
                    "Message": json.dumps({"commandId": "cmd-3", "status": "Failed"}),
                },
            )
        ]
    }
    result = handler(event, None)
    assert result == {"batchItemFailures": []}
    call_args = mock_sessions.update_session.call_args
    assert call_args[1]["new_session"]["state"] == "ERROR"


# --- Validate Software Stack Handler Tests ---


@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_events_queue_lambda.event_handlers.validate_software_stack_handler.sessions"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_events_queue_lambda.event_handlers.validate_software_stack_handler.ec2_utils"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_events_queue_lambda.event_handlers.validate_software_stack_handler.software_stacks"
)
def test_validate_handler_enables_stack_when_ami_available(
    mock_stacks, mock_ec2, mock_sessions
):
    """When AMI is available, stack is enabled."""
    mock_stacks.get_software_stack.return_value = {
        "ami_id": "ami-123",
        "stack_id": "ss1",
    }
    mock_ec2.describe_image_id.return_value = {"State": "available"}
    mock_sessions.get_session.return_value = {
        "idea_session_id": "s1",
        "owner": "u1",
        "server": {"locked": True},
    }
    event = {
        "Records": [
            _sqs_record(
                "msg-val",
                {
                    "event_type": "VALIDATE_SOFTWARE_STACK_CREATION_EVENT",
                    "detail": {
                        "software_stack_id": "ss1",
                        "base_os": "amazonlinux2",
                        "idea_session_id": "s1",
                        "idea_session_owner": "u1",
                        "instance_id": "i-1",
                    },
                },
            )
        ]
    }
    result = handler(event, None)
    assert result == {"batchItemFailures": []}
    mock_stacks.update_software_stack.assert_called_once()
    updated = mock_stacks.update_software_stack.call_args[1]["software_stack"]
    assert updated["enabled"] is True


@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_events_queue_lambda.event_handlers.validate_software_stack_handler.ec2_utils"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_events_queue_lambda.event_handlers.validate_software_stack_handler.software_stacks"
)
def test_validate_handler_retries_when_ami_not_ready(mock_stacks, mock_ec2):
    """When AMI is pending, message goes to batchItemFailures for redelivery."""
    mock_stacks.get_software_stack.return_value = {
        "ami_id": "ami-123",
        "stack_id": "ss1",
    }
    mock_ec2.describe_image_id.return_value = {"State": "pending"}
    event = {
        "Records": [
            _sqs_record(
                "msg-retry",
                {
                    "event_type": "VALIDATE_SOFTWARE_STACK_CREATION_EVENT",
                    "detail": {
                        "software_stack_id": "ss1",
                        "base_os": "amazonlinux2",
                        "idea_session_id": "s1",
                        "idea_session_owner": "u1",
                        "instance_id": "i-1",
                    },
                },
            )
        ]
    }
    result = handler(event, None)
    assert result == {"batchItemFailures": [{"itemIdentifier": "msg-retry"}]}


@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_events_queue_lambda.event_handlers.validate_software_stack_handler.ec2_utils"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_events_queue_lambda.event_handlers.validate_software_stack_handler.software_stacks"
)
def test_validate_handler_discards_when_stack_not_found(mock_stacks, mock_ec2):
    """When software stack no longer exists, message is discarded (not retried)."""
    from res.exceptions import SoftwareStackNotFound

    mock_stacks.get_software_stack.side_effect = SoftwareStackNotFound(
        "Software stack not found for base_os: windows, stack_id: ss-gone"
    )
    event = {
        "Records": [
            _sqs_record(
                "msg-gone",
                {
                    "event_type": "VALIDATE_SOFTWARE_STACK_CREATION_EVENT",
                    "detail": {
                        "software_stack_id": "ss-gone",
                        "base_os": "windows",
                        "idea_session_id": "s1",
                        "idea_session_owner": "u1",
                        "instance_id": "i-1",
                    },
                },
            )
        ]
    }
    result = handler(event, None)
    assert result == {"batchItemFailures": []}
    mock_ec2.describe_image_id.assert_not_called()


@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_events_queue_lambda.event_handlers.validate_software_stack_handler.ec2_utils"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_events_queue_lambda.event_handlers.validate_software_stack_handler.software_stacks"
)
def test_validate_handler_discards_terminal_ami_state(mock_stacks, mock_ec2):
    """When AMI is in a terminal failure state, message is discarded (not retried)."""
    mock_stacks.get_software_stack.return_value = {
        "ami_id": "ami-failed",
        "stack_id": "ss1",
    }
    mock_ec2.describe_image_id.return_value = {"State": "failed"}
    event = {
        "Records": [
            _sqs_record(
                "msg-terminal",
                {
                    "event_type": "VALIDATE_SOFTWARE_STACK_CREATION_EVENT",
                    "detail": {
                        "software_stack_id": "ss1",
                        "base_os": "amazonlinux2",
                        "idea_session_id": "s1",
                        "idea_session_owner": "u1",
                        "instance_id": "i-1",
                    },
                },
            )
        ]
    }
    result = handler(event, None)
    assert result == {"batchItemFailures": []}
    mock_stacks.update_software_stack.assert_not_called()


@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_events_queue_lambda.event_handlers.validate_software_stack_handler.ec2_utils"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_events_queue_lambda.event_handlers.validate_software_stack_handler.software_stacks"
)
def test_validate_handler_discards_deregistered_ami(mock_stacks, mock_ec2):
    """Deregistered AMI is a terminal state — message is discarded."""
    mock_stacks.get_software_stack.return_value = {
        "ami_id": "ami-dereg",
        "stack_id": "ss1",
    }
    mock_ec2.describe_image_id.return_value = {"State": "deregistered"}
    event = {
        "Records": [
            _sqs_record(
                "msg-dereg",
                {
                    "event_type": "VALIDATE_SOFTWARE_STACK_CREATION_EVENT",
                    "detail": {
                        "software_stack_id": "ss1",
                        "base_os": "windows",
                        "idea_session_id": "s1",
                        "idea_session_owner": "u1",
                        "instance_id": "i-1",
                    },
                },
            )
        ]
    }
    result = handler(event, None)
    assert result == {"batchItemFailures": []}
    mock_stacks.update_software_stack.assert_not_called()


@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_events_queue_lambda.event_handlers.ssm_commands_handler.vdi_management"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_events_queue_lambda.event_handlers.ssm_commands_handler.cluster_settings"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_events_queue_lambda.event_handlers.ssm_commands_handler.ssm_utils"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_events_queue_lambda.event_handlers.ssm_commands_handler.sessions"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_events_queue_lambda.event_handlers.ssm_commands_handler.ssm_commands"
)
def test_cpu_utilization_calls_get_command_invocation_with_correct_kwargs(
    mock_ssm_commands, mock_sessions, mock_ssm_utils, mock_cluster_settings, mock_vdi
):
    """get_command_invocation is called with snake_case kwargs (command_id, instance_id)."""
    mock_ssm_commands.get_ssm_command.return_value = {
        "command_type": "CPU_UTILIZATION_CHECK_STOP_SCHEDULED_SESSION",
        "additional_payload": {
            "idea_session_id": "s1",
            "idea_session_owner": "u1",
            "instance_id": "i-abc",
        },
    }
    mock_sessions.get_session.return_value = {
        "idea_session_id": "s1",
        "owner": "u1",
    }
    mock_ssm_utils.get_command_invocation.return_value = {
        "StandardOutputContent": json.dumps({"CPUAveragePerformanceLast10Secs": 5.0})
    }
    mock_cluster_settings.get_setting.return_value = "10.0"
    mock_vdi.stop_sessions.return_value = (["s1"], [])

    event = {
        "Records": [
            _sqs_record(
                "msg-cpu",
                {
                    "Type": "Notification",
                    "Message": json.dumps(
                        {"commandId": "cmd-cpu", "status": "Success"}
                    ),
                },
            )
        ]
    }
    result = handler(event, None)
    assert result == {"batchItemFailures": []}
    mock_ssm_utils.get_command_invocation.assert_called_once_with(
        command_id="cmd-cpu", instance_id="i-abc"
    )
