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

__all__ = (
    'ApplySnapshot',
    'ApplySnapshotStatus',
    'Snapshot',
    'SnapshotStatus',
    'TableKeys',
    'TableName',
    'RESVersion'
)

from ideadatamodel import SocaBaseModel
from datetime import datetime
from enum import Enum
from typing import Optional


class SnapshotStatus(str, Enum):
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'


class Snapshot(SocaBaseModel):
    s3_bucket_name: Optional[str]
    snapshot_path: Optional[str]
    status: Optional[SnapshotStatus]
    created_on: Optional[datetime]
    failure_reason: Optional[str]


class ApplySnapshotStatus(str, Enum):
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    ROLLBACK_IN_PROGRESS = "ROLLBACK_IN_PROGRESS"
    ROLLBACK_COMPLETE = "ROLLBACK_COMPLETE"
    ROLLBACE_FAILED = "ROLLBACK_FAILED"


class ApplySnapshot(SocaBaseModel):
    apply_snapshot_identifier: Optional[str]
    s3_bucket_name: Optional[str]
    snapshot_path: Optional[str]
    status: Optional[ApplySnapshotStatus]
    created_on: Optional[datetime]
    failure_reason: Optional[str]


class TableKeys(SocaBaseModel):
    partition_key: str
    sort_key: Optional[str]


class TableName(str, Enum):
    CLUSTER_SETTINGS_TABLE_NAME = "cluster-settings"
    USERS_TABLE_NAME = "accounts.users"
    PROJECTS_TABLE_NAME = "projects"
    PERMISSION_PROFILES_TABLE_NAME = "vdc.controller.permission-profiles"
    SOFTWARE_STACKS_TABLE_NAME = "vdc.controller.software-stacks"
    ROLE_ASSIGNMENTS_TABLE_NAME = "authz.role-assignments"
    ROLES_TABLE_NAME = "authz.roles"


class RESVersion(str, Enum):
    v_2023_11 = "2023.11"
    v_2024_01 = "2024.01"
    v_2024_01_01 = "2024.01.01"
    v_2024_04 = "2024.04"
    v_2024_04_01 = "2024.04.01"
    v_2024_04_02 = "2024.04.02"
    v_2024_06 = "2024.06"
    v_2024_08 = "2024.08"
