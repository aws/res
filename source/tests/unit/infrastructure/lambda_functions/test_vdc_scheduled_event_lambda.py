#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from datetime import time
from unittest.mock import MagicMock, patch

import pytest

from idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler import (
    _should_resume,
    _should_stop,
    handler,
)


@pytest.fixture(autouse=True)
def _no_op_permission_sweep():
    """Default permission-expiry sweep to a no-op so handler-level tests don't hit DDB."""
    with patch(
        "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.session_permissions.list_session_permissions_paginated",
        return_value=([], None),
    ):
        yield


# --- pure-logic tests ------------------------------------------------------


def test_should_resume_inside_window():
    # start=09:00, event=09:15, end=17:00 — inside [09:00, 09:30) and before 17:00
    assert _should_resume(time(9, 15), time(9, 0), time(17, 0)) is True


def test_should_resume_at_start_boundary_inclusive():
    assert _should_resume(time(9, 0), time(9, 0), time(17, 0)) is True


def test_should_resume_outside_30min_window():
    # 30 minutes past start-up is exclusive: 09:30 is NOT in the window
    assert _should_resume(time(9, 30), time(9, 0), time(17, 0)) is False


def test_should_resume_after_shutdown_returns_false():
    assert _should_resume(time(18, 0), time(9, 0), time(17, 0)) is False


def test_should_resume_window_late_night_no_midnight_wraparound():
    # start=23:45, event=23:50, end=23:59 — inside [23:45, 00:15) without wrapping.
    assert _should_resume(time(23, 50), time(23, 45), time(23, 59)) is True


def test_should_stop_inside_window():
    # end=17:00, event=17:15 — inside [17:00, 17:30).
    assert _should_stop(time(17, 15), time(17, 0)) is True


def test_should_stop_at_shutdown_boundary_inclusive():
    assert _should_stop(time(17, 0), time(17, 0)) is True


def test_should_stop_outside_30min_window():
    # 30 minutes past shutdown is exclusive.
    assert _should_stop(time(17, 30), time(17, 0)) is False


def test_should_stop_before_shutdown_returns_false():
    assert _should_stop(time(9, 0), time(17, 0)) is False


# --- handler tests --------------------------------------------------------


def _setting_lookup(enforce_schedule=True, timezone="UTC"):
    """Build a side_effect for cluster_settings.get_setting."""

    def get(key):
        return {
            "cluster.timezone": timezone,
            "vdc.dcv_session.enforce_schedule": enforce_schedule,
        }.get(key)

    return get


@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler._get_res_api_client"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.res_sessions.get_session"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.schedules.get_schedules_for_day_of_week"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.cluster_settings.get_setting"
)
def test_handler_calls_batch_start_for_due_sessions(
    mock_cluster_settings, mock_schedules, mock_res_sessions, mock_get_client
):
    mock_cluster_settings.side_effect = _setting_lookup()
    mock_schedules.return_value = [
        {
            "schedule_id": "sched-1",
            "idea_session_id": "s-1",
            "idea_session_owner": "user1",
            "start_up_time": "09:00",
            "shut_down_time": "17:00",
        },
        {
            "schedule_id": "sched-2",
            "idea_session_id": "s-2",
            "idea_session_owner": "user2",
            "start_up_time": "13:00",  # outside the 09:15 window
            "shut_down_time": "17:00",
        },
    ]
    mock_res_sessions.return_value = {
        "idea_session_id": "s-1",
        "owner": "user1",
        "state": "STOPPED",
    }

    api_client = MagicMock()
    api_client.batch_start_session.return_value = MagicMock(unsuccessful_list=[])
    mock_get_client.return_value = api_client

    # 2026-06-22 is a Monday; 09:15 UTC falls into the 09:00 window
    event = {"detail-type": "Scheduled Event", "time": "2026-06-22T09:15:00Z"}

    handler(event, None)

    api_client.batch_start_session.assert_called_once()
    request = api_client.batch_start_session.call_args[0][0]
    assert len(request.sessions) == 1
    assert request.sessions[0].idea_session_id == "s-1"
    assert request.sessions[0].owner == "user1"


@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler._get_res_api_client"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.res_sessions.get_session"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.schedules.get_schedules_for_day_of_week"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.cluster_settings.get_setting"
)
def test_handler_no_op_when_nothing_due(
    mock_cluster_settings, mock_schedules, mock_res_sessions, mock_get_client
):
    mock_cluster_settings.side_effect = _setting_lookup()
    mock_schedules.return_value = [
        {
            "schedule_id": "sched-x",
            "idea_session_id": "s-x",
            "idea_session_owner": "user",
            "start_up_time": "13:00",
            "shut_down_time": "17:00",
        }
    ]
    api_client = MagicMock()
    mock_get_client.return_value = api_client

    handler({"detail-type": "Scheduled Event", "time": "2026-06-22T09:15:00Z"}, None)

    api_client.batch_start_session.assert_not_called()
    mock_res_sessions.assert_not_called()


@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler._get_res_api_client"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.res_sessions.get_session"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.schedules.get_schedules_for_day_of_week"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.cluster_settings.get_setting"
)
def test_handler_skips_non_resumable_states(
    mock_cluster_settings, mock_schedules, mock_res_sessions, mock_get_client
):
    mock_cluster_settings.side_effect = _setting_lookup()
    mock_schedules.return_value = [
        {
            "schedule_id": "sched-1",
            "idea_session_id": "s-ready",
            "idea_session_owner": "user1",
            "start_up_time": "09:00",
            "shut_down_time": "17:00",
        },
    ]
    mock_res_sessions.return_value = {"state": "READY"}

    api_client = MagicMock()
    mock_get_client.return_value = api_client

    handler({"detail-type": "Scheduled Event", "time": "2026-06-22T09:15:00Z"}, None)
    api_client.batch_start_session.assert_not_called()


@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler._get_res_api_client"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.res_sessions.get_session"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.schedules.get_schedules_for_day_of_week"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.cluster_settings.get_setting"
)
def test_handler_skips_stopped_idle_when_enforcement_disabled(
    mock_cluster_settings, mock_schedules, mock_res_sessions, mock_get_client
):
    mock_cluster_settings.side_effect = _setting_lookup(enforce_schedule=False)
    mock_schedules.return_value = [
        {
            "schedule_id": "sched-1",
            "idea_session_id": "s-stopped",
            "idea_session_owner": "user1",
            "start_up_time": "09:00",
            "shut_down_time": "17:00",
        },
        {
            "schedule_id": "sched-2",
            "idea_session_id": "s-idle",
            "idea_session_owner": "user2",
            "start_up_time": "09:00",
            "shut_down_time": "17:00",
        },
    ]
    mock_res_sessions.side_effect = lambda owner, sid: {
        "s-stopped": {
            "idea_session_id": "s-stopped",
            "owner": "user1",
            "state": "STOPPED",
        },
        "s-idle": {
            "idea_session_id": "s-idle",
            "owner": "user2",
            "state": "STOPPED_IDLE",
        },
    }[sid]

    api_client = MagicMock()
    api_client.batch_start_session.return_value = MagicMock(unsuccessful_list=[])
    mock_get_client.return_value = api_client

    handler({"detail-type": "Scheduled Event", "time": "2026-06-22T09:15:00Z"}, None)

    request = api_client.batch_start_session.call_args[0][0]
    assert len(request.sessions) == 1
    assert request.sessions[0].idea_session_id == "s-stopped"


@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler._get_res_api_client"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.res_sessions.get_session"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.schedules.get_schedules_for_day_of_week"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.cluster_settings.get_setting"
)
def test_handler_resumes_stopped_idle_when_enforcement_enabled(
    mock_cluster_settings, mock_schedules, mock_res_sessions, mock_get_client
):
    mock_cluster_settings.side_effect = _setting_lookup(enforce_schedule=True)
    mock_schedules.return_value = [
        {
            "schedule_id": "sched-1",
            "idea_session_id": "s-idle",
            "idea_session_owner": "user1",
            "start_up_time": "09:00",
            "shut_down_time": "17:00",
        },
    ]
    mock_res_sessions.return_value = {
        "idea_session_id": "s-idle",
        "owner": "user1",
        "state": "STOPPED_IDLE",
    }

    api_client = MagicMock()
    api_client.batch_start_session.return_value = MagicMock(unsuccessful_list=[])
    mock_get_client.return_value = api_client

    handler({"detail-type": "Scheduled Event", "time": "2026-06-22T09:15:00Z"}, None)

    request = api_client.batch_start_session.call_args[0][0]
    assert len(request.sessions) == 1
    assert request.sessions[0].idea_session_id == "s-idle"


@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.ssm_commands"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler._get_res_api_client"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.res_sessions.get_session"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.schedules.get_schedules_for_day_of_week"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.cluster_settings.get_setting"
)
def test_handler_submits_cpu_check_for_due_stop_sessions(
    mock_cluster_settings,
    mock_schedules,
    mock_res_sessions,
    mock_get_client,
    mock_ssm_commands,
):
    """Scheduled stop submits an SSM CPU check (does NOT directly stop) — mirrors legacy."""
    mock_cluster_settings.side_effect = _setting_lookup()
    mock_schedules.return_value = [
        {
            "schedule_id": "sched-1",
            "idea_session_id": "s-1",
            "idea_session_owner": "user1",
            "start_up_time": "09:00",
            "shut_down_time": "17:00",
        },
    ]
    mock_res_sessions.return_value = {
        "idea_session_id": "s-1",
        "owner": "user1",
        "state": "READY",
        "base_os": "amazonlinux2",
        "server": {"instance_id": "i-abc123"},
    }

    api_client = MagicMock()
    mock_get_client.return_value = api_client

    # 2026-06-22 is a Monday; 17:15 UTC falls into the 17:00 shutdown window.
    event = {"detail-type": "Scheduled Event", "time": "2026-06-22T17:15:00Z"}

    handler(event, None)

    api_client.batch_start_session.assert_not_called()
    mock_ssm_commands.submit_ssm_command_to_get_cpu_utilization.assert_called_once_with(
        instance_id="i-abc123",
        idea_session_id="s-1",
        idea_session_owner="user1",
        base_os="amazonlinux2",
    )


@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.ssm_commands"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler._get_res_api_client"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.res_sessions.get_session"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.schedules.get_schedules_for_day_of_week"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.cluster_settings.get_setting"
)
def test_handler_stop_skips_non_ready_state(
    mock_cluster_settings,
    mock_schedules,
    mock_res_sessions,
    mock_get_client,
    mock_ssm_commands,
):
    """Legacy stop handler only stops READY sessions; STOPPED/STOPPED_IDLE are no-op."""
    mock_cluster_settings.side_effect = _setting_lookup()
    mock_schedules.return_value = [
        {
            "schedule_id": "sched-1",
            "idea_session_id": "s-stopped",
            "idea_session_owner": "user1",
            "start_up_time": "09:00",
            "shut_down_time": "17:00",
        },
    ]
    mock_res_sessions.return_value = {"state": "STOPPED"}

    api_client = MagicMock()
    mock_get_client.return_value = api_client

    handler({"detail-type": "Scheduled Event", "time": "2026-06-22T17:15:00Z"}, None)

    mock_ssm_commands.submit_ssm_command_to_get_cpu_utilization.assert_not_called()


@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.VirtualDesktopSessionPermission.from_ddb_dict"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.session_permissions.list_session_permissions_paginated"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler._get_res_api_client"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.schedules.get_schedules_for_day_of_week"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.cluster_settings.get_setting"
)
def test_handler_calls_backend_update_session_permissions_for_expired(
    mock_cluster_settings,
    mock_schedules,
    mock_get_client,
    mock_list_perms,
    mock_from_ddb_dict,
):
    mock_cluster_settings.side_effect = _setting_lookup()
    mock_schedules.return_value = []
    api_client = MagicMock()
    mock_get_client.return_value = api_client

    fresh_perm = {
        "idea_session_id": "ses-fresh",
        "idea_session_owner": "alice",
        "actor_name": "bob",
        "expiry_date": 1_999_999_999_999,
    }
    expired_perm = {
        "idea_session_id": "ses-expired",
        "idea_session_owner": "carol",
        "actor_name": "dave",
        "expiry_date": 1_000_000_000_000,
    }
    mock_list_perms.return_value = ([fresh_perm, expired_perm], None)
    mock_from_ddb_dict.side_effect = lambda p: MagicMock(
        idea_session_id=p["idea_session_id"],
        idea_session_owner=p["idea_session_owner"],
        actor_name=p["actor_name"],
    )

    handler({"detail-type": "Scheduled Event", "time": "2026-06-22T17:15:00Z"}, None)

    api_client.update_session_permissions.assert_called_once()
    request = api_client.update_session_permissions.call_args[0][0]
    assert len(request.delete) == 1
    assert request.delete[0].idea_session_id == "ses-expired"
    assert request.delete[0].idea_session_owner == "carol"
    assert request.delete[0].actor_name == "dave"
    mock_from_ddb_dict.assert_called_once_with(expired_perm)


@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.session_permissions.list_session_permissions_paginated"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler._get_res_api_client"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.schedules.get_schedules_for_day_of_week"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.cluster_settings.get_setting"
)
def test_handler_no_op_when_no_expired_permissions(
    mock_cluster_settings,
    mock_schedules,
    mock_get_client,
    mock_list_perms,
):
    mock_cluster_settings.side_effect = _setting_lookup()
    mock_schedules.return_value = []
    api_client = MagicMock()
    mock_get_client.return_value = api_client
    mock_list_perms.return_value = ([], None)

    handler({"detail-type": "Scheduled Event", "time": "2026-06-22T17:15:00Z"}, None)

    api_client.update_session_permissions.assert_not_called()


@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler._get_res_api_client"
)
def test_handler_ignores_non_scheduled_event(mock_get_client):
    handler({"detail-type": "Other Event"}, None)
    mock_get_client.assert_not_called()


def test_handler_skips_when_event_time_missing():
    # No mocks needed — the handler returns before touching anything.
    handler({"detail-type": "Scheduled Event"}, None)


@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler._get_res_api_client"
)
@patch(
    "idea.infrastructure.resources.lambda_functions_with_utils.vdc_scheduled_event_lambda.handler.logger"
)
def test_handler_swallows_exception(mock_logger, mock_get_client):
    mock_get_client.side_effect = RuntimeError("boom")
    handler({"detail-type": "Scheduled Event", "time": "2026-06-22T09:15:00Z"}, None)
    mock_logger.exception.assert_called_once()
