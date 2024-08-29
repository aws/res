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

from ideasdk.auth.api_authorization_service_base import ApiAuthorizationServiceBase
from ideasdk.auth.token_service import TokenService
from ideasdk.client import AccountsClient, RolesClient, RoleAssignmentsClient
from ideasdk.utils import Utils
from ideadatamodel.auth import GetUserByEmailRequest, GetUserRequest, User
from ideadatamodel import ListRoleAssignmentsRequest, GetRoleRequest
from ideadatamodel import exceptions, errorcodes, constants
from typing import Optional, List, Dict

class VdcApiAuthorizationService(ApiAuthorizationServiceBase):
    def __init__(self, accounts_client: AccountsClient, token_service: TokenService, roles_client: RolesClient, role_assignments_client: RoleAssignmentsClient):
        self.accounts_client = accounts_client
        self.token_service = token_service
        self.roles_client = roles_client
        self.role_assignments_client = role_assignments_client
    
    def get_user_from_token_username(self, token_username: str) -> Optional[User]:
        if not token_username:
            raise exceptions.unauthorized_access()
        
        email = self.token_service.get_email_from_token_username(token_username=token_username)
        user = None
        if email:
            user = self.accounts_client.get_user_by_email(request=GetUserByEmailRequest(email=email)).user
        else:
            # This is for clusteradmin
            user =  self.accounts_client.get_user(request=GetUserRequest(username=token_username)).user
        if not user:
            exception_string = f'email: {email}' if email else f'username: {token_username}' 
            raise exceptions.SocaException(
                 error_code=errorcodes.AUTH_USER_NOT_FOUND,
                 message=f'User not found with {exception_string}'
            )
        return user
    
    def get_roles_for_user(self, user: User, role_assignment_resource_key: Optional[str]) -> List[Dict]:
        # Get all role assignments for this user (both direct assignments and those via groups)
        role_ids_assigned = set()
        user_role_assignments = self.role_assignments_client.list_role_assignments(ListRoleAssignmentsRequest(actor_key=f"{user.username}:user", resource_key=role_assignment_resource_key))
        if not Utils.is_empty(user_role_assignments.items):
            # Since we provide both actor_key and resource_key, the response will be one or none
            role_ids_assigned.add(user_role_assignments.items[0].role_id)
        
        if not Utils.is_empty(user.additional_groups):
            if len(user.additional_groups)>constants.CONSERVE_DDB_RCU_LIST_GROUP_ROLES:
                group_role_assignments = self.role_assignments_client.list_role_assignments(ListRoleAssignmentsRequest(resource_key=role_assignment_resource_key))
                group_actor_keys = [f"{group}:group" for group in user.additional_groups]
                for group_role_assignment in group_role_assignments.items:
                    if group_role_assignment.actor_key in group_actor_keys:
                        role_ids_assigned.add(group_role_assignment.role_id)
            else:
                for group in user.additional_groups:
                    group_role_assignments = self.role_assignments_client.list_role_assignments(ListRoleAssignmentsRequest(actor_key=f"{group}:group", resource_key=role_assignment_resource_key))
                    # Since we provide both actor_key and resource_key, the response will be one or none
                    if not Utils.is_empty(group_role_assignments.items):
                        role_ids_assigned.add(group_role_assignments.items[0].role_id)
        
        roles = []
        for role_id in role_ids_assigned:
            role = self.roles_client.get_role(GetRoleRequest(role_id=role_id)).role
            roles.append(Utils.flatten_dict(Utils.convert_to_dict(role)))

        return roles
