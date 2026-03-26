#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import logging
from typing import Any, Dict, List, Optional

import pytest
import requests

from tests.integration.framework.fixtures.res_environment import ResEnvironment
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.model_utils import (
    get_backend_model_class,
    remove_none_values,
)

# Import backend model classes using the utility function
ListAllowedInstanceTypesForSessionRequestContent = get_backend_model_class(
    "list_allowed_instance_types_for_session_request_content",
    "ListAllowedInstanceTypesForSessionRequestContent",
)
ListAllowedInstanceTypesForSessionResponseContent = get_backend_model_class(
    "list_allowed_instance_types_for_session_response_content",
    "ListAllowedInstanceTypesForSessionResponseContent",
)
ListAllowedInstanceTypesRequestContent = get_backend_model_class(
    "list_allowed_instance_types_request_content",
    "ListAllowedInstanceTypesRequestContent",
)
ListAllowedInstanceTypesResponseContent = get_backend_model_class(
    "list_allowed_instance_types_response_content",
    "ListAllowedInstanceTypesResponseContent",
)
GetPermissionProfileResponseContent = get_backend_model_class(
    "get_permission_profile_response_content", "GetPermissionProfileResponseContent"
)
ListPermissionProfilesResponseContent = get_backend_model_class(
    "list_permission_profiles_response_content", "ListPermissionProfilesResponseContent"
)
ListDCVServersResponseContent = get_backend_model_class(
    "list_dcv_servers_response_content", "ListDCVServersResponseContent"
)
CreateSoftwareStackRequestContent = get_backend_model_class(
    "create_software_stack_request_content", "CreateSoftwareStackRequestContent"
)
CreateSoftwareStackResponseContent = get_backend_model_class(
    "create_software_stack_response_content", "CreateSoftwareStackResponseContent"
)
DeleteSoftwareStackRequestContent = get_backend_model_class(
    "delete_software_stack_request_content", "DeleteSoftwareStackRequestContent"
)
DeleteSoftwareStackResponseContent = get_backend_model_class(
    "delete_software_stack_response_content", "DeleteSoftwareStackResponseContent"
)
GetSoftwareStackResponseContent = get_backend_model_class(
    "get_software_stack_response_content", "GetSoftwareStackResponseContent"
)
ListSoftwareStacksResponseContent = get_backend_model_class(
    "list_software_stacks_response_content", "ListSoftwareStacksResponseContent"
)
UpdateSoftwareStackRequestContent = get_backend_model_class(
    "update_software_stack_request_content", "UpdateSoftwareStackRequestContent"
)
UpdateSoftwareStackResponseContent = get_backend_model_class(
    "update_software_stack_response_content", "UpdateSoftwareStackResponseContent"
)
BatchGetDCVSessionsRequestContent = get_backend_model_class(
    "batch_get_dcv_sessions_request_content", "BatchGetDCVSessionsRequestContent"
)
BatchGetDCVSessionsResponseContent = get_backend_model_class(
    "batch_get_dcv_sessions_response_content", "BatchGetDCVSessionsResponseContent"
)
CreatePermissionProfileRequestContent = get_backend_model_class(
    "create_permission_profile_request_content", "CreatePermissionProfileRequestContent"
)
CreatePermissionProfileResponseContent = get_backend_model_class(
    "create_permission_profile_response_content",
    "CreatePermissionProfileResponseContent",
)
ListSessionPermissionsResponseContent = get_backend_model_class(
    "list_session_permissions_response_content", "ListSessionPermissionsResponseContent"
)
ListSharedPermissionsResponseContent = get_backend_model_class(
    "list_shared_permissions_response_content", "ListSharedPermissionsResponseContent"
)
DeletePermissionProfileResponseContent = get_backend_model_class(
    "delete_permission_profile_response_content",
    "DeletePermissionProfileResponseContent",
)
UpdatePermissionProfileRequestContent = get_backend_model_class(
    "update_permission_profile_request_content", "UpdatePermissionProfileRequestContent"
)
UpdatePermissionProfileResponseContent = get_backend_model_class(
    "update_permission_profile_response_content",
    "UpdatePermissionProfileResponseContent",
)
UpdateSessionPermissionsRequestContent = get_backend_model_class(
    "update_session_permissions_request_content",
    "UpdateSessionPermissionsRequestContent",
)
UpdateSessionPermissionsResponseContent = get_backend_model_class(
    "update_session_permissions_response_content",
    "UpdateSessionPermissionsResponseContent",
)
ListSessionsResponseContent = get_backend_model_class(
    "list_sessions_response_content", "ListSessionsResponseContent"
)
GetSessionResponseContent = get_backend_model_class(
    "get_session_response_content", "GetSessionResponseContent"
)

logger = logging.getLogger(__name__)


class ApiClient:
    """
    API client for invoking RES REST APIs
    """

    def __init__(self, res_environment: ResEnvironment, client_auth: ClientAuth):
        """
        Initialize the API client

        Args:
            res_environment: ResEnvironment fixture containing environment configuration
            client_auth: ClientAuth fixture containing authentication information
        """
        self._endpoint = f"https://{res_environment.web_app_domain_name}"

        # Extract authentication information from ClientAuth
        self.auth_token = client_auth.auth_token
        self.username = client_auth.username

        # Set up session for connection pooling
        self.session = requests.Session()

        # Disable SSL verification for test environment
        self.session.verify = False

        default_headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json",
        }
        if self.auth_token:
            default_headers["Authorization"] = f"Bearer {self.auth_token}"

        # Set default headers
        self.session.headers.update(default_headers)

        # Add X_RES_TEST_USERNAME header
        self.session.headers.update({"X_RES_TEST_USERNAME": self.username})

    def _make_request(
        self,
        method: str,
        path: str,
        request_content: Optional[Any] = None,
        response_model_class: Optional[Any] = None,
    ) -> Any:
        """
        Make an HTTP request to the API

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH, etc.)
            path: API endpoint path
            request_content: Request content object (optional)
            response_model_class: Expected response model class for deserialization (optional)

        Returns:
            Response content object or raw response data

        Raises:
            requests.RequestException: If the request fails
        """
        url = f"{self._endpoint}{path}"

        logger.info(f"Making {method} request to {url}")

        # Convert request content object to JSON if it's a model
        request_data = None
        if request_content is not None:
            raw_dict = request_content.to_dict()
            logger.debug(
                f"Raw dict from to_dict(): {json.dumps(raw_dict, indent=2, default=str)}"
            )
            request_data = remove_none_values(raw_dict)

        logger.debug(
            f"Final request data being sent: {json.dumps(request_data, indent=2, default=str) if request_data else 'None'}"
        )

        try:
            response = self.session.request(
                method.upper(), url, verify=False, json=request_data
            )

            response.raise_for_status()

            # Try to parse JSON response
            try:
                json_response = response.json()
                logger.debug(
                    f"Response received: {json.dumps(json_response, indent=2)}"
                )

                # If we have a response model class, deserialize to that class
                if response_model_class and isinstance(json_response, dict):
                    return response_model_class.from_dict(json_response)
                else:
                    # Return raw response if no model class specified
                    return json_response

            except json.JSONDecodeError:
                # If not JSON, return the text content
                return response.text

        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response content: {e.response.text}")
            raise

    def list_allowed_instance_types(
        self, request_content: ListAllowedInstanceTypesRequestContent  # type: ignore
    ) -> ListAllowedInstanceTypesResponseContent:  # type: ignore
        """
        List allowed instance types for virtual desktops

        Args:
            request_content: ListAllowedInstanceTypesRequestContent object containing:
                - hibernation_support: Whether the instance types need to support hibernation
                - software_stack: Optional virtual desktop software stack which defines the requirements

        Returns:
            ListAllowedInstanceTypesResponseContent containing allowed instance type information
        """
        logger.info(f"Getting allowed instance types...")

        return self._make_request(  # type: ignore
            "POST",
            "/res/virtual-desktop-utils/allowed-instance-type",
            request_content,
            ListAllowedInstanceTypesResponseContent,
        )

    def list_allowed_instance_types_for_session(
        self, request_content: ListAllowedInstanceTypesForSessionRequestContent  # type: ignore
    ) -> ListAllowedInstanceTypesForSessionResponseContent:  # type: ignore
        """
        List allowed instance types for a virtual desktop session

        Args:
            request_content: ListAllowedInstanceTypesForSessionRequestContent object containing:
                - session: Virtual desktop session which defines the requirements

        Returns:
            ListAllowedInstanceTypesForSessionResponseContent containing allowed instance type information
        """
        logger.info(f"Getting allowed instance types for session...")

        return self._make_request(  # type: ignore
            "POST",
            "/res/virtual-desktop-utils/allowed-instance-type-for-session",
            request_content,
            ListAllowedInstanceTypesForSessionResponseContent,
        )

    def create_permission_profile(
        self, request_content: CreatePermissionProfileRequestContent  # type: ignore
    ) -> CreatePermissionProfileResponseContent:  # type: ignore
        """
        Create a permission profile

        Args:
            request_content: CreatePermissionProfileRequestContent object containing:
                - profile: Permission profile to create

        Returns:
            CreatePermissionProfileResponseContent containing the created permission profile
        """
        logger.info(f"Creating permission profile...")
        return self._make_request(  # type: ignore
            "POST",
            "/res/virtual-desktop/permission-profile",
            request_content,
            CreatePermissionProfileResponseContent,
        )

    def delete_permission_profile(
        self, profile_id: str
    ) -> DeletePermissionProfileResponseContent:  # type: ignore
        """
        Delete a permission profile

        Args:
            profile_id: ID of the profile to delete

        Returns:
            DeletePermissionProfileResponseContent containing the deletion result
        """
        logger.info(f"Deleting permission profile: {profile_id}...")
        return self._make_request(  # type: ignore
            "DELETE",
            f"/res/virtual-desktop/permission-profile/{profile_id}",
            response_model_class=DeletePermissionProfileResponseContent,
        )

    def list_permission_profiles(
        self, profile_id: Optional[str] = None
    ) -> ListPermissionProfilesResponseContent:  # type: ignore
        """
        Get list of permission profiles

        Args:
            profile_id: Optional filter by profile ID substring

        Returns:
            ListPermissionProfilesResponseContent containing permission profiles
        """
        logger.info(f"Listing permission profiles (filter: {profile_id})...")
        path = "/res/virtual-desktop-utils/permission-profile"
        if profile_id:
            path += f"?profileId={profile_id}"
        return self._make_request(  # type: ignore
            "GET",
            path,
            response_model_class=ListPermissionProfilesResponseContent,
        )

    def get_permission_profile(self, profile_id: str) -> GetPermissionProfileResponseContent:  # type: ignore
        """
        Get details of a specific permission profile

        Args:
            profile_id: ID of the profile to retrieve

        Returns:
            GetPermissionProfileResponseContent containing permission profile details
        """
        logger.info(f"Getting permission profile: {profile_id}...")
        return self._make_request(  # type: ignore
            "GET",
            f"/res/virtual-desktop-utils/permission-profile/{profile_id}",
            response_model_class=GetPermissionProfileResponseContent,
        )

    def update_permission_profile(
        self,
        profile_id: str,
        request_content: UpdatePermissionProfileRequestContent,  # type: ignore
    ) -> UpdatePermissionProfileResponseContent:  # type: ignore
        """
        Update a permission profile

        Args:
            profile_id: ID of the permission profile to update
            request_content: UpdatePermissionProfileRequestContent object containing:
                - profile: Permission profile to update

        Returns:
            UpdatePermissionProfileResponseContent containing the updated permission profile
        """
        logger.info(f"Updating permission profile: {profile_id}...")
        return self._make_request(  # type: ignore
            "PUT",
            f"/res/virtual-desktop/permission-profile/{profile_id}",
            request_content,
            UpdatePermissionProfileResponseContent,
        )

    def list_dcv_servers(self, next_token: Optional[str] = None) -> ListDCVServersResponseContent:  # type: ignore
        """
        Get list of DCV servers

        Args:
            next_token: Optional pagination token for next page

        Returns:
            ListDCVServersResponseContent containing DCV servers information
        """
        logger.info(f"Listing DCV servers (next_token: {next_token})...")
        path = "/res/virtual-desktop-dcv/server"
        if next_token:
            path += f"?nextToken={next_token}"
        return self._make_request(  # type: ignore
            "GET",
            path,
            response_model_class=ListDCVServersResponseContent,
        )

    def create_software_stack(
        self, request_content: CreateSoftwareStackRequestContent  # type: ignore
    ) -> CreateSoftwareStackResponseContent:  # type: ignore
        """
        Create a virtual desktop software stack

        Args:
            request_content: CreateSoftwareStackRequestContent object containing:
                - software_stack: Virtual desktop software stack to create

        Returns:
            CreateSoftwareStackResponseContent containing the created software stack information
        """
        logger.info(f"Creating software stack...")
        return self._make_request(  # type: ignore
            "POST",
            "/res/virtual-desktop/software-stack",
            request_content,
            CreateSoftwareStackResponseContent,
        )

    def delete_software_stack(
        self, stack_id: str, request_content: DeleteSoftwareStackRequestContent  # type: ignore
    ) -> DeleteSoftwareStackResponseContent:  # type: ignore
        """
        Delete a virtual desktop software stack

        Args:
            stack_id: ID of the software stack to delete
            request_content: DeleteSoftwareStackRequestContent object containing:
                - base_os: Base OS of the software stack to delete

        Returns:
            DeleteSoftwareStackResponseContent containing the deletion result
        """
        logger.info(f"Deleting software stack: {stack_id}...")
        return self._make_request(  # type: ignore
            "DELETE",
            f"/res/virtual-desktop/software-stack/{stack_id}",
            request_content,
            DeleteSoftwareStackResponseContent,
        )

    def get_software_stack(self, stack_id: str, base_os: str) -> GetSoftwareStackResponseContent:  # type: ignore
        """
        Get details of a specific software stack

        Args:
            stack_id: ID of the software stack to retrieve
            base_os: Base operating system of the software stack

        Returns:
            GetSoftwareStackResponseContent containing software stack details
        """
        logger.info(f"Getting software stack: {stack_id} with base_os: {base_os}...")
        return self._make_request(  # type: ignore
            "GET",
            f"/res/virtual-desktop/software-stack/{stack_id}?baseOs={base_os}",
            response_model_class=GetSoftwareStackResponseContent,
        )

    def list_software_stacks(
        self,
        project_id: Optional[str] = None,
        base_os: Optional[str] = None,
        software_stack_name: Optional[str] = None,
    ) -> ListSoftwareStacksResponseContent:  # type: ignore
        """
        Get list of software stacks

        Args:
            project_id: Optional filter by project ID
            base_os: Optional filter by base operating system
            software_stack_name: Optional filter by software stack name

        Returns:
            ListSoftwareStacksResponseContent containing software stacks information
        """
        logger.info(
            f"Listing software stacks (project_id: {project_id}, base_os: {base_os}, name: {software_stack_name})..."
        )
        path = "/res/virtual-desktop/software-stack"

        # Build query parameters
        params = []
        if project_id:
            params.append(f"projectId={project_id}")
        if base_os:
            params.append(f"baseOs={base_os}")
        if software_stack_name:
            params.append(f"softwareStackName={software_stack_name}")

        if params:
            path += "?" + "&".join(params)

        return self._make_request(  # type: ignore
            "GET",
            path,
            response_model_class=ListSoftwareStacksResponseContent,
        )

    def list_session_permissions(
        self,
        res_session_id: Optional[str] = None,
    ) -> ListSessionPermissionsResponseContent:  # type: ignore
        """
        Get list of session permissions

        Args:
            res_session_id: Optional filter by idea session ID

        Returns:
            ListSessionPermissionsResponseContent containing session permissions information
        """
        logger.info(f"Listing software stacks (res_session_id: {res_session_id})...")
        path = "/res/virtual-desktop/session-permission"

        # Build query parameters
        params = []
        if res_session_id:
            params.append(f"resSessionId={res_session_id}")

        if params:
            path += "?" + "&".join(params)

        return self._make_request(  # type: ignore
            "GET",
            path,
            response_model_class=ListSessionPermissionsResponseContent,
        )

    def update_session_permissions(
        self, request_content: UpdateSessionPermissionsRequestContent  # type: ignore
    ) -> UpdateSessionPermissionsResponseContent:  # type: ignore
        """
        Update session permissions

        Args:
            request_content: UpdateSessionPermissionsRequestContent object containing:
                - create: List of session permissions to create
                - update: List of session permissions to update
                - delete: List of session permissions to delete

        Returns:
            UpdateSessionPermissionsResponseContent containing the updated permissions
        """
        logger.info("Updating session permissions...")
        return self._make_request(  # type: ignore
            "PUT",
            "/res/virtual-desktop/session-permission",
            request_content,
            response_model_class=UpdateSessionPermissionsResponseContent,
        )

    def list_shared_permissions(
        self,
        username: Optional[str] = None,
        next_token: Optional[str] = None,
    ) -> ListSharedPermissionsResponseContent:  # type: ignore
        """
        Get list of shared permissions

        Args:
            username: Optional filter by username
            next_token: Optional pagination token for next page

        Returns:
            ListSharedPermissionsResponseContent containing shared permissions information
        """
        logger.info(
            f"Listing shared permissions (username: {username}, next_token: {next_token})..."
        )
        path = "/res/virtual-desktop/shared-permissions"

        # Build query parameters
        params = []
        if username:
            params.append(f"username={username}")
        if next_token:
            params.append(f"nextToken={next_token}")

        if params:
            path += "?" + "&".join(params)

        return self._make_request(  # type: ignore
            "GET",
            path,
            response_model_class=ListSharedPermissionsResponseContent,
        )

    def update_software_stack(
        self, stack_id: str, request_content: UpdateSoftwareStackRequestContent  # type: ignore
    ) -> UpdateSoftwareStackResponseContent:  # type: ignore
        """
        Update a virtual desktop software stack

        Args:
            stack_id: ID of the software stack to update
            request_content: UpdateSoftwareStackRequestContent object containing:
                - software_stack: Virtual desktop software stack to update

        Returns:
            UpdateSoftwareStackResponseContent containing the update result
        """
        logger.info(f"Updating software stack: {stack_id}...")
        return self._make_request(  # type: ignore
            "PUT",
            f"/res/virtual-desktop/software-stack/{stack_id}",
            request_content,
            UpdateSoftwareStackResponseContent,
        )

    def batch_get_dcv_sessions(
        self, sessions: Optional[List[Any]] = None, next_token: Optional[str] = None
    ) -> BatchGetDCVSessionsResponseContent:  # type: ignore
        """
        Batch get DCV sessions

        Args:
            sessions: Optional list of sessions to query
            next_token: Optional pagination token for next page

        Returns:
            BatchGetDCVSessionsResponseContent containing DCV sessions information
        """
        logger.info(
            f"Batch getting DCV sessions (sessions count: {len(sessions) if sessions else 0}, next_token: {next_token})..."
        )

        # Create request content object
        request_content = BatchGetDCVSessionsRequestContent(
            sessions=sessions if sessions is not None else [], next_token=next_token
        )

        return self._make_request(  # type: ignore
            "POST",
            "/res/virtual-desktop-dcv/session",
            request_content=request_content,
            response_model_class=BatchGetDCVSessionsResponseContent,
        )

    def list_sessions(
        self,
        state: Optional[str] = None,
        base_os: Optional[str] = None,
        session_name: Optional[str] = None,
        stack_id: Optional[str] = None,
        owner: Optional[str] = None,
        next_token: Optional[str] = None,
    ) -> ListSessionsResponseContent:  # type: ignore
        """
        Get list of virtual desktop sessions

        Args:
            state: Optional filter by session state
            base_os: Optional filter by base operating system
            session_name: Optional filter by session name
            owner: Optional filter by session owner
            stack_id: Optional filter by software stack ID

        Returns:
            ListSessionsResponseContent containing sessions information
        """
        logger.info(
            f"Listing sessions (state: {state}, base_os: {base_os}, name: {session_name}, stack_id: {stack_id})..."
        )
        path = "/res/virtual-desktop/session"

        # Build query parameters
        params = []
        if state:
            params.append(f"state={state}")
        if base_os:
            params.append(f"baseOs={base_os}")
        if session_name:
            params.append(f"sessionName={session_name}")
        if owner:
            params.append(f"owner={owner}")
        if stack_id:
            params.append(f"stackId={stack_id}")
        if next_token:
            params.append(f"nextToken={next_token}")

        if params:
            path += "?" + "&".join(params)

        return self._make_request(  # type: ignore
            "GET", path, response_model_class=ListSessionsResponseContent
        )

    def get_session(
        self, res_session_id: str, owner: str
    ) -> GetSessionResponseContent:  # type: ignore
        """
        Get details of a virtual desktop session

        Args:
            res_session_id: ID of the session to retrieve
            owner: Owner of the session

        Returns:
            GetSessionResponseContent containing session details
        """
        logger.info(f"Getting session {res_session_id} for owner {owner}...")
        path = f"/res/virtual-desktop/session/{res_session_id}?owner={owner}"

        return self._make_request(  # type: ignore
            "GET", path, response_model_class=GetSessionResponseContent
        )

    def close(self) -> None:
        """
        Close the session and clean up resources
        """
        if self.session:
            self.session.close()

    def __enter__(self) -> "ApiClient":
        """Context manager entry"""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit"""
        self.close()
