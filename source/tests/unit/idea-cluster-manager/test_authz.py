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
from ideaclustermanager import AppContext
from ideasdk.utils import Utils

from ideadatamodel import (
    BatchDeleteRoleAssignmentRequest,
    BatchDeleteRoleAssignmentResponse,
    BatchPutRoleAssignmentRequest,
    BatchPutRoleAssignmentResponse,
    DeleteRoleAssignmentErrorResponse,
    DeleteRoleAssignmentRequest,
    DeleteRoleAssignmentSuccessResponse,
    ListRoleAssignmentsRequest,
    ListRoleAssignmentsResponse,
    PutRoleAssignmentErrorResponse,
    PutRoleAssignmentRequest,
    PutRoleAssignmentSuccessResponse,
    RoleAssignment,
    SocaAnyPayload,
    SocaKeyValue,
    User,
    constants,
    errorcodes,
    exceptions,
)


def generate_random_id(prefix: str) -> str:
    return f"test-{prefix}-{Utils.short_uuid()}".lower()[
        : constants.AD_SAM_ACCOUNT_NAME_MAX_LENGTH
    ]


class RoleAssignmentsTestContext:
    crud_role_assignment: Optional[RoleAssignment]


@pytest.fixture(scope="module")
def monkey_session(request):
    mp = MonkeyPatch()
    yield mp
    mp.undo()


def test_put_role_assignment(context, monkey_session):
    """
    Test for put_role_assignment method
    """
    assert context.authz is not None

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
        context.authz, "verify_actor_exists", lambda actor_id, actor_type: True
    )
    monkey_session.setattr(
        context.authz, "verify_resource_exists", lambda resource_id, resource_type: True
    )

    # Perform the put_role_assignment operation
    response = context.authz.put_role_assignment(request)

    # Check the success response
    assert isinstance(response, PutRoleAssignmentSuccessResponse)
    assert response.request_id == request.request_id
    assert response.status_code in {"200", "201"}

    # Retrieve the role assignment to verify the update
    retrieved_assignment = context.authz.list_role_assignments(
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
    assert context.authz is not None

    def verify_invalid_scenario(
        invalid_request: PutRoleAssignmentRequest, error_message: str
    ):
        # Perform the put_role_assignment operation with invalid parameters
        response = context.authz.put_role_assignment(invalid_request)

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
        context.authz, "verify_actor_exists", lambda actor_id, actor_type: True
    )
    monkey_session.setattr(
        context.authz, "verify_resource_exists", lambda resource_id, resource_type: True
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
    assert context.authz is not None

    def verify_invalid_scenario(
        invalid_request: ListRoleAssignmentsRequest, error_message: str
    ):
        # Perform the list_role_assignments operation with invalid parameters
        with pytest.raises(exceptions.SocaException) as exc_info:
            context.authz.list_role_assignments(
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
    assert context.authz is not None

    # Define a DeleteRoleAssignmentRequest
    request = DeleteRoleAssignmentRequest(
        actor_id=generate_random_id("actor"),
        resource_id=generate_random_id("project"),
        actor_type="group",
        resource_type="project",
        request_id=generate_random_id("req"),
    )

    monkey_session.setattr(
        context.authz, "verify_actor_exists", lambda actor_id, actor_type: True
    )
    monkey_session.setattr(
        context.authz, "verify_resource_exists", lambda resource_id, resource_type: True
    )

    # Perform the delete_role_assignment operation
    response = context.authz.delete_role_assignment(request)

    # Check the success response
    assert isinstance(response, DeleteRoleAssignmentSuccessResponse)
    assert response.request_id == request.request_id
    assert response.status_code == "204"

    # Verify that the role assignment has been deleted
    retrieved_assignments = context.authz.list_role_assignments(
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
    assert context.authz is not None

    def verify_invalid_scenario(
        invalid_request: DeleteRoleAssignmentRequest, error_message: str
    ):
        # Perform the delete_role_assignment operation with invalid parameters
        response = context.authz.delete_role_assignment(invalid_request)

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
    assert context.authz is not None

    request = PutRoleAssignmentRequest(
        actor_id=generate_random_id("actor"),
        resource_id=generate_random_id("project"),
        actor_type="user",
        resource_type="project",
        role_id=constants.PROJECT_MEMBER_ROLE_ID,
        request_id=generate_random_id("req"),
    )

    monkey_session.setattr(
        context.authz, "verify_actor_exists", lambda actor_id, actor_type: True
    )
    monkey_session.setattr(
        context.authz, "verify_resource_exists", lambda resource_id, resource_type: True
    )

    # Perform the put_role_assignment operation
    response = context.authz.put_role_assignment(request)

    # Perform the get_role_assignment operation
    response = context.authz.get_role_assignment(
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
    assert context.authz is not None

    def verify_invalid_scenario(actor_key: str, resource_key: str, error_message: str):
        with pytest.raises(exceptions.SocaException) as exc_info:
            # Perform the get_role_assignment operation with invalid parameters
            response = context.authz.get_role_assignment(actor_key, resource_key)
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
