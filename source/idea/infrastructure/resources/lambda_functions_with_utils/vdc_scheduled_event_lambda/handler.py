#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional, Tuple

from datamodel.models.backend.batch_start_session_request_content import (  # type: ignore
    BatchStartSessionRequestContent,
)
from datamodel.models.backend.day_of_week import DayOfWeek  # type: ignore
from datamodel.models.backend.update_session_permissions_request_content import (  # type: ignore
    UpdateSessionPermissionsRequestContent,
)
from datamodel.models.backend.virtual_desktop_session import (  # type: ignore
    VirtualDesktopSession,
)
from datamodel.models.backend.virtual_desktop_session_permission import (  # type: ignore
    VirtualDesktopSessionPermission,
)
from datamodel.models.backend.virtual_desktop_session_state import (  # type: ignore
    VirtualDesktopSessionState,
)
from res import exceptions as res_exceptions
from res.clients.api_client.res_api_client import ResApiClient  # type: ignore
from res.constants import (  # type: ignore
    CLUSTER_TIMEZONE_KEY,
    CUSTOM_DOMAIN_NAME_FOR_WEBAPP_KEY,
    ENFORCE_SCHEDULE_SETTING_KEY,
    ENVIRONMENT_NAME_KEY,
    EXTERNAL_ALB_DNS_NAME_KEY,
    MODULE_ID_VDC,
)
from res.resources import ssm_commands  # type: ignore
from res.resources import cluster_settings, schedules, session_permissions
from res.resources import sessions as res_sessions
from res.utils import aws_utils, logging_utils, time_utils  # type: ignore

logger = logging_utils.get_logger(__name__)

SCHEDULE_TRIGGER_WINDOW_MINUTES = 30

DAY_OF_WEEKS = [
    DayOfWeek.MONDAY,
    DayOfWeek.TUESDAY,
    DayOfWeek.WEDNESDAY,
    DayOfWeek.THURSDAY,
    DayOfWeek.FRIDAY,
    DayOfWeek.SATURDAY,
    DayOfWeek.SUNDAY,
]

NON_RESUMABLE_STATES = {
    VirtualDesktopSessionState.STOPPING.value,
    VirtualDesktopSessionState.PROVISIONING.value,
    VirtualDesktopSessionState.CREATING.value,
    VirtualDesktopSessionState.RESUMING.value,
    VirtualDesktopSessionState.READY.value,
    VirtualDesktopSessionState.INITIALIZING.value,
    VirtualDesktopSessionState.DELETED.value,
    VirtualDesktopSessionState.DELETING.value,
}

_res_api_client: Optional[ResApiClient] = None


def handler(event: Dict[str, Any], context: Any) -> None:
    """
    EventBridge-triggered Lambda that resumes or stops VDI sessions whose schedule fires this tick.
    """
    try:
        detail_type = event.get("detail-type", "")
        if detail_type != "Scheduled Event":
            logger.warning(f"Unexpected detail-type: {detail_type}. Discarding.")
            return

        event_time = event.get("time", "")
        if not event_time:
            logger.error(f"event time is {event_time}. Invalid message. Returning.")
            return

        cluster_tz = (
            cluster_settings.get_setting(CLUSTER_TIMEZONE_KEY) or "America/Los_Angeles"
        )
        event_time = time_utils.to_datetime_in_timezone(event_time, cluster_tz)
        logger.info(f"Handling scheduled event at time {event_time} in {cluster_tz}")

        day_of_week = DAY_OF_WEEKS[event_time.weekday()]
        schedule_db_entries = schedules.get_schedules_for_day_of_week(day_of_week)

        res_api_client = _get_res_api_client()

        to_resume, to_stop = _trigger_schedule(schedule_db_entries, event_time)
        if to_resume:
            _resume_sessions(to_resume, res_api_client)
        if to_stop:
            _submit_cpu_check_for_sessions(to_stop)
        if not to_resume and not to_stop:
            logger.info("No sessions due to resume or stop in this trigger window.")

        _sweep_expired_permissions(event_time, res_api_client)
    except Exception as e:
        logger.exception(f"error in handling scheduled event: {event}, error: {e}")


def _resolve_external_endpoint() -> str:
    dns_name = cluster_settings.get_setting(
        CUSTOM_DOMAIN_NAME_FOR_WEBAPP_KEY
    ) or cluster_settings.get_setting(EXTERNAL_ALB_DNS_NAME_KEY)
    if not dns_name:
        raise RuntimeError("Cluster external endpoint not found in cluster settings.")
    return f"https://{dns_name}"


def _build_res_api_client() -> ResApiClient:
    client_id = aws_utils.get_secret_string(
        cluster_settings.get_setting(f"{MODULE_ID_VDC}.client_id")
    )
    client_secret = aws_utils.get_secret_string(
        cluster_settings.get_setting(f"{MODULE_ID_VDC}.client_secret")
    )
    cluster_name = os.environ[ENVIRONMENT_NAME_KEY]
    return ResApiClient(
        endpoint=_resolve_external_endpoint(),
        client_id=client_id,
        client_secret=client_secret,
        scopes=[f"{cluster_name}-{MODULE_ID_VDC}/write"],
    )


def _get_res_api_client() -> ResApiClient:
    global _res_api_client
    if _res_api_client is None:
        _res_api_client = _build_res_api_client()
    return _res_api_client


def _should_resume(event_time: time, start_up_time: time, shut_down_time: time) -> bool:
    today = date.today()
    event_dt = datetime.combine(today, event_time)
    start_dt = datetime.combine(today, start_up_time)
    shut_down_dt = datetime.combine(today, shut_down_time)
    start_dt_with_delta = start_dt + timedelta(minutes=SCHEDULE_TRIGGER_WINDOW_MINUTES)

    return (
        event_dt >= start_dt
        and event_dt < shut_down_dt
        and event_dt < start_dt_with_delta
    )


def _should_stop(event_time: time, shut_down_time: time) -> bool:
    today = date.today()
    event_dt = datetime.combine(today, event_time)
    shut_down_dt = datetime.combine(today, shut_down_time)
    shut_down_dt_with_delta = shut_down_dt + timedelta(
        minutes=SCHEDULE_TRIGGER_WINDOW_MINUTES
    )

    return event_dt >= shut_down_dt and event_dt < shut_down_dt_with_delta


def _trigger_schedule(
    schedule_db_entries: List[Dict[str, Any]], event_time: datetime
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    is_schedule_enforced = bool(
        cluster_settings.get_setting(ENFORCE_SCHEDULE_SETTING_KEY)
    )
    to_resume: List[Dict[str, Any]] = []
    to_stop: List[Dict[str, Any]] = []

    for schedule_db_entry in schedule_db_entries:
        idea_session_id = schedule_db_entry.get(schedules.SCHEDULE_DB_SESSION_ID_KEY)
        idea_session_owner = schedule_db_entry.get(
            schedules.SCHEDULE_DB_SESSION_OWNER_KEY
        )
        if not idea_session_id or not idea_session_owner:
            continue

        logger.info(
            f"Triggering schedule {schedule_db_entry.get(schedules.SCHEDULE_DB_RANGE_KEY)}"
        )

        start_up_time = schedule_db_entry.get(
            schedules.SCHEDULE_DB_START_UP_TIME_KEY, ""
        ).split(":")
        shut_down_time = schedule_db_entry.get(
            schedules.SCHEDULE_DB_SHUT_DOWN_TIME_KEY, ""
        ).split(":")
        if len(start_up_time) < 2 or len(shut_down_time) < 2:
            continue
        start_up_time = time(int(start_up_time[0]), int(start_up_time[1]))
        shut_down_time = time(int(shut_down_time[0]), int(shut_down_time[1]))

        if _should_resume(event_time.time(), start_up_time, shut_down_time):
            logger.info(
                f"handle event to resume RES Session ID: {idea_session_id} for owner: {idea_session_owner}"
            )
            try:
                session = res_sessions.get_session(idea_session_owner, idea_session_id)
            except res_exceptions.UserSessionNotFound:
                logger.error(
                    f"Trying to resume Invalid RES Session with RES Session ID: "
                    f"{idea_session_id} and owner: {idea_session_owner}. No OP. Returning."
                )
                continue
            except Exception:
                logger.exception(
                    f"Failed to look up RES Session ID: {idea_session_id}, owner: "
                    f"{idea_session_owner}. Skipping."
                )
                continue

            state = session.get(res_sessions.SESSION_DB_STATE_KEY)
            if state in NON_RESUMABLE_STATES:
                logger.info(f"Session in state {state}. No OP. Returning.")
                continue

            if (
                state == VirtualDesktopSessionState.STOPPED_IDLE.value
                and not is_schedule_enforced
            ):
                logger.info(
                    "session in STOPPED_IDLE state and schedule enforcement is disabled. "
                    "No OP. Returning."
                )
                continue

            to_resume.append(session)
        elif _should_stop(event_time.time(), shut_down_time):
            logger.info(
                f"handle stop RES Session ID: {idea_session_id} for owner: {idea_session_owner}"
            )
            try:
                session = res_sessions.get_session(idea_session_owner, idea_session_id)
            except res_exceptions.UserSessionNotFound:
                logger.error(
                    f"Trying to stop Invalid RES Session ID: {idea_session_id} and "
                    f"owner: {idea_session_owner}. No OP. Returning."
                )
                continue
            except Exception:
                logger.exception(
                    f"Failed to look up RES Session ID: {idea_session_id}, owner: "
                    f"{idea_session_owner}. Skipping."
                )
                continue

            state = session.get(res_sessions.SESSION_DB_STATE_KEY)
            if state != VirtualDesktopSessionState.READY.value:
                logger.info(f"Session in state {state}. No OP. Returning.")
                continue

            to_stop.append(session)

    return to_resume, to_stop


def _resume_sessions(
    to_resume: List[Dict[str, Any]], res_api_client: ResApiClient
) -> None:
    sessions = [
        VirtualDesktopSession(
            idea_session_id=session[res_sessions.SESSION_DB_RANGE_KEY],
            owner=session[res_sessions.SESSION_DB_HASH_KEY],
        )
        for session in to_resume
    ]
    logger.info(f"Calling BatchStartSession for {len(sessions)} session(s).")
    response = res_api_client.batch_start_session(
        BatchStartSessionRequestContent(sessions=sessions)
    )
    for failure in response.unsuccessful_list:
        logger.error(
            f"Error in resuming RES Session ID: "
            f"{failure.session.idea_session_id}:{failure.session.name}. "
            f"Error: {failure.message}"
        )


def _sweep_expired_permissions(
    event_time: datetime, res_api_client: ResApiClient
) -> None:
    """Send expired session permissions to the backend as a delete batch."""
    event_time_ms = int(event_time.timestamp() * 1000)
    expired_permissions: List[Dict[str, Any]] = []
    next_token: Optional[str] = None
    while True:
        permissions, next_token = (
            session_permissions.list_session_permissions_paginated(
                next_token=next_token
            )
        )
        for permission in permissions:
            expiry_ms = permission.get("expiry_date")
            if expiry_ms and event_time_ms >= expiry_ms:
                expired_permissions.append(permission)
        if not next_token:
            break

    if not expired_permissions:
        return

    logger.info(
        f"Found {len(expired_permissions)} expired session permission(s). "
        f"Calling update_session_permissions to delete."
    )
    delete_payload = [
        VirtualDesktopSessionPermission.from_ddb_dict(permission)
        for permission in expired_permissions
    ]
    res_api_client.update_session_permissions(
        UpdateSessionPermissionsRequestContent(delete=delete_payload)
    )


def _submit_cpu_check_for_sessions(to_stop: List[Dict[str, Any]]) -> None:
    logger.info(f"Submitting CPU utilization check for {len(to_stop)} session(s).")
    for session in to_stop:
        try:
            ssm_commands.submit_ssm_command_to_get_cpu_utilization(
                instance_id=session[res_sessions.SESSION_DB_SERVER_KEY][
                    res_sessions.SESSION_DB_SERVER_NESTED_INSTANCE_ID_KEY
                ],
                idea_session_id=session[res_sessions.SESSION_DB_RANGE_KEY],
                idea_session_owner=session[res_sessions.SESSION_DB_HASH_KEY],
                base_os=session[res_sessions.SESSION_DB_BASE_OS_KEY],
            )
        except Exception:
            logger.exception(
                f"Failed to submit CPU check for RES Session ID: "
                f"{session.get(res_sessions.SESSION_DB_RANGE_KEY)}. Skipping."
            )
