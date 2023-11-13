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

from ideasdk.api import BaseAPI
from ideasdk.protocols import SocaContextProtocol
from ideasdk.api import ApiInvocationContext

from ideadatamodel.app import (
    GetModuleInfoResult,
    ModuleInfo
)


class SocaAppAPI(BaseAPI):

    def __init__(self, context: SocaContextProtocol):
        self.context = context

    def get_module_info(self, context: ApiInvocationContext):
        context.success(GetModuleInfoResult(
            module=ModuleInfo(
                module_name=self.context.module_name(),
                module_version=self.context.module_version(),
                module_id=self.context.module_id()
            )
        ))

    def invoke(self, context: ApiInvocationContext):
        if context.namespace == 'App.GetModuleInfo':
            self.get_module_info(context)
