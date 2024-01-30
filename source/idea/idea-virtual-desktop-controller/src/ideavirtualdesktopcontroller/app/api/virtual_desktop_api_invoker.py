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
from ideasdk.api import ApiInvocationContext
from ideasdk.app import SocaAppAPI
from ideasdk.auth import TokenService, ApiAuthorizationServiceBase
from ideasdk.protocols import ApiInvokerProtocol
from ideavirtualdesktopcontroller.app.api.virtual_desktop_admin_api import VirtualDesktopAdminAPI
from ideavirtualdesktopcontroller.app.api.virtual_desktop_dcv_api import VirtualDesktopDCVAPI
from ideavirtualdesktopcontroller.app.api.virtual_desktop_user_api import VirtualDesktopUserAPI
from ideavirtualdesktopcontroller.app.api.virtual_desktop_utils_api import VirtualDesktopUtilsAPI
from typing import Optional

class VirtualDesktopApiInvoker(ApiInvokerProtocol):

    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        self._context = context
        self.INVOKER_MAP = {
            'VirtualDesktopUtils': VirtualDesktopUtilsAPI(context),
            'VirtualDesktopDCV': VirtualDesktopDCVAPI(context),
            'VirtualDesktopAdmin': VirtualDesktopAdminAPI(context),
            'VirtualDesktop': VirtualDesktopUserAPI(context),
            'App': SocaAppAPI(context)
        }

    def get_token_service(self) -> Optional[TokenService]:
        return self._context.token_service
    
    def get_api_authorization_service(self) -> Optional[ApiAuthorizationServiceBase]:
        return self._context.api_authorization_service

    def invoke(self, context: ApiInvocationContext):
        namespace = context.namespace
        leading_namespace = namespace.split('.')[0]

        return self.INVOKER_MAP[leading_namespace].invoke(context)

