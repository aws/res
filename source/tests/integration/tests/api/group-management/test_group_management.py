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
Group management integration tests.

Covers group enable/disable lifecycle via the cluster-manager API.
All tests are ``@dev`` — API-only, no VDI launch required.
"""

import logging
import uuid

import pytest

from tests.integration.framework.client.res_client import ResClient
from tests.integration.framework.fixtures.res_environment import (
    ResEnvironment,
    res_environment,
)
from tests.integration.framework.fixtures.users.admin import admin
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
class TestGroupManagement:
    """Group enable/disable lifecycle."""

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize("admin_username", ["admin1"])
    def test_disable_and_enable_group(
        self,
        request: pytest.FixtureRequest,
        res_environment: ResEnvironment,
        admin: ClientAuth,
        admin_username: str,
    ) -> None:
        """
        Disable group -> verify disabled; re-enable -> verify enabled.
        """
        api_invoker_type = request.config.getoption("--api-invoker-type")
        admin_client = ResClient(res_environment, admin, api_invoker_type)

        group_name = "group_1"

        def _restore() -> None:
            admin_client.enable_group(group_name)

        request.addfinalizer(_restore)

        logger.info(f"Disabling group {group_name}...")
        admin_client.disable_group(group_name)

        def _check_group_disabled() -> None:
            result = admin_client.get_group(group_name)
            assert not result.group.enabled, "Group should be disabled"

        retry_with_backoff(
            func=_check_group_disabled,
            max_retries=DEFAULT_MAX_RETRIES,
            initial_delay=DEFAULT_INITIAL_DELAY,
            backoff_factor=DEFAULT_BACKOFF_FACTOR,
            max_delay=DEFAULT_MAX_DELAY,
            exceptions=(AssertionError,),
        )

        logger.info(f"Re-enabling group {group_name}...")
        admin_client.enable_group(group_name)

        def _check_group_enabled() -> None:
            result = admin_client.get_group(group_name)
            assert result.group.enabled, "Group should be re-enabled"

        retry_with_backoff(
            func=_check_group_enabled,
            max_retries=DEFAULT_MAX_RETRIES,
            initial_delay=DEFAULT_INITIAL_DELAY,
            backoff_factor=DEFAULT_BACKOFF_FACTOR,
            max_delay=DEFAULT_MAX_DELAY,
            exceptions=(AssertionError,),
        )
