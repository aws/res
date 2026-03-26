#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
from typing import Any, Dict, List, Tuple

from res.clients import dcv_swagger_client
from res.clients.dcv_swagger_client.models.describe_sessions_request_data import (
    DescribeSessionsRequestData,
)
from res.clients.dcv_swagger_client.models.key_value_pair import KeyValuePair
from res.resources import cluster_settings, token
from res.utils import aws_utils, logging_utils

logger = logging_utils.get_logger("dcv-broker-client")

DCV_SESSION_DELETE_ERROR_SESSION_DOESNT_EXIST = (
    "The requested dcvSession does not exist"
)


def get_active_counts_for_sessions(
    sessions: List[Dict[str, Any]],
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


def describe_sessions(sessions: List[Dict[str, Any]], next_token=None) -> Dict:
    if not sessions:
        sessions = []

    session_ids = [
        session.get("dcv_session_id")
        for session in sessions
        if session.get("dcv_session_id")
    ]
    if not session_ids:
        session_ids = None

    response = _describe_sessions(session_ids=session_ids, next_token=next_token)

    # Transform sessions list to dict, but preserve next_token and other fields
    sessions_list = response.get("sessions", [])
    response["sessions"] = {session["id"]: session for session in sessions_list}
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
    VDC_SCOPE = [
        f"{os.getenv('environment_name')}-dcv-session-manager/sm_scope",
        f"{os.getenv('environment_name')}-cluster-manager/read",
    ]

    client_id, client_secret = _get_vdc_client_id_secret()
    access_token = token.get_access_token_using_client_credentials(
        client_id,
        client_secret,
        " ".join(VDC_SCOPE),
    )
    api_client.set_default_header(
        header_name="Authorization", header_value="Bearer {}".format(access_token)
    )
