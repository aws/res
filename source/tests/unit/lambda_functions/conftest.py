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

import time
from typing import Any
from unittest.mock import MagicMock, Mock

import boto3
import pytest
from _pytest.monkeypatch import MonkeyPatch
from constants import CLUSTER_NAME, LOAD_BALANCER_DNS, SECRET_ARN, USER_POOL_ID
from lambda_functions.configure_sso import ClientProvider, SingleSignOnHelper

from ideadatamodel import SocaAnyPayload

# initialize monkey patch globally, so that it can be used inside session scoped context fixtures
# this allows session scoped monkey patches to be applicable across all unit tests
# monkeypatch.undo() is called at the end of context fixture
monkeypatch = MonkeyPatch()


class MockClusterConfigDB:

    def __init__(self):
        self.items = {
            "identity-provider.cognito.user_pool_id": USER_POOL_ID,
            "cluster-manager.server.web_resources_context_path": "/",
            "cluster.load_balancers.external_alb.load_balancer_dns_name": LOAD_BALANCER_DNS,
        }

    def add_to_db(self, key, value):
        self.items[key] = value

    def remove_from_db(self, key):
        self.items.pop(key)

    def get_item(self, key):
        return self.items.get(key)

    def put_item(self, key, value):
        pass

    def update_item(self, key, value):
        pass


@pytest.fixture(scope="session")
def sso_helper():

    mock_cognito_idp = SocaAnyPayload()
    mock_cognito_idp.update_identity_provider = MagicMock(return_value="idp updated")
    mock_cognito_idp.create_identity_provider = MagicMock(return_value="idp created")
    mock_cognito_idp.delete_identity_provider = MagicMock(return_value="idp deleted")
    mock_cognito_idp.update_user_pool_client = MagicMock(
        return_value={
            "UserPoolClient": {"ClientId": "test-id", "ClientSecret": "test-secret"}
        }
    )
    mock_cognito_idp.create_user_pool_client = MagicMock(
        return_value={
            "UserPoolClient": {"ClientId": "test-id", "ClientSecret": "test-secret"}
        }
    )
    mock_cognito_idp.get_identity_provider_by_identifier = MagicMock(
        return_value={"IdentityProvider": None}
    )

    mock_secrets_manager = SocaAnyPayload()
    mock_secrets_manager.describe_secret = MagicMock(return_value=None)
    mock_secrets_manager.create_secret = MagicMock(return_value={"ARN": SECRET_ARN})
    mock_secrets_manager.update_secret = MagicMock(return_value={"ARN": SECRET_ARN})

    mock_cluster_db = MockClusterConfigDB()
    monkeypatch.setattr(ClientProvider, "cognito", lambda *_: mock_cognito_idp)
    monkeypatch.setattr(
        ClientProvider, "secrets_manager", lambda *_: mock_secrets_manager
    )
    monkeypatch.setattr(ClientProvider, "dynamodb_resource", lambda *_: Mock())
    sso_helper = SingleSignOnHelper(CLUSTER_NAME)
    sso_helper.config = mock_cluster_db

    yield sso_helper

    print("clean-up ...")
    monkeypatch.undo()
