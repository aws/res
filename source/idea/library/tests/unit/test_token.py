#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import unittest
from unittest.mock import MagicMock

import pytest
import requests
import res as res
from res.resources import cluster_settings, token
from res.utils import auth_utils, table_utils

TEST_COGNITO_DOMAIN_URL = "test_cognito_domain_url"
TEST_ACCESS_TOKEN = "test_access_token"
TEST_STRING = "test"


@pytest.fixture(scope="class")
def monkeypatch_for_class(request):
    request.cls.monkeypatch = pytest.MonkeyPatch()


@pytest.mark.usefixtures("monkeypatch_for_class")
class TestToken(unittest.TestCase):

    def setUp(self):
        table_utils.create_item(
            cluster_settings.CLUSTER_SETTINGS_TABLE_NAME,
            item={
                cluster_settings.CLUSTER_SETTINGS_HASH_KEY: auth_utils.COGNITO_DOMAIN_URL_KEY,
                cluster_settings.CLUSTER_SETTINGS_VALUE_KEY: TEST_COGNITO_DOMAIN_URL,
            },
        )

    def test_get_access_token_without_client_details_returns_empty_access_token(self):
        access_token = token.get_access_token_using_client_credentials(None, None, None)
        assert access_token == ""

    def test_get_access_token_using_client_credentials_pass(self):
        def verify_and_return_response(url, headers, data):
            assert url == access_token_url
            assert data.get("scope") == TEST_STRING
            return mocked_repsonse

        response_string = {"access_token": TEST_ACCESS_TOKEN}
        access_token_url = f"{cluster_settings.get_setting(key=auth_utils.COGNITO_DOMAIN_URL_KEY)}/oauth2/token"
        self.monkeypatch.setattr(requests, "post", verify_and_return_response)
        mocked_repsonse = MagicMock()
        mocked_repsonse.json.return_value = response_string

        access_token = token.get_access_token_using_client_credentials(
            TEST_STRING, TEST_STRING, TEST_STRING
        )
        assert access_token == TEST_ACCESS_TOKEN
