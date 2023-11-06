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

from ideadatamodel import constants
from ideasdk.aws.opensearch.aws_opensearch_client import AwsOpenSearchClient

from ideavirtualdesktopcontroller.cli import build_cli_context

import click


@click.command(context_settings=constants.CLICK_SETTINGS, short_help='Execute commands to clean up before deleting module')
@click.option('--delete-databases', is_flag=True)
def app_module_clean_up(delete_databases: bool):
    """
    Utility hook to do any clean-up before the module is being deleted
    """
    if not delete_databases:
        return

    context = build_cli_context()
    os_client = AwsOpenSearchClient(context)
    os_client.delete_template(f'{context.cluster_name()}-{context.module_id()}_session_permission_template')
    os_client.delete_alias_and_index(
        name=context.config().get_string('virtual-desktop-controller.opensearch.session_permission.alias')
    )

    os_client.delete_template(f'{context.cluster_name()}-{context.module_id()}_user_sessions_template')
    os_client.delete_alias_and_index(
        name=context.config().get_string('virtual-desktop-controller.opensearch.dcv_session.alias')
    )
    os_client.delete_template(f'{context.cluster_name()}-{context.module_id()}_software_stack_template')
    os_client.delete_alias_and_index(
        name=context.config().get_string('virtual-desktop-controller.opensearch.software_stack.alias')
    )
