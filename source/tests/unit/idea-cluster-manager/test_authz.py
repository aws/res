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

"""
Test Cases for RoleAssignmentsService
"""

from typing import Optional

import pytest
from _pytest.monkeypatch import MonkeyPatch
from ideasdk.utils import Utils

from ideadatamodel import (
    CreateRoleRequest,
    CreateRoleResponse,
    DeleteRoleAssignmentErrorResponse,
    DeleteRoleAssignmentRequest,
    DeleteRoleAssignmentSuccessResponse,
    DeleteRoleRequest,
    DeleteRoleResponse,
    GetRoleRequest,
    GetRoleResponse,
    ListRoleAssignmentsRequest,
    ListRolesRequest,
    ListRolesResponse,
    ProjectPermissions,
    PutRoleAssignmentErrorResponse,
    PutRoleAssignmentRequest,
    PutRoleAssignmentSuccessResponse,
    Role,
    UpdateRoleRequest,
    UpdateRoleResponse,
    VDIPermissions,
    constants,
    errorcodes,
    exceptions,
)


class RolesTestContext:
    crud_role: Optional[Role]


def generate_random_id(prefix: str) -> str:
    return f"test-{prefix}-{Utils.short_uuid()}".lower()[
        : constants.AD_SAM_ACCOUNT_NAME_MAX_LENGTH
    ]


@pytest.fixture(scope="module")
def monkey_session(request):
    mp = MonkeyPatch()
    yield mp
    mp.undo()


# ========== Unit tests for Role Assignments ==========


def test_put_role_assignment(context, monkey_session):
    """
    Test for put_role_assignment method
    """
    assert context.role_assignments is not None

    # Define a PutRoleAssignmentRequest
    request = PutRoleAssignmentRequest(
        actor_id=generate_random_id("actor"),
        resource_id=generate_random_id("project"),
        actor_type="user",
        resource_type="project",
        role_id=constants.PROJECT_MEMBER_ROLE_ID,
        request_id=generate_random_id("req"),
    )

    monkey_session.setattr(
        context.role_assignments,
        "verify_actor_exists",
        lambda actor_id, actor_type: True,
    )
    monkey_session.setattr(
        context.role_assignments,
        "verify_resource_exists",
        lambda resource_id, resource_type: True,
    )

    # Perform the put_role_assignment operation
    response = context.role_assignments.put_role_assignment(request)

    # Check the success response
    assert isinstance(response, PutRoleAssignmentSuccessResponse)
    assert response.request_id == request.request_id
    assert response.status_code in {"200", "201"}

    # Retrieve the role assignment to verify the update
    retrieved_assignment = context.role_assignments.list_role_assignments(
        ListRoleAssignmentsRequest(
            actor_key=f"{request.actor_id}:{request.actor_type}",
            resource_key=f"{request.resource_id}:{request.resource_type}",
        )
    ).items[0]

    # Check that the role assignment exists and has been updated
    assert retrieved_assignment is not None
    assert retrieved_assignment.role_id == request.role_id
    assert retrieved_assignment.actor_id == request.actor_id
    assert retrieved_assignment.actor_type == request.actor_type
    assert retrieved_assignment.resource_type == request.resource_type
    assert retrieved_assignment.resource_id == request.resource_id


def test_put_role_assignment_invalid_params(context, monkey_session):
    """
    Test for put_role_assignment method with invalid parameters
    """
    assert context.role_assignments is not None

    def verify_invalid_scenario(
        invalid_request: PutRoleAssignmentRequest, error_message: str
    ):
        # Perform the put_role_assignment operation with invalid parameters
        response = context.role_assignments.put_role_assignment(invalid_request)

        # Check the error response
        assert isinstance(response, PutRoleAssignmentErrorResponse)
        assert response.request_id == invalid_request.request_id
        assert response.error_code == errorcodes.INVALID_PARAMS
        assert error_message in response.message

    invalid_req = PutRoleAssignmentRequest(
        actor_id=generate_random_id("actor"),
        resource_id=generate_random_id("project"),
        actor_type="blah",  # invalid
        resource_type="project",
        role_id=constants.PROJECT_MEMBER_ROLE_ID,
        request_id=generate_random_id("req"),
    )
    monkey_session.setattr(
        context.role_assignments,
        "verify_actor_exists",
        lambda actor_id, actor_type: True,
    )
    monkey_session.setattr(
        context.role_assignments,
        "verify_resource_exists",
        lambda resource_id, resource_type: True,
    )
    verify_invalid_scenario(invalid_req, constants.INVALID_ROLE_ASSIGNMENT_ACTOR_TYPE)

    invalid_req = PutRoleAssignmentRequest(
        actor_id=generate_random_id("actor"),
        resource_id=generate_random_id("project"),
        actor_type="user",
        resource_type="blah",  # invalid
        role_id=constants.PROJECT_MEMBER_ROLE_ID,
        request_id=generate_random_id("req"),
    )
    verify_invalid_scenario(
        invalid_req, constants.INVALID_ROLE_ASSIGNMENT_RESOURCE_TYPE
    )

    invalid_req = PutRoleAssignmentRequest(
        actor_id=generate_random_id("actor"),
        resource_id=generate_random_id("project")
        + "\u2460\u2461\u2462\u2463",  # invalid
        actor_type="user",
        resource_type="project",
        role_id=constants.PROJECT_MEMBER_ROLE_ID,
        request_id=generate_random_id("req"),
    )

    verify_invalid_scenario(
        invalid_req, constants.ROLE_ASSIGNMENT_RESOURCE_ID_ERROR_MESSAGE
    )

    invalid_req = PutRoleAssignmentRequest(
        actor_id=generate_random_id("actor") + "\u2460\u2461\u2462\u2463",  # invalid
        resource_id=generate_random_id("project"),
        actor_type="user",
        resource_type="project",
        role_id=constants.PROJECT_MEMBER_ROLE_ID,
        request_id=generate_random_id("req"),
    )

    verify_invalid_scenario(
        invalid_req, constants.ROLE_ASSIGNMENT_ACTOR_ID_ERROR_MESSAGE
    )


def test_list_role_assignments_invalid_params(context, monkey_session):
    """
    Test for list_role_assignments method with invalid parameters
    """
    assert context.role_assignments is not None

    def verify_invalid_scenario(
        invalid_request: ListRoleAssignmentsRequest, error_message: str
    ):
        # Perform the list_role_assignments operation with invalid parameters
        with pytest.raises(exceptions.SocaException) as exc_info:
            context.role_assignments.list_role_assignments(
                ListRoleAssignmentsRequest(
                    actor_key=invalid_request.actor_key,
                    resource_key=invalid_request.resource_key,
                )
            )
        assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
        assert error_message in exc_info.value.message

    invalid_req = ListRoleAssignmentsRequest(
        actor_key=f"{generate_random_id('actor')}:blah",  # invalid
        resource_key=f"{generate_random_id('project')}:project",
    )
    verify_invalid_scenario(
        invalid_req, constants.ROLE_ASSIGNMENT_ACTOR_KEY_ERROR_MESSAGE
    )

    invalid_req = ListRoleAssignmentsRequest(
        actor_key=f"{generate_random_id('actor')}:user",
        resource_key=f"{generate_random_id('project')}:blah",  # invalid
    )
    verify_invalid_scenario(
        invalid_req, constants.ROLE_ASSIGNMENT_RESOURCE_KEY_ERROR_MESSAGE
    )

    invalid_req = ListRoleAssignmentsRequest()
    verify_invalid_scenario(invalid_req, "Either actor_key or resource_key is required")

    invalid_req = ListRoleAssignmentsRequest(
        actor_key=f"\u2460\u2461\u2462\u2463:user",  # invalid
        resource_key=f"{generate_random_id('project')}:project",
    )
    verify_invalid_scenario(
        invalid_req, constants.ROLE_ASSIGNMENT_ACTOR_KEY_ERROR_MESSAGE
    )

    invalid_req = ListRoleAssignmentsRequest(
        actor_key=f"{generate_random_id('actor')}:user",
        resource_key=f"\u2460\u2461\u2462\u2463:project",  # invalid
    )
    verify_invalid_scenario(
        invalid_req, constants.ROLE_ASSIGNMENT_RESOURCE_KEY_ERROR_MESSAGE
    )


def test_delete_role_assignment(context, monkey_session):
    """
    Test for delete_role_assignment method
    """
    assert context.role_assignments is not None

    # Define a DeleteRoleAssignmentRequest
    request = DeleteRoleAssignmentRequest(
        actor_id=generate_random_id("actor"),
        resource_id=generate_random_id("project"),
        actor_type="group",
        resource_type="project",
        request_id=generate_random_id("req"),
    )

    monkey_session.setattr(
        context.role_assignments,
        "verify_actor_exists",
        lambda actor_id, actor_type: True,
    )
    monkey_session.setattr(
        context.role_assignments,
        "verify_resource_exists",
        lambda resource_id, resource_type: True,
    )

    # Perform the delete_role_assignment operation
    response = context.role_assignments.delete_role_assignment(request)

    # Check the success response
    assert isinstance(response, DeleteRoleAssignmentSuccessResponse)
    assert response.request_id == request.request_id
    assert response.status_code == "204"

    # Verify that the role assignment has been deleted
    retrieved_assignments = context.role_assignments.list_role_assignments(
        ListRoleAssignmentsRequest(
            actor_key=f"{request.actor_id}:{request.actor_type}",
            resource_key=f"{request.resource_id}:{request.resource_type}",
        )
    ).items

    assert len(retrieved_assignments) == 0


def test_delete_role_assignment_invalid_params(context, monkey_session):
    """
    Test for delete_role_assignment method with invalid parameters
    """
    assert context.role_assignments is not None

    def verify_invalid_scenario(
        invalid_request: DeleteRoleAssignmentRequest, error_message: str
    ):
        # Perform the delete_role_assignment operation with invalid parameters
        response = context.role_assignments.delete_role_assignment(invalid_request)

        # Check the error response
        assert isinstance(response, DeleteRoleAssignmentErrorResponse)
        assert response.request_id == invalid_request.request_id
        assert response.error_code == errorcodes.INVALID_PARAMS
        assert error_message in response.message

    invalid_req = DeleteRoleAssignmentRequest(
        actor_id=generate_random_id("actor"),
        resource_id=generate_random_id("project"),
        actor_type="blah",  # invalid
        resource_type="project",
        request_id=generate_random_id("req"),
    )
    verify_invalid_scenario(invalid_req, constants.INVALID_ROLE_ASSIGNMENT_ACTOR_TYPE)

    invalid_req = DeleteRoleAssignmentRequest(
        actor_id=generate_random_id("actor"),
        resource_id=generate_random_id("project"),
        actor_type="group",
        resource_type="blah",  # invalid
        request_id=generate_random_id("req"),
    )
    verify_invalid_scenario(
        invalid_req, constants.INVALID_ROLE_ASSIGNMENT_RESOURCE_TYPE
    )

    invalid_req = DeleteRoleAssignmentRequest(
        actor_id=generate_random_id("actor") + "\u2460\u2461\u2462\u2463",  # invalid
        resource_id=generate_random_id("project"),
        actor_type="user",
        resource_type="project",
        request_id=generate_random_id("req"),
    )
    verify_invalid_scenario(
        invalid_req, constants.ROLE_ASSIGNMENT_ACTOR_ID_ERROR_MESSAGE
    )

    invalid_req = DeleteRoleAssignmentRequest(
        actor_id=generate_random_id("actor"),
        resource_id=generate_random_id("project")
        + "\u2460\u2461\u2462\u2463",  # invalid
        actor_type="group",
        resource_type="project",
        request_id=generate_random_id("req"),
    )
    verify_invalid_scenario(
        invalid_req, constants.ROLE_ASSIGNMENT_RESOURCE_ID_ERROR_MESSAGE
    )


def test_get_role_assignment(context, monkey_session):
    """
    Test for get_role_assignment method
    """
    assert context.role_assignments is not None

    request = PutRoleAssignmentRequest(
        actor_id=generate_random_id("actor"),
        resource_id=generate_random_id("project"),
        actor_type="user",
        resource_type="project",
        role_id=constants.PROJECT_MEMBER_ROLE_ID,
        request_id=generate_random_id("req"),
    )

    monkey_session.setattr(
        context.role_assignments,
        "verify_actor_exists",
        lambda actor_id, actor_type: True,
    )
    monkey_session.setattr(
        context.role_assignments,
        "verify_resource_exists",
        lambda resource_id, resource_type: True,
    )

    # Perform the put_role_assignment operation
    response = context.role_assignments.put_role_assignment(request)

    # Perform the get_role_assignment operation
    response = context.role_assignments.get_role_assignment(
        f"{request.actor_id}:{request.actor_type}",
        f"{request.resource_id}:{request.resource_type}",
    )

    # Check the success response
    assert response is not None
    assert response.actor_key == f"{request.actor_id}:{request.actor_type}"
    assert response.resource_key == f"{request.resource_id}:{request.resource_type}"
    assert response.role_id == request.role_id


def test_get_role_assignment_invalid_params(context, monkey_session):
    """
    Test for get_role_assignment method with invalid parameters
    """
    assert context.role_assignments is not None

    def verify_invalid_scenario(actor_key: str, resource_key: str, error_message: str):
        with pytest.raises(exceptions.SocaException) as exc_info:
            # Perform the get_role_assignment operation with invalid parameters
            response = context.role_assignments.get_role_assignment(
                actor_key, resource_key
            )
        # Check the error response
        assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
        assert error_message in exc_info.value.message

    verify_invalid_scenario(
        actor_key=f"{generate_random_id('user')}:blah",  # invalid
        resource_key=f"{generate_random_id('project')}:project",
        error_message=constants.ROLE_ASSIGNMENT_ACTOR_KEY_ERROR_MESSAGE,
    )

    verify_invalid_scenario(
        actor_key=f"{generate_random_id('user')}:user",
        resource_key=f"{generate_random_id('project')}:blah",  # invalid
        error_message=constants.ROLE_ASSIGNMENT_RESOURCE_KEY_ERROR_MESSAGE,
    )

    verify_invalid_scenario(
        actor_key=f"\u2460\u2461\u2462\u2463:user",  # invalid
        resource_key=f"{generate_random_id('project')}:project",
        error_message=constants.ROLE_ASSIGNMENT_ACTOR_KEY_ERROR_MESSAGE,
    )

    verify_invalid_scenario(
        actor_key=f"{generate_random_id('user')}:user",
        resource_key=f"\u2460\u2461\u2462\u2463:project",  # invalid
        error_message=constants.ROLE_ASSIGNMENT_RESOURCE_KEY_ERROR_MESSAGE,
    )


# ========== Unit tests for Roles ==========


def test_list_roles(context, monkey_session):
    """
    Test for list_roles method
    """
    assert context.roles is not None

    valid_req = ListRolesRequest()

    response = context.roles.list_roles(valid_req)

    # Check the response
    assert isinstance(response, ListRolesResponse)
    assert hasattr(response, "items")


def test_get_role(context, monkey_session):
    """
    Test for get_role method
    """
    assert context.roles is not None

    expected_role = {
        "role_id": constants.PROJECT_OWNER_ROLE_ID,
        "projects": {
            "update_status": False,
            "update_personnel": True,
        },
        "description": "Project Owner Role",
        "name": "Project Owner",
    }

    monkey_session.setattr(
        context.roles.roles_dao,
        "get_role",
        lambda role_id: expected_role,
    )

    valid_req = GetRoleRequest(role_id=constants.PROJECT_OWNER_ROLE_ID)

    response = context.roles.get_role(valid_req)

    # Check the response
    assert isinstance(response, GetRoleResponse)
    assert hasattr(response, "role")
    assert response.role == context.roles.roles_dao.convert_from_db(expected_role)


def test_get_role_invalid_params(context, monkey_session):
    """
    Test for get_role method with invalid params
    """
    assert context.roles is not None

    def verify_invalid_scenario(invalid_request: GetRoleRequest, error_message: str):
        with pytest.raises(exceptions.SocaException) as exc_info:
            context.roles.get_role(GetRoleRequest(role_id=invalid_request.role_id))
        assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
        assert error_message in exc_info.value.message

    verify_invalid_scenario(
        invalid_request=GetRoleRequest(),
        error_message="role_id is required",
    )

    verify_invalid_scenario(
        invalid_request=GetRoleRequest(role_id="\u2460\u2461\u2462\u2463"),
        error_message=constants.ROLE_ID_ERROR_MESSAGE,
    )


def test_get_role_not_found(context, monkey_session):
    """
    Test for get_role method for role not found
    """
    assert context.roles is not None

    monkey_session.setattr(
        context.roles.roles_dao,
        "get_role",
        lambda role_id: None,
    )

    with pytest.raises(exceptions.SocaException) as exc_info:
        context.roles.get_role(GetRoleRequest(role_id=constants.PROJECT_OWNER_ROLE_ID))
    assert exc_info.value.error_code == errorcodes.ROLE_NOT_FOUND
    assert "role not found" in exc_info.value.message


def test_create_role_success(context, monkey_session):
    """
    Test for create_role succeeds as expected
    """
    assert context.roles is not None

    role = Role(
        role_id="samplerole",
        name="Sample Role",
        description="Sample Role Description",
        projects={"update_personnel": True},
        vdis={"create_sessions": True, "create_terminate_others_sessions": False},
    )

    result = context.roles.create_role(CreateRoleRequest(role=role))

    # Check the response
    assert isinstance(result, CreateRoleResponse)
    assert hasattr(result, "role")
    assert result.role.role_id == role.role_id
    assert result.role.name == role.name
    assert result.role.description == role.description
    assert result.role.projects == role.projects
    assert result.role.vdis == role.vdis
    assert result.role.created_on is not None
    assert result.role.updated_on is not None


def test_create_role_invalid_params(context, monkey_session):
    """
    Test create_role fails for invalid parameter values
    """
    assert context.roles is not None

    # missing request
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.roles.create_role(None)
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS

    # missing role id
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.roles.create_role(CreateRoleRequest(role=Role(name="sample role")))
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS

    # missing role name
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.roles.create_role(CreateRoleRequest(role=Role(role_id="samplerole")))
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS

    # invalid role id
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.roles.create_role(
            CreateRoleRequest(
                role=Role(role_id="contains-!nvalid-char@acters", name="sample role")
            )
        )
    assert exc_info.value.message == constants.ROLE_ID_ERROR_MESSAGE

    # invalid role name
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.roles.create_role(
            CreateRoleRequest(
                role=Role(role_id="samplerole", name="contains-!nvalid-char@acters")
            )
        )
    assert exc_info.value.message == constants.ROLE_NAME_ERROR_MESSAGE

    # invalid role desc
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.roles.create_role(
            CreateRoleRequest(
                role=Role(
                    role_id="samplerole",
                    name="sample role",
                    description="contains-!nvalid-char@acters",
                )
            )
        )
    assert exc_info.value.message == constants.ROLE_DESC_ERROR_MESSAGE


def test_create_role_fails_duplicate_record(context, monkey_session):
    """
    Test create_role fails when duplicate record exists
    """
    assert context.roles is not None

    role = Role(
        role_id="samplerole",
        name="Sample Role",
        description="Sample Role Description",
        projects={"update_personnel": True},
        vdis={"create_sessions": True, "create_terminate_others_sessions": False},
    )

    monkey_session.setattr(
        context.roles.roles_dao,
        "get_role",
        lambda role_id: context.roles.roles_dao.convert_to_db(role),
    )

    with pytest.raises(exceptions.SocaException) as exc_info:
        context.roles.create_role(CreateRoleRequest(role=role))

    assert exc_info.value.error_code == errorcodes.AUTH_USER_ALREADY_EXISTS
    assert f"{role.role_id} already exists" in exc_info.value.message


def test_delete_role_succeeds(context):
    """
    Test delete_role succeeds as expected
    """
    assert context.roles is not None

    role = Role(
        role_id="test_delete_role",
        name="Test Delete Role",
        description="Sample Role Description",
        projects={"update_personnel": True},
        vdis={"create_sessions": True, "create_terminate_others_sessions": False},
    )

    result = context.roles.delete_role(DeleteRoleRequest(role_id=role.role_id))

    # Check the response
    assert isinstance(result, DeleteRoleResponse)


def test_delete_role_fails_role_id_not_provided(context):
    """
    Test delete_role fails when role id is not provided
    """
    assert context.roles is not None

    with pytest.raises(exceptions.SocaException) as exc_info:
        context.roles.delete_role(DeleteRoleRequest())

    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "role_id is required" in exc_info.value.message


def test_delete_role_fails_invalid_params(context):
    """
    Test delete_role fails when role id contains invalid characters
    """
    assert context.roles is not None

    with pytest.raises(exceptions.SocaException) as exc_info:
        context.roles.delete_role(
            DeleteRoleRequest(role_id="contains-!nvalid-char@acters")
        )

    assert exc_info.value.message == constants.ROLE_ID_ERROR_MESSAGE


def test_delete_role_fails_projects_exist(context, monkey_session):
    """
    Test delete_role fails when role is being used by projects
    """
    assert context.roles is not None

    monkey_session.setattr(
        context.roles.role_assignments_dao,
        "list_projects_for_role",
        lambda role_id: ["project1", "project2"],
    )

    role = Role(
        role_id="role_with_projects",
        name="Test Delete Role Fails Projects Exist",
        description="Sample Role Description",
        projects={"update_personnel": True},
        vdis={"create_sessions": True, "create_terminate_others_sessions": False},
    )

    with pytest.raises(exceptions.SocaException) as exc_info:
        context.roles.delete_role(DeleteRoleRequest(role_id=role.role_id))

    assert exc_info.value.error_code == errorcodes.GENERAL_ERROR
    assert f"role {role.role_id} is used by projects" in exc_info.value.message


def test_update_role_succeeds(context, monkey_session):
    """
    Test update_role succeeds as expected
    """
    assert context.roles is not None

    existing_role = {
        "role_id": "samplerole",
        "name": "Sample Role",
        "description": "Sample Role Description",
        "projects": {"update_personnel": True, "update_status": True},
        "vdis": {"create_sessions": True, "create_terminate_others_sessions": False},
    }

    monkey_session.setattr(
        context.roles.roles_dao,
        "get_role",
        lambda role_id: existing_role,
    )

    role_to_update = Role(
        role_id="samplerole",
        name="Role Name updated",
        projects=ProjectPermissions(update_personnel=False, update_status=False),
        vdis=VDIPermissions(
            create_sessions=False, create_terminate_others_sessions=True
        ),
    )

    result = result = context.roles.update_role(UpdateRoleRequest(role=role_to_update))

    expected_role = Role(
        role_id="samplerole",
        name="Role Name updated",
        description="Sample Role Description",
        projects=ProjectPermissions(update_personnel=False, update_status=False),
        vdis=VDIPermissions(
            create_sessions=False, create_terminate_others_sessions=True
        ),
    )

    # Check the response
    assert isinstance(result, UpdateRoleResponse)
    assert result.role.role_id == expected_role.role_id
    assert result.role.name == expected_role.name
    assert result.role.description == expected_role.description
    assert result.role.projects == expected_role.projects
    assert result.role.vdis == expected_role.vdis


def test_update_role_fails_role_id_not_provided(context):
    """
    Test update_role fails when role id is not provided
    """
    assert context.roles is not None

    with pytest.raises(exceptions.SocaException) as exc_info:
        context.roles.update_role(UpdateRoleRequest(role=Role(name="sample role")))
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS


def test_update_role_fails_invalid_params(context):
    """
    Test update_role fails when role id contains invalid characters
    """
    assert context.roles is not None

    with pytest.raises(exceptions.SocaException) as exc_info:
        context.roles.update_role(
            UpdateRoleRequest(
                role=Role(role_id="contains-!nvalid-char@acters", name="sample role")
            )
        )
    assert exc_info.value.message == constants.ROLE_ID_ERROR_MESSAGE
