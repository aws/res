#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

import boto3
from boto3.dynamodb.conditions import Attr, Key


@lru_cache
def table(table_name: str) -> Any:
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(f"{os.environ.get('environment_name')}.{table_name}")


def list_table(table_name: str) -> List[Dict[str, Any]]:
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
    table_name: str, key: Dict[str, str], item: Dict[str, Any]
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

    result = table(table_name).update_item(
        Key=key,
        UpdateExpression="SET " + ", ".join(update_expression_tokens),
        ExpressionAttributeNames=expression_attr_names,
        ExpressionAttributeValues=expression_attr_values,
        ReturnValues="ALL_NEW",
    )

    updated_item: Dict[str, Any] = result["Attributes"]
    for attribute_name, attribute_value in key.items():
        updated_item[attribute_name] = attribute_value
    return updated_item


def scan(table_name: str, attributes: Dict[str, Any]) -> List[Dict[str, Any]]:
    filter_expression = None
    for attribute_name, attribute_value in attributes.items():
        if not filter_expression:
            filter_expression = Key(attribute_name).eq(attribute_value)
        else:
            filter_expression += Key(attribute_name).eq(attribute_value)

    exclusive_start_key = None
    results: List[Dict[str, Any]] = []
    while True:
        query_params: Dict[str, Any] = {
            "FilterExpression": filter_expression,
        }
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
