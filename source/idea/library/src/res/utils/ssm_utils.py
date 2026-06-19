#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from functools import lru_cache
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from botocore.exceptions import ClientError, WaiterError
from res.clients.aws.aws_provider import AwsClientProvider
from res.constants import SSM_COMMAND_OUTPUT_BUCKET_KEY
from res.resources import cluster_settings
from res.utils import logging_utils

SSM_DEFAULT_BATCH_SIZE = 50

logger = logging_utils.get_logger("ssm-utils")


@lru_cache
def _get_ssm_client():
    return AwsClientProvider().ssm()


@lru_cache
def _get_s3_client():
    return AwsClientProvider().s3()


COMMAND_TIMEOUT_SECONDS = 60
COMMAND_POLL_INTERVAL_SECONDS = 2
LINUX_DOCUMENT_NAME = "AWS-RunShellScript"
WINDOWS_DOCUMENT_NAME = "AWS-RunPowerShellScript"


@lru_cache
def _get_ssm_output_bucket_name() -> str:
    return cluster_settings.get_setting(SSM_COMMAND_OUTPUT_BUCKET_KEY)


def send_command(
    instance_ids: List[str],
    commands: List[str],
    base_os: str,
    timeout_seconds: int = COMMAND_TIMEOUT_SECONDS,
    output_to_s3: bool = True,
) -> Dict[str, Any]:
    """Send a shell command to EC2 instances (up to 50) via SSM.

    When ``output_to_s3`` is True (default), command outputs are written to
    ``{cluster_name}-ssm-command-output-{region}-{account_id}``. Set to False
    for short-output commands where the inline ``StandardOutputContent``
    on ``get_command_invocation`` is sufficient.
    """
    document_name = (
        WINDOWS_DOCUMENT_NAME if base_os == "windows" else LINUX_DOCUMENT_NAME
    )
    kwargs: Dict[str, Any] = {
        "InstanceIds": instance_ids,
        "DocumentName": document_name,
        "Parameters": {"commands": commands},
        "TimeoutSeconds": timeout_seconds,
        "MaxErrors": "100%",
    }
    if output_to_s3:
        kwargs["OutputS3BucketName"] = _get_ssm_output_bucket_name()
    response = _get_ssm_client().send_command(**kwargs)
    return response["Command"]


def send_command_to_os_groups(
    os_groups: Dict[str, List[Dict[str, str]]],
    commands: Dict[str, str],
    batch_size: int = SSM_DEFAULT_BATCH_SIZE,
    output_to_s3: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Send batched SSM commands per OS group.

    Args:
        os_groups: Mapping of OS key to list of
            {"session_id", "instance_id"} dicts.
        commands: Mapping of OS key to the command string to run.
        batch_size: Max instances per SSM SendCommand call (up to 50).
        output_to_s3: Forwarded to ``send_command``.

    Returns (pending_commands, unsuccessful_list).
    """
    pending_commands: List[Dict[str, Any]] = []
    unsuccessful_list: List[Dict[str, Any]] = []

    for os_key, entries in os_groups.items():
        command = commands[os_key]
        for i in range(0, len(entries), batch_size):
            batch = entries[i : i + batch_size]
            instance_ids = [e["instance_id"] for e in batch]
            try:
                cmd = send_command(
                    instance_ids=instance_ids,
                    commands=[command],
                    base_os=os_key,
                    output_to_s3=output_to_s3,
                )
                command_id = cmd["CommandId"]
                for entry in batch:
                    pending_commands.append(
                        {
                            "session_id": entry["session_id"],
                            "command_id": command_id,
                            "instance_id": entry["instance_id"],
                        }
                    )
            except ClientError as e:
                error_msg = f"Failed to send SSM command batch: {e}"
                logger.error(error_msg)
                for entry in batch:
                    unsuccessful_list.append(
                        {"session_id": entry["session_id"], "failure_reason": error_msg}
                    )

    return pending_commands, unsuccessful_list


def collect_command_results(
    pending_commands: List[Dict[str, Any]],
    on_success: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Wait for each pending SSM command and collect per-command results.

    Args:
        pending_commands: dicts with keys ``session_id``, ``command_id``,
            ``instance_id``.
        on_success: optional callback ``(session_id, command_result) -> dict``
            to build each successful entry. Defaults to ``{"session_id": session_id}``
            when omitted. Exceptions raised by the callback are caught and
            surfaced as unsuccessful entries.

    Returns (successful_list, unsuccessful_list).
    """
    successful_list: List[Dict[str, Any]] = []
    unsuccessful_list: List[Dict[str, Any]] = []

    for command in pending_commands:
        sid = command["session_id"]
        try:
            result = wait_for_command(command["command_id"], command["instance_id"])
        except Exception as e:
            error_msg = f"SSM command for session_id: {sid} failed to execute: {e}"
            logger.error(error_msg)
            unsuccessful_list.append({"session_id": sid, "failure_reason": error_msg})
            continue

        status = result.get("Status", "Unknown")
        if status != "Success":
            error_msg = (
                f"SSM command for session_id: {sid} failed with status: {status}"
            )
            logger.error(error_msg)
            unsuccessful_list.append({"session_id": sid, "failure_reason": error_msg})
            continue

        if on_success is None:
            successful_list.append({"session_id": sid})
            continue

        try:
            successful_list.append(on_success(sid, result))
        except Exception as e:
            error_msg = (
                f"Failed to process SSM command output for session_id: {sid}: {e}"
            )
            logger.error(error_msg)
            unsuccessful_list.append({"session_id": sid, "failure_reason": error_msg})

    return successful_list, unsuccessful_list


def wait_for_command(
    command_id: str,
    instance_id: str,
    max_wait_time: int = COMMAND_TIMEOUT_SECONDS,
    wait_interval: int = COMMAND_POLL_INTERVAL_SECONDS,
) -> Dict[str, Any]:
    """Wait for an SSM command to reach a terminal status.

    Uses the boto3 ``CommandExecuted`` waiter, then returns the full
    ``get_command_invocation`` response which includes
    ``StandardOutputUrl`` for reading output from S3.
    """
    waiter = _get_ssm_client().get_waiter("command_executed")
    try:
        waiter.wait(
            CommandId=command_id,
            InstanceId=instance_id,
            WaiterConfig={
                "Delay": wait_interval,
                "MaxAttempts": max_wait_time // wait_interval,
            },
        )
    except WaiterError as e:
        invocation = _get_ssm_client().get_command_invocation(
            CommandId=command_id, InstanceId=instance_id
        )
        status = invocation.get("Status", "Unknown")
        if status in ("InProgress", "Pending", "Delayed"):
            raise TimeoutError(
                f"SSM command {command_id} on {instance_id} timed out after {max_wait_time}s"
            ) from e
        raise RuntimeError(
            f"SSM command {command_id} on {instance_id} failed with status: {status}"
        ) from e

    return _get_ssm_client().get_command_invocation(
        CommandId=command_id, InstanceId=instance_id
    )


def read_command_output_from_s3(s3_url: str) -> str:
    """Read SSM command output from S3 using the ``StandardOutputUrl``."""
    parsed = urlparse(s3_url)
    hostname = parsed.hostname or ""

    if hostname.startswith("s3.") or hostname.startswith("s3-"):
        # Path-style: https://s3.region.amazonaws.com/bucket/key
        path_parts = parsed.path.lstrip("/").split("/", 1)
        if len(path_parts) < 2 or not path_parts[1]:
            raise ValueError(f"Could not extract S3 key from URL: {s3_url}")
        bucket, key = path_parts[0], path_parts[1]
    else:
        # Virtual-hosted-style: https://bucket.s3.region.amazonaws.com/key
        dot_s3 = hostname.find(".s3.")
        if dot_s3 < 0:
            dot_s3 = hostname.find(".s3-")
        if dot_s3 <= 0:
            raise ValueError(f"Unrecognized S3 URL format: {s3_url}")
        bucket = hostname[:dot_s3]
        key = parsed.path.lstrip("/")
        if not key:
            raise ValueError(f"Could not extract S3 key from URL: {s3_url}")

    obj = _get_s3_client().get_object(Bucket=bucket, Key=key)
    return obj["Body"].read().decode("utf-8")
