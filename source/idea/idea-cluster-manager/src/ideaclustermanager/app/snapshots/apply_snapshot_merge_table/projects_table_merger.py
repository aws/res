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

from ideaclustermanager.app.projects.db.projects_dao import ProjectsDAO
from ideaclustermanager.app.snapshots.helpers.apply_snapshot_observability_helper import ApplySnapshotObservabilityHelper, ApplyResourceStatus
from ideaclustermanager.app.snapshots.helpers.merged_record_utils import MergedRecordDelta, MergedRecordActionType
from ideaclustermanager.app.snapshots.apply_snapshot_merge_table.merge_table import MergeTable

from ideadatamodel.snapshots.snapshot_model import TableName
from ideadatamodel import (
    GetProjectRequest,
    CreateProjectRequest,
    DeleteProjectRequest,
    UpdateProjectRequest,
    Project,
    errorcodes,
    exceptions,
)

from ideasdk.context import SocaContext

import copy
from typing import Dict, List, Optional, Tuple

PROJECTS_TABLE_PROJECT_NAME_KEY = "name"
TABLE_NAME = TableName.PROJECTS_TABLE_NAME


class ProjectsTableMerger(MergeTable):
    """
    Helper class for merging the projects table
    """

    def merge(self, context: SocaContext, table_data_to_merge: List[Dict],
              dedup_id: str, _merged_record_deltas: Dict[TableName, List[MergedRecordDelta]],
              logger: ApplySnapshotObservabilityHelper) -> Tuple[List[MergedRecordDelta], bool]:
        record_deltas: List[MergedRecordDelta] = []
        for project_db_record in table_data_to_merge:
            if not project_db_record or not project_db_record.get(PROJECTS_TABLE_PROJECT_NAME_KEY):
                logger.debug(TABLE_NAME, "", ApplyResourceStatus.SKIPPED, "project name is empty")
                continue

            project_name = project_db_record[PROJECTS_TABLE_PROJECT_NAME_KEY]
            try:
                resolved_record, action_type = self.resolve_record(
                    context, copy.deepcopy(project_db_record),
                    dedup_id, logger)
                if not action_type:
                    logger.debug(TABLE_NAME, project_name, ApplyResourceStatus.SKIPPED, "project is unchanged")
                    continue

                record_delta = MergedRecordDelta(
                    snapshot_record=project_db_record,
                    resolved_record=resolved_record,
                    action_performed=action_type
                )
                project_name = resolved_record[PROJECTS_TABLE_PROJECT_NAME_KEY]

                if record_delta.action_performed == MergedRecordActionType.CREATE:
                    project = ProjectsDAO.convert_from_db(record_delta.resolved_record)
                    project.ldap_groups = []
                    project.users = []
                    project.enable_budgets = self._budget_is_enabled_and_exists(context, project, logger)
                    project = context.projects.create_project(CreateProjectRequest(project=project)).project
                    record_delta.resolved_record = ProjectsDAO.convert_to_db(project)
                    record_deltas.append(record_delta)
            except Exception as e:
                logger.error(TABLE_NAME, project_name, ApplyResourceStatus.FAILED_APPLY, str(e))
                return record_deltas, False

            self._add_groups_and_users_to_project(context, project_db_record, record_delta, logger)

            logger.debug(TABLE_NAME, project_name, ApplyResourceStatus.APPLIED, "adding project succeeded")

        return record_deltas, True

    def rollback(self, context: SocaContext, record_deltas: List[MergedRecordDelta], logger: ApplySnapshotObservabilityHelper) -> None:
        while record_deltas:
            record_delta = record_deltas[0]
            project_name = record_delta.resolved_record.get(PROJECTS_TABLE_PROJECT_NAME_KEY, "")
            if record_delta.action_performed == MergedRecordActionType.CREATE:
                # Currently we only add new projects instead of updating existing ones when applying a snapshot.
                # Add this checking here for handling updated records in the future.
                try:
                    context.projects.delete_project(DeleteProjectRequest(project_name=project_name))
                except Exception as e:
                    logger.error(TABLE_NAME, project_name, ApplyResourceStatus.FAILED_ROLLBACK, str(e))
                    raise e

                logger.debug(TABLE_NAME, project_name, ApplyResourceStatus.ROLLBACKED,"removing project succeeded")

            record_deltas.pop(0)

    @staticmethod
    def _add_groups_and_users_to_project(context: SocaContext, project_db_record: Dict,
                                         record_delta: MergedRecordDelta, logger: ApplySnapshotObservabilityHelper):
        project = copy.deepcopy(record_delta.resolved_record)
        project["ldap_groups"] = project_db_record.get("ldap_groups", [])
        project["users"] = project_db_record.get("users", [])
        project_name = project["name"]
        try:
            project = ProjectsDAO.convert_from_db(project)
            project = context.projects.update_project(
                UpdateProjectRequest(project=project)
            ).project
            record_delta.resolved_record = ProjectsDAO.convert_to_db(project)

            logger.info(TABLE_NAME, project_name, reason="adding ldap groups and users to project successfully")
        except Exception as e:
            logger.warning(TABLE_NAME, project_name, reason=f"failed to add ldap groups and users to project: {str(e)}")

    @staticmethod
    def _budget_is_enabled_and_exists(context: SocaContext, project: Project, logger: ApplySnapshotObservabilityHelper) -> bool:
        if not project.enable_budgets:
            return False

        if not project.budget or not project.budget.budget_name:
            logger.warning(TABLE_NAME, project.name, reason="budget name is empty and will be ignored")
            return False

        try:
            _budget = context.aws_util().budgets_get_budget(project.budget.budget_name)
        except Exception as e:
            logger.warning(TABLE_NAME, project.name, reason=f"cannot get the budget name and it will be ignored: {str(e)}")
            return False

        return True

    @staticmethod
    def resolve_record(context: SocaContext, db_entry: dict, dedup_id: str,
                       logger: ApplySnapshotObservabilityHelper) -> (Dict, Optional[MergedRecordActionType]):
        project_name = db_entry[PROJECTS_TABLE_PROJECT_NAME_KEY]
        try:
            existing_project = context.projects.get_project(GetProjectRequest(project_name=project_name)).project
            snapshot_project = ProjectsDAO.convert_from_db(db_entry)
            if existing_project == snapshot_project:
                return db_entry, None

            # If the project already exists, rename the project ID by appending the dedup ID.
            # This merger will add new projects instead of overriding the existing ones to resolve conflicts.
            project_name = MergeTable.unique_resource_id_generator(project_name, dedup_id)
            db_entry[PROJECTS_TABLE_PROJECT_NAME_KEY] = project_name
            logger.debug(TABLE_NAME, project_name, reason="Project with the same name exists under the current environment. "
                                                          "Created a new record with the dedup ID appended to the project name")
        except exceptions.SocaException as e:
            if e.error_code != errorcodes.PROJECT_NOT_FOUND:
                raise e

        return db_entry, MergedRecordActionType.CREATE
