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

from ideasdk.context import SocaCliContext, SocaContextOptions
from ideasdk.config.cluster_config import ClusterConfig
from ideadatamodel import constants
import ideaadministrator

from tasks import cli

from invoke import task, Context
from typing import Optional
import os
import prettytable


@task
def cdk_nag_scan(c, cluster_name, aws_region, aws_profile=None, module_name=None):
    # type: (Context, str, str, Optional[str], Optional[str]) -> None
    """
    perform cdk nag scan on all applicable cdk stacks
    """

    ignore_modules = [
        constants.MODULE_BOOTSTRAP,
        constants.MODULE_CLUSTER,
        constants.MODULE_GLOBAL_SETTINGS
    ]

    context = SocaCliContext(options=SocaContextOptions(
        cluster_name=cluster_name,
        aws_region=aws_region,
        aws_profile=aws_profile,
        enable_aws_client_provider=True,
        enable_aws_util=True
    ))

    cluster_config: ClusterConfig = context.config()

    summary = []

    os.environ['IDEA_ADMIN_ENABLE_CDK_NAG_SCAN'] = 'true'

    cluster_module_id = cluster_config.get_module_id(constants.MODULE_CLUSTER)
    cluster_module_info = cluster_config.db.get_module_info(cluster_module_id)
    cluster_deployed = cluster_module_info['status'] == 'deployed'

    for current_module_name in constants.ALL_MODULES:
        if current_module_name in ignore_modules:
            continue
        if module_name is not None:
            if current_module_name != module_name:
                continue

        if not cluster_deployed:
            continue

        module_id = cluster_config.get_module_id(current_module_name)

        with context.spinner(f'running cdk_nag scan for module: {current_module_name}, module_id: {module_id} ...'):
            invoke_args = [
                'cdk',
                'synth',
                module_id,
                '--cluster-name',
                cluster_name,
                '--aws-region',
                aws_region
            ]
            if aws_profile is not None:
                invoke_args += [
                    '--aws-profile',
                    aws_profile
                ]

            success = False
            try:
                cli.invoke_cli(
                    c=c,
                    app_name='res-admin',
                    module_name='ideaadministrator.app_main',
                    invoke_args=invoke_args
                )
            except SystemExit as e:
                success = e.code == 0

            cluster_cdk_dir = ideaadministrator.props.cluster_cdk_dir(cluster_name=cluster_name, aws_region=aws_region)
            report_file = os.path.join(cluster_cdk_dir, 'cdk.out', f'AwsSolutions-{cluster_name}-{module_id}-NagReport.csv')

            if success:
                if not os.path.isfile(report_file):
                    success = False
                    report_file = None

            if success:
                context.success(f'cdk_nag scan for module: {current_module_name}, module_id: {module_id} succeeded: {report_file}')
            else:
                if report_file:
                    context.error(f'cdk_nag scan for module: {current_module_name}, module_id: {module_id} failed: {report_file}')
                else:
                    context.error(f'cdk synth for module: {current_module_name}, module_id: {module_id} failed.')

            summary.append({
                'module_name': current_module_name,
                'status': success,
                'report_csv': report_file
            })

    context.new_line()
    context.print_title('cdk_nag scan summary')
    table = prettytable.PrettyTable(['Module', 'Status', 'Report'])
    table.align = 'l'
    for module_info in summary:
        status = 'Success' if module_info['status'] else 'Fail'
        table.add_row([module_info['module_name'], status, module_info['report_csv']])
    print(table)
