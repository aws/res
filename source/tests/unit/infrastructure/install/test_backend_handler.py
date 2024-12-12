import json
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from idea.backend import bastion_host_service

bastion_host_details = {
    "instance_id": "i-1234567890abcdef",
    "private_ip": "10.0.0.1",
    "public_ip": "1.2.3.4",
    "private_dns_name": "ec2-10-0-0-1.us-west-2.compute.amazonaws.com",
}

new_bastion_host_details = {
    "instance_id": "i-9876543210abcdef",
    "private_ip": "10.0.0.2",
    "public_ip": "4.3.2.1",
    "private_dns_name": "ec2-10-0-0-2.us-west-2.compute.amazonaws.com",
}
bastion_host_config = {
    "instance_ami": "ami-0123456789abcdef",
    "instance_type": "t2.micro",
    "key_pair": "my-key-pair",
    "security_group_id": "sg-0123456789abcdef",
}


@pytest.fixture
def mock_bastion_host_details(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        bastion_host_service,
        "_get_bastion_host_details_from_ddb",
        MagicMock(return_value=bastion_host_details),
    )


@pytest.fixture
def mock_bastion_host_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        bastion_host_service,
        "_get_bastion_host_config_from_ddb",
        MagicMock(return_value=bastion_host_config),
    )


@pytest.fixture
def mock_provision_bastion_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        bastion_host_service,
        "_provision_bastion_host",
        MagicMock(return_value=new_bastion_host_details),
    )


@pytest.fixture
def mock_os_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLUSTER_NAME", "res-test")


@pytest.fixture
def mock_cleanup_bastion_host(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock(return_value=None)
    monkeypatch.setattr(bastion_host_service, "_cleanup_bastion_host", mock)
    return mock


def mock_get_bastion_host_details_error() -> None:
    raise ClientError({}, "Error")


def test_modify_bastion_host_create_success(
    mock_bastion_host_config: None,
    mock_provision_bastion_host: None,
    mock_os_env_var: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = {
        "path": "/res/",
        "httpMethod": "PUT",
        "body": json.dumps({"ssh_enabled": True}),
    }
    monkeypatch.setattr(
        bastion_host_service,
        "_get_bastion_host_details_from_ddb",
        MagicMock(return_value={}),
    )
    monkeypatch.setattr(
        bastion_host_service,
        "_create_route53_record_set",
        MagicMock(return_value={}),
    )
    monkeypatch.setattr(
        bastion_host_service,
        "_run_ssm_command_on_vdi_sessions",
        MagicMock(return_value={}),
    )
    result = bastion_host_service.modify_bastion_host(event)

    assert result["statusCode"] == 200
    assert result["statusDescription"] == "SSH Access is enabled"
    assert result["body"] == json.dumps(new_bastion_host_details)


def test_modify_bastion_host_create_already_exists(
    mock_bastion_host_details: None,
    mock_os_env_var: None,
) -> None:
    event = {
        "path": "/res/",
        "httpMethod": "PUT",
        "body": json.dumps({"ssh_enabled": True}),
    }
    result = bastion_host_service.modify_bastion_host(event)

    assert result["statusCode"] == 200
    assert result["statusDescription"] == "Bastion host already exists"
    assert result["body"] == json.dumps(bastion_host_details)


def test_modify_bastion_host_terminate_success(
    mock_bastion_host_details: None,
    mock_os_env_var: None,
    mock_cleanup_bastion_host: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = {
        "path": "/res/",
        "httpMethod": "PUT",
        "body": json.dumps({"ssh_enabled": False}),
    }
    monkeypatch.setattr(
        bastion_host_service,
        "_run_ssm_command_on_vdi_sessions",
        MagicMock(return_value={}),
    )
    result = bastion_host_service.modify_bastion_host(event)

    mock_cleanup_bastion_host.assert_called_once_with(
        bastion_host_details["instance_id"]
    )
    assert result["statusCode"] == 200
    assert result["statusDescription"] == "SSH Access turned off"
    assert result["body"] == "{}"


def test_modify_bastion_host_error(
    monkeypatch: pytest.MonkeyPatch, mock_os_env_var: None
) -> None:
    event = {
        "path": "/res/",
        "httpMethod": "PUT",
        "body": json.dumps({"ssh_enabled": True}),
    }

    # Define the error to be raised
    error_message = "Test error message"
    error = ClientError({"Error": {"Message": error_message}}, "TestOperation")

    def mock_get_bastion_host_details_error() -> None:
        raise error

    monkeypatch.setattr(
        bastion_host_service,
        "_get_bastion_host_details_from_ddb",
        mock_get_bastion_host_details_error,
    )

    # Verify that modify_bastion_host raises the same error
    with pytest.raises(ClientError) as excinfo:
        bastion_host_service.modify_bastion_host(event)

    # Check that the raised error matches the original error
    assert str(excinfo.value) == str(error)


def test_get_bastion_host_success(
    mock_bastion_host_details: None, mock_os_env_var: None
) -> None:
    result = bastion_host_service.get_bastion_host()

    assert result["statusCode"] == 200
    assert result["statusDescription"] == "SSH Access turned on with Bastion Host"
    assert result["body"] == json.dumps(bastion_host_details)


def test_get_bastion_host_unavailable(
    monkeypatch: pytest.MonkeyPatch, mock_os_env_var: None
) -> None:
    monkeypatch.setattr(
        bastion_host_service,
        "_get_bastion_host_details_from_ddb",
        MagicMock(return_value={}),
    )
    result = bastion_host_service.get_bastion_host()

    assert result["statusCode"] == 200
    assert result["statusDescription"] == "Bastion Host is unavailable"
    assert result["body"] == "Bastion Host unavailable"


def test_get_bastion_host_error(
    monkeypatch: pytest.MonkeyPatch, mock_os_env_var: None
) -> None:

    # Define the error to be raised
    error_message = "Test error message"
    error = ClientError({"Error": {"Message": error_message}}, "TestOperation")

    def mock_get_bastion_host_details_error() -> None:
        raise error

    monkeypatch.setattr(
        bastion_host_service,
        "_get_bastion_host_details_from_ddb",
        mock_get_bastion_host_details_error,
    )

    # Verify that modify_bastion_host raises the same error
    with pytest.raises(ClientError) as excinfo:
        bastion_host_service.get_bastion_host()

    # Check that the raised error matches the original error
    assert str(excinfo.value) == str(error)
