#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

import logging
from typing import Any, Dict

import requests
import urllib3
from res.resources import cluster_settings, token  # type: ignore
from res.utils import aws_utils  # type: ignore

from tests.integration.framework.fixtures.res_environment import ResEnvironment

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class DcvSessionManagementClient:
    """
    Client for calling private DCV Session Management APIs via the internal ALB.
    Authenticates using OAuth2 client credentials (Cognito sm_scope).
    """

    def __init__(self, res_environment: ResEnvironment):
        self._endpoint = f"https://{res_environment.internal_alb_endpoint}"
        self._environment_name = res_environment.environment_name
        self._session = requests.Session()
        self._session.verify = False
        self._session.headers.update({"Content-Type": "application/json"})
        self._authenticate()

    def _authenticate(self) -> None:
        client_id_arn = cluster_settings.get_setting("vdc.client_id")
        client_secret_arn = cluster_settings.get_setting("vdc.client_secret")
        client_id = aws_utils.get_secret_string(client_id_arn)
        client_secret = aws_utils.get_secret_string(client_secret_arn)
        if not client_id or not client_secret:
            raise RuntimeError(
                "Failed to retrieve DCV client credentials from Secrets Manager. "
                f"client_id_arn={client_id_arn}, client_secret_arn={client_secret_arn}"
            )

        scope = f"{self._environment_name}-dcv-session-manager/sm_scope"
        access_token = token.get_access_token_using_client_credentials(
            client_id, client_secret, scope
        )
        if not access_token:
            raise RuntimeError("Failed to obtain access token for DCV session management")

        self._session.headers.update(
            {"Authorization": f"Bearer {access_token}"}
        )

    def health_check(self) -> Dict[str, Any]:
        """Check the health of the DCV session management service."""
        response = self._session.get(f"{self._endpoint}/health")
        response.raise_for_status()
        return response.json()

    def get_session_connection_data(
        self, session_id: str, username: str
    ) -> Dict[str, Any]:
        """Get connection data for a specific session and user."""
        response = self._session.post(
            f"{self._endpoint}/sessionConnectionData/{session_id}/{username}"
        )
        response.raise_for_status()
        return response.json()

    def describe_sessions(self, sessions: list[Dict[str, str]]) -> Dict[str, Any]:
        """Describe one or more sessions by session_id and owner."""
        payload = {
            "sessions": [
                {"session_id": s["session_id"], "owner": s["owner"]}
                for s in sessions
            ]
        }
        response = self._session.post(
            f"{self._endpoint}/describeSessions", json=payload
        )
        response.raise_for_status()
        return response.json()

    def get_session_screenshots(self, session_ids: list[str]) -> Dict[str, Any]:
        """Get screenshots for one or more sessions."""
        payload = {
            "sessions": [{"session_id": sid} for sid in session_ids]
        }
        response = self._session.post(
            f"{self._endpoint}/sessionScreenshots", json=payload
        )
        response.raise_for_status()
        return response.json()

    def update_session_permissions(
        self, sessions: list[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Update permissions for one or more sessions."""
        payload = {"sessions": sessions}
        response = self._session.put(
            f"{self._endpoint}/sessionPermissions", json=payload
        )
        response.raise_for_status()
        return response.json()

    def external_auth(
        self, res_session_id: str, authentication_token: str, client_address: str = ""
    ) -> Dict[str, Any]:
        """Perform external authentication for a session.

        Args:
            res_session_id: RES session ID (idea_session_id), passed in the URL path
            authentication_token: Bearer token to validate
            client_address: Client IP address
        """
        payload = {
            "session_id": "console",
            "authentication_token": authentication_token,
            "client_address": client_address,
        }
        response = self._session.post(
            f"{self._endpoint}/externalAuth/{res_session_id}", json=payload
        )
        response.raise_for_status()
        return response.json()

    def resolve_session(
        self, session_id: str, transport: str, client_ip_address: str
    ) -> Dict[str, Any]:
        """Resolve a session to a specific transport and client IP."""
        response = self._session.post(
            f"{self._endpoint}/resolveSession",
            params={
                "sessionId": session_id,
                "transport": transport,
                "clientIpAddress": client_ip_address,
            },
        )
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        """Close the session and clean up resources."""
        if self._session:
            self._session.close()

    def __enter__(self) -> "DcvSessionManagementClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
