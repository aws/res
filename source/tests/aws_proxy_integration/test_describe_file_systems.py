import os
from typing import Any

import pytest

from tests.aws_proxy_integration.util import post_api_response, post_api_response_data


@pytest.fixture
def api_response_without_token(url_path: str, request_body: Any) -> Any:
    headers = {
        "X-Amz-Target": "AWSSimbaAPIService_v20180301.DescribeFileSystems",
        "Content-Type": "application/json",
    }
    return post_api_response(url_path, headers, request_body)


@pytest.fixture
def api_response_with_non_admin_token_token(url_path: str, request_body: Any) -> Any:
    headers = {
        "X-Amz-Target": "AWSSimbaAPIService_v20180301.DescribeFileSystems",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ.get('NON_ADMIN_BEARER_TOKEN')}",
    }
    return post_api_response(url_path, headers, request_body)


@pytest.fixture
def api_response_create_file_system(url_path: str, request_body: Any) -> Any:
    headers = {
        "X-Amz-Target": "AWSSimbaAPIService_v20180301.AWSSimbaAPIService_v20180301.CreateFileSystem",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ.get('NON_ADMIN_BEARER_TOKEN')}",
    }
    return post_api_response(url_path, headers, request_body)


@pytest.fixture
def url_path() -> str:
    return f"/awsproxy/{os.environ.get('REGION')}/fsx/"


@pytest.fixture
def headers() -> dict[str, str]:
    return {
        "X-Amz-Target": "AWSSimbaAPIService_v20180301.DescribeFileSystems",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ.get('ADMIN_BEARER_TOKEN')}",
    }


@pytest.fixture
def request_body() -> dict[str, str]:
    return {}  # Empty body for DescribeFileSystems


def test_describe_file_systems(url_path: str, headers: Any, request_body: Any) -> None:
    """
    Test the DescribeFileSystems API call.
    """
    response_data = post_api_response_data(url_path, headers, request_body)

    # Add assertions based on the expected response structure
    assert "FileSystems" in response_data
    assert isinstance(response_data["FileSystems"], list)


def test_describe_file_systems_without_token(api_response_without_token: Any) -> None:
    """
    Test the DescribeFileSystems API call without a token.
    """
    response = api_response_without_token

    assert response.status_code == 401


def test_describe_file_systems_with_non_admin_token(
    api_response_with_non_admin_token_token: Any,
) -> None:
    """
    Test the DescribeFileSystems API call without a token.
    """
    response = api_response_with_non_admin_token_token

    assert response.status_code == 403


def test_create_file_system(api_response_create_file_system: Any) -> None:
    """
    Test the CreateFileSystem API call.
    """
    response = api_response_create_file_system

    assert response.status_code == 403
