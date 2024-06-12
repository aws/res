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
    ListRoleAssignmentsRequest
)
from ideadatamodel import exceptions
from ideasdk.utils import Utils, ApiUtils


class AuthzAPI(BaseAPI):

    def __init__(self, context: ideaclustermanager.AppContext):
        self.context = context
        self.logger = context.logger('authz')
        self.SCOPE_WRITE = f'{self.context.module_id()}/write'
        self.SCOPE_READ = f'{self.context.module_id()}/read'

        self.acl = {
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
        result = self.context.authz.put_role_assignments(request)
        context.success(result)

    def delete_role_assignments(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(BatchDeleteRoleAssignmentRequest)
        result = self.context.authz.delete_role_assignments(request)
        context.success(result)

    def list_role_assignments(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(ListRoleAssignmentsRequest)
        result = self.context.authz.list_role_assignments(request)
        context.success(result)

    def invoke(self, context: ApiInvocationContext):
        namespace = context.namespace

        acl_entry = Utils.get_value_as_dict(namespace, self.acl)
        if acl_entry is None:
            raise exceptions.unauthorized_access()
        
        acl_entry_scope = Utils.get_value_as_string('scope', acl_entry)
        is_authorized = context.is_authorized(elevated_access=True, scopes=[acl_entry_scope])
        username = context.get_username()
        user = self.context.accounts.get_user(username)
        
        # Current user needs to be IT admin or a project owner for all projects in the Put/Delete request
        if namespace in ['Authz.BatchPutRoleAssignment', 'Authz.BatchDeleteRoleAssignment']:
            request = context.get_request_payload_as(BatchPutRoleAssignmentRequest) if namespace == 'Authz.BatchPutRoleAssignment' else context.get_request_payload_as(BatchDeleteRoleAssignmentRequest)
            project_ids = list(set([assignment.resource_id for assignment in request.items]))
            if (is_authorized or self.context.authz.is_user_project_owner_for_all_projects(user=user, project_ids=project_ids)):
                acl_entry['method'](context)
                return
        
        # Current user needs to be IT admin or a project owner for any project
        if namespace == 'Authz.ListRoleAssignments' and (is_authorized or self.context.authz.is_user_any_project_owner(user=user)):
            acl_entry['method'](context)
            return
        
        raise exceptions.unauthorized_access()

    
