#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

import boto3
from boto3.dynamodb.conditions import Attr, Key
from python_dynamodb_lock.python_dynamodb_lock import DynamoDBLockClient
from res.constants import ENVIRONMENT_NAME_KEY


@lru_cache
def table(table_name: str) -> Any:
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(f"{os.environ.get(ENVIRONMENT_NAME_KEY)}.{table_name}")


def list_items(table_name: str) -> List[Dict[str, Any]]:
    """
    Retrieve the items from DDB
    :return: list of items
    """
    response = table(table_name).scan()
    items: List[Dict[str, Any]] = response.get("Items", [])

    while "LastEvaluatedKey" in response:
        response = table(table_name).scan(
            ExclusiveStartKey=response["LastEvaluatedKey"]
        )
        items.extend(response.get("Items", []))

    return items


def create_item(
    table_name: str,
    item: Dict[str, Any],
    attribute_names_to_check: Optional[List[str]] = None,
) -> Dict[str, Any]:
    if attribute_names_to_check:
        condition = Attr(attribute_names_to_check[0]).not_exists()
        for attribute_name in attribute_names_to_check[1:]:
            condition += Attr(attribute_name).not_exists()  # type: ignore

        table(table_name).put_item(
            Item=item,
            ConditionExpression=condition,
        )
    else:
        table(table_name).put_item(
            Item=item,
        )
    return item


def delete_item(table_name: str, key: Dict[str, str]) -> None:
    table(table_name).delete_item(Key=key)


def get_item(table_name: str, key: Dict[str, str]) -> Optional[Dict[str, Any]]:
    item: Optional[Dict[str, Any]] = (
        table(table_name).get_item(Key=key).get("Item", None)
    )
    return item


def batch_get_items(
    table_name: str, keys: List[Dict[str, str]]
) -> List[Optional[Dict[str, Any]]]:
    """
    Retrieves multiple items from a DynamoDB table using batch_get_item.

    Args:
        table_name (str): The name of the DynamoDB table.
        keys (List[Dict[str, str]]): A list of primary key dictionaries for the items to retrieve.

    Returns:
        List[Optional[Dict[str, Any]]]: A list of retrieved items. Each item is either a dictionary
        with "key" and "value" or None if the item was not found.
    """
    dynamodb = boto3.resource("dynamodb")
    table_name = f"{os.environ.get('environment_name')}.{table_name}"

    # Use the DynamoDB resource to perform the batch_get_item operation
    response = dynamodb.meta.client.batch_get_item(
        RequestItems={table_name: {"Keys": keys}}
    )

    # Extract the items from the response
    items = response.get("Responses", {}).get(table_name, [])

    # Create a dictionary to map keys to items
    item_map = {
        item["key"]: {"key": item["key"], "value": item["value"]} for item in items
    }

    # Return items in the same order as the input keys, with None for missing items
    result = []
    for key in keys:
        result.append(item_map.get(key["key"]))

    return result


def query(
    table_name: str,
    attributes: Dict[str, Any],
    limit: Optional[int] = None,
    index_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    key_condition_expression = None
    for attribute_name, attribute_value in attributes.items():
        if not key_condition_expression:
            key_condition_expression = Key(attribute_name).eq(attribute_value)
        else:
            key_condition_expression += Key(attribute_name).eq(attribute_value)

    exclusive_start_key = None
    results: List[Dict[str, Any]] = []
    while True:
        query_params: Dict[str, Any] = {
            "KeyConditionExpression": key_condition_expression,
        }
        if exclusive_start_key:
            query_params["ExclusiveStartKey"] = exclusive_start_key
        if limit is not None:
            query_params["Limit"] = limit
        if index_name:
            query_params["IndexName"] = index_name

        query_result = table(table_name).query(
            **query_params,
        )
        results.extend(query_result.get("Items", []))
        exclusive_start_key = query_result.get("LastEvaluatedKey")
        if not exclusive_start_key:
            break

    return results


def update_item(
    table_name: str, key: Dict[str, str], item: Dict[str, Any], versioned: bool = False
) -> Dict[str, Any]:
    update_expression_tokens = []
    expression_attr_names = {}
    expression_attr_values = {}

    for attribute_name, attribute_value in item.items():
        if attribute_name in key:
            continue
        update_expression_tokens.append(f"#{attribute_name} = :{attribute_name}")
        expression_attr_names[f"#{attribute_name}"] = attribute_name
        expression_attr_values[f":{attribute_name}"] = attribute_value
    update_expression = "SET " + ", ".join(update_expression_tokens)

    if versioned:
        update_expression += " ADD #version :version"
        expression_attr_values[":version"] = 1
        expression_attr_names["#version"] = "version"

    result = table(table_name).update_item(
        Key=key,
        UpdateExpression=update_expression,
        ExpressionAttributeNames=expression_attr_names,
        ExpressionAttributeValues=expression_attr_values,
        ReturnValues="ALL_NEW",
    )

    updated_item: Dict[str, Any] = result["Attributes"]
    for attribute_name, attribute_value in key.items():
        updated_item[attribute_name] = attribute_value
    return updated_item


def scan(
    table_name: str, attributes: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    filter_expression = None
    if attributes:
        for attribute_name, attribute_value in attributes.items():
            if not filter_expression:
                filter_expression = Key(attribute_name).eq(attribute_value)
            else:
                filter_expression += Key(attribute_name).eq(attribute_value)

    exclusive_start_key = None
    results: List[Dict[str, Any]] = []
    while True:
        query_params: Dict[str, Any] = {}
        if filter_expression:
            query_params["FilterExpression"] = filter_expression

        if exclusive_start_key:
            query_params["ExclusiveStartKey"] = exclusive_start_key

        query_result = table(table_name).scan(
            **query_params,
        )
        results.extend(query_result.get("Items", []))
        exclusive_start_key = query_result.get("LastEvaluatedKey")
        if not exclusive_start_key:
            break

    return results


def get_distributed_lock_client(table_name: str) -> Any:
    dynamodb_resource = boto3.resource("dynamodb")
    return DynamoDBLockClient(
        dynamodb_resource=dynamodb_resource,
        table_name=f"{os.environ.get('environment_name')}.{table_name}",
    )


def is_table_empty(table_name: str) -> bool:
    query_result = table(table_name).scan(Limit=1).get("Items", [])
    return len(query_result) == 0
