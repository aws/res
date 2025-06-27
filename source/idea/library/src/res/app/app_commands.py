#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import click
from res.constants import CONFIG_LEVEL_CRITICAL


def launch_decorator():
    def args(func):
        func = click.command(
            context_settings=dict(
                help_option_names=["-h", "--help"], max_content_width=1200
            )
        )(func)
        func = click.option(
            "--cluster-name", type=str, required=False, help="Cluster Name"
        )(func)
        func = click.option(
            "--cluster-version", type=str, required=False, help="Cluster Version"
        )(func)
        func = click.option(
            "--cluster-deployment-id",
            type=int,
            required=False,
            help="Cluster Deployment Id",
        )(func)
        func = click.option(
            "--app-deployment-id", type=int, required=False, help="App Deployment Id"
        )(func)
        func = click.option(
            "--locale", type=str, required=False, help="Locale eg. en_US"
        )(func)
        func = click.option(
            "--cluster-config-file",
            type=str,
            required=False,
            help="Cluster config file. eg. /opt/idea/cluster-config[.json|.yml]",
        )(func)
        func = click.option(
            "--config-file",
            "-c",
            type=str,
            required=False,
            help="RES configuration file. eg. /opt/idea/app/[app-dir]/config/idea.conf",
        )(func)
        func = click.option(
            "--env-file",
            "-e",
            type=str,
            required=False,
            help="Environment file. eg. /path/to/customenv.env",
        )(func)
        func = click.option(
            "--config-overrides-file",
            "-o",
            type=str,
            required=False,
            help="RES config override file. eg. /path/to/config-overrides.properties",
        )(func)
        func = click.option(
            "--validation-level",
            "-l",
            default=CONFIG_LEVEL_CRITICAL,
            help="Configuration validation level. configuration errors higher than this will cause "
            "the app startup to fail.",
        )(func)
        func = click.option(
            "--port", "-p", type=str, required=False, help="HTTP Server Port. eg. 8080"
        )(func)
        return func

    return args
