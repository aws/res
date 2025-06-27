#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
from typing import Any, Dict, Optional

import boto3
import res.constants as constants
from botocore.exceptions import ClientError
from res.utils import logging_utils

logger = logging_utils.get_logger("virtual-desktop-app")


def get_secret_string(secret_id: str) -> str:
    client = boto3.client(service_name="secretsmanager")
    result = client.get_secret_value(SecretId=secret_id)
    return result.get("SecretString", "")


def create_or_update_secret(
    cluster_name: str, module_name: str, key: str, secret_string_value: str
) -> Optional[str]:
    secret_name = f"{cluster_name}-{module_name}-{key}"
    client = boto3.client(service_name="secretsmanager")
    try:
        client.describe_secret(SecretId=secret_name)
        result = client.put_secret_value(
            SecretId=secret_name, SecretString=secret_string_value
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            result = client.create_secret(
                Name=secret_name,
                SecretString=secret_string_value,
                Tags=[
                    {"Key": constants.RES_TAG_ENVIRONMENT_NAME, "Value": cluster_name},
                    {"Key": constants.RES_TAG_MODULE_NAME, "Value": module_name},
                    {"Key": constants.RES_TAG_MODULE_ID, "Value": module_name},
                ],
            )
        else:
            raise e

    return result.get("ARN")


def sqs_send_message(
    payload: Dict[str, Any],
    queue_url: str,
    group_id: str,
    dedup_id: Optional[str] = None,
):

    sqs = boto3.client("sqs")
    request = {
        "QueueUrl": queue_url,
        "MessageBody": json.dumps(payload),
        "MessageGroupId": group_id,
    }
    if dedup_id:
        request["MessageDeduplicationId"] = dedup_id

    try:
        sqs.send_message(**request)
    except Exception as e:
        logger.info(f"Unexpected error sending SQS message: {str(e)}")
