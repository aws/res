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
from ideadatamodel import exceptions

from ideaclustermanager.app.accounts.ldapclient.abstract_ldap_client import AbstractLDAPClient, LdapClientOptions
from ideaclustermanager.app.accounts.ldapclient.ldap_utils import LdapUtils

from typing import Dict
import ldap  # noqa


class OpenLDAPClient(AbstractLDAPClient):

    def __init__(self, context: SocaContext, options: LdapClientOptions, logger=None):
        if logger is None:
            logger = context.logger('openldap-client')
        super().__init__(context, options, logger=logger)

    @property
    def ldap_root_bind(self) -> str:
        return f'sAMAccountName={self.ldap_root_username},{self.ldap_base}'

    @property
    def ldap_user_base(self) -> str:
        return f'ou=People,{self.ldap_base}'

    @property
    def ldap_user_filterstr(self) -> str:
        return '(objectClass=posixAccount)'

    @property
    def ldap_group_base(self) -> str:
        return f'ou=Group,{self.ldap_base}'

    @property
    def ldap_group_filterstr(self) -> str:
        return '(objectClass=posixGroup)'

    def build_group_filterstr(self, group_name: str = None, username: str = None) -> str:
        filterstr = self.ldap_group_filterstr
        if group_name is not None:
            filterstr = f'{filterstr}(cn={group_name})'
        if username is not None:
            filterstr = f'{filterstr}(memberUid={username})'
        return f'(&{filterstr})'

    @property
    def ldap_sudoers_base(self) -> str:
        return f'ou=Sudoers,{self.ldap_base}'

    @property
    def ldap_sudoer_filterstr(self) -> str:
        return '(objectClass=sudoRole)'

    def build_sudoer_dn(self, username: str) -> str:
        return f'cn={username},{self.ldap_sudoers_base}'

    def change_password(self, username: str, password: str):
        encrypted_password = LdapUtils.encrypt_password(password)
        user_dn = self.build_user_dn(username)
        user_attrs = [
            (ldap.MOD_REPLACE, 'userPassword', [Utils.to_bytes(encrypted_password)])
        ]

        self.modify_s(user_dn, user_attrs)

    def create_service_account(self, username: str, password: str):
        raise exceptions.general_exception('not supported for OpenLDAP')

    def sync_user(self, *,
                  uid: int,
                  gid: int,
                  username: str,
                  email: str,
                  login_shell: str,
                  home_dir: str) -> Dict:
        user_dn = self.build_user_dn(username)
        user_attrs = [
            ('objectClass', [
                Utils.to_bytes('top'),
                Utils.to_bytes('person'),
                Utils.to_bytes('posixAccount'),
                Utils.to_bytes('shadowAccount'),
                Utils.to_bytes('inetOrgPerson'),
                Utils.to_bytes('organizationalPerson')
            ]),
            ('uid', [Utils.to_bytes(username)]),
            ('uidNumber', [Utils.to_bytes(str(uid))]),
            ('gidNumber', [Utils.to_bytes(str(gid))]),
            ('mail', [Utils.to_bytes(email)]),
            ('cn', [Utils.to_bytes(username)]),
            ('sn', [Utils.to_bytes(username)]),
            ('loginShell', [Utils.to_bytes(login_shell)]),
            ('homeDirectory', [Utils.to_bytes(home_dir)])
        ]

        if self.is_existing_user(username):
            modify_user_attrs = []
            for user_attr in user_attrs:
                modify_user_attr = list(user_attr)
                modify_user_attr.insert(0, ldap.MOD_REPLACE)
                modify_user_attrs.append(tuple(modify_user_attr))
            self.modify_s(user_dn, modify_user_attrs)
        else:
            self.add_s(user_dn, user_attrs)

        return self.get_user(username)

    def sync_group(self, group_name: str, gid: int) -> Dict:
        group_dn = self.build_group_dn(group_name)
        group_attrs = [
            ('objectClass', [
                Utils.to_bytes('top'),
                Utils.to_bytes('posixGroup')
            ]),
            ('gidNumber', [Utils.to_bytes(str(gid))]),
            ('cn', [Utils.to_bytes(group_name)])
        ]

        if self.is_existing_group(group_name):
            modify_group_attrs = []
            for group_attr in group_attrs:
                modify_group_attr = list(group_attr)
                modify_group_attr.insert(0, ldap.MOD_REPLACE)
                modify_group_attrs.append(tuple(modify_group_attr))
            self.modify_s(group_dn, modify_group_attrs)
        else:
            self.add_s(group_dn, group_attrs)

        return self.get_group(group_name)

    def add_sudo_user(self, username: str):
        user_dn = self.build_sudoer_dn(username)
        user_attrs = [
            ('objectClass', [
                Utils.to_bytes('top'),
                Utils.to_bytes('sudoRole')
            ]),
            ('sudoHost', [Utils.to_bytes('ALL')]),
            ('sudoUser', [Utils.to_bytes(username)]),
            ('sudoCommand', [Utils.to_bytes('ALL')])
        ]

        self.add_s(user_dn, user_attrs)

    def remove_sudo_user(self, username: str):
        user_dn = self.build_sudoer_dn(username)
        self.delete_s(user_dn)
