#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from enum import Enum
from typing import Any, Dict

import boto3


class RequestType(str, Enum):
    CREATE = "Create"
    UPDATE = "Update"
    DELETE = "Delete"


def delete_dcv_broker_tables(event: Dict[str, Any], _: Any) -> None:
    request_type = event["RequestType"]
    if request_type == RequestType.DELETE:
        environmentName = event["ResourceProperties"]["environment_name"]
        client = boto3.client("dynamodb")
        dcvBrokerTables = []
        lastEvaluatedTableName = None
        while True:
            if not lastEvaluatedTableName:
                response = client.list_tables()
            else:
                response = client.list_tables(
                    ExclusiveStartTableName=lastEvaluatedTableName
                )
            dcvBrokerTables.extend(
                [
                    table
                    for table in response["TableNames"]
                    if table.startswith(f"{environmentName}.vdc.dcv-broker")
                ]
            )
            lastEvaluatedTableName = response.get("LastEvaluatedTableName", None)
            if not lastEvaluatedTableName:
                break
        print("Tables to be deleted: " + str(dcvBrokerTables))
        for table in dcvBrokerTables:
            client.delete_table(TableName=table)
    return
