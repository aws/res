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
import click


@click.command(context_settings=constants.CLICK_SETTINGS, short_help='Execute commands to clean up before deleting module')
@click.option('--delete-databases', is_flag=True)
def app_module_clean_up(delete_databases: bool):
    """
    Utility hook to do any clean-up before the module is being deleted
    """
    pass
