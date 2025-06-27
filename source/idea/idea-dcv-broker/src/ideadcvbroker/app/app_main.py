#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import sys
import traceback

import click
import ideadcvbroker
import res.constants as constants
from ideadcvbroker.app.dcv_broker_app import DcvBrokerApp
from res.app.app_commands import launch_decorator
from res.resources import cluster_settings


@click.version_option(version=ideadcvbroker.__version__)
@launch_decorator()
def main(**kwargs):
    """
    start DCV broker app
    """

    try:
        configure_environment()

        DcvBrokerApp().launch()

    except Exception as e:
        print(f'failed to initialize application context: {e}')
        traceback.print_exc()
        print('exit code: 1')
        sys.exit(1)


def configure_environment():
    os.environ["IDEA_MODULE_NAME"] = constants.MODULE_NAME_VDC
    os.environ["IDEA_CLUSTER_NAME"] = cluster_settings.get_setting("cluster.cluster_name") or "" 
    os.environ["AWS_REGION"] = cluster_settings.get_setting("cluster.aws.region") or ""
    os.environ["IDEA_HTTPS_PROXY"] = (
        cluster_settings.get_setting("cluster.network.https_proxy") or ""
    )
    os.environ["IDEA_NO_PROXY"] = (
        cluster_settings.get_setting("cluster.network.no_proxy") or ""
    )

# used only for local testing
if __name__ == '__main__':
    main(sys.argv[1:])
