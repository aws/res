#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import tempfile
from unittest.mock import MagicMock

from ideabootstrap import bootstrap_common
from res.resources import sessions

def test_file_content_exists():
    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        content = "first\n"
        assert not bootstrap_common.file_content_exists(content, temp_file.name)

        temp_file.write(content)
        temp_file.flush()
        assert bootstrap_common.file_content_exists(content, temp_file.name)


def test_append_to_file():
    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        content = "first\n"
        temp_file.write(content)
        temp_file.flush()
        append_content = "second"
        bootstrap_common.append_to_file(append_content, temp_file.name)
        assert bootstrap_common.file_content_exists(append_content, temp_file.name)


def test_overwrite_file():
    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        content = "first\n"
        temp_file.write(content)
        temp_file.flush()
        overwrite_content = "second"
        bootstrap_common.overwrite_file(overwrite_content, temp_file.name)
        assert bootstrap_common.file_content_exists(overwrite_content, temp_file.name)
        assert not bootstrap_common.file_content_exists(content, temp_file.name)

def test_set_reboot_required(monkeypatch):
    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        temp_file_name = temp_file.name
        monkeypatch.setattr(bootstrap_common, "REBOOT_REQUIRED_FILE_PATH", temp_file_name)

        bootstrap_common.set_reboot_required("message")

        with open(temp_file_name, "r") as f:
            assert "message\n" in f.readlines()

def test_set_reboot_required(monkeypatch):
    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        temp_file_name = temp_file.name
        monkeypatch.setattr(bootstrap_common, "REBOOT_REQUIRED_FILE_PATH", temp_file_name)

        bootstrap_common.set_reboot_required("message")

        with open(temp_file_name, "r") as f:
            assert "message\n" in f.readlines()


def test_update_session_host_info(monkeypatch):
    monkeypatch.setenv("IDEA_SESSION_OWNER", "test_owner")
    monkeypatch.setenv("IDEA_SESSION_ID", "test_session_id")
    monkeypatch.setattr(
        "res.utils.instance_metadata_utils.get_private_dns_name",
        lambda: "ip-10-0-1-5.ec2.internal",
    )

    mock_session = {
        sessions.SESSION_DB_HASH_KEY: "test_owner",
        sessions.SESSION_DB_RANGE_KEY: "test_session_id",
        sessions.SESSION_DB_SERVER_KEY: {"instance_id": "i-123"},
    }
    monkeypatch.setattr(
        "res.resources.sessions.get_session",
        lambda owner, session_id: mock_session,
    )

    updated_session = {}

    def mock_update_session(session):
        updated_session.update(session)

    monkeypatch.setattr(
        "res.resources.sessions.update_session",
        mock_update_session,
    )

    bootstrap_common.update_session_host_info()

    server = updated_session[sessions.SESSION_DB_SERVER_KEY]
    assert server[sessions.SESSION_DB_PRIVATE_DNS_NAME_KEY] == "ip-10-0-1-5.ec2.internal"
    assert server["instance_id"] == "i-123"
    assert updated_session[sessions.SESSION_DB_DCV_SESSION_ID_KEY] == "console"


def test_update_session_host_info_logs_error_on_failure(monkeypatch):
    monkeypatch.setenv("IDEA_SESSION_OWNER", "test_owner")
    monkeypatch.setenv("IDEA_SESSION_ID", "test_session_id")

    def mock_get_private_dns_name():
        raise Exception("IMDS unavailable")

    monkeypatch.setattr(
        "res.utils.instance_metadata_utils.get_private_dns_name",
        mock_get_private_dns_name,
    )

    mock_get_session = MagicMock()
    monkeypatch.setattr("res.resources.sessions.get_session", mock_get_session)

    # Should not raise — exception is caught and logged
    bootstrap_common.update_session_host_info()

    mock_get_session.assert_not_called()


def test_update_session_host_info_get_session_fails(monkeypatch):
    """get_session raises — should not propagate."""
    monkeypatch.setenv("IDEA_SESSION_OWNER", "test_owner")
    monkeypatch.setenv("IDEA_SESSION_ID", "test_session_id")
    monkeypatch.setattr(
        "res.utils.instance_metadata_utils.get_private_dns_name",
        lambda: "ip-10-0-1-5.ec2.internal",
    )

    def mock_get_session(owner, session_id):
        raise Exception("DDB unavailable")

    monkeypatch.setattr(
        "res.resources.sessions.get_session",
        mock_get_session,
    )

    mock_update_session = MagicMock()
    monkeypatch.setattr("res.resources.sessions.update_session", mock_update_session)

    # Should not raise
    bootstrap_common.update_session_host_info()

    mock_update_session.assert_not_called()


def test_update_session_host_info_update_session_fails(monkeypatch):
    """update_session raises — should not propagate."""
    monkeypatch.setenv("IDEA_SESSION_OWNER", "test_owner")
    monkeypatch.setenv("IDEA_SESSION_ID", "test_session_id")
    monkeypatch.setattr(
        "res.utils.instance_metadata_utils.get_private_dns_name",
        lambda: "ip-10-0-1-5.ec2.internal",
    )

    monkeypatch.setattr(
        "res.resources.sessions.get_session",
        lambda owner, session_id: {
            sessions.SESSION_DB_HASH_KEY: "test_owner",
            sessions.SESSION_DB_RANGE_KEY: "test_session_id",
            sessions.SESSION_DB_SERVER_KEY: {},
        },
    )

    def mock_update_session(session):
        raise Exception("DDB write failed")

    monkeypatch.setattr(
        "res.resources.sessions.update_session",
        mock_update_session,
    )

    # Should not raise
    bootstrap_common.update_session_host_info()


def test_update_session_host_info_missing_env_vars(monkeypatch):
    """Env variables not set — should not raise."""
    monkeypatch.delenv("IDEA_SESSION_OWNER", raising=False)
    monkeypatch.delenv("IDEA_SESSION_ID", raising=False)
    monkeypatch.setattr(
        "res.utils.instance_metadata_utils.get_private_dns_name",
        lambda: "ip-10-0-1-5.ec2.internal",
    )

    mock_get_session = MagicMock(side_effect=Exception("None args"))
    monkeypatch.setattr("res.resources.sessions.get_session", mock_get_session)

    mock_update_session = MagicMock()
    monkeypatch.setattr("res.resources.sessions.update_session", mock_update_session)

    bootstrap_common.update_session_host_info()

    mock_get_session.assert_called_once()
    mock_update_session.assert_not_called()


def test_update_session_state(monkeypatch):
    monkeypatch.setenv("IDEA_SESSION_OWNER", "test_owner")
    monkeypatch.setenv("IDEA_SESSION_ID", "test_session_id")

    mock_update = MagicMock()
    monkeypatch.setattr("res.resources.sessions.update_session_state", mock_update)

    bootstrap_common.update_session_state("CREATING")

    mock_update.assert_called_once_with(
        owner="test_owner",
        session_id="test_session_id",
        state="CREATING",
        publish_event=True,
    )


def test_update_session_state_exception(monkeypatch):
    """Should not propagate exceptions."""
    monkeypatch.setenv("IDEA_SESSION_OWNER", "test_owner")
    monkeypatch.setenv("IDEA_SESSION_ID", "test_session_id")

    monkeypatch.setattr(
        "res.resources.sessions.update_session_state",
        MagicMock(side_effect=Exception("DDB error")),
    )

    # Should not raise
    bootstrap_common.update_session_state("READY")
