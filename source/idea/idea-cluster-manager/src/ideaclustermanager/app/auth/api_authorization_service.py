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
from ideaclustermanager.app.accounts.accounts_service import AccountsService
from ideaclustermanager.app.authz.roles_service import RolesService
from ideaclustermanager.app.authz.role_assignments_service import RoleAssignmentsService
from ideadatamodel import GetRoleRequest, ListRoleAssignmentsRequest
from ideadatamodel.auth import User
from ideadatamodel import constants
from typing import Optional, List, Dict
from ideasdk.utils import Utils

class ClusterManagerApiAuthorizationService(ApiAuthorizationServiceBase):
    def __init__(self, accounts: AccountsService, roles: RolesService, role_assignments: RoleAssignmentsService):
        self.accounts = accounts
        self.roles = roles
        self.role_assignments = role_assignments

    def get_user_from_token_username(self, token_username: str) -> Optional[User]:
        return self.accounts.get_user_from_token_username(token_username=token_username)

    def get_roles_for_user(self, user: User, role_assignment_resource_key: Optional[str]) -> List[Dict]:
        # Get all role assignments for this user (both direct assignments and those via groups)
        role_ids_assigned = set()
        user_role_assignment = self.role_assignments.get_role_assignment(actor_key=f"{user.username}:user", resource_key=role_assignment_resource_key)
        if user_role_assignment is not None:
            role_ids_assigned.add(user_role_assignment.role_id)
        
        if not Utils.is_empty(user.additional_groups):
            if len(user.additional_groups)>constants.CONSERVE_DDB_RCU_LIST_GROUP_ROLES:
                group_role_assignments = self.role_assignments.list_role_assignments(ListRoleAssignmentsRequest(resource_key=role_assignment_resource_key)).items
                group_actor_keys = [f"{group}:group" for group in user.additional_groups]
                for group_role_assignment in group_role_assignments:
                    if group_role_assignment.actor_key in group_actor_keys:
                        role_ids_assigned.add(group_role_assignment.role_id)
            else:
                for group in user.additional_groups:
                    group_role_assignment = self.role_assignments.get_role_assignment(actor_key=f"{group}:group", resource_key=role_assignment_resource_key)
                    if group_role_assignment is not None:
                        role_ids_assigned.add(group_role_assignment.role_id)

        roles = []
        for role_id in role_ids_assigned:
            role = self.roles.get_role(GetRoleRequest(role_id=role_id)).role
            roles.append(Utils.flatten_dict(self.roles.roles_dao.convert_to_db(role)))

        return roles