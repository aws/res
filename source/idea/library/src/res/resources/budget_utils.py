#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import time
from typing import Any, Dict, Optional

from botocore.exceptions import ClientError
from res.clients.aws.aws_provider import AwsClientProvider
from res.resources import cluster_settings

_budget_cache = {}
_BUDGET_CACHE_TTL_SECONDS = 300  # 5 minutes


def get_budget(budget_name: str) -> Optional[Dict[str, Any]]:
    """
    Get budget information from AWS Budgets
    :param budget_name: name of the budget
    :return: dict with budget info or None if not found
    """

    aws_account_id = cluster_settings.get_setting("cluster.aws.account_id")
    cache_key = f"{aws_account_id}.{budget_name}"

    if cache_key in _budget_cache:
        cached_data, timestamp = _budget_cache[cache_key]
        if time.time() - timestamp < _BUDGET_CACHE_TTL_SECONDS:
            return cached_data

    try:
        aws_provider = AwsClientProvider()
        response = aws_provider.budgets().describe_budget(
            AccountId=aws_account_id, BudgetName=budget_name
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "NotFoundException":
            return None
        raise e

    response_budget = response.get("Budget", {})
    budget_limit = response_budget.get("BudgetLimit", {})
    calculated_spend = response_budget.get("CalculatedSpend", {})
    actual_spend = calculated_spend.get("ActualSpend", {})

    budget = {
        "budget_name": budget_name,
        "budget_limit": float(budget_limit.get("Amount", 0)),
        "actual_spend": float(actual_spend.get("Amount", 0)),
    }

    _budget_cache[cache_key] = (budget, time.time())
    return budget
