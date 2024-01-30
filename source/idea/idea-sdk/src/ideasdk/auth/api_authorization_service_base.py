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
from typing import Optional, Dict
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
