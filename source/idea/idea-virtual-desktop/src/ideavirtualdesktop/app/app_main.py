#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import ideavirtualdesktop

from res.app.app_commands import launch_decorator
import res.constants as constants

from res.resources import cluster_settings

from ideavirtualdesktop.app.virtual_desktop_app import IdeaVirtualDesktopApp

import os
import sys
import click
import traceback

import boto3
import json
            
@click.version_option(version=ideavirtualdesktop.__version__)
@launch_decorator()
def main(**kwargs):
    """
    start virtual-desktop-app
    """

    try:
        configure_environment()
        IdeaVirtualDesktopApp().launch()

    except Exception as e:
        print(f'failed to initialize application context: {e}')
        traceback.print_exc()
        print('exit code: 1')
        sys.exit(1)


def configure_environment():
    # RES environment configuration
    os.environ["IDEA_MODULE_NAME"] = constants.MODULE_NAME_VIRTUAL_DESKTOP_APP
    os.environ["IDEA_MODULE_SET"] = constants.DEFAULT_MODULE_SET
    os.environ["IDEA_MODULE_VERSION"] = ideavirtualdesktop.__version__
    os.environ["IDEA_CLUSTER_NAME"] = cluster_settings.get_setting("cluster.cluster_name") or "" 
    os.environ["IDEA_CLUSTER_HOME"] = cluster_settings.get_setting("cluster.home_dir")
    
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
