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

from ideadatamodel import exceptions
from ideasdk.utils import Utils, EnvironmentUtils
from ideasdk.context import SocaContextOptions
from ideaadministrator.app_protocols import (
    AdministratorContextProtocol
)
from ideaadministrator.app_utils import AdministratorUtils

from typing import Optional


class AdministratorContext(AdministratorContextProtocol):

    def __init__(self, cluster_name: str, aws_region: str, aws_profile: Optional[str] = None, module_id: Optional[str] = None):
        super().__init__(
            options=SocaContextOptions(
                cluster_name=cluster_name,
                aws_region=aws_region,
                aws_profile=aws_profile,
                module_id=module_id,
                enable_aws_client_provider=True,
                enable_aws_util=True,
                locale=EnvironmentUtils.get_environment_variable('LC_CTYPE', default='en_US')
            )
        )
        self._admin_utils = AdministratorUtils()

    def get_stack_name(self, module_id: str = None) -> str:
        if Utils.is_empty(module_id):
            raise exceptions.invalid_params('get_stack_name: cannot create stack name without a module_id')

        cluster_name = self.config().get_string('cluster.cluster_name')
        return f'{cluster_name}-{module_id}'
