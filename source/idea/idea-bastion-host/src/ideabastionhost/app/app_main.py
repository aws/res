#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import ideabastionhost
from ideadatamodel import constants


from ideasdk.context import SocaContextOptions
from ideasdk.app.soca_app_commands import launch_decorator
from ideasdk.utils import EnvironmentUtils
from ideabastionhost.app.bastion_host_app import IdeaBastionHostApp

import sys
import click
import traceback


@click.version_option(version=ideabastionhost.__version__)
@launch_decorator()
def main(**kwargs):
    """
    start bastion-host
    """

    try:
        cluster_name = EnvironmentUtils.idea_cluster_name(required=True)
        module_id = EnvironmentUtils.idea_module_id(required=True)
        module_set = EnvironmentUtils.idea_module_set(required=True)
        aws_region = EnvironmentUtils.aws_default_region(required=True)

        IdeaBastionHostApp(
            context=ideabastionhost.AppContext(
                options=SocaContextOptions(
                    cluster_name=cluster_name,
                    module_name=constants.MODULE_BASTION_HOST,
                    module_id=module_id,
                    module_set=module_set,
                    aws_region=aws_region,
                    is_app_server=True,
                    enable_aws_util=True,
                    enable_aws_client_provider=True,
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
