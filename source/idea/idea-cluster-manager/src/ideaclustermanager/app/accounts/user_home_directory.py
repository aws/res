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
from ideadatamodel import exceptions

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

    def own_path(self, path: str):
        shutil.chown(path, user=self.user.username, group=Utils.get_as_int(pwd.getpwnam(self.user.username).pw_gid, default=0))

    def initialize_ssh_dir(self):
        os.makedirs(self.ssh_dir, exist_ok=True)
        os.chmod(self.ssh_dir, 0o700)
        self.own_path(self.ssh_dir)

        id_rsa_file = os.path.join(self.ssh_dir, 'id_rsa')

        # if an existing id_rsa file already exists, return
        if Utils.is_file(id_rsa_file):
            return

        key = rsa.generate_private_key(
            backend=crypto_default_backend(),
            public_exponent=65537,
            key_size=2048
        )
        private_key = key.private_bytes(
            crypto_serialization.Encoding.PEM,
            crypto_serialization.PrivateFormat.TraditionalOpenSSL,
            crypto_serialization.NoEncryption())
        public_key = key.public_key().public_bytes(
            crypto_serialization.Encoding.OpenSSH,
            crypto_serialization.PublicFormat.OpenSSH
        )

        with open(id_rsa_file, 'w') as f:
            f.write(Utils.from_bytes(private_key))
        os.chmod(id_rsa_file, 0o600)
        self.own_path(id_rsa_file)

        id_rsa_pub_file = os.path.join(self.ssh_dir, 'id_rsa.pub')
        with open(id_rsa_pub_file, 'w') as f:
            f.write(Utils.from_bytes(public_key))
        self.own_path(id_rsa_pub_file)

        authorized_keys_file = os.path.join(self.ssh_dir, 'authorized_keys')
        with open(authorized_keys_file, 'w') as f:
            f.write(Utils.from_bytes(public_key))
        os.chmod(id_rsa_file, 0o600)
        self.own_path(authorized_keys_file)

    def initialize_home_dir(self):
        os.makedirs(self.home_dir, exist_ok=True)
        os.chmod(self.home_dir, 0o700)
        self.own_path(self.home_dir)

        skeleton_files = [
            '/etc/skel/.bashrc',
            '/etc/skel/.bash_profile',
            '/etc/skel/.bash_logout'
        ]

        for src_file in skeleton_files:
            dest_file = os.path.join(self.home_dir, os.path.basename(src_file))
            if Utils.is_file(dest_file):
                continue
            shutil.copy(src_file, dest_file)
            self.own_path(dest_file)

    def initialize(self):
        # wait for system to sync the newly created user by using system libraries to resolve the user
        # this happens on a fresh installation of auth-server, where all system services have just started
        # and a new clusteradmin user is created.
        # although the user is created in directory services, it's not yet synced with the local system
        # If you continue to see this log message it may indicate that the underlying cluster-manager
        # host is not probably linked to the back-end directory service in some fashion.
        while True:
            try:
                pwd.getpwnam(self.user.username)
                break
            except KeyError:
                self._logger.info(f'{self.user.username} not available yet. waiting for user to be synced ...')
                time.sleep(5)

        self.initialize_home_dir()
        self.initialize_ssh_dir()

    def archive(self):
        if not Utils.is_dir(self.home_dir):
            return

        archive_dir = os.path.join(USER_HOME_DIR_BASE, f'{self.user.username}_{Utils.file_system_friendly_timestamp()}')
        shutil.move(self.home_dir, archive_dir)
        os.chown(archive_dir, 0, 0)
        os.chmod(archive_dir, 0o700)

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
