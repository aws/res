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

import ideaclustermanager
from ideadatamodel.constants import CLICK_SETTINGS

from ideaclustermanager.cli.logs import logs
from ideaclustermanager.cli.accounts import accounts
from ideaclustermanager.cli.groups import groups
from ideaclustermanager.cli.ldap_commands import ldap_commands
from ideaclustermanager.cli.module import app_module_clean_up

import sys
import click


@click.group(CLICK_SETTINGS)
@click.version_option(version=ideaclustermanager.__version__)
def main():
    """
    cluster manager
    """
    pass


main.add_command(logs)
main.add_command(accounts)
main.add_command(groups)
main.add_command(ldap_commands)
main.add_command(app_module_clean_up)

# used only for local testing
if __name__ == '__main__':
    main(sys.argv[1:])
