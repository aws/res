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
    'SyncGroupInDirectoryServiceTask',
)

from ideasdk.utils import Utils

import ideaclustermanager
from ideaclustermanager.app.tasks.base_task import BaseTask

from typing import Dict


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

