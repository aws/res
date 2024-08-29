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
from ideadatamodel.authz import (
    GetRoleRequest,
    GetRoleResponse,
    ListRolesRequest,
    ListRolesResponse
)

from typing import Optional


class RolesClient:

    def __init__(self, context: SocaContextProtocol,
                 options: SocaClientOptions,
                 token_service: Optional[TokenService]):
        """
        :param context: Application Context
        :param options: Client Options
        :param token_service: TokenService to get the access token. Token service is not required if options.unix_socket is provided.
        """
        self.context = context
        self.logger = context.logger('roles-client')
        self.client = SocaClient(context=context, options=options)

        if Utils.is_empty(options.unix_socket) and token_service is None:
            raise exceptions.invalid_params('token_service is required for http client')
        self.token_service = token_service

    def get_access_token(self) -> Optional[str]:
        if self.token_service is None:
            return None
        return self.token_service.get_access_token()

    def get_role(self, request: GetRoleRequest) -> GetRoleResponse:
        return self.client.invoke_alt(
            namespace='Authz.GetRole',
            payload=request,
            result_as=GetRoleResponse,
            access_token=self.get_access_token()
        )

    def list_roles(self, request: ListRolesRequest) -> ListRolesResponse:
        return self.client.invoke_alt(
            namespace='Authz.ListRole',
            payload=request,
            result_as=ListRolesResponse,
            access_token=self.get_access_token()
        )

    def destroy(self):
        self.client.close()
