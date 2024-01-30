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

from ideasdk.protocols import SocaContextProtocol

from ideasdk.client.soca_client import SocaClient, SocaClientOptions
from ideasdk.auth import TokenService
from ideasdk.utils import Utils
from ideadatamodel import exceptions
from ideadatamodel.auth import (
    ListUsersInGroupRequest,
    ListUsersInGroupResult,
    GetUserRequest,
    GetUserResult,
    GetUserByEmailRequest,
    GetUserByEmailResult,
    GetGroupRequest,
    GetGroupResult
)

from typing import Optional


class AccountsClient:

    def __init__(self, context: SocaContextProtocol,
                 options: SocaClientOptions,
                 token_service: Optional[TokenService]):
        """
        :param context: Application Context
        :param options: Client Options
        :param token_service: TokenService to get the access token. Token service is not required if options.unix_socket is provided.
        """
        self.context = context
        self.logger = context.logger('accounts-client')
        self.client = SocaClient(context=context, options=options)

        if Utils.is_empty(options.unix_socket) and token_service is None:
            raise exceptions.invalid_params('token_service is required for http client')
        self.token_service = token_service

    def get_access_token(self) -> Optional[str]:
        if self.token_service is None:
            return None
        return self.token_service.get_access_token()

    def list_users_in_group(self, request: ListUsersInGroupRequest) -> ListUsersInGroupResult:
        return self.client.invoke_alt(
            namespace='Accounts.ListUsersInGroup',
            payload=request,
            result_as=ListUsersInGroupResult,
            access_token=self.get_access_token()
        )

    def get_user(self, request: GetUserRequest) -> GetUserResult:
        return self.client.invoke_alt(
            namespace='Accounts.GetUser',
            payload=request,
            result_as=GetUserResult,
            access_token=self.get_access_token()
        )

    def get_user_by_email(self, request: GetUserByEmailRequest) -> GetUserByEmailResult:
        return self.client.invoke_alt(
            namespace='Accounts.GetUserByEmail',
            payload=request,
            result_as=GetUserByEmailResult,
            access_token=self.get_access_token()
        )

    def get_group(self, request: GetGroupRequest) -> GetGroupResult:
        return self.client.invoke_alt(
            namespace='Accounts.GetUserGroup',
            payload=request,
            result_as=GetGroupResult,
            access_token=self.get_access_token()
        )

    def destroy(self):
        self.client.close()
