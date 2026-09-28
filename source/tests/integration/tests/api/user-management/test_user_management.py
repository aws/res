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

"""
User management integration tests.

Covers user enable/disable lifecycle via the cluster-manager API.
All tests are ``@dev`` — API-only, no VDI launch required.
"""

import logging
import uuid

import pytest

from ideadatamodel import GetUserRequest  # type: ignore
from tests.integration.framework.client.res_client import ResClient
from tests.integration.framework.fixtures.res_environment import (
    ResEnvironment,
    res_environment,
)
from tests.integration.framework.fixtures.users.admin import admin
from tests.integration.framework.fixtures.users.non_admin import non_admin
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.retry_utils import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_INITIAL_DELAY,
    DEFAULT_MAX_DELAY,
    DEFAULT_MAX_RETRIES,
    retry_with_backoff,
)

logger = logging.getLogger(__name__)

_RUN_ID = str(uuid.uuid4())[:6]


@pytest.mark.dev
@pytest.mark.usefixtures("res_environment")
@pytest.mark.usefixtures("region")
class TestUserManagement:
    """User enable/disable lifecycle via the cluster-manager API."""

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize("admin_username", ["admin1"])
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_disable_user_rejects_api_calls(
        self,
        request: pytest.FixtureRequest,
        res_environment: ResEnvironment,
        admin: ClientAuth,
        admin_username: str,
        non_admin: ClientAuth,
        non_admin_username: str,
    ) -> None:
        """
        Disable user -> API rejected; re-enable -> API works again.
        """
        api_invoker_type = request.config.getoption("--api-invoker-type")
        admin_client = ResClient(res_environment, admin, api_invoker_type)

        def _restore() -> None:
            admin_client.enable_user(non_admin_username)

        request.addfinalizer(_restore)

        original_user = admin_client.get_user(
            GetUserRequest(username=non_admin_username)
        ).user
        assert original_user.enabled, f"User {non_admin_username} should be enabled"

        logger.info(f"Disabling user {non_admin_username}...")
        admin_client.disable_user(non_admin_username)

        def _check_disabled() -> None:
            user = admin_client.get_user(
                GetUserRequest(username=non_admin_username)
            ).user
            assert not user.enabled, "User should be disabled"

        retry_with_backoff(
            func=_check_disabled,
            max_retries=DEFAULT_MAX_RETRIES,
            initial_delay=DEFAULT_INITIAL_DELAY,
            backoff_factor=DEFAULT_BACKOFF_FACTOR,
            max_delay=DEFAULT_MAX_DELAY,
            exceptions=(AssertionError,),
        )

        logger.info("Verifying disabled user cannot make API calls...")
        disabled_client = ResClient(res_environment, non_admin, api_invoker_type)
        disabled_client.get_user(
            GetUserRequest(username=non_admin_username),
            should_succeed=False,
            expected_error_code="UNAUTHORIZED_ACCESS",
        )

        logger.info(f"Re-enabling user {non_admin_username}...")
        admin_client.enable_user(non_admin_username)

        def _check_reenabled() -> None:
            user = admin_client.get_user(
                GetUserRequest(username=non_admin_username)
            ).user
            assert user.enabled, "Re-enabled user should be active"

        retry_with_backoff(
            func=_check_reenabled,
            max_retries=DEFAULT_MAX_RETRIES,
            initial_delay=DEFAULT_INITIAL_DELAY,
            backoff_factor=DEFAULT_BACKOFF_FACTOR,
            max_delay=DEFAULT_MAX_DELAY,
            exceptions=(AssertionError,),
        )

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize("admin_username", ["admin1"])
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_get_user_returns_expected_fields(
        self,
        request: pytest.FixtureRequest,
        res_environment: ResEnvironment,
        admin: ClientAuth,
        admin_username: str,
        non_admin: ClientAuth,
        non_admin_username: str,
    ) -> None:
        """get_user returns correct user data after AD sync."""
        api_invoker_type = request.config.getoption("--api-invoker-type")
        admin_client = ResClient(res_environment, admin, api_invoker_type)

        result = admin_client.get_user(GetUserRequest(username=non_admin_username))
        user = result.user

        assert user is not None, "get_user should return a user object"
        assert user.username == non_admin_username
        assert user.is_active is not None
