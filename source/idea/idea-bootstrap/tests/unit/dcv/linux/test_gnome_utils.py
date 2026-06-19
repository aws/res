#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import os
import tempfile
from unittest.mock import Mock

import pytest
from ideabootstrap.dcv.linux import gnome_utils
from ideabootstrap.dcv.linux.gnome_utils import _EXTENSION_JS, _EXTENSION_UUID, _METADATA


def _make_pw(home):
    pw = Mock()
    pw.pw_uid = 1000
    pw.pw_gid = 1000
    pw.pw_dir = home
    return pw


def _mock_subprocess_run(gnome_version="GNOME Shell 47.3", gsettings_stdout="@as []"):
    """Create a mock subprocess.run that handles gnome-shell --version and gsettings calls."""
    def side_effect(cmd, **kwargs):
        if cmd[0] == "gnome-shell":
            return Mock(returncode=0, stdout=gnome_version)
        return Mock(returncode=0, stdout=gsettings_stdout)
    return Mock(side_effect=side_effect)


def test_configure_skips_non_amzn2023(monkeypatch):
    monkeypatch.setenv("RES_BASE_OS", "rhel9")
    mock_pwd = Mock()
    monkeypatch.setattr("pwd.getpwnam", mock_pwd)

    gnome_utils.configure()

    mock_pwd.assert_not_called()


def test_configure_skips_missing_session_owner(monkeypatch):
    monkeypatch.setenv("RES_BASE_OS", "amzn2023")
    monkeypatch.delenv("IDEA_SESSION_OWNER", raising=False)
    mock_pwd = Mock()
    monkeypatch.setattr("pwd.getpwnam", mock_pwd)

    gnome_utils.configure()

    mock_pwd.assert_not_called()


def test_configure_skips_unknown_user(monkeypatch):
    monkeypatch.setenv("RES_BASE_OS", "amzn2023")
    monkeypatch.setenv("IDEA_SESSION_OWNER", "nobody")
    monkeypatch.setattr("pwd.getpwnam", Mock(side_effect=KeyError))
    mock_run = Mock()
    monkeypatch.setattr("subprocess.run", mock_run)

    gnome_utils.configure()

    mock_run.assert_not_called()


def test_configure_installs_extension(monkeypatch):
    monkeypatch.setenv("RES_BASE_OS", "amzn2023")
    monkeypatch.setenv("IDEA_SESSION_OWNER", "testuser")

    with tempfile.TemporaryDirectory() as home:
        monkeypatch.setattr("pwd.getpwnam", Mock(return_value=_make_pw(home)))
        monkeypatch.setattr("os.chown", Mock())
        mock_run = _mock_subprocess_run()
        monkeypatch.setattr("subprocess.run", mock_run)

        gnome_utils.configure()

        ext_dir = os.path.join(home, ".local", "share", "gnome-shell", "extensions", _EXTENSION_UUID)
        with open(os.path.join(ext_dir, "extension.js")) as f:
            assert f.read() == _EXTENSION_JS
        with open(os.path.join(ext_dir, "metadata.json")) as f:
            assert json.load(f) == _METADATA

        # gsettings set should have been called with the UUID
        set_call_args = mock_run.call_args_list[-1][0][0]
        assert "gsettings" in set_call_args
        assert "set" in set_call_args
        assert f"['{_EXTENSION_UUID}']" in set_call_args


def test_configure_appends_to_existing_extensions(monkeypatch):
    monkeypatch.setenv("RES_BASE_OS", "amzn2023")
    monkeypatch.setenv("IDEA_SESSION_OWNER", "testuser")

    with tempfile.TemporaryDirectory() as home:
        monkeypatch.setattr("pwd.getpwnam", Mock(return_value=_make_pw(home)))
        monkeypatch.setattr("os.chown", Mock())
        mock_run = _mock_subprocess_run(gsettings_stdout="['other-ext@example']")
        monkeypatch.setattr("subprocess.run", mock_run)

        gnome_utils.configure()

        set_call_args = mock_run.call_args_list[-1][0][0]
        new_value = set_call_args[-1]
        assert "other-ext@example" in new_value
        assert _EXTENSION_UUID in new_value


def test_configure_skips_gsettings_if_already_enabled(monkeypatch):
    monkeypatch.setenv("RES_BASE_OS", "amzn2023")
    monkeypatch.setenv("IDEA_SESSION_OWNER", "testuser")

    with tempfile.TemporaryDirectory() as home:
        monkeypatch.setattr("pwd.getpwnam", Mock(return_value=_make_pw(home)))
        monkeypatch.setattr("os.chown", Mock())
        mock_run = _mock_subprocess_run(gsettings_stdout=f"['{_EXTENSION_UUID}']")
        monkeypatch.setattr("subprocess.run", mock_run)

        gnome_utils.configure()

        # gsettings set should not have been called
        for c in mock_run.call_args_list:
            if c[0][0][0] != "gnome-shell":
                assert "set" not in c[0][0]


def test_configure_skips_if_already_up_to_date(monkeypatch):
    monkeypatch.setenv("RES_BASE_OS", "amzn2023")
    monkeypatch.setenv("IDEA_SESSION_OWNER", "testuser")

    with tempfile.TemporaryDirectory() as home:
        ext_dir = os.path.join(home, ".local", "share", "gnome-shell", "extensions", _EXTENSION_UUID)
        os.makedirs(ext_dir)
        with open(os.path.join(ext_dir, "extension.js"), "w") as f:
            f.write(_EXTENSION_JS)
        with open(os.path.join(ext_dir, "metadata.json"), "w") as f:
            json.dump(_METADATA, f)

        monkeypatch.setattr("pwd.getpwnam", Mock(return_value=_make_pw(home)))
        mock_run = Mock(return_value=Mock(returncode=0, stdout="GNOME Shell 47.3"))
        monkeypatch.setattr("subprocess.run", mock_run)

        gnome_utils.configure()

        # Only gnome-shell --version should have been called, not gsettings
        assert mock_run.call_count == 1
        assert mock_run.call_args_list[0][0][0] == ["gnome-shell", "--version"]


def test_configure_updates_if_extension_js_changed(monkeypatch):
    monkeypatch.setenv("RES_BASE_OS", "amzn2023")
    monkeypatch.setenv("IDEA_SESSION_OWNER", "testuser")

    with tempfile.TemporaryDirectory() as home:
        ext_dir = os.path.join(home, ".local", "share", "gnome-shell", "extensions", _EXTENSION_UUID)
        os.makedirs(ext_dir)
        with open(os.path.join(ext_dir, "extension.js"), "w") as f:
            f.write("outdated content")
        with open(os.path.join(ext_dir, "metadata.json"), "w") as f:
            json.dump(_METADATA, f)

        monkeypatch.setattr("pwd.getpwnam", Mock(return_value=_make_pw(home)))
        monkeypatch.setattr("os.chown", Mock())
        mock_run = _mock_subprocess_run()
        monkeypatch.setattr("subprocess.run", mock_run)

        gnome_utils.configure()

        with open(os.path.join(ext_dir, "extension.js")) as f:
            assert f.read() == _EXTENSION_JS


def test_configure_warns_on_non_47_gnome_shell(monkeypatch):
    monkeypatch.setenv("RES_BASE_OS", "amzn2023")
    monkeypatch.setenv("IDEA_SESSION_OWNER", "testuser")

    with tempfile.TemporaryDirectory() as home:
        monkeypatch.setattr("pwd.getpwnam", Mock(return_value=_make_pw(home)))
        monkeypatch.setattr("os.chown", Mock())
        mock_run = _mock_subprocess_run(gnome_version="GNOME Shell 46.1")
        monkeypatch.setattr("subprocess.run", mock_run)
        mock_warning = Mock()
        monkeypatch.setattr(gnome_utils.logger, "warning", mock_warning)

        gnome_utils.configure()

        mock_warning.assert_any_call(
            "GNOME Shell version is 46.1, extension targets 47. "
            "The extension may not load correctly."
        )


def test_configure_no_warning_on_gnome_47(monkeypatch):
    monkeypatch.setenv("RES_BASE_OS", "amzn2023")
    monkeypatch.setenv("IDEA_SESSION_OWNER", "testuser")

    with tempfile.TemporaryDirectory() as home:
        monkeypatch.setattr("pwd.getpwnam", Mock(return_value=_make_pw(home)))
        monkeypatch.setattr("os.chown", Mock())
        mock_run = _mock_subprocess_run(gnome_version="GNOME Shell 47.3")
        monkeypatch.setattr("subprocess.run", mock_run)
        mock_warning = Mock()
        monkeypatch.setattr(gnome_utils.logger, "warning", mock_warning)

        gnome_utils.configure()

        for c in mock_warning.call_args_list:
            assert "may not load correctly" not in str(c)


def test_configure_chowns_local_and_share_directories(monkeypatch):
    monkeypatch.setenv("RES_BASE_OS", "amzn2023")
    monkeypatch.setenv("IDEA_SESSION_OWNER", "testuser")

    with tempfile.TemporaryDirectory() as home:
        pw = _make_pw(home)
        monkeypatch.setattr("pwd.getpwnam", Mock(return_value=pw))
        chown_calls = []
        monkeypatch.setattr("os.chown", lambda path, uid, gid: chown_calls.append((path, uid, gid)))
        mock_run = _mock_subprocess_run()
        monkeypatch.setattr("subprocess.run", mock_run)

        gnome_utils.configure()

        local_dir = os.path.join(home, ".local")
        share_dir = os.path.join(home, ".local", "share")
        assert (local_dir, 1000, 1000) in chown_calls
        assert (share_dir, 1000, 1000) in chown_calls
