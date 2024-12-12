#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List, Optional

import aws_cdk.aws_dynamodb as _dynamodb
import orjson
import res.constants as constants  # type: ignore
from aws_cdk.aws_dynamodb import (
    Attribute,
    AttributeType,
    GlobalSecondaryIndexProps,
    TableProps,
)
from pydantic import BaseModel
from res.resources import (  # type: ignore
    accounts,
    cluster_settings,
    modules,
    permission_profiles,
    projects,
    role_assignments,
    schedules,
    servers,
    session_permissions,
    sessions,
    software_stacks,
)


class RESDDBTable(BaseModel):
    id: str
    module_id: str
    table_props: TableProps
    global_secondary_indexes_props: Optional[List[GlobalSecondaryIndexProps]]
    enable_kinesis_stream: bool = False

    class Config:
        arbitrary_types_allowed = True
        json_loads = orjson.loads


cluster_settings_table: RESDDBTable = RESDDBTable(
    id=cluster_settings.CLUSTER_SETTINGS_TABLE_NAME,
    module_id=constants.MODULE_ID_CLUSTER_MANAGER,
    table_props=TableProps(
        partition_key=Attribute(
            name=cluster_settings.CLUSTER_SETTINGS_HASH_KEY, type=AttributeType.STRING
        ),
    ),
    enable_kinesis_stream=True,
)

modules_table: RESDDBTable = RESDDBTable(
    id=modules.MODULES_TABLE_NAME,
    module_id=constants.MODULE_ID_CLUSTER_MANAGER,
    table_props=TableProps(
        partition_key=Attribute(
            name=modules.MODULES_TABLE_HASH_KEY, type=AttributeType.STRING
        ),
    ),
)

project_table: RESDDBTable = RESDDBTable(
    id=projects.PROJECTS_TABLE_NAME,
    module_id=constants.MODULE_ID_CLUSTER_MANAGER,
    table_props=TableProps(
        partition_key=Attribute(
            name=projects.PROJECTS_DB_HASH_KEY, type=AttributeType.STRING
        ),
    ),
    global_secondary_indexes_props=[
        GlobalSecondaryIndexProps(
            index_name=projects.GSI_PROJECT_NAME,
            partition_key=Attribute(
                name=projects.GSI_PROJECT_NAME_HASH_KEY, type=AttributeType.STRING
            ),
            projection_type=_dynamodb.ProjectionType.ALL,
        )
    ],
)

user_table: RESDDBTable = RESDDBTable(
    id=accounts.USERS_TABLE_NAME,
    module_id=constants.MODULE_ID_CLUSTER_MANAGER,
    table_props=TableProps(
        partition_key=Attribute(
            name=accounts.USERS_DB_HASH_KEY, type=AttributeType.STRING
        ),
    ),
    global_secondary_indexes_props=[
        GlobalSecondaryIndexProps(
            index_name=accounts.GSI_ROLE,
            partition_key=Attribute(
                name=accounts.GSI_ROLE_HASH_KEY, type=AttributeType.STRING
            ),
            projection_type=_dynamodb.ProjectionType.INCLUDE,
            non_key_attributes=["additional_groups", "username"],
        ),
        GlobalSecondaryIndexProps(
            index_name=accounts.GSI_EMAIL,
            partition_key=Attribute(
                name=accounts.GSI_EMAIL_HASH_KEY, type=AttributeType.STRING
            ),
            projection_type=_dynamodb.ProjectionType.INCLUDE,
            non_key_attributes=[
                "role",
                "username",
                "is_active",
                "enabled",
                "identity_source",
            ],
        ),
    ],
)

group_table: RESDDBTable = RESDDBTable(
    id=accounts.GROUPS_TABLE_NAME,
    module_id=constants.MODULE_ID_CLUSTER_MANAGER,
    table_props=TableProps(
        partition_key=Attribute(
            name=accounts.GROUPS_DB_HASH_KEY, type=AttributeType.STRING
        ),
    ),
)

group_members_table: RESDDBTable = RESDDBTable(
    id=accounts.GROUP_MEMBERS_TABLE_NAME,
    module_id=constants.MODULE_ID_CLUSTER_MANAGER,
    table_props=TableProps(
        partition_key=Attribute(
            name=accounts.GROUPS_MEMBERS_DB_HASH_KEY, type=AttributeType.STRING
        ),
        sort_key=Attribute(
            name=accounts.GROUPS_MEMBERS_DB_RANGE_KEY, type=AttributeType.STRING
        ),
    ),
)

sso_state_table: RESDDBTable = RESDDBTable(
    id=accounts.SSO_STATE_TABLE_NAME,
    module_id=constants.MODULE_ID_CLUSTER_MANAGER,
    table_props=TableProps(
        partition_key=Attribute(
            name=accounts.SSO_STATE_DB_HASH_KEY, type=AttributeType.STRING
        ),
        time_to_live_attribute="ttl",
    ),
)

role_assignment_table: RESDDBTable = RESDDBTable(
    id=role_assignments.ROLE_ASSIGNMENTS_TABLE_NAME,
    module_id=constants.MODULE_ID_CLUSTER_MANAGER,
    table_props=TableProps(
        partition_key=Attribute(
            name=role_assignments.ROLE_ASSIGNMENTS_DB_HASH_KEY,
            type=AttributeType.STRING,
        ),
        sort_key=Attribute(
            name=role_assignments.ROLE_ASSIGNMENTS_DB_RANGE_KEY,
            type=AttributeType.STRING,
        ),
    ),
    global_secondary_indexes_props=[
        GlobalSecondaryIndexProps(
            index_name=role_assignments.GSI_RESOURCE_KEY,
            partition_key=Attribute(
                name=role_assignments.GSI_RESOURCE_KEY_HASH_KEY,
                type=AttributeType.STRING,
            ),
            sort_key=Attribute(
                name=role_assignments.GSI_RESOURCE_KEY_RANGE_KEY,
                type=AttributeType.STRING,
            ),
            projection_type=_dynamodb.ProjectionType.ALL,
        )
    ],
)

ad_automation_table: RESDDBTable = RESDDBTable(
    id=constants.AD_AUTOMATION_TABLE_NAME,
    module_id=constants.MODULE_ID_CLUSTER_MANAGER,
    table_props=TableProps(
        partition_key=Attribute(
            name=constants.AD_AUTOMATION_DB_HASH_KEY, type=AttributeType.STRING
        ),
        sort_key=Attribute(
            name=constants.AD_AUTOMATION_DB_RANGE_KEY, type=AttributeType.STRING
        ),
        time_to_live_attribute="ttl",
    ),
)

snapshot_table: RESDDBTable = RESDDBTable(
    id=constants.SNAPSHOT_TABLE_NAME,
    module_id=constants.MODULE_ID_CLUSTER_MANAGER,
    table_props=TableProps(
        partition_key=Attribute(
            name=constants.SNAPSHOT_DB_HASH_KEY, type=AttributeType.STRING
        ),
        sort_key=Attribute(
            name=constants.SNAPSHOT_DB_RANGE_KEY, type=AttributeType.STRING
        ),
    ),
)

apply_snapshot_table: RESDDBTable = RESDDBTable(
    id=constants.APPLY_SNAPSHOT_TABLE_NAME,
    module_id=constants.MODULE_ID_CLUSTER_MANAGER,
    table_props=TableProps(
        partition_key=Attribute(
            name=constants.APPLY_SNAPSHOT_DB_HASH_KEY, type=AttributeType.STRING
        ),
    ),
)


distributed_lock_table: RESDDBTable = RESDDBTable(
    id=constants.CLUSTER_MANAGER_LOCK_TABLE_NAME,
    module_id=constants.MODULE_ID_CLUSTER_MANAGER,
    table_props=TableProps(
        partition_key=Attribute(
            name=constants.LOCK_DB_HASH_KEY, type=AttributeType.STRING
        ),
        sort_key=Attribute(name=constants.LOCK_DB_RANGE_KEY, type=AttributeType.STRING),
        time_to_live_attribute="expiry_time",
    ),
)

email_template_table: RESDDBTable = RESDDBTable(
    id=constants.EMAIL_TEMPLATE_TABLE_NAME,
    module_id=constants.MODULE_ID_CLUSTER_MANAGER,
    table_props=TableProps(
        partition_key=Attribute(
            name=constants.EMAIL_TEMPLATE_DB_HASH_KEY, type=AttributeType.STRING
        ),
    ),
)

vdc_permission_profile_table: RESDDBTable = RESDDBTable(
    id=permission_profiles.PERMISSION_PROFILE_TABLE_NAME,
    module_id=constants.MODULE_ID_VDC,
    table_props=TableProps(
        partition_key=Attribute(
            name=permission_profiles.PERMISSION_PROFILE_DB_HASH_KEY,
            type=AttributeType.STRING,
        ),
    ),
)

vdc_schedule_table: RESDDBTable = RESDDBTable(
    id=schedules.SCHEDULE_DB_TABLE_NAME,
    module_id=constants.MODULE_ID_VDC,
    table_props=TableProps(
        partition_key=Attribute(
            name=schedules.SCHEDULE_DB_HASH_KEY, type=AttributeType.STRING
        ),
        sort_key=Attribute(
            name=schedules.SCHEDULE_DB_RANGE_KEY, type=AttributeType.STRING
        ),
    ),
)

vdc_ssm_command_table: RESDDBTable = RESDDBTable(
    id=constants.SSM_COMMAND_TABLE_NAME,
    module_id=constants.MODULE_ID_VDC,
    table_props=TableProps(
        partition_key=Attribute(
            name=constants.SSM_COMMAND_DB_HASH_KEY, type=AttributeType.STRING
        ),
    ),
)

vdc_software_stack_table: RESDDBTable = RESDDBTable(
    id=software_stacks.SOFTWARE_STACK_TABLE_NAME,
    module_id=constants.MODULE_ID_VDC,
    table_props=TableProps(
        partition_key=Attribute(
            name=software_stacks.SOFTWARE_STACK_DB_HASH_KEY, type=AttributeType.STRING
        ),
        sort_key=Attribute(
            name=software_stacks.SOFTWARE_STACK_DB_RANGE_KEY, type=AttributeType.STRING
        ),
    ),
)

vdc_session_table: RESDDBTable = RESDDBTable(
    id=sessions.SESSIONS_TABLE_NAME,
    module_id=constants.MODULE_ID_VDC,
    table_props=TableProps(
        partition_key=Attribute(
            name=sessions.SESSION_DB_HASH_KEY, type=AttributeType.STRING
        ),
        sort_key=Attribute(
            name=sessions.SESSION_DB_RANGE_KEY, type=AttributeType.STRING
        ),
    ),
)

vdc_session_counter_table: RESDDBTable = RESDDBTable(
    id=sessions.SESSIONS_COUNTER_TABLE_NAME,
    module_id=constants.MODULE_ID_VDC,
    table_props=TableProps(
        partition_key=Attribute(
            name=sessions.SESSIONS_COUNTER_DB_HASH_KEY, type=AttributeType.STRING
        ),
        sort_key=Attribute(
            name=sessions.SESSIONS_COUNTER_DB_RANGE_KEY, type=AttributeType.STRING
        ),
    ),
)

vdc_server_table: RESDDBTable = RESDDBTable(
    id=servers.SERVER_TABLE_NAME,
    module_id=constants.MODULE_ID_VDC,
    table_props=TableProps(
        partition_key=Attribute(
            name=servers.SERVER_DB_HASH_KEY, type=AttributeType.STRING
        ),
    ),
)

vdc_session_permission_table: RESDDBTable = RESDDBTable(
    id=session_permissions.SESSION_PERMISSION_TABLE_NAME,
    module_id=constants.MODULE_ID_VDC,
    table_props=TableProps(
        partition_key=Attribute(
            name=session_permissions.SESSION_PERMISSION_DB_HASH_KEY,
            type=AttributeType.STRING,
        ),
        sort_key=Attribute(
            name=session_permissions.SESSION_PERMISSION_DB_RANGE_KEY,
            type=AttributeType.STRING,
        ),
    ),
)

vdc_distributed_lock_table: RESDDBTable = RESDDBTable(
    id=constants.VDC_LOCK_TABLE_NAME,
    module_id=constants.MODULE_ID_VDC,
    table_props=TableProps(
        partition_key=Attribute(
            name=constants.LOCK_DB_HASH_KEY, type=AttributeType.STRING
        ),
        sort_key=Attribute(name=constants.LOCK_DB_RANGE_KEY, type=AttributeType.STRING),
        time_to_live_attribute="expiry_time",
    ),
)


ddb_tables_list: List[RESDDBTable] = [
    cluster_settings_table,
    modules_table,
    project_table,
    user_table,
    group_table,
    group_members_table,
    sso_state_table,
    role_assignment_table,
    ad_automation_table,
    snapshot_table,
    apply_snapshot_table,
    distributed_lock_table,
    email_template_table,
    vdc_permission_profile_table,
    vdc_schedule_table,
    vdc_ssm_command_table,
    vdc_software_stack_table,
    vdc_session_table,
    vdc_session_counter_table,
    vdc_server_table,
    vdc_session_permission_table,
    vdc_distributed_lock_table,
]
