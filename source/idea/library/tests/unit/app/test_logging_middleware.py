#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from res.app.middleware.logging_middleware import redact_sensitive_fields


class TestRedactSensitiveFields:

    def test_redacts_authentication_token(self):
        result = redact_sensitive_fields(
            '{"authentication_token": "secret123", "session_id": "ses-1"}'
        )
        assert '"authentication_token": "***"' in result
        assert "secret123" not in result
        assert "ses-1" in result

    def test_redacts_camel_case_variant(self):
        result = redact_sensitive_fields('{"authenticationToken": "secret123"}')
        assert "secret123" not in result

    def test_leaves_non_sensitive_fields_unchanged(self):
        result = redact_sensitive_fields(
            '{"session_id": "ses-1", "client_address": "10.0.0.1"}'
        )
        assert "ses-1" in result
        assert "10.0.0.1" in result

    def test_returns_non_json_unchanged(self):
        assert redact_sensitive_fields("not-json") == "not-json"

    def test_returns_non_dict_json_unchanged(self):
        assert redact_sensitive_fields("[1, 2, 3]") == "[1, 2, 3]"

    def test_handles_empty_string(self):
        assert redact_sensitive_fields("") == ""
