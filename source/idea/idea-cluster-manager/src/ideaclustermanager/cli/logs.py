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
from ideadatamodel import constants, exceptions
from ideasdk.utils import EnvironmentUtils
from ideasdk.shell.log_tail import LogTail
from ideasdk.context import SocaCliContext

from typing import Optional, List, Dict, Union
import os.path
import click


class LogFinder:
    def __init__(self, kwargs: Dict, tokens: Optional[Union[str, List[str]]]):
        self.tokens = tokens
        self.kwargs = kwargs
        self._config = None
        self.files = []

    def add_log_files(self, files: list = None):
        if files is None:
            return
        for file in files:
            if file in self.files:
                continue
            if not os.path.isfile(file):
                click.echo(f'{file} not found. Ignoring')
                continue
            self.files.append(file)

    def find_applicable_logs(self):
        self.add_log_files(files=[
            os.path.join(EnvironmentUtils.idea_app_deploy_dir(required=True), 'logs', 'application.log')
        ])

    def print_logs(self):
        self.find_applicable_logs()

        if len(self.files) == 0:
            raise exceptions.general_exception(
                message='No log files files found.'
            )

        LogTail(
            context=SocaCliContext(),
            files=self.files,
            search_tokens=self.tokens,
            **self.kwargs
        ).invoke()


@click.command(context_settings=constants.CLICK_SETTINGS, short_help='print logs for a specified resource(s)')
@click.argument('tokens', nargs=-1)
@click.option('--tail', '-t', default=100, help='Lines of recent log file to display. Default: 100')
@click.option('--follow', '-f', is_flag=True, help='Specify if the logs should be streamed')
@click.option('--command', '-c', is_flag=True, help='Print the command, instead of printing logs.')
@click.option('--and', '-a', is_flag=True, help='Specify if the TOKENS should be ANDed instead of ORed.')
def logs(tokens, **kwargs):
    """
    idea logs

    \b
    Examples:

    \b
    # print last 100 lines of application logs
    $ resctl logs

    \b
    # print last 100 lines of application logs
    $ resctl logs -t 100

    \b
    # follow application logs
    $ resctl logs -f

    """
    LogFinder(
        tokens=tokens,
        kwargs=kwargs
    ).print_logs()
