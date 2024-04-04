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
from ideaclustermanager.app.snapshots.apply_snapshot_merge_table.users_table_merger import (
    UsersTableMerger,
)
from ideaclustermanager.app.snapshots.helpers.apply_snapshot_observability_helper import (
    ApplySnapshotObservabilityHelper,
)
from ideaclustermanager.app.snapshots.helpers.merged_record_utils import (
    MergedRecordActionType,
    MergedRecordDelta,
)

from ideadatamodel import constants, errorcodes, exceptions


def test_users_table_merger_merge_valid_data_succeed(context: AppContext):
    table_data_to_merge = [
        {"username": "test_user_1", "role": constants.ADMIN_ROLE, "sudo": True},
        {"username": "test_user_2", "role": constants.USER_ROLE, "sudo": False},
    ]
    context.accounts.user_dao.create_user(
        {
            "username": "test_user_1",
            "email": "test_user_1@example.org",
            "uid": 0,
            "gid": 0,
            "additional_groups": [],
            "login_shell": "",
            "home_dir": "",
            "sudo": False,
            "enabled": True,
            "role": constants.USER_ROLE,
            "is_active": True,
        }
    )
    context.accounts.user_dao.create_user(
        {
            "username": "test_user_2",
            "email": "test_user_2@example.org",
            "uid": 1,
            "gid": 1,
            "additional_groups": [],
            "login_shell": "",
            "home_dir": "",
            "sudo": True,
            "enabled": True,
            "role": constants.ADMIN_ROLE,
            "is_active": True,
        }
    )

    merger = UsersTableMerger()
    record_deltas, success = merger.merge(
        context,
        table_data_to_merge,
        "dedup_id",
        {},
        ApplySnapshotObservabilityHelper(context.logger("users_table_merger")),
    )
    assert success
    assert len(record_deltas) == 2
    assert record_deltas[0].original_record.get("role") == constants.USER_ROLE
    assert record_deltas[0].snapshot_record.get("role") == constants.ADMIN_ROLE
    assert record_deltas[0].resolved_record is None
    assert record_deltas[0].action_performed == MergedRecordActionType.UPDATE
    assert record_deltas[1].original_record.get("role") == constants.ADMIN_ROLE
    assert record_deltas[1].snapshot_record.get("role") == constants.USER_ROLE
    assert record_deltas[1].resolved_record is None
    assert record_deltas[1].action_performed == MergedRecordActionType.UPDATE

    imported_test_user_1 = context.accounts.get_user("test_user_1")
    assert imported_test_user_1.role == constants.ADMIN_ROLE
    assert imported_test_user_1.sudo

    imported_test_user_2 = context.accounts.get_user("test_user_2")
    assert imported_test_user_2.role == constants.USER_ROLE
    assert not imported_test_user_2.sudo


def test_users_table_merger_ignore_nonexistent_user_succeed(context: AppContext):
    table_data_to_merge = [
        {"username": "test_user_3", "role": constants.ADMIN_ROLE, "sudo": True},
    ]

    merger = UsersTableMerger()
    record_deltas, success = merger.merge(
        context,
        table_data_to_merge,
        "dedup_id",
        {},
        ApplySnapshotObservabilityHelper(context.logger("users_table_merger")),
    )
    assert success
    assert len(record_deltas) == 0

    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.get_user("test_user_3")
    assert exc_info.value.error_code == errorcodes.AUTH_USER_NOT_FOUND


def test_users_table_merger_ignore_user_without_permission_change_succeed(
    context: AppContext,
):
    table_data_to_merge = [
        {"username": "test_user_3", "role": constants.ADMIN_ROLE, "sudo": True},
    ]

    context.accounts.user_dao.create_user(
        {
            "username": "test_user_3",
            "email": "test_user_1@example.org",
            "uid": 2,
            "gid": 2,
            "additional_groups": [],
            "login_shell": "",
            "home_dir": "",
            "sudo": True,
            "enabled": True,
            "role": constants.ADMIN_ROLE,
            "is_active": True,
        }
    )

    merger = UsersTableMerger()
    record_deltas, success = merger.merge(
        context,
        table_data_to_merge,
        "dedup_id",
        {},
        ApplySnapshotObservabilityHelper(context.logger("users_table_merger")),
    )
    assert success
    assert len(record_deltas) == 0

    imported_test_user_3 = context.accounts.get_user("test_user_3")
    assert imported_test_user_3.role == constants.ADMIN_ROLE
    assert imported_test_user_3.sudo


def test_users_table_merger_roll_back_original_data_succeed(
    context: AppContext, monkeypatch
):
    context.accounts.user_dao.create_user(
        {
            "username": "test_user_4",
            "email": "test_user_1@example.org",
            "uid": 3,
            "gid": 3,
            "additional_groups": [],
            "login_shell": "",
            "home_dir": "",
            "sudo": True,
            "enabled": True,
            "role": constants.ADMIN_ROLE,
            "is_active": True,
        }
    )
    context.accounts.user_dao.create_user(
        {
            "username": "test_user_5",
            "email": "test_user_2@example.org",
            "uid": 4,
            "gid": 4,
            "additional_groups": [],
            "login_shell": "",
            "home_dir": "",
            "sudo": False,
            "enabled": True,
            "role": constants.USER_ROLE,
            "is_active": True,
        }
    )

    merger = UsersTableMerger()
    delta_records = [
        MergedRecordDelta(
            original_record={
                "username": "test_user_4",
                "sudo": False,
                "role": constants.USER_ROLE,
            },
            snapshot_record={
                "username": "test_user_4",
                "sudo": False,
                "role": constants.ADMIN_ROLE,
            },
            action_performed=MergedRecordActionType.UPDATE,
        ),
        MergedRecordDelta(
            original_record={
                "username": "test_user_5",
                "sudo": False,
                "role": constants.ADMIN_ROLE,
            },
            snapshot_record={
                "username": "test_user_5",
                "sudo": False,
                "role": constants.USER_ROLE,
            },
            action_performed=MergedRecordActionType.UPDATE,
        ),
    ]
    merger.rollback(
        context,
        delta_records,
        ApplySnapshotObservabilityHelper(context.logger("users_table_merger")),
    )

    imported_test_user_4 = context.accounts.get_user("test_user_4")
    assert imported_test_user_4.role == constants.USER_ROLE
    assert not imported_test_user_4.sudo

    imported_test_user_5 = context.accounts.get_user("test_user_5")
    assert imported_test_user_5.role == constants.ADMIN_ROLE
    assert imported_test_user_5.sudo
