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
from ideasdk.client import AccountsClient
from ideadatamodel.auth import GetUserByEmailRequest, GetUserRequest, User
from ideadatamodel import exceptions, errorcodes
from typing import Optional

class VdcApiAuthorizationService(ApiAuthorizationServiceBase):
    def __init__(self, accounts_client: AccountsClient, token_service: TokenService):
        self.accounts_client = accounts_client
        self.token_service = token_service
    
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
