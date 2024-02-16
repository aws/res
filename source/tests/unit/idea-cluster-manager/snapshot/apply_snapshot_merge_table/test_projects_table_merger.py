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
from ideaclustermanager.app.snapshots.apply_snapshot_merge_table.projects_table_merger import (
    ProjectsTableMerger,
)
from ideaclustermanager.app.snapshots.helpers.apply_snapshot_observability_helper import (
    ApplySnapshotObservabilityHelper,
)
from ideaclustermanager.app.snapshots.helpers.merged_record_utils import (
    MergedRecordActionType,
    MergedRecordDelta,
)
from ideasdk.utils.utils import Utils

from ideadatamodel import (
    GetProjectRequest,
    UpdateProjectRequest,
    UpdateProjectResult,
    errorcodes,
    exceptions,
)


def test_projects_table_merger_merge_new_project_succeed(
    context: AppContext, monkeypatch
):
    table_data_to_merge = [
        {
            "project_id": "test_project_id",
            "created_on": 0,
            "description": "test_project",
            "enable_budgets": False,
            "enabled": True,
            "ldap_groups": [],
            "name": "test_project",
            "title": "test_project",
            "updated_on": 0,
            "users": [],
        }
    ]

    resolver = ProjectsTableMerger()
    record_deltas, success = resolver.merge(
        context,
        table_data_to_merge,
        "dedup_id",
        {},
        ApplySnapshotObservabilityHelper(context.logger("projects_table_resolver")),
    )
    assert success
    assert len(record_deltas) == 1
    assert record_deltas[0].original_record is None
    assert record_deltas[0].snapshot_record.get("name") == "test_project"
    assert record_deltas[0].resolved_record.get("name") == "test_project"
    assert record_deltas[0].action_performed == MergedRecordActionType.CREATE

    imported_project = context.projects.get_project(
        GetProjectRequest(project_name="test_project")
    ).project
    assert imported_project is not None


def test_users_table_merger_merge_existing_project_succeed(
    context: AppContext, monkeypatch
):
    context.projects.projects_dao.create_project(
        {
            "project_id": "test_project_id_1",
            "created_on": 0,
            "description": "",
            "enable_budgets": False,
            "enabled": True,
            "ldap_groups": [],
            "name": "test_project_1",
            "title": "test_project_1",
            "updated_on": 0,
            "users": [],
        }
    )
    table_data_to_merge = [
        {
            "project_id": "test_project_id_1",
            "created_on": 0,
            "description": "test_project_1",
            "enable_budgets": False,
            "enabled": True,
            "ldap_groups": [],
            "name": "test_project_1",
            "title": "test_project_1",
            "updated_on": 0,
            "users": [],
        },
    ]

    resolver = ProjectsTableMerger()
    record_deltas, success = resolver.merge(
        context,
        table_data_to_merge,
        "dedup_id",
        {},
        ApplySnapshotObservabilityHelper(context.logger("projects_table_resolver")),
    )
    assert success
    assert len(record_deltas) == 1
    assert record_deltas[0].original_record is None
    assert record_deltas[0].snapshot_record.get("name") == "test_project_1"
    assert record_deltas[0].resolved_record.get("name") == "test_project_1_dedup_id"
    assert record_deltas[0].action_performed == MergedRecordActionType.CREATE

    project = context.projects.get_project(
        GetProjectRequest(project_name=f"test_project_1_dedup_id")
    ).project
    assert project is not None


def test_users_table_resolver_rollback_original_data_succeed(
    context: AppContext, monkeypatch
):
    context.projects.projects_dao.create_project(
        {
            "project_id": "test_project_id_2",
            "created_on": 0,
            "description": "test_project_2",
            "enable_budgets": False,
            "enabled": True,
            "ldap_groups": [],
            "name": "test_project_2",
            "title": "test_project_2",
            "updated_on": 0,
            "users": [],
        }
    )

    resolver = ProjectsTableMerger()
    delta_records = [
        MergedRecordDelta(
            snapshot_record={
                "project_id": "test_project_id_2",
                "created_on": 0,
                "description": "test_project_2",
                "enable_budgets": False,
                "enabled": True,
                "ldap_groups": [],
                "name": "test_project_2",
                "title": "test_project_2",
                "updated_on": 0,
                "users": [],
            },
            resolved_record={
                "project_id": "test_project_id_2",
                "created_on": 0,
                "description": "test_project_2",
                "enable_budgets": False,
                "enabled": True,
                "ldap_groups": [],
                "name": "test_project_2",
                "title": "test_project_2",
                "updated_on": 0,
                "users": [],
            },
            action_performed=MergedRecordActionType.CREATE,
        ),
    ]
    resolver.rollback(
        context,
        delta_records,
        ApplySnapshotObservabilityHelper(context.logger("projects_table_resolver")),
    )

    with pytest.raises(exceptions.SocaException) as exc_info:
        _project = context.projects.get_project(
            GetProjectRequest(project_name="test_project_2")
        ).project
    assert exc_info.value.error_code == errorcodes.PROJECT_NOT_FOUND


def test_users_table_merger_ignore_existing_project_succeed(
    context: AppContext, monkeypatch
):
    context.projects.projects_dao.create_project(
        {
            "project_id": "test_project_id_3",
            "created_on": 0,
            "description": "test_project_3",
            "enable_budgets": False,
            "enabled": False,
            "ldap_groups": [],
            "name": "test_project_3",
            "title": "test_project_3",
            "updated_on": 0,
            "users": [],
        }
    )
    project = context.projects.get_project(
        GetProjectRequest(project_name=f"test_project_3")
    ).project
    created_on = Utils.to_milliseconds(project.created_on)
    updated_on = Utils.to_milliseconds(project.updated_on)
    project = context.projects.projects_dao.convert_to_db(project)
    project["created_on"] = created_on
    project["updated_on"] = updated_on
    table_data_to_merge = [project]

    resolver = ProjectsTableMerger()
    record_deltas, success = resolver.merge(
        context,
        table_data_to_merge,
        "dedup_id",
        {},
        ApplySnapshotObservabilityHelper(context.logger("projects_table_resolver")),
    )
    assert success
    assert len(record_deltas) == 0


def test_projects_table_merger_ignore_nonexistent_group_succeed(
    context: AppContext, monkeypatch
):
    table_data_to_merge = [
        {
            "project_id": "test_project_id_4",
            "created_on": 0,
            "description": "test_project_4",
            "enable_budgets": False,
            "enabled": True,
            "ldap_groups": ["group_1"],
            "name": "test_project_4",
            "title": "test_project_4",
            "updated_on": 0,
            "users": [],
        }
    ]

    resolver = ProjectsTableMerger()
    record_deltas, success = resolver.merge(
        context,
        table_data_to_merge,
        "dedup_id",
        {},
        ApplySnapshotObservabilityHelper(context.logger("projects_table_resolver")),
    )
    assert success
    assert len(record_deltas) == 1
    assert not record_deltas[0].resolved_record.get("ldap_groups")


def test_projects_table_merger_ignore_nonexistent_user_succeed(
    context: AppContext, monkeypatch
):
    table_data_to_merge = [
        {
            "project_id": "test_project_id_5",
            "created_on": 0,
            "description": "test_project_5",
            "enable_budgets": False,
            "enabled": True,
            "ldap_groups": [],
            "name": "test_project_5",
            "title": "test_project_5",
            "updated_on": 0,
            "users": ["user1"],
        }
    ]

    resolver = ProjectsTableMerger()
    record_deltas, success = resolver.merge(
        context,
        table_data_to_merge,
        "dedup_id",
        {},
        ApplySnapshotObservabilityHelper(context.logger("projects_table_resolver")),
    )
    assert success
    assert len(record_deltas) == 1
    assert not record_deltas[0].resolved_record.get("users")


def test_projects_table_merger_add_groups_and_users_to_project_succeed(
    context: AppContext, monkeypatch
):
    monkeypatch.setattr(context.accounts, "get_group", lambda group_name: None)
    monkeypatch.setattr(context.accounts, "get_user", lambda username: None)

    project_groups_updated_called = False

    def _task_manager_send_mock(
        task_name, payload, message_group_id=None, message_dedupe_id=None
    ):
        if task_name == "projects.project-groups-updated":
            nonlocal project_groups_updated_called
            project_groups_updated_called = True

            assert payload["groups_added"] == ["group_1"]
            assert payload["users_added"] == ["user1"]

    monkeypatch.setattr(
        context.task_manager,
        "send",
        _task_manager_send_mock,
    )
    table_data_to_merge = [
        {
            "project_id": "test_project_id_6",
            "created_on": 0,
            "description": "test_project_6",
            "enable_budgets": False,
            "enabled": True,
            "ldap_groups": ["group_1"],
            "name": "test_project_6",
            "title": "test_project_6",
            "updated_on": 0,
            "users": ["user1"],
        }
    ]

    resolver = ProjectsTableMerger()
    record_deltas, success = resolver.merge(
        context,
        table_data_to_merge,
        "dedup_id",
        {},
        ApplySnapshotObservabilityHelper(context.logger("projects_table_resolver")),
    )
    assert success
    assert project_groups_updated_called


def test_projects_table_merger_ignore_nonexistent_budget_succeed(
    context: AppContext, monkeypatch
):
    def _budgets_get_budget(_budget_name):
        raise Exception()

    monkeypatch.setattr(
        context.aws_util(),
        "budgets_get_budget",
        _budgets_get_budget,
    )
    table_data_to_merge = [
        {
            "project_id": "test_project_id_7",
            "created_on": 0,
            "description": "test_project_7",
            "enable_budgets": True,
            "budget_name": "budget_name",
            "enabled": True,
            "ldap_groups": [],
            "name": "test_project_7",
            "title": "test_project_7",
            "updated_on": 0,
            "users": [],
        }
    ]

    resolver = ProjectsTableMerger()
    record_deltas, success = resolver.merge(
        context,
        table_data_to_merge,
        "dedup_id",
        {},
        ApplySnapshotObservabilityHelper(context.logger("projects_table_resolver")),
    )
    assert success

    project = context.projects.get_project(
        GetProjectRequest(project_name=f"test_project_7")
    ).project

    assert not project.enable_budgets
