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

from ideasdk.context import SocaContext
from ideadatamodel.auth import User
from ideasdk.utils import Utils
from ideadatamodel import exceptions, errorcodes

import time
import os
import shutil
import pwd
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend as crypto_default_backend

from ideaclustermanager.app.accounts.auth_constants import USER_HOME_DIR_BASE
from ideasdk.shell import ShellInvoker


class UserHomeDirectory:

    def __init__(self, context: SocaContext, user: User):
        self._context = context
        self._logger = context.logger('user-home-init')
        self.user = user
        self._shell = ShellInvoker(self._logger)

    @property
    def home_dir(self) -> str:
        return self.user.home_dir

    @property
    def ssh_dir(self) -> str:
        return os.path.join(self.user.home_dir, '.ssh')

    @staticmethod
    def validate_and_sanitize_key_format(key_format: str) -> str:
        if Utils.is_empty(key_format):
            raise exceptions.invalid_params('key_format is required')
        key_format = key_format.strip().lower()
        if key_format not in ('ppk', 'pem'):
            raise exceptions.invalid_params('key_format must be one of [pem, ppk]')
        return key_format

    def get_key_name(self, key_format: str) -> str:
        key_format = self.validate_and_sanitize_key_format(key_format)
        cluster_name = self._context.cluster_name()
        username = self.user.username
        return f'{username}_{cluster_name}_privatekey.{key_format}'

    def get_key_material(self, key_format: str, platform: str = 'linux') -> str:
        """
        read the user's private key from user's ~/.ssh directory
        add \r\n (for platform = 'windows) or \n (for platform = 'linux' or 'osx')
        :param key_format: one of [ppk, pem]
        :param platform: one of [windows, linux, osx]
        :return: private key content
        """

        if Utils.is_empty(platform):
            platform = 'linux'

        id_rsa_file = os.path.join(self.ssh_dir, 'id_rsa')
        if not Utils.is_empty(id_rsa_file):
            exceptions.general_exception(f'private key not found in home directory for user: {self.user.username}')

        key_format = self.validate_and_sanitize_key_format(key_format)

        def read_private_key_content(file: str) -> str:
            with open(file, 'r') as f:
                private_key_content = f.read()

            lines = private_key_content.splitlines()
            if platform in ('linux', 'osx'):
                return '\n'.join(lines)
            elif platform == 'windows':
                return '\r\n'.join(lines)

            # default
            return '\n'.join(lines)

        if key_format == 'pem':
            return read_private_key_content(id_rsa_file)

        elif key_format == 'ppk':
            result = self._shell.invoke('command -v puttygen', shell=True)
            if result.returncode != 0:
                raise exceptions.general_exception('puttygen binary not found in PATH')
            putty_gen_bin = result.stdout
            if not os.access(putty_gen_bin, os.X_OK):
                os.chmod(putty_gen_bin, 0o700)

            id_rsa_ppk_file = os.path.join(self.ssh_dir, 'id_rsa.ppk')
            if not Utils.is_file(id_rsa_ppk_file):
                result = self._shell.invoke([
                    'su',
                    self.user.username,
                    '-c',
                    f'{putty_gen_bin} {id_rsa_file} -o {id_rsa_ppk_file}'
                ])
                if result.returncode != 0:
                    raise exceptions.general_exception(f'failed to generate .ppk file: {result}')

            return read_private_key_content(id_rsa_ppk_file)
