#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict, List, Optional

import res.constants as constants  # type: ignore
from res.resources import accounts, cluster_settings
from res.resources import projects as res_projects  # type: ignore
from res.resources import role_assignments, roles
from res.utils import logging_utils, table_utils  # type: ignore

GSI_PROJECT_NAME = "project-name-index"
GSI_PROJECT_NAME_HASH_KEY = "name"
PROJECTS_TABLE_NAME = "projects"
PROJECTS_DB_HASH_KEY = "project_id"

logger = logging_utils.get_logger(PROJECTS_TABLE_NAME)


def get_project(
    project_id: Optional[str] = None, project_name: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Retrieve the Project from the DDB
    :param project_name name of the project you are getting
    :param project_id UUID of the project being searched
    :return: Project from DDB
    """
    if not project_id and not project_name:
        raise Exception("Either project_id or project_name is required")

    project = None
    if project_id:
        project = _get_project_by_id(project_id)
    elif project_name:
        project = _get_project_by_name(project_name)

    if not project:
        if project_id:
            raise Exception(
                f"project not found for project id: {project_id}",
            )
        if project_name:
            raise Exception(
                f"project not found for project name: {project_name}",
            )

    return project


def _get_project_by_id(project_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve the Project from the DDB by ID
    :param project_id UUID of the project being searched
    :return: Project from DDB
    """
    if not project_id:
        raise Exception("project_id is required")

    project: Optional[Dict[str, Any]] = table_utils.get_item(
        PROJECTS_TABLE_NAME, key={"project_id": project_id}
    )
    return project


def _get_project_by_name(name: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve the Project from the DDB by name
    :param name name of the project you are getting
    :return: Project from DDB
    """
    if not name:
        raise Exception("name is required")

    items = table_utils.query(
        PROJECTS_TABLE_NAME, index_name=GSI_PROJECT_NAME, attributes={"name": name}
    )
    if len(items) == 0:
        return None

    project: Dict[str, Any] = items[0]
    return project


def list_projects() -> List[Dict[str, Any]]:
    """
    Retrieve the projects from DDB
    :return: List of projects
    """
    projects: List[Dict[str, Any]] = table_utils.list_items(PROJECTS_TABLE_NAME)
    return projects


def list_user_manage_sessions_projects(username: str) -> List[str]:
    """
    Retrieve the project IDs where the user has permission to manage other user sessions
    :return: List of project IDs
    """
    # Get all role assignments for the user and their groups
    assignments = role_assignments.list_role_assignments_for_user_and_groups(username)
    if not assignments:
        return []

    # Extract unique role IDs from assignments
    unique_role_ids = {
        assignment[role_assignments.ROLE_ASSIGNMENTS_ROLE_ID_KEY]
        for assignment in assignments
    }
    # Filter to roles that have manage sessions permission
    manage_sessions_role_ids = roles.filter_roles_with_manage_sessions_permission(
        unique_role_ids
    )
    if not manage_sessions_role_ids:
        return []

    # Extract project IDs where user has manage sessions permission
    project_ids = {
        assignment[role_assignments.ROLE_ASSIGNMENTS_RESOURCE_ID_KEY]
        for assignment in assignments
        if assignment[role_assignments.ROLE_ASSIGNMENTS_ROLE_ID_KEY]
        in manage_sessions_role_ids
        and assignment[role_assignments.ROLE_ASSIGNMENTS_RESOURCE_TYPE_KEY]
        == constants.PROJECT_ROLE_ASSIGNMENT_TYPE
    }

    return sorted(project_ids)


def get_user_projects(username: str) -> List[Dict[str, Any]]:
    user_role_assignments = role_assignments.list_role_assignments_for_user_and_groups(
        username
    )

    user_project_ids = {
        assignment["resource_id"]
        for assignment in user_role_assignments
        if assignment.get("resource_type") == "project"
    }

    user_projects = []
    for project_id in user_project_ids:
        project = res_projects._get_project_by_id(project_id)
        if project is not None:
            user_projects.append(project)

    return user_projects


def get_allowed_sessions_per_user(project_id: str) -> int:
    """
    Get the allowed number of sessions per user for a project.
    Falls back to the cluster-level default if not set on the project.
    """
    project = _get_project_by_id(project_id)
    allowed = project.get("allowed_sessions_per_user") if project else None

    if allowed is None:
        allowed = cluster_settings.get_setting(
            "vdc.dcv_session.default_allowed_sessions_per_user_per_project",
        )
    return allowed
