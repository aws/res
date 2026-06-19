#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
from typing import Any, Dict, List, Tuple

from res.clients import dcv_session_management_client
from res.clients.dcv_session_management_client.api.health_api import HealthApi
from res.clients.dcv_session_management_client.api.sessions_api import SessionsApi
from res.clients.dcv_session_management_client.models.describe_sessions_request_content import (
    DescribeSessionsRequestContent,
)
from res.clients.dcv_session_management_client.models.describe_sessions_request_data import (
    DescribeSessionsRequestData,
)
from res.clients.dcv_session_management_client.models.get_session_screenshot_request_data import (
    GetSessionScreenshotRequestData,
)
from res.clients.dcv_session_management_client.models.get_session_screenshots_request_content import (
    GetSessionScreenshotsRequestContent,
)
from res.clients.dcv_session_management_client.models.update_session_permissions_request_content import (
    UpdateSessionPermissionsRequestContent,
)
from res.clients.dcv_session_management_client.models.update_session_permissions_request_data import (
    UpdateSessionPermissionsRequestData,
)
from res.resources import cluster_settings, token
from res.utils import aws_utils, logging_utils

logger = logging_utils.get_logger("dcv-session-manager-client")


def get_session_connection_data(session_id: str, username: str) -> Dict[str, Any]:
    """Gets the information to connect to a session.

    Args:
        :param session_id: Session id to get connection details for (required)
        :param username: User to get the connection token for (required)

    Returns:
        Dict with session connection details.

    Raises:
        ApiException: on API errors.
        Exception: on unexpected errors.
    """
    api = _get_api(SessionsApi)
    raw_response = api.get_session_connection_data(
        session_id=session_id, username=username
    )
    connection_token = (
        raw_response.connection_token.get_secret_value()
        if raw_response.connection_token
        else None
    )

    session = raw_response.session
    server = session.server if session else None

    return {
        "idea_session_id": session.id if session else None,
        "idea_session_owner": session.owner if session else None,
        "username": username,
        "web_url_path": server.web_url_path if server else None,
        "access_token": connection_token,
    }


def get_session_screenshots(session_ids: List[str], requester: str) -> dict:
    """Get screenshots for a list of DCV sessions.

    Args:
        :param session_ids: List of RES session IDs to fetch screenshots for.
        :param requester: Username used by the private API to authorize each
            screenshot against session ownership and shared session permissions.

    Returns:
        Dict with 'successful_list' and 'unsuccessful_list'.
    """
    if not session_ids:
        return {"successful_list": [], "unsuccessful_list": []}

    api = _get_api(SessionsApi)
    request_content = GetSessionScreenshotsRequestContent(
        requester=requester,
        sessions=[
            GetSessionScreenshotRequestData(session_id=sid) for sid in session_ids
        ],
    )
    response = api.get_session_screenshots(request_content)
    return response.to_dict()


def health_check() -> dict:
    """Check the health of the DCV Session Management service."""
    api = _get_api(HealthApi)
    response = api.health_check()
    return response.to_dict()


def _get_api(api_class):
    """Create an API instance with configured client and auth headers."""
    api_instance = api_class(
        dcv_session_management_client.ApiClient(_get_client_configuration())
    )
    _set_request_headers(api_instance.api_client)
    return api_instance


def update_session_permissions(
    session_id: str, owner: str, permissions_file: str = None
) -> dict:
    """Update session permissions via the DCV Session Management Lambda."""
    logger.info(
        f"update_session_permissions called with: session_id={session_id}, owner={owner}"
    )
    api = _get_api(SessionsApi)
    request = UpdateSessionPermissionsRequestContent(
        sessions=[
            UpdateSessionPermissionsRequestData(
                session_id=session_id,
                owner=owner,
                permissions_file=permissions_file,
            )
        ]
    )
    response = api.update_session_permissions(request)
    logger.info(f"update_session_permissions response: {response}")
    return response.to_dict()


def describe_sessions(session_requests: List[Dict[str, str]]) -> dict:
    """Describe DCV sessions via the DCV Session Management Lambda.

    Args:
        session_requests: list of {"session_id": str, "owner": str} dicts.

    Returns:
        Dict with 'successful_list' and 'unsuccessful_list'.
    """
    if not session_requests:
        return {"successful_list": [], "unsuccessful_list": []}

    api = _get_api(SessionsApi)
    request = DescribeSessionsRequestContent(
        sessions=[
            DescribeSessionsRequestData(
                session_id=req["session_id"],
                owner=req["owner"],
            )
            for req in session_requests
        ]
    )
    response = api.describe_sessions(request)
    logger.info(f"describe_sessions response: {response}")
    return response.to_dict()


def _get_client_configuration() -> dcv_session_management_client.Configuration:
    configuration = dcv_session_management_client.Configuration()
    internal_alb_endpoint = cluster_settings.get_setting(
        "cluster.load_balancers.internal_alb.certificates.custom_dns_name"
    )
    if not internal_alb_endpoint:
        raise ValueError(
            "Missing required setting: cluster.load_balancers.internal_alb.certificates.custom_dns_name"
        )
    configuration.host = f"https://{internal_alb_endpoint}"
    configuration.verify_ssl = False
    return configuration


def _get_vdc_client_id_secret() -> Tuple[str, str]:
    client_id_arn = cluster_settings.get_setting("vdc.client_id")
    client_secret_arn = cluster_settings.get_setting("vdc.client_secret")
    client_id = aws_utils.get_secret_string(client_id_arn)
    client_secret = aws_utils.get_secret_string(client_secret_arn)
    return client_id, client_secret


def _set_request_headers(api_client) -> None:
    environment_name = os.environ["environment_name"]
    VDC_SCOPE = [
        f"{environment_name}-dcv-session-manager/sm_scope",
    ]

    client_id, client_secret = _get_vdc_client_id_secret()
    access_token = token.get_access_token_using_client_credentials(
        client_id,
        client_secret,
        " ".join(VDC_SCOPE),
    )
    api_client.set_default_header(
        header_name="Authorization", header_value=f"Bearer {access_token}"
    )
