#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import json
import os
import random
from typing import Any, Dict, List

import boto3


def handle_event(event: Dict[str, Any], context: Any) -> Any:
    batch_item_failures = []
    sqs_batch_response = {}
    user_pool_id = os.getenv("USER_POOL_ID", "")

    existing_uids = get_uid_of_all_users_in_cognito(user_pool_id)
    username = ""
    for record in event["Records"]:
        try:
            username = json.loads(record["body"]).get("username")
            uid = generate_uid_for_user(existing_uids)
            cognito_idp = boto3.client("cognito-idp")
            cognito_idp.admin_update_user_attributes(
                UserPoolId=user_pool_id,
                Username=username,
                UserAttributes=[
                    {
                        "Name": os.environ["CUSTOM_UID_ATTRIBUTE"],
                        "Value": str(uid),
                    },
                ],
            )
            write_uid_attribute_to_ddb(username, str(uid))
            existing_uids.add(uid)
        except Exception as e:
            print(f"Failed to process user {username}")
            batch_item_failures.append({"itemIdentifier": record["messageId"]})

    # Reporting batch item failures
    # https://docs.aws.amazon.com/lambda/latest/dg/example_serverless_SQS_Lambda_batch_item_failures_section.html
    sqs_batch_response["batchItemFailures"] = batch_item_failures
    return sqs_batch_response


def write_uid_attribute_to_ddb(username: str, uid: str) -> None:
    table_name = f"{os.environ['CLUSTER_NAME']}.accounts.users"
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    table.update_item(
        Key={"username": username},
        UpdateExpression="SET #attr = :val",
        ExpressionAttributeNames={"#attr": "uid"},
        ExpressionAttributeValues={":val": uid},
    )


def generate_uid_for_user(existing_uids: set[int]) -> int:
    cognito_min_id_inclusive_str = os.getenv("COGNITO_MIN_ID_INCLUSIVE")
    if cognito_min_id_inclusive_str is None:
        raise ValueError("COGNITO_MIN_ID_INCLUSIVE needs to be defined")
    cognito_min_id_inclusive_int = int(cognito_min_id_inclusive_str)

    cognito_max_id_inclusive_str = os.getenv("COGNITO_MAX_ID_INCLUSIVE")
    if cognito_max_id_inclusive_str is None:
        raise ValueError("COGNITO_MAX_ID_INCLUSIVE needs to be defined")
    cognito_max_id_inclusive_int = int(cognito_max_id_inclusive_str)

    uid = random.randint(cognito_min_id_inclusive_int, cognito_max_id_inclusive_int)

    while uid in existing_uids:
        uid = random.randint(cognito_min_id_inclusive_int, cognito_max_id_inclusive_int)
    return uid


def get_uid_of_all_users_in_cognito(user_pool_id: str) -> set[int]:
    uids = set()
    cognito_idp = boto3.client("cognito-idp")
    paginator = cognito_idp.get_paginator("list_users")

    custom_uid_attribute = os.getenv("CUSTOM_UID_ATTRIBUTE")
    for page in paginator.paginate(UserPoolId=user_pool_id):
        for user in page["Users"]:
            # Find the 'custom:uid' attribute for the user
            uid_attribute = next(
                (
                    attr
                    for attr in user["Attributes"]
                    if attr["Name"] == custom_uid_attribute
                ),
                None,
            )

            # If the 'custom:uid' attribute exists, add it to the set
            if uid_attribute:
                uids.add(int(uid_attribute["Value"]))

    return uids
