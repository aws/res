#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import pytest
from boto3.dynamodb.conditions import And, Attr
from res.utils.table_utils import FilterOperator, construct_filter_expression


def test_construct_filter_expression_empty_filter_specs():
    result = construct_filter_expression({})
    assert result is None


def test_construct_filter_expression_none_values_ignored():
    result = construct_filter_expression({"attr1": None})
    assert result is None


def test_construct_filter_expression_simple_eq():
    result = construct_filter_expression({"status": "active"})
    expected = Attr("status").eq("active")
    assert result == expected


def test_construct_filter_expression_operator_eq():
    result = construct_filter_expression({"status": (FilterOperator.EQ, "active")})
    expected = Attr("status").eq("active")
    assert result == expected


def test_construct_filter_expression_operator_ne():
    result = construct_filter_expression({"status": (FilterOperator.NE, "inactive")})
    expected = Attr("status").ne("inactive")
    assert result == expected


def test_construct_filter_expression_operator_contains():
    result = construct_filter_expression({"name": (FilterOperator.CONTAINS, "test")})
    expected = Attr("name").contains("test")
    assert result == expected


def test_construct_filter_expression_operator_is_in():
    result = construct_filter_expression(
        {"status": (FilterOperator.IS_IN, ["active", "pending"])}
    )
    expected = Attr("status").is_in(["active", "pending"])
    assert result == expected


def test_construct_filter_expression_tuple_with_none_value():
    result = construct_filter_expression({"status": (FilterOperator.EQ, None)})
    assert result is None


def test_construct_filter_expression_multiple_conditions():
    result = construct_filter_expression({"status": "active", "type": "user"})
    expected = And(Attr("status").eq("active"), Attr("type").eq("user"))
    assert result == expected


def test_construct_filter_expression_mixed_operators():
    result = construct_filter_expression(
        {
            "status": (FilterOperator.EQ, "active"),
            "name": (FilterOperator.CONTAINS, "test"),
        }
    )
    expected = And(Attr("status").eq("active"), Attr("name").contains("test"))
    assert result == expected


def test_construct_filter_expression_with_date_range_both():
    result = construct_filter_expression(
        {"status": "active"},
        date_range_key="created_at",
        after="1000",
        before="2000",
    )
    expected = And(Attr("status").eq("active"), Attr("created_at").between(1000, 2000))
    assert result == expected


def test_construct_filter_expression_with_date_range_after_only():
    result = construct_filter_expression(
        {"status": "active"}, date_range_key="created_at", after="1000"
    )
    expected = And(Attr("status").eq("active"), Attr("created_at").gte(1000))
    assert result == expected


def test_construct_filter_expression_with_date_range_before_only():
    result = construct_filter_expression(
        {"status": "active"}, date_range_key="created_at", before="2000"
    )
    expected = And(Attr("status").eq("active"), Attr("created_at").lte(2000))
    assert result == expected


def test_construct_filter_expression_date_range_only():
    result = construct_filter_expression(
        {}, date_range_key="created_at", after="1000", before="2000"
    )
    expected = Attr("created_at").between(1000, 2000)
    assert result == expected


def test_construct_filter_expression_complex_multiple_conditions():
    result = construct_filter_expression(
        {
            "status": (FilterOperator.EQ, "active"),
            "type": "user",
            "name": (FilterOperator.CONTAINS, "test"),
        },
        date_range_key="created_at",
        after="1000",
    )
    expected = And(
        And(
            And(Attr("status").eq("active"), Attr("type").eq("user")),
            Attr("name").contains("test"),
        ),
        Attr("created_at").gte(1000),
    )
    assert result == expected
