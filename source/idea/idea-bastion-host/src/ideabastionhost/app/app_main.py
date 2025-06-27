#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import sys
import traceback

import click
import ideabastionhost
import res.constants as constants
from ideabastionhost.app.bastion_host_app import IdeaBastionHostApp
from res.app.app_commands import launch_decorator
from res.resources import cluster_settings


@click.version_option(version=ideabastionhost.__version__)
@launch_decorator()
def main(**kwargs):
    """
    start bastion-host
    """

    try:
        configure_environment()

        IdeaBastionHostApp().launch()

    except Exception as e:
        print(f'failed to initialize application context: {e}')
        traceback.print_exc()
        print('exit code: 1')
        sys.exit(1)


def configure_environment():
    # RES environment configuration
    os.environ["IDEA_MODULE_NAME"] = constants.MODULE_NAME_BASTION_HOST
    os.environ["IDEA_MODULE_SET"] = constants.DEFAULT_MODULE_SET
    os.environ["IDEA_MODULE_VERSION"] = ideabastionhost.__version__
    os.environ["IDEA_CLUSTER_NAME"] = os.environ.get("environment_name")

    # Proxy configuration
    os.environ["IDEA_HTTPS_PROXY"] = (
        cluster_settings.get_setting("cluster.network.https_proxy") or ""
    )
    os.environ["IDEA_NO_PROXY"] = (
        cluster_settings.get_setting("cluster.network.no_proxy") or ""
    )

# used only for local testing
if __name__ == '__main__':
    main(sys.argv[1:])
