#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
Test Cases for RoleAssignmentsService
"""

from typing import Dict, Optional

import pytest
import res.constants as constants
import shortuuid
from res.resources import role_assignments
from res.utils import table_utils


class RoleAssignmentsTestContext:
    crud_role_assignment: Optional[Dict]


def generate_random_id(prefix: str) -> str:
    return f"test-{prefix}-{shortuuid.uuid()}".lower()[
        : constants.AD_SAM_ACCOUNT_NAME_MAX_LENGTH
    ]


def put_role_assignment() -> Dict:
    actor_id = generate_random_id("actor")
    resource_id = generate_random_id("project")
    actor_type = "user"
    resource_type = "project"
    role_id = constants.PROJECT_MEMBER_ROLE_ID
    actor_key = f"{actor_id}:{actor_type}"
    resource_key = f"{resource_id}:{resource_type}"
    table_utils.create_item(
        role_assignments.ROLE_ASSIGNMENTS_TABLE_NAME,
        item={
            "actor_key": actor_key,
            "resource_key": resource_key,
            "actor_id": actor_id,
            "resource_id": resource_id,
            "actor_type": actor_type,
            "resource_type": resource_type,
            "role_id": role_id,
        },
    )
    return {
        "actor_key": actor_key,
        "resource_key": resource_key,
        "actor_id": actor_id,
        "resource_id": resource_id,
        "actor_type": actor_type,
        "resource_type": resource_type,
        "role_id": role_id,
    }


def test_delete_role_assignment_invalid_params():
    """
    Test for delete_role_assignment method with invalid parameters
    """

    def verify_invalid_scenario(actor_key: str, resource_key: str, error_message: str):
        # Perform the delete_role_assignment operation with invalid parameters
        with pytest.raises(Exception) as exc_info:
            role_assignments.delete_role_assignment(
                {
                    "actor_key": actor_key,
                    "resource_key": resource_key,
                }
            )
        assert error_message in exc_info.value.args[0]

    verify_invalid_scenario(
        actor_key=f'{generate_random_id("actor")}:blah',
        resource_key="",
        error_message="resource_key is required",
    )

    verify_invalid_scenario(
        actor_key="",
        resource_key=f'{generate_random_id("project")}:blah',
        error_message="actor_key is required",
    )


def test_get_role_assignment(context, monkeypatch):
    """
    Test for get_role_assignment method
    """
    crud_role_assignment = put_role_assignment()
    RoleAssignmentsTestContext.crud_role_assignment = crud_role_assignment

    monkeypatch.setattr(
        role_assignments,
        "_verify_actor_exists",
        lambda actor_id, actor_type: True,
    )
    monkeypatch.setattr(
        role_assignments,
        "_verify_resource_exists",
        lambda resource_id, resource_type: True,
    )

    # Perform the get_role_assignment operation
    response = role_assignments.get_role_assignment(
        crud_role_assignment["actor_key"],
        crud_role_assignment["resource_key"],
    )

    # Check the success response
    assert response is not None
    assert response["actor_key"] == crud_role_assignment["actor_key"]
    assert response["resource_key"] == crud_role_assignment["resource_key"]
    assert response["role_id"] == crud_role_assignment["role_id"]


def test_crud_list_role_assignment(context, monkeypatch):
    """
    Test for list_role_assignment method
    """
    assert RoleAssignmentsTestContext.crud_role_assignment is not None
    crud_role_assignment = RoleAssignmentsTestContext.crud_role_assignment

    monkeypatch.setattr(
        role_assignments,
        "_verify_actor_exists",
        lambda actor_id, actor_type: True,
    )
    monkeypatch.setattr(
        role_assignments,
        "_verify_resource_exists",
        lambda resource_id, resource_type: True,
    )

    retrieved_assignments = role_assignments.list_role_assignments(
        actor_key=crud_role_assignment["actor_key"],
        resource_key=crud_role_assignment["resource_key"],
    )

    assert len(retrieved_assignments) == 1
    assert retrieved_assignments[0]["actor_key"] == crud_role_assignment["actor_key"]
    assert (
        retrieved_assignments[0]["resource_key"] == crud_role_assignment["resource_key"]
    )
    assert retrieved_assignments[0]["role_id"] == crud_role_assignment["role_id"]


def test_crud_delete_role_assignment(context, monkeypatch):
    """
    Test for delete_role_assignment method
    """
    assert RoleAssignmentsTestContext.crud_role_assignment is not None
    crud_role_assignment = RoleAssignmentsTestContext.crud_role_assignment

    monkeypatch.setattr(
        role_assignments,
        "_verify_actor_exists",
        lambda actor_id, actor_type: True,
    )
    monkeypatch.setattr(
        role_assignments,
        "_verify_resource_exists",
        lambda resource_id, resource_type: True,
    )

    # Perform the delete_role_assignment operation
    role_assignments.delete_role_assignment(crud_role_assignment)

    # Verify that the role assignment has been deleted
    retrieved_assignments = role_assignments.list_role_assignments(
        actor_key=crud_role_assignment["actor_key"],
        resource_key=crud_role_assignment["resource_key"],
    )

    assert len(retrieved_assignments) == 0
