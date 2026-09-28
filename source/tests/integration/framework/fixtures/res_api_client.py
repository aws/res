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
Fixtures for constructing a ``ResApiClient`` against the live RES backend
Lambda using cluster-manager's Cognito service-token credentials.

Tests that exercise service-token-only behavior (e.g. ``skip_user_authz``,
``enforce_scope``) should depend on these fixtures rather than re-deriving
the credential / scope wiring per test.
"""

from typing import List

import pytest
from res.clients.api_client.res_api_client import ResApiClient  # type: ignore
from res.constants import MODULE_ID_VDC  # type: ignore
from res.resources import cluster_settings  # type: ignore
from res.utils import aws_utils  # type: ignore

from tests.integration.framework.fixtures.res_environment import ResEnvironment


def _cluster_manager_client_id_secret() -> tuple[str, str]:
    client_id_arn = cluster_settings.get_setting("cluster-manager.client_id")
    client_secret_arn = cluster_settings.get_setting("cluster-manager.client_secret")
    return (
        aws_utils.get_secret_string(client_id_arn),
        aws_utils.get_secret_string(client_secret_arn),
    )


def _vdc_scopes(environment_name: str) -> List[str]:
    return [
        f"{environment_name}-{MODULE_ID_VDC}/read",
        f"{environment_name}-{MODULE_ID_VDC}/write",
    ]


@pytest.fixture
def res_api_client(res_environment: ResEnvironment) -> ResApiClient:
    """
    ``ResApiClient`` configured with cluster-manager's Cognito client credentials
    and the full VDC read+write scope set.

    Use this fixture in tests that need to exercise the backend's service-token
    code path (``token_info["scope"]`` present, ``skip_user_authz=True``).
    """
    client_id, client_secret = _cluster_manager_client_id_secret()
    return ResApiClient(
        endpoint=f"https://{res_environment.web_app_domain_name}",
        client_id=client_id,
        client_secret=client_secret,
        scopes=_vdc_scopes(res_environment.environment_name),
    )


@pytest.fixture
def res_api_client_read_only(res_environment: ResEnvironment) -> ResApiClient:
    """
    ``ResApiClient`` configured with cluster-manager's credentials but only the
    VDC read scope. Used to verify ``enforce_scope`` rejects write operations
    when the token does not carry the write scope.
    """
    client_id, client_secret = _cluster_manager_client_id_secret()
    return ResApiClient(
        endpoint=f"https://{res_environment.web_app_domain_name}",
        client_id=client_id,
        client_secret=client_secret,
        scopes=[f"{res_environment.environment_name}-{MODULE_ID_VDC}/read"],
    )
