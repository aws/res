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

from ideaclustermanager.app.snapshots.apply_snapshot_data_transformation_from_version.abstract_transformation_from_res_version import (
    TransformationFromRESVersion,
)
import ideaclustermanager.app.snapshots.helpers.db_utils as db_utils
from ideadatamodel.snapshots import TableName

from logging import Logger
from typing import Dict, List
import copy


class TransformationFromVersion2024_04_02(TransformationFromRESVersion):

    def transform_data(self, env_data_by_table: Dict[TableName, List], logger = Logger) -> Dict[TableName, List]:
        role_assignments = []

        # Step 1: Get all projects from the env_data_by_table
        projects = env_data_by_table[TableName.PROJECTS_TABLE_NAME]

        # Step 2: Loop through all users and ldap_groups attribute values of each project
        for project in projects:
            # Step 3: Create Role assignments for each project-user and project-group associations
            users = project.get("users", [])
            for user in users:
                role_assignment = {
                    db_utils.ROLE_ASSIGNMENT_DB_ACTOR_KEY: f"{user}:{db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_USER_VALUE}",
                    db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY: f"{project[db_utils.PROJECT_DB_PROJECT_ID_KEY]}:{db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_PROJECT_VALUE}",
                    db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_KEY: db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_USER_VALUE,
                    db_utils.ROLE_ASSIGNMENT_DB_ACTOR_ID_KEY: user,
                    db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_KEY: db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_PROJECT_VALUE,
                    db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_ID_KEY: project[db_utils.PROJECT_DB_PROJECT_ID_KEY],
                    db_utils.ROLE_ASSIGNMENT_DB_ROLD_ID_KEY: db_utils.ROLE_ASSIGNMENT_DB_ROLD_ID_PROJECT_MEMBER_VALUE,    # We start off everyone at the project member role by default
                }
                role_assignments.append(role_assignment)

            groups = project.get("ldap_groups", [])
            for group in groups:
                role_assignment = {
                    db_utils.ROLE_ASSIGNMENT_DB_ACTOR_KEY: f"{group}:{db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_GROUP_VALUE}",
                    db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY: f"{project[db_utils.PROJECT_DB_PROJECT_ID_KEY]}:{db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_PROJECT_VALUE}",
                    db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_KEY: db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_GROUP_VALUE,
                    db_utils.ROLE_ASSIGNMENT_DB_ACTOR_ID_KEY: group,
                    db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_KEY: db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_PROJECT_VALUE,
                    db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_ID_KEY: project[db_utils.PROJECT_DB_PROJECT_ID_KEY],
                    db_utils.ROLE_ASSIGNMENT_DB_ROLD_ID_KEY: db_utils.ROLE_ASSIGNMENT_DB_ROLD_ID_PROJECT_MEMBER_VALUE,    # We start off everyone at the project member role by default
                }
                role_assignments.append(role_assignment)

        # Step 4: Add role assignments dictionary to env_data_by_table
        env_data_by_table_copy = copy.deepcopy(env_data_by_table)
        env_data_by_table_copy[TableName.ROLE_ASSIGNMENTS_TABLE_NAME] = role_assignments

        return env_data_by_table_copy
