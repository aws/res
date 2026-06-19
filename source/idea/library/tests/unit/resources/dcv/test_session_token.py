#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import time

import pytest
from res.constants import (
    DCV_CONNECTION_TOKEN_DB_HASH_KEY,
    DCV_CONNECTION_TOKEN_DB_SESSION_ID_KEY,
    DCV_CONNECTION_TOKEN_DB_TTL_KEY,
    DCV_CONNECTION_TOKEN_DB_USERNAME_KEY,
    DCV_CONNECTION_TOKEN_TABLE_NAME,
)
from res.resources.dcv import session_token

TEST_USERNAME = "testuser"
TEST_SESSION_ID = "ses-abc123"


@pytest.fixture(autouse=True)
def mock_deps(monkeypatch):
    monkeypatch.setattr(session_token, "_get_token_expiry_seconds", lambda: 3600)


class TestGenerateConnectionToken:

    def test_generates_token_and_stores_in_ddb(self, monkeypatch):
        stored_items = []
        monkeypatch.setattr(
            session_token.table_utils,
            "create_item",
            lambda table_name, item, **kwargs: stored_items.append((table_name, item))
            or item,
        )

        token = session_token.generate_connection_token(TEST_USERNAME, TEST_SESSION_ID)

        assert len(token) > 0
        assert len(stored_items) == 1
        table_name, item = stored_items[0]
        assert table_name == DCV_CONNECTION_TOKEN_TABLE_NAME
        assert item[DCV_CONNECTION_TOKEN_DB_HASH_KEY] == token
        assert item[DCV_CONNECTION_TOKEN_DB_SESSION_ID_KEY] == TEST_SESSION_ID
        assert item[DCV_CONNECTION_TOKEN_DB_USERNAME_KEY] == TEST_USERNAME
        assert item[DCV_CONNECTION_TOKEN_DB_TTL_KEY] > int(time.time())

    def test_token_is_unique_each_call(self, monkeypatch):
        monkeypatch.setattr(
            session_token.table_utils,
            "create_item",
            lambda table_name, item, **kwargs: item,
        )

        token1 = session_token.generate_connection_token(TEST_USERNAME, TEST_SESSION_ID)
        token2 = session_token.generate_connection_token(TEST_USERNAME, TEST_SESSION_ID)
        assert token1 != token2

    def test_token_expiry_uses_configured_value(self, monkeypatch):
        stored_items = []
        monkeypatch.setattr(
            session_token.table_utils,
            "create_item",
            lambda table_name, item, **kwargs: stored_items.append(item) or item,
        )

        before = int(time.time())
        session_token.generate_connection_token(TEST_USERNAME, TEST_SESSION_ID)
        after = int(time.time())

        ttl = stored_items[0][DCV_CONNECTION_TOKEN_DB_TTL_KEY]
        assert before + 3600 <= ttl <= after + 3600


class TestLookupConnectionToken:

    def _make_valid_item(self, token="tok123"):
        return {
            DCV_CONNECTION_TOKEN_DB_HASH_KEY: token,
            DCV_CONNECTION_TOKEN_DB_SESSION_ID_KEY: TEST_SESSION_ID,
            DCV_CONNECTION_TOKEN_DB_USERNAME_KEY: TEST_USERNAME,
            DCV_CONNECTION_TOKEN_DB_TTL_KEY: int(time.time()) + 3600,
        }

    def test_returns_item_on_valid_lookup(self, monkeypatch):
        item = self._make_valid_item()
        monkeypatch.setattr(
            session_token.table_utils, "get_item", lambda table, key: item
        )

        result = session_token.lookup_connection_token("tok123", TEST_SESSION_ID)
        assert result == item

    def test_returns_none_when_not_found(self, monkeypatch):
        monkeypatch.setattr(
            session_token.table_utils, "get_item", lambda table, key: None
        )

        result = session_token.lookup_connection_token("missing", TEST_SESSION_ID)
        assert result is None

    def test_returns_none_on_session_id_mismatch(self, monkeypatch):
        item = self._make_valid_item()
        monkeypatch.setattr(
            session_token.table_utils, "get_item", lambda table, key: item
        )

        result = session_token.lookup_connection_token("tok123", "different-session")
        assert result is None

    def test_returns_none_on_expired_token(self, monkeypatch):
        item = self._make_valid_item()
        item[DCV_CONNECTION_TOKEN_DB_TTL_KEY] = int(time.time()) - 100
        monkeypatch.setattr(
            session_token.table_utils, "get_item", lambda table, key: item
        )

        result = session_token.lookup_connection_token("tok123", TEST_SESSION_ID)
        assert result is None
