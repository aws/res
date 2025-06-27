#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import sys
import traceback

import click
import ideadcvconnectiongateway
import res.constants as constants
from ideadcvconnectiongateway.app.dcv_connection_gateway_app import (
    DcvConnectionGatewayApp,
)
from res.app.app_commands import launch_decorator
from res.resources import cluster_settings


@click.version_option(version=ideadcvconnectiongateway.__version__)
@launch_decorator()
def main(**kwargs):
    """
    start DCV connection gateway app
    """

    try:
        configure_environment()

        DcvConnectionGatewayApp().launch()

    except Exception as e:
        print(f'failed to initialize application context: {e}')
        traceback.print_exc()
        print('exit code: 1')
        sys.exit(1)


def configure_environment():
    os.environ["IDEA_MODULE_NAME"] = constants.MODULE_NAME_VDC
    os.environ["IDEA_CLUSTER_NAME"] = os.environ.get("environment_name") or ""

    os.environ["IDEA_HTTPS_PROXY"] = (
        cluster_settings.get_setting("cluster.network.https_proxy") or ""
    )
    os.environ["IDEA_NO_PROXY"] = (
        cluster_settings.get_setting("cluster.network.no_proxy") or ""
    )


# used only for local testing
if __name__ == '__main__':
    main(sys.argv[1:])
