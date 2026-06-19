#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import unittest

import pytest
from res.constants import DCV_CONNECTION_TOKEN_VALIDITY_KEY
from res.resources.dcv import session_connection_data, session_token

TEST_USERNAME = "testuser"
TEST_SESSION_ID = "267afc1c-83ef-4735-92a9-03bfecbb97d8"
TEST_OWNER = "testuser"
TEST_SESSION = {
    "owner": TEST_OWNER,
    "dcv_session_id": TEST_SESSION_ID,
}


@pytest.fixture(scope="class")
def monkeypatch_for_class(request):
    request.cls.monkeypatch = pytest.MonkeyPatch()


@pytest.mark.usefixtures("monkeypatch_for_class")
class TestGenerateConnectionToken(unittest.TestCase):

    def setUp(self):
        self.monkeypatch.setattr(
            session_token, "_get_token_expiry_seconds", lambda: 86400
        )
        self.monkeypatch.setattr(
            session_token.table_utils,
            "create_item",
            lambda table_name, item, **kwargs: item,
        )

    def tearDown(self):
        self.monkeypatch.undo()

    def test_token_is_nonempty_string(self):
        token = session_token.generate_connection_token(TEST_USERNAME, TEST_SESSION_ID)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_tokens_are_unique(self):
        token1 = session_token.generate_connection_token(TEST_USERNAME, TEST_SESSION_ID)
        token2 = session_token.generate_connection_token(TEST_USERNAME, TEST_SESSION_ID)
        assert token1 != token2


@pytest.mark.usefixtures("monkeypatch_for_class")
class TestGetTokenExpirySeconds(unittest.TestCase):

    def tearDown(self):
        self.monkeypatch.undo()

    def test_reads_from_cluster_settings(self):
        self.monkeypatch.setattr(
            session_token.cluster_settings,
            "get_setting",
            lambda key: ("10" if key == DCV_CONNECTION_TOKEN_VALIDITY_KEY else None),
        )
        assert session_token._get_token_expiry_seconds() == 600

    def test_falls_back_to_default(self):
        self.monkeypatch.setattr(
            session_token.cluster_settings,
            "get_setting",
            lambda key: None,
        )
        assert session_token._get_token_expiry_seconds() == 86400


@pytest.mark.usefixtures("monkeypatch_for_class")
class TestGetSessionConnectionData(unittest.TestCase):

    def setUp(self):
        self.monkeypatch.setattr(
            session_token, "_get_token_expiry_seconds", lambda: 86400
        )
        self.monkeypatch.setattr(
            session_token.table_utils,
            "create_item",
            lambda table_name, item, **kwargs: item,
        )

    def tearDown(self):
        self.monkeypatch.undo()

    def test_returns_session_info_and_token(self):
        result = session_connection_data.get_session_connection_data(
            TEST_SESSION_ID, TEST_USERNAME
        )
        assert result["webUrlPath"] == "/"
        assert "connectionToken" in result
        assert isinstance(result["connectionToken"], str)
        assert len(result["connectionToken"]) > 0
