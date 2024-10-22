#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Dict, Optional

from res.utils import table_utils  # type: ignore

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

GSI_PROJECT_NAME = "project-name-index"
PROJECTS_TABLE_NAME = "projects"


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
