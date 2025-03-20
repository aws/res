#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import ideavirtualdesktop
from ideadatamodel import constants

from ideasdk.context import SocaContextOptions
from ideasdk.app.soca_app_commands import launch_decorator
from ideasdk.utils import EnvironmentUtils

from ideavirtualdesktop.app.virtual_desktop_app import IdeaVirtualDesktopApp

import sys
import click
import traceback


@click.version_option(version=ideavirtualdesktop.__version__)
@launch_decorator()
def main(**kwargs):
    """
    start virtual-desktop-app
    """

    try:
        cluster_name = EnvironmentUtils.idea_cluster_name(required=True)
        aws_region = EnvironmentUtils.aws_default_region(required=True)

        IdeaVirtualDesktopApp(
            context=ideavirtualdesktop.AppContext(
                options=SocaContextOptions(
                    cluster_name=cluster_name,
                    module_name=constants.MODULE_VIRTUAL_DESKTOP_APP,
                    module_id="vdi-app",
                    module_set="default",
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
