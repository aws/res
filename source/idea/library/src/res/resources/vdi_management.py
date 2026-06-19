#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import random
from typing import Any, Dict, List, Tuple

import res.exceptions as exceptions
from res.clients.aws.aws_provider import AwsClientProvider
from res.clients.dcv_session_manager import dcv_session_manager_client
from res.clients.events import events_client
from res.resources import ad_automation, schedules, session_permissions
from res.resources import sessions as user_sessions
from res.utils import logging_utils

SESSION_ID_KEY = "idea_session_id"

logger = logging_utils.get_logger("vdi-management")


# Stop VDI logic
def stop_sessions(sessions: List[Dict[str, Any]]) -> Tuple[List, List]:
    """
    Stop sessions
    :param sessions: list of sessions to be stopped
    :returns successful and unsuccessful list of stopped sessions
    """
    validate_sessions_to_delete(sessions, True)

    servers_to_stop = []
    servers_to_hibernate = []
    success_response_list = []
    fail_response_list = []
    for session in sessions:
        if session.get("failure_reason"):
            logger.error(f'{session[SESSION_ID_KEY]}: {session["failure_reason"]}')
            fail_response_list.append(session)
            continue

        if session.get("hibernation_enabled"):
            servers_to_hibernate.append(session.get("server"))
        else:
            servers_to_stop.append(session.get("server"))
        session["state"] = "STOPPING"
        session = user_sessions.update_session(session)
        success_response_list.append(session)

    logger.info(f"Stopping session(s)")
    stop_servers(servers_to_stop)
    hibernate_servers(servers_to_hibernate)
    return success_response_list, fail_response_list


def reboot_sessions(sessions: List[Dict[str, Any]]) -> Tuple[List, List]:
    """
    Reboot EC2 instances for validated sessions and update state to RESUMING.
    Assumes sessions have already been validated (exists, correct state, connections checked).
    :param sessions: list of validated session dicts (from DDB)
    :returns (successful_list, unsuccessful_list)
    """
    instance_ids = [
        session.get("server", {}).get("instance_id") for session in sessions
    ]

    ec2_client = AwsClientProvider().ec2()
    ec2_client.reboot_instances(InstanceIds=instance_ids)

    success_response_list = []
    fail_response_list = []
    for session in sessions:
        try:
            updated = user_sessions.update_session_state(
                session["owner"], session[SESSION_ID_KEY], "RESUMING"
            )
            success_response_list.append(updated)
        except Exception as e:
            logger.error(
                f"Failed to update session state for {session[SESSION_ID_KEY]}: {e}"
            )
            session["failure_reason"] = f"State update failed: {e}"
            session["failure_code"] = exceptions.FAILURE_CODE_INTERNAL_SERVICE
            fail_response_list.append(session)

    return success_response_list, fail_response_list


def validate_sessions_to_delete(
    sessions: List[Dict[str, Any]],
    check_ready_state: bool = False,
) -> None:
    sessions_to_check = []
    for i, session in enumerate(sessions):
        try:
            existing_session = user_sessions.get_session(
                owner=session["owner"],
                session_id=session[SESSION_ID_KEY],
            )
            session = {
                **existing_session,
                "is_idle": session.get("is_idle", False),
                "force": session.get("force", False),
            }
            sessions[i] = session

        except exceptions.UserSessionNotFound:
            session["failure_reason"] = (
                f"Invalid RES Session ID: {session[SESSION_ID_KEY]}:{session['name']} for user: {session['owner']}.  Nothing to delete"
            )
            session["failure_code"] = exceptions.FAILURE_CODE_NOT_FOUND
            continue

        if check_ready_state and session.get("state", "") != "READY":
            session["failure_reason"] = (
                f"RES Session ID: {session[SESSION_ID_KEY]}:{session['name']} for user: {session['owner']} is in {session['state']} state. Can't stop. Wait for it to be READY."
            )
            session["failure_code"] = exceptions.FAILURE_CODE_BAD_REQUEST
            continue
        if session.get("state", "") in {"STOPPED", "STOPPED_IDLE"}:
            continue

        if not session.get(user_sessions.SESSION_DB_DCV_SESSION_ID_KEY):
            session["server"]["is_idle"] = (
                session.get("is_idle") if session.get("is_idle") else False
            )
            continue

        if not session.get("force"):
            sessions_to_check.append(session)

    sessions_with_count = get_active_counts_for_sessions(sessions_to_check)

    for session in sessions_with_count:
        if session.get("connection_count", 0) > 0:
            logger.info(
                f"Session {session.get('idea_session_id')}:{session.get('name')} has {session.get('connection_count')} active connection(s)"
            )
            session["failure_reason"] = (
                f"There exists {session.get('connection_count')} active connection(s)for session_id: {session.get('idea_session_id')}:{session.get('name')}. Please terminate."
            )
            session["failure_code"] = exceptions.FAILURE_CODE_CONFLICT


def get_active_counts_for_sessions(
    sessions: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Populate ``connection_count`` on each session via the DCV Session Management Lambda.

    Sessions that fail to describe (e.g. host unreachable) keep ``connection_count = 0``.
    """
    if not sessions:
        return []

    response = dcv_session_manager_client.describe_sessions(
        [{"session_id": s[SESSION_ID_KEY], "owner": s["owner"]} for s in sessions]
    )
    counts = {
        entry["session_id"]: entry.get("num_of_connections", 0)
        for entry in response.get("successful_list", [])
    }
    for entry in response.get("unsuccessful_list", []):
        logger.warning(
            "Failed to describe session %s: %s. Treating as 0 connections.",
            entry.get("session_id"),
            entry.get("failure_reason"),
        )

    for session in sessions:
        session["connection_count"] = counts.get(session[SESSION_ID_KEY], 0)

    return sessions


def stop_servers(servers: List[Dict] = None) -> None:
    if not servers:
        logger.info("No servers provided to stop")
        return
    _stop_or_hibernate_servers(servers)


def hibernate_servers(servers: List[Dict] = None) -> None:
    if not servers:
        logger.info("No servers provided to hibernate...")
        return
    _stop_or_hibernate_servers(servers, True)


def _stop_or_hibernate_servers(servers, hibernate=False) -> None:
    _stop_hosts(servers=servers, hibernate=hibernate)


def _stop_hosts(servers: List[Dict], hibernate=False) -> dict:
    if not servers:
        logger.info("No servers provided to _stop_hosts...")
        return {}

    instance_ids = [server["instance_id"] for server in servers]

    if hibernate:
        logger.info(f"Hibernating {instance_ids}")
    else:
        logger.info(f"Stopping {instance_ids}")

    ec2_client = AwsClientProvider().ec2()
    response = ec2_client.stop_instances(InstanceIds=instance_ids, Hibernate=hibernate)
    return response


# Terminate VDI logic
def terminate_sessions(sessions: List[Dict[str, Any]]):
    """
    Terminates sessions
    :param sessions: list of sessions to be terminated
    :returns successful and unsuccessful list of terminated sessions
    """
    validate_sessions_to_delete(sessions)

    servers_to_delete = []
    success_response_list = []
    fail_response_list = []
    for session in sessions:
        if session.get("failure_reason"):
            logger.error(f'{session[SESSION_ID_KEY]}: {session["failure_reason"]}')
            fail_response_list.append(session)
            continue

        session["state"] = "DELETING"
        session = user_sessions.update_session(session)

        delete_schedule_for_session(session=session)
        session_permissions.delete_session_permission_by_id(
            session_id=session[SESSION_ID_KEY]
        )
        user_sessions.delete_session(session=session)
        session["state"] = "DELETED"
        servers_to_delete.append(session.get("server"))

        success_response_list.append(session)

    terminate_servers(servers_to_delete)

    ad_automation.remove_ad_authorization(
        [server["instance_id"] for server in servers_to_delete]
    )

    return success_response_list, fail_response_list


def terminate_servers(servers: List[Dict[str, Any]]) -> None:
    if not servers:
        logger.info("No servers provided to terminate")
        return

    _terminate_hosts(servers)


def _terminate_hosts(servers: List[Dict[str, Any]]) -> dict:
    ec2_client = AwsClientProvider().ec2()

    instance_ids = [server["instance_id"] for server in servers]
    logger.info(f"Terminating {instance_ids}")

    response = ec2_client.terminate_instances(InstanceIds=instance_ids)
    return response


def delete_schedule_for_session(session: Dict[str, Any]) -> None:
    session_id = session.get(user_sessions.SESSION_DB_RANGE_KEY)
    owner = session.get(user_sessions.SESSION_DB_HASH_KEY)
    curr_session = user_sessions.get_session(owner=owner, session_id=session_id)

    for day in schedules.DayOfWeek:
        key = f"{day.value}{user_sessions.SESSION_DB_SCHEDULE_SUFFIX}"
        schedule = curr_session.get(key)
        if schedule and schedule.get("schedule_id"):
            schedules.delete_schedule(schedule=schedule)


# Start VDI logic
def start_sessions(sessions: List[Dict[str, Any]]) -> Tuple[List, List]:
    """
    Start sessions by calling EC2 start_instances and updating session state.
    Only updates state for instances that actually transitioned from stopped.
    :param sessions: list of validated sessions to be started (DDB dicts)
    :returns (successful list, unsuccessful list)
    """
    servers_to_start = [session.get("server") for session in sessions]
    response = _start_hosts(servers_to_start)

    started_ids = set()
    for instance in response.get("StartingInstances", []):
        if instance.get("CurrentState", {}).get("Name") in ("pending", "running"):
            started_ids.add(instance["InstanceId"])

    success_response_list = []
    fail_response_list = []
    for session in sessions:
        instance_id = session.get("server", {}).get("instance_id")
        if instance_id in started_ids:
            updated = user_sessions.update_session_state(
                owner=session["owner"],
                session_id=session[SESSION_ID_KEY],
                state="RESUMING",
            )
            success_response_list.append(updated)
        else:
            session["failure_reason"] = f"EC2 instance {instance_id} failed to start"
            session["failure_code"] = exceptions.FAILURE_CODE_INTERNAL_SERVICE
            fail_response_list.append(session)

    return success_response_list, fail_response_list


def _start_hosts(servers: List[Dict]) -> dict:
    if not servers:
        logger.info("No servers provided to start")
        return {}

    instance_ids = [server["instance_id"] for server in servers]
    logger.info(f"Starting {instance_ids}")

    ec2_client = AwsClientProvider().ec2()
    response = ec2_client.start_instances(InstanceIds=instance_ids)
    return response
