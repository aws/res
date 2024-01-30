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

import ideavirtualdesktopcontroller

from ideadatamodel.constants import CLICK_SETTINGS

from ideavirtualdesktopcontroller.cli.logs import logs

import sys
import click

from ideavirtualdesktopcontroller.cli.sessions import (
    batch_create_sessions,
    create_session,
    delete_session
)


@click.group(CLICK_SETTINGS)
@click.version_option(version=ideavirtualdesktopcontroller.__version__)
def main():
    """
    idea virtual desktop controller - manage virtual desktops in your cluster
    """
    pass


main.add_command(logs)
main.add_command(batch_create_sessions)
main.add_command(create_session)
main.add_command(delete_session)

# used only for local testing
if __name__ == '__main__':
    main(sys.argv[1:])
