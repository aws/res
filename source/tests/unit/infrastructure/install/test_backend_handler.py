#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
from typing import Any, Optional
from unittest.mock import MagicMock

import pytest
import res.exceptions as exceptions  # type: ignore
from botocore.exceptions import ClientError
from res.clients.ad_sync import ad_sync_client  # type: ignore

from idea.backend.resources import ad_sync, bastion_host_service

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

ad_sync_status = {
    "id": "test",
    "submission_time": 0,
    "update_time": 0,
    "status": "STOPPED",
    "ttl": 0,
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


@pytest.fixture
def mock_ad_sync_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        ad_sync_client,
        "get_ad_sync_status",
        MagicMock(return_value=ad_sync_status),
    )


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


def test_get_ad_sync_without_task_id_success(
    monkeypatch: pytest.MonkeyPatch,
    mock_ad_sync_status: None,
) -> None:
    event = {
        "httpMethod": "GET",
    }
    monkeypatch.setattr(ad_sync, "check_admin_authorized", lambda x: None)

    result = ad_sync.handle_ad_sync_event(event)

    assert result["statusCode"] == 200
    assert result["body"] == json.dumps(ad_sync_status)


def test_get_ad_sync_with_task_id_success(
    monkeypatch: pytest.MonkeyPatch,
    mock_ad_sync_status: None,
) -> None:
    event = {
        "httpMethod": "GET",
        "queryStringParameters": {"id": "test"},
    }
    monkeypatch.setattr(ad_sync, "check_admin_authorized", lambda x: None)

    result = ad_sync.handle_ad_sync_event(event)

    assert result["statusCode"] == 200
    assert result["body"] == json.dumps(ad_sync_status)


def test_get_ad_sync_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = {
        "httpMethod": "GET",
    }

    monkeypatch.setattr(ad_sync, "check_admin_authorized", lambda x: None)

    error_message = "Test error message"
    error = ClientError({"Error": {"Message": error_message}}, "TestOperation")

    def mock_get_ad_sync_status_error(_task_id: Optional[str]) -> None:
        raise error

    monkeypatch.setattr(
        ad_sync,
        "_get_ad_sync_status_from_ddb",
        mock_get_ad_sync_status_error,
    )

    with pytest.raises(ClientError) as excinfo:
        ad_sync.handle_ad_sync_event(event)

    assert str(excinfo.value) == str(error)


def test_start_ad_sync_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = {
        "httpMethod": "PUT",
    }

    monkeypatch.setattr(ad_sync, "check_admin_authorized", lambda x: None)

    monkeypatch.setattr(ad_sync_client, "start_ad_sync", lambda: "test")

    result = ad_sync.handle_ad_sync_event(event)

    assert result["statusCode"] == 200
    assert result["body"] == json.dumps({"id": "test"})


def test_start_ad_sync_ad_sync_in_progress(
    monkeypatch: pytest.MonkeyPatch, mock_os_env_var: None
) -> None:
    event = {
        "httpMethod": "PUT",
    }

    def mock_ad_sync_in_progress_error() -> None:
        raise exceptions.ADSyncInProcess()

    monkeypatch.setattr(ad_sync_client, "start_ad_sync", mock_ad_sync_in_progress_error)
    monkeypatch.setattr(ad_sync, "check_admin_authorized", lambda x: None)

    result = ad_sync.handle_ad_sync_event(event)

    assert result["statusCode"] == 400
    assert result["statusDescription"] == "Client Error"


def test_start_ad_sync_configuration_not_found(
    monkeypatch: pytest.MonkeyPatch, mock_os_env_var: None
) -> None:
    event = {
        "httpMethod": "PUT",
    }

    def mock_configuration_not_found_error() -> None:
        raise exceptions.ADSyncConfigurationNotFound()

    monkeypatch.setattr(
        ad_sync_client, "start_ad_sync", mock_configuration_not_found_error
    )
    monkeypatch.setattr(ad_sync, "check_admin_authorized", lambda x: None)

    result = ad_sync.handle_ad_sync_event(event)

    assert result["statusCode"] == 400
    assert result["statusDescription"] == "Client Error"


def test_stop_ad_sync_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = {
        "httpMethod": "DELETE",
        "body": r'{"id": "test"}',
    }

    monkeypatch.setattr(ad_sync, "check_admin_authorized", lambda x: None)

    monkeypatch.setattr(ad_sync_client, "stop_ad_sync", lambda x: "test")

    result = ad_sync.handle_ad_sync_event(event)

    assert result["statusCode"] == 200


def test_handle_ad_sync_event_non_admin_unauthorized(
    monkeypatch: pytest.MonkeyPatch, mock_os_env_var: None
) -> None:
    error_message = "Test error message"
    error = exceptions.UnauthorizedAccess({"Error": {"Message": error_message}})

    def mock_check_admin_authorized_error(_event: dict[str, Any]) -> None:
        raise error

    monkeypatch.setattr(
        ad_sync,
        "check_admin_authorized",
        mock_check_admin_authorized_error,
    )

    result = ad_sync.handle_ad_sync_event({})

    assert result["statusCode"] == 401
    assert result["statusDescription"] == "401 Unauthorized"
