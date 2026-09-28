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

import pytest

from tests.integration.framework.client.api_client import (
    ApiClient,
    GetPermissionProfileResponseContent,
    UpdatePermissionProfileRequestContent,
)
from tests.integration.framework.fixtures.permission_profile import permission_profile
from tests.integration.framework.fixtures.res_environment import (
    ResEnvironment,
    res_environment,
)
from tests.integration.framework.fixtures.users.admin import admin
from tests.integration.framework.model.client_auth import ClientAuth

logger = logging.getLogger(__name__)

# The admin profile acts as the "environment boundary": when a permission is
# disabled here, the backend propagates the disable to all other profiles.
ADMIN_PROFILE_ID = "admin_profile"

# The permission key we toggle in the boundary tests.
BOUNDARY_PERMISSION_KEY = "clipboard_copy"


def _get_permission_value(
    profile_response: GetPermissionProfileResponseContent, key: str
) -> bool:
    """Extract a permission's enabled state from a get-profile response."""
    for perm in profile_response.profile.permissions:
        if perm.key == key:
            return bool(perm.enabled)
    raise KeyError(f"Permission '{key}' not found in profile")


def _build_admin_update_payload(enabled: bool) -> Dict[str, Any]:
    """Build an update payload that sets BOUNDARY_PERMISSION_KEY on admin."""
    return {
        "profile": {
            "profile_id": ADMIN_PROFILE_ID,
            "title": "Admin Profile",
            "permissions": [
                {"key": BOUNDARY_PERMISSION_KEY, "enabled": enabled},
            ],
        }
    }


def _read_admin_boundary_value(api_client: ApiClient) -> bool:
    """Read the current value of BOUNDARY_PERMISSION_KEY on the admin profile."""
    admin_profile = api_client.get_permission_profile(ADMIN_PROFILE_ID)
    return _get_permission_value(admin_profile, BOUNDARY_PERMISSION_KEY)


@pytest.mark.dev
@pytest.mark.usefixtures("res_environment")
@pytest.mark.usefixtures("region")
class TestDcvPermissionBoundaries:
    """
    DCV Permission Boundary tests (doc "DCV Permission"). Verifies that the
    admin profile acts as an environment-wide boundary: disabling a permission
    on the admin profile propagates the disable to all other profiles, and
    re-enabling on the admin profile does NOT re-enable it on profiles that
    were already disabled.

    The permission_profile fixture handles teardown (deletes the test profile).
    """

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    @pytest.mark.parametrize(
        "permission_profile",
        [
            (
                "test-boundary-profile",
                {
                    "title": "Boundary Test Profile",
                    "permissions": [
                        {
                            "key": BOUNDARY_PERMISSION_KEY,
                            "name": "Clipboard Copy",
                            "enabled": True,
                        },
                    ],
                },
                "admin",
            )
        ],
        indirect=True,
    )
    def test_boundary_disable_propagates_to_profile(
        self,
        request: pytest.FixtureRequest,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
        permission_profile: Any,
    ) -> None:
        """
        Disabling a permission on the admin profile (boundary) propagates the
        disable to other profiles.
        """
        api_client = ApiClient(res_environment, admin)
        profile_id = permission_profile.profile.profile_id

        # Read the original boundary value so we can restore it exactly.
        original_value = _read_admin_boundary_value(api_client)
        if not original_value:
            pytest.skip(
                f"{BOUNDARY_PERMISSION_KEY} is already disabled on the admin "
                f"profile — cannot test propagation of a disable"
            )

        # Confirm the test profile starts with the permission enabled.
        initial = api_client.get_permission_profile(profile_id)
        assert _get_permission_value(initial, BOUNDARY_PERMISSION_KEY) is True

        # Disable the permission on the admin profile (the boundary).
        api_client.update_permission_profile(
            ADMIN_PROFILE_ID,
            UpdatePermissionProfileRequestContent(
                **_build_admin_update_payload(enabled=False)
            ),
        )
        # Restore the admin profile to its original value regardless of outcome.
        request.addfinalizer(
            lambda: api_client.update_permission_profile(
                ADMIN_PROFILE_ID,
                UpdatePermissionProfileRequestContent(
                    **_build_admin_update_payload(enabled=original_value)
                ),
            )
        )

        # The test profile should now have the permission disabled.
        after_disable = api_client.get_permission_profile(profile_id)
        assert _get_permission_value(after_disable, BOUNDARY_PERMISSION_KEY) is False, (
            f"Expected {BOUNDARY_PERMISSION_KEY} to be disabled after boundary "
            f"propagation, but got: {after_disable.profile.permissions}"  # type: ignore[attr-defined]
        )

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    @pytest.mark.parametrize(
        "permission_profile",
        [
            (
                "test-boundary-norenable",
                {
                    "title": "Boundary No-Reenable Profile",
                    "permissions": [
                        {
                            "key": BOUNDARY_PERMISSION_KEY,
                            "name": "Clipboard Copy",
                            "enabled": True,
                        },
                    ],
                },
                "admin",
            )
        ],
        indirect=True,
    )
    def test_boundary_reenable_does_not_propagate(
        self,
        request: pytest.FixtureRequest,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
        permission_profile: Any,
    ) -> None:
        """
        Re-enabling a permission on the admin profile does NOT re-enable it on
        profiles that were already disabled (boundary only propagates disables).
        """
        api_client = ApiClient(res_environment, admin)
        profile_id = permission_profile.profile.profile_id

        # Read the original boundary value so we can restore it exactly.
        original_value = _read_admin_boundary_value(api_client)
        if not original_value:
            pytest.skip(
                f"{BOUNDARY_PERMISSION_KEY} is already disabled on the admin "
                f"profile — cannot test propagation of a disable"
            )

        # Step 1: disable in the boundary (admin profile).
        api_client.update_permission_profile(
            ADMIN_PROFILE_ID,
            UpdatePermissionProfileRequestContent(
                **_build_admin_update_payload(enabled=False)
            ),
        )
        # Restore the admin profile to its original value regardless of outcome.
        request.addfinalizer(
            lambda: api_client.update_permission_profile(
                ADMIN_PROFILE_ID,
                UpdatePermissionProfileRequestContent(
                    **_build_admin_update_payload(enabled=original_value)
                ),
            )
        )

        # Confirm propagation disabled it on the test profile.
        after_disable = api_client.get_permission_profile(profile_id)
        assert _get_permission_value(after_disable, BOUNDARY_PERMISSION_KEY) is False

        # Step 2: re-enable on the admin profile.
        api_client.update_permission_profile(
            ADMIN_PROFILE_ID,
            UpdatePermissionProfileRequestContent(
                **_build_admin_update_payload(enabled=True)
            ),
        )

        # The test profile must STILL have the permission disabled.
        after_reenable = api_client.get_permission_profile(profile_id)
        assert (
            _get_permission_value(after_reenable, BOUNDARY_PERMISSION_KEY) is False
        ), (
            f"Expected {BOUNDARY_PERMISSION_KEY} to remain disabled after boundary "
            f"re-enable, but it was re-enabled: {after_reenable.profile.permissions}"  # type: ignore[attr-defined]
        )
