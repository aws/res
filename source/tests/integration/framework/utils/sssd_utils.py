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

import logging
import time
from typing import Any

from botocore.exceptions import ClientError
from res.utils import ssm_utils  # type: ignore[import]

MAX_RETRIES = 3
RETRY_INTERVAL = 20

logger = logging.getLogger(__name__)


def grep_sssd_config_from_instance(instance_id: str, base_os: str, key: str) -> Any:
    commands = [
        f"sudo grep '^{key}' /etc/sssd/sssd.conf | awk -F '=' '{{print $2}}' | tr -d ' \\r\\n'"
    ]
    result = ssm_utils.send_command(
        instance_ids=[instance_id],
        commands=commands,
        base_os=base_os,
        output_to_s3=False,
    )
    invocation = ssm_utils.wait_for_command(result["CommandId"], instance_id)
    value = invocation.get("StandardOutputContent", "")
    logger.info(f"Got sssd config {key} value {value} from instance {instance_id}")
    return value


def check_sssd_config_field(
    instance_id: str,
    base_os: str,
    key: str,
    expected_value: str,
) -> None:
    sssd_config_value = ""
    last_error = None
    num_retries = 0
    while num_retries < MAX_RETRIES:
        try:
            sssd_config_value = grep_sssd_config_from_instance(
                instance_id, base_os, key
            )
            last_error = None
            if sssd_config_value == expected_value:
                return
        except (TimeoutError, ClientError) as e:
            # SSM commands can fail transiently when SSSD is restarting on the
            # instance (the restart is triggered by the settings update that
            # this test is validating).  Retry instead of failing immediately.
            logger.warning(
                f"Attempt {num_retries + 1}/{MAX_RETRIES} failed to read "
                f"SSSD config from {instance_id}: {e}"
            )
            last_error = e

        num_retries += 1
        time.sleep(RETRY_INTERVAL)

    if last_error is not None:
        raise last_error

    assert (
        False
    ), f"Expect SSSD config {key} to be {expected_value}, but got {sssd_config_value} from instance {instance_id}"
