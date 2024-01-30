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

import ideaclustermanager

from ideadatamodel import constants
from ideasdk.context import SocaContextOptions
from ideasdk.app.soca_app_commands import launch_decorator
from ideasdk.utils import EnvironmentUtils

from ideaclustermanager.app.cluster_manager_app import ClusterManagerApp

import sys
import click
import traceback


@click.version_option(version=ideaclustermanager.__version__)
@launch_decorator()
def main(**kwargs):
    """
    start cluster-manager
    """
    try:

        cluster_name = EnvironmentUtils.idea_cluster_name(required=True)
        module_id = EnvironmentUtils.idea_module_id(required=True)
        module_set = EnvironmentUtils.idea_module_set(required=True)
        aws_region = EnvironmentUtils.aws_default_region(required=True)

        ClusterManagerApp(
            context=ideaclustermanager.AppContext(
                options=SocaContextOptions(
                    cluster_name=cluster_name,
                    module_name=constants.MODULE_CLUSTER_MANAGER,
                    module_id=module_id,
                    module_set=module_set,
                    aws_region=aws_region,
                    is_app_server=True,
                    enable_aws_client_provider=True,
                    enable_aws_util=True,
                    enable_instance_metadata_util=True,
                    use_vpc_endpoints=True,
                    enable_distributed_lock=True,
                    enable_leader_election=True,
                    enable_metrics=True,
                )
            ),
            **kwargs
        ).launch()

    except Exception as e:
        print(f'failed to initialize application context: {e}')
        traceback.print_exc()
        print('exit code: 1')
        sys.exit(1)


# used only for local testing
if __name__ == '__main__':
    main(sys.argv[1:])
