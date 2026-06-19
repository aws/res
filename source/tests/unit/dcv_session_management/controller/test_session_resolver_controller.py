#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from unittest.mock import patch

import pytest

from idea.dcv_session_management.api.controllers import session_resolver_controller
from datamodel.models.resolve_session_response_content import (
    ResolveSessionResponseContent,
)
from res.app.exceptions import BadRequestException, NotFoundException


SESSION_ID = "ses-111"
CLIENT_IP = "10.0.1.50"
PRIVATE_DNS = "ip-10-0-1-5.ec2.internal"

MOCK_SESSION = {"server": {"private_dns_name": PRIVATE_DNS}}

RESOLVE_RESULT = {
    "SessionId": "console",
    "TransportProtocol": "HTTP",
    "DcvServerEndpoint": PRIVATE_DNS,
    "Port": 8443,
    "WebUrlPath": "/",
}


class TestSessionResolverController:

    @patch("res.resources.sessions.get_sessions_by_ids")
    @patch.object(session_resolver_controller, "session_resolver")
    def test_resolve_session_http_success(self, mock_resolver, mock_get_sessions):
        mock_get_sessions.return_value = {SESSION_ID: MOCK_SESSION}
        mock_resolver.SUPPORTED_TRANSPORT_PROTOCOLS = {"HTTP", "QUIC"}
        mock_resolver.resolve_session.return_value = RESOLVE_RESULT

        result = session_resolver_controller.resolve_session(
            SESSION_ID, "HTTP", CLIENT_IP
        )

        assert isinstance(result, ResolveSessionResponseContent)
        assert result.session_id == "console"
        assert result.transport_protocol == "HTTP"
        assert result.dcv_server_endpoint == PRIVATE_DNS
        assert result.port == 8443
        assert result.web_url_path == "/"
        mock_get_sessions.assert_called_once_with([SESSION_ID])
        mock_resolver.resolve_session.assert_called_once_with(MOCK_SESSION, "HTTP")

    @patch("res.resources.sessions.get_sessions_by_ids")
    @patch.object(session_resolver_controller, "session_resolver")
    def test_resolve_session_quic_success(self, mock_resolver, mock_get_sessions):
        mock_get_sessions.return_value = {SESSION_ID: MOCK_SESSION}
        quic_result = {**RESOLVE_RESULT, "TransportProtocol": "QUIC"}
        mock_resolver.SUPPORTED_TRANSPORT_PROTOCOLS = {"HTTP", "QUIC"}
        mock_resolver.resolve_session.return_value = quic_result

        result = session_resolver_controller.resolve_session(
            SESSION_ID, "QUIC", CLIENT_IP
        )

        assert isinstance(result, ResolveSessionResponseContent)
        assert result.transport_protocol == "QUIC"

    @patch.object(session_resolver_controller, "session_resolver")
    def test_resolve_session_invalid_transport(self, mock_resolver):
        mock_resolver.SUPPORTED_TRANSPORT_PROTOCOLS = {"HTTP", "QUIC"}

        with pytest.raises(BadRequestException):
            session_resolver_controller.resolve_session(SESSION_ID, "TCP", CLIENT_IP)

        mock_resolver.resolve_session.assert_not_called()

    @patch("res.resources.sessions.get_sessions_by_ids")
    @patch.object(session_resolver_controller, "session_resolver")
    def test_resolve_session_not_found(self, mock_resolver, mock_get_sessions):
        mock_get_sessions.return_value = {}
        mock_resolver.SUPPORTED_TRANSPORT_PROTOCOLS = {"HTTP", "QUIC"}

        with pytest.raises(NotFoundException):
            session_resolver_controller.resolve_session(SESSION_ID, "HTTP", CLIENT_IP)

        mock_resolver.resolve_session.assert_not_called()

    @patch("res.resources.sessions.get_sessions_by_ids")
    @patch.object(session_resolver_controller, "session_resolver")
    def test_resolve_session_no_dns_name(self, mock_resolver, mock_get_sessions):
        mock_get_sessions.return_value = {SESSION_ID: MOCK_SESSION}
        mock_resolver.SUPPORTED_TRANSPORT_PROTOCOLS = {"HTTP", "QUIC"}
        mock_resolver.resolve_session.side_effect = ValueError("no server DNS name")

        with pytest.raises(NotFoundException):
            session_resolver_controller.resolve_session(SESSION_ID, "HTTP", CLIENT_IP)
