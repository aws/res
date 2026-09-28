#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
from unittest.mock import patch

import pytest
from connexion.exceptions import OAuthProblem

from idea.backend.api import auth


# Default cluster-manager client_id used by tests below; tests that want to
# assert the client_id check independently override _resolve_client_id directly.
_CM_CLIENT_ID = "cm-client"


class TestEnforceScope:

    @pytest.fixture(autouse=True)
    def _stub_resolve_client_id(self, monkeypatch):
        """Stub Cognito client_id resolution so the allowlist check has a stable value.

        Scoped to this class so ``TestResolveClientId`` can exercise the real helper
        against patched ``cluster_settings`` / ``aws_utils`` dependencies.
        """
        monkeypatch.setattr(auth, "_resolve_client_id", lambda module_id: _CM_CLIENT_ID)

    def test_none_token_info_rejected(self):
        with pytest.raises(OAuthProblem):
            auth.enforce_scope(None, "any_op")

    def test_token_info_missing_scope_rejected(self):
        with pytest.raises(OAuthProblem):
            auth.enforce_scope({"uid": _CM_CLIENT_ID}, "any_op")

    @patch.dict(auth.OPERATION_SCOPES, {"some_read_op": "read"}, clear=False)
    @patch.dict(os.environ, {"environment_name": "test"}, clear=False)
    def test_service_token_with_required_read_scope(self):
        auth.enforce_scope(
            {"uid": _CM_CLIENT_ID, "scope": ["test-vdc/read"]}, "some_read_op"
        )

    @patch.dict(auth.OPERATION_SCOPES, {"some_write_op": "write"}, clear=False)
    @patch.dict(os.environ, {"environment_name": "test"}, clear=False)
    def test_service_token_with_required_write_scope(self):
        auth.enforce_scope(
            {"uid": _CM_CLIENT_ID, "scope": ["test-vdc/write"]}, "some_write_op"
        )

    @patch.dict(auth.OPERATION_SCOPES, {"some_read_op": "read"}, clear=False)
    @patch.dict(os.environ, {"environment_name": "test"}, clear=False)
    def test_service_token_with_both_read_and_write_scopes_succeeds(self):
        # cluster-manager requests both read and write at token-issue time, so a
        # read-only operation should still pass when the token carries both.
        token_info = {
            "uid": _CM_CLIENT_ID,
            "scope": ["test-vdc/read", "test-vdc/write"],
        }
        auth.enforce_scope(token_info, "some_read_op")

    @patch.dict(auth.OPERATION_SCOPES, {"some_write_op": "write"}, clear=False)
    @patch.dict(os.environ, {"environment_name": "test"}, clear=False)
    def test_service_token_read_scope_rejected_for_write_op(self):
        token_info = {"uid": _CM_CLIENT_ID, "scope": ["test-vdc/read"]}
        with pytest.raises(OAuthProblem) as exc_info:
            auth.enforce_scope(token_info, "some_write_op")
        assert "Insufficient scope" in str(exc_info.value)

    @patch.dict(auth.OPERATION_SCOPES, {"some_read_op": "read"}, clear=False)
    @patch.dict(os.environ, {"environment_name": "test"}, clear=False)
    def test_service_token_write_scope_rejected_for_read_op(self):
        token_info = {"uid": _CM_CLIENT_ID, "scope": ["test-vdc/write"]}
        with pytest.raises(OAuthProblem) as exc_info:
            auth.enforce_scope(token_info, "some_read_op")
        assert "Insufficient scope" in str(exc_info.value)

    @patch.dict(auth.OPERATION_SCOPES, {"some_read_op": "read"}, clear=False)
    @patch.dict(os.environ, {"environment_name": "test"}, clear=False)
    def test_service_token_empty_scope_rejected(self):
        with pytest.raises(OAuthProblem):
            auth.enforce_scope({"uid": _CM_CLIENT_ID, "scope": []}, "some_read_op")

    @patch.dict(auth.OPERATION_SCOPES, {"some_read_op": "read"}, clear=False)
    @patch.dict(os.environ, {"environment_name": "test"}, clear=False)
    def test_service_token_wrong_module_rejected(self):
        token_info = {
            "uid": _CM_CLIENT_ID,
            "scope": ["test-cluster-manager/read"],
        }
        with pytest.raises(OAuthProblem):
            auth.enforce_scope(token_info, "some_read_op")

    @patch.dict(auth.OPERATION_SCOPES, {"some_read_op": "read"}, clear=False)
    @patch.dict(os.environ, {"environment_name": "prod-env"}, clear=False)
    def test_environment_name_mismatch_rejected(self):
        # Token carries scope for "test" env but Lambda runs in "prod-env" —
        # cross-environment token reuse is rejected.
        token_info = {"uid": _CM_CLIENT_ID, "scope": ["test-vdc/read"]}
        with pytest.raises(OAuthProblem):
            auth.enforce_scope(token_info, "some_read_op")

    def test_unknown_operation_id_raises_oauth_problem(self):
        token_info = {"uid": _CM_CLIENT_ID, "scope": ["test-vdc/read"]}
        with pytest.raises(OAuthProblem) as exc_info:
            auth.enforce_scope(token_info, "no_such_operation")
        assert "Insufficient scope" in str(exc_info.value)

    @patch.dict(auth.OPERATION_SCOPES, {"some_read_op": "read"}, clear=False)
    @patch.dict(os.environ, {"environment_name": "test"}, clear=False)
    def test_unauthorized_client_id_rejected(self, monkeypatch):
        """Token carries the right scope but client_id is not on the allowlist."""
        monkeypatch.setattr(auth, "_resolve_client_id", lambda module_id: _CM_CLIENT_ID)
        token_info = {"uid": "rogue-client", "scope": ["test-vdc/read"]}
        with pytest.raises(OAuthProblem) as exc_info:
            auth.enforce_scope(token_info, "some_read_op")
        assert "Unauthorized client" in str(exc_info.value)

    @patch.dict(auth.OPERATION_SCOPES, {"some_read_op": "read"}, clear=False)
    @patch.dict(os.environ, {"environment_name": "test"}, clear=False)
    def test_missing_uid_rejected(self, monkeypatch):
        """Token info without a uid should not silently pass the allowlist check."""
        monkeypatch.setattr(auth, "_resolve_client_id", lambda module_id: _CM_CLIENT_ID)
        token_info = {"scope": ["test-vdc/read"]}
        with pytest.raises(OAuthProblem):
            auth.enforce_scope(token_info, "some_read_op")


class TestOperationScopesRegistry:

    def test_migrated_operations_registered(self):
        """Operations migrating to service-token auth must be registered."""
        assert auth.OPERATION_SCOPES["batch_create_session"] == "write"
        assert auth.OPERATION_SCOPES["list_sessions"] == "read"
        assert auth.OPERATION_SCOPES["batch_stop_session"] == "write"
        assert auth.OPERATION_SCOPES["batch_delete_session"] == "write"
        assert auth.OPERATION_SCOPES["list_software_stacks"] == "read"
        assert auth.OPERATION_SCOPES["get_software_stack"] == "read"
        assert auth.OPERATION_SCOPES["create_software_stack"] == "write"
        assert auth.OPERATION_SCOPES["update_software_stack"] == "write"
        assert auth.OPERATION_SCOPES["delete_software_stack"] == "write"
        assert auth.OPERATION_SCOPES["get_permission_profile"] == "read"
        assert auth.OPERATION_SCOPES["create_permission_profile"] == "write"
        assert auth.OPERATION_SCOPES["delete_permission_profile"] == "write"


class TestResolveClientId:

    @pytest.fixture(autouse=True)
    def _clear_cache(self):
        """``_resolve_client_id`` is ``lru_cache``-wrapped; clear between tests."""
        auth._resolve_client_id.cache_clear()
        yield
        auth._resolve_client_id.cache_clear()

    def test_resolve_client_id_reads_cluster_setting_and_secret(self, monkeypatch):
        monkeypatch.setattr(
            auth.cluster_settings,
            "get_setting",
            lambda key: f"arn:{key}" if key == "cluster-manager.client_id" else None,
        )
        monkeypatch.setattr(
            auth.aws_utils,
            "get_secret_string",
            lambda arn: "resolved-cm-client-id" if arn == "arn:cluster-manager.client_id" else None,
        )
        assert auth._resolve_client_id("cluster-manager") == "resolved-cm-client-id"

    def test_resolve_client_id_caches_results(self, monkeypatch):
        """Second call for the same module reuses the cached value rather than
        hitting cluster_settings + Secrets Manager again."""
        call_counts = {"settings": 0, "secrets": 0}

        def fake_get_setting(key):
            call_counts["settings"] += 1
            return "arn:cm-id"

        def fake_get_secret(arn):
            call_counts["secrets"] += 1
            return "cm-client-id"

        monkeypatch.setattr(auth.cluster_settings, "get_setting", fake_get_setting)
        monkeypatch.setattr(auth.aws_utils, "get_secret_string", fake_get_secret)

        auth._resolve_client_id("cluster-manager")
        auth._resolve_client_id("cluster-manager")
        auth._resolve_client_id("cluster-manager")

        assert call_counts == {"settings": 1, "secrets": 1}

    def test_resolve_client_id_wraps_dependency_failures_in_oauth_problem(
        self, monkeypatch
    ):
        """A cluster_settings or Secrets Manager failure must surface as
        ``OAuthProblem("Service configuration error")`` so internal details
        (ARNs, table names) do not leak in the error response."""

        def boom(*args, **kwargs):
            raise RuntimeError("internal arn: arn:aws:secretsmanager:...")

        monkeypatch.setattr(auth.cluster_settings, "get_setting", boom)

        with pytest.raises(OAuthProblem) as exc_info:
            auth._resolve_client_id("cluster-manager")
        assert "Service configuration error" in str(exc_info.value)
        # the underlying ARN must not leak through the OAuthProblem
        assert "arn:aws:secretsmanager" not in str(exc_info.value)
