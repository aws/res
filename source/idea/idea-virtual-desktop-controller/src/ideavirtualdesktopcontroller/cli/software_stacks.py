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

from ideadatamodel import (
    ReIndexSoftwareStacksRequest,
    ReIndexSoftwareStacksResponse
)
from ideadatamodel import constants

from ideavirtualdesktopcontroller.cli import build_cli_context

import click


@click.command(context_settings=constants.CLICK_SETTINGS, short_help='Re Index all software stacks to Open Search')
@click.argument('tokens', nargs=-1)
def reindex_software_stacks(tokens, **kwargs):

    context = build_cli_context()

    request = ReIndexSoftwareStacksRequest()
    response = context.unix_socket_client.invoke_alt(
        namespace='VirtualDesktopAdmin.ReIndexSoftwareStacks',
        payload=request,
        result_as=ReIndexSoftwareStacksResponse
    )
    # TODO: PrettyPrint response.
    # TODO: handle flag --destroy-and-recreate-index
    print(response)
