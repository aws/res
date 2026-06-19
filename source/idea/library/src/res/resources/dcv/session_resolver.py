#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict

from res.resources import sessions

# Default DCV server's web URL path
DEFAULT_WEB_URL_PATH = "/"

# Default HTTPS port for the DCV server in dcv.conf.
DCV_SERVER_PORT = 8443

SUPPORTED_TRANSPORT_PROTOCOLS = {"HTTP", "QUIC"}


def resolve_session(session: Dict[str, Any], transport: str) -> Dict[str, Any]:
    """Resolve a DCV session to its server endpoint.

    :param session: User session
    :param transport: transport protocol (HTTP or QUIC)
    :return: dict with session routing info for the Connection Gateway
    """
    private_dns_name = session.get(sessions.SESSION_DB_SERVER_KEY, {}).get(
        sessions.SESSION_DB_PRIVATE_DNS_NAME_KEY
    )
    if not private_dns_name:
        session_id = session.get(sessions.SESSION_DB_RANGE_KEY)
        raise ValueError(f"Session {session_id} has no server DNS name")
    return {
        "SessionId": "console",
        "TransportProtocol": transport,
        "DcvServerEndpoint": private_dns_name,
        "Port": DCV_SERVER_PORT,
        "WebUrlPath": DEFAULT_WEB_URL_PATH,
    }
