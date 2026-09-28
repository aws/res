#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
from typing import Any, Dict, List, Optional

from res.constants import ENVIRONMENT_NAME_KEY, MODULE_ID_VDC
from res.resources import cluster_settings
from res.utils import ssm_utils, table_utils

SSM_COMMANDS_TABLE_NAME = "vdc.controller.ssm-commands"
SSM_COMMANDS_DB_HASH_KEY = "command_id"
SSM_COMMANDS_DB_COMMAND_TYPE_KEY = "command_type"
SSM_COMMANDS_DB_ADDITIONAL_PAYLOAD_KEY = "additional_payload"

SNS_TOPIC_ARN_KEY = "vdc.ssm_commands_sns_topic_arn"
SERVICE_ROLE_ARN_KEY = "vdc.ssm_commands_pass_role_arn"

CPU_UTILIZATION_CHECK_STOP_SCHEDULED_SESSION = (
    "CPU_UTILIZATION_CHECK_STOP_SCHEDULED_SESSION"
)

_WINDOWS_CPU_PROBE = [
    '$CPUAveragePerformanceLast10Secs = (GET-COUNTER -Counter "\\Processor(_Total)\\% Processor Time" -SampleInterval 2 -MaxSamples 5 |select -ExpandProperty countersamples | select -ExpandProperty cookedvalue | Measure-Object -Average).average',
    "$output = @{}",
    '$output["CPUAveragePerformanceLast10Secs"] = $CPUAveragePerformanceLast10Secs',
    "$output | ConvertTo-Json",
]

_LINUX_CPU_PROBE = [
    "CPUAveragePerformanceLast10Secs=$(top -d 5 -b -n2 | grep 'Cpu(s)' |tail -n 1 | awk '{print $2 + $4}')",
    "echo '{\"CPUAveragePerformanceLast10Secs\": '\"$CPUAveragePerformanceLast10Secs\"'}'",
]


def send_ssm_command(
    instance_id: str,
    commands: List[str],
    base_os: str,
    command_type: str,
    additional_payload: Dict[str, Any],
    cloud_watch_log_group: Optional[str] = None,
    output_s3_key_prefix: Optional[str] = None,
) -> str:
    """Send an SSM command with SNS notification and store it in DDB.

    Returns the command ID.
    """
    sns_topic_arn = cluster_settings.get_setting(SNS_TOPIC_ARN_KEY)
    service_role_arn = cluster_settings.get_setting(SERVICE_ROLE_ARN_KEY)

    notification_config = None
    if sns_topic_arn and service_role_arn:
        notification_config = {
            "NotificationArn": sns_topic_arn,
            "NotificationEvents": ["All"],
            "NotificationType": "Invocation",
        }

    ssm_result = ssm_utils.send_command(
        instance_ids=[instance_id],
        commands=commands,
        base_os=base_os,
        notification_config=notification_config,
        service_role_arn=service_role_arn,
        cloud_watch_log_group=cloud_watch_log_group,
        output_s3_key_prefix=output_s3_key_prefix,
    )

    command_id = ssm_result.get("CommandId", "")
    create_ssm_command(
        command_id=command_id,
        command_type=command_type,
        additional_payload=additional_payload,
    )
    return command_id


def create_ssm_command(
    command_id: str, command_type: str, additional_payload: Dict[str, Any]
) -> Dict[str, Any]:
    """Store an SSM command record in DDB for the VDC event handler to process."""
    item = {
        SSM_COMMANDS_DB_HASH_KEY: command_id,
        SSM_COMMANDS_DB_COMMAND_TYPE_KEY: command_type,
        SSM_COMMANDS_DB_ADDITIONAL_PAYLOAD_KEY: additional_payload,
    }
    return table_utils.create_item(table_name=SSM_COMMANDS_TABLE_NAME, item=item)


def submit_ssm_command_to_get_cpu_utilization(
    instance_id: str,
    idea_session_id: str,
    idea_session_owner: str,
    base_os: str,
) -> str:
    """Submit an SSM command to probe CPU utilization on a VDI instance."""
    cluster_name = os.environ[ENVIRONMENT_NAME_KEY]
    commands = _WINDOWS_CPU_PROBE if base_os == "windows" else _LINUX_CPU_PROBE
    log_path = (
        f"/{cluster_name}/{MODULE_ID_VDC}/dcv-session/{idea_session_id}/cpu-utilization"
    )

    return send_ssm_command(
        instance_id=instance_id,
        commands=commands,
        base_os=base_os,
        command_type=CPU_UTILIZATION_CHECK_STOP_SCHEDULED_SESSION,
        additional_payload={
            "idea_session_id": idea_session_id,
            "idea_session_owner": idea_session_owner,
            "instance_id": instance_id,
        },
        cloud_watch_log_group=log_path,
        output_s3_key_prefix=log_path,
    )


def get_ssm_command(command_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve an SSM command record from DDB by command_id."""
    if not command_id:
        return None
    return table_utils.get_item(
        table_name=SSM_COMMANDS_TABLE_NAME,
        key={SSM_COMMANDS_DB_HASH_KEY: command_id},
    )


def delete_ssm_command(command_id: str) -> None:
    """Delete an SSM command record from DDB."""
    if not command_id:
        return
    table_utils.delete_item(
        table_name=SSM_COMMANDS_TABLE_NAME,
        key={SSM_COMMANDS_DB_HASH_KEY: command_id},
    )
