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
ListScheduleTypesResponseContent = get_backend_model_class(
    "list_schedule_types_response_content", "ListScheduleTypesResponseContent"
)
ListSupportedGpusResponseContent = get_backend_model_class(
    "list_supported_gpus_response_content", "ListSupportedGpusResponseContent"
)
ListSupportedOsesResponseContent = get_backend_model_class(
    "list_supported_oses_response_content", "ListSupportedOsesResponseContent"
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
BatchGetDCVSessionsRequestContent = get_backend_model_class(
    "batch_get_dcv_sessions_request_content", "BatchGetDCVSessionsRequestContent"
)
BatchGetDCVSessionsResponseContent = get_backend_model_class(
    "batch_get_dcv_sessions_response_content", "BatchGetDCVSessionsResponseContent"
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

    def list_supported_oses(self) -> Dict[str, Any]:
        """
        List supported operating systems for virtual desktops

        Returns:
            ListSupportedOsesResponseContent containing supported OS information
        """
        logger.info(f"Getting supported OS list...")
        return self._make_request(  # type: ignore
            "GET",
            "/res/virtual-desktop-utils/supported-os",
            response_model_class=ListSupportedOsesResponseContent,
        )

    def list_supported_gpus(self) -> Dict[str, Any]:
        """
        List supported GPUs for virtual desktops

        Returns:
            ListSupportedGpusResponseContent containing supported GPU information
        """
        logger.info(f"Getting supported GPU list...")
        return self._make_request(  # type: ignore
            "GET",
            "/res/virtual-desktop-utils/supported-gpu",
            response_model_class=ListSupportedGpusResponseContent,
        )

    def list_schedule_types(self) -> Dict[str, Any]:
        """
        List available schedule types for virtual desktops

        Returns:
            ListScheduleTypesResponseContent containing schedule type information
        """
        logger.info(f"Getting schedule type list...")
        return self._make_request(  # type: ignore
            "GET",
            "/res/virtual-desktop-utils/schedule-type",
            response_model_class=ListScheduleTypesResponseContent,
        )

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
