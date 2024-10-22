#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import boto3


def get_secret_string(secret_arn: str) -> str:
    sm_client = boto3.client("secretsmanager")
    result = sm_client.get_secret_value(SecretId=secret_arn)
    return result.get("SecretString", "")
