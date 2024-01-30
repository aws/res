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
from ideaclustermanager.app.accounts.db.user_dao import UserDAO
from ideaclustermanager.app.snapshots.helpers.apply_snapshot_observability_helper import ApplySnapshotObservabilityHelper, ApplyResourceStatus
from ideaclustermanager.app.snapshots.helpers.merged_record_utils import MergedRecordDelta, MergedRecordActionType
from ideaclustermanager.app.snapshots.apply_snapshot_merge_table.merge_table import MergeTable
from ideadatamodel.snapshots.snapshot_model import TableName
from ideadatamodel import errorcodes, exceptions, constants, User

from typing import Dict, List, Tuple

TABLE_NAME = TableName.USERS_TABLE_NAME


class UsersTableMerger(MergeTable):
    """
    Helper class for merging the accounts.users table
    """
    def merge(self, context: SocaContext, table_data_to_merge: List[Dict],
              _dedup_id: str, _merged_record_deltas: Dict[TableName, List[MergedRecordDelta]],
              logger: ApplySnapshotObservabilityHelper) -> Tuple[List[MergedRecordDelta], bool]:
        record_deltas: List[MergedRecordDelta] = []
        for user_db_record in table_data_to_merge:
            user_to_merge = UserDAO.convert_from_db(user_db_record)
            try:
                existing_user = context.accounts.get_user(user_to_merge.username)
            except exceptions.SocaException as e:
                if e.error_code == errorcodes.AUTH_USER_NOT_FOUND:
                    logger.debug(TABLE_NAME, user_to_merge.username, ApplyResourceStatus.SKIPPED, "the user doesn't exist in the current environment")
                    continue
                raise e
            except Exception as e:
                logger.error(TABLE_NAME, user_to_merge.username, ApplyResourceStatus.FAILED_APPLY, str(e))
                return record_deltas, False

            if user_to_merge.role == existing_user.role:
                logger.debug(TABLE_NAME, user_to_merge.username, ApplyResourceStatus.SKIPPED, "the user role is unchanged")
                continue

            try:
                self.apply(context, user_to_merge, logger)
                record_deltas.append(
                    MergedRecordDelta(
                        original_record=UserDAO.convert_to_db(existing_user),
                        snapshot_record=user_db_record,
                        action_performed=MergedRecordActionType.UPDATE
                    )
                )
            except Exception as e:
                logger.error(TABLE_NAME, user_to_merge.username, ApplyResourceStatus.FAILED_APPLY, str(e))
                return record_deltas, False

        return record_deltas, True

    def rollback(self, context: SocaContext, record_deltas: List[MergedRecordDelta], logger: ApplySnapshotObservabilityHelper) -> None:
        while record_deltas:
            record_delta = record_deltas[0]
            user = UserDAO.convert_from_db(record_delta.original_record)
            if record_delta.action_performed == MergedRecordActionType.UPDATE:
                # Currently we only update admin permissions for existing users.
                # Add this checking here for handling new users in the future.
                try:
                    self.apply(context, user, logger, True)
                except Exception as e:
                    logger.error(TABLE_NAME, user.username, ApplyResourceStatus.FAILED_ROLLBACK, str(e))
                    raise e

            record_deltas.pop(0)

    @staticmethod
    def apply(context: SocaContext, user: User, logger: ApplySnapshotObservabilityHelper, is_rolling_back: bool = False) -> None:
        expected_resource_status = ApplyResourceStatus.ROLLBACKED if is_rolling_back else ApplyResourceStatus.APPLIED
        if user.role == constants.ADMIN_ROLE:
            context.accounts.add_admin_user(user.username)
            logger.debug(TABLE_NAME, user.username, expected_resource_status, "setting admin privileges succeeded")
        else:
            context.accounts.remove_admin_user(user.username)
            logger.debug(TABLE_NAME, user.username, expected_resource_status, "removing admin privileges succeeded")
