#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from datamodel.models.resolve_session_response_content import (
    ResolveSessionResponseContent,
)  # noqa: E501

from res.app.exceptions import BadRequestException, NotFoundException  # type: ignore
from res.resources import sessions
from res.utils import logging_utils  # type: ignore
from res.resources.dcv import session_resolver  # type: ignore

logger = logging_utils.get_logger(__name__)


def resolve_session(session_id, transport, client_ip_address):  # noqa: E501
    """resolve_session

    Maps RES Session ID to a destination host running the Amazon DCV server # noqa: E501

    :param session_id: RES Session ID to resolve
    :type session_id: str
    :param transport: Transport protocol
    :type transport: str
    :param client_ip_address: Client IP address
    :type client_ip_address: str

    :rtype: Union[ResolveSessionResponseContent, Tuple[ResolveSessionResponseContent, int], Tuple[ResolveSessionResponseContent, int, Dict[str, str]]
    """
    logger.info("Resolving session %s for client %s", session_id, client_ip_address)

    if transport not in session_resolver.SUPPORTED_TRANSPORT_PROTOCOLS:
        raise BadRequestException(f"Invalid transport protocol: {transport}")
    
    sessions_map = sessions.get_sessions_by_ids([session_id])
    session = sessions_map.get(session_id)
    if not session:
        raise NotFoundException(f"No session found for session ID: {session_id}")

    try:
        result = session_resolver.resolve_session(session, transport)
    except ValueError as e:
        raise NotFoundException(f"Session {session_id} DNS name not found: {e}")

    return ResolveSessionResponseContent.from_dict(result)
