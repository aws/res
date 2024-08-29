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
    ListRolesRequest,
    RoleAssignment,
    GetProjectRequest,
    User
)
from ideasdk.utils import Utils, ApiUtils
from ideasdk.context import SocaContext

from ideaclustermanager.app.authz.db.roles_dao import RolesDAO
from ideaclustermanager.app.authz.db.role_assignments_dao import RoleAssignmentsDAO

from typing import Set, Union, Optional, List


class RoleAssignmentsService:

    def __init__(self, context: SocaContext):
        self.context = context
        self.logger = context.logger('role-assignments-service')

        self.role_assignments_dao = RoleAssignmentsDAO(
            context=context
        )
        self.roles_dao = RolesDAO(
            context=context
        )
        self.role_assignments_dao.initialize()
        self.roles_dao.initialize()

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
            
            role_ids = [role.role_id for role in self.roles_dao.list_roles(False, "", []).listing]
            if request.role_id not in role_ids:
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
            
        role_assignments = []
        
        role_assignments = self.role_assignments_dao.list_role_assignments(actor_key = request.actor_key if request.actor_key is not None else "", 
                                                                           resource_key = request.resource_key if request.resource_key is not None else "")

        return ListRoleAssignmentsResponse(
            items=role_assignments
        )

    ### Helper methods

    # Checks if the given user has any of the given permissions for any project directly or via any of their groups
    def check_permissions_in_any_role(self, user: User, permissions: List[str]) -> bool:
        self.logger.debug(f'Checking if user {user.username} has any of these permissions {permissions} in any of their roles')

        if not user.enabled: return False
        
        # We maintain a set for when we have to go over roles assigned through the user's groups
        roles_seen = set()

        def check_permission_in_roles(roles_to_check: Set[str], permissions: List[str]) -> bool:
            for role_id in roles_to_check:
                if role_id not in roles_seen:
                    roles_seen.add(role_id)
                    db_role = self.roles_dao.get_role(role_id=role_id)
                    if db_role is not None:
                        role = Utils.flatten_dict(db_role)
                        
                        # We try to short-circuit the process if we find that the user has one of these permissions
                        for permission in permissions:
                            if Utils.get_value_as_bool(key=permission, obj=role, default=False): return True
            return False

        # First get all role assignments associated directly to this user
        roles_to_check = set()

        user_role_assignments = self.list_role_assignments(ListRoleAssignmentsRequest(actor_key=f"{user.username}:user"))
        for user_role_assignment in user_role_assignments.items:
            roles_to_check.add(user_role_assignment.role_id)
        
        if check_permission_in_roles(roles_to_check=roles_to_check, permissions=permissions): return True
        
        # reset the role IDs set to get role assignments via groups
        roles_to_check = set()

        for group in user.additional_groups:
            group_role_assignments = self.list_role_assignments(ListRoleAssignmentsRequest(actor_key=f"{group}:group"))
            for group_role_assignment in group_role_assignments.items:
                roles_to_check.add(group_role_assignment.role_id)

        if check_permission_in_roles(roles_to_check=roles_to_check, permissions=permissions): return True

        return False