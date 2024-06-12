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


from ideadatamodel import exceptions, constants
from ideadatamodel import (
    BatchPutRoleAssignmentRequest,
    BatchPutRoleAssignmentResponse,
    PutRoleAssignmentRequest,
    PutRoleAssignmentSuccessResponse,
    PutRoleAssignmentErrorResponse,
    BatchDeleteRoleAssignmentRequest,
    BatchDeleteRoleAssignmentResponse,
    DeleteRoleAssignmentRequest,
    DeleteRoleAssignmentSuccessResponse,
    DeleteRoleAssignmentErrorResponse,
    ListRoleAssignmentsRequest,
    ListRoleAssignmentsResponse,
    RoleAssignment,
    GetProjectRequest,
    User
)
from ideasdk.utils import Utils, ApiUtils
from ideasdk.context import SocaContext

from ideaclustermanager.app.authz.db.role_assignments_dao import RoleAssignmentsDAO

from typing import Union, Optional, List


class RoleAssignmentsService:

    def __init__(self, context: SocaContext):
        self.context = context
        self.logger = context.logger('role-assignments-service')

        self.role_assignments_dao = RoleAssignmentsDAO(
            context=context
        )
        self.role_assignments_dao.initialize()

    def put_role_assignments(self, request: BatchPutRoleAssignmentRequest) -> BatchPutRoleAssignmentResponse:
        success = []
        error = []

        for item in request.items:
            response = self.put_role_assignment(item)
            if hasattr(response,'error_code') and response.error_code:
                error.append(response)
            else:
                success.append(response)

        return BatchPutRoleAssignmentResponse(
            items=success,
            errors=error
        )

    def put_role_assignment(self, request: PutRoleAssignmentRequest) -> Union[PutRoleAssignmentSuccessResponse, PutRoleAssignmentErrorResponse]:
        try:
            if Utils.is_empty(request):
                raise exceptions.invalid_params('request is required')
            if Utils.is_empty(request.actor_id):
                raise exceptions.invalid_params('actor_id is required')
            if Utils.is_empty(request.resource_id):
                raise exceptions.invalid_params('resource_id is required')
            if Utils.is_empty(request.actor_type):
                raise exceptions.invalid_params('actor_type is required')
            if Utils.is_empty(request.resource_type):
                raise exceptions.invalid_params('resource_type is required')
            if Utils.is_empty(request.role_id):
                raise exceptions.invalid_params('role_id is required')
            if Utils.is_empty(request.request_id):
                raise exceptions.invalid_params('request_id is required')

            if request.actor_type not in constants.VALID_ROLE_ASSIGNMENT_ACTOR_TYPES:
                raise exceptions.invalid_params(constants.INVALID_ROLE_ASSIGNMENT_ACTOR_TYPE)
            if request.resource_type not in constants.VALID_ROLE_ASSIGNMENT_RESOURCE_TYPES:
                raise exceptions.invalid_params(constants.INVALID_ROLE_ASSIGNMENT_RESOURCE_TYPE)
            if request.role_id not in constants.VALID_ROLE_ASSIGNMENT_ROLE_IDS:
                raise exceptions.invalid_params('role_id value is not recognized')
            
            ApiUtils.validate_input(request.actor_id, constants.ROLE_ASSIGNMENT_ACTOR_ID_REGEX, constants.ROLE_ASSIGNMENT_ACTOR_ID_ERROR_MESSAGE)
            ApiUtils.validate_input(request.resource_id, constants.ROLE_ASSIGNMENT_RESOURCE_ID_REGEX, constants.ROLE_ASSIGNMENT_RESOURCE_ID_ERROR_MESSAGE)

            self.verify_actor_exists(request.actor_id, request.actor_type)
            self.verify_resource_exists(request.resource_id, request.resource_type)

            self.logger.debug(f'put_role_assignment() called for actor {request.actor_type}:{request.actor_id} and resource {request.resource_type}:{request.resource_id} and role {request.role_id}')

            # Construct the PK/SK values as stored in DDB
            actor_key = f'{request.actor_id}:{request.actor_type}'
            resource_key = f'{request.resource_id}:{request.resource_type}'

            existing = self.get_role_assignment(actor_key, resource_key)

            self.role_assignments_dao.put_role_assignment(actor_key, resource_key, request.role_id)

            return PutRoleAssignmentSuccessResponse(
                request_id = request.request_id,
                status_code = 200 if existing else 201
            )

        except exceptions.SocaException as e:

            return PutRoleAssignmentErrorResponse(
                request_id=request.request_id,
                error_code=e.error_code,
                message=e.message
            )
    
    def verify_actor_exists(self, actor_id: str, actor_type: str):
        if Utils.is_empty(actor_id):
            raise exceptions.invalid_params('actor_id is required')
        if Utils.is_empty(actor_type):
            raise exceptions.invalid_params('actor_type is required')

        if actor_type == 'user':
            self.context.accounts.get_user(actor_id)
        elif actor_type == 'group':
            self.context.accounts.get_group(actor_id)
    
    def verify_resource_exists(self, resource_id: str, resource_type: str):
        if Utils.is_empty(resource_id):
            raise exceptions.invalid_params('resource_id is required')
        if Utils.is_empty(resource_type):
            raise exceptions.invalid_params('resource_type is required')

        if resource_type == 'project':
            self.context.projects.get_project(GetProjectRequest(project_id=resource_id))

    def delete_role_assignments(self, request: BatchDeleteRoleAssignmentRequest) -> BatchDeleteRoleAssignmentResponse:
        success = []
        error = []

        for item in request.items:
            response = self.delete_role_assignment(item)
            if hasattr(response,'error_code') and response.error_code:
                error.append(response)
            else:
                success.append(response)

        return BatchDeleteRoleAssignmentResponse(
            items=success,
            errors=error
        )

    def delete_role_assignment(self, request: DeleteRoleAssignmentRequest) -> Union[DeleteRoleAssignmentSuccessResponse, DeleteRoleAssignmentErrorResponse]:
        try:
            if Utils.is_empty(request):
                raise exceptions.invalid_params('request is required')
            if Utils.is_empty(request.actor_id):
                raise exceptions.invalid_params('actor_id is required')
            if Utils.is_empty(request.resource_id):
                raise exceptions.invalid_params('resource_id is required')
            if Utils.is_empty(request.actor_type):
                raise exceptions.invalid_params('actor_type is required')
            if Utils.is_empty(request.resource_type):
                raise exceptions.invalid_params('resource_type is required')
            if Utils.is_empty(request.request_id):
                raise exceptions.invalid_params('request_id is required')

            if request.actor_type not in constants.VALID_ROLE_ASSIGNMENT_ACTOR_TYPES:
                raise exceptions.invalid_params(constants.INVALID_ROLE_ASSIGNMENT_ACTOR_TYPE)
            if request.resource_type not in constants.VALID_ROLE_ASSIGNMENT_RESOURCE_TYPES:
                raise exceptions.invalid_params(constants.INVALID_ROLE_ASSIGNMENT_RESOURCE_TYPE)
            
            ApiUtils.validate_input(request.actor_id, constants.ROLE_ASSIGNMENT_ACTOR_ID_REGEX, constants.ROLE_ASSIGNMENT_ACTOR_ID_ERROR_MESSAGE)
            ApiUtils.validate_input(request.resource_id, constants.ROLE_ASSIGNMENT_RESOURCE_ID_REGEX, constants.ROLE_ASSIGNMENT_RESOURCE_ID_ERROR_MESSAGE)

            self.verify_actor_exists(request.actor_id, request.actor_type)
            self.verify_resource_exists(request.resource_id, request.resource_type)

            self.logger.debug(f'delete_role_assignment() called for actor {request.actor_type}:{request.actor_id} and resource {request.resource_type}:{request.resource_id}')

            # Construct the PK/SK values as stored in DDB
            actor_key = f'{request.actor_id}:{request.actor_type}'
            resource_key = f'{request.resource_id}:{request.resource_type}'

            self.role_assignments_dao.delete_role_assignment(actor_key, resource_key)

            return DeleteRoleAssignmentSuccessResponse(
                request_id = request.request_id,
                status_code = 204
            )

        except exceptions.SocaException as e:

            return DeleteRoleAssignmentErrorResponse(
                request_id=request.request_id,
                error_code=e.error_code,
                message=e.message
            )

    # Checks if there is a specific record of the given actor-resource with the given role
    def is_actor_in_project(self, actor_id: str, actor_type: str, resource_id: str, role_id: str) -> bool:
        actor_key=f"{actor_id}:{actor_type}"
        resource_key=f"{resource_id}:project"
        role_assignment = self.get_role_assignment(actor_key, resource_key)

        # Check role equality if role ID was provided
        return role_assignment and role_assignment.role_id == role_id
    
    # Checks if there is a specific record of the given actor-resource with the project owner role
    def is_actor_any_project_owner(self, actor_id: str, actor_type: str) -> bool:
        actor_key=f"{actor_id}:{actor_type}"
        self.logger.debug(f'is_actor_any_project_owner() - actor_key: {actor_key}')
        role_assignments = self.list_role_assignments(ListRoleAssignmentsRequest(actor_key=actor_key)).items

        # Check role equality if role ID was provided
        return any(role_assignment.role_id == constants.PROJECT_OWNER_ROLE_ID for role_assignment in role_assignments)

    def get_role_assignment(self, actor_key: str, resource_key: str) -> Optional[RoleAssignment]:
        # Perform validations on the incoming actor/resource types
        if Utils.is_empty(actor_key) or Utils.is_empty(resource_key):
            raise exceptions.invalid_params('Either actor_key or resource_key is not provided')

        if not Utils.is_empty(actor_key):
            ApiUtils.validate_input(actor_key, constants.ROLE_ASSIGNMENT_ACTOR_KEY_REGEX, constants.ROLE_ASSIGNMENT_ACTOR_KEY_ERROR_MESSAGE)
        if not Utils.is_empty(resource_key):
            ApiUtils.validate_input(resource_key, constants.ROLE_ASSIGNMENT_RESOURCE_KEY_REGEX, constants.ROLE_ASSIGNMENT_RESOURCE_KEY_ERROR_MESSAGE)

        actor_key_split = actor_key.split(':')
        resource_key_split = resource_key.split(':')

        self.verify_actor_exists(actor_key_split[0], actor_key_split[1])
        self.verify_resource_exists(resource_key_split[0], resource_key_split[1])

        self.logger.debug(f'get_role_assignments() - actor: {actor_key} resource: {resource_key}')
        return self.role_assignments_dao.get_role_assignment(actor_key, resource_key)

    def list_role_assignments(self, request: ListRoleAssignmentsRequest) -> ListRoleAssignmentsResponse:
        # Perform validations on the incoming actor/resource types
        if Utils.is_empty(request.actor_key) and Utils.is_empty(request.resource_key):
            raise exceptions.invalid_params('Either actor_key or resource_key is required')
        
        if not Utils.is_empty(request.actor_key):
            ApiUtils.validate_input(request.actor_key, constants.ROLE_ASSIGNMENT_ACTOR_KEY_REGEX, constants.ROLE_ASSIGNMENT_ACTOR_KEY_ERROR_MESSAGE)
            self.logger.debug(f'list_role_assignments() called for actor {request.actor_key}')
        if not Utils.is_empty(request.resource_key):
            ApiUtils.validate_input(request.resource_key, constants.ROLE_ASSIGNMENT_RESOURCE_KEY_REGEX, constants.ROLE_ASSIGNMENT_RESOURCE_KEY_ERROR_MESSAGE)
            self.logger.debug(f'list_role_assignments() called for resource {request.resource_key}')

            resource_type = request.resource_key.split(':')[1] if len(request.resource_key.split(':')) == 2 else ""
            if resource_type not in constants.VALID_ROLE_ASSIGNMENT_RESOURCE_TYPES:
                raise exceptions.invalid_params(constants.INVALID_ROLE_ASSIGNMENT_RESOURCE_TYPE)
        
        return self.role_assignments_dao.list_role_assignments(request)

    ### Helper methods

    # Checks if the given user is assigned as a project owner for the given project directly or via any of their groups
    def is_user_project_owner(self, user: User, project_id: str) -> bool:
        if user.enabled and (
            self.is_actor_in_project(actor_id=user.username, actor_type='user', resource_id=project_id, role_id=constants.PROJECT_OWNER_ROLE_ID) or 
            any(self.is_actor_in_project(actor_id=group, actor_type='group', resource_id=project_id, role_id=constants.PROJECT_OWNER_ROLE_ID) for group in user.additional_groups)
            ):
            return True
        
        return False

    # Checks if the given user is assigned as a project owner for ANY project directly or via any of their groups
    def is_user_any_project_owner(self, user: User) -> bool:
        self.logger.debug(f'is_user_any_project_owner() - username: {user.username}')
        if user.enabled and (
            self.is_actor_any_project_owner(actor_id=user.username, actor_type='user') or 
            any(self.is_actor_any_project_owner(actor_id=group, actor_type='group') for group in user.additional_groups)
            ):
            return True
        
        return False
    
    # Checks if the given user is assigned as a project owner for ALL given project directly or via any of their groups
    def is_user_project_owner_for_all_projects(self, user: User, project_ids: List[str]) -> bool:
        return all(self.is_user_project_owner(user=user, project_id=project_id) for project_id in project_ids)