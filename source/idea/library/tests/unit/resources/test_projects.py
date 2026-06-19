#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Dict, Optional
from unittest.mock import Mock, patch

import pytest
from res.resources import projects  # type: ignore
from res.utils import table_utils  # type: ignore


class ProjectsTestContext:
    crud_project: Optional[Dict]


def create_project() -> Dict:
    project_id = "test_project_id"
    name = "test_project_name"
    created_project = {
        "project_id": project_id,
        "name": name,
    }
    table_utils.create_item(projects.PROJECTS_TABLE_NAME, item=created_project)

    return created_project


def test_projects_get_project_invalid_should_fail(context):
    """
    get project - invalid project id or name
    """
    # by project id
    with pytest.raises(Exception) as exc_info:
        projects.get_project(project_id="unknown-project-id")
    assert "project not found" in exc_info.value.args[0]

    # by project name
    with pytest.raises(Exception) as exc_info:
        projects.get_project(project_name="unknown-project-name")
    assert "project not found" in exc_info.value.args[0]


def test_projects_crud_get_project_by_name(context):
    """
    get project by name
    """
    project = create_project()
    ProjectsTestContext.crud_project = project

    result = projects.get_project(project_name=project["name"])
    assert result is not None
    assert result["name"] == project["name"]
    assert result["project_id"] == project["project_id"]


def test_projects_crud_get_project_by_id(context):
    """
    get project by id
    """
    assert ProjectsTestContext.crud_project is not None
    crud_project = ProjectsTestContext.crud_project

    result = projects.get_project(project_id=crud_project["project_id"])
    assert result is not None
    assert result["name"] == crud_project["name"]
    assert result["project_id"] == crud_project["project_id"]


@patch("res.resources.projects.roles.filter_roles_with_manage_sessions_permission")
@patch(
    "res.resources.projects.role_assignments.list_role_assignments_for_user_and_groups"
)
def test_list_user_manage_sessions_projects_user_with_manage_permission(
    mock_list_assignments_for_user, mock_filter_roles
):
    """
    Test list_user_manage_sessions_projects returns project IDs where user has manage sessions permission
    """
    mock_list_assignments_for_user.return_value = [
        {"role_id": "role1", "resource_id": "project1", "resource_type": "project"},
        {"role_id": "role2", "resource_id": "project2", "resource_type": "project"},
    ]
    mock_filter_roles.return_value = {"role1"}

    result = projects.list_user_manage_sessions_projects("testuser")

    assert result == ["project1"]
    mock_list_assignments_for_user.assert_called_once_with("testuser")
    mock_filter_roles.assert_called_once_with({"role1", "role2"})


@patch("res.resources.projects.roles.filter_roles_with_manage_sessions_permission")
@patch(
    "res.resources.projects.role_assignments.list_role_assignments_for_user_and_groups"
)
def test_list_user_manage_sessions_projects_user_without_manage_permission(
    mock_list_assignments_for_user, mock_filter_roles
):
    """
    Test list_user_manage_sessions_projects returns empty list when user has no manage sessions permission
    """
    mock_list_assignments_for_user.return_value = [
        {"role_id": "role1", "resource_id": "project1", "resource_type": "project"},
    ]
    mock_filter_roles.return_value = set()

    result = projects.list_user_manage_sessions_projects("testuser")

    assert result == []
    mock_list_assignments_for_user.assert_called_once_with("testuser")
    mock_filter_roles.assert_called_once_with({"role1"})


@patch("res.resources.projects.roles.filter_roles_with_manage_sessions_permission")
@patch(
    "res.resources.projects.role_assignments.list_role_assignments_for_user_and_groups"
)
def test_list_user_manage_sessions_projects_no_role_assignments(
    mock_list_assignments_for_user, mock_filter_roles
):
    """
    Test list_user_manage_sessions_projects returns empty list when user has no role assignments
    """
    mock_list_assignments_for_user.return_value = []

    result = projects.list_user_manage_sessions_projects("testuser")

    assert result == []
    mock_list_assignments_for_user.assert_called_once_with("testuser")
    mock_filter_roles.assert_not_called()


@patch("res.resources.projects.roles.filter_roles_with_manage_sessions_permission")
@patch(
    "res.resources.projects.role_assignments.list_role_assignments_for_user_and_groups"
)
def test_list_user_manage_sessions_projects_non_project_resources(
    mock_list_assignments_for_user, mock_filter_roles
):
    """
    Test list_user_manage_sessions_projects filters out non-project resource assignments
    """
    mock_list_assignments_for_user.return_value = [
        {"role_id": "role1", "resource_id": "project1", "resource_type": "project"},
        {"role_id": "role1", "resource_id": "cluster1", "resource_type": "cluster"},
    ]
    mock_filter_roles.return_value = {"role1"}

    result = projects.list_user_manage_sessions_projects("testuser")

    assert result == ["project1"]
    mock_list_assignments_for_user.assert_called_once_with("testuser")
    mock_filter_roles.assert_called_once_with({"role1"})


@patch("res.resources.projects.roles.filter_roles_with_manage_sessions_permission")
@patch(
    "res.resources.projects.role_assignments.list_role_assignments_for_user_and_groups"
)
def test_list_user_manage_sessions_projects_duplicate_roles_checked_once(
    mock_list_assignments_for_user, mock_filter_roles
):
    """
    Test list_user_manage_sessions_projects checks each unique role only once
    """
    mock_list_assignments_for_user.return_value = [
        {"role_id": "role1", "resource_id": "project1", "resource_type": "project"},
        {"role_id": "role1", "resource_id": "project2", "resource_type": "project"},
    ]
    mock_filter_roles.return_value = {"role1"}

    result = projects.list_user_manage_sessions_projects("testuser")

    assert sorted(result) == ["project1", "project2"]
    mock_list_assignments_for_user.assert_called_once_with("testuser")
    mock_filter_roles.assert_called_once_with({"role1"})


@patch("res.resources.projects._get_project_by_id")
@patch(
    "res.resources.projects.role_assignments.list_role_assignments_for_user_and_groups"
)
def test_get_user_projects_returns_project_details(
    mock_list_assignments_for_user, mock_get_project_by_id
):
    """
    Test get_user_projects returns full project details for user's assigned projects
    """
    mock_list_assignments_for_user.return_value = [
        {"role_id": "role1", "resource_id": "proj-1", "resource_type": "project"},
        {"role_id": "role2", "resource_id": "proj-2", "resource_type": "project"},
    ]
    mock_get_project_by_id.side_effect = [
        {"project_id": "proj-1", "name": "Project 1"},
        {"project_id": "proj-2", "name": "Project 2"},
    ]

    result = projects.get_user_projects("testuser")

    assert len(result) == 2
    assert {"project_id": "proj-1", "name": "Project 1"} in result
    assert {"project_id": "proj-2", "name": "Project 2"} in result
    mock_list_assignments_for_user.assert_called_once_with("testuser")


@patch("res.resources.projects._get_project_by_id")
@patch(
    "res.resources.projects.role_assignments.list_role_assignments_for_user_and_groups"
)
def test_get_user_projects_filters_non_project_resources(
    mock_list_assignments_for_user, mock_get_project_by_id
):
    """
    Test get_user_projects only returns projects, not other resource types
    """
    mock_list_assignments_for_user.return_value = [
        {"role_id": "role1", "resource_id": "proj-1", "resource_type": "project"},
        {"role_id": "role2", "resource_id": "cluster-1", "resource_type": "cluster"},
    ]
    mock_get_project_by_id.return_value = {"project_id": "proj-1", "name": "Project 1"}

    result = projects.get_user_projects("testuser")

    assert len(result) == 1
    assert result[0]["project_id"] == "proj-1"
    mock_get_project_by_id.assert_called_once_with("proj-1")


@patch("res.resources.projects._get_project_by_id")
@patch(
    "res.resources.projects.role_assignments.list_role_assignments_for_user_and_groups"
)
def test_get_user_projects_no_assignments(
    mock_list_assignments_for_user, mock_get_project_by_id
):
    """
    Test get_user_projects returns empty list when user has no role assignments
    """
    mock_list_assignments_for_user.return_value = []

    result = projects.get_user_projects("testuser")

    assert result == []
    mock_get_project_by_id.assert_not_called()


@patch("res.resources.projects._get_project_by_id")
@patch(
    "res.resources.projects.role_assignments.list_role_assignments_for_user_and_groups"
)
def test_get_user_projects_skips_none_projects(
    mock_list_assignments_for_user, mock_get_project_by_id
):
    """
    Test get_user_projects skips projects that return None from _get_project_by_id
    """
    mock_list_assignments_for_user.return_value = [
        {"role_id": "role1", "resource_id": "proj-1", "resource_type": "project"},
        {"role_id": "role2", "resource_id": "proj-2", "resource_type": "project"},
    ]
    mock_get_project_by_id.side_effect = [
        {"project_id": "proj-1", "name": "Project 1"},
        None,
    ]

    result = projects.get_user_projects("testuser")

    assert len(result) == 1
    assert result[0]["project_id"] == "proj-1"


@patch("res.resources.projects._get_project_by_id")
def test_get_allowed_sessions_per_user_from_project(mock_get_project_by_id):
    """Test returns allowed_sessions_per_user from project when set."""
    mock_get_project_by_id.return_value = {
        "project_id": "proj-1",
        "allowed_sessions_per_user": 3,
    }

    result = projects.get_allowed_sessions_per_user("proj-1")

    assert result == 3


@patch("res.resources.projects.cluster_settings.get_setting")
@patch("res.resources.projects._get_project_by_id")
def test_get_allowed_sessions_per_user_falls_back_to_cluster_setting(
    mock_get_project_by_id, mock_get_setting
):
    """Test falls back to cluster setting when project doesn't have it set."""
    mock_get_project_by_id.return_value = {"project_id": "proj-1"}
    mock_get_setting.return_value = 5

    result = projects.get_allowed_sessions_per_user("proj-1")

    assert result == 5
    mock_get_setting.assert_called_once_with(
        "vdc.dcv_session.default_allowed_sessions_per_user_per_project"
    )
