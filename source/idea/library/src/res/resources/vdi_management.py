#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Dict, List, Tuple

import boto3
import res.exceptions as exceptions
from res.clients.dcv_broker import dcv_broker_client
from res.clients.events import events_client
from res.resources import schedules
from res.resources import servers as server_db
from res.resources import session_permissions
from res.resources import sessions as user_sessions

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

SESSION_ID_KEY = "idea_session_id"


# Stop VDI logic
def stop_sessions(sessions: List[Dict[str, Any]]) -> Tuple[List, List]:
    """
    Stop sessions
    :param sessions: list of sessions to be stopped
    :returns successful and unsuccessul list of stopped sessions
    """
    vdi_with_no_dcv_session = []
    vdi_with_dcv_session = []
    success_response_list = []
    fail_response_list = []
    session_map: Dict[str, Any] = {}
    for curr_session in sessions:
        try:
            session = user_sessions.get_session(
                owner=curr_session["owner"],
                session_id=curr_session[SESSION_ID_KEY],
            )
        except exceptions.UserSessionNotFound as e:
            session = {}
            session["failure_reason"] = (
                f"Invalid RES Session ID: {curr_session[SESSION_ID_KEY]}:{curr_session['name']} for user: {curr_session['owner']}. Nothing to stop"
            )
            logger.error(session["failure_reason"])
            fail_response_list.append(session)
            continue

        session["is_idle"] = curr_session.get("is_idle", False)
        if session.get("state", "") != "READY":
            session["failure_reason"] = (
                f"RES Session ID: {session[SESSION_ID_KEY]}:{session['name']} for user: {session['owner']} is in {session['state']} state. Can't stop. Wait for it to be READY."
            )
            logger.error(session["failure_reason"])
            fail_response_list.append(session)
            continue

        if not session.get("dcv_session_id"):
            vdi_with_no_dcv_session.append(session)
        else:
            session["force"] = curr_session.get("force", False)
            vdi_with_dcv_session.append(session)
            session_map[session.get("dcv_session_id")] = session

    success_list, error_list = dcv_broker_client.delete_sessions(vdi_with_dcv_session)

    servers_to_stop = []
    servers_to_hibernate = []

    for dcv_session in success_list:
        session = session_map.get(dcv_session.get("dcv_session_id"))
        session["state"] = "STOPPING"
        session = user_sessions.update_session(session)
        events_client.publish_validate_dcv_session_deletion_event(
            session_id=session.get(SESSION_ID_KEY), owner=session.get("owner")
        )
        success_response_list.append(session)

    for session in vdi_with_no_dcv_session:
        session["server"]["is_idle"] = (
            session.get("is_idle") if session.get("is_idle") else False
        )
        if session.get("hibernation_enabled"):
            servers_to_hibernate.append(session.get("server"))
        else:
            servers_to_stop.append(session.get("server"))
        session["state"] = "STOPPING"
        session = user_sessions.update_session(session)
        success_response_list.append(session)

    for session in error_list:
        session_map.get(session.get("dcv_session_id"))["failure_reason"] = session.get(
            "failure_reason"
        )
        fail_response_list.append(session_map[session["dcv_session_id"]])

    session_id_names = [
        f"{session.get(SESSION_ID_KEY)}:{session.get('name')}"
        for session in vdi_with_no_dcv_session
    ]
    logger.info(f"Stopping session(s): {session_id_names}")

    stop_servers(servers_to_stop)
    hibernate_servers(servers_to_hibernate)
    return success_response_list, fail_response_list


def stop_servers(servers: List[Dict] = None) -> None:
    if not servers:
        logger.info("No servers provided to stop")
        return {}
    _stop_or_hibernate_servers(servers)


def hibernate_servers(servers: List[Dict] = None) -> None:
    if not servers:
        logger.info("No servers provided to hibernate...")
        return {}
    _stop_or_hibernate_servers(servers, True)


def _stop_or_hibernate_servers(servers, hibernate=False) -> None:
    response = _stop_hosts(servers=servers, hibernate=hibernate)
    instances = response.get("StoppingInstances", [])
    for instance in instances:
        instance_id = instance.get("InstanceId")
        server = server_db.get_server(instance_id=instance_id)
        if server.get("is_idle"):
            server["state"] = "STOPPED_IDLE"
        else:
            server["state"] = "HIBERNATED" if hibernate else "STOPPED"
        server_db.update_server(server)


def _stop_hosts(servers: List[Dict], hibernate=False) -> dict:
    if not servers:
        logger.info("No servers provided to _stop_hosts...")
        return {}

    instance_ids = [server["instance_id"] for server in servers]

    if hibernate:
        logger.info(f"Hibernating {instance_ids}")
    else:
        logger.info(f"Stopping {instance_ids}")

    ec2_client = boto3.client("ec2")
    response = ec2_client.stop_instances(InstanceIds=instance_ids, Hibernate=hibernate)
    return response


# Terminate VDI logic
def terminate_sessions(sessions: List[Dict[str, Any]]):
    """
    Terminates sessions
    :param sessions: list of sessions to be terminated
    :returns successful and unsuccessul list of terminated sessions
    """
    vdi_with_no_dcv_session = []
    vdi_with_dcv_session = []
    success_response_list = []
    fail_response_list = []
    session_map: Dict[str, Any] = {}

    for curr_session in sessions:
        try:
            session = user_sessions.get_session(
                owner=curr_session["owner"],
                session_id=curr_session[SESSION_ID_KEY],
            )
        except exceptions.UserSessionNotFound as e:
            session = {}
            session["failure_reason"] = (
                f"Invalid RES Session ID: {curr_session[SESSION_ID_KEY]}:{curr_session['name']} for user: {curr_session['owner']}.  Nothing to delete"
            )
            logger.error(session["failure_reason"])
            fail_response_list.append(session)
            continue

        session["force"] = curr_session.get("force", False)
        if session.get("state", "") in {"STOPPED", "STOPPED_IDLE"} or not session.get(
            user_sessions.SESSION_DB_DCV_SESSION_ID_KEY
        ):
            vdi_with_no_dcv_session.append(session)
            continue

        session_map[session["dcv_session_id"]] = session
        vdi_with_dcv_session.append(session)

    success_list, error_list = dcv_broker_client.delete_sessions(vdi_with_dcv_session)

    servers_to_delete = []
    session_db_entries_to_delete = []

    for dcv_session in success_list:
        session = session_map.get(dcv_session.get("dcv_session_id"))
        session["state"] = "DELETING"
        session = user_sessions.update_session(session)
        events_client.publish_validate_dcv_session_deletion_event(
            session_id=session.get(SESSION_ID_KEY), owner=session.get("owner")
        )
        success_response_list.append(session)

    for session in vdi_with_no_dcv_session:
        session_db_entries_to_delete.append(session)
        servers_to_delete.append(session.get("server"))

    terminate_servers(servers_to_delete)

    for session in session_db_entries_to_delete:
        delete_schedule_for_session(session)
        session_permissions.delete_session_permission_by_id(
            session_id=session[SESSION_ID_KEY]
        )
        user_sessions.delete_session(session)
        session["state"] = "DELETED"
        success_response_list.append(session)

    for session in error_list:
        session_map.get(session.get("dcv_session_id"))["failure_reason"] = session.get(
            "failure_reason"
        )
        fail_response_list.append(session_map[session["dcv_session_id"]])

    return success_response_list, fail_response_list


def terminate_servers(servers: List[Dict[str, Any]]) -> None:
    if not servers:
        logger.info("No servers provided to terminate")
        return {}

    response = _terminate_hosts(servers)

    instances = response.get("TerminatingInstances", [])
    for instance in instances:
        instance_id = instance.get("InstanceId")
        server_db.delete_server(instance_id=instance_id)

    return response


def _terminate_hosts(servers: List[Dict[str, Any]]) -> dict:
    ec2_client = boto3.client("ec2")

    instance_ids = [server["instance_id"] for server in servers]
    logger.info(f"Terminating {instance_ids}")

    response = ec2_client.terminate_instances(InstanceIds=instance_ids)
    return response


def delete_schedule_for_session(session: Dict[str, Any]) -> None:
    session_id = session.get(user_sessions.SESSION_DB_RANGE_KEY)
    owner = session.get(user_sessions.SESSION_DB_HASH_KEY)
    curr_session = user_sessions.get_session(owner=owner, session_id=session_id)

    for day in schedules.SCHEDULE_DAYS:
        key = f"{day}{user_sessions.SESSION_DB_SCHEDULE_SUFFIX}"
        schedule = curr_session.get(key)
        if schedule and schedule.get("schedule_id"):
            schedules.delete_schedule(schedule=schedule)
