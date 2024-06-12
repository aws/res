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

import copy

import ideaclustermanager.app.snapshots.helpers.db_utils as db_utils
import pytest
from _pytest.monkeypatch import MonkeyPatch
from ideaclustermanager import AppContext
from ideaclustermanager.app.snapshots.apply_snapshot_data_transformation_from_version import (
    data_transformation_from_2024_04_02,
)
from ideaclustermanager.app.snapshots.helpers.apply_snapshot_observability_helper import (
    ApplySnapshotObservabilityHelper,
)
from ideasdk.utils.utils import Utils

from ideadatamodel.snapshots.snapshot_model import TableName


def test_data_transformation_old_projects_new_role_assignments(
    context: AppContext, monkeypatch
):

    env_data_by_table = {
        TableName.PROJECTS_TABLE_NAME: [
            {
                db_utils.PROJECT_DB_PROJECT_ID_KEY: "test_project_1",
                db_utils.PROJECT_DB_OLD_LDAP_GROUPS_KEY: ["group1", "group2"],
                db_utils.PROJECT_DB_OLD_USERS_KEY: ["user1", "user2"],
            }
        ]
    }

    transformation = (
        data_transformation_from_2024_04_02.TransformationFromVersion2024_04_02()
    )

    transformed_env_data = transformation.transform_data(
        env_data_by_table,
        ApplySnapshotObservabilityHelper(context.logger("transformation_2024_04_01")),
    )

    expected_transformed_env_data = {
        TableName.PROJECTS_TABLE_NAME: [
            {
                db_utils.PROJECT_DB_PROJECT_ID_KEY: "test_project_1",
                db_utils.PROJECT_DB_OLD_LDAP_GROUPS_KEY: ["group1", "group2"],
                db_utils.PROJECT_DB_OLD_USERS_KEY: ["user1", "user2"],
            }
        ],
        TableName.ROLE_ASSIGNMENTS_TABLE_NAME: [
            {
                db_utils.ROLE_ASSIGNMENT_DB_ACTOR_KEY: f"user1:{db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_USER_VALUE}",
                db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY: f"{env_data_by_table[TableName.PROJECTS_TABLE_NAME][0][db_utils.PROJECT_DB_PROJECT_ID_KEY]}:{db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_PROJECT_VALUE}",
                db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_KEY: db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_USER_VALUE,
                db_utils.ROLE_ASSIGNMENT_DB_ACTOR_ID_KEY: "user1",
                db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_KEY: db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_PROJECT_VALUE,
                db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_ID_KEY: env_data_by_table[
                    TableName.PROJECTS_TABLE_NAME
                ][0][db_utils.PROJECT_DB_PROJECT_ID_KEY],
                db_utils.ROLE_ASSIGNMENT_DB_ROLD_ID_KEY: db_utils.ROLE_ASSIGNMENT_DB_ROLD_ID_PROJECT_MEMBER_VALUE,
            },
            {
                db_utils.ROLE_ASSIGNMENT_DB_ACTOR_KEY: f"user2:{db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_USER_VALUE}",
                db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY: f"{env_data_by_table[TableName.PROJECTS_TABLE_NAME][0][db_utils.PROJECT_DB_PROJECT_ID_KEY]}:{db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_PROJECT_VALUE}",
                db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_KEY: db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_USER_VALUE,
                db_utils.ROLE_ASSIGNMENT_DB_ACTOR_ID_KEY: "user2",
                db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_KEY: db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_PROJECT_VALUE,
                db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_ID_KEY: env_data_by_table[
                    TableName.PROJECTS_TABLE_NAME
                ][0][db_utils.PROJECT_DB_PROJECT_ID_KEY],
                db_utils.ROLE_ASSIGNMENT_DB_ROLD_ID_KEY: db_utils.ROLE_ASSIGNMENT_DB_ROLD_ID_PROJECT_MEMBER_VALUE,
            },
            {
                db_utils.ROLE_ASSIGNMENT_DB_ACTOR_KEY: f"group1:{db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_GROUP_VALUE}",
                db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY: f"{env_data_by_table[TableName.PROJECTS_TABLE_NAME][0][db_utils.PROJECT_DB_PROJECT_ID_KEY]}:{db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_PROJECT_VALUE}",
                db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_KEY: db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_GROUP_VALUE,
                db_utils.ROLE_ASSIGNMENT_DB_ACTOR_ID_KEY: "group1",
                db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_KEY: db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_PROJECT_VALUE,
                db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_ID_KEY: env_data_by_table[
                    TableName.PROJECTS_TABLE_NAME
                ][0][db_utils.PROJECT_DB_PROJECT_ID_KEY],
                db_utils.ROLE_ASSIGNMENT_DB_ROLD_ID_KEY: db_utils.ROLE_ASSIGNMENT_DB_ROLD_ID_PROJECT_MEMBER_VALUE,
            },
            {
                db_utils.ROLE_ASSIGNMENT_DB_ACTOR_KEY: f"group2:{db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_GROUP_VALUE}",
                db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY: f"{env_data_by_table[TableName.PROJECTS_TABLE_NAME][0][db_utils.PROJECT_DB_PROJECT_ID_KEY]}:{db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_PROJECT_VALUE}",
                db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_KEY: db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_GROUP_VALUE,
                db_utils.ROLE_ASSIGNMENT_DB_ACTOR_ID_KEY: "group2",
                db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_KEY: db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_PROJECT_VALUE,
                db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_ID_KEY: env_data_by_table[
                    TableName.PROJECTS_TABLE_NAME
                ][0][db_utils.PROJECT_DB_PROJECT_ID_KEY],
                db_utils.ROLE_ASSIGNMENT_DB_ROLD_ID_KEY: db_utils.ROLE_ASSIGNMENT_DB_ROLD_ID_PROJECT_MEMBER_VALUE,
            },
        ],
    }

    assert transformed_env_data == expected_transformed_env_data
