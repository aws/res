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

from ideaclustermanager.app.authz.db.roles_dao import RolesDAO
from ideaclustermanager.app.snapshots.helpers.apply_snapshot_observability_helper import ApplySnapshotObservabilityHelper, ApplyResourceStatus
from ideaclustermanager.app.snapshots.helpers.merged_record_utils import MergedRecordDelta, MergedRecordActionType
from ideaclustermanager.app.snapshots.apply_snapshot_merge_table.merge_table import MergeTable
import ideaclustermanager.app.snapshots.helpers.db_utils as db_utils
from ideasdk.utils import Utils

from ideadatamodel.snapshots.snapshot_model import TableName
from ideadatamodel import (
    DeleteRoleRequest,
    CreateRoleRequest,
    Role,
    errorcodes,
    exceptions,
)

from ideasdk.context import SocaContext

import copy
from typing import Dict, List, Optional, Tuple

TABLE_NAME = TableName.ROLES_TABLE_NAME

class RolesTableMerger(MergeTable):
    """
    Helper class for merging the roles table
    """

    def merge(self, context: SocaContext, table_data_to_merge: List[Dict],
              dedup_id: str, merged_record_deltas: Dict[TableName, List[MergedRecordDelta]],
              logger: ApplySnapshotObservabilityHelper) -> Tuple[List[MergedRecordDelta], bool]:
        
        record_deltas: List[MergedRecordDelta] = []

        # If roles table snapshot records were present, migrate them to new roles table
        for role_snapshot_record in table_data_to_merge:
            if not role_snapshot_record or not role_snapshot_record.get(db_utils.ROLE_DB_ROLE_ID_KEY):
                continue

            role_id = role_snapshot_record[db_utils.ROLE_DB_ROLE_ID_KEY]

            try:
                resolved_record, action_type = self.resolve_record(
                    context, copy.deepcopy(role_snapshot_record), logger)
                if not action_type:
                    logger.debug(TABLE_NAME, role_id, ApplyResourceStatus.SKIPPED, "role is unchanged")
                    continue

                record_delta = MergedRecordDelta(
                    snapshot_record=role_snapshot_record,
                    resolved_record=resolved_record,
                    action_performed=action_type
                )

                if record_delta.action_performed == MergedRecordActionType.CREATE:
                    role = RolesDAO.convert_from_db(record_delta.resolved_record)
                    create_role_request = CreateRoleRequest(role=role)
                    response = context.roles.create_role(create_role_request)
                    record_delta.resolved_record = RolesDAO.convert_to_db(role)
                    record_deltas.append(record_delta)
            except exceptions.SocaException as e:
                if e.error_code == errorcodes.ROLE_ALREADY_EXISTS:
                    logger.warning(TABLE_NAME, role_id, None, f"{e.message}. Skipping migration for this record")
                else:
                    logger.error(TABLE_NAME, role_id, ApplyResourceStatus.FAILED_APPLY, str(e))
                    return record_deltas, False
                
            logger.debug(TABLE_NAME, role_id, ApplyResourceStatus.APPLIED, "migrating role succeeded")

        return record_deltas, True

    def rollback(self, context: SocaContext, record_deltas: List[MergedRecordDelta], logger: ApplySnapshotObservabilityHelper) -> None:
        while record_deltas:
            record_delta = record_deltas.pop()
            role_id = record_delta.resolved_record.get(db_utils.ROLE_DB_ROLE_ID_KEY, "")
            role = RolesDAO.convert_from_db(record_delta.resolved_record)

            # Currently we only add new roles instead of updating existing ones when applying a snapshot.
            if record_delta.action_performed == MergedRecordActionType.CREATE:
                try:
                    delete_role_request = DeleteRoleRequest(role_id=role.role_id)
                    response = context.roles.delete_role(delete_role_request)
                except Exception as e:
                    logger.error(TABLE_NAME, role_id, ApplyResourceStatus.FAILED_ROLLBACK, str(e))
                    raise e
                logger.debug(TABLE_NAME, role_id, ApplyResourceStatus.ROLLBACKED,"removing role succeeded")

    @staticmethod
    def resolve_record(context: SocaContext, db_entry: dict, logger: ApplySnapshotObservabilityHelper) -> (Dict, Optional[MergedRecordActionType]):
        role_id = db_entry[db_utils.ROLE_DB_ROLE_ID_KEY]
        
        existing_role = context.roles.roles_dao.get_role(role_id=role_id)
        if not existing_role:
            # Corresponding snapshot entry does not exist in DB. Create a new role in DB
            return db_entry, MergedRecordActionType.CREATE
        else:
            # If a record exists with same keys in DB, skip creation. Duplicate records should not be created for this table
            logger.debug(TABLE_NAME, "", None, f"role with ID {role_id} exists. Skipping snapshot application for this record")
            return db_entry, None
