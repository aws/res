#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Dict, Optional

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
