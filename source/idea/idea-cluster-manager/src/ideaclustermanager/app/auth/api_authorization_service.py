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
from ideadatamodel.auth import User
from typing import Optional

class ClusterManagerApiAuthorizationService(ApiAuthorizationServiceBase):
    def __init__(self, accounts: AccountsService):
        self.accounts = accounts

    def get_user_from_token_username(self, token_username: str) -> Optional[User]:
        return self.accounts.get_user_from_token_username(token_username=token_username)
