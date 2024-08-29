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
from ideasdk.utils import Utils
from ideadatamodel import exceptions, errorcodes, constants

from ideaclustermanager.app.accounts.ldapclient.abstract_ldap_client import AbstractLDAPClient, LdapClientOptions
from ideaclustermanager.app.accounts.ldapclient.ldap_utils import LdapUtils

from typing import Dict, Optional
import ldap  # noqa
import time


class ActiveDirectoryClient(AbstractLDAPClient):

    def __init__(self, context: SocaContext, options: LdapClientOptions, logger=None):
        if logger is None:
            logger = context.logger('active-directory-client')
        super().__init__(context, options, logger=logger)

        if Utils.is_empty(self.directory_id) and (self.ds_provider == constants.DIRECTORYSERVICE_AWS_MANAGED_ACTIVE_DIRECTORY):
            raise exceptions.general_exception(f'options.directory_id is required when using {constants.DIRECTORYSERVICE_AWS_MANAGED_ACTIVE_DIRECTORY}')
        if Utils.is_empty(self.ad_netbios):
            raise exceptions.general_exception('options.ad_netbios is required')

    @property
    def ds_provider(self) -> str:
        return self.context.config().get_string('directoryservice.provider', required=True)

    @property
    def directory_id(self) -> str:
        return self.options.directory_id

    @property
    def ad_netbios(self) -> str:
        return self.options.ad_netbios

    @property
    def ldap_uri(self) -> str:
        if Utils.is_not_empty(self.options.uri):
            return self.options.uri
        return f'ldap://{self.domain_name}'

    @property
    def ldap_root_bind(self) -> str:
        return f'{self.ldap_root_username}@{self.domain_name}'

    @property
    def ldap_computers_base(self) -> str:
        ou_computers = self.context.config().get_string('directoryservice.computers.ou', required=True)
        if '=' in ou_computers:
            return ou_computers
        return f'ou={ou_computers},ou={self.ad_netbios},{self.ldap_base}'

    @property
    def ldap_user_base(self) -> str:
        ou_users = self.context.config().get_string('directoryservice.users.ou', required=True)
        if '=' in ou_users:
            return ou_users
        return f'ou={ou_users},ou={self.ad_netbios},{self.ldap_base}'

    @property
    def ldap_user_filterstr(self) -> str:
        return '(objectClass=user)'

    @property
    def ldap_group_base(self) -> str:
        ou_groups = self.context.config().get_string('directoryservice.groups.ou', required=True)
        if '=' in ou_groups:
            return ou_groups
        return f'ou={ou_groups},ou={self.ad_netbios},{self.ldap_base}'

    @property
    def ldap_group_filterstr(self) -> str:
        return '(objectClass=group)'

    @property
    def ldap_sudoers_group_name(self) -> str:
        return self.context.config().get_string('directoryservice.sudoers.group_name', required=True)

    @property
    def ldap_sudoers_group_dn(self) -> str:
        sudoers_group_name = self.ldap_sudoers_group_name
        tokens = [
            f'cn={sudoers_group_name}'
        ]
        ou_sudoers = self.context.config().get_string('directoryservice.sudoers.ou')
        if Utils.is_not_empty(ou_sudoers):
            if '=' in ou_sudoers:
                tokens.append(ou_sudoers)
            else:
                tokens.append(f'ou={ou_sudoers}')
                tokens.append(self.ldap_base)
        return ','.join(tokens)

    @property
    def ldap_sudoers_base(self) -> str:
        return self.ldap_user_base

    @property
    def ldap_sudoer_filterstr(self) -> str:
        return f'(&(objectClass=user)(memberOf={self.ldap_sudoers_group_dn}))'

    def build_sudoer_filterstr(self, username: str) -> str:
        return f'(&{self.ldap_sudoer_filterstr[2:-1]}(sAMAccountName={username}))'

    def build_samaccountname_filterstr(self, username: str) -> str:
        return f'(&{self.ldap_user_filterstr}(sAMAccountName={username}))'

    def build_nestedgroup_membership_filterstr(self, username: str, groupname: str) -> str:
        return f"(&(memberOf:1.2.840.113556.1.4.1941:={self.build_group_dn(group_name=groupname)})(objectCategory=person)(objectClass=user)(sAMAccountName={username}))"

    def build_email_filterstr(self, email: str) -> str:
        return f'(&{self.ldap_user_filterstr}(mail={email}))'

    def build_nestedgroup_email_membership_filterstr(self, email: str, groupname: str) -> str:
        return f"(&(memberOf:1.2.840.113556.1.4.1941:={self.build_group_dn(group_name=groupname)})(objectCategory=person)(objectClass=user)(mail={email}))"

    def get_user(self, username: str, required_group=None, trace=True) -> Optional[Dict]:

        # required_group will recursively validate user in a group
        # only works in MS-AD LDAP environments
        results = self.search_s(
            base=self.ldap_user_base,
            filterstr=self.build_nestedgroup_membership_filterstr(username=username, groupname=required_group) if required_group else self.build_samaccountname_filterstr(username=username),
            trace=trace
        )

        if len(results) == 0:
            return None

        return self.convert_ldap_user(results[0][1])

    def get_user_by_email(self, email: str, required_group=None, trace=True) -> Optional[Dict]:

        # required_group will recursively validate user in a group
        # only works in MS-AD LDAP environments
        results = self.search_s(
            base=self.ldap_user_base,
            filterstr=self.build_nestedgroup_email_membership_filterstr(email=email, groupname=required_group) if required_group else self.build_email_filterstr(email=email),
            trace=trace
        )

        if len(results) == 0:
            return None

        return self.convert_ldap_user(results[0][1])

    def change_password(self, username: str, password: str):

        ad_provider = self.context.config().get_string('directoryservice.provider', required=True)

        if ad_provider == constants.DIRECTORYSERVICE_ACTIVE_DIRECTORY:
            self.logger.info(f'change_passwd() for Active Directory provider {ad_provider} - NOOP')
            return

        elif ad_provider == constants.DIRECTORYSERVICE_AWS_MANAGED_ACTIVE_DIRECTORY:
            try:
                self.context.aws().ds().reset_user_password(
                    DirectoryId=self.directory_id,
                    UserName=username,
                    NewPassword=password
                )
            except self.context.aws().ds().exceptions.UserDoesNotExistException:
                raise exceptions.soca_exception(
                    error_code=errorcodes.AUTH_USER_NOT_FOUND,
                    message=f'{username} is not yet synced with AD Domain Controllers. Please wait for a few minutes and try again.'
                )
        else:
            raise exceptions.soca_exception(
                error_code=errorcodes.VALIDATION_FAILED,
                message=f'Unable to update password. Active Directory provider is unsupported: {ad_provider}'
            )

    def create_service_account(self, username: str, password: str) -> Dict:
        user_principal_name = f'{username}@{self.domain_name}'

        user_dn = self.build_user_dn(username)
        existing = self.is_existing_user(username)

        readonly = self.is_readonly()

        if existing:
            if readonly:
                return self.get_user(username)
            else:
                raise exceptions.invalid_params(f'username already exists: {username}')

        user_attrs = [
            ('objectClass', [
                Utils.to_bytes('top'),
                Utils.to_bytes('person'),
                Utils.to_bytes('user'),
                Utils.to_bytes('organizationalPerson')
            ]),
            ('displayName', [Utils.to_bytes(username)]),
            ('sAMAccountName', [Utils.to_bytes(username)]),
            ('userPrincipalName', [Utils.to_bytes(user_principal_name)]),
            ('cn', [Utils.to_bytes(username)]),
            ('uid', [Utils.to_bytes(username)])
        ]
        self.add_s(user_dn, user_attrs)
        self.wait_for_user_creation(username, interval=5, min_success=5)
        self.change_password(username=username, password=password)
        self.add_sudo_user(username=username)
        return self.get_user(username)

    def sync_user(self, *,
                  uid: int,
                  gid: int,
                  username: str,
                  email: str,
                  login_shell: str,
                  home_dir: str) -> Dict:

        user_principal_name = f'{username}@{self.domain_name}'

        user_dn = self.build_user_dn(username)
        existing = self.is_existing_user(username)

        readonly = self.is_readonly()

        if readonly:
            if existing:
                self.logger.info(f'Working with existing user / read-only DS: {username}')
                # TODO - validate the fetched user has the required attributes
                # TODO - update the DynamoDB with the fetched uid/gid/info
                return self.get_user(username)
            else:
                # todo - how to notify caller?
                pass

        if existing:
            user_attrs = [
                ('mail', [Utils.to_bytes(email)]),
                ('uidNumber', [Utils.to_bytes(str(uid))]),
                ('gidNumber', [Utils.to_bytes(str(gid))]),
                ('loginShell', [Utils.to_bytes(login_shell)]),
                ('homeDirectory', [Utils.to_bytes(home_dir)])
            ]
        else:
            user_attrs = [
                ('objectClass', [
                    Utils.to_bytes('top'),
                    Utils.to_bytes('person'),
                    Utils.to_bytes('user'),
                    Utils.to_bytes('organizationalPerson')
                ]),
                ('displayName', [Utils.to_bytes(username)]),
                ('mail', [Utils.to_bytes(email)]),
                ('sAMAccountName', [Utils.to_bytes(username)]),
                ('userPrincipalName', [Utils.to_bytes(user_principal_name)]),
                ('cn', [Utils.to_bytes(username)]),
                ('uid', [Utils.to_bytes(username)]),
                ('uidNumber', [Utils.to_bytes(str(uid))]),
                ('gidNumber', [Utils.to_bytes(str(gid))]),
                ('loginShell', [Utils.to_bytes(login_shell)]),
                ('homeDirectory', [Utils.to_bytes(home_dir)])
            ]

        if existing:
            modify_user_attrs = []
            for user_attr in user_attrs:
                modify_user_attr = list(user_attr)
                modify_user_attr.insert(0, ldap.MOD_REPLACE)
                modify_user_attrs.append(tuple(modify_user_attr))
            self.modify_s(user_dn, modify_user_attrs)
        else:
            self.add_s(user_dn, user_attrs)
            # todo
            self.logger.info('Applying user updates to enable user')
            # Make sure the user account is enabled in AD.
            # This is a two-step process
            enable_attrs = [
                (ldap.MOD_REPLACE, 'userAccountControl', [Utils.to_bytes('512')])
            ]
            self.modify_s(user_dn, enable_attrs)
            self.wait_for_user_creation(username)

        return self.get_user(username)

    def sync_group(self, group_name: str, gid: int) -> Dict:
        group_dn = self.build_group_dn(group_name)

        existing = self.is_existing_group(group_name)

        readonly = self.is_readonly()
        if readonly:
            if existing:
                self.logger.info(f'Read-only DS - returning {group_name} lookup')
                return self.get_group(group_name)
            else:
                self.logger.error(f'Unable to find existing group [{group_name}] in read-only Directory Service. Has it been created?')
                # fall back to default group?
                # todo how to notify the caller?

        if existing:
            group_attrs = [
                ('gidNumber', [Utils.to_bytes(str(gid))])
            ]
        else:
            group_attrs = [
                ('objectClass', [
                    Utils.to_bytes('top'),
                    Utils.to_bytes('group')
                ]),
                ('gidNumber', [Utils.to_bytes(str(gid))]),
                ('sAMAccountName', [Utils.to_bytes(group_name)]),
                ('cn', [Utils.to_bytes(group_name)])
            ]

        if existing:
            modify_group_attrs = []
            for group_attr in group_attrs:
                modify_group_attr = list(group_attr)
                modify_group_attr.insert(0, ldap.MOD_REPLACE)
                modify_group_attrs.append(tuple(modify_group_attr))
            self.modify_s(group_dn, modify_group_attrs)
        else:
            self.add_s(group_dn, group_attrs)
            self.wait_for_group_creation(group_name)

        return self.get_group(group_name)

    def add_sudo_user(self, username: str):
        user_dn = self.build_user_dn(username)
        sudoer_group_dn = self.ldap_sudoers_group_dn

        group_attrs = [
            (ldap.MOD_ADD, 'member', [Utils.to_bytes(user_dn)])
        ]

        self.modify_s(sudoer_group_dn, group_attrs)

    def remove_sudo_user(self, username: str):
        user_dn = self.build_user_dn(username)
        sudoer_group_dn = self.ldap_sudoers_group_dn

        group_attrs = [
            (ldap.MOD_DELETE, 'member', [Utils.to_bytes(user_dn)])
        ]

        self.modify_s(sudoer_group_dn, group_attrs)

    def wait_for_group_creation(self, group_name: str, interval: float = 2, max_attempts: int = 15, min_success: int = 3):
        """
        wait for group to be replicated across domain controllers.
        :param group_name:
        :param interval:
        :param max_attempts:
        :param min_success:
        :return:
        """
        current_attempt = 0
        current_success = 0
        while current_attempt < max_attempts:
            if not self.is_existing_group(group_name):
                current_attempt += 1
            else:
                current_success += 1
                if current_success == min_success:
                    break
            time.sleep(interval)

    def wait_for_user_creation(self, username: str, interval: float = 2, max_attempts: int = 15, min_success: int = 3):
        """
        wait for user to be replicated across domain controllers.
        :param username:
        :param interval:
        :param max_attempts:
        :param min_success:
        :return:
        """
        current_attempt = 0
        current_success = 0
        while current_attempt < max_attempts:
            if not self.is_existing_user(username):
                current_attempt += 1
            else:
                current_success += 1
                if current_success == min_success:
                    break
            time.sleep(interval)
