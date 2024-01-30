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

from ideaclustermanager.app.snapshots.apply_snapshot_merge_table.merge_table import MergeTable
from ideaclustermanager.app.snapshots.helpers.merged_record_utils import MergedRecordDelta, MergedRecordActionType
from ideaclustermanager.app.snapshots.helpers.apply_snapshot_observability_helper import ApplySnapshotObservabilityHelper, ApplyResourceStatus
import ideaclustermanager.app.snapshots.helpers.db_utils as db_utils

from ideadatamodel import (
    VirtualDesktopPermission,
    errorcodes,
    exceptions,
)
from ideadatamodel.snapshots.snapshot_model import TableName

from ideasdk.context import SocaContext

import copy
from typing import Dict, List, Optional, Tuple

TABLE_NAME = TableName.PERMISSION_PROFILES_TABLE_NAME


class PermissionProfilesTableMerger(MergeTable):
    def merge(self, context: SocaContext, table_data_to_merge: List[Dict],
              dedup_id: str, _merged_record_deltas: Dict[TableName, List[MergedRecordDelta]],
              logger: ApplySnapshotObservabilityHelper) -> Tuple[List[MergedRecordDelta], bool]:
        record_deltas: List[MergedRecordDelta] = []

        try:
            permission_types = context.vdc_client.get_base_permissions()
        except Exception as e:
            logger.error(TABLE_NAME, "", ApplyResourceStatus.FAILED_APPLY, str(e))
            return [], False

        for permission_profile_db_record in table_data_to_merge:
            if not permission_profile_db_record or not permission_profile_db_record.get(db_utils.PERMISSION_PROFILE_DB_HASH_KEY):
                logger.warning(TABLE_NAME, "", ApplyResourceStatus.SKIPPED, "permission profile ID is empty")
                continue

            profile_id = permission_profile_db_record[db_utils.PERMISSION_PROFILE_DB_HASH_KEY]
            try:
                resolved_record, action_type = self.resolve_record(
                    context, copy.deepcopy(permission_profile_db_record),
                    dedup_id, permission_types, logger)
                if not action_type:
                    logger.debug(TABLE_NAME, profile_id, ApplyResourceStatus.SKIPPED, "permission profile is unchanged")
                    continue

                record_delta = MergedRecordDelta(
                    snapshot_record=permission_profile_db_record,
                    resolved_record=resolved_record,
                    action_performed=action_type,
                )
                profile_id = resolved_record[db_utils.PERMISSION_PROFILE_DB_HASH_KEY]

                if record_delta.action_performed == MergedRecordActionType.CREATE:
                    permission_profile = db_utils.convert_db_dict_to_permission_profile_object(record_delta.resolved_record, permission_types)
                    permission_profile = context.vdc_client.create_permission_profile(permission_profile)
                    record_delta.resolved_record = db_utils.convert_permission_profile_object_to_db_dict(permission_profile, permission_types)
                    record_deltas.append(record_delta)
            except Exception as e:
                logger.error(TABLE_NAME, profile_id, ApplyResourceStatus.FAILED_APPLY, str(e))
                return record_deltas, False

            logger.debug(TABLE_NAME, profile_id, ApplyResourceStatus.APPLIED, "adding permission profile succeeded")

        return record_deltas, True

    def rollback(self, context: SocaContext, record_deltas: List[MergedRecordDelta], logger: ApplySnapshotObservabilityHelper):
        while record_deltas:
            record_delta = record_deltas[0]
            profile_id = record_delta.resolved_record.get(db_utils.PERMISSION_PROFILE_DB_HASH_KEY, "")
            if record_delta.action_performed == MergedRecordActionType.CREATE:
                # Currently we only add new permission profiles instead of updating existing ones when applying a snapshot.
                # Add this checking here for handling updated records in the future.
                try:
                    context.vdc_client.delete_permission_profile(profile_id)
                except Exception as e:
                    logger.error(TABLE_NAME, profile_id, ApplyResourceStatus.FAILED_ROLLBACK, str(e))
                    raise e

                logger.debug(TABLE_NAME, profile_id, ApplyResourceStatus.ROLLBACKED, "removing permission profile succeeded")

            record_deltas.pop(0)

    @staticmethod
    def resolve_record(context: SocaContext, db_entry: dict, dedup_id: str,
                       permission_types: list[VirtualDesktopPermission],
                       logger: ApplySnapshotObservabilityHelper) -> (Dict, Optional[MergedRecordActionType]):
        profile_id = db_entry[db_utils.PERMISSION_PROFILE_DB_HASH_KEY]
        try:
            existing_permission_profile = context.vdc_client.get_permission_profile(profile_id)
            snapshot_permission_profile = db_utils.convert_db_dict_to_permission_profile_object(db_entry, permission_types)
            if existing_permission_profile == snapshot_permission_profile:
                return db_entry, None

            # Permission profile with the same profile ID exists.
            # This merger will add a new permission profile by appending the dedup ID to its profile ID instead of overriding the existing ones,
            # since the existing permission profiles might be used by active VDIs under the new environment.
            profile_id = MergeTable.unique_resource_id_generator(profile_id, dedup_id)
            db_entry[db_utils.PERMISSION_PROFILE_DB_HASH_KEY] = profile_id

            logger.debug(TABLE_NAME, profile_id, reason="Permission profile with the same ID exists under the current environment. "
                                                        "Created a new record with the dedup ID appended to the permission profile id")
        except exceptions.SocaException as e:
            if e.error_code != errorcodes.INVALID_PARAMS:
                raise e

        return db_entry, MergedRecordActionType.CREATE
