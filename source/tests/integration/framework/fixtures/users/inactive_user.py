#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import pytest

from ideadatamodel import GetUserRequest, ModifyUserRequest  # type: ignore
from tests.integration.framework.client.res_client import ResClient
from tests.integration.framework.fixtures.fixture_request import FixtureRequest
from tests.integration.framework.fixtures.res_environment import ResEnvironment
from tests.integration.framework.model.client_auth import ClientAuth


@pytest.fixture
def inactive_user(
    request: FixtureRequest, res_environment: ResEnvironment, inactive_username: str
) -> ClientAuth:
    """
    Fixture for the inactive user
    """

    api_invoker_type = request.config.getoption("--api-invoker-type")
    client = ResClient(
        res_environment, ClientAuth(username="clusteradmin"), api_invoker_type
    )
    inactive_user = client.get_user(GetUserRequest(username=inactive_username)).user

    is_active = inactive_user.is_active
    if is_active:
        # Activate the non admin user for running integ tests
        inactive_user.is_active = False
        inactive_user = client.modify_user(ModifyUserRequest(user=inactive_user)).user

    def tear_down() -> None:
        if is_active:
            # Revert the non admin user activation status
            inactive_user.is_active = True
            client.modify_user(ModifyUserRequest(user=inactive_user))

    request.addfinalizer(tear_down)

    return ClientAuth(username=inactive_username)
