#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from unittest.mock import MagicMock, Mock, patch

from botocore.exceptions import ClientError
from res.resources import budget_utils


class TestBudgetsGetBudget:
    """Test budgets_get_budget function."""

    @patch("res.resources.budget_utils.AwsClientProvider")
    @patch("res.resources.budget_utils.cluster_settings.get_setting")
    def test_budgets_get_budget_successfully_retrieves_budget(
        self, mock_get_setting, mock_aws_provider
    ):
        """Test successfully retrieving budget information."""
        mock_get_setting.return_value = "123456789012"
        mock_budgets_client = Mock()
        mock_aws_provider.return_value.budgets.return_value = mock_budgets_client
        mock_budgets_client.describe_budget.return_value = {
            "Budget": {
                "BudgetName": "test-budget",
                "BudgetLimit": {"Amount": "1000", "Unit": "USD"},
                "CalculatedSpend": {"ActualSpend": {"Amount": "500", "Unit": "USD"}},
            }
        }

        result = budget_utils.get_budget("test-budget")

        assert result is not None
        assert result["budget_limit"] == 1000.0
        assert result["actual_spend"] == 500.0

    @patch("res.resources.budget_utils.AwsClientProvider")
    @patch("res.resources.budget_utils.cluster_settings.get_setting")
    def test_budgets_get_budget_budget_not_found_returns_none(
        self, mock_get_setting, mock_aws_provider
    ):
        """Test that budget not found returns None."""
        mock_get_setting.return_value = "123456789012"
        mock_budgets_client = Mock()
        mock_aws_provider.return_value.budgets.return_value = mock_budgets_client

        error_response = {
            "Error": {"Code": "NotFoundException", "Message": "Budget not found"}
        }
        mock_budgets_client.describe_budget.side_effect = ClientError(
            error_response, "DescribeBudget"
        )

        result = budget_utils.get_budget("nonexistent-budget")

        assert result is None
