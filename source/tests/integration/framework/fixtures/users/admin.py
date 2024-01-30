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

import pytest

from ideadatamodel import GetUserRequest, ModifyUserRequest  # type: ignore
from tests.integration.framework.client.res_client import ResClient
from tests.integration.framework.fixtures.fixture_request import FixtureRequest
from tests.integration.framework.fixtures.res_environment import ResEnvironment
from tests.integration.framework.model.client_auth import ClientAuth


@pytest.fixture
def admin(
    request: FixtureRequest, res_environment: ResEnvironment, admin_username: str
) -> ClientAuth:
    """
    Fixture for the admin user
    """

    client = ResClient(request, res_environment, ClientAuth(username="clusteradmin"))
    admin = client.get_user(GetUserRequest(username=admin_username)).user

    is_active = admin.is_active
    if not is_active:
        # Activate the admin user for running integ tests
        admin.is_active = True
        admin = client.modify_user(ModifyUserRequest(user=admin)).user

    def tear_down() -> None:
        if not is_active:
            # Revert the admin user activation status
            admin.is_active = False
            client.modify_user(ModifyUserRequest(user=admin))

    request.addfinalizer(tear_down)

    return ClientAuth(username=admin_username)
