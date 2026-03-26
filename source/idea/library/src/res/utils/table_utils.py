#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import base64
import json
import os
from decimal import Decimal
from enum import Enum
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import boto3
from boto3.dynamodb.conditions import And, Attr, Key
from python_dynamodb_lock.python_dynamodb_lock import DynamoDBLockClient
from res.constants import ENVIRONMENT_NAME_KEY


class FilterOperator(str, Enum):
    EQ = "eq"
    NE = "ne"
    CONTAINS = "contains"
    IS_IN = "is_in"


@lru_cache
def table(table_name: str) -> Any:
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(f"{os.environ.get(ENVIRONMENT_NAME_KEY)}.{table_name}")


def resolve_table_name(table_name: str) -> str:
    return f"{os.environ.get(ENVIRONMENT_NAME_KEY)}.{table_name}"


def get_table_kinesis_stream_name(table_name: str) -> str:
    resolved_table_name = resolve_table_name(table_name)
    return f"{resolved_table_name}-kinesis-stream"


def list_items(
    table_name: str, scan_filter: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve the items from DDB
    :param table_name: Name of the DynamoDB table
    :param scan_filter: Optional ScanFilter to apply to the scan operation
    :return: list of items
    """
    scan_params: Dict[str, Any] = {}
    if scan_filter is not None:
        scan_params["ScanFilter"] = scan_filter

    response = table(table_name).scan(**scan_params)
    items: List[Dict[str, Any]] = response.get("Items", [])

    while "LastEvaluatedKey" in response:
        scan_params["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        response = table(table_name).scan(**scan_params)
        items.extend(response.get("Items", []))

    return items


def list_items_paginated(
    table_name: str,
    filter_expression: Any = None,
    next_token: Optional[str] = None,
    limit: int = 100,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Retrieve one page of items from DDB with pagination support
    :param table_name: Name of the DynamoDB table
    :param filter_expression: Optional FilterExpression for modern filtering
    :param next_token: Pagination token from previous request
    :return: tuple of (list of items, next_token or None)
    """
    scan_params: Dict[str, Any] = {"Limit": limit}

    if filter_expression is not None:
        scan_params["FilterExpression"] = filter_expression

    if next_token is not None:
        scan_params["ExclusiveStartKey"] = json.loads(base64.b64decode(next_token))

    response = table(table_name).scan(**scan_params)
    items: List[Dict[str, Any]] = response.get("Items", [])

    response_next_token = None
    if "LastEvaluatedKey" in response:
        response_next_token = base64.b64encode(
            json.dumps(response["LastEvaluatedKey"]).encode()
        ).decode()

    return items, response_next_token


def create_item(
    table_name: str,
    item: Dict[str, Any],
    attribute_names_to_check: Optional[List[str]] = None,
) -> Dict[str, Any]:
    if attribute_names_to_check:
        condition = Attr(attribute_names_to_check[0]).not_exists()
        for attribute_name in attribute_names_to_check[1:]:
            condition = condition and Attr(attribute_name).not_exists()  # type: ignore

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


def get_item(table_name: str, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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


def check_and_convert_decimal_value(value: Any) -> Any:
    """
    since the ddb table resource returns all Number (N) types as decimals, additional processing is required to distinguish between int and float

    if value is of type Decimal, return it's applicable int or float value
    if value is a list of Decimals, converts all values in the list to applicable int of float

    see: https://github.com/boto/boto3/issues/369
    below implementation will not work for very large decimal numbers and exponent values for float
    :param value: Any
    :return: value with Decimal types converted to float of int if applicable
    """
    if value is None:
        return value
    updated_value = None
    if isinstance(value, Decimal):
        string_val = str(value)
        if "." in string_val:
            updated_value = float(string_val)
        else:
            updated_value = int(string_val)
    elif isinstance(value, list):
        list_entry = value
        if len(list_entry) > 0 and isinstance(list_entry[0], Decimal):
            updated_list = []
            for list_val in list_entry:
                string_val = str(list_val)
                if "." in string_val:
                    updated_list.append(float(string_val))
                else:
                    updated_list.append(int(string_val))
                updated_list.append(value)
            updated_value = updated_list
    if updated_value is None:
        return value
    return updated_value


def construct_date_range_filter(
    date_range_key: str, after: Optional[str] = None, before: Optional[str] = None
) -> Optional[Any]:
    """
    Construct a DynamoDB filter expression for date range filtering.

    Assumes inputs are already validated and after or before is not None

    :param date_range_key: The attribute name to filter on
    :param after: Start of the date range in milliseconds as string
    :param before: End of the date range in milliseconds as string
    :return: DynamoDB filter expression or None
    """
    if after and before:
        return Attr(date_range_key).between(int(after), int(before))
    elif after:
        return Attr(date_range_key).gte(int(after))
    else:
        return Attr(date_range_key).lte(int(before))


def construct_filter_expression(
    filter_specs: Dict[str, Any],
    date_range_key: Optional[str] = None,
    after: Optional[str] = None,
    before: Optional[str] = None,
) -> Any:
    """
    Construct DynamoDB filter expression from filter specifications
    :param filter_specs: Dict mapping attribute names to values or (FilterOperator, value) tuples
    :param date_range_key: Optional date range attribute name
    :param after: Optional start date for range filter
    :param before: Optional end date for range filter
    :return: DynamoDB filter expression or None
    """
    filter_conditions = []

    for attr_name, spec in filter_specs.items():
        if spec is None:
            continue
        if isinstance(spec, tuple):
            operator, value = spec
            if value is None:
                continue
            if operator == FilterOperator.EQ:
                filter_conditions.append(Attr(attr_name).eq(value))
            elif operator == FilterOperator.NE:
                filter_conditions.append(Attr(attr_name).ne(value))
            elif operator == FilterOperator.CONTAINS:
                filter_conditions.append(Attr(attr_name).contains(value))
            elif operator == FilterOperator.IS_IN:
                filter_conditions.append(Attr(attr_name).is_in(value))
        else:
            filter_conditions.append(Attr(attr_name).eq(spec))

    if date_range_key:
        filter_conditions.append(
            construct_date_range_filter(date_range_key, after, before)
        )

    if not filter_conditions:
        return None

    filter_expression = filter_conditions[0]
    for condition in filter_conditions[1:]:
        filter_expression = And(filter_expression, condition)

    return filter_expression
