#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
Fixture for permission profile testing.

This module provides a pytest fixture for setting up and tearing down
permission profiles in integration tests.
"""

import logging

import pytest

from tests.integration.framework.client.api_client import (
    ApiClient,
    CreatePermissionProfileRequestContent,
    CreatePermissionProfileResponseContent,
    GetPermissionProfileResponseContent,
)
from tests.integration.framework.fixtures.fixture_request import FixtureRequest
from tests.integration.framework.fixtures.res_environment import ResEnvironment
from tests.integration.framework.utils.virtual_desktop import (
    get_permission_profile_base_payload,
)

logger = logging.getLogger(__name__)


@pytest.fixture
def permission_profile(
    request: FixtureRequest,
    res_environment: ResEnvironment,
) -> GetPermissionProfileResponseContent:
    """
    Fixture for setting up/tearing down a test permission profile.

    This fixture creates a permission profile using the provided parameters,
    and automatically cleans it up after the test completes.

    Usage:
        @pytest.mark.parametrize("permission_profile", [
            ("test-profile-id", {"title": "Custom Test Profile"}, "admin")
        ], indirect=True)
        def test_something(permission_profile):
            # permission_profile contains the created profile details
            assert permission_profile.profile.profile_id == "test-profile-id"

    Args:
        request: FixtureRequest containing parameters:
            - param[0]: profile_id (str) - The ID for the permission profile
            - param[1]: overrides (dict, optional) - Override values for the profile
            - param[2]: auth_fixture_name (str) - Name of the auth fixture to use (e.g., "admin")

    Returns:
        GetPermissionProfileResponseContent: The created permission profile details
    """
    if hasattr(request, "param") and request.param:
        profile_id = request.param[0]
        overrides = request.param[1] if len(request.param) > 1 else {}
        auth_fixture_name = request.param[2] if len(request.param) > 2 else "admin"
    else:
        # Default values if no parameters provided
        profile_id = "test-permission-profile"
        overrides = {}
        auth_fixture_name = "admin"

    auth = request.getfixturevalue(auth_fixture_name)
    api_client = ApiClient(res_environment, auth)

    # Prepare the payload
    payload = get_permission_profile_base_payload(profile_id, **overrides)
    request_content = CreatePermissionProfileRequestContent(**payload)

    # Create the permission profile
    try:
        logger.info(f"Creating permission profile: {profile_id}")
        create_response = api_client.create_permission_profile(request_content)

        if (
            not create_response
            or not hasattr(create_response, "profile")
            or not create_response.profile  # type: ignore[attr-defined]
        ):
            raise ValueError(f"Failed to create permission profile: {profile_id}")

        # We've already verified above that create_response and profile are not None
        created_profile_id = create_response.profile.profile_id  # type: ignore[attr-defined]
        logger.info(f"Successfully created permission profile: {created_profile_id}")

        profile_details = api_client.get_permission_profile(created_profile_id)

    except Exception as e:
        logger.error(f"Failed to create permission profile {profile_id}: {str(e)}")
        raise

    def tear_down() -> None:
        """Clean up the permission profile after test completion."""
        try:
            logger.info(f"Cleaning up permission profile: {created_profile_id}")
            api_client.delete_permission_profile(created_profile_id)
            logger.info(
                f"Successfully cleaned up permission profile: {created_profile_id}"
            )
        except Exception as cleanup_error:
            logger.warning(
                f"Failed to cleanup permission profile {created_profile_id}: {cleanup_error}"
            )

    request.addfinalizer(tear_down)

    return profile_details
