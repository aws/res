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

from __future__ import print_function
import json
from dataclasses import dataclass
from typing import Optional, Any
import logging

from idea_lambda_commons import CfnResponseStatus

logger = logging.getLogger()
logger.setLevel(logging.INFO)


@dataclass
class CfnResponse:
    context: Optional[Any]
    event: Optional[dict]
    status: Optional[CfnResponseStatus]
    physical_resource_id: Optional[str] = None
    no_echo: Optional[bool] = False
    reason: Optional[str] = None
    data: Optional[dict] = None

    def build_response_payload(self) -> str:

        context = self.context

        reason = self.reason
        if reason is None:
            reason = f'See the details in CloudWatch Log Stream: {context.log_stream_name}'

        physical_resource_id = self.physical_resource_id
        if physical_resource_id is None:
            physical_resource_id = context.log_stream_name

        stack_id = self.event.get('StackId', None)
        request_id = self.event.get('RequestId', None)
        logical_resource_id = self.event.get('LogicalResourceId', None)

        payload = {
            'Status': self.status,
            'Reason': reason,
            'PhysicalResourceId': physical_resource_id,
            'StackId': stack_id,
            'RequestId': request_id,
            'LogicalResourceId': logical_resource_id,
            'NoEcho': self.no_echo,
            'Data': self.data
        }
        return json.dumps(payload)

    @property
    def response_url(self) -> str:
        return self.event.get('ResponseURL', None)
