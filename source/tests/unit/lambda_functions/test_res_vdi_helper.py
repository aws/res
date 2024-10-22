from unittest.mock import MagicMock, patch

import pytest
from lambda_functions.res_vdi_helper.auth import (
    get_instance_id_from_user_arn,
    get_source_ip_from_request_context,
    validate_instance_origin,
)
from lambda_functions.res_vdi_helper.handler import handle_vdi_auto_stop
from res.resources import servers
from res.resources import sessions as user_sessions
from res.resources import vdi_management

PRIVATE_IP_ADDRESS = "192.168.1.1"
INVALID_IP_ADDRESS = "192.168.1.5"
INSTANCE_ID = "i-012345678910"
ROLE = "arn:aws:sts::123456789012:assumed-role/MyRole"
TEST_OWNER = "test_owner"
TEST_SESSION_ID = "test_session_id"


def test_get_instance_id_from_user_arn():
    user_arn = f"{ROLE}/{INSTANCE_ID}"
    instance_id = get_instance_id_from_user_arn(user_arn)
    assert instance_id == INSTANCE_ID


def test_get_instance_id_from_user_arn_no_match():
    user_arn = ROLE
    instance_id = get_instance_id_from_user_arn(user_arn)
    assert instance_id is None


def test_get_source_ip_from_request_context():
    request_context = {"identity": {"sourceIp": PRIVATE_IP_ADDRESS}}
    source_ip = get_source_ip_from_request_context(request_context)
    assert source_ip == PRIVATE_IP_ADDRESS


@patch("boto3.client")
def test_validate_instance_origin(mock_boto_client):
    ec2_client = MagicMock()
    ec2_client.describe_instances.return_value = {
        "Reservations": [{"Instances": [{"PrivateIpAddress": PRIVATE_IP_ADDRESS}]}]
    }
    mock_boto_client.return_value = ec2_client

    is_valid = validate_instance_origin(INSTANCE_ID, PRIVATE_IP_ADDRESS)
    assert is_valid is True


@patch("boto3.client")
def test_validate_instance_origin_with_invalid_origin(mock_boto_client):
    ec2_client = MagicMock()
    ec2_client.describe_instances.return_value = {
        "Reservations": [{"Instances": [{"PrivateIpAddress": PRIVATE_IP_ADDRESS}]}]
    }
    mock_boto_client.return_value = ec2_client

    is_valid = validate_instance_origin(INSTANCE_ID, INVALID_IP_ADDRESS)
    assert is_valid is False


def mock_get_server(instance_id):
    assert instance_id == INSTANCE_ID
    return {
        servers.SERVER_DB_HASH_KEY: INSTANCE_ID,
        servers.SERVER_DB_SESSION_OWNER_KEY: TEST_OWNER,
        servers.SERVER_DB_SESSION_ID_KEY: TEST_SESSION_ID,
    }


def mock_get_session(owner, session_id):
    assert owner == TEST_OWNER
    assert session_id == TEST_SESSION_ID
    return {
        user_sessions.SESSION_DB_HASH_KEY: TEST_OWNER,
        user_sessions.SESSION_DB_RANGE_KEY: TEST_SESSION_ID,
    }


def mock_stop_terminate_session(sessions):
    assert len(sessions) == 1
    session = sessions[0]
    assert session is not None
    assert session[user_sessions.SESSION_DB_HASH_KEY] == TEST_OWNER
    assert session[user_sessions.SESSION_DB_RANGE_KEY] == TEST_SESSION_ID
    return {}


def mock_not_called(sessions):
    assert False


def test_validate_stop_session_called():
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(user_sessions, "get_session", mock_get_session)
    monkeypatch.setattr(servers, "get_server", mock_get_server)
    monkeypatch.setattr(vdi_management, "stop_sessions", mock_stop_terminate_session)
    monkeypatch.setattr(vdi_management, "terminate_sessions", mock_not_called)

    handle_vdi_auto_stop(INSTANCE_ID, "Stop")


def test_validate_terminate_session_called():
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(user_sessions, "get_session", mock_get_session)
    monkeypatch.setattr(servers, "get_server", mock_get_server)
    monkeypatch.setattr(
        vdi_management, "terminate_sessions", mock_stop_terminate_session
    )
    monkeypatch.setattr(vdi_management, "stop_sessions", mock_not_called)

    handle_vdi_auto_stop(INSTANCE_ID, "Terminate")
