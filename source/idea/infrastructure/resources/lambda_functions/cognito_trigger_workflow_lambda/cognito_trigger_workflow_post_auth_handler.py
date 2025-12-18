#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import json
import os
from typing import Any, Dict

import boto3


def handle_event(event: Dict[str, Any], _: Any) -> Any:
    print(f"Login event: {event}")
    username = event["userName"]
    # Don't update SSO users or Cognito users that already have uid
    if event["request"]["userAttributes"][
        "cognito:user_status"
    ] == "EXTERNAL_PROVIDER" or user_has_uid_in_ddb(username):
        return event
    try:
        sqs_client = boto3.client("sqs")
        message = {"username": username}
        response = sqs_client.send_message(
            QueueUrl=os.environ.get("QUEUE_URL"),
            MessageBody=json.dumps(message),
            MessageGroupId="LOGGED_IN_USER_EVENT",
        )
        print(f"Result of SQS send message {response}")
    except Exception as e:
        print(f"Error in handling user event: {event}, error: {e}")
    return event


def user_has_uid_in_ddb(username: str) -> bool:
    table_name = f"{os.environ['CLUSTER_NAME']}.accounts.users"
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    user = table.get_item(Key={"username": username})

    return (
        user
        and "uid" in user["Item"]
        and user["Item"]["identity_source"] == os.environ["COGNITO_USER_IDP_TYPE"]
    )
