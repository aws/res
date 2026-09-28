#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
from unittest.mock import MagicMock

import pytest
import requests
from res.clients.api_client import res_api_client as res_api_client_module
from res.clients.api_client.res_api_client import ResApiClient


def _build_response(status_code=200, json_data=None, text=None):
    response = MagicMock(spec=requests.Response)
    response.status_code = status_code
    response.text = text if text is not None else json.dumps(json_data or {})
    if json_data is not None:
        response.json.return_value = json_data
    else:
        response.json.side_effect = json.JSONDecodeError("err", "", 0)
    response.raise_for_status = MagicMock()
    return response


@pytest.fixture
def stub_token(monkeypatch):
    """Stub the RES library token resource so _get_access_token returns a known value."""
    captured = {}

    def fake_get_token(client_id, client_secret, scope):
        captured["client_id"] = client_id
        captured["client_secret"] = client_secret
        captured["scope"] = scope
        return captured.get("return_value", "test-token")

    monkeypatch.setattr(
        res_api_client_module.token,
        "get_access_token_using_client_credentials",
        fake_get_token,
    )
    return captured


@pytest.fixture
def client(stub_token):
    return ResApiClient(
        endpoint="https://internal-alb.example.com",
        client_id="cm-client-id",
        client_secret="cm-client-secret",
        scopes=["env-vdc/read", "env-vdc/write"],
    )


class TestResApiClient:

    def test_init_sets_default_headers_and_disables_ssl(self, stub_token):
        """constructor sets default JSON headers, disables SSL verify, defers token fetch"""
        client = ResApiClient(
            endpoint="https://internal-alb.example.com",
            client_id="cid",
            client_secret="csec",
            scopes=["env-vdc/read"],
        )
        assert client._endpoint == "https://internal-alb.example.com"
        assert client._session.verify is False
        assert (
            client._session.headers["Content-Type"] == "application/json;charset=UTF-8"
        )
        assert client._session.headers["Accept"] == "application/json"
        # token resource is not invoked at construction time
        assert stub_token == {}

    def test_make_request_sets_authorization_header_from_token_resource(
        self, client, stub_token, monkeypatch
    ):
        """_make_request resolves cluster-manager creds, requests VDC scopes, sets Bearer header"""
        stub_token["return_value"] = "fresh-token"
        captured = {}

        def fake_request(method, url, verify, json, timeout):
            captured["headers"] = dict(client._session.headers)
            return _build_response(json_data={"ok": True})

        monkeypatch.setattr(client._session, "request", fake_request)

        client._make_request("GET", "/res/virtual-desktop/sessions")

        assert captured["headers"]["Authorization"] == "Bearer fresh-token"
        assert stub_token["client_id"] == "cm-client-id"
        assert stub_token["client_secret"] == "cm-client-secret"
        assert stub_token["scope"] == "env-vdc/read env-vdc/write"

    def test_make_request_refreshes_token_on_each_request(self, client, monkeypatch):
        """token resource is invoked on every request so callers always send a fresh token"""
        tokens = iter(["token-1", "token-2"])

        monkeypatch.setattr(
            res_api_client_module.token,
            "get_access_token_using_client_credentials",
            lambda cid, csec, scope: next(tokens),
        )

        seen_tokens = []

        def fake_request(method, url, verify, json, timeout):
            seen_tokens.append(client._session.headers["Authorization"])
            return _build_response(json_data={})

        monkeypatch.setattr(client._session, "request", fake_request)

        client._make_request("GET", "/path-1")
        client._make_request("GET", "/path-2")

        assert seen_tokens == ["Bearer token-1", "Bearer token-2"]

    def test_make_request_serializes_request_content_via_to_dict(
        self, client, monkeypatch
    ):
        """request body is the model's to_dict() output, sent to the joined URL"""
        request_content = MagicMock()
        request_content.to_dict.return_value = {"keep": "value", "nested": {"b": 2}}
        captured = {}

        def fake_request(method, url, verify, json, timeout):
            captured["json"] = json
            captured["method"] = method
            captured["url"] = url
            return _build_response(json_data={})

        monkeypatch.setattr(client._session, "request", fake_request)

        client._make_request("POST", "/path", request_content=request_content)

        request_content.to_dict.assert_called_once_with()
        assert captured["method"] == "POST"
        assert captured["url"] == "https://internal-alb.example.com/path"
        assert captured["json"] == {"keep": "value", "nested": {"b": 2}}

    def test_make_request_strips_none_values_from_request_body(
        self, client, monkeypatch
    ):
        """``None`` fields from to_dict() must be stripped before serialization
        so the backend schema validator does not reject sparse model objects."""
        request_content = MagicMock()
        request_content.to_dict.return_value = {
            "idea_session_id": "s1",
            "owner": "user1",
            "force": True,
            "server": None,
            "project": {"project_id": "p1", "title": None},
            "tags": [None, "keep"],
        }
        captured = {}

        def fake_request(method, url, verify, json, timeout):
            captured["json"] = json
            return _build_response(json_data={})

        monkeypatch.setattr(client._session, "request", fake_request)

        client._make_request("POST", "/path", request_content=request_content)

        assert captured["json"] == {
            "idea_session_id": "s1",
            "owner": "user1",
            "force": True,
            "project": {"project_id": "p1"},
            "tags": ["keep"],
        }

    def test_make_request_sends_no_body_when_request_content_is_none(
        self, client, monkeypatch
    ):
        """request body is None when no request_content is provided"""
        captured = {}

        def fake_request(method, url, verify, json, timeout):
            captured["json"] = json
            return _build_response(json_data={})

        monkeypatch.setattr(client._session, "request", fake_request)

        client._make_request("GET", "/path")

        assert captured["json"] is None

    def test_make_request_uses_default_timeout(self, client, monkeypatch):
        """default per-request timeout is forwarded to requests"""
        captured = {}

        def fake_request(method, url, verify, json, timeout):
            captured["timeout"] = timeout
            return _build_response(json_data={})

        monkeypatch.setattr(client._session, "request", fake_request)

        client._make_request("GET", "/path")
        assert (
            captured["timeout"] == res_api_client_module.DEFAULT_REQUEST_TIMEOUT_SECONDS
        )

    def test_make_request_uses_overridden_timeout(self, stub_token, monkeypatch):
        """timeout kwarg on the constructor is forwarded to requests"""
        client = ResApiClient(
            endpoint="https://internal-alb.example.com",
            client_id="cid",
            client_secret="csec",
            scopes=["env-vdc/read"],
            timeout=5,
        )
        captured = {}

        def fake_request(method, url, verify, json, timeout):
            captured["timeout"] = timeout
            return _build_response(json_data={})

        monkeypatch.setattr(client._session, "request", fake_request)

        client._make_request("GET", "/path")
        assert captured["timeout"] == 5

    def test_make_request_deserializes_with_response_model_class(
        self, client, monkeypatch
    ):
        """response_model_class.from_dict() is used to deserialize JSON object responses"""
        response_payload = {"id": "abc"}
        monkeypatch.setattr(
            client._session,
            "request",
            lambda method, url, verify, json, timeout: _build_response(
                json_data=response_payload
            ),
        )

        response_model_class = MagicMock()
        response_model_class.from_dict.return_value = "deserialized"

        result = client._make_request(
            "GET", "/path", response_model_class=response_model_class
        )

        response_model_class.from_dict.assert_called_once_with(response_payload)
        assert result == "deserialized"

    def test_make_request_returns_raw_json_when_no_response_model_class(
        self, client, monkeypatch
    ):
        """parsed JSON dict is returned as-is when no response_model_class is given"""
        monkeypatch.setattr(
            client._session,
            "request",
            lambda method, url, verify, json, timeout: _build_response(
                json_data={"k": "v"}
            ),
        )

        result = client._make_request("GET", "/path")
        assert result == {"k": "v"}

    def test_make_request_returns_raw_json_when_response_is_list(
        self, client, monkeypatch
    ):
        """non-dict JSON responses bypass response_model_class deserialization"""
        monkeypatch.setattr(
            client._session,
            "request",
            lambda method, url, verify, json, timeout: _build_response(
                json_data=[1, 2, 3]
            ),
        )

        response_model_class = MagicMock()

        result = client._make_request(
            "GET", "/path", response_model_class=response_model_class
        )
        assert result == [1, 2, 3]
        response_model_class.from_dict.assert_not_called()

    def test_make_request_returns_text_when_response_is_not_json(
        self, client, monkeypatch
    ):
        """falls back to response.text on JSONDecodeError"""
        monkeypatch.setattr(
            client._session,
            "request",
            lambda method, url, verify, json, timeout: _build_response(
                text="plain text"
            ),
        )

        result = client._make_request("GET", "/path")
        assert result == "plain text"

    def test_make_request_uppercases_http_method(self, client, monkeypatch):
        """lowercase method names are normalized to uppercase"""
        captured = {}

        def fake_request(method, url, verify, json, timeout):
            captured["method"] = method
            return _build_response(json_data={})

        monkeypatch.setattr(client._session, "request", fake_request)

        client._make_request("post", "/path")
        assert captured["method"] == "POST"

    def test_make_request_propagates_request_exception(self, client, monkeypatch):
        """RequestException raised by the underlying session is propagated"""
        error_response = MagicMock()
        error_response.status_code = 500
        error_response.text = "boom"
        err = requests.RequestException("boom")
        err.response = error_response

        def fake_request(method, url, verify, json, timeout):
            raise err

        monkeypatch.setattr(client._session, "request", fake_request)

        with pytest.raises(requests.RequestException):
            client._make_request("GET", "/path")

    def test_make_request_raises_for_status_propagates_http_error(
        self, client, monkeypatch
    ):
        """response.raise_for_status() errors propagate to the caller"""
        response = _build_response(json_data={})
        response.raise_for_status.side_effect = requests.HTTPError("403")

        monkeypatch.setattr(
            client._session,
            "request",
            lambda method, url, verify, json, timeout: response,
        )

        with pytest.raises(requests.HTTPError):
            client._make_request("GET", "/path")

    def test_list_sessions_builds_query_params(self, client, monkeypatch):
        """list_sessions appends provided filters as URL query params"""
        captured = {}

        def fake_request(method, url, verify, json, timeout):
            captured["method"] = method
            captured["url"] = url
            return _build_response(json_data={"listing": [], "nextToken": None})

        monkeypatch.setattr(client._session, "request", fake_request)

        client.list_sessions(
            state="READY",
            base_os="amazonlinux2",
            session_name="my-session",
            stack_id="ss-1",
            owner="alice",
            next_token="t",
        )

        assert captured["method"] == "GET"
        assert captured["url"].startswith(
            "https://internal-alb.example.com/res/virtual-desktop/sessions?"
        )
        for fragment in (
            "state=READY",
            "baseOs=amazonlinux2",
            "sessionName=my-session",
            "stackId=ss-1",
            "owner=alice",
            "nextToken=t",
        ):
            assert fragment in captured["url"]

    def test_list_sessions_no_params(self, client, monkeypatch):
        """list_sessions without filters hits the bare path"""
        captured = {}

        def fake_request(method, url, verify, json, timeout):
            captured["url"] = url
            return _build_response(json_data={"listing": []})

        monkeypatch.setattr(client._session, "request", fake_request)

        client.list_sessions()
        assert (
            captured["url"]
            == "https://internal-alb.example.com/res/virtual-desktop/sessions"
        )

    def test_list_sessions_url_encodes_special_characters(self, client, monkeypatch):
        """Filter values with URL-special characters must be percent-encoded
        so the URL is well-formed and not vulnerable to injection."""
        captured = {}

        def fake_request(method, url, verify, json, timeout):
            captured["url"] = url
            return _build_response(json_data={"listing": []})

        monkeypatch.setattr(client._session, "request", fake_request)

        client.list_sessions(
            session_name="my session & friends",
            owner="user@example.com",
        )

        # raw special chars must not appear in the URL
        assert "my session & friends" not in captured["url"]
        # percent-encoded forms must be present
        assert "sessionName=my+session+%26+friends" in captured["url"]
        assert "owner=user%40example.com" in captured["url"]

    def test_batch_delete_session_posts_to_delete_path(self, client, monkeypatch):
        """batch_delete_session POSTs to /sessions/delete with the request payload"""
        captured = {}

        def fake_request(method, url, verify, json, timeout):
            captured["method"] = method
            captured["url"] = url
            captured["json"] = json
            return _build_response(
                json_data={"successful_list": [], "unsuccessful_list": []}
            )

        monkeypatch.setattr(client._session, "request", fake_request)

        request_content = MagicMock()
        request_content.to_dict.return_value = {"sessions": [{"idea_session_id": "s1"}]}

        client.batch_delete_session(request_content)

        assert captured["method"] == "POST"
        assert (
            captured["url"]
            == "https://internal-alb.example.com/res/virtual-desktop/sessions/delete"
        )
        assert captured["json"] == {"sessions": [{"idea_session_id": "s1"}]}

    def test_batch_stop_session_posts_to_stop_path(self, client, monkeypatch):
        """batch_stop_session POSTs to /sessions/stop with the request payload"""
        captured = {}

        def fake_request(method, url, verify, json, timeout):
            captured["method"] = method
            captured["url"] = url
            captured["json"] = json
            return _build_response(
                json_data={"successful_list": [], "unsuccessful_list": []}
            )

        monkeypatch.setattr(client._session, "request", fake_request)

        request_content = MagicMock()
        request_content.to_dict.return_value = {"sessions": [{"idea_session_id": "s2"}]}

        client.batch_stop_session(request_content)

        assert captured["method"] == "POST"
        assert (
            captured["url"]
            == "https://internal-alb.example.com/res/virtual-desktop/sessions/stop"
        )
        assert captured["json"] == {"sessions": [{"idea_session_id": "s2"}]}

    def test_batch_start_session_posts_to_start_path(self, client, monkeypatch):
        """batch_start_session POSTs to /sessions/start with the request payload"""
        captured = {}

        def fake_request(method, url, verify, json, timeout):
            captured["method"] = method
            captured["url"] = url
            captured["json"] = json
            return _build_response(
                json_data={"successful_list": [], "unsuccessful_list": []}
            )

        monkeypatch.setattr(client._session, "request", fake_request)

        request_content = MagicMock()
        request_content.to_dict.return_value = {"sessions": [{"idea_session_id": "s3"}]}

        client.batch_start_session(request_content)

        assert captured["method"] == "POST"
        assert (
            captured["url"]
            == "https://internal-alb.example.com/res/virtual-desktop/sessions/start"
        )
        assert captured["json"] == {"sessions": [{"idea_session_id": "s3"}]}

    def test_list_all_sessions_paginates(self, client, monkeypatch):
        """list_all_sessions iterates until nextToken is None."""
        call_count = {"n": 0}

        def fake_request(method, url, verify, json, timeout):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return _build_response(
                    json_data={
                        "listing": [{"idea_session_id": "s1"}],
                        "nextToken": "tok2",
                    }
                )
            return _build_response(
                json_data={"listing": [{"idea_session_id": "s2"}], "nextToken": None}
            )

        monkeypatch.setattr(client._session, "request", fake_request)

        results = client.list_all_sessions(owner="user1")
        assert len(results) == 2
        assert call_count["n"] == 2

    def test_list_all_sessions_empty(self, client, monkeypatch):
        """list_all_sessions returns empty list when no sessions."""

        def fake_request(method, url, verify, json, timeout):
            return _build_response(json_data={"listing": [], "nextToken": None})

        monkeypatch.setattr(client._session, "request", fake_request)

        results = client.list_all_sessions()
        assert results == []

    def test_create_software_stack_posts_to_software_stack_path(
        self, client, monkeypatch
    ):
        """create_software_stack POSTs to /software-stack with the request payload"""
        captured = {}

        def fake_request(method, url, verify, json, timeout):
            captured["method"] = method
            captured["url"] = url
            captured["json"] = json
            return _build_response(json_data={"software_stack": {"stack_id": "ss-1"}})

        monkeypatch.setattr(client._session, "request", fake_request)

        request_content = MagicMock()
        request_content.to_dict.return_value = {
            "software_stack": {"stack_id": "ss-1", "name": "ss"}
        }

        client.create_software_stack(request_content)

        assert captured["method"] == "POST"
        assert (
            captured["url"]
            == "https://internal-alb.example.com/res/virtual-desktop/software-stacks"
        )
        assert captured["json"] == {
            "software_stack": {"stack_id": "ss-1", "name": "ss"}
        }

    def test_update_software_stack_puts_to_software_stack_path(
        self, client, monkeypatch
    ):
        """update_software_stack PUTs to /software-stack/{stack_id} with the request payload"""
        captured = {}

        def fake_request(method, url, verify, json, timeout):
            captured["method"] = method
            captured["url"] = url
            captured["json"] = json
            return _build_response(json_data={"software_stack": {"stack_id": "ss-1"}})

        monkeypatch.setattr(client._session, "request", fake_request)

        request_content = MagicMock()
        request_content.to_dict.return_value = {
            "software_stack": {"stack_id": "ss-1", "name": "ss-updated"}
        }

        client.update_software_stack(stack_id="ss-1", request_content=request_content)

        assert captured["method"] == "PUT"
        assert (
            captured["url"]
            == "https://internal-alb.example.com/res/virtual-desktop/software-stacks/ss-1"
        )
        assert captured["json"] == {
            "software_stack": {"stack_id": "ss-1", "name": "ss-updated"}
        }

    def test_delete_software_stack_deletes_software_stack_path(
        self, client, monkeypatch
    ):
        """delete_software_stack DELETEs /software-stack/{stack_id} with base_os payload"""
        captured = {}

        def fake_request(method, url, verify, json, timeout):
            captured["method"] = method
            captured["url"] = url
            captured["json"] = json
            return _build_response(json_data={"success": True})

        monkeypatch.setattr(client._session, "request", fake_request)

        request_content = MagicMock()
        request_content.to_dict.return_value = {"base_os": "amazonlinux2"}

        client.delete_software_stack(stack_id="ss-1", request_content=request_content)

        assert captured["method"] == "DELETE"
        assert (
            captured["url"]
            == "https://internal-alb.example.com/res/virtual-desktop/software-stacks/ss-1"
        )
        assert captured["json"] == {"base_os": "amazonlinux2"}

    def test_get_software_stack_gets_with_base_os_query_param(
        self, client, monkeypatch
    ):
        """get_software_stack GETs /software-stack/{stack_id}?baseOs=... with URL-encoded value"""
        captured = {}

        def fake_request(method, url, verify, json, timeout):
            captured["method"] = method
            captured["url"] = url
            return _build_response(json_data={"software_stack": {"stack_id": "ss-1"}})

        monkeypatch.setattr(client._session, "request", fake_request)

        client.get_software_stack(stack_id="ss-1", base_os="amazonlinux2")

        assert captured["method"] == "GET"
        assert (
            captured["url"]
            == "https://internal-alb.example.com/res/virtual-desktop/software-stacks/ss-1?baseOs=amazonlinux2"
        )

    def test_list_software_stacks_builds_query_params(self, client, monkeypatch):
        """list_software_stacks appends provided filters as URL query params"""
        captured = {}

        def fake_request(method, url, verify, json, timeout):
            captured["method"] = method
            captured["url"] = url
            return _build_response(json_data={"listing": []})

        monkeypatch.setattr(client._session, "request", fake_request)

        client.list_software_stacks(
            project_id="p-1",
            base_os="amazonlinux2",
            software_stack_name="my stack",
            next_token="t",
        )

        assert captured["method"] == "GET"
        assert captured["url"].startswith(
            "https://internal-alb.example.com/res/virtual-desktop/software-stacks?"
        )
        for fragment in (
            "projectId=p-1",
            "baseOs=amazonlinux2",
            "softwareStackName=my+stack",
            "nextToken=t",
        ):
            assert fragment in captured["url"]

    def test_list_software_stacks_no_params(self, client, monkeypatch):
        """list_software_stacks without filters hits the bare path"""
        captured = {}

        def fake_request(method, url, verify, json, timeout):
            captured["url"] = url
            return _build_response(json_data={"listing": []})

        monkeypatch.setattr(client._session, "request", fake_request)

        client.list_software_stacks()
        assert (
            captured["url"]
            == "https://internal-alb.example.com/res/virtual-desktop/software-stacks"
        )

    def test_create_permission_profile_posts_to_permission_profile_path(
        self, client, monkeypatch
    ):
        """create_permission_profile POSTs to /virtual-desktop/permission-profiles."""
        captured = {}

        def fake_request(method, url, verify, json, timeout):
            captured["method"] = method
            captured["url"] = url
            captured["json"] = json
            return _build_response(json_data={"profile": {"profile_id": "pp-1"}})

        monkeypatch.setattr(client._session, "request", fake_request)

        request_content = MagicMock()
        request_content.to_dict.return_value = {"profile": {"profile_id": "pp-1"}}

        client.create_permission_profile(request_content)

        assert captured["method"] == "POST"
        assert (
            captured["url"]
            == "https://internal-alb.example.com/res/virtual-desktop/permission-profiles"
        )
        assert captured["json"] == {"profile": {"profile_id": "pp-1"}}

    def test_delete_permission_profile_deletes_permission_profile_path(
        self, client, monkeypatch
    ):
        """delete_permission_profile DELETEs /virtual-desktop/permission-profiles/{id}."""
        captured = {}

        def fake_request(method, url, verify, json, timeout):
            captured["method"] = method
            captured["url"] = url
            return _build_response(json_data={"success": True})

        monkeypatch.setattr(client._session, "request", fake_request)

        client.delete_permission_profile(profile_id="pp-1")

        assert captured["method"] == "DELETE"
        assert (
            captured["url"]
            == "https://internal-alb.example.com/res/virtual-desktop/permission-profiles/pp-1"
        )

    def test_get_permission_profile_gets_utils_permission_profile_path(
        self, client, monkeypatch
    ):
        """get_permission_profile GETs the /virtual-desktop-utils/permission-profiles/{id}."""
        captured = {}

        def fake_request(method, url, verify, json, timeout):
            captured["method"] = method
            captured["url"] = url
            return _build_response(json_data={"profile": {"profile_id": "pp-1"}})

        monkeypatch.setattr(client._session, "request", fake_request)

        client.get_permission_profile(profile_id="pp-1")

        assert captured["method"] == "GET"
        assert (
            captured["url"]
            == "https://internal-alb.example.com/res/virtual-desktop-utils/permission-profiles/pp-1"
        )

    def test_close_closes_session(self, client):
        """close() closes the underlying session"""
        client._session = MagicMock()
        client.close()
        client._session.close.assert_called_once()

    def test_context_manager_closes_on_exit(self, stub_token):
        """leaving a `with` block closes the session"""
        with ResApiClient(
            endpoint="https://internal-alb.example.com",
            client_id="cid",
            client_secret="csec",
            scopes=["env-vdc/read"],
        ) as client:
            client._session = MagicMock()
            session = client._session
        session.close.assert_called_once()
