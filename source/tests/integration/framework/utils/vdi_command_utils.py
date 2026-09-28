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

import shlex

from res.utils import ssm_utils  # type: ignore[import]

# Markers echoed by the command wrapper so callers can tell success from failure
# without relying on the exit code (see run_command).
OK_MARKER = "__RES_OK__"
_FAIL = "__RES_FAIL__"


def run_command(instance_id: str, command: str) -> str:
    """
    Run a shell command in a Linux VDI over SSM and return its stdout.

    The command is wrapped so it always exits 0 — ssm_utils.wait_for_command
    raises on a non-zero exit, so wrapping lets callers inspect the result of
    commands that are expected to fail (e.g. permission-denied checks). Use
    command_succeeded() on the returned output to check the outcome.
    """
    wrapped = f"{{ {command} ; }} 2>/dev/null && echo {OK_MARKER} || echo {_FAIL}"
    result = ssm_utils.send_command(
        instance_ids=[instance_id],
        commands=[wrapped],
        base_os="linux",
        output_to_s3=False,
    )
    invocation = ssm_utils.wait_for_command(result["CommandId"], instance_id)
    return str(invocation.get("StandardOutputContent", ""))


def run_command_as(instance_id: str, user: str, command: str) -> str:
    """
    Run a command as ``user`` rather than root. SSM runs commands as root, so
    privilege checks (sudo, file access) must switch to the user first.
    """
    return run_command(instance_id, f"runuser -l {user} -c {shlex.quote(command)}")


def command_succeeded(output: str) -> bool:
    return OK_MARKER in output
