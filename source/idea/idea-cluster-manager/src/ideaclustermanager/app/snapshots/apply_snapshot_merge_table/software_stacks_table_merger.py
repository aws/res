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

from ideaclustermanager.app.snapshots.helpers.apply_snapshot_observability_helper import (
    ApplySnapshotObservabilityHelper,
    ApplyResourceStatus,
)
from ideaclustermanager.app.snapshots.helpers.merged_record_utils import (
    MergedRecordDelta,
    MergedRecordActionType,
)
from ideaclustermanager.app.snapshots.apply_snapshot_merge_table.merge_table import (
    MergeTable,
)
import ideaclustermanager.app.snapshots.helpers.db_utils as db_utils

from ideadatamodel.snapshots.snapshot_model import TableName
from ideadatamodel import errorcodes, exceptions

from ideasdk.context import SocaContext

from typing import Dict, List, Optional, Tuple
import copy

TABLE_NAME = TableName.SOFTWARE_STACKS_TABLE_NAME


class SoftwareStacksTableMerger(MergeTable):
    """
    Helper class for merging the software stacks table
    """

    def merge(self, context: SocaContext, table_data_to_merge: List[Dict],
              dedup_id: str, merged_record_deltas: Dict[TableName, List[MergedRecordDelta]],
              logger: ApplySnapshotObservabilityHelper) -> Tuple[List[MergedRecordDelta], bool]:
        project_table_deltas = merged_record_deltas.get(TableName.PROJECTS_TABLE_NAME, [])
        project_id_mappings = {
            project_delta.snapshot_record["project_id"]: project_delta.resolved_record["project_id"]
            for project_delta in project_table_deltas
        }

        record_deltas: List[MergedRecordDelta] = []
        for software_stack_db_record in table_data_to_merge:
            if not software_stack_db_record or not software_stack_db_record.get(db_utils.SOFTWARE_STACK_DB_NAME_KEY):
                logger.debug(TABLE_NAME, "", ApplyResourceStatus.SKIPPED,
                             f"{db_utils.SOFTWARE_STACK_DB_NAME_KEY} is empty")
                continue

            stack_name = software_stack_db_record[db_utils.SOFTWARE_STACK_DB_NAME_KEY]
            try:
                resolved_record, action_type = self.resolve_record(
                    context, copy.deepcopy(software_stack_db_record),
                    dedup_id, project_id_mappings, logger)
                if not action_type:
                    logger.debug(TABLE_NAME, stack_name, ApplyResourceStatus.SKIPPED, "software stack is unchanged")
                    continue

                record_delta = MergedRecordDelta(
                    snapshot_record=software_stack_db_record,
                    resolved_record=resolved_record,
                    action_performed=action_type,
                )
                stack_name = resolved_record[db_utils.SOFTWARE_STACK_DB_NAME_KEY]

                if record_delta.action_performed == MergedRecordActionType.CREATE:
                    software_stack = db_utils.convert_db_dict_to_software_stack_object(record_delta.resolved_record)
                    software_stack = context.vdc_client.create_software_stack(software_stack)
                    record_delta.resolved_record = db_utils.convert_software_stack_object_to_db_dict(software_stack)
                    record_deltas.append(record_delta)
            except exceptions.SocaException as e:
                if e.error_code == errorcodes.INVALID_PARAMS and e.message.startswith("Invalid software_stack.ami_id"):
                    logger.debug(TABLE_NAME, stack_name, ApplyResourceStatus.SKIPPED, f"AMI ID of the software stack is not available in the current region: {str(e)}")
                    continue
                raise e
            except Exception as e:
                if "is not a valid VirtualDesktopBaseOS" in str(e):
                    logger.debug(TABLE_NAME, stack_name, ApplyResourceStatus.SKIPPED, f"{str(e)}. Base OS is no longer supported.")
                    continue
                logger.error(TABLE_NAME, stack_name, ApplyResourceStatus.FAILED_APPLY, str(e))
                return record_deltas, False

            logger.debug(TABLE_NAME, stack_name, ApplyResourceStatus.APPLIED, "adding software stack succeeded")

        return record_deltas, True

    def rollback(
        self,
        context: SocaContext,
        record_deltas: List[MergedRecordDelta],
        logger: ApplySnapshotObservabilityHelper,
    ) -> None:
        while record_deltas:
            record_delta = record_deltas[0]
            if record_delta.action_performed == MergedRecordActionType.CREATE:
                # Currently we only add new software stacks instead of updating existing ones when applying a snapshot.
                # Add this checking here for handling updated records in the future.
                try:
                    context.vdc_client.delete_software_stack(
                        db_utils.convert_db_dict_to_software_stack_object(record_delta.resolved_record),
                    )
                except Exception as e:
                    logger.error(TABLE_NAME, record_delta.resolved_record[db_utils.SOFTWARE_STACK_DB_NAME_KEY],
                                 ApplyResourceStatus.FAILED_ROLLBACK, str(e))
                    raise e

                logger.debug(TABLE_NAME, record_delta.resolved_record[db_utils.SOFTWARE_STACK_DB_NAME_KEY],
                             ApplyResourceStatus.ROLLBACKED,"removing software stack succeeded")

            record_deltas.pop(0)

    @staticmethod
    def resolve_record(
        context: SocaContext,
        db_entry: dict,
        dedup_id: str,
        project_id_mappings: Dict[str, str],
        logger: ApplySnapshotObservabilityHelper,
    ) -> (Dict, Optional[MergedRecordActionType]):
        SoftwareStacksTableMerger._resolve_project_ids(db_entry, project_id_mappings)

        stack_name = db_entry[db_utils.SOFTWARE_STACK_DB_NAME_KEY]
        software_stacks_by_name = context.vdc_client.get_software_stacks_by_name(stack_name)
        if software_stacks_by_name:
            snapshot_software_stack = db_utils.convert_db_dict_to_software_stack_object(db_entry)
            if any(existing_software_stack == snapshot_software_stack for existing_software_stack in software_stacks_by_name):
                return db_entry, None

            # If software stacks with the exact same name already exists, rename the stack name by appending the dedup ID.
            # This merger will add new software stacks instead of overriding the existing ones to resolve conflicts.
            stack_name = MergeTable.unique_resource_id_generator(stack_name, dedup_id)
            db_entry[db_utils.SOFTWARE_STACK_DB_NAME_KEY] = stack_name

            logger.debug(TABLE_NAME, stack_name, reason="Software stack with the same name exists under the current environment. "
                                                        "Created a new record with the dedup ID appended to the software stack name")

        return db_entry, MergedRecordActionType.CREATE

    @staticmethod
    def _resolve_project_ids(
        db_entry: Dict,
        project_id_mappings: Dict[str, str],
    ):
        projects = db_entry.get(db_utils.SOFTWARE_STACK_DB_PROJECTS_KEY, [])
        for index in range(len(projects)):
            project_id = projects[index]
            if not project_id_mappings.get(project_id):
                # project is unchanged, so it's not in the merged record delta.
                continue
            projects[index] = project_id_mappings[project_id]
        db_entry[db_utils.SOFTWARE_STACK_DB_PROJECTS_KEY] = projects
