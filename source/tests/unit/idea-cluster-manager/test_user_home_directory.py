#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

"""
Test Cases for UserHomeDirectory.get_key_material symlink protection
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from ideaclustermanager.app.accounts.user_home_directory import UserHomeDirectory

from ideadatamodel import errorcodes, exceptions
from ideadatamodel.auth import User

_SENTINEL = object()


def _make_user_home_directory(tmp_path, uid=_SENTINEL):
    """Create a UserHomeDirectory with a minimal mock context and user pointing at tmp_path."""
    if uid is _SENTINEL:
        uid = os.getuid()

    user = User(username="testuser", home_dir=str(tmp_path), uid=uid)

    mock_context = MagicMock()
    mock_context.logger.return_value = MagicMock()

    return UserHomeDirectory(context=mock_context, user=user)


def _create_ssh_key(
    tmp_path,
    content="-----BEGIN RSA PRIVATE KEY-----\nfakekeydata\n-----END RSA PRIVATE KEY-----\n",
):
    """Create a valid .ssh/id_rsa file owned by current user."""
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()
    id_rsa = ssh_dir / "id_rsa"
    id_rsa.write_text(content)
    return id_rsa


class TestGetKeyMaterialSymlinkProtection:

    def test_happy_path_reads_regular_file(self, tmp_path):
        _create_ssh_key(tmp_path)
        uhd = _make_user_home_directory(tmp_path)

        result = uhd.get_key_material(key_format="pem", platform="linux")

        assert "-----BEGIN RSA PRIVATE KEY-----" in result
        assert "fakekeydata" in result

    def test_symlink_is_rejected(self, tmp_path):
        ssh_dir = tmp_path / ".ssh"
        ssh_dir.mkdir()
        # Create a real file and a symlink pointing to it
        real_file = tmp_path / "secret.txt"
        real_file.write_text("stolen secret")
        id_rsa = ssh_dir / "id_rsa"
        id_rsa.symlink_to(real_file)

        uhd = _make_user_home_directory(tmp_path)

        with pytest.raises(exceptions.SocaException) as exc_info:
            uhd.get_key_material(key_format="pem", platform="linux")
        assert exc_info.value.error_code == errorcodes.UNAUTHORIZED_ACCESS

    def test_ownership_mismatch_is_rejected(self, tmp_path):
        _create_ssh_key(tmp_path)
        # Use a uid that doesn't match the file owner (current user)
        fake_uid = os.getuid() + 9999
        uhd = _make_user_home_directory(tmp_path, uid=fake_uid)

        with pytest.raises(exceptions.SocaException) as exc_info:
            uhd.get_key_material(key_format="pem", platform="linux")
        assert exc_info.value.error_code == errorcodes.UNAUTHORIZED_ACCESS

    def test_missing_file_raises_general_error(self, tmp_path):
        ssh_dir = tmp_path / ".ssh"
        ssh_dir.mkdir()

        uhd = _make_user_home_directory(tmp_path)

        with pytest.raises(exceptions.SocaException) as exc_info:
            uhd.get_key_material(key_format="pem", platform="linux")
        assert exc_info.value.error_code == errorcodes.GENERAL_ERROR

    @patch("ideaclustermanager.app.accounts.user_home_directory.pwd.getpwnam")
    def test_uid_none_resolves_via_getpwnam(self, mock_getpwnam, tmp_path):
        _create_ssh_key(tmp_path)
        mock_getpwnam.return_value = MagicMock(pw_uid=os.getuid())
        uhd = _make_user_home_directory(tmp_path, uid=None)

        result = uhd.get_key_material(key_format="pem", platform="linux")

        assert "fakekeydata" in result
        mock_getpwnam.assert_called_once_with("testuser")

    @patch("ideaclustermanager.app.accounts.user_home_directory.pwd.getpwnam")
    def test_uid_none_getpwnam_fails_is_rejected(self, mock_getpwnam, tmp_path):
        _create_ssh_key(tmp_path)
        mock_getpwnam.side_effect = KeyError("testuser")
        uhd = _make_user_home_directory(tmp_path, uid=None)

        with pytest.raises(exceptions.SocaException) as exc_info:
            uhd.get_key_material(key_format="pem", platform="linux")
        assert exc_info.value.error_code == errorcodes.UNAUTHORIZED_ACCESS
