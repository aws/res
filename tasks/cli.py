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

import tasks.idea as idea

from invoke import task, Context
import sys
import runpy
from typing import List
import os


def invoke_cli(c: Context, app_name: str, module_name: str, invoke_args: List[str]):
    with c.cd(idea.props.scheduler_src):
        invoke_args.insert(0, app_name)
        sys.argv = invoke_args
        os.environ['RES_DEV_MODE'] = 'true'
        runpy.run_module(mod_name=module_name, run_name='__main__')


@task
def cluster_manager(c, args):
    # type: (Context, str) -> None
    """
    invoke cluster-manager cli
    """
    from ideasdk.utils import Utils
    tokens = Utils.from_json(Utils.base64_decode(args))
    invoke_cli(c, 'resctl', 'ideaclustermanager.cli.cli_main', tokens)

@task
def scheduler(c, args):
    # type: (Context, str) -> None
    """
    invoke virtual desktop controller cli
    """
    from ideasdk.utils import Utils
    tokens = Utils.from_json(Utils.base64_decode(args))
    invoke_cli(c, 'resctl', 'ideavirtualdesktopcontroller.cli.cli_main', tokens)

@task
def admin(c, args):
    # type: (Context, str) -> None
    """
    invoke administrator app cli
    """
    from ideasdk.utils import Utils
    tokens = Utils.from_json(Utils.base64_decode(args))
    invoke_cli(c, 'res-admin', 'ideaadministrator.app_main', tokens)
