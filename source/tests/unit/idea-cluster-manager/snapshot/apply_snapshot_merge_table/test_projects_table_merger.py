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

from ideadatamodel import GetProjectRequest, errorcodes, exceptions


def generate_random_id(prefix: str) -> str:
    return f"test-{prefix}-{Utils.short_uuid()}"


def test_projects_table_merger_merge_new_project_succeed(
    context: AppContext, monkeypatch
):
    project_name = generate_random_id("proj-name")
    table_data_to_merge = [
        {
            "name": project_name,
            "title": "Test Project",
            "description": "This is a test project.",
            "enable_budgets": False,
            "enabled": True,
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
    assert record_deltas[0].snapshot_record.get("name") == project_name
    assert record_deltas[0].resolved_record.get("name") == project_name
    assert record_deltas[0].action_performed == MergedRecordActionType.CREATE

    imported_project = context.projects.get_project(
        GetProjectRequest(project_name=project_name)
    ).project
    assert imported_project is not None


def test_projects_table_merger_merge_new_ldap_users_project_succeed(
    context: AppContext, monkeypatch
):
    project_name = generate_random_id("proj-name")
    table_data_to_merge = [
        {
            "name": project_name,
            "title": "Test Project",
            "description": "This is a test project.",
            "enable_budgets": False,
            "enabled": True,
            "ldap_groups": ["RESAdministrators", "group_1", "group_2"],
            "users": ["admin1", "user1", "user2", "admin2"],
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
    assert record_deltas[0].snapshot_record.get("name") == project_name
    assert record_deltas[0].resolved_record.get("name") == project_name
    assert record_deltas[0].action_performed == MergedRecordActionType.CREATE

    imported_project = context.projects.get_project(
        GetProjectRequest(project_name=table_data_to_merge[0]["name"])
    ).project
    assert imported_project is not None


def test_users_table_resolver_rollback_original_data_succeed(
    context: AppContext, monkeypatch
):

    project_name = generate_random_id("proj-name")
    context.projects.projects_dao.create_project(
        {
            "name": project_name,
            "title": "Test Project",
            "description": "This is a test project.",
            "enable_budgets": False,
            "enabled": True,
        }
    )

    resolver = ProjectsTableMerger()
    delta_records = [
        MergedRecordDelta(
            snapshot_record={
                "name": project_name,
                "title": "Test Project",
                "created_on": 0,
                "description": "This is a test project.",
                "enable_budgets": False,
                "enabled": True,
                "ldap_groups": [],
                "updated_on": 0,
                "users": [],
            },
            resolved_record={
                "name": project_name,
                "title": "Test Project",
                "created_on": 0,
                "description": "This is a test project.",
                "enable_budgets": False,
                "enabled": True,
                "updated_on": 0,
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
            GetProjectRequest(project_name=project_name)
        ).project
    assert exc_info.value.error_code == errorcodes.PROJECT_NOT_FOUND


def test_users_table_merger_ignore_existing_project_succeed(
    context: AppContext, monkeypatch
):

    project_name = generate_random_id("proj-name")
    context.projects.projects_dao.create_project(
        {
            "name": project_name,
            "title": "Test Project",
            "description": "This is a test project.",
            "enable_budgets": False,
            "enabled": False,
        }
    )
    project = context.projects.projects_dao.convert_to_db(
        context.projects.get_project(
            GetProjectRequest(project_name=project_name)
        ).project
    )
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

    project_name = generate_random_id("proj-name")
    table_data_to_merge = [
        {
            "name": project_name,
            "title": "Test Project",
            "description": "This is a test project.",
            "enable_budgets": True,
            "budget_name": "budget_name",
            "enabled": True,
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
        GetProjectRequest(project_name=project_name)
    ).project

    assert not project.enable_budgets
