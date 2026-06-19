#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import pytest
from res.resources.dcv import session_resolver

PRIVATE_DNS = "ip-10-0-1-5.ec2.internal"


class TestResolveSession:

    def test_resolve_session_success(self):
        session = {"server": {"private_dns_name": PRIVATE_DNS}}

        result = session_resolver.resolve_session(session, "HTTP")

        assert result == {
            "SessionId": "console",
            "TransportProtocol": "HTTP",
            "DcvServerEndpoint": PRIVATE_DNS,
            "Port": 8443,
            "WebUrlPath": "/",
        }

    def test_resolve_session_quic(self):
        session = {"server": {"private_dns_name": PRIVATE_DNS}}

        result = session_resolver.resolve_session(session, "QUIC")

        assert result["TransportProtocol"] == "QUIC"

    def test_resolve_session_no_dns_name(self):
        session = {"server": {"instance_id": "i-123"}, "idea_session_id": "ses-1"}

        with pytest.raises(ValueError, match="Session ses-1 has no server DNS name"):
            session_resolver.resolve_session(session, "HTTP")

    def test_resolve_session_missing_server_field(self):
        session = {"owner": "user1", "idea_session_id": "ses-2"}

        with pytest.raises(ValueError, match="Session ses-2 has no server DNS name"):
            session_resolver.resolve_session(session, "HTTP")
