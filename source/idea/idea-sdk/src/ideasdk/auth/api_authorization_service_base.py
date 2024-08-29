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

from ideasdk.protocols import ApiAuthorizationServiceProtocol
from ideadatamodel.api.api_model import ApiAuthorization, ApiAuthorizationType
from ideadatamodel.auth import User
from ideadatamodel import exceptions, errorcodes
from ideasdk.utils import Utils
from typing import Optional, Dict, List
from abc import abstractmethod

class ApiAuthorizationServiceBase(ApiAuthorizationServiceProtocol):

    @abstractmethod
    def get_user_from_token_username(self, token_username: str) -> Optional[User]:
        ...

    def get_authorization_type(self, role: Optional[str]) -> ApiAuthorizationType:
        authorization_type = None
        if role:
            if role == ApiAuthorizationType.ADMINISTRATOR:
                authorization_type = ApiAuthorizationType.ADMINISTRATOR
            else:
                authorization_type = ApiAuthorizationType.USER
        if not authorization_type:
            authorization_type = ApiAuthorizationType.USER
        return authorization_type

    def get_authorization(self, decoded_token: Optional[Dict]) -> ApiAuthorization:
        username = decoded_token.get('username')
        token_scope = decoded_token.get('scope')
        client_id = decoded_token.get('client_id')
        authorization_type, role, db_username, scopes = None, None, None, None
        if not username:
            authorization_type = ApiAuthorizationType.APP
            if token_scope:
                scopes = token_scope.split(' ')
        else:
            user = self.get_user_from_token_username(username)
            username = user.username
            if not user.enabled:
                raise exceptions.unauthorized_access(errorcodes.AUTH_USER_IS_DISABLED)
            authorization_type = self.get_authorization_type(user.role)

        return ApiAuthorization(
            type=authorization_type,
            username=username,
            scopes=scopes,
            client_id=client_id
        )

    def is_scope_authorized(self, decoded_token: str, scope: str) -> bool:
        if not decoded_token:
            return False
        if not scope:
            return False
        authorization = self.get_authorization(decoded_token)
        if authorization.type != ApiAuthorizationType.APP:
            return False
        return authorization.scopes and scope in authorization.scopes

    def get_username(self, decoded_token: str) -> Optional[str]:
        if not decoded_token:
            return None
        token_username = decoded_token.get('username')
        user = self.get_user_from_token_username(token_username)
        return user.username

    @abstractmethod
    def get_roles_for_user(self, user: User, role_assignment_resource_key: Optional[str]) -> List[Dict]:
        ...

    def is_user_authorized(self, authorization: ApiAuthorization, namespace: str, role_assignment_resource_key: Optional[str], permission: Optional[str]) -> bool:
        if authorization.type != ApiAuthorizationType.USER:
            return False

        # Permissions are resource-specific (currently project-specific but will expand to other resources in the future)
        permission_needed_for_api = self._role_based_permission_lookup(permission)

        # If role-based authorization is not supported for this API namespace, nothing else needs to be checked
        if namespace not in permission_needed_for_api:
            return True

        # Some APIs can have varying authorization requirements - some use cases requiring role-based authz while some not
        # If role_assignment_resource_key is provided, role-based authorization is being requested
        if not role_assignment_resource_key:
            return True

        user = self.get_user_from_token_username(token_username=authorization.username)
        roles = self.get_roles_for_user(user, role_assignment_resource_key)

        # We get back roles as flattened dictionaries for easier permission querying
        return any(Utils.get_value_as_bool(key=permission_needed_for_api[namespace], obj=role, default=False) for role in roles)

    # Role-based authorization helpers

    def _role_based_permission_lookup(self, permission: Optional[str]) -> Dict:
        """
        Permissions to certain RES actions will need to be granted to non-admin users via their role assignments
        Roles contain permissions scoped to their respective resources. This action-to-permission scoping is represented here
        The value is the location of the permission in the role upon flattening of the object

        For some use cases, an API might be linked to more than one permission. In such cases, the "permission" param value should be used.
        """
        return {
            "Authz.BatchPutRoleAssignment": "projects.update_personnel",
            "Authz.BatchDeleteRoleAssignment": "projects.update_personnel",
            "Projects.EnableProject": "projects.update_status",
            "Projects.DisableProject": "projects.update_status",
            "VirtualDesktop.CreateSession": permission,
            "VirtualDesktop.DeleteSessions": permission,
            }
