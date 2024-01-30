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

import json

import requests

from tests.integration.framework.api_invoker.api_invoker_base import ResApiInvokerBase
from tests.integration.framework.model.api_invocation_context import (
    ApiInvocationContext,
)


class HttpApiInvoker(ResApiInvokerBase):
    """
    API invoker implementation for invoking service APIs via HTTP requests
    """

    def invoke(self, context: ApiInvocationContext) -> None:
        http_headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "X_RES_TEST_USERNAME": context.auth.username,
        }
        response = requests.post(
            f"{context.endpoint}/api/v{context.request.header.version}/{context.request.namespace}",
            json=json.loads(context.request.json(exclude_none=True, by_alias=True)),
            headers=http_headers,
            verify=False,
        ).json()

        context.response = response
