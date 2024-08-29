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

import pytest
from ideaclustermanager import AppContext
from ideaclustermanager.app.snapshots.apply_snapshot_merge_table.roles_table_merger import (
    RolesTableMerger,
)
from ideaclustermanager.app.snapshots.helpers.apply_snapshot_observability_helper import (
    ApplySnapshotObservabilityHelper,
)
from ideaclustermanager.app.snapshots.helpers.merged_record_utils import (
    MergedRecordActionType,
    MergedRecordDelta,
)
from ideasdk.utils.utils import Utils

from ideadatamodel import GetRoleRequest, errorcodes, exceptions


def test_roles_table_merger_merge_new_role_succeed(context: AppContext, monkeypatch):
    role_id = "test_role"
    table_data_to_merge = [
        {
            "role_id": role_id,
            "name": "Test Role",
            "description": "This is a test role",
            "projects": {
                "update_status": False,
                "update_personnel": False,
            },
            "created_on": Utils.current_time_ms(),
            "updated_on": Utils.current_time_ms(),
        }
    ]

    resolver = RolesTableMerger()
    record_deltas, success = resolver.merge(
        context,
        table_data_to_merge,
        "dedup_id",
        {},
        ApplySnapshotObservabilityHelper(context.logger("roles_table_resolver")),
    )
    assert success
    assert len(record_deltas) == 1
    assert record_deltas[0].original_record is None
    assert record_deltas[0].snapshot_record.get("role_id") == role_id
    assert record_deltas[0].resolved_record.get("role_id") == role_id
    assert record_deltas[0].action_performed == MergedRecordActionType.CREATE

    imported_role = context.roles.get_role(GetRoleRequest(role_id=role_id)).role
    assert imported_role is not None


def test_roles_table_resolver_rollback_original_data_succeed(
    context: AppContext, monkeypatch
):
    role_id = "test_role"
    context.roles.roles_dao.create_role(
        {
            "role_id": role_id,
            "name": "Test Role",
            "description": "This is a test role",
            "projects": {
                "update_status": False,
                "update_personnel": False,
            },
            "created_on": Utils.current_time_ms(),
            "updated_on": Utils.current_time_ms(),
        }
    )

    resolver = RolesTableMerger()
    delta_records = [
        MergedRecordDelta(
            snapshot_record={
                "role_id": role_id,
                "name": "Test Role",
                "description": "This is a test role",
                "projects": {
                    "update_status": False,
                    "update_personnel": False,
                },
                "created_on": Utils.current_time_ms(),
                "updated_on": Utils.current_time_ms(),
            },
            resolved_record={
                "role_id": role_id,
                "name": "Test Role",
                "description": "This is a test role",
                "projects": {
                    "update_status": False,
                    "update_personnel": False,
                },
                "created_on": Utils.current_time_ms(),
                "updated_on": Utils.current_time_ms(),
            },
            action_performed=MergedRecordActionType.CREATE,
        ),
    ]
    resolver.rollback(
        context,
        delta_records,
        ApplySnapshotObservabilityHelper(context.logger("roles_table_resolver")),
    )

    with pytest.raises(exceptions.SocaException) as exc_info:
        _role = context.roles.get_role(GetRoleRequest(role_id=role_id)).role
    assert exc_info.value.error_code == errorcodes.ROLE_NOT_FOUND


def test_users_table_merger_ignore_existing_role_succeed(
    context: AppContext, monkeypatch
):
    context.roles.roles_dao.create_role(
        {
            "role_id": "test_role",
            "name": "Test Role",
            "description": "This is a test role",
            "projects": {
                "update_status": False,
                "update_personnel": False,
            },
            "created_on": Utils.current_time_ms(),
            "updated_on": Utils.current_time_ms(),
        }
    )
    role = context.roles.roles_dao.convert_to_db(
        context.roles.get_role(GetRoleRequest(role_id="test_role")).role
    )
    table_data_to_merge = [role]

    resolver = RolesTableMerger()
    record_deltas, success = resolver.merge(
        context,
        table_data_to_merge,
        "dedup_id",
        {},
        ApplySnapshotObservabilityHelper(context.logger("roles_table_resolver")),
    )
    assert success
    assert len(record_deltas) == 0
