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


from ideadatamodel import exceptions, constants, errorcodes
from ideadatamodel import (
    ListRolesRequest,
    ListRolesResponse,
    GetRoleRequest,
    GetRoleResponse,
    CreateRoleRequest,
    CreateRoleResponse,
    DeleteRoleRequest,
    DeleteRoleResponse,
    UpdateRoleRequest,
    UpdateRoleResponse,
    SocaPaginator,
)
from ideasdk.utils import Utils, ApiUtils
from ideasdk.context import SocaContext

from ideaclustermanager.app.authz.db.roles_dao import RolesDAO
from ideaclustermanager.app.authz.db.role_assignments_dao import RoleAssignmentsDAO

class RolesService:

    def __init__(self, context: SocaContext):
        self.context = context
        self.logger = context.logger('roles-service')

        self.roles_dao = RolesDAO(
            context=context
        )
        self.roles_dao.initialize()

        self.role_assignments_dao = RoleAssignmentsDAO(
            context=context
        )
        self.role_assignments_dao.initialize()

    def create_defaults(self):
        # Create default roles if the do not exist
        project_owner_role = self.roles_dao.get_role(constants.PROJECT_OWNER_ROLE_ID)
        if project_owner_role is None:
            project_owner_role = {
                'role_id': constants.PROJECT_OWNER_ROLE_ID,
                'name': constants.PROJECT_OWNER_ROLE_NAME,
                'description': f"Default Permission Profile for {constants.PROJECT_OWNER_ROLE_NAME}",
                'projects': {
                    'update_personnel': True,
                    'update_status': True
                },
                'vdis': {
                    'create_sessions': True,
                    'create_terminate_others_sessions': True
                },
            }
            self.roles_dao.create_role(project_owner_role)
        
        project_member_role = self.roles_dao.get_role(constants.PROJECT_MEMBER_ROLE_ID)
        if project_member_role is None:
            project_member_role = {
                'role_id': constants.PROJECT_MEMBER_ROLE_ID,
                'name': constants.PROJECT_MEMBER_ROLE_NAME,
                'description': f"Default Permission Profile for {constants.PROJECT_MEMBER_ROLE_NAME}",
                'projects': {
                    'update_personnel': False,
                    'update_status': False
                },
                'vdis': {
                    'create_sessions': True,
                    'create_terminate_others_sessions': False
                },
            }
            self.roles_dao.create_role(project_member_role)
        
    def list_roles(self, request: ListRolesRequest) -> ListRolesResponse:
        response = self.roles_dao.list_roles(request.include_permissions, request.cursor, request.filters)

        return ListRolesResponse(
            items=response.listing,
            paginator=SocaPaginator(
                cursor=response.cursor
            )
        )

    def get_role(self, request: GetRoleRequest) -> GetRoleResponse:
        if Utils.is_empty(request) or Utils.is_empty(request.role_id):
            raise exceptions.invalid_params('role_id is required')

        ApiUtils.validate_input(request.role_id, constants.ROLE_ID_REGEX, constants.ROLE_ID_ERROR_MESSAGE)

        role = self.roles_dao.get_role(request.role_id)

        if role is None:
            raise exceptions.soca_exception(
                error_code=errorcodes.ROLE_NOT_FOUND,
                message=f'role not found for role id: {request.role_id}'
            )

        return GetRoleResponse(role=self.roles_dao.convert_from_db(role))

    def create_role(self, request: CreateRoleRequest) -> CreateRoleResponse:
        """
        Create a new Role
        validate required fields, add the role to DynamoDB 
        :param request: CreateRoleRequest
        :return: the created role in CreateRoleResponse
        """

        if Utils.is_empty(request):
            raise exceptions.invalid_params('request is required')

        role = request.role
        if Utils.is_empty(role):
            raise exceptions.invalid_params('role is required')
        
        if Utils.is_empty(role.role_id):
            raise exceptions.invalid_params('role_id is required')

        if Utils.is_empty(role.name):
            raise exceptions.invalid_params('name is required')

        ApiUtils.validate_input(role.role_id, constants.ROLE_ID_REGEX, constants.ROLE_ID_ERROR_MESSAGE)
        ApiUtils.validate_input(role.name, constants.ROLE_NAME_REGEX, constants.ROLE_NAME_ERROR_MESSAGE)
        ApiUtils.validate_input(role.description, constants.ROLE_DESC_REGEX, constants.ROLE_DESC_ERROR_MESSAGE)

        if role.projects is not None:
            if role.projects.update_personnel is not None and type(role.projects.update_personnel) is not bool:
                raise exceptions.invalid_params('invalid permission type')
            if role.projects.update_status is not None and type(role.projects.update_status) is not bool:
                raise exceptions.invalid_params('invalid permission type')
        
        if role.vdis is not None:
            if role.vdis.create_sessions is not None and type(role.vdis.create_sessions) is not bool:
                raise exceptions.invalid_params('invalid permission type')
            if role.vdis.create_terminate_others_sessions is not None and type(role.vdis.create_terminate_others_sessions) is not bool:
                raise exceptions.invalid_params('invalid permission type')

        existing = self.roles_dao.get_role(role.role_id)
        if existing is not None:
            raise exceptions.soca_exception(
                error_code=errorcodes.AUTH_USER_ALREADY_EXISTS,
                message=f'role with id: {role.role_id} already exists'
            )
        
        response = self.roles_dao.create_role(self.roles_dao.convert_to_db(role))

        return CreateRoleResponse(role=self.roles_dao.convert_from_db(response))

    def delete_role(self, request: DeleteRoleRequest) -> DeleteRoleResponse:
        """
        Delete a Role
        validate required fields, remove the project from DynamoDB
        :param request: DeleteRoleRequest
        :return: DeleteRoleResponse
        """
        if Utils.is_empty(request):
            raise exceptions.invalid_params('request is required')

        if Utils.is_empty(request.role_id):
            raise exceptions.invalid_params('role_id is required')

        ApiUtils.validate_input(request.role_id, constants.ROLE_ID_REGEX, constants.ROLE_ID_ERROR_MESSAGE)

        # Check if role exists
        role_to_update = self.roles_dao.get_role(role_id=request.role_id)
        if role_to_update:

            # Check if role is used by any project
            projects = self.role_assignments_dao.list_projects_for_role(role_id=request.role_id)
            if projects is not None and len(projects) > 0:
                raise exceptions.general_exception(f'role {request.role_id} is used by projects {projects}')
            
            # Delete the role
            self.roles_dao.delete_role(request.role_id)

        return DeleteRoleResponse()

    def update_role(self, request: UpdateRoleRequest) -> UpdateRoleResponse:
        """
        Update a Role
        validate required fields, update the role in DynamoDB
        :param role_id: str
        :param role: Role
        :return: the updated role in Role
        """
        role = request.role
        if Utils.is_empty(role):
            raise exceptions.invalid_params('role is required')
        
        if Utils.is_empty(role.role_id):
            raise exceptions.invalid_params('role.role_id is required')
        
        ApiUtils.validate_input(role.role_id, constants.ROLE_ID_REGEX, constants.ROLE_ID_ERROR_MESSAGE)
        
        # Check if role exists
        existing_role = self.roles_dao.get_role(role_id=role.role_id)
        if Utils.is_empty(existing_role):
            raise exceptions.soca_exception(
                error_code=errorcodes.ROLE_NOT_FOUND,
                message=f'role not found for id: {role.role_id}'
            )
        
        role_to_update = existing_role
        
        if not Utils.is_empty(role.name):
            ApiUtils.validate_input(role.name, constants.ROLE_NAME_REGEX, constants.ROLE_NAME_ERROR_MESSAGE)
            role_to_update['name'] = role.name
        if not Utils.is_empty(role.description):
            ApiUtils.validate_input(role.description, constants.ROLE_DESC_REGEX, constants.ROLE_DESC_ERROR_MESSAGE)
            role_to_update['desciption'] = role.description
        
        # Update the role permissions if they exist in the request; none values will be skipped
        if not Utils.is_empty(role.projects):
            # create project permissions section if it doesn't exist yet
            if role_to_update.get('projects') is None:
                role_to_update['projects'] = {}
            
            if not Utils.is_empty(role.projects.update_personnel):
                role_to_update['projects']['update_personnel'] = Utils.get_as_bool(role.projects.update_personnel, False)
            if not Utils.is_empty(role.projects.update_status):
                role_to_update['projects']['update_status'] = Utils.get_as_bool(role.projects.update_status, False)
        
        if not Utils.is_empty(role.vdis):
            # create vdi permissions section if it doesn't exist yet
            if role_to_update.get('vdis') is None:
                role_to_update['vdis'] = {}
            
            if not Utils.is_empty(role.vdis.create_sessions):
                role_to_update['vdis']['create_sessions'] = Utils.get_as_bool(role.vdis.create_sessions, False)
            if not Utils.is_empty(role.vdis.create_terminate_others_sessions):
                role_to_update['vdis']['create_terminate_others_sessions'] = Utils.get_as_bool(role.vdis.create_terminate_others_sessions, False)
        
        # Update the role in DynamoDB
        updated_role = self.roles_dao.update_role(role_to_update)
        
        return UpdateRoleResponse(role=self.roles_dao.convert_from_db(updated_role))
