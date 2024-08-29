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

import ideaclustermanager

from ideasdk.api import ApiInvocationContext, BaseAPI
from ideadatamodel.authz import (
    BatchPutRoleAssignmentRequest,
    BatchDeleteRoleAssignmentRequest,
    ListRoleAssignmentsRequest,
    ListRolesRequest,
    GetRoleRequest,
    CreateRoleRequest,
    DeleteRoleRequest,
    UpdateRoleRequest
)
from ideadatamodel.projects import (
    GetUserProjectsRequest
)
from ideadatamodel import exceptions
from ideasdk.utils import Utils, ApiUtils

'''
This class is used to manage both roles and role assignments. Since both services lead to defining user authorization, 
they are logged within the same context for easier debugging if needed.
'''
class AuthzAPI(BaseAPI):

    def __init__(self, context: ideaclustermanager.AppContext):
        self.context = context
        self.logger = context.logger('authz')
        self.SCOPE_WRITE = f'{self.context.module_id()}/write'
        self.SCOPE_READ = f'{self.context.module_id()}/read'

        self.acl = {
            # ======== Role APIs ========
            'Authz.ListRoles': {
                'scope': self.SCOPE_READ,
                'method': self.list_roles
            },
            'Authz.GetRole': {
                'scope': self.SCOPE_READ,
                'method': self.get_role
            },
            'Authz.CreateRole': {
                'scope': self.SCOPE_WRITE,
                'method': self.create_role
            },
            'Authz.DeleteRole': {
                'scope': self.SCOPE_WRITE,
                'method': self.delete_role
            },
            'Authz.UpdateRole': {
                'scope': self.SCOPE_WRITE,
                'method': self.update_role
            },

            # ======== Role Assignment APIs ========
            'Authz.BatchPutRoleAssignment': {
                'scope': self.SCOPE_WRITE,
                'method': self.put_role_assignments
            },
            'Authz.BatchDeleteRoleAssignment': {
                'scope': self.SCOPE_WRITE,
                'method': self.delete_role_assignments
            },
            'Authz.ListRoleAssignments': {
                'scope': self.SCOPE_READ,
                'method': self.list_role_assignments
            }
        }

    def put_role_assignments(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(BatchPutRoleAssignmentRequest)
        result = self.context.role_assignments.put_role_assignments(request)
        context.success(result)

    def delete_role_assignments(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(BatchDeleteRoleAssignmentRequest)
        result = self.context.role_assignments.delete_role_assignments(request)
        context.success(result)

    def list_role_assignments(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(ListRoleAssignmentsRequest)
        result = self.context.role_assignments.list_role_assignments(request)
        context.success(result)

    def list_roles(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(ListRolesRequest)
        result = self.context.roles.list_roles(request)
        context.success(result)
    
    def get_role(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(GetRoleRequest)
        result = self.context.roles.get_role(request)
        context.success(result)
    
    def create_role(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(CreateRoleRequest)
        result = self.context.roles.create_role(request)
        context.success(result)
    
    def delete_role(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(DeleteRoleRequest)
        result = self.context.roles.delete_role(request)
        context.success(result)
    
    def update_role(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(UpdateRoleRequest)
        result = self.context.roles.update_role(request)
        context.success(result)

    def invoke(self, context: ApiInvocationContext):
        namespace = context.namespace

        acl_entry = Utils.get_value_as_dict(namespace, self.acl)
        if acl_entry is None:
            raise exceptions.unauthorized_access()
        
        acl_entry_scope = Utils.get_value_as_string('scope', acl_entry)
        is_authorized = context.is_authorized(elevated_access=True, scopes=[acl_entry_scope])

        if is_authorized:
            acl_entry['method'](context)
            return

        username = context.get_username()

        # Conditional permissions for non-admins

        if namespace == 'Authz.BatchPutRoleAssignment':
            request = context.get_request_payload_as(BatchPutRoleAssignmentRequest)
            project_ids = list(set([assignment.resource_id for assignment in request.items]))
            # Current user must have "update_personnel" permission for all projects in the Put request
            if all([context.is_authorized(elevated_access=False, scopes=[acl_entry_scope], role_assignment_resource_key=f"{project_id}:project") for project_id in project_ids]):
                acl_entry['method'](context)
                return
        elif namespace == 'Authz.BatchDeleteRoleAssignment':
            request = context.get_request_payload_as(BatchDeleteRoleAssignmentRequest)
            project_ids = list(set([assignment.resource_id for assignment in request.items]))
            # Current user must have "update_personnel" permission for all projects in the Delete request
            if all([context.is_authorized(elevated_access=False, scopes=[acl_entry_scope], role_assignment_resource_key=f"{project_id}:project") for project_id in project_ids]):
                acl_entry['method'](context)
                return
        elif namespace == 'Authz.ListRoleAssignments':
            # Current user must be assigned to a project in the application
            projects_assigned = self.context.projects.get_user_projects(GetUserProjectsRequest(username=username, exclude_disabled=False))
            if not Utils.is_empty(projects_assigned.projects):
                acl_entry['method'](context)
                return
        elif namespace == 'Authz.ListRoles':
            # Current user must be assigned to a project in the application
            projects_assigned = self.context.projects.get_user_projects(GetUserProjectsRequest(username=username, exclude_disabled=False))
            if not Utils.is_empty(projects_assigned.projects):
                acl_entry['method'](context)
                return
        elif namespace == 'Authz.GetRole':
            # Current user must be assigned to a project in the application
            projects_assigned = self.context.projects.get_user_projects(GetUserProjectsRequest(username=username, exclude_disabled=False))
            if not Utils.is_empty(projects_assigned.projects):
                acl_entry['method'](context)
                return
        
        raise exceptions.unauthorized_access()
