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

from ideadatamodel.snapshots.snapshot_model import RESVersion, TableName, TableKeys
from ideaclustermanager.app.snapshots.apply_snapshot_data_transformation_from_version import data_transformation_from_2023_11, data_transformation_from_2024_04_02
from ideaclustermanager.app.snapshots.apply_snapshot_merge_table import (
    merge_table,
    users_table_merger,
    permission_profiles_table_merger,
    projects_table_merger,
    filesystems_cluster_settings_table_merger,
    software_stacks_table_merger,
    role_assignments_table_merger,
)
from typing import Dict, Type

# This array should be updated each release to include the new RES version number
RES_VERSION_IN_TOPOLOGICAL_ORDER = [
    RESVersion.v_2023_11,
    RESVersion.v_2024_01,
    RESVersion.v_2024_01_01,
    RESVersion.v_2024_04,
    RESVersion.v_2024_04_01,
    RESVersion.v_2024_04_02,
    RESVersion.v_2024_06,
    RESVersion.v_2024_08,
]

TABLE_TO_TABLE_KEYS_BY_VERSION: Dict[TableName, Dict[RESVersion, TableKeys]] = {
    TableName.CLUSTER_SETTINGS_TABLE_NAME: {
        RESVersion.v_2023_11: TableKeys(partition_key='key')
    },
    TableName.USERS_TABLE_NAME: {
        RESVersion.v_2023_11: TableKeys(partition_key='username')
    },
    TableName.PROJECTS_TABLE_NAME: {
        RESVersion.v_2023_11: TableKeys(partition_key='project_id')
    },
    TableName.PERMISSION_PROFILES_TABLE_NAME: {
        RESVersion.v_2023_11: TableKeys(partition_key='profile_id')
    },
    TableName.SOFTWARE_STACKS_TABLE_NAME: {
        RESVersion.v_2023_11: TableKeys(partition_key='base_os', sort_key='stack_id')
    },
    TableName.ROLE_ASSIGNMENTS_TABLE_NAME: {
        RESVersion.v_2024_06: TableKeys(partition_key='actor_key', sort_key='resource_key')
    },
    TableName.ROLES_TABLE_NAME: {
        RESVersion.v_2024_08: TableKeys(partition_key='role_id')
    },
}
"""
- This is a strictly additive list.
- New table addition -> Add an entry for the table, res_version the table is introduced, table's partition_key and sort_key.
- Existing table, keys change -> In the table dict, add an entry for the res_version in which the change is introduced,
table's updated partition_key and sort_key.
- Table deletion -> Do not remove the entry from this list. This is a strictly additive list. This is to maintain backward compatability.
"""

RES_VERSION_TO_DATA_TRANSFORMATION_CLASS = {
    RESVersion.v_2023_11: data_transformation_from_2023_11.TransformationFromVersion2023_11,
    RESVersion.v_2024_04_02: data_transformation_from_2024_04_02.TransformationFromVersion2024_04_02
}
"""
- An entry must be added to this map when data transformation logic must be added for a version.
- Data transformation class naming convention: TransformationFromVersion<RES_Version>
- If a RES version does not have any schema changes, an entry does not need to be created in this map.
"""

TABLES_IN_MERGE_DEPENDENCY_ORDER = [
    TableName.USERS_TABLE_NAME,
    TableName.PERMISSION_PROFILES_TABLE_NAME,
    TableName.PROJECTS_TABLE_NAME,
    TableName.ROLE_ASSIGNMENTS_TABLE_NAME,
    TableName.SOFTWARE_STACKS_TABLE_NAME,
    TableName.CLUSTER_SETTINGS_TABLE_NAME,
]

TABLE_TO_MERGE_LOGIC_CLASS: Dict[TableName, Type[merge_table.MergeTable]] = {
    TableName.USERS_TABLE_NAME: users_table_merger.UsersTableMerger,
    TableName.PERMISSION_PROFILES_TABLE_NAME: permission_profiles_table_merger.PermissionProfilesTableMerger,
    TableName.PROJECTS_TABLE_NAME: projects_table_merger.ProjectsTableMerger,
    TableName.CLUSTER_SETTINGS_TABLE_NAME: filesystems_cluster_settings_table_merger.FileSystemsClusterSettingTableMerger,
    TableName.SOFTWARE_STACKS_TABLE_NAME: software_stacks_table_merger.SoftwareStacksTableMerger,
    TableName.ROLE_ASSIGNMENTS_TABLE_NAME: role_assignments_table_merger.RoleAssignmentsTableMerger,
}
"""
- An entry must be added to this map for all tables that must be applied from snapshot.
- Merge logic class naming convention: <TableName>TableMerger
"""
