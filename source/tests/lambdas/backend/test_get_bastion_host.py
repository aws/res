import os
from typing import Any

import pytest

from tests.lambdas.util import get_api_response_data


@pytest.fixture
def url_path() -> str:
    return f"/res/config"


@pytest.fixture
def headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
    }


def test_get_bastion_host(url_path: str, headers: Any) -> None:
    """
    Args:
        url_path (str): The URL path to get bastion host details.
        headers (Any): The headers for the API call.
    """
    response_data = get_api_response_data(url_path, headers)

    assert "instance_id" in response_data
    assert isinstance(response_data["instance_id"], str)
    assert "private_dns_name" in response_data
    assert isinstance(response_data["private_dns_name"], str)
    assert "private_ip" in response_data
    assert isinstance(response_data["private_ip"], str)
    assert "public_ip" in response_data
    assert isinstance(response_data["public_ip"], str)
