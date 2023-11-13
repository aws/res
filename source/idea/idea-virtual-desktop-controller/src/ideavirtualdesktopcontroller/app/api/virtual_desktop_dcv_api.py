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

import ideavirtualdesktopcontroller
from ideadatamodel import exceptions
from ideadatamodel.virtual_desktop import (
    DescribeServersResponse,
    DescribeSessionsRequest,
    DescribeSessionsResponse
)
from ideasdk.api import ApiInvocationContext
from ideavirtualdesktopcontroller.app.api.virtual_desktop_api import VirtualDesktopAPI


class VirtualDesktopDCVAPI(VirtualDesktopAPI):
    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        super().__init__(context)
        self.context = context
        self._logger = context.logger('virtual-desktop-dcv-api')
        self.namespace_handler_map = {
            'VirtualDesktopDCV.DescribeServers': self.describe_dcv_servers,
            'VirtualDesktopDCV.DescribeSessions': self.describe_dcv_sessions
        }

    def describe_dcv_servers(self, context: ApiInvocationContext):
        response = self.context.dcv_broker_client.describe_servers()
        context.success(DescribeServersResponse(
            response=response
        ))

    def describe_dcv_sessions(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(DescribeSessionsRequest)
        response = self.context.dcv_broker_client.describe_sessions(request.sessions)
        context.success(DescribeSessionsResponse(
            response=response
        ))

    def invoke(self, context: ApiInvocationContext):

        if not context.is_authorized(elevated_access=True):
            raise exceptions.unauthorized_access()

        namespace = context.namespace
        if namespace in self.namespace_handler_map:
            self.namespace_handler_map[namespace](context)
