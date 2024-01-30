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

from typing import Any, Dict, Type

from pydantic import BaseModel

from ideadatamodel import SocaEnvelope, SocaPayloadType, get_payload_as  # type: ignore
from tests.integration.framework.model.client_auth import ClientAuth


class ApiInvocationContext(BaseModel):
    """
    API invocation context that wraps endpoint, authorization, request and response.
    """

    endpoint: str
    request: SocaEnvelope
    auth: ClientAuth
    response: Dict[str, Any] = {}

    def get_response_payload_as(
        self, payload_type: Type[SocaPayloadType]
    ) -> SocaPayloadType:
        return get_payload_as(
            payload=self.response.get("payload"), payload_type=payload_type
        )

    def response_is_success(self) -> bool:
        return self.response.get("success", False)
