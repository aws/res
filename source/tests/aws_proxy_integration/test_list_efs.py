import os
from typing import Any

import pytest

from tests.aws_proxy_integration.util import get_api_response, get_api_response_data


@pytest.fixture
def api_response_without_token(url_path: str) -> Any:
    return get_api_response(url_path, {})


@pytest.fixture
def api_response_with_non_admin_token_token(url_path: str) -> Any:
    headers = {
        "Authorization": f"Bearer {os.environ.get('NON_ADMIN_BEARER_TOKEN')}",
    }
    return get_api_response(url_path, headers)


@pytest.fixture
def url_path() -> str:
    return f"/awsproxy/{os.environ.get('REGION')}/elasticfilesystem/2015-02-01/file-systems/"


@pytest.fixture
def headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {os.environ.get('ADMIN_BEARER_TOKEN')}",
    }


def test_describe_file_systems(url_path: str, headers: Any) -> None:
    """
    Test the DescribeFileSystems API call.
    """
    response_data = get_api_response_data(url_path, headers)

    # Add assertions based on the expected response structure
    assert "FileSystems" in response_data
    assert isinstance(response_data["FileSystems"], list)


def test_describe_file_systems_without_token(api_response_without_token: Any) -> None:
    """
    Test the DescribeFileSystems API call without a token.
    """
    response = api_response_without_token

    # Check if the response status code is 401 (Unauthorized)
    assert response.status_code == 401


def test_describe_file_systems_with_non_admin_token(
    api_response_with_non_admin_token_token: Any,
) -> None:
    """
    Test the DescribeFileSystems API call without a token.
    """
    response = api_response_with_non_admin_token_token

    assert response.status_code == 403
