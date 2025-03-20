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
from typing import Any

from tests.integration.framework.utils.remote_command_runner import (
    EC2InstancePlatform,
    RemoteCommandRunner,
)

logger = logging.getLogger(__name__)


def grep_sssd_config_from_instance(
    region: str, instance_id: str, platform: EC2InstancePlatform, key: str
) -> Any:
    remote_command_runner = RemoteCommandRunner(region, platform)
    commands = [
        f"sudo grep '^{key}' /etc/sssd/sssd.conf | awk -F '=' '{{print $2}}' | tr -d ' \\r\\n'"
    ]
    value = remote_command_runner.run(instance_id, commands)
    logger.info(f"Got sssd config {key} value {value} from instance {instance_id}")
    return value


def check_sssd_config_field(
    region: str,
    instance_id: str,
    platform: EC2InstancePlatform,
    key: str,
    expected_value: str,
) -> None:
    sssd_config_value = grep_sssd_config_from_instance(
        region, instance_id, platform, key
    )
    assert (
        sssd_config_value == expected_value
    ), f"Expect SSSD config {key} to be {expected_value}, but got {sssd_config_value} from instance {instance_id}"
