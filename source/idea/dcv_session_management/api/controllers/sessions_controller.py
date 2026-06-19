#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import base64
import binascii
import re

import connexion
from connexion.exceptions import OAuthProblem
from typing import Any, Dict, List, Tuple

from datamodel import util  # noqa: E501
from datamodel.models.bad_request_exception_response_content import BadRequestExceptionResponseContent  # noqa: E501
from datamodel.models.external_auth_request_content import ExternalAuthRequestContent  # noqa: E501
from datamodel.models.external_auth_response_content import ExternalAuthResponseContent  # noqa: E501
from datamodel.models.get_session_connection_data_response_content import GetSessionConnectionDataResponseContent  # noqa: E501
from datamodel.models.get_session_screenshot_request_data import GetSessionScreenshotRequestData  # noqa: E501
from datamodel.models.get_session_screenshot_successful_response import GetSessionScreenshotSuccessfulResponse  # noqa: E501
from datamodel.models.get_session_screenshot_unsuccessful_response import GetSessionScreenshotUnsuccessfulResponse  # noqa: E501
from datamodel.models.get_session_screenshots_request_content import GetSessionScreenshotsRequestContent  # noqa: E501
from datamodel.models.get_session_screenshots_response_content import GetSessionScreenshotsResponseContent  # noqa: E501
from datamodel.models.internal_service_exception_response_content import InternalServiceExceptionResponseContent  # noqa: E501
from datamodel.models.server import Server  # noqa: E501
from datamodel.models.session import Session  # noqa: E501
from datamodel.models.session_screenshot import SessionScreenshot  # noqa: E501
from datamodel.models.dcv_session_management.update_session_permissions_request_content import UpdateSessionPermissionsRequestContent  # noqa: E501
from datamodel.models.dcv_session_management.update_session_permissions_response_content import UpdateSessionPermissionsResponseContent  # noqa: E501
from datamodel.models.dcv_session_management.update_session_permissions_successful_response import UpdateSessionPermissionsSuccessfulResponse  # noqa: E501
from datamodel.models.dcv_session_management.update_session_permissions_unsuccessful_response import UpdateSessionPermissionsUnsuccessfulResponse  # noqa: E501
from datamodel.models.dcv_session_management.describe_sessions_request_content import DescribeSessionsRequestContent  # noqa: E501
from datamodel.models.dcv_session_management.describe_sessions_response_content import DescribeSessionsResponseContent  # noqa: E501
from datamodel.models.dcv_session_management.describe_sessions_successful_response import DescribeSessionsSuccessfulResponse  # noqa: E501
from datamodel.models.dcv_session_management.describe_sessions_unsuccessful_response import DescribeSessionsUnsuccessfulResponse  # noqa: E501
from res.app.exceptions import ForbiddenException  # type: ignore
from res.exceptions import SessionAccessDenied, UserSessionNotFound  # type: ignore
from res.resources import session_permissions, sessions  # type: ignore
from res.resources.dcv import (  # type: ignore
    session_connection_data,
    session_permissions as dcv_session_permissions,
    session_screenshots,
    sessions as dcv_sessions,
    external_auth as external_auth_service,
)
from res.utils import logging_utils  # type: ignore

logger = logging_utils.get_logger(__name__)

BASE64_PATTERN = re.compile(r"^[A-Za-z0-9+/=]+$")


def _validate_permissions_requests(
    session_requests: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Validate base64 encoding of permissions_file for each session request.

    Returns (valid_requests, unsuccessful_list).
    """
    valid_requests: List[Dict[str, Any]] = []
    unsuccessful_list: List[Dict[str, Any]] = []

    for session_data in session_requests:
        session_id = session_data.get("session_id", "unknown")
        permissions_file = session_data.get("permissions_file")

        if not permissions_file:
            unsuccessful_list.append({
                "session_id": session_id,
                "failure_reason": "permissions_file is required",
            })
            continue

        if not BASE64_PATTERN.fullmatch(permissions_file):
            unsuccessful_list.append({
                "session_id": session_id,
                "failure_reason": "permissions_file contains invalid base64 characters",
            })
            continue

        try:
            base64.b64decode(permissions_file, validate=True)
        except binascii.Error:
            unsuccessful_list.append({
                "session_id": session_id,
                "failure_reason": "permissions_file is not valid base64",
            })
            continue

        valid_requests.append(session_data)

    return valid_requests, unsuccessful_list


def _validate_session_access(session_id: str, username: str) -> Dict[str, Any]:
    """Validate session exists and user has access. Returns the session record."""
    try:
        return session_permissions.validate_session_access(session_id, username)
    except SessionAccessDenied:
        raise ForbiddenException(session_permissions.ACCESS_DENIED_MSG) from None

def external_auth(body, res_session_id):  # noqa: E501
    """external_auth

    Validate user credentials and session permissions on DCV session streaming # noqa: E501

    :param external_auth_request_content:
    :type external_auth_request_content: dict | bytes
    :param res_session_id: RES session ID embedded in the auth-token-verifier URL configured on the DCV host
    :type res_session_id: str

    :rtype: Union[ExternalAuthResponseContent, Tuple[ExternalAuthResponseContent, int], Tuple[ExternalAuthResponseContent, int, Dict[str, str]]
    """
    authentication_token = body.get("authentication_token", "")
    client_address = body.get("client_address", "")

    try:
        username, error = external_auth_service.validate_connection_token(
            authentication_token, res_session_id
        )
    except Exception:
        logger.exception(
            "Unexpected error during external auth for session %s from %s",
            res_session_id, client_address
        )
        return {"result": "no", "message": "Authentication failed"}

    if error:
        logger.warning(
            "External auth denied for session %s from %s",
            res_session_id, client_address
        )
        return {"result": "no", "message": error}
    return {"result": "yes", "username": username}


def get_session_connection_data(session_id, username):  # noqa: E501
    """get_session_connection_data

    Gets the information to connect to a session # noqa: E501

    :param session_id: Session id to get connection details for
    :type session_id: str
    :param username: User to get the connection token for
    :type username: str

    :rtype: Union[GetSessionConnectionDataResponseContent, Tuple[GetSessionConnectionDataResponseContent, int], Tuple[GetSessionConnectionDataResponseContent, int, Dict[str, str]]
    """
    session = _validate_session_access(session_id, username)

    result = session_connection_data.get_session_connection_data(session_id, username)

    return GetSessionConnectionDataResponseContent(
        session=Session(
            id=session_id,
            owner=session.get("owner"),
            server=Server(web_url_path=result["webUrlPath"]),
        ),
        connection_token=result["connectionToken"],
    )


def get_session_screenshots(body):  # noqa: E501
    """get_session_screenshots

    Gets DCV session screenshots # noqa: E501

    :param body:
    :type body: dict | bytes

    :rtype: GetSessionScreenshotsResponseContent
    """
    request = GetSessionScreenshotsRequestContent.from_dict(body)
    requester = request.requester

    authorized_session_ids: List[str] = []
    unauthorized_failures: List[Dict[str, str]] = []
    for session in request.sessions:
        try:
            session_permissions.validate_session_access(session.session_id, requester)
            authorized_session_ids.append(session.session_id)
        except SessionAccessDenied:
            unauthorized_failures.append({
                "session_id": session.session_id,
                "failure_reason": session_permissions.ACCESS_DENIED_MSG,
            })

    successful, unsuccessful = session_screenshots.get_session_screenshots(authorized_session_ids)
    unsuccessful.extend(unauthorized_failures)

    return GetSessionScreenshotsResponseContent(
        successful_list=[
            GetSessionScreenshotSuccessfulResponse(
                session_screenshot=SessionScreenshot.from_dict(s)
            )
            for s in successful
        ],
        unsuccessful_list=[
            GetSessionScreenshotUnsuccessfulResponse(
                get_session_screenshot_request_data=GetSessionScreenshotRequestData(
                    session_id=u["session_id"],
                ),
                failure_reason=u["failure_reason"],
            )
            for u in unsuccessful
        ],
    )


def update_session_permissions(body):  # noqa: E501
    """Updates DCV session permissions via SSM.

    Authorization: This is a service-to-service endpoint authenticated via
    Cognito client credentials (sm_scope). It is called by the VDC controller,
    not by end users directly.
    """
    request = UpdateSessionPermissionsRequestContent.from_dict(body)

    session_requests = [
        {"session_id": s.session_id, "permissions_file": s.permissions_file}
        for s in request.sessions
    ]

    valid_requests, validation_failures = _validate_permissions_requests(session_requests)

    if not valid_requests:
        return UpdateSessionPermissionsResponseContent(
            successful_list=[],
            unsuccessful_list=[
                UpdateSessionPermissionsUnsuccessfulResponse(
                    session_id=u["session_id"],
                    failure_reason=u["failure_reason"],
                )
                for u in validation_failures
            ],
        )

    successful_list, unsuccessful_list = dcv_session_permissions.update_session_permissions(valid_requests)
    unsuccessful_list.extend(validation_failures)

    return UpdateSessionPermissionsResponseContent(
        successful_list=[
            UpdateSessionPermissionsSuccessfulResponse(session_id=s["session_id"])
            for s in successful_list
        ],
        unsuccessful_list=[
            UpdateSessionPermissionsUnsuccessfulResponse(
                session_id=u["session_id"],
                failure_reason=u["failure_reason"],
            )
            for u in unsuccessful_list
        ],
    )


def describe_sessions(body):  # noqa: E501
    """describe_sessions

    Describes DCV sessions # noqa: E501

    :param describe_sessions_request_content:
    :type describe_sessions_request_content: dict | bytes

    :rtype: Union[DescribeSessionsResponseContent, Tuple[DescribeSessionsResponseContent, int], Tuple[DescribeSessionsResponseContent, int, Dict[str, str]]
    """
    request = DescribeSessionsRequestContent.from_dict(body)

    session_map = {}
    for s in request.sessions:
        try:
            session_map[s.session_id] = sessions.get_session(
                owner=s.owner, session_id=s.session_id
            )
        except UserSessionNotFound:
            session_map[s.session_id] = None

    successful_list, unsuccessful_list = dcv_sessions.describe_sessions(session_map)

    return DescribeSessionsResponseContent(
        successful_list=[
            DescribeSessionsSuccessfulResponse(
                session_id=s["session_id"],
                num_of_connections=s["num_of_connections"],
            )
            for s in successful_list
        ],
        unsuccessful_list=[
            DescribeSessionsUnsuccessfulResponse(
                session_id=u["session_id"],
                failure_reason=u["failure_reason"],
            )
            for u in unsuccessful_list
        ],
    )
