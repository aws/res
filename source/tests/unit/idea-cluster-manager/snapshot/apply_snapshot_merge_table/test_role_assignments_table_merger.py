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
from _pytest.monkeypatch import MonkeyPatch
from ideaclustermanager import AppContext
from ideaclustermanager.app.snapshots.apply_snapshot_merge_table.role_assignments_table_merger import (
    RoleAssignmentsTableMerger,
)
from ideaclustermanager.app.snapshots.helpers.apply_snapshot_observability_helper import (
    ApplySnapshotObservabilityHelper,
)
from ideaclustermanager.app.snapshots.helpers.merged_record_utils import (
    MergedRecordActionType,
    MergedRecordDelta,
)
from ideasdk.utils.utils import Utils

from ideadatamodel import ListRoleAssignmentsRequest, PutRoleAssignmentRequest
from ideadatamodel.snapshots.snapshot_model import TableName


def generate_random_id(prefix: str) -> str:
    return f"test-{prefix}-{Utils.short_uuid()}"


def test_role_assignments_table_merger_merge_new_role_assignment_succeed(
    context: AppContext, monkeypatch: MonkeyPatch
):

    monkeypatch.setattr(
        context.role_assignments,
        "verify_actor_exists",
        lambda actor_id, actor_type: True,
    )
    monkeypatch.setattr(
        context.role_assignments,
        "verify_resource_exists",
        lambda resource_id, resource_type: True,
    )

    table_data_to_merge = [
        {
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_ID_KEY: "admin1",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_ID_KEY: "test_project1",
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_KEY: "user",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_KEY: "project",
            db_utils.ROLE_ASSIGNMENT_DB_ROLD_ID_KEY: "project_owner",
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_KEY: "admin1:user",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY: "test_project1:project",
        },
        {
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_ID_KEY: "Admin Group",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_ID_KEY: "test_project1",
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_KEY: "group",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_KEY: "project",
            db_utils.ROLE_ASSIGNMENT_DB_ROLD_ID_KEY: "project_owner",
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_KEY: "Admin Group:group",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY: "test_project1:project",
        },
    ]

    resolver = RoleAssignmentsTableMerger()
    record_deltas, success = resolver.merge(
        context,
        table_data_to_merge,
        "dedup_id",
        {
            TableName.PROJECTS_TABLE_NAME: [
                MergedRecordDelta(
                    snapshot_record={"project_id": "test_project1"},
                    resolved_record={"project_id": "test_project1"},
                )
            ]
        },
        ApplySnapshotObservabilityHelper(
            context.logger("role_assignments_table_resolver")
        ),
    )
    assert success
    assert len(record_deltas) == 2
    assert record_deltas[0].original_record is None

    for i in range(len(record_deltas)):
        assert (
            record_deltas[i].snapshot_record.get(
                db_utils.ROLE_ASSIGNMENT_DB_ACTOR_ID_KEY
            )
            == table_data_to_merge[i][db_utils.ROLE_ASSIGNMENT_DB_ACTOR_ID_KEY]
        )
        assert (
            record_deltas[i].resolved_record.get(
                db_utils.ROLE_ASSIGNMENT_DB_ACTOR_ID_KEY
            )
            == table_data_to_merge[i][db_utils.ROLE_ASSIGNMENT_DB_ACTOR_ID_KEY]
        )
        assert record_deltas[i].action_performed == MergedRecordActionType.CREATE

        retrieved_assignment = context.role_assignments.list_role_assignments(
            ListRoleAssignmentsRequest(
                actor_key=f"{record_deltas[i].resolved_record.get(db_utils.ROLE_ASSIGNMENT_DB_ACTOR_KEY)}",
                resource_key=f"{record_deltas[i].resolved_record.get(db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY)}",
            )
        ).items[0]

        assert retrieved_assignment is not None
        assert retrieved_assignment.role_id == record_deltas[i].resolved_record.get(
            db_utils.ROLE_ASSIGNMENT_DB_ROLD_ID_KEY
        )
        assert retrieved_assignment.actor_id == record_deltas[i].resolved_record.get(
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_ID_KEY
        )
        assert retrieved_assignment.actor_type == record_deltas[i].resolved_record.get(
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_KEY
        )
        assert retrieved_assignment.resource_type == record_deltas[
            i
        ].resolved_record.get(db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_KEY)
        assert retrieved_assignment.resource_id == record_deltas[i].resolved_record.get(
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_ID_KEY
        )

        imported_role_assignment_id = context.role_assignments.get_role_assignment(
            actor_key=table_data_to_merge[i][db_utils.ROLE_ASSIGNMENT_DB_ACTOR_KEY],
            resource_key=table_data_to_merge[i][
                db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY
            ],
        ).role_id
        assert (
            imported_role_assignment_id
            == table_data_to_merge[i][db_utils.ROLE_ASSIGNMENT_DB_ROLD_ID_KEY]
        )


def test_role_assignments_table_merger_ignore_existing_role_assignment_succeed(
    context: AppContext, monkeypatch
):
    monkeypatch.setattr(
        context.role_assignments,
        "verify_actor_exists",
        lambda actor_id, actor_type: True,
    )
    monkeypatch.setattr(
        context.role_assignments,
        "verify_resource_exists",
        lambda resource_id, resource_type: True,
    )

    context.role_assignments.put_role_assignment(
        PutRoleAssignmentRequest(
            request_id=generate_random_id("req"),
            actor_id="admin1",
            resource_id="test_project1",
            resource_type="project",
            actor_type="user",
            role_id="project_owner",
        )
    )

    table_data_to_merge = [
        {
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_ID_KEY: "admin1",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_ID_KEY: "test_project1",
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_KEY: "user",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_KEY: "project",
            db_utils.ROLE_ASSIGNMENT_DB_ROLD_ID_KEY: "project_owner",
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_KEY: "admin1:user",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY: "test_project1:project",
        }
    ]

    resolver = RoleAssignmentsTableMerger()
    record_deltas, success = resolver.merge(
        context,
        table_data_to_merge,
        "dedup_id",
        {
            TableName.PROJECTS_TABLE_NAME: [
                MergedRecordDelta(
                    snapshot_record={"project_id": "test_project1"},
                    resolved_record={"project_id": "test_project1"},
                )
            ]
        },
        ApplySnapshotObservabilityHelper(
            context.logger("role_assignments_table_resolver")
        ),
    )
    assert success
    assert len(record_deltas) == 0


def test_role_assignments_table_merger_rollback_original_data_succeed(
    context: AppContext, monkeypatch
):
    monkeypatch.setattr(
        context.role_assignments,
        "verify_actor_exists",
        lambda actor_id, actor_type: True,
    )
    monkeypatch.setattr(
        context.role_assignments,
        "verify_resource_exists",
        lambda resource_id, resource_type: True,
    )

    put_role_assignment_request = PutRoleAssignmentRequest(
        request_id=generate_random_id("req"),
        actor_id="admin1",
        resource_id="test_project1",
        resource_type="project",
        actor_type="user",
        role_id="project_owner",
    )

    context.role_assignments.put_role_assignment(put_role_assignment_request)

    resolver = RoleAssignmentsTableMerger()
    delta_records = [
        MergedRecordDelta(
            snapshot_record={
                db_utils.ROLE_ASSIGNMENT_DB_ACTOR_ID_KEY: "admin1",
                db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_ID_KEY: "test_project1",
                db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_KEY: "user",
                db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_KEY: "project",
                db_utils.ROLE_ASSIGNMENT_DB_ROLD_ID_KEY: "project_owner",
                db_utils.ROLE_ASSIGNMENT_DB_ACTOR_KEY: "admin1:user",
                db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY: "test_project1:project",
            },
            resolved_record={
                db_utils.ROLE_ASSIGNMENT_DB_ACTOR_ID_KEY: "admin1",
                db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_ID_KEY: "test_project1",
                db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_KEY: "user",
                db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_KEY: "project",
                db_utils.ROLE_ASSIGNMENT_DB_ROLD_ID_KEY: "project_owner",
                db_utils.ROLE_ASSIGNMENT_DB_ACTOR_KEY: "admin1:user",
                db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY: "test_project1:project",
            },
            action_performed=MergedRecordActionType.CREATE,
        ),
    ]
    resolver.rollback(
        context,
        delta_records,
        ApplySnapshotObservabilityHelper(
            context.logger("role_assignments_table_resolver")
        ),
    )

    retrieved_assignment = context.role_assignments.get_role_assignment(
        actor_key=f"{put_role_assignment_request.actor_id}:{put_role_assignment_request.actor_type}",
        resource_key=f"{put_role_assignment_request.resource_id}:{put_role_assignment_request.resource_type}",
    )

    assert retrieved_assignment is None


def test_role_assignments_table_resolve_non_existing_record_succeed(
    context: AppContext, monkeypatch
):
    monkeypatch.setattr(
        context.role_assignments,
        "verify_actor_exists",
        lambda actor_id, actor_type: True,
    )
    monkeypatch.setattr(
        context.role_assignments,
        "verify_resource_exists",
        lambda resource_id, resource_type: True,
    )

    table_data_to_merge = [
        {
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_ID_KEY: "admin1",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_ID_KEY: "test_project1",
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_KEY: "user",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_KEY: "project",
            db_utils.ROLE_ASSIGNMENT_DB_ROLD_ID_KEY: "project_owner",
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_KEY: "admin1:user",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY: "test_project1:project",
        }
    ]

    resolver = RoleAssignmentsTableMerger()

    for role_assignment_snapshot_record in table_data_to_merge:
        resolved_record, action_type = resolver.resolve_record(
            context,
            copy.deepcopy(role_assignment_snapshot_record),
            {"test_project1": "test_project1"},  # project ID mappings
            ApplySnapshotObservabilityHelper(
                context.logger("role_assignments_table_resolver")
            ),
        )

        assert resolved_record == role_assignment_snapshot_record
        assert action_type == MergedRecordActionType.CREATE


def test_role_assignments_table_resolve_non_existing_actor_suppress_error_no_record_creation(
    context: AppContext, monkeypatch
):
    monkeypatch.setattr(
        context.role_assignments,
        "verify_resource_exists",
        lambda resource_id, resource_type: True,
    )

    table_data_to_merge = [
        {
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_ID_KEY: "admin1",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_ID_KEY: "test_project1",
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_KEY: "user",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_KEY: "project",
            db_utils.ROLE_ASSIGNMENT_DB_ROLD_ID_KEY: "project_owner",
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_KEY: "admin1:user",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY: "test_project1:project",
        }
    ]

    resolver = RoleAssignmentsTableMerger()

    for role_assignment_snapshot_record in table_data_to_merge:
        resolved_record, action_type = resolver.resolve_record(
            context,
            copy.deepcopy(role_assignment_snapshot_record),
            {"test_project1": "test_project1"},
            ApplySnapshotObservabilityHelper(
                context.logger("role_assignments_table_resolver")
            ),
        )

        assert resolved_record == role_assignment_snapshot_record
        assert (
            action_type == None
        )  # Record should not be created since actor does not exist in RES environment


def test_role_assignments_table_resolve_non_existing_resource_suppress_error_no_record_creation(
    context: AppContext, monkeypatch
):
    monkeypatch.setattr(
        context.role_assignments,
        "verify_actor_exists",
        lambda actor_id, actor_type: True,
    )

    table_data_to_merge = [
        {
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_ID_KEY: "admin1",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_ID_KEY: "test_project1",
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_KEY: "user",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_KEY: "project",
            db_utils.ROLE_ASSIGNMENT_DB_ROLD_ID_KEY: "project_owner",
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_KEY: "admin1:user",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY: "test_project1:project",
        }
    ]

    resolver = RoleAssignmentsTableMerger()

    for role_assignment_snapshot_record in table_data_to_merge:
        resolved_record, action_type = resolver.resolve_record(
            context,
            copy.deepcopy(role_assignment_snapshot_record),
            {"test_project1": "test_project1"},
            ApplySnapshotObservabilityHelper(
                context.logger("role_assignments_table_resolver")
            ),
        )

        assert resolved_record == role_assignment_snapshot_record
        assert (
            action_type == None
        )  # Record should not be created since project does not exist in RES environment


def test_role_assignments_table_resolve_existing_record_succeed(
    context: AppContext, monkeypatch
):
    monkeypatch.setattr(
        context.role_assignments,
        "verify_actor_exists",
        lambda actor_id, actor_type: True,
    )
    monkeypatch.setattr(
        context.role_assignments,
        "verify_resource_exists",
        lambda resource_id, resource_type: True,
    )

    table_data_to_merge = [
        {
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_ID_KEY: "admin1",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_ID_KEY: "test_project1",
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_KEY: "user",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_KEY: "project",
            db_utils.ROLE_ASSIGNMENT_DB_ROLD_ID_KEY: "project_owner",
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_KEY: "admin1:user",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY: "test_project1:project",
        },
        # Add a group record
        {
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_ID_KEY: "Admin Group",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_ID_KEY: "test_project1",
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_KEY: "group",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_KEY: "project",
            db_utils.ROLE_ASSIGNMENT_DB_ROLD_ID_KEY: "project_owner",
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_KEY: "Admin Group:group",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY: "test_project1:project",
        },
    ]

    context.role_assignments.put_role_assignment(
        PutRoleAssignmentRequest(
            request_id=generate_random_id("req"),
            actor_id="admin1",
            resource_id="test_project1",
            resource_type="project",
            actor_type="user",
            role_id="project_owner",
        )
    )

    context.role_assignments.put_role_assignment(
        PutRoleAssignmentRequest(
            request_id=generate_random_id("req"),
            actor_id="Admin Group",
            resource_id="test_project1",
            resource_type="project",
            actor_type="group",
            role_id="project_owner",
        )
    )

    resolver = RoleAssignmentsTableMerger()

    for role_assignment_snapshot_record in table_data_to_merge:
        resolved_record, action_type = resolver.resolve_record(
            context,
            copy.deepcopy(role_assignment_snapshot_record),
            {"test_project1": "test_project1"},  # project ID mappings
            ApplySnapshotObservabilityHelper(
                context.logger("role_assignments_table_resolver")
            ),
        )

        assert resolved_record == role_assignment_snapshot_record
        assert action_type is None


def test_role_assignments_resolver_resolve_project_id_succeed(
    context: AppContext, monkeypatch
):

    monkeypatch.setattr(
        context.role_assignments,
        "verify_actor_exists",
        lambda actor_id, actor_type: True,
    )
    monkeypatch.setattr(
        context.role_assignments,
        "verify_resource_exists",
        lambda resource_id, resource_type: True,
    )

    table_data_to_merge = [
        {
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_ID_KEY: "admin1",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_ID_KEY: "snapshot_project_id",
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_KEY: "user",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_KEY: "project",
            db_utils.ROLE_ASSIGNMENT_DB_ROLD_ID_KEY: "project_owner",
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_KEY: "admin1:user",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY: "snapshot_project_id:project",
        }
    ]

    resolver = RoleAssignmentsTableMerger()
    record_deltas, success = resolver.merge(
        context,
        table_data_to_merge,
        "dedup_id",
        {
            TableName.PROJECTS_TABLE_NAME: [
                MergedRecordDelta(
                    snapshot_record={"project_id": "snapshot_project_id"},
                    resolved_record={"project_id": "resolved_project_id"},
                )
            ]
        },
        ApplySnapshotObservabilityHelper(
            context.logger("role_assignments_table_resolver")
        ),
    )
    assert success
    assert len(record_deltas) == 1
    assert record_deltas[0].original_record is None
    assert (
        record_deltas[0].snapshot_record.get(db_utils.ROLE_ASSIGNMENT_DB_ACTOR_ID_KEY)
        == "admin1"
    )
    assert (
        record_deltas[0].resolved_record.get(db_utils.ROLE_ASSIGNMENT_DB_ACTOR_ID_KEY)
        == "admin1"
    )
    assert record_deltas[0].action_performed == MergedRecordActionType.CREATE
    assert (
        record_deltas[0].resolved_record.get(db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY)
        == f"resolved_project_id:{db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_PROJECT_VALUE}"
    )

    retrieved_assignment = context.role_assignments.list_role_assignments(
        ListRoleAssignmentsRequest(
            actor_key=f"{record_deltas[0].resolved_record.get(db_utils.ROLE_ASSIGNMENT_DB_ACTOR_KEY)}",
            resource_key=f"{record_deltas[0].resolved_record.get(db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY)}",
        )
    ).items[0]

    assert retrieved_assignment is not None
    assert retrieved_assignment.role_id == record_deltas[0].resolved_record.get(
        db_utils.ROLE_ASSIGNMENT_DB_ROLD_ID_KEY
    )
    assert retrieved_assignment.actor_id == record_deltas[0].resolved_record.get(
        db_utils.ROLE_ASSIGNMENT_DB_ACTOR_ID_KEY
    )
    assert retrieved_assignment.actor_type == record_deltas[0].resolved_record.get(
        db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_KEY
    )
    assert retrieved_assignment.resource_type == record_deltas[0].resolved_record.get(
        db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_KEY
    )
    assert retrieved_assignment.resource_id == record_deltas[0].resolved_record.get(
        db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_ID_KEY
    )

    record_with_old_project_id = context.role_assignments.get_role_assignment(
        actor_key=table_data_to_merge[0][db_utils.ROLE_ASSIGNMENT_DB_ACTOR_KEY],
        resource_key=table_data_to_merge[0][
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY
        ],  # This contains the old snapshot_project_id value
    )
    assert record_with_old_project_id is None


def test_role_assignments_table_resolve_non_existing_record_different_project_id_succeed(
    context: AppContext, monkeypatch
):
    monkeypatch.setattr(
        context.role_assignments,
        "verify_actor_exists",
        lambda actor_id, actor_type: True,
    )
    monkeypatch.setattr(
        context.role_assignments,
        "verify_resource_exists",
        lambda resource_id, resource_type: True,
    )

    table_data_to_merge = [
        {
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_ID_KEY: "admin1",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_ID_KEY: "old_project_id",
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_KEY: "user",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_KEY: "project",
            db_utils.ROLE_ASSIGNMENT_DB_ROLD_ID_KEY: "project_owner",
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_KEY: "admin1:user",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY: "old_project_id:project",
        }
    ]

    expected_resolved_record = {
        db_utils.ROLE_ASSIGNMENT_DB_ACTOR_ID_KEY: "admin1",
        db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_ID_KEY: "new_project_id",
        db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_KEY: "user",
        db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_KEY: "project",
        db_utils.ROLE_ASSIGNMENT_DB_ROLD_ID_KEY: "project_owner",
        db_utils.ROLE_ASSIGNMENT_DB_ACTOR_KEY: "admin1:user",
        db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY: "new_project_id:project",
    }

    resolver = RoleAssignmentsTableMerger()

    for role_assignment_snapshot_record in table_data_to_merge:
        resolved_record, action_type = resolver.resolve_record(
            context,
            copy.deepcopy(role_assignment_snapshot_record),
            {"old_project_id": "new_project_id"},  # project ID mappings
            ApplySnapshotObservabilityHelper(
                context.logger("role_assignments_table_resolver")
            ),
        )

        assert resolved_record == expected_resolved_record
        assert action_type == MergedRecordActionType.CREATE


def test_role_assignments_table_resolve_existing_record_different_project_id_skip(
    context: AppContext, monkeypatch
):
    monkeypatch.setattr(
        context.role_assignments,
        "verify_actor_exists",
        lambda actor_id, actor_type: True,
    )
    monkeypatch.setattr(
        context.role_assignments,
        "verify_resource_exists",
        lambda resource_id, resource_type: True,
    )

    table_data_to_merge = [
        {
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_ID_KEY: "admin1",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_ID_KEY: "old_project_id",
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_KEY: "user",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_KEY: "project",
            db_utils.ROLE_ASSIGNMENT_DB_ROLD_ID_KEY: "project_owner",
            db_utils.ROLE_ASSIGNMENT_DB_ACTOR_KEY: "admin1:user",
            db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY: "old_project_id:project",
        }
    ]

    context.role_assignments.put_role_assignment(
        PutRoleAssignmentRequest(
            request_id=generate_random_id("req"),
            actor_id="admin1",
            resource_id="new_project_id",
            resource_type="project",
            actor_type="user",
            role_id="project_owner",
        )
    )

    expected_resolved_record = {
        db_utils.ROLE_ASSIGNMENT_DB_ACTOR_ID_KEY: "admin1",
        db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_ID_KEY: "new_project_id",
        db_utils.ROLE_ASSIGNMENT_DB_ACTOR_TYPE_KEY: "user",
        db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_TYPE_KEY: "project",
        db_utils.ROLE_ASSIGNMENT_DB_ROLD_ID_KEY: "project_owner",
        db_utils.ROLE_ASSIGNMENT_DB_ACTOR_KEY: "admin1:user",
        db_utils.ROLE_ASSIGNMENT_DB_RESOURCE_KEY: "new_project_id:project",
    }

    resolver = RoleAssignmentsTableMerger()

    for role_assignment_snapshot_record in table_data_to_merge:
        resolved_record, action_type = resolver.resolve_record(
            context,
            copy.deepcopy(role_assignment_snapshot_record),
            {"old_project_id": "new_project_id"},  # project ID mappings
            ApplySnapshotObservabilityHelper(
                context.logger("role_assignments_table_resolver")
            ),
        )

        assert resolved_record == expected_resolved_record
        assert action_type == None
