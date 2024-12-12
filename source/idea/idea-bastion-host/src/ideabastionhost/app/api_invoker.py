#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from ideasdk.api import ApiInvocationContext
from ideasdk.protocols import ApiInvokerProtocol
from ideasdk.auth import TokenService, ApiAuthorizationServiceBase
from typing import Optional, Dict


class BastionHostApiInvoker(ApiInvokerProtocol):

    def get_token_service(self) -> Optional[TokenService]:
        pass

    def get_api_authorization_service(self) -> Optional[ApiAuthorizationServiceBase]:
        pass

    def get_request_logging_payload(self, context: ApiInvocationContext) -> Optional[Dict]:
        pass

    def get_response_logging_payload(self, context: ApiInvocationContext) -> Optional[Dict]:
        pass

    def invoke(self, context: ApiInvocationContext):
        pass
