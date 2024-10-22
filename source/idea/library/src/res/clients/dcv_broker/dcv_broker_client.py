#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Dict, List, Tuple

from res.clients import dcv_swagger_client
from res.clients.dcv_swagger_client.models.delete_session_request_data import (
    DeleteSessionRequestData,
)
from res.clients.dcv_swagger_client.models.describe_sessions_request_data import (
    DescribeSessionsRequestData,
)
from res.clients.dcv_swagger_client.models.key_value_pair import KeyValuePair
from res.resources import cluster_settings, token
from res.utils import aws_utils

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

DCV_SESSION_DELETE_ERROR_SESSION_DOESNT_EXIST = (
    "The requested dcvSession does not exist"
)

VDC_SCOPE = ["dcv-session-manager/sm_scope", "cluster-manager/read"]


def delete_sessions(sessions: List[Dict[str, Any]]) -> Tuple[List, List]:
    """
    Delete dcv sessions
    :param sessions: list of dcv sessions to be deleted
    :returns successful and unsuccessul list of stopped sessions
    """
    can_delete_sessions = []
    sessions_to_check = []
    for session in sessions:
        if session.get("force", False):
            can_delete_sessions.append(session)
        else:
            sessions_to_check.append(session)

    sessions_with_count = get_active_counts_for_sessions(sessions_to_check)
    unsuccessful_list = []
    delete_fail_session_ids = []
    for session in sessions_with_count:
        if session.get("connection_count", 0) > 0:
            logger.info(
                f"Session {session.get('idea_session_id')}:{session.get('name')} has {session.get('connection_count')} active connection(s)"
            )
            session["failure_reason"] = (
                f"There exists {session.get('connection_count')} active connection(s)for session_id: {session.get('idea_session_id')}:{session.get('name')}. Please terminate."
            )
            logger.error(session["failure_reason"])
            delete_fail_session_ids.append(session["dcv_session_id"])
            unsuccessful_list.append(session)
        else:
            can_delete_sessions.append(session)

    session_id_names = [
        f"{session.get('idea_session_id')}:{session.get('name')}"
        for session in can_delete_sessions
    ]
    logger.debug(f"Attempting to delete dcv session(s): {session_id_names}")

    response = _delete_sessions(can_delete_sessions)
    successful_list = [
        {"dcv_session_id": e.get("session_id")}
        for e in response.get("successful_list", [])
    ]

    for entry in response.get("unsuccessful_list", []):
        dcv_session_id = entry.get("session_id")
        failure_reason = entry.get("failure_reason")
        if failure_reason == DCV_SESSION_DELETE_ERROR_SESSION_DOESNT_EXIST:
            successful_list.append({"dcv_session_id": dcv_session_id})
        else:
            unsuccessful_list.append(
                {
                    "dcv_session_id": dcv_session_id,
                    "failure_reason": failure_reason,
                }
            )
            delete_fail_session_ids.append(dcv_session_id)
            logger.info(
                f"Delete session request failed for dcv_session_id: {dcv_session_id} because{failure_reason}"
            )
    return successful_list, unsuccessful_list


def get_active_counts_for_sessions(
    sessions: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    if not sessions:
        return []
    dcv_session_id_map = {}
    for session in sessions:
        dcv_session_id_map[session.get("dcv_session_id")] = session
        session["connection_count"] = 0

    response = describe_sessions(sessions)
    session_response = response.get("sessions", {})
    for dcv_session_id, session_info in session_response.items():
        dcv_session_id_map[dcv_session_id]["connection_count"] = session_info.get(
            "num_of_connections", 0
        )
    return sessions


def _delete_sessions(sessions: List[Dict[str, Any]]) -> Dict:
    if not sessions:
        return {}

    delete_sessions_request = list()
    for session in sessions:
        delete_sessions_request.append(
            DeleteSessionRequestData(
                session_id=session.get("dcv_session_id"),
                owner=session.get("owner"),
                force=session.get("force"),
            )
        )

    api_response = _get_sessions_api().delete_sessions(body=delete_sessions_request)
    return api_response.to_dict()


def describe_sessions(sessions: List[Dict[str, Any]]) -> Dict:
    if not sessions:
        sessions = []

    session_ids = [session.get("dcv_session_id") for session in sessions]
    if not session_ids:
        session_ids = None

    response = _describe_sessions(session_ids=session_ids)
    response["sessions"] = {session["id"]: session for session in response["sessions"]}
    return response


def _describe_sessions(
    session_ids: List[str] = None, next_token=None, tags=None, owner=None
) -> Dict:
    filters = list()
    if tags:
        for tag in tags:
            filter_key_value_pair = KeyValuePair(
                key="tag:" + tag["Key"], value=tag["Value"]
            )
            filters.append(filter_key_value_pair)
    if owner:
        filter_key_value_pair = KeyValuePair(key="owner", value=owner)
        filters.append(filter_key_value_pair)

    request = DescribeSessionsRequestData(
        session_ids=session_ids, filters=filters, next_token=next_token
    )
    api_response = _get_sessions_api().describe_sessions(body=request)
    return api_response.to_dict()


def _get_sessions_api() -> dcv_swagger_client.SessionsApi:
    api_instance = dcv_swagger_client.SessionsApi(
        dcv_swagger_client.ApiClient(_get_client_configuration())
    )
    _set_request_headers(api_instance.api_client)
    return api_instance


def _get_internal_endpoints() -> Tuple[str, str]:
    internal_alb_endpoint = cluster_settings.get_setting(
        "cluster.load_balancers.internal_alb.certificates.custom_dns_name"
    )
    broker_client_communication_port = cluster_settings.get_setting(
        "vdc.dcv_broker.client_communication_port"
    )
    return f"https://{internal_alb_endpoint}", broker_client_communication_port


def _get_client_configuration() -> dcv_swagger_client.Configuration:
    configuration = dcv_swagger_client.Configuration()
    endpoint, port = _get_internal_endpoints()
    configuration.host = f"{endpoint}:{port}"
    configuration.verify_ssl = False
    return configuration


def _get_vdc_client_id_secret() -> Tuple[str, str]:
    client_id_arn = cluster_settings.get_setting("vdc.client_id")
    client_secret_arn = cluster_settings.get_setting("vdc.client_secret")
    client_id = aws_utils.get_secret_string(client_id_arn)
    client_secret = aws_utils.get_secret_string(client_secret_arn)
    return client_id, client_secret


def _set_request_headers(api_client) -> None:
    client_id, client_secret = _get_vdc_client_id_secret()
    access_token = token.get_access_token_using_client_credentials(
        client_id,
        client_secret,
        " ".join(VDC_SCOPE),
    )
    api_client.set_default_header(
        header_name="Authorization", header_value="Bearer {}".format(access_token)
    )
