#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import tempfile
from unittest.mock import Mock, call

from ideabootstrap.dcv import constants
from ideabootstrap.dcv.linux import dcv_host


def _storage_root_mocks(monkeypatch, storage_root_exists: bool, owners: dict) -> Mock:
    """Common monkeypatching for _configure_storage_root tests.

    owners maps path -> uid returned by os.stat; paths created by makedirs
    during the run default to root (uid 0) unless present in owners.
    """
    monkeypatch.setenv("IDEA_SESSION_OWNER", "test-user")
    mock_chown = Mock()
    mock_pwd = Mock(return_value=Mock(pw_uid=1000, pw_gid=1000))

    def _exists(path: str) -> bool:
        if path == "/home/test-user/storage-root":
            return storage_root_exists
        return True

    def _stat(path: str):
        return Mock(st_uid=owners.get(path, 0))

    monkeypatch.setattr("os.path.islink", lambda x: False)
    monkeypatch.setattr("os.path.exists", _exists)
    monkeypatch.setattr("os.makedirs", Mock())
    monkeypatch.setattr("os.stat", _stat)
    monkeypatch.setattr("os.chown", mock_chown)
    monkeypatch.setattr("pwd.getpwnam", mock_pwd)
    return mock_chown


def test_configure_storage_root_fresh_create(monkeypatch) -> None:
    # Nothing exists yet: makedirs creates home + storage-root as root, so both
    # must be chowned to the session owner.
    mock_chown = _storage_root_mocks(monkeypatch, storage_root_exists=False, owners={})

    dcv_host._configure_storage_root()

    mock_chown.assert_has_calls(
        [
            call("/home/test-user", 1000, 1000),
            call("/home/test-user/storage-root", 1000, 1000),
        ]
    )


def test_configure_storage_root_healthy_existing(monkeypatch) -> None:
    # Home and storage-root both exist and are correctly owned (the normal
    # steady state on the shared NFS): nothing should be chowned.
    mock_chown = _storage_root_mocks(
        monkeypatch,
        storage_root_exists=True,
        owners={"/home/test-user": 1000, "/home/test-user/storage-root": 1000},
    )

    dcv_host._configure_storage_root()

    mock_chown.assert_not_called()


def test_configure_storage_root_repairs_root_owned_home(monkeypatch) -> None:
    # Regression: a prior session (or an unmounted-/home race) left the home
    # dir root-owned on the shared NFS. pam_mkhomedir skips existing dirs, so
    # the bootstrap must self-heal the ownership even when storage-root
    # already exists and the create path is not taken.
    mock_chown = _storage_root_mocks(
        monkeypatch,
        storage_root_exists=True,
        owners={"/home/test-user": 0, "/home/test-user/storage-root": 1000},
    )

    dcv_host._configure_storage_root()

    mock_chown.assert_called_once_with("/home/test-user", 1000, 1000)


def test_configure_storage_root_repairs_root_owned_storage_root(monkeypatch) -> None:
    # The storage-root itself was left root-owned by a prior buggy run: it
    # must be repaired even though it already exists.
    mock_chown = _storage_root_mocks(
        monkeypatch,
        storage_root_exists=True,
        owners={"/home/test-user": 1000, "/home/test-user/storage-root": 0},
    )

    dcv_host._configure_storage_root()

    mock_chown.assert_called_once_with("/home/test-user/storage-root", 1000, 1000)


def test_configure_dcv_conf(monkeypatch) -> None:
    mock_settings = {
        constants.IDLE_TIMEOUT_KEY: 3600,
        constants.IDLE_TIMEOUT_WARNING_KEY: 300,
    }
    mock_get_setting = Mock(side_effect=lambda x: mock_settings[x])

    monkeypatch.setattr(
        "ideabootstrap.dcv.dcv_utils.get_cluster_internal_endpoint",
        lambda: "internal-alb.example.com",
    )
    monkeypatch.setattr("res.resources.cluster_settings.get_setting", mock_get_setting)
    monkeypatch.setattr("os.path.exists", lambda x: False)
    monkeypatch.setenv("IDEA_SESSION_ID", "ses-test-123")

    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        temp_file_name = temp_file.name
        monkeypatch.setattr(constants, "DCV_CONFIG_FILE_PATH", temp_file_name)
        dcv_host._configure_dcv_conf()

        with open(temp_file_name, "r") as f:
            content = f.read()

    assert "idle-timeout = 3600" in content
    assert "idle-timeout-warning = 300" in content
    assert (
        'auth-token-verifier = "internal-alb.example.com/externalAuth/ses-test-123"'
        in content
    )


def test_configure_dcv_conf_missing_session_id(monkeypatch) -> None:
    import pytest

    monkeypatch.delenv("IDEA_SESSION_ID", raising=False)

    with pytest.raises(ValueError, match="IDEA_SESSION_ID"):
        dcv_host._configure_dcv_conf()


def test_configure_all(monkeypatch) -> None:
    mock_storage = Mock()
    mock_dcv = Mock()
    monkeypatch.setattr(dcv_host, "_configure_storage_root", mock_storage)
    monkeypatch.setattr(dcv_host, "_configure_dcv_conf", mock_dcv)

    dcv_host.configure()

    mock_storage.assert_called_once()
    mock_dcv.assert_called_once()


def test_apply_automatic_console_session_config(monkeypatch, tmp_path) -> None:
    dcv_conf = tmp_path / "dcv.conf"
    dcv_conf.write_text("[session-management]\n")
    monkeypatch.setattr(constants, "DCV_CONFIG_FILE_PATH", str(dcv_conf))
    mock_run = Mock()
    monkeypatch.setattr("subprocess.run", mock_run)

    dcv_host.apply_automatic_console_session_config(
        session_owner="test-user",
        storage_root="/home/test-user/storage-root",
        permissions_file_path="/etc/dcv/console/idea.perm",
    )

    with open(str(dcv_conf)) as f:
        content = f.read()
    assert "create-session = true" in content
    assert '"test-user"' in content
    assert '"/home/test-user/storage-root"' in content
    assert '"/etc/dcv/console/idea.perm"' in content
    mock_run.assert_called_once_with(["systemctl", "restart", "dcvserver"], check=True)
