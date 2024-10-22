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
import arrow
import stat
import mimetypes
import shutil
import pathlib
from pwd import getpwnam
import aiofiles
from typing import Dict, List, Any
from zipfile import ZipFile
from collections import deque

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
        # return os.path.join(self.context.config().get_string('shared-storage.home.mount_dir', required=True), self.username)

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

        if check_dir:
            is_dir = self.shell.invoke(['su', self.username, '-c', f'test -d "{file}"'])
            if is_dir.returncode != 0:
                raise exceptions.unauthorized_access()
        if check_read:
            can_read = self.shell.invoke(['su', self.username, '-c', f'test -r "{file}"'])
            if can_read.returncode != 0:
                raise exceptions.unauthorized_access()
        if check_write:
            can_write = self.shell.invoke(['su', self.username, '-c', f'test -w "{file}"'])
            if can_write.returncode != 0:
                raise exceptions.unauthorized_access()

    def list_files(self, request: ListFilesRequest) -> ListFilesResult:
        cwd = request.cwd
        user_home = self.get_user_home()

        if Utils.is_empty(cwd):
            cwd = user_home

        self.check_access(cwd, check_dir=True, check_read=True, check_write=False)

        result = self.shell.invoke(['su', self.username, '-c', f'ls "{cwd}" -1'])
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

            file_stat = os.stat(file_path)
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

        with open(file, 'r') as f:
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
                file_handle = open(file, 'r')
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
            with open(file, 'r') as f:
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

        with open(file, 'w') as f:
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
            # use aiofiles to not block the event loop
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file.body)

            primary_group_id = self.get_primary_group_id(self.username)
            if primary_group_id is None:
                self.logger.warning('primary group id not found, chown will not change group ownership')
            shutil.chown(file_path, user=self.username, group=primary_group_id)
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
        if Utils.is_symlink(downloads_dir):
            # prevent symlink/hijack attacks
            raise exceptions.invalid_params(f'a symbolic link already exists at: {downloads_dir}')

        os.makedirs(downloads_dir, exist_ok=True)
        if primary_group_id is None:
            self.logger.warning('primary group id not found, chown will not change group ownership')
        shutil.chown(downloads_dir, user=self.username, group=primary_group_id)

        short_uuid = Utils.short_uuid()
        zip_file_path = os.path.join(downloads_dir, f'{short_uuid}.zip')
        with ZipFile(zip_file_path, 'w') as zipfile:
            for download_file in download_list:
                zipfile.write(download_file)

        shutil.chown(zip_file_path, user=self.username, group=primary_group_id)

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
        if is_folder:
            if Utils.is_dir(create_path):
                raise exceptions.invalid_params(f'directory: {filename} already exists under: {cwd}')
            os.makedirs(create_path)
        else:
            if Utils.is_file(create_path):
                raise exceptions.invalid_params(f'file: {filename} already exists under: {cwd}')
            with open(create_path, 'w') as f:
                f.write('')

        primary_group_id = self.get_primary_group_id(self.username)
        if primary_group_id is None:
            self.logger.warning('primary group id not found, chown will not change group ownership')
        shutil.chown(create_path, self.username, primary_group_id)

        self.logger.info(f'{self.username} has created the following file: "{create_path}"')
        return CreateFileResult()

    def delete_files(self, request: DeleteFilesRequest) -> DeleteFilesResult:
        files = request.files
        if Utils.is_empty(files):
            raise exceptions.invalid_params('files[] is required')

        directories = []
        regular_files = []
        symlinks = []

        for file in files:

            self.check_access(file, check_read=False, check_write=True)

            if Utils.is_dir(file):
                directories.append(file)
            elif os.path.islink(file):
                symlinks.append(file)
            else:
                regular_files.append(file)

        for file in regular_files:
            os.remove(file)
            self.logger.info(f'{self.username} deleted file: "{file}"')

        for link in symlinks:
            os.unlink(link)
            self.logger.info(f'{self.username} deleted symlink: "{link}"')

        for directory in directories:
            shutil.rmtree(directory, ignore_errors=True)
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
            return result[3]
        return None
