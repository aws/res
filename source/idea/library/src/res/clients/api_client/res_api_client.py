#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
from typing import Any, List, Optional
from urllib.parse import urlencode

import requests
import urllib3
from datamodel.models.backend.batch_delete_session_request_content import (
    BatchDeleteSessionRequestContent,
)
from datamodel.models.backend.batch_delete_session_response_content import (
    BatchDeleteSessionResponseContent,
)
from datamodel.models.backend.batch_start_session_request_content import (
    BatchStartSessionRequestContent,
)
from datamodel.models.backend.batch_start_session_response_content import (
    BatchStartSessionResponseContent,
)
from datamodel.models.backend.batch_stop_session_request_content import (
    BatchStopSessionRequestContent,
)
from datamodel.models.backend.batch_stop_session_response_content import (
    BatchStopSessionResponseContent,
)
from datamodel.models.backend.create_permission_profile_request_content import (
    CreatePermissionProfileRequestContent,
)
from datamodel.models.backend.create_permission_profile_response_content import (
    CreatePermissionProfileResponseContent,
)
from datamodel.models.backend.create_software_stack_request_content import (
    CreateSoftwareStackRequestContent,
)
from datamodel.models.backend.create_software_stack_response_content import (
    CreateSoftwareStackResponseContent,
)
from datamodel.models.backend.delete_permission_profile_response_content import (
    DeletePermissionProfileResponseContent,
)
from datamodel.models.backend.delete_software_stack_request_content import (
    DeleteSoftwareStackRequestContent,
)
from datamodel.models.backend.delete_software_stack_response_content import (
    DeleteSoftwareStackResponseContent,
)
from datamodel.models.backend.get_permission_profile_response_content import (
    GetPermissionProfileResponseContent,
)
from datamodel.models.backend.get_software_stack_response_content import (
    GetSoftwareStackResponseContent,
)
from datamodel.models.backend.list_sessions_response_content import (
    ListSessionsResponseContent,
)
from datamodel.models.backend.list_software_stacks_response_content import (
    ListSoftwareStacksResponseContent,
)
from datamodel.models.backend.update_session_permissions_request_content import (
    UpdateSessionPermissionsRequestContent,
)
from datamodel.models.backend.update_session_permissions_response_content import (
    UpdateSessionPermissionsResponseContent,
)
from datamodel.models.backend.update_software_stack_request_content import (
    UpdateSoftwareStackRequestContent,
)
from datamodel.models.backend.update_software_stack_response_content import (
    UpdateSoftwareStackResponseContent,
)
from res.resources import token
from res.utils import logging_utils
from res.utils.model_utils import remove_none_values

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging_utils.get_logger("res-api-client")

DEFAULT_REQUEST_TIMEOUT_SECONDS = 30


class ResApiClient:
    """
    Generic client for invoking RES backend Lambda APIs through the internal ALB.

    Uses the RES library token resource to obtain an OAuth2 client_credentials
    access token from Cognito with the provided Cognito app client ID, client
    secret, and scopes in the ``{env-name}-{module-id}/{read|write}`` format.
    """

    def __init__(
        self,
        endpoint: str,
        client_id: str,
        client_secret: str,
        scopes: List[str],
        timeout: float = DEFAULT_REQUEST_TIMEOUT_SECONDS,
    ):
        """
        Initialize the API client.

        Args:
            endpoint: Base URL of the backend Lambda's internal ALB,
                e.g. ``https://internal-alb.example.com``.
            client_id: Cognito app client ID of the calling module.
            client_secret: Cognito app client secret of the calling module.
            scopes: OAuth2 scopes to request when issuing tokens, formatted as
                ``{env-name}-{module-id}/{read|write}`` (e.g.
                ``["env-vdc/read", "env-vdc/write"]``).
            timeout: Per-request timeout in seconds.
        """
        self._endpoint = endpoint
        self._client_id = client_id
        self._client_secret = client_secret
        self._scopes = scopes
        self._timeout = timeout

        self._session = requests.Session()
        self._session.verify = False
        self._session.headers.update(
            {
                "Content-Type": "application/json;charset=UTF-8",
                "Accept": "application/json",
            }
        )

    def _get_access_token(self) -> str:
        return token.get_access_token_using_client_credentials(
            self._client_id,
            self._client_secret,
            " ".join(self._scopes),
        )

    def _make_request(
        self,
        method: str,
        path: str,
        request_content: Optional[Any] = None,
        response_model_class: Optional[Any] = None,
    ) -> Any:
        """
        Make an HTTP request to the API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH, etc.)
            path: API endpoint path
            request_content: Request content object with ``to_dict()`` (optional)
            response_model_class: Response model class with ``from_dict`` (optional)

        Returns:
            Response model instance, parsed JSON, or response text.

        Raises:
            requests.RequestException: If the request fails.
        """
        self._session.headers["Authorization"] = f"Bearer {self._get_access_token()}"

        url = f"{self._endpoint}{path}"

        logger.info(f"Making {method} request to {url}")

        request_data = None
        if request_content is not None:
            request_data = remove_none_values(request_content.to_dict())

        logger.debug(
            f"Final request data being sent: {json.dumps(request_data, indent=2, default=str) if request_data else 'None'}"
        )

        try:
            response = self._session.request(
                method.upper(),
                url,
                verify=False,
                json=request_data,
                timeout=self._timeout,
            )

            response.raise_for_status()

            try:
                json_response = response.json()
                logger.debug(
                    f"Response received: {json.dumps(json_response, indent=2)}"
                )

                if response_model_class and isinstance(json_response, dict):
                    return response_model_class.from_dict(json_response)
                return json_response

            except json.JSONDecodeError:
                return response.text

        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response content: {e.response.text}")
            raise

    def list_sessions(
        self,
        state: Optional[str] = None,
        base_os: Optional[str] = None,
        session_name: Optional[str] = None,
        stack_id: Optional[str] = None,
        owner: Optional[str] = None,
        next_token: Optional[str] = None,
    ) -> ListSessionsResponseContent:
        """List virtual desktop sessions.

        Returns ``ListSessionsResponseContent`` with ``listing`` and ``next_token``.
        Callers requiring full pages must iterate until ``next_token`` is empty.
        """
        path = "/res/virtual-desktop/sessions"

        params = {}
        if state:
            params["state"] = state
        if base_os:
            params["baseOs"] = base_os
        if session_name:
            params["sessionName"] = session_name
        if stack_id:
            params["stackId"] = stack_id
        if owner:
            params["owner"] = owner
        if next_token:
            params["nextToken"] = next_token
        if params:
            path += "?" + urlencode(params)

        return self._make_request(
            "GET", path, response_model_class=ListSessionsResponseContent
        )

    def batch_delete_session(
        self, request_content: BatchDeleteSessionRequestContent
    ) -> BatchDeleteSessionResponseContent:
        """Batch delete virtual desktop sessions."""
        return self._make_request(
            "POST",
            "/res/virtual-desktop/sessions/delete",
            request_content,
            BatchDeleteSessionResponseContent,
        )

    def batch_stop_session(
        self, request_content: BatchStopSessionRequestContent
    ) -> BatchStopSessionResponseContent:
        """Batch stop virtual desktop sessions."""
        return self._make_request(
            "POST",
            "/res/virtual-desktop/sessions/stop",
            request_content,
            BatchStopSessionResponseContent,
        )

    def batch_start_session(
        self, request_content: BatchStartSessionRequestContent
    ) -> BatchStartSessionResponseContent:
        """Batch start virtual desktop sessions."""
        return self._make_request(
            "POST",
            "/res/virtual-desktop/sessions/start",
            request_content,
            BatchStartSessionResponseContent,
        )

    def update_session_permissions(
        self, request_content: UpdateSessionPermissionsRequestContent
    ) -> UpdateSessionPermissionsResponseContent:
        """Create, update, and/or delete virtual desktop session permissions."""
        return self._make_request(
            "PUT",
            "/res/virtual-desktop/session-permissions",
            request_content,
            UpdateSessionPermissionsResponseContent,
        )

    def list_all_sessions(self, **kwargs: Any) -> List[Any]:
        """List all sessions across all pages. Accepts same kwargs as list_sessions."""
        sessions = []
        next_token = None
        while True:
            response = self.list_sessions(next_token=next_token, **kwargs)
            sessions.extend(response.listing or [])
            next_token = response.next_token
            if not next_token:
                break
        return sessions

    def create_software_stack(
        self, request_content: CreateSoftwareStackRequestContent
    ) -> CreateSoftwareStackResponseContent:
        """Create a virtual desktop software stack."""
        return self._make_request(
            "POST",
            "/res/virtual-desktop/software-stacks",
            request_content,
            CreateSoftwareStackResponseContent,
        )

    def update_software_stack(
        self,
        stack_id: str,
        request_content: UpdateSoftwareStackRequestContent,
    ) -> UpdateSoftwareStackResponseContent:
        """Update a virtual desktop software stack."""
        return self._make_request(
            "PUT",
            f"/res/virtual-desktop/software-stacks/{stack_id}",
            request_content,
            UpdateSoftwareStackResponseContent,
        )

    def delete_software_stack(
        self,
        stack_id: str,
        request_content: DeleteSoftwareStackRequestContent,
    ) -> DeleteSoftwareStackResponseContent:
        """Delete a virtual desktop software stack."""
        return self._make_request(
            "DELETE",
            f"/res/virtual-desktop/software-stacks/{stack_id}",
            request_content,
            DeleteSoftwareStackResponseContent,
        )

    def get_software_stack(
        self, stack_id: str, base_os: str
    ) -> GetSoftwareStackResponseContent:
        """Get details of a specific software stack."""
        path = f"/res/virtual-desktop/software-stacks/{stack_id}?{urlencode({'baseOs': base_os})}"
        return self._make_request(
            "GET",
            path,
            response_model_class=GetSoftwareStackResponseContent,
        )

    def list_software_stacks(
        self,
        project_id: Optional[str] = None,
        base_os: Optional[str] = None,
        software_stack_name: Optional[str] = None,
        next_token: Optional[str] = None,
    ) -> ListSoftwareStacksResponseContent:
        """List virtual desktop software stacks. Callers must paginate via
        ``next_token`` for full results."""
        path = "/res/virtual-desktop/software-stacks"

        params = {}
        if project_id:
            params["projectId"] = project_id
        if base_os:
            params["baseOs"] = base_os
        if software_stack_name:
            params["softwareStackName"] = software_stack_name
        if next_token:
            params["nextToken"] = next_token
        if params:
            path += "?" + urlencode(params)

        return self._make_request(
            "GET", path, response_model_class=ListSoftwareStacksResponseContent
        )

    def create_permission_profile(
        self, request_content: CreatePermissionProfileRequestContent
    ) -> CreatePermissionProfileResponseContent:
        """Create a virtual desktop permission profile."""
        return self._make_request(
            "POST",
            "/res/virtual-desktop/permission-profiles",
            request_content,
            CreatePermissionProfileResponseContent,
        )

    def delete_permission_profile(
        self, profile_id: str
    ) -> DeletePermissionProfileResponseContent:
        """Delete a virtual desktop permission profile."""
        return self._make_request(
            "DELETE",
            f"/res/virtual-desktop/permission-profiles/{profile_id}",
            response_model_class=DeletePermissionProfileResponseContent,
        )

    def get_permission_profile(
        self, profile_id: str
    ) -> GetPermissionProfileResponseContent:
        """Get a virtual desktop permission profile by id."""
        return self._make_request(
            "GET",
            f"/res/virtual-desktop-utils/permission-profiles/{profile_id}",
            response_model_class=GetPermissionProfileResponseContent,
        )

    def close(self) -> None:
        """Close the session and clean up resources."""
        if self._session:
            self._session.close()

    def __enter__(self) -> "ResApiClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
