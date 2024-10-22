import json
import os
import typing
from http.client import HTTPResponse
from typing import Any, Generator, Optional
from unittest.mock import MagicMock, Mock, patch

import jwt
import pytest
from jwt import ExpiredSignatureError, InvalidTokenError

from idea.infrastructure.install import proxy_handler
from idea.infrastructure.install.proxy_handler import (
    AWSRequestInfo,
    InvalidRequestException,
)

os.environ["ASSUME_ROLE_ARN"] = "fake-role-arn"

# Mock environment variables
os.environ["DDB_USERS_TABLE_NAME"] = "mock_users_table"
os.environ["DDB_GROUPS_TABLE_NAME"] = "mock_groups_table"
os.environ["DDB_CLUSTER_SETTINGS_TABLE_NAME"] = "mock_cluster_settings_table"

# Mock user and group data
mock_user_data = {
    "username": "test_user",
    "enabled": True,
    "is_active": True,
    "role": "user",
    "additional_groups": ["group1", "group2"],
}

mock_group_data = [
    {"id": "group1", "role": "user"},
    {"id": "group2", "role": "admin"},
]


@pytest.fixture(params=(None, "error"), ids=("success", "error"))
def error(request: pytest.FixtureRequest) -> Optional[str]:
    value = getattr(request, "param")
    if value is None:
        return None
    return str(value)


@pytest.fixture
def mock_user_and_groups(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        proxy_handler, "get_user", MagicMock(return_value=mock_user_data)
    )

    monkeypatch.setattr(
        proxy_handler, "get_all_admin_groups", MagicMock(return_value=["group2"])
    )


@pytest.fixture(params=(None, "error"), ids=("success", "error"))
def jwt_error(request: pytest.FixtureRequest) -> Optional[str]:
    value = getattr(request, "param")
    if value is None:
        return None
    return str(value)


def test_get_ddb_user_name() -> None:
    assert proxy_handler.get_ddb_user_name("clusteradmin", None) == "clusteradmin"
    assert proxy_handler.get_ddb_user_name("clusteradmin", "saml") == "clusteradmin"
    assert proxy_handler.get_ddb_user_name("test1@amazon.com", None) == "test1"
    assert proxy_handler.get_ddb_user_name("test_1@amazon.com", None) == "test_1"
    assert (
        proxy_handler.get_ddb_user_name("saml_admin_1@amazon.com", "saml") == "admin_1"
    )
    assert (
        proxy_handler.get_ddb_user_name("saml_admin_1@amazon.com", "SAML") == "admin_1"
    )


def test_is_any_group_admin(mock_user_and_groups: None) -> None:
    assert (
        proxy_handler.is_any_group_admin(
            mock_user_data["additional_groups"]
            if isinstance(mock_user_data["additional_groups"], list)
            else []
        )
        is True
    )


def test_verify_user_authorization(monkeypatch: pytest.MonkeyPatch) -> None:
    # Test case 1: User is authenticated and authorized (role is "admin")
    mock_decoded_token = {"username": "test_user"}
    mock_user = {
        "enabled": True,
        "is_active": True,
        "role": "admin",
        "additional_groups": [],
    }
    monkeypatch.setattr(proxy_handler, "get_user", lambda username: mock_user)
    monkeypatch.setattr(proxy_handler, "is_any_group_admin", lambda groups: False)

    try:
        proxy_handler.verify_user_authorization(mock_decoded_token)
    except Exception:
        pytest.fail("Unexpected exception raised for authorized user")

    # Test case 2: User is authenticated and authorized (in admin groups)
    mock_decoded_token = {"username": "test_user"}
    mock_user = {
        "enabled": True,
        "is_active": True,
        "role": "user",
        "additional_groups": ["admin_group"],
    }
    monkeypatch.setattr(proxy_handler, "get_user", lambda username: mock_user)
    monkeypatch.setattr(proxy_handler, "is_any_group_admin", lambda groups: True)

    try:
        proxy_handler.verify_user_authorization(mock_decoded_token)
    except Exception:
        pytest.fail("Unexpected exception raised for authorized user")

    # Test case 3: User is inactive or disabled
    mock_decoded_token = {"username": "test_user"}
    mock_user = {
        "enabled": False,
        "is_active": False,
        "role": "user",
        "additional_groups": [],
    }
    monkeypatch.setattr(proxy_handler, "get_user", lambda username: mock_user)
    monkeypatch.setattr(proxy_handler, "is_any_group_admin", lambda groups: False)

    with pytest.raises(Exception) as exc_info:
        proxy_handler.verify_user_authorization(mock_decoded_token)
    assert str(exc_info.value) == "User test_user is inactive or disabled"

    # Test case 4: User is not authorized (not an admin and not in admin groups)
    mock_decoded_token = {"username": "test_user"}
    mock_user = {
        "enabled": True,
        "is_active": True,
        "role": "user",
        "additional_groups": [],
    }
    monkeypatch.setattr(proxy_handler, "get_user", lambda username: mock_user)
    monkeypatch.setattr(proxy_handler, "is_any_group_admin", lambda groups: False)

    with pytest.raises(Exception) as exc_info:
        proxy_handler.verify_user_authorization(mock_decoded_token)
    assert str(exc_info.value) == "User test_user is not authorized"


@patch("jwt.PyJWKClient")
def test_decode_jwt_valid_token(mock_pyjwkclient: Any) -> None:
    with patch.dict(
        "os.environ", {"COGNITO_USER_POOL_PROVIDER_URL": "https://example.com/userpool"}
    ):
        valid_jwt_token = jwt.encode(
            {"username": "test_user"},  # Valid token payload
            "mock_signing_key",
            algorithm="HS256",
        )

        # Mock the PyJWKClient instance
        mock_client = Mock()
        mock_pyjwkclient.return_value = mock_client

        # Mock the get_signing_key_from_jwt method
        mock_signing_key = Mock()
        mock_signing_key.key = "mock_signing_key"
        mock_client.get_signing_key_from_jwt.return_value = mock_signing_key

        # Mock the get_signing_key method
        with patch.object(
            proxy_handler, "get_signing_key", return_value="mock_signing_key"
        ):
            # Mock the jwt.decode function
            with patch("jwt.decode") as mock_decode:
                mock_decode.return_value = {"username": "test_user"}
                decoded_token = proxy_handler.decode_jwt(valid_jwt_token)
                assert decoded_token == {"username": "test_user"}


def test_decode_jwt_missing_token() -> None:
    with patch.dict(
        "os.environ", {"COGNITO_USER_POOL_PROVIDER_URL": "https://example.com/userpool"}
    ):
        with pytest.raises(Exception) as exc_info:
            proxy_handler.decode_jwt("")
        assert str(exc_info.value) == "Not enough segments"


@patch("jwt.PyJWKClient")
def test_decode_jwt_expired_token(mock_pyjwkclient: Any) -> None:
    with patch.dict(
        "os.environ", {"COGNITO_USER_POOL_PROVIDER_URL": "https://example.com/userpool"}
    ):
        expired_jwt_token = jwt.encode(
            {"username": "test_user", "exp": 1234567890},  # Expired token payload
            "mock_signing_key",
            algorithm="HS256",
        )

        # Mock the PyJWKClient instance
        mock_client = Mock()
        mock_pyjwkclient.return_value = mock_client

        # Mock the get_signing_key_from_jwt method
        mock_signing_key = Mock()
        mock_signing_key.key = "mock_signing_key"
        mock_client.get_signing_key_from_jwt.return_value = mock_signing_key

        # Mock the get_signing_key method
        with patch.object(
            proxy_handler, "get_signing_key", return_value="mock_signing_key"
        ):
            # Mock the jwt.decode function
            with patch("jwt.decode") as mock_decode:
                mock_decode.side_effect = ExpiredSignatureError("Token has expired")
                with pytest.raises(Exception) as exc_info:
                    proxy_handler.decode_jwt(expired_jwt_token)
                assert str(exc_info.value) == "Token has expired"


@patch("jwt.PyJWKClient")
def test_decode_jwt_invalid_token(mock_pyjwkclient: Any) -> None:
    with patch.dict(
        "os.environ", {"COGNITO_USER_POOL_PROVIDER_URL": "https://example.com/userpool"}
    ):
        invalid_jwt_token = jwt.encode(
            {"username": "test_user", "exp": 1234567890},  # Invalid token payload
            "invalid_secret_key",
            algorithm="HS256",
        )

        # Mock the PyJWKClient instance
        mock_client = Mock()
        mock_pyjwkclient.return_value = mock_client

        # Mock the get_signing_key_from_jwt method
        mock_signing_key = Mock()
        mock_signing_key.key = "mock_signing_key"
        mock_client.get_signing_key_from_jwt.return_value = mock_signing_key

        # Mock the get_signing_key method
        with patch.object(
            proxy_handler, "get_signing_key", return_value="mock_signing_key"
        ):
            with patch("jwt.decode") as mock_decode:
                mock_decode.side_effect = InvalidTokenError("Invalid token")
                with pytest.raises(Exception) as exc_info:
                    proxy_handler.decode_jwt(invalid_jwt_token)
                assert str(exc_info.value) == "Invalid token"


class Context:
    def __init__(self, invoked_function_arn: str):
        self.invoked_function_arn = invoked_function_arn


class MockResponse:
    def __init__(
        self,
        status: int,
        body: str,
        reason: str,
    ):
        self.status = status
        self.body = body
        self.reason = reason

    def read(self) -> bytes:
        return self.body.encode("utf-8")

    def getheaders(self) -> typing.List[typing.Tuple[str, str]]:
        return [("Content-Type", "application/json")]


class HTTPSConnection:
    def __init__(self, domain: str) -> None:
        self.domain = domain
        assert domain == "budgets.amazonaws.com"

    def request(
        self, http_method: str, path: str, body: Any = None, headers: Any = None
    ) -> None:
        assert http_method == "POST"
        assert path == "/"
        assert body == '{"AccountId": "123456789012"}'
        assert headers == {
            "Content-Type": "application/x-amz-json-1.1",
            "X-Amz-Target": "AWSBudgetServiceGateway.DescribeBudgets",
        }

    def getresponse(self) -> HTTPResponse:
        return typing.cast(HTTPResponse, MockResponse(200, '{"test": "value"}', "Okay"))


@pytest.fixture
def lambda_context() -> Context:
    return Context(
        "arn:aws:lambda:us-east-1:123456789012:function:mock-lambda-function"
    )


@pytest.fixture
def mock_https_connection() -> Generator:  # type: ignore
    with patch("http.client.HTTPSConnection", new=HTTPSConnection):
        yield


@pytest.fixture
def mock_sigv4_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(proxy_handler, "sigv4_auth", MagicMock(return_value=None))


def test_parse_event_path() -> None:
    # Global service without ending slash
    assert proxy_handler.parse_event_path("/awsproxy/budgets", "us-east-1") == (
        "budgets",
        "us-east-1",
        "/",
        "budgets.amazonaws.com",
    )

    # Valid path with region and ending slash
    assert proxy_handler.parse_event_path("/awsproxy/us-east-1/fsx/", "us-east-2") == (
        "fsx",
        "us-east-1",
        "/",
        "fsx.us-east-1.amazonaws.com",
    )

    # Valid path with default region represented as _ (underscore)
    assert proxy_handler.parse_event_path("/awsproxy/_/fsx/", "us-east-2") == (
        "fsx",
        "us-east-2",
        "/",
        "fsx.us-east-2.amazonaws.com",
    )

    # Valid path /awsproxy/us-east-1/elasticfilesystem/2015-02-01/file-systems/
    assert proxy_handler.parse_event_path(
        "/awsproxy/us-east-1/elasticfilesystem/2015-02-01/file-systems/",
        "us-east-2",
    ) == (
        "elasticfilesystem",
        "us-east-1",
        "/2015-02-01/file-systems/",
        "elasticfilesystem.us-east-1.amazonaws.com",
    )

    # Invalid paths
    with pytest.raises(InvalidRequestException) as exc_info:
        proxy_handler.parse_event_path("//awsproxy/budgets/", "us-east-2")
    assert str(exc_info.value) == "Invalid event path: //awsproxy/budgets/"

    with pytest.raises(InvalidRequestException) as exc_info:
        proxy_handler.parse_event_path("/awsproxy/us-east-1/_/budgets/", "us-east-2")
    assert str(exc_info.value) == "Invalid event path: /awsproxy/us-east-1/_/budgets/"


def test_send_aws_request(
    lambda_context: Context, mock_sigv4_auth: Any, mock_https_connection: Any
) -> None:

    result = proxy_handler.send_aws_request(
        AWSRequestInfo(
            "POST",
            "budgets.amazonaws.com",
            "us-east-1",
            "budgets",
            "/",
            {},
            json.dumps({"AccountId": "123456789012"}),
            {
                "Content-Type": "application/x-amz-json-1.1",
                "X-Amz-Target": "AWSBudgetServiceGateway.DescribeBudgets",
            },
            "arn:aws:iam::123456789012:role/MockRole",
        ),
        "admin1",
    )
    assert result.status == 200


def test_get_aws_reqeust_info_from_event() -> None:
    # Test KeyError gets recognized and rethrow as InvalidRequestException
    with pytest.raises(InvalidRequestException) as exc_info:
        proxy_handler.get_aws_request_info_from_event({}, "us-east-2")
    assert str(exc_info.value) == "Invalid event: attribute 'path' is required in event"

    with pytest.raises(InvalidRequestException) as exc_info:
        proxy_handler.get_aws_request_info_from_event(
            {"path": "/awsproxy/test"}, "us-east-2"
        )
    assert (
        str(exc_info.value) == "Invalid event: attribute 'headers' is required in event"
    )
    # Test valid event gets parsed correctly
    event = {
        "path": "/awsproxy/us-east-1/fsx/",
        "httpMethod": "POST",
        "body": '{"AccountId": "XXXXXXXXXXXX"}',
        "headers": {
            "Content-Type": "application/x-amz-json-1.1",
        },
        "requestContext": {"identity": {"sourceIp": "127.0.0.1"}},
        "queryStringParameters": {},
    }
    aws_request_info = proxy_handler.get_aws_request_info_from_event(event, "us-east-2")
    assert aws_request_info.http_method == "POST"
    assert aws_request_info.host == "fsx.us-east-1.amazonaws.com"
    assert aws_request_info.region == "us-east-1"
    assert aws_request_info.service_name == "fsx"
    assert aws_request_info.path == "/"
    assert aws_request_info.body == '{"AccountId": "XXXXXXXXXXXX"}'
    assert aws_request_info.headers == {
        "Content-Type": "application/x-amz-json-1.1",
    }
    assert aws_request_info.role_arn == "fake-role-arn"


def test_get_sanitized_response() -> None:
    assert proxy_handler.get_sanitized_response(
        typing.cast(
            HTTPResponse,
            MockResponse(
                401,
                json.dumps({"test": "value"}),
                "Unauthorized",
            ),
        )
    ) == {
        "isBase64Encoded": False,
        "statusCode": 401,
        "statusDescription": "401 Unauthorized",
        "headers": {"Content-Type": "application/json"},
        "body": '{"error": "Unauthorized"}',
    }

    assert proxy_handler.get_sanitized_response(
        typing.cast(
            HTTPResponse,
            MockResponse(
                403,
                json.dumps({"test": "value"}),
                "Forbidden",
            ),
        )
    ) == {
        "isBase64Encoded": False,
        "statusCode": 403,
        "statusDescription": "403 Forbidden",
        "headers": {"Content-Type": "application/json"},
        "body": '{"error": "Forbidden"}',
    }

    assert proxy_handler.get_sanitized_response(
        typing.cast(
            HTTPResponse,
            MockResponse(
                200,
                json.dumps({"test": "value"}),
                "Okay",
            ),
        )
    ) == {
        "isBase64Encoded": False,
        "statusCode": 200,
        "statusDescription": "200 Okay",
        "headers": {"Content-Type": "application/json"},
        "body": '{"test": "value"}',
    }
