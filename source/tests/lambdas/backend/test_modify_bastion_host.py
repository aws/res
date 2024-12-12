import json
from typing import Any

import pytest

from tests.lambdas.util import get_api_response_data, put_api_response_data


@pytest.fixture
def url_path() -> str:
    return "/res/config"


@pytest.fixture
def headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
    }


def test_modify_bastion_host_already_exists(url_path: str, headers: Any) -> None:
    """
    Test 1: Attempt to modify bastion host when it already exists.
    This should get the details of the existing bastion host.
    """
    response_data = put_api_response_data(
        url_path, headers, request_body=json.dumps({"ssh_enabled": True})
    )

    assert "instance_id" in response_data
    assert isinstance(response_data["instance_id"], str)
    assert "private_dns_name" in response_data
    assert isinstance(response_data["private_dns_name"], str)
    assert "private_ip" in response_data
    assert isinstance(response_data["private_ip"], str)
    assert "public_ip" in response_data
    assert isinstance(response_data["public_ip"], str)


def test_modify_bastion_host_enable_ssh(url_path: str, headers: Any) -> None:
    """
    Test 2: Send a PUT API with {ssh_enabled: True} to create a new bastion host.
    The API response will have details of new bastion host being provisioned.
    """
    response_data = put_api_response_data(
        url_path, headers, request_body=json.dumps({"ssh_enabled": True})
    )

    assert "instance_id" in response_data
    assert isinstance(response_data["instance_id"], str)
    assert "private_dns_name" in response_data
    assert isinstance(response_data["private_dns_name"], str)
    assert "private_ip" in response_data
    assert isinstance(response_data["private_ip"], str)
    assert "public_ip" in response_data
    assert isinstance(response_data["public_ip"], str)
