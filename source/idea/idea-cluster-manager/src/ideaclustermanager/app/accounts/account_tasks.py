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

__all__ = (
    'SyncUserInDirectoryServiceTask',
    'CreateUserHomeDirectoryTask',
    'SyncGroupInDirectoryServiceTask',
)

from ideasdk.utils import Utils
from ideadatamodel import exceptions, errorcodes

import ideaclustermanager
from ideaclustermanager.app.tasks.base_task import BaseTask
from ideaclustermanager.app.accounts.user_home_directory import UserHomeDirectory

from typing import Dict
import os
import pathlib
import shutil


class SyncGroupInDirectoryServiceTask(BaseTask):

    def __init__(self, context: ideaclustermanager.AppContext):
        self.context = context
        self.logger = context.logger(self.get_name())

    def get_name(self) -> str:
        return 'accounts.sync-group'

    def invoke(self, payload: Dict):
        group_name = payload['group_name']
        group = self.context.accounts.group_dao.get_group(group_name)

        if self.context.ldap_client.is_readonly():
            self.logger.info(f'Read-only Directory service - NOOP for {self.get_name()}')
            return

        delete_group = False
        if group is not None:
            if group['enabled']:
                self.logger.info(f'sync group: {group_name} directory service ...')
                self.context.ldap_client.sync_group(
                    group_name=group['group_name'],
                    gid=group['gid']
                )
            else:
                delete_group = True
        else:
            delete_group = True

        if delete_group:
            self.logger.info(f'deleting group: {group_name} from directory service ...')
            if self.context.ldap_client.is_existing_group(group_name):
                self.context.ldap_client.delete_group(group_name)

class SyncUserInDirectoryServiceTask(BaseTask):

    def __init__(self, context: ideaclustermanager.AppContext):
        self.context = context
        self.logger = context.logger(self.get_name())

    def get_name(self) -> str:
        return 'accounts.sync-user'

    def invoke(self, payload: Dict):
        username = payload['username']
        user = self.context.accounts.user_dao.get_user(username)
        enabled = user['enabled']
        sudo = Utils.get_value_as_bool('sudo', user, False)

        if self.context.ldap_client.is_readonly():
            self.logger.info(f'sync user: Read-only Directory service - sync {username} NOOP ... returning')
            return

        if enabled:
            self.logger.info(f'sync user: {username} TO directory service ...')
            self.context.ldap_client.sync_group(
                gid=user['gid']
            )
            self.context.ldap_client.sync_user(
                uid=user['uid'],
                gid=user['gid'],
                username=user['username'],
                email=user['email'],
                login_shell=user['login_shell'],
                home_dir=user['home_dir']
            )

            if sudo:
                if not self.context.ldap_client.is_sudo_user(username):
                    self.context.ldap_client.add_sudo_user(username)
            else:
                if self.context.ldap_client.is_sudo_user(username):
                    self.context.ldap_client.remove_sudo_user(username)

        else:
            self.logger.info(f'deleting user: {username} from directory service ...')
            if self.context.ldap_client.is_existing_user(username):
                self.context.ldap_client.delete_user(username)
            if self.context.ldap_client.is_sudo_user(username):
                self.context.ldap_client.remove_sudo_user(username)

class CreateUserHomeDirectoryTask(BaseTask):

    def __init__(self, context: ideaclustermanager.AppContext):
        self.context = context
        self.logger = context.logger(self.get_name())

    def get_name(self) -> str:
        return 'accounts.create-home-directory'

    def invoke(self, payload: Dict):
        username = payload['username']
        user = self.context.accounts.get_user(username)
        UserHomeDirectory(
            context=self.context,
            user=user
        ).initialize()
