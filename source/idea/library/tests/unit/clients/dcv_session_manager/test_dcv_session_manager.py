#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

# Mock the generated client package before importing the module under test
_MOCKED_MODULES = [
    "res.clients.dcv_session_management_client",
    "res.clients.dcv_session_management_client.api",
    "res.clients.dcv_session_management_client.api.health_api",
    "res.clients.dcv_session_management_client.api.sessions_api",
    "res.clients.dcv_session_management_client.exceptions",
    "res.clients.dcv_session_management_client.models",
    "res.clients.dcv_session_management_client.models.get_session_screenshot_request_data",
    "res.clients.dcv_session_management_client.models.get_session_screenshots_request_content",
    "res.clients.dcv_session_management_client.models.update_session_permissions_request_content",
    "res.clients.dcv_session_management_client.models.update_session_permissions_request_data",
    "res.clients.dcv_session_management_client.models.describe_sessions_request_content",
    "res.clients.dcv_session_management_client.models.describe_sessions_request_data",
]
_original_modules = {key: sys.modules.get(key) for key in _MOCKED_MODULES}


class _MockApiException(Exception):
    pass


mock_dcv_client = MagicMock()
mock_exceptions = MagicMock()
mock_exceptions.ApiException = _MockApiException
sys.modules["res.clients.dcv_session_management_client"] = mock_dcv_client
sys.modules["res.clients.dcv_session_management_client.api"] = mock_dcv_client.api
sys.modules["res.clients.dcv_session_management_client.api.health_api"] = (
    mock_dcv_client.api.health_api
)
sys.modules["res.clients.dcv_session_management_client.api.sessions_api"] = (
    mock_dcv_client.api.sessions_api
)
sys.modules["res.clients.dcv_session_management_client.exceptions"] = mock_exceptions
sys.modules["res.clients.dcv_session_management_client.models"] = mock_dcv_client.models
sys.modules[
    "res.clients.dcv_session_management_client.models.get_session_screenshot_request_data"
] = mock_dcv_client.models.get_session_screenshot_request_data
sys.modules[
    "res.clients.dcv_session_management_client.models.get_session_screenshots_request_content"
] = mock_dcv_client.models.get_session_screenshots_request_content
sys.modules[
    "res.clients.dcv_session_management_client.models.update_session_permissions_request_content"
] = mock_dcv_client.models.update_session_permissions_request_content
sys.modules[
    "res.clients.dcv_session_management_client.models.update_session_permissions_request_data"
] = mock_dcv_client.models.update_session_permissions_request_data
sys.modules[
    "res.clients.dcv_session_management_client.models.describe_sessions_request_content"
] = mock_dcv_client.models.describe_sessions_request_content
sys.modules[
    "res.clients.dcv_session_management_client.models.describe_sessions_request_data"
] = mock_dcv_client.models.describe_sessions_request_data


def teardown_module():
    for key in _MOCKED_MODULES:
        if _original_modules[key] is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = _original_modules[key]


from res.clients.dcv_session_management_client.api.health_api import HealthApi
from res.clients.dcv_session_management_client.api.sessions_api import SessionsApi
from res.clients.dcv_session_manager import dcv_session_manager_client


@pytest.fixture(autouse=True)
def _reset_dcv_mock():
    mock_dcv_client.reset_mock()
    yield


class TestDcvSessionManager:

    def test_health_check_pass(self, monkeypatch):
        """health check returns status"""
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {"status": "OK"}

        mock_api = MagicMock()
        mock_api.health_check.return_value = mock_response

        fake_get_api = MagicMock(return_value=mock_api)
        monkeypatch.setattr(dcv_session_manager_client, "_get_api", fake_get_api)

        result = dcv_session_manager_client.health_check()
        fake_get_api.assert_called_once_with(HealthApi)
        mock_api.health_check.assert_called_once()
        assert result == {"status": "OK"}

    def test_get_client_configuration(self, monkeypatch):
        """configuration uses endpoint from cluster settings"""
        fake_config = SimpleNamespace(host=None, verify_ssl=None)
        mock_dcv_client.Configuration.return_value = fake_config
        settings = {
            "cluster.load_balancers.internal_alb.certificates.custom_dns_name": "internal-alb.example.com",
        }
        monkeypatch.setattr(
            dcv_session_manager_client.cluster_settings,
            "get_setting",
            lambda key: settings[key],
        )

        config = dcv_session_manager_client._get_client_configuration()
        assert config.host == "https://internal-alb.example.com"
        assert config.verify_ssl is False

    def test_set_request_headers(self, monkeypatch):
        """sets Authorization header with bearer token from client credentials"""
        monkeypatch.setenv("environment_name", "test-env")
        monkeypatch.setattr(
            dcv_session_manager_client,
            "_get_vdc_client_id_secret",
            lambda: ("client-id", "client-secret"),
        )
        monkeypatch.setattr(
            dcv_session_manager_client.token,
            "get_access_token_using_client_credentials",
            lambda cid, csec, scope: "test-token",
        )

        mock_api_client = MagicMock()
        dcv_session_manager_client._set_request_headers(mock_api_client)

        mock_api_client.set_default_header.assert_called_once_with(
            header_name="Authorization", header_value="Bearer test-token"
        )

    def test_set_request_headers_scope_format(self, monkeypatch):
        """scope string includes environment name"""
        monkeypatch.setenv("environment_name", "my-env")
        monkeypatch.setattr(
            dcv_session_manager_client,
            "_get_vdc_client_id_secret",
            lambda: ("cid", "csec"),
        )
        captured = {}
        monkeypatch.setattr(
            dcv_session_manager_client.token,
            "get_access_token_using_client_credentials",
            lambda cid, csec, scope: captured.update(scope=scope) or "tok",
        )

        dcv_session_manager_client._set_request_headers(MagicMock())
        assert captured["scope"] == "my-env-dcv-session-manager/sm_scope"

    def test_set_request_headers_missing_env_raises(self, monkeypatch):
        """raises KeyError when environment_name is not set"""
        monkeypatch.delenv("environment_name", raising=False)
        with pytest.raises(KeyError):
            dcv_session_manager_client._set_request_headers(MagicMock())

    def test_get_vdc_client_id_secret(self, monkeypatch):
        """retrieves client id and secret from cluster settings and secrets manager"""
        settings = {
            "vdc.client_id": "arn:aws:secretsmanager:us-east-1:123:secret:client-id",
            "vdc.client_secret": "arn:aws:secretsmanager:us-east-1:123:secret:client-secret",
        }
        secrets = {
            "arn:aws:secretsmanager:us-east-1:123:secret:client-id": "my-client-id",
            "arn:aws:secretsmanager:us-east-1:123:secret:client-secret": "my-client-secret",
        }
        monkeypatch.setattr(
            dcv_session_manager_client.cluster_settings,
            "get_setting",
            lambda key: settings[key],
        )
        monkeypatch.setattr(
            dcv_session_manager_client.aws_utils,
            "get_secret_string",
            lambda arn: secrets[arn],
        )

        client_id, client_secret = (
            dcv_session_manager_client._get_vdc_client_id_secret()
        )
        assert client_id == "my-client-id"
        assert client_secret == "my-client-secret"

    def test_get_session_screenshots_empty_returns_empty(self):
        """returns empty lists when no session IDs provided"""
        result = dcv_session_manager_client.get_session_screenshots(
            [], requester="user1"
        )
        assert result == {"successful_list": [], "unsuccessful_list": []}

    def test_get_session_screenshots_calls_api(self, monkeypatch):
        """calls sessions API with requester + session_id list and returns to_dict()"""
        expected = {
            "successful_list": [
                {"session_screenshot": {"session_id": "s-1", "images": []}}
            ],
            "unsuccessful_list": [],
        }
        mock_response = MagicMock()
        mock_response.to_dict.return_value = expected

        mock_api = MagicMock()
        mock_api.get_session_screenshots.return_value = mock_response

        fake_get_api = MagicMock(return_value=mock_api)
        monkeypatch.setattr(dcv_session_manager_client, "_get_api", fake_get_api)

        result = dcv_session_manager_client.get_session_screenshots(
            ["s-1", "s-2"], requester="user1"
        )

        fake_get_api.assert_called_once_with(SessionsApi)
        mock_api.get_session_screenshots.assert_called_once()

        request_data_calls = (
            mock_dcv_client.models.get_session_screenshot_request_data.GetSessionScreenshotRequestData.call_args_list
        )
        session_ids = [call.kwargs["session_id"] for call in request_data_calls]
        assert session_ids == ["s-1", "s-2"]

        request_content_call = (
            mock_dcv_client.models.get_session_screenshots_request_content.GetSessionScreenshotsRequestContent.call_args
        )
        assert request_content_call.kwargs["requester"] == "user1"

        assert result == expected

    def test_describe_sessions_empty_returns_empty(self):
        """returns empty lists when no session requests provided"""
        result = dcv_session_manager_client.describe_sessions([])
        assert result == {"successful_list": [], "unsuccessful_list": []}

    def test_describe_sessions_calls_api(self, monkeypatch):
        """calls sessions API with (session_id, owner) request and returns to_dict()"""
        expected = {
            "successful_list": [{"session_id": "s-1", "num_of_connections": 2}],
            "unsuccessful_list": [],
        }
        mock_response = MagicMock()
        mock_response.to_dict.return_value = expected

        mock_api = MagicMock()
        mock_api.describe_sessions.return_value = mock_response

        fake_get_api = MagicMock(return_value=mock_api)
        monkeypatch.setattr(dcv_session_manager_client, "_get_api", fake_get_api)

        session_requests = [
            {"session_id": "s-1", "owner": "alice"},
            {"session_id": "s-2", "owner": "bob"},
        ]
        result = dcv_session_manager_client.describe_sessions(session_requests)

        fake_get_api.assert_called_once_with(SessionsApi)
        mock_api.describe_sessions.assert_called_once()
        request_data_calls = (
            mock_dcv_client.models.describe_sessions_request_data.DescribeSessionsRequestData.call_args_list
        )
        session_ids = [call.kwargs["session_id"] for call in request_data_calls]
        owners = [call.kwargs["owner"] for call in request_data_calls]
        assert session_ids == ["s-1", "s-2"]
        assert owners == ["alice", "bob"]
        assert result == expected

    def test_get_sessions_api_sets_headers(self, monkeypatch):
        """_get_sessions_api creates client with config and sets auth headers"""
        fake_config = SimpleNamespace(host="https://alb.example.com", verify_ssl=False)
        monkeypatch.setattr(
            dcv_session_manager_client, "_get_client_configuration", lambda: fake_config
        )
        mock_set_headers = MagicMock()
        monkeypatch.setattr(
            dcv_session_manager_client, "_set_request_headers", mock_set_headers
        )

        dcv_session_manager_client._get_api(SessionsApi)

        mock_dcv_client.ApiClient.assert_called_once_with(fake_config)
        mock_set_headers.assert_called_once()

    def test_get_session_connection_data_success(self, monkeypatch):
        """returns mapped session connection data on success"""
        mock_secret = MagicMock()
        mock_secret.get_secret_value.return_value = "jwt-token-abc"

        mock_server = MagicMock()
        mock_server.web_url_path = "/"

        mock_session = MagicMock()
        mock_session.id = "ses-123"
        mock_session.owner = "testuser"
        mock_session.server = mock_server

        mock_response = MagicMock()
        mock_response.connection_token = mock_secret
        mock_response.session = mock_session

        mock_api = MagicMock()
        mock_api.get_session_connection_data.return_value = mock_response

        fake_get_api = MagicMock(return_value=mock_api)
        monkeypatch.setattr(dcv_session_manager_client, "_get_api", fake_get_api)

        result = dcv_session_manager_client.get_session_connection_data(
            "ses-123", "testuser"
        )

        fake_get_api.assert_called_once_with(SessionsApi)
        mock_api.get_session_connection_data.assert_called_once_with(
            session_id="ses-123", username="testuser"
        )
        assert result == {
            "idea_session_id": "ses-123",
            "idea_session_owner": "testuser",
            "username": "testuser",
            "web_url_path": "/",
            "access_token": "jwt-token-abc",
        }

    def test_get_session_connection_data_api_error(self, monkeypatch):
        """API exceptions propagate to caller"""
        mock_api = MagicMock()
        mock_api.get_session_connection_data.side_effect = _MockApiException(
            "connection refused"
        )

        fake_get_api = MagicMock(return_value=mock_api)
        monkeypatch.setattr(dcv_session_manager_client, "_get_api", fake_get_api)

        with pytest.raises(_MockApiException):
            dcv_session_manager_client.get_session_connection_data(
                "ses-123", "testuser"
            )

    def test_get_session_connection_data_no_token(self, monkeypatch):
        """access_token is None when connection_token is absent"""
        mock_session = MagicMock()
        mock_session.id = "ses-123"
        mock_session.owner = "testuser"
        mock_session.server = MagicMock(web_url_path="/")

        mock_response = MagicMock()
        mock_response.connection_token = None
        mock_response.session = mock_session

        mock_api = MagicMock()
        mock_api.get_session_connection_data.return_value = mock_response
        monkeypatch.setattr(
            dcv_session_manager_client, "_get_api", MagicMock(return_value=mock_api)
        )

        result = dcv_session_manager_client.get_session_connection_data(
            "ses-123", "testuser"
        )
        assert result["access_token"] is None
        assert result["idea_session_id"] == "ses-123"

    def test_get_session_connection_data_no_session(self, monkeypatch):
        """session fields are None when session is absent"""
        mock_response = MagicMock()
        mock_response.connection_token = None
        mock_response.session = None

        mock_api = MagicMock()
        mock_api.get_session_connection_data.return_value = mock_response
        monkeypatch.setattr(
            dcv_session_manager_client, "_get_api", MagicMock(return_value=mock_api)
        )

        result = dcv_session_manager_client.get_session_connection_data(
            "ses-123", "testuser"
        )
        assert result["idea_session_id"] is None
        assert result["idea_session_owner"] is None
        assert result["web_url_path"] is None

    def test_get_session_connection_data_unexpected_error_propagates(self, monkeypatch):
        """unexpected exceptions propagate after logging"""
        mock_api = MagicMock()
        mock_api.get_session_connection_data.side_effect = TypeError("unexpected")

        monkeypatch.setattr(
            dcv_session_manager_client, "_get_api", MagicMock(return_value=mock_api)
        )

        with pytest.raises(TypeError):
            dcv_session_manager_client.get_session_connection_data(
                "ses-123", "testuser"
            )
