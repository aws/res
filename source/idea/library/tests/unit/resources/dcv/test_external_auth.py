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
from res.exceptions import SessionAccessDenied
from res.resources.dcv import external_auth, session_token

TEST_USERNAME = "testuser"
TEST_SESSION_ID = "ses-abc123"
OTHER_SESSION_ID = "ses-other-999"


def _make_token_record(
    username=TEST_USERNAME, session_id=TEST_SESSION_ID, expired=False
):
    ttl = int(time.time()) - 100 if expired else int(time.time()) + 3600
    return {
        DCV_CONNECTION_TOKEN_DB_HASH_KEY: "test-token",
        DCV_CONNECTION_TOKEN_DB_SESSION_ID_KEY: session_id,
        DCV_CONNECTION_TOKEN_DB_USERNAME_KEY: username,
        DCV_CONNECTION_TOKEN_DB_TTL_KEY: ttl,
    }


class TestValidateConnectionToken:

    def test_valid_token_returns_username(self, monkeypatch):
        record = _make_token_record()
        monkeypatch.setattr(
            session_token, "lookup_connection_token", lambda token, sid: record
        )
        monkeypatch.setattr(
            "res.resources.session_permissions.validate_session_access",
            lambda sid, user: {"owner": user, "dcv_session_id": sid},
        )

        username, error = external_auth.validate_connection_token(
            "test-token", TEST_SESSION_ID
        )
        assert username == TEST_USERNAME
        assert error is None

    def test_invalid_token_returns_error(self, monkeypatch):
        monkeypatch.setattr(
            session_token, "lookup_connection_token", lambda token, sid: None
        )

        username, error = external_auth.validate_connection_token(
            "bad-token", TEST_SESSION_ID
        )
        assert username is None
        assert error == "Authentication failed"

    def test_expired_token_returns_error(self, monkeypatch):
        monkeypatch.setattr(
            session_token, "lookup_connection_token", lambda token, sid: None
        )

        username, error = external_auth.validate_connection_token(
            "expired-token", TEST_SESSION_ID
        )
        assert username is None
        assert error == "Authentication failed"

    def test_empty_username_returns_error(self, monkeypatch):
        record = _make_token_record(username="")
        monkeypatch.setattr(
            session_token, "lookup_connection_token", lambda token, sid: record
        )

        username, error = external_auth.validate_connection_token(
            "test-token", TEST_SESSION_ID
        )
        assert username is None
        assert error == "Authentication failed"

    def test_session_access_denied_returns_error(self, monkeypatch):
        record = _make_token_record()
        monkeypatch.setattr(
            session_token, "lookup_connection_token", lambda token, sid: record
        )

        def deny_access(sid, user):
            raise SessionAccessDenied("Session not found or access denied")

        monkeypatch.setattr(
            "res.resources.session_permissions.validate_session_access", deny_access
        )

        username, error = external_auth.validate_connection_token(
            "test-token", TEST_SESSION_ID
        )
        assert username is None
        assert error == "Authentication failed"


class TestTokenSessionBinding:
    """Verify that a bearer token issued for one session cannot authenticate to a different session.

    The idea_session_id is passed via the URL path (from the DCV host's
    auth-token-verifier config). Session binding is enforced by comparing
    the stored session_id in the token record against this value.
    """

    @pytest.fixture(autouse=True)
    def setup_ddb_stub(self, monkeypatch):
        """Replace table_utils with an in-memory store so generate + lookup work together."""
        self.token_store = {}

        def fake_create_item(table_name, item, **kwargs):
            assert table_name == DCV_CONNECTION_TOKEN_TABLE_NAME
            self.token_store[item[DCV_CONNECTION_TOKEN_DB_HASH_KEY]] = item
            return item

        def fake_get_item(table_name, key):
            assert table_name == DCV_CONNECTION_TOKEN_TABLE_NAME
            return self.token_store.get(key[DCV_CONNECTION_TOKEN_DB_HASH_KEY])

        monkeypatch.setattr(session_token.table_utils, "create_item", fake_create_item)
        monkeypatch.setattr(session_token.table_utils, "get_item", fake_get_item)
        monkeypatch.setattr(session_token, "_get_token_expiry_seconds", lambda: 3600)
        monkeypatch.setattr(
            "res.resources.session_permissions.validate_session_access",
            lambda sid, user: {"owner": user},
        )

    def test_token_authenticates_to_its_own_session(self):
        token = session_token.generate_connection_token(TEST_USERNAME, TEST_SESSION_ID)

        username, error = external_auth.validate_connection_token(
            token, TEST_SESSION_ID
        )

        assert username == TEST_USERNAME
        assert error is None

    def test_token_rejected_for_different_session(self):
        token = session_token.generate_connection_token(TEST_USERNAME, TEST_SESSION_ID)

        username, error = external_auth.validate_connection_token(
            token, OTHER_SESSION_ID
        )

        assert username is None
        assert error == "Authentication failed"

    def test_two_users_tokens_are_isolated(self):
        token_a = session_token.generate_connection_token("alice", TEST_SESSION_ID)
        token_b = session_token.generate_connection_token("bob", OTHER_SESSION_ID)

        user_a, err_a = external_auth.validate_connection_token(
            token_a, TEST_SESSION_ID
        )
        assert user_a == "alice"
        assert err_a is None

        user_b, err_b = external_auth.validate_connection_token(
            token_b, OTHER_SESSION_ID
        )
        assert user_b == "bob"
        assert err_b is None

        # alice's token must not work for bob's session
        user_cross, err_cross = external_auth.validate_connection_token(
            token_a, OTHER_SESSION_ID
        )
        assert user_cross is None
        assert err_cross == "Authentication failed"

        # bob's token must not work for alice's session
        user_cross2, err_cross2 = external_auth.validate_connection_token(
            token_b, TEST_SESSION_ID
        )
        assert user_cross2 is None
        assert err_cross2 == "Authentication failed"


class TestTokenExpiration:
    """Verify that expired tokens are rejected even when the record exists in DynamoDB."""

    @pytest.fixture(autouse=True)
    def setup_ddb_stub(self, monkeypatch):
        self.token_store = {}

        def fake_create_item(table_name, item, **kwargs):
            self.token_store[item[DCV_CONNECTION_TOKEN_DB_HASH_KEY]] = item
            return item

        def fake_get_item(table_name, key):
            return self.token_store.get(key[DCV_CONNECTION_TOKEN_DB_HASH_KEY])

        monkeypatch.setattr(session_token.table_utils, "create_item", fake_create_item)
        monkeypatch.setattr(session_token.table_utils, "get_item", fake_get_item)
        monkeypatch.setattr(
            "res.resources.session_permissions.validate_session_access",
            lambda sid, user: {"owner": user},
        )

    def test_token_valid_before_expiry(self, monkeypatch):
        monkeypatch.setattr(session_token, "_get_token_expiry_seconds", lambda: 3600)
        token = session_token.generate_connection_token(TEST_USERNAME, TEST_SESSION_ID)

        username, error = external_auth.validate_connection_token(
            token, TEST_SESSION_ID
        )
        assert username == TEST_USERNAME
        assert error is None

    def test_token_rejected_after_expiry(self, monkeypatch):
        monkeypatch.setattr(session_token, "_get_token_expiry_seconds", lambda: 3600)
        token = session_token.generate_connection_token(TEST_USERNAME, TEST_SESSION_ID)

        record = self.token_store[token]
        record[DCV_CONNECTION_TOKEN_DB_TTL_KEY] = int(time.time()) - 1

        username, error = external_auth.validate_connection_token(
            token, TEST_SESSION_ID
        )
        assert username is None
        assert error == "Authentication failed"

    def test_already_expired_token_immediately_invalid(self, monkeypatch):
        monkeypatch.setattr(session_token, "_get_token_expiry_seconds", lambda: 3600)
        token = session_token.generate_connection_token(TEST_USERNAME, TEST_SESSION_ID)

        record = self.token_store[token]
        record[DCV_CONNECTION_TOKEN_DB_TTL_KEY] = int(time.time()) - 3600

        username, error = external_auth.validate_connection_token(
            token, TEST_SESSION_ID
        )
        assert username is None
        assert error == "Authentication failed"
