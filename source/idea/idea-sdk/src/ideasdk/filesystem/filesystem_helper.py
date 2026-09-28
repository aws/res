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

from ideadatamodel.filesystem import (
    ListFilesRequest,
    ListFilesResult,
    ReadFileRequest,
    ReadFileResult,
    SaveFileRequest,
    SaveFileResult,
    DownloadFilesRequest,
    CreateFileRequest,
    CreateFileResult,
    DeleteFilesRequest,
    DeleteFilesResult,
    TailFileRequest,
    TailFileResult,
    FileData
)
from ideadatamodel import exceptions, errorcodes
from ideasdk.utils import Utils, GroupNameHelper
from ideasdk.protocols import SocaContextProtocol
from ideasdk.shell import ShellInvoker

import os
import asyncio
import errno
import arrow
import stat
import mimetypes
import shutil
import pathlib
from pwd import getpwnam
from typing import Dict, List, Any
from zipfile import ZipFile
from collections import deque
import shlex

# default lines to prefetch on an initial tail request.
TAIL_FILE_MAX_LINE_COUNT = 10000
# default lines to prefetch on an initial tail request.
TAIL_FILE_DEFAULT_LINE_COUNT = 1000
# min interval during subsequent tail requests. requests less than this interval will return empty lines
TAIL_FILE_MIN_INTERVAL_SECONDS = 5

RESTRICTED_ROOT_FOLDERS = [
    'boot',
    'bin',
    'dev',
    'etc',
    'home',
    'local',
    'lib',
    'lib64',
    'media',
    'opt',
    'proc',
    'root',
    'run',
    'srv',
    'sys',
    'sbin',
    'tmp',
    'usr',
    'var'
]


class FileSystemHelper:
    """
    File System Helper
    Used for supporting web based file browser APIs
    """

    def __init__(self, context: SocaContextProtocol, username: str):
        self.context = context
        self.logger = context.logger('file-system-api')

        if Utils.is_empty(username):
            raise exceptions.invalid_params('username is required')
        self.username = username
        self.shell = ShellInvoker(logger=self.logger)
        self.group_name_helper = GroupNameHelper(context)

    def get_user_home(self) -> str:
        return os.path.join(self.context.config().get_string('shared-storage.home.mount_dir', required=True), self.username)

    def safe_open(self, file: str, mode: str):
        """
        Prevents symlink-swap attacks by combining realpath containment check
        with O_NOFOLLOW on every path component.

        :param file: absolute path to the file
        :param mode: Python file mode ('r', 'w', 'rb', 'wb')
        :return: file object
        """
        parent_fd, leaf = self._safe_open_parent_dir(file)
        try:
            flags = self._mode_to_flags(mode) | os.O_NOFOLLOW
            try:
                fd = os.open(leaf, flags, 0o644, dir_fd=parent_fd)
            except OSError as e:
                if e.errno in (errno.ELOOP, errno.ENOTDIR):
                    raise exceptions.unauthorized_access()
                raise
        finally:
            os.close(parent_fd)

        return os.fdopen(fd, mode)

    def safe_chown_dir(self, path: str, uid: int, gid: int) -> None:
        """
        Atomically chown a directory without following symlinks.

        Opens the directory with O_NOFOLLOW to prevent TOCTOU race conditions
        where an attacker swaps the path with a symlink between a check and chown.
        Uses fchown on the file descriptor to guarantee the operation targets
        the actual opened directory.

        :param path: absolute path to the directory
        :param uid: user id to set
        :param gid: group id to set (-1 to leave unchanged)
        """
        try:
            dir_fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        except OSError as e:
            if e.errno in (errno.ELOOP, errno.ENOTDIR):
                raise exceptions.unauthorized_access()
            raise
        try:
            os.fchown(dir_fd, uid, gid)
        finally:
            os.close(dir_fd)

    def _safe_open_parent_dir(self, file: str) -> tuple:
        """
        Walk the path to file component by component with O_NOFOLLOW, returning
        a file descriptor for the verified parent directory and the leaf name.

        Prevents symlink-in-parent attacks by refusing to traverse any symlink
        in the path.

        :param file: absolute path to a file or directory
        :return: tuple of (parent_dir_fd, leaf_name)
        :raises unauthorized_access: if any component is a symlink
        """
        user_home = os.path.realpath(self.get_user_home())

        resolved = os.path.realpath(file)
        if not (resolved == user_home or resolved.startswith(user_home + '/')):
            raise exceptions.unauthorized_access()

        rel_path = os.path.relpath(resolved, user_home)
        components = rel_path.split(os.sep)

        dir_fd = self._walk_nofollow(user_home, components[:-1])
        return dir_fd, components[-1]

    def _walk_nofollow(self, start_dir: str, components: list) -> int:
        """
        Walk a sequence of path components from start_dir using O_NOFOLLOW,
        returning a file descriptor for the final directory reached.

        :param start_dir: absolute path to the starting directory
        :param components: list of directory names to traverse
        :return: open file descriptor for the directory after traversing all components
        :raises unauthorized_access: if any component is a symlink
        """
        dir_fd = os.open(start_dir, os.O_RDONLY | os.O_DIRECTORY)
        try:
            for component in components:
                if component == '.':
                    continue
                try:
                    next_fd = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=dir_fd)
                except OSError as e:
                    if e.errno in (errno.ELOOP, errno.ENOTDIR):
                        raise exceptions.unauthorized_access()
                    raise
                os.close(dir_fd)
                dir_fd = next_fd
        except BaseException:
            os.close(dir_fd)
            raise

        return dir_fd

    def safe_delete_file(self, file: str) -> None:
        """
        Atomically delete a file without following symlinks in any path component.

        :param file: absolute path to the file to delete
        """
        parent_fd, leaf = self._safe_open_parent_dir(file)
        try:
            os.unlink(leaf, dir_fd=parent_fd)
        finally:
            os.close(parent_fd)

    def safe_delete_symlink(self, link: str) -> None:
        """
        Safely delete a symlink by resolving only the parent directory path
        (not the symlink itself) and unlinking the leaf name.

        Unlike safe_delete_file which resolves the full path (following symlinks),
        this method only resolves and verifies the parent directory, then unlinks
        the leaf name directly — removing the symlink itself, not its target.

        :param link: absolute path to the symlink to delete
        """
        parent = os.path.dirname(link)
        leaf = os.path.basename(link)

        user_home = os.path.realpath(self.get_user_home())
        resolved_parent = os.path.realpath(parent)
        if not (resolved_parent == user_home or resolved_parent.startswith(user_home + '/')):
            raise exceptions.unauthorized_access()

        rel_path = os.path.relpath(resolved_parent, user_home)
        components = rel_path.split(os.sep)

        dir_fd = self._walk_nofollow(user_home, components)
        try:
            os.unlink(leaf, dir_fd=dir_fd)
        finally:
            os.close(dir_fd)

    def safe_delete_dir(self, directory: str) -> None:
        """
        Safely delete a directory tree, verifying no symlinks in the path.

        Uses _safe_open_parent_dir to verify the path, then opens the target
        directory with O_NOFOLLOW and deletes contents through the verified fd
        to eliminate any TOCTOU gap.

        :param directory: absolute path to the directory to delete
        """
        parent_fd, leaf = self._safe_open_parent_dir(directory)
        try:
            # Verify the leaf itself is a real directory, not a symlink
            try:
                target_fd = os.open(leaf, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
            except OSError as e:
                if e.errno in (errno.ELOOP, errno.ENOTDIR):
                    raise exceptions.unauthorized_access()
                raise
            try:
                # Delete all contents through the verified fd using fwalk
                # (bottom-up traversal so directories are empty before rmdir)
                for dirpath, dirnames, filenames, dirfd in os.fwalk(top='.', dir_fd=target_fd, topdown=False):
                    for filename in filenames:
                        os.unlink(filename, dir_fd=dirfd)
                    for dirname in dirnames:
                        # Use unlink for symlinks-to-directories, rmdir for real directories
                        try:
                            os.rmdir(dirname, dir_fd=dirfd)
                        except OSError:
                            os.unlink(dirname, dir_fd=dirfd)
            finally:
                os.close(target_fd)
            # Now remove the empty target directory itself
            os.rmdir(leaf, dir_fd=parent_fd)
        finally:
            os.close(parent_fd)

    def _get_allowed_mount_dirs(self) -> List[str]:
        """
        Returns realpath-resolved mount directories for all filesystems
        configured in shared-storage.
        """
        allowed = []
        storage_config = self.context.config().get_config('shared-storage')
        if storage_config is None:
            return allowed
        for name, storage in storage_config.items():
            if not isinstance(storage, dict):
                continue
            mount_dir = storage.get('mount_dir')
            if mount_dir:
                allowed.append(os.path.realpath(mount_dir))
        return allowed

    def safe_open_with_project_scope(self, file: str, mode: str):
        """
        Prevents symlink-swap attacks by combining realpath containment check
        with O_NOFOLLOW on every path component.

        Unlike safe_open() which restricts to the user's home directory only,
        this method validates against all shared-storage mount directories
        (home + project filesystems), and additionally verifies the requesting
        user's POSIX read permission on the opened file descriptor.

        :param file: absolute path to the file
        :param mode: Python file mode ('r', 'w', 'rb', 'wb')
        :return: file object
        """
        if Utils.is_empty(file):
            raise exceptions.unauthorized_access()
        if '..' in pathlib.PurePosixPath(file).parts:
            raise exceptions.unauthorized_access()

        if not self.is_file_browser_enabled():
            raise exceptions.disabled_feature("FileBrowser")

        # Build allowlist: all shared-storage mount dirs + user home
        allowed_bases = self._get_allowed_mount_dirs()
        user_home = os.path.realpath(self.get_user_home())
        if user_home not in allowed_bases:
            allowed_bases.append(user_home)

        # Resolve symlinks and validate path is within an allowed base
        resolved = os.path.realpath(file)
        base_dir = None
        for base in allowed_bases:
            if resolved == base or resolved.startswith(base + '/'):
                base_dir = base
                break

        if base_dir is None:
            raise exceptions.unauthorized_access()

        # Walk resolved path component by component with O_NOFOLLOW
        rel_path = os.path.relpath(resolved, base_dir)
        components = rel_path.split(os.sep)

        dir_fd = self._walk_nofollow(base_dir, components[:-1])
        try:
            # Open final file with O_NOFOLLOW relative to verified dir_fd
            filename = components[-1]
            flags = self._mode_to_flags(mode) | os.O_NOFOLLOW
            try:
                fd = os.open(filename, flags, 0o644, dir_fd=dir_fd)
            except OSError as e:
                if e.errno in (errno.ELOOP, errno.ENOTDIR):
                    raise exceptions.unauthorized_access()
                raise
        finally:
            os.close(dir_fd)

        self._verify_read_permission(fd)
        return os.fdopen(fd, mode)

    def _verify_read_permission(self, fd: int) -> None:
        """
        Verify the requesting user has POSIX read permission on the opened fd.

        Closes the fd and raises unauthorized_access if the user lacks read,
        or if the user lookup fails.

        :param fd: open file descriptor to check
        """
        try:
            file_stat = os.fstat(fd)
            user_info = getpwnam(self.username)
            uid = user_info.pw_uid
            gid = user_info.pw_gid
            user_groups = os.getgrouplist(self.username, gid)

            if file_stat.st_uid == uid:
                has_read = bool(file_stat.st_mode & stat.S_IRUSR)
            elif file_stat.st_gid in user_groups:
                has_read = bool(file_stat.st_mode & stat.S_IRGRP)
            else:
                has_read = bool(file_stat.st_mode & stat.S_IROTH)

            if not has_read:
                raise exceptions.unauthorized_access()
        except Exception:
            os.close(fd)
            raise

    @staticmethod
    def _mode_to_flags(mode: str) -> int:
        """Map Python file mode string to os.O_* flags."""
        if mode in ('r', 'rb'):
            return os.O_RDONLY
        elif mode in ('w', 'wb'):
            return os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        elif mode in ('a', 'ab'):
            return os.O_WRONLY | os.O_CREAT | os.O_APPEND
        else:
            raise ValueError(f'Unsupported file mode: {mode}')

    def _sync_write(self, file_path: str, data: bytes):
        """Synchronous write using safe_open for use with run_in_executor."""
        primary_group_id = self.get_primary_group_id(self.username)
        uid = getpwnam(self.username).pw_uid
        gid = primary_group_id if primary_group_id is not None else -1
        with self.safe_open(file_path, 'wb') as f:
            f.write(data)
            os.fchown(f.fileno(), uid, gid)

    def is_file_browser_enabled(self) -> bool:
        return self.context.config().get_bool('shared-storage.enable_file_browser', required=True)

    def has_access(self, file: str) -> bool:
        try:
            user_home = self.get_user_home()
            if not file.startswith(user_home):
                raise exceptions.unauthorized_access()
            if '..' in file:
                raise exceptions.unauthorized_access()
            if Utils.is_empty(file):
                raise exceptions.invalid_params('file is required')
            if not Utils.is_file(file):
                raise exceptions.file_not_found(file)
            return True
        except:  # noqa
            return False

    def check_access(self, file: str, check_dir=False, check_read=True, check_write=True):
        if Utils.is_empty(file):
            raise exceptions.unauthorized_access()
        # only support absolute paths
        if '..' in file:
            raise exceptions.unauthorized_access()
        
        if not self.is_file_browser_enabled():
            raise exceptions.disabled_feature("FileBrowser")

        if not pathlib.Path(file).exists():
            # Validate the file path
            raise exceptions.unauthorized_access()

        data_mount_dir = self.context.config().get_string('shared-storage.home.mount_dir')
        is_data_mount = Utils.is_not_empty(data_mount_dir) and file.startswith(data_mount_dir)

        # do not allow any access to system folders
        tokens = file.split('/')
        if len(tokens) > 1 and tokens[1] in RESTRICTED_ROOT_FOLDERS and not is_data_mount:
            raise exceptions.unauthorized_access()

        # Sanitize file path to prevent command injection
        safe_file = shlex.quote(file)

        if check_dir:
            is_dir = self.shell.invoke(['su', self.username, '-c', f'test -d {safe_file}'])
            if is_dir.returncode != 0:
                raise exceptions.unauthorized_access()
        if check_read:
            can_read = self.shell.invoke(['su', self.username, '-c', f'test -r {safe_file}'])
            if can_read.returncode != 0:
                raise exceptions.unauthorized_access()
        if check_write:
            can_write = self.shell.invoke(['su', self.username, '-c', f'test -w {safe_file}'])
            if can_write.returncode != 0:
                raise exceptions.unauthorized_access()

    def list_files(self, request: ListFilesRequest) -> ListFilesResult:
        cwd = request.cwd
        user_home = self.get_user_home()

        if Utils.is_empty(cwd):
            cwd = user_home

        self.check_access(cwd, check_dir=True, check_read=True, check_write=False)
        
        # Sanitize cwd to prevent command injection
        safe_cwd = shlex.quote(cwd)
        result = self.shell.invoke(['su', self.username, '-c', f'ls {safe_cwd} -1'])
        if result.returncode != 0:
            raise exceptions.unauthorized_access()

        files = result.stdout.split(os.linesep)
        result = []
        for file in files:
            if Utils.is_empty(file):
                continue
            file_path = os.path.join(cwd, file)
            if os.path.islink(file_path):
                # skip symlinks to avoid any security risks
                continue

            if cwd == '/':
                if file in RESTRICTED_ROOT_FOLDERS:
                    continue

            try:
                file_stat = os.lstat(file_path)
            except FileNotFoundError:
                continue
            is_dir = stat.S_ISDIR(file_stat.st_mode)
            is_hidden = file.startswith('.')
            file_size = None
            if not is_dir:
                file_size = file_stat.st_size
            mod_date = arrow.get(file_stat.st_mtime).datetime
            result.append(FileData(
                file_id=Utils.shake_256(f'{file}{is_dir}', 5),
                name=file,
                size=file_size,
                mod_date=mod_date,
                is_dir=is_dir,
                is_hidden=is_hidden
            ))

        return ListFilesResult(
            cwd=cwd,
            listing=result
        )

    def read_file(self, request: ReadFileRequest) -> ReadFileResult:
        file = request.file

        if not Utils.is_file(file):
            raise exceptions.file_not_found(file)

        self.check_access(file, check_dir=False, check_read=True, check_write=False)

        if file.endswith('.que'):
            content_type = 'text/plain'
        else:
            content_type, encoding = mimetypes.guess_type(file)

        if Utils.is_binary_file(file):
            raise exceptions.soca_exception(
                error_code=errorcodes.FILE_BROWSER_NOT_A_TEXT_FILE,
                message='file is not a text file. download the binary file instead'
            )

        with self.safe_open(file, 'r') as f:
            content = f.read()

        return ReadFileResult(
            file=file,
            content_type=content_type,
            content=Utils.base64_encode(content)
        )

    def tail_file(self, request: TailFileRequest) -> TailFileResult:
        file = request.file

        if not Utils.is_file(file):
            raise exceptions.file_not_found(file)

        self.check_access(file, check_dir=False, check_read=True, check_write=False)

        if Utils.is_binary_file(file):
            raise exceptions.soca_exception(
                error_code=errorcodes.FILE_BROWSER_NOT_A_TEXT_FILE,
                message='file is not a text file. download the binary file instead.'
            )

        next_token = request.next_token

        lines = []
        line_count = Utils.get_as_int(request.line_count, TAIL_FILE_DEFAULT_LINE_COUNT)
        max_line_count = min(line_count, TAIL_FILE_MAX_LINE_COUNT)

        if Utils.is_not_empty(next_token):
            cursor_tokens = Utils.base64_decode(next_token).split(';')
            last_read = Utils.get_as_int(cursor_tokens[1])
            now = Utils.current_time_ms()

            if (now - last_read) < TAIL_FILE_MIN_INTERVAL_SECONDS * 1000:
                raise exceptions.soca_exception(error_code=errorcodes.FILE_BROWSER_TAIL_THROTTLE, message=f'tail file request throttled. subsequent requests should be called at {TAIL_FILE_MIN_INTERVAL_SECONDS} seconds frequency')

            file_handle = None
            try:
                file_handle = self.safe_open(file, 'r')
                offset = Utils.get_as_int(cursor_tokens[0])
                file_handle.seek(offset)

                while len(lines) < max_line_count:
                    line = file_handle.readline()
                    if line == '':
                        break
                    lines.append(line)

                cursor_tokens = [file_handle.tell(), Utils.current_time_ms()]
            finally:
                if file_handle is not None:
                    file_handle.close()
        else:
            # if cursor file does not exist, prefetch last N lines
            with self.safe_open(file, 'r') as f:
                prefetch_lines = list(deque(f, max_line_count))
                for line in prefetch_lines:
                    lines.append(line.strip())
                # seek to end of file and update cursor
                f.seek(0, os.SEEK_END)
                cursor_tokens = [f.tell(), Utils.current_time_ms()]

        if cursor_tokens is not None:
            next_token = Utils.base64_encode(f'{cursor_tokens[0]};{cursor_tokens[1]}')

        return TailFileResult(
            file=file,
            next_token=next_token,
            lines=lines,
            line_count=len(lines)
        )

    def save_file(self, request: SaveFileRequest) -> SaveFileResult:
        file = request.file
        if Utils.is_empty(file):
            raise exceptions.invalid_params('file is required')
        if not Utils.is_file(file):
            raise exceptions.file_not_found(file)
        if Utils.is_binary_file(file):
            raise exceptions.invalid_params('file is not a text file. upload the binary file instead')

        self.check_access(file, check_dir=False, check_read=True, check_write=True)

        content_base64 = request.content
        content = Utils.base64_decode(content_base64)

        with self.safe_open(file, 'w') as f:
            f.write(content)

        self.logger.info(f'{self.username} has modified the following file: "{file}"')

        return SaveFileResult()

    async def upload_files(self, cwd: str, files: List[Any]) -> Dict:
        """
        called from SocaServer to handle file upload routes
        :param cwd
        :param files:
        :return:
        """

        if Utils.is_empty(files):
            return {
                'success': False
            }

        user_home = self.get_user_home()
        if Utils.is_empty(cwd):
            raise exceptions.unauthorized_access()
        if not Utils.is_dir(cwd):
            raise exceptions.unauthorized_access()
        if not cwd.startswith(user_home):
            raise exceptions.unauthorized_access()
        if '..' in cwd:
            raise exceptions.unauthorized_access()

        if not self.is_file_browser_enabled():
            raise exceptions.disabled_feature("FileBrowser")

        files_uploaded = []
        files_skipped = []
        for file in files:
            secure_file_name = Utils.to_secure_filename(file.name)
            if Utils.is_empty(secure_file_name):
                files_skipped.append(file.name)
                continue
            file_path = os.path.join(cwd, secure_file_name)
            # use safe_open to prevent symlink-based TOCTOU attacks
            await asyncio.get_event_loop().run_in_executor(
                None, self._sync_write, file_path, file.body
            )

            files_uploaded.append(file_path)

        files_uploaded_to_string = '\n'.join([f'"{file}"' for file in files_uploaded])
        self.logger.info(f'{self.username} has uploaded the following files:\n{files_uploaded_to_string}')

        return {
            'success': True,
            'payload': {
                'files_uploaded': files_uploaded,
                'files_skipped': files_skipped
            }
        }

    def download_files(self, request: DownloadFilesRequest) -> str:
        files = Utils.get_as_list(request.files, [])
        if Utils.is_empty(files):
            raise exceptions.invalid_params('file is required')

        download_list = []
        for file in files:
            if Utils.is_empty(file):
                continue
            if '..' in file:
                raise exceptions.unauthorized_access()
            if Utils.is_empty(file):
                raise exceptions.invalid_params('file is required')
            if not Utils.is_file(file):
                raise exceptions.file_not_found(file)
            self.check_access(file, check_dir=False, check_read=True, check_write=False)
            download_list.append(file)

        primary_group_id = self.get_primary_group_id(self.username)
        downloads_dir = os.path.join(self.get_user_home(), 'idea_downloads')

        # Create the downloads directory if it doesn't exist.
        # safe_chown_dir below will verify the path is a real directory (not a symlink)
        # via O_NOFOLLOW, so even if an attacker swaps it between makedirs and chown,
        # the chown will safely refuse.
        os.makedirs(downloads_dir, exist_ok=True)

        if primary_group_id is None:
            self.logger.warning('primary group id not found, chown will not change group ownership')
        uid = getpwnam(self.username).pw_uid
        gid = primary_group_id if primary_group_id is not None else -1
        self.safe_chown_dir(downloads_dir, uid, gid)

        short_uuid = Utils.short_uuid()
        zip_file_path = os.path.join(downloads_dir, f'{short_uuid}.zip')
        with ZipFile(zip_file_path, 'w') as zipfile:
            for download_file in download_list:
                with self.safe_open(download_file, 'rb') as f:
                    archive_name = os.path.relpath(download_file, self.get_user_home())
                    with zipfile.open(archive_name, 'w') as zf:
                        shutil.copyfileobj(f, zf)

        # Use safe_open (O_NOFOLLOW) + fchown to avoid TOCTOU on the zip file path
        with self.safe_open(zip_file_path, 'rb') as zf:
            os.fchown(zf.fileno(), uid, gid)

        download_list_to_string = '\n'.join([f'"{file}"' for file in download_list])
        self.logger.info(f'{self.username} has downloaded the following files:\n{download_list_to_string}')
        return zip_file_path

    def create_file(self, request: CreateFileRequest) -> CreateFileResult:

        cwd = request.cwd

        filename = request.filename
        if Utils.is_empty(filename):
            raise exceptions.invalid_params('filename is required')

        self.check_access(cwd, check_dir=True, check_read=True, check_write=True)

        original_filename = filename

        # ensure file name is the leaf name and not directory
        filename = os.path.basename(filename)
        if original_filename != filename:
            raise exceptions.invalid_params(f'invalid name: {original_filename}, name cannot contain "/" or special characters')

        # ensure file name is ascii characters and nothing funky going on in file name
        filename = Utils.to_secure_filename(filename)
        if original_filename != filename:
            raise exceptions.invalid_params(f'invalid characters in name: {original_filename}')

        create_path = os.path.join(cwd, filename)
        if Utils.is_symlink(create_path):
            raise exceptions.invalid_params(f'a symbolic link already exists at: {create_path}')

        is_folder = Utils.get_as_bool(request.is_folder, False)
        primary_group_id = self.get_primary_group_id(self.username)
        if primary_group_id is None:
            self.logger.warning('primary group id not found, chown will not change group ownership')
        uid = getpwnam(self.username).pw_uid
        gid = primary_group_id if primary_group_id is not None else -1

        if is_folder:
            if Utils.is_dir(create_path):
                raise exceptions.invalid_params(f'directory: {filename} already exists under: {cwd}')
            os.makedirs(create_path)
            self.safe_chown_dir(create_path, uid, gid)
        else:
            if Utils.is_file(create_path):
                raise exceptions.invalid_params(f'file: {filename} already exists under: {cwd}')
            with self.safe_open(create_path, 'w') as f:
                f.write('')
                os.fchown(f.fileno(), uid, gid)

        self.logger.info(f'{self.username} has created the following file: "{create_path}"')
        return CreateFileResult()

    def delete_files(self, request: DeleteFilesRequest) -> DeleteFilesResult:
        files = request.files
        if Utils.is_empty(files):
            raise exceptions.invalid_params('files[] is required')

        user_home = os.path.realpath(self.get_user_home())

        directories = []
        regular_files = []
        symlinks = []

        for file in files:

            file = file.rstrip('/')

            if os.path.islink(file):
                # For symlinks, only verify the parent is within user's home
                # (the symlink target may point outside, which is allowed)
                resolved_parent = os.path.realpath(os.path.dirname(file))
                if not (resolved_parent == user_home or resolved_parent.startswith(user_home + '/')):
                    raise exceptions.unauthorized_access()
                parent_dir = os.path.dirname(file)
                self.check_access(parent_dir, check_dir=True, check_read=False, check_write=True)
                symlinks.append(file)
            else:
                # For regular files and directories, verify the resolved path is within user's home
                resolved = os.path.realpath(file)
                if not (resolved == user_home or resolved.startswith(user_home + '/')):
                    raise exceptions.unauthorized_access()
                if Utils.is_dir(file):
                    self.check_access(file, check_read=False, check_write=True)
                    directories.append(file)
                else:
                    self.check_access(file, check_read=False, check_write=True)
                    regular_files.append(file)

        for file in regular_files:
            self.safe_delete_file(file)
            self.logger.info(f'{self.username} deleted file: "{file}"')

        for link in symlinks:
            self.safe_delete_symlink(link)
            self.logger.info(f'{self.username} deleted symlink: "{link}"')

        for directory in directories:
            self.safe_delete_dir(directory)
            self.logger.info(f'{self.username} deleted directory: "{directory}"')

        return DeleteFilesResult()

    @staticmethod
    def get_primary_group_id(username: str):
        """Returns primary group id for the username"""
        try:
            result = getpwnam(username)
        except KeyError:
            result = None
        if result is not None:
            return result.pw_gid
        return None
