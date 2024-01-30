#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

__all__ = (
    'SyncAllGroupsTask',
    'SyncAllUsersTask',
    'SyncFromAD'
)

from typing import Dict
import ideaclustermanager
from ideaclustermanager.app.tasks.base_task import BaseTask
from ideasdk.utils import Utils

import time


class SyncAllGroupsTask(BaseTask):

    def __init__(self, context: ideaclustermanager.AppContext):
        self.context = context
        self.logger = context.logger(self.get_name())

    def get_name(self) -> str:
        return 'adsync.sync-all-groups'

    def invoke(self, payload: Dict):
        self.logger.info('starting sync for groups from AD')
        # todo
        # do something
        # self.context.ldap_client.<>
        # self.context.accounts.<>


class SyncAllUsersTask(BaseTask):

    def __init__(self, context: ideaclustermanager.AppContext):
        self.context = context
        self.logger = context.logger(self.get_name())

    def get_name(self) -> str:
        return 'adsync.sync-all-users'

    def invoke(self, payload: Dict):
        self.logger.info('starting sync for users from AD')
        # todo
        # self.context.ldap_client.<>
        # self.context.accounts.<>


class SyncFromAD(BaseTask):

    def __init__(self, context: ideaclustermanager.AppContext):
        self.context = context
        self.logger = context.logger(self.get_name())

    def get_name(self) -> str:
        return 'adsync.sync-from-ad'

    def invoke(self, payload: Dict):
        self.logger.info('Starting sync from AD')
        start_time = time.time()
        ldap_groups = self.context.ad_sync.fetch_all_ldap_groups()
        group_addition_failures = self.context.ad_sync.sync_all_groups(ldap_groups)
        self.context.ad_sync.sync_all_users(ldap_groups, group_addition_failures)
        self.logger.info(f"-------------TIME: {time.time()-start_time}------------")
