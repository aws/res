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

from ideaclustermanager.app.authz.db.role_assignments_dao import RoleAssignmentsDAO
from ideaclustermanager.app.projects.db.projects_dao import ProjectsDAO
from ideaclustermanager.app.snapshots.helpers.apply_snapshot_observability_helper import ApplySnapshotObservabilityHelper, ApplyResourceStatus
from ideaclustermanager.app.snapshots.helpers.merged_record_utils import MergedRecordDelta, MergedRecordActionType
from ideaclustermanager.app.snapshots.apply_snapshot_merge_table.merge_table import MergeTable
import ideaclustermanager.app.snapshots.helpers.db_utils as db_utils
from ideasdk.utils import Utils

from ideadatamodel.snapshots.snapshot_model import TableName
from ideadatamodel import (
    DeleteRoleAssignmentRequest,
    DeleteRoleAssignmentErrorResponse,
    PutRoleAssignmentRequest,
    PutRoleAssignmentErrorResponse,
    ListRoleAssignmentsRequest,
    RoleAssignment,
    errorcodes,
    exceptions,
)

from ideasdk.context import SocaContext

import copy
from typing import Dict, List, Optional, Tuple

TABLE_NAME = TableName.ROLE_ASSIGNMENTS_TABLE_NAME

class RoleAssignmentsTableMerger(MergeTable):
    """
    Helper class for merging the role-assignments table
    """

    def merge(self, context: SocaContext, table_data_to_merge: List[Dict],
              dedup_id: str, merged_record_deltas: Dict[TableName, List[MergedRecordDelta]],
              logger: ApplySnapshotObservabilityHelper) -> Tuple[List[MergedRecordDelta], bool]:
        project_table_deltas = merged_record_deltas.get(TableName.PROJECTS_TABLE_NAME, [])
        project_id_mappings = {
            project_delta.snapshot_record[db_utils.PROJECT_DB_PROJECT_ID_KEY]: project_delta.resolved_record[db_utils.PROJECT_DB_PROJECT_ID_KEY]
            for project_delta in project_table_deltas
        }

        record_deltas: List[MergedRecordDelta] = []

        # If role assignments table snapshot records were present, migrate them to new role assignments table
        for role_assignment_snapshot_record in table_data_to_merge:
            if not role_assignment_snapshot_record or not role_assignment_snapshot_record.get(db_utils.ROLE_ASSIGNMENT_DB_ACTOR_KEY) or not role_assignment_snapshot_record.get(db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY):
                continue

            role_assignment_actor_key = role_assignment_snapshot_record[db_utils.ROLE_ASSIGNMENT_DB_ACTOR_KEY]
            role_assignment_resource_key = role_assignment_snapshot_record[db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY]
            composite_key = f"{role_assignment_actor_key}#{role_assignment_resource_key}"

            try:
                resolved_record, action_type = self.resolve_record(
                    context, copy.deepcopy(role_assignment_snapshot_record),
                    project_id_mappings, logger)
                if not action_type:
                    logger.debug(TABLE_NAME, composite_key, ApplyResourceStatus.SKIPPED, "role assignment is unchanged")
                    continue

                record_delta = MergedRecordDelta(
                    snapshot_record=role_assignment_snapshot_record,
                    resolved_record=resolved_record,
                    action_performed=action_type
                )

                if record_delta.action_performed == MergedRecordActionType.CREATE:
                    role_assignment = RoleAssignmentsDAO.convert_from_db(record_delta.resolved_record)
                    put_role_assignment_request = PutRoleAssignmentRequest(
                        request_id = Utils.short_uuid(),
                        actor_id = role_assignment.actor_id,
                        resource_id = role_assignment.resource_id,
                        resource_type = role_assignment.resource_type,
                        actor_type = role_assignment.actor_type,
                        role_id = role_assignment.role_id,
                        )
                    response = context.role_assignments.put_role_assignment(put_role_assignment_request)
                    if isinstance(response, PutRoleAssignmentErrorResponse):
                        if response.error_code in [errorcodes.AUTH_USER_NOT_FOUND, errorcodes.AUTH_GROUP_NOT_FOUND]:
                            logger.warning(TABLE_NAME, composite_key, None, "Actor not found. Skipping migration for this record")
                            continue
                        else:
                            raise exceptions.SocaException(response.error_code, response.message)
                    record_delta.resolved_record = RoleAssignmentsDAO.convert_to_db(role_assignment)
                    record_deltas.append(record_delta)
            except Exception as e:
                logger.error(TABLE_NAME, composite_key, ApplyResourceStatus.FAILED_APPLY, str(e))
                return record_deltas, False
            logger.debug(TABLE_NAME, composite_key, ApplyResourceStatus.APPLIED, "migrating role assignments succeeded")

        return record_deltas, True

    def rollback(self, context: SocaContext, record_deltas: List[MergedRecordDelta], logger: ApplySnapshotObservabilityHelper) -> None:
        while record_deltas:
            record_delta = record_deltas.pop()
            role_assignment_actor_key = record_delta.resolved_record.get(db_utils.ROLE_ASSIGNMENT_DB_ACTOR_KEY, "")
            role_assignment_resource_key = record_delta.resolved_record.get(db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY, "")
            composite_key = f"{role_assignment_actor_key}#{role_assignment_resource_key}"
            role_assignment = RoleAssignmentsDAO.convert_from_db(record_delta.resolved_record)

            # Currently we only add new role assignments instead of updating existing ones when applying a snapshot.
            if record_delta.action_performed == MergedRecordActionType.CREATE:
                try:
                    delete_role_assignment_request = DeleteRoleAssignmentRequest(
                        request_id = Utils.short_uuid(),
                        actor_id = role_assignment.actor_id,
                        resource_id = role_assignment.resource_id,
                        resource_type = role_assignment.resource_type,
                        actor_type = role_assignment.actor_type,
                        )
                    response = context.role_assignments.delete_role_assignment(delete_role_assignment_request)
                    if isinstance(response, DeleteRoleAssignmentErrorResponse):
                        raise exceptions.SocaException(response.error_code, response.message)
                except Exception as e:
                    logger.error(TABLE_NAME, composite_key, ApplyResourceStatus.FAILED_ROLLBACK, str(e))
                    raise e
                logger.debug(TABLE_NAME, composite_key, ApplyResourceStatus.ROLLBACKED,"removing role assignment succeeded")

    @staticmethod
    def resolve_record(context: SocaContext, db_entry: dict, project_id_mappings: Dict[str, str],
                       logger: ApplySnapshotObservabilityHelper) -> (Dict, Optional[MergedRecordActionType]):
        RoleAssignmentsTableMerger._resolve_project_ids(db_entry, project_id_mappings)
        role_assignment_actor_key = db_entry[db_utils.ROLE_ASSIGNMENT_DB_ACTOR_KEY]
        role_assignment_resource_key = db_entry[db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY]
        
        try:
            existing_role_assignment = context.role_assignments.get_role_assignment(actor_key = role_assignment_actor_key, resource_key = role_assignment_resource_key)
            if not existing_role_assignment:
                # Corresponding snapshot entry does not exist in DB. Create a new role assignment in DB
                return db_entry, MergedRecordActionType.CREATE
            else:
                # If a record exists with same keys in DB, skip creation. Duplicate records should not be created for this table
                logger.debug(TABLE_NAME, "", None, f"role assignment record with {role_assignment_actor_key} actor key and {role_assignment_resource_key} resoruce key exists. Skipping snapshot application for this record")
                return db_entry, None
        except exceptions.SocaException as e:
            if e.error_code in [errorcodes.AUTH_USER_NOT_FOUND, errorcodes.AUTH_GROUP_NOT_FOUND]:
                logger.warning(TABLE_NAME, role_assignment_actor_key, None, "Actor not found. Skipping migration for this record")
            elif e.error_code in [errorcodes.PROJECT_NOT_FOUND]:
                logger.warning(TABLE_NAME, role_assignment_resource_key, None, "Project not found. Skipping migration for this record")
            else:
                raise e
            return db_entry, None

    @staticmethod
    def _resolve_project_ids(
        db_entry: Dict,
        project_id_mappings: Dict[str, str]
    ):
        if db_entry.get(db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_KEY) == db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_PROJECT_VALUE:
            project_id = db_entry.get(db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_ID_KEY)
            if project_id_mappings.get(project_id) is not None:
                db_entry[db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_ID_KEY] = project_id_mappings.get(project_id)
                db_entry[db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY] = f"{project_id_mappings.get(project_id)}:{db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_PROJECT_VALUE}"
        # Add more resource types here once we add support for them in role assignments
