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
        self.SCOPE_READ = f'{self.context.module_id()}/read'
        self.acl = {
            'VirtualDesktopDCV.DescribeServers': {
                'scope': self.SCOPE_READ,
                'method': self.describe_dcv_servers,
            },
            'VirtualDesktopDCV.DescribeSessions': {
                'scope': self.SCOPE_READ,
                'method': self.describe_dcv_sessions,
            },
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
        namespace = context.namespace

        acl_entry = self.acl.get(namespace)
        if acl_entry is None:
            raise exceptions.unauthorized_access()

        acl_entry_scope = acl_entry.get('scope')
        is_authorized = context.is_authorized(elevated_access=True, scopes=[acl_entry_scope])

        if is_authorized:
            acl_entry['method'](context)
        else:
            raise exceptions.unauthorized_access()
