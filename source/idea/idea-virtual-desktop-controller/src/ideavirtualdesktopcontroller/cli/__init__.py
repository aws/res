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

from ideadatamodel import constants
from ideasdk.context import SocaContextOptions, SocaCliContext
from ideasdk.utils import EnvironmentUtils


def build_cli_context(cluster_config: bool = True, enable_aws_client_provider: bool = True, enable_aws_util: bool = True, unix_socket_timeout: int = 10):
    cluster_name = EnvironmentUtils.idea_cluster_name(required=True)
    module_id = EnvironmentUtils.idea_module_id(required=True)
    module_set = EnvironmentUtils.idea_module_set(required=True)
    aws_region = EnvironmentUtils.aws_default_region(required=True)
    return SocaCliContext(
        api_context_path=f'/{module_id}/api/v1',
        unix_socket_timeout=unix_socket_timeout,
        options=SocaContextOptions(
            module_name=constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER,
            module_id=module_id,
            module_set=module_set,
            cluster_name=cluster_name if cluster_config else None,
            aws_region=aws_region,
            enable_aws_client_provider=enable_aws_client_provider,
            enable_aws_util=enable_aws_util,
            default_logging_profile='console'
        )
    )
