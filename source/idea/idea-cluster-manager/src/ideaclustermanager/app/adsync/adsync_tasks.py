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
from ideadatamodel import exceptions

from ldap.filter import escape_filter_chars # noqa
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

    @staticmethod
    def validate_ldap_filter(ldap_filter: str):
        if not (ldap_filter.startswith("(") and ldap_filter.endswith(")")):
            raise exceptions.invalid_params(
                'Invalid LDAP filter: Filter string must start with "(" and end with ")".'
                ' Check https://ldap.com/ldap-filters/ for the LDAP filter syntax.'
            )

    def invoke(self, payload: Dict):
        self.logger.info('Starting sync from AD')
        start_time = time.time()
        groups_filter = self.context.config().get_string('directoryservice.groups_filter')
        self.validate_ldap_filter(groups_filter)
        users_filter = self.context.config().get_string('directoryservice.users_filter')
        self.validate_ldap_filter(users_filter)

        ldap_groups = self.context.ad_sync.fetch_ldap_groups(groups_filter)
        group_addition_failures = self.context.ad_sync.sync_groups(ldap_groups)
        self.context.ad_sync.sync_users(ldap_groups, group_addition_failures, users_filter)

        self.logger.info(f"-------------TIME: {time.time()-start_time}------------")
