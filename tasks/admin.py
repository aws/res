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

from ideaadministrator.app_utils import AdministratorUtils
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
def test_iam_policies(c, cluster_name, aws_region, aws_profile=None):
    # type: (Context, str, str, Optional[str]) -> None
    """
    test and render all IAM policy documents
    """

    all_modules = [
        {
            'module_name': constants.MODULE_CLUSTER,
            'templates': [
                'custom-resource-cluster-endpoints.yml',
                'custom-resource-self-signed-certificate.yml',
                'custom-resource-update-cluster-prefix-list.yml',
                'custom-resource-update-cluster-settings.yml',
                'log-retention.yml',
                'solution-metrics-lambda-function.yml',
            ]
        },
        {
            'module_name': constants.MODULE_SHARED_STORAGE,
            'templates': [
                'efs-throughput-lambda.yml'
            ]
        },
        {
            'module_name': constants.MODULE_IDENTITY_PROVIDER,
            'templates': [
                'custom-resource-get-user-pool-client-secret.yml'
            ]
        },
        {
            'module_name': constants.MODULE_ANALYTICS,
            'templates': [
                'analytics-stream-processing-lambda.yml'
            ]
        },
        {
            'module_name': constants.MODULE_DIRECTORYSERVICE,
            'templates': [
                'openldap-server.yml'
            ]
        },
        {
            'module_name': constants.MODULE_CLUSTER_MANAGER,
            'templates': [
                'cluster-manager.yml'
            ]
        },
        {
            'module_name': constants.MODULE_SCHEDULER,
            'templates': [
                'scheduler.yml',
                'compute-node.yml',
                'spot-fleet-request.yml'
            ]
        },
        {
            'module_name': constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER,
            'templates': [
                'virtual-desktop-controller.yml',
                'virtual-desktop-dcv-broker.yml',
                'virtual-desktop-dcv-connection-gateway.yml',
                'virtual-desktop-dcv-host.yml',
                'controller-scheduled-event-transformer-lambda.yml',
                'controller-ssm-command-pass-role.yml'
            ]
        },
        {
            'module_name': constants.MODULE_BASTION_HOST,
            'templates': [
                'bastion-host.yml'
            ]
        }
    ]

    context = SocaCliContext(options=SocaContextOptions(
        cluster_name=cluster_name,
        aws_region=aws_region,
        aws_profile=aws_profile,
        enable_aws_client_provider=True,
        enable_aws_util=True
    ))

    for module in all_modules:
        module_name = module['module_name']
        if not context.config().is_module_enabled(module_name):
            continue
        module_id = context.config().get_module_id(module_name)

        context.print_title(f'ModuleName: {module_name}, ModuleId: {module_id}')
        templates = module['templates']
        for policy_template_name in templates:
            context.print(f'PolicyTemplate: {policy_template_name}')
            policy = AdministratorUtils.render_policy(
                policy_template_name=policy_template_name,
                cluster_name=cluster_name,
                module_id=module_id,
                config=context.config()
            )
            context.print_json(policy)
        context.new_line(2)


@task
def cdk_nag_scan(c, cluster_name, aws_region, aws_profile=None, module_name=None):
    # type: (Context, str, str, Optional[str], Optional[str]) -> None
    """
    perform cdk nag scan on all applicable cdk stacks
    """

    ignore_modules = [
        constants.MODULE_BOOTSTRAP,
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

        if current_module_name != constants.MODULE_CLUSTER and not cluster_deployed:
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
