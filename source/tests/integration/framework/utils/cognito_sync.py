#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import os

import boto3
import res.exceptions as exceptions  # type: ignore
from res.resources import cluster_settings  # type: ignore

from ideadatamodel import constants  # type: ignore


def cognito_sync() -> None:
    lambda_client = boto3.client("lambda")

    try:
        response = lambda_client.invoke(
            FunctionName=f'{os.environ["environment_name"]}_cognito-sync-lambda',
            InvocationType="RequestResponse",
            Payload=json.dumps({}),
        )

        if "FunctionError" in response:
            assert (
                False
            ), f"Failed to sync users and groups from Cognito: {response['FunctionError']}"
    except Exception as e:
        assert False, f"Failed to sync users and groups from Cognito: {e}"
