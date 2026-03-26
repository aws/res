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
