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

import os
import tempfile
import uuid

import pytest
from filelock import FileLock
from res import constants
from res.clients.aws.aws_provider import get_aws_provider  # type: ignore
from res.resources import cluster_settings  # type: ignore

from tests.integration.framework.fixtures.fixture_request import FixtureRequest
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.cognito_sync import cognito_sync

# Cognito stores the POSIX uid in this custom attribute. create-session rejects a
# Cognito user with no uid, so the fixture must set one; picking a value in the
# Cognito id range but above the auto-assigned start avoids colliding with real
# synced users.
CUSTOM_UID_ATTRIBUTE = "custom:uid"
NON_ADMIN_UID = str(constants.COGNITO_MIN_ID_INCLUSIVE + 99000)

# cognito_sync does a full pool->DDB reconcile, so two xdist workers syncing at
# once can leave a stale row. This host-wide lock keeps each worker's pool change
# and its sync atomic relative to the others.
_SYNC_LOCK = FileLock(os.path.join(tempfile.gettempdir(), "res-cognito-sync.lock"))


@pytest.fixture
def cognito_non_admin(request: FixtureRequest) -> ClientAuth:
    """
    Create a Cognito (native) non-admin user for the duration of a test.

    The user is created directly in the Cognito user pool without being placed
    in the sudoer group, then materialized into RES (role=user) via cognito_sync.
    Backend test mode accepts the ClientAuth token, so no real login is needed.

    Safe under parallel (xdist) runs: each username is unique and the pool
    change + sync is serialized by a host-wide lock.
    """
    user_pool_id = cluster_settings.get_setting(constants.IDENTITY_PROVIDER_USERPOOL_ID)
    # Keep the username short: role-assignment actor keys ("<name>:user") cap the
    # name at 21 chars, so a longer prefix would break project membership grants.
    username = f"cog-na-{uuid.uuid4().hex[:8]}"

    cognito = get_aws_provider().cognito_idp()

    with _SYNC_LOCK:
        cognito.admin_create_user(
            UserPoolId=user_pool_id,
            Username=username,
            UserAttributes=[
                {"Name": "email", "Value": f"{username}@example.com"},
                {"Name": "email_verified", "Value": "true"},
                {"Name": CUSTOM_UID_ATTRIBUTE, "Value": NON_ADMIN_UID},
            ],
            # Suppress the invite email; this account is only ever used via test mode.
            MessageAction="SUPPRESS",
        )
        # Move the user out of FORCE_CHANGE_PASSWORD so it syncs as enabled/active.
        cognito.admin_set_user_password(
            UserPoolId=user_pool_id,
            Username=username,
            Password=f"Res-{uuid.uuid4().hex[:12]}!",
            Permanent=True,
        )
        # Pull the new user into the RES users table (role=user, since it is not
        # in the sudoer group and is not the cluster admin).
        cognito_sync()

    def tear_down() -> None:
        with _SYNC_LOCK:
            cognito.admin_delete_user(UserPoolId=user_pool_id, Username=username)
            # Re-sync so the deleted user is removed from the RES users table.
            cognito_sync()

    request.addfinalizer(tear_down)

    return ClientAuth(username=username)
