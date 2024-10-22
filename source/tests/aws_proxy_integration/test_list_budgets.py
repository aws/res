import os
from typing import Any

import pytest
import requests

from tests.aws_proxy_integration.util import post_api_response, post_api_response_data


@pytest.fixture
def api_response(url_path: str, headers: Any, request_body: Any) -> Any:
    """
    Makes an API request with the provided headers and request body, and returns the JSON response data.
    """
    return post_api_response_data(url_path, headers, request_body)


@pytest.fixture
def api_response_without_token(url_path: str, request_body: Any) -> Any:
    """
    Makes an API request without a Bearer token in the headers.
    """
    headers = {
        "X-Amz-Target": "AWSBudgetServiceGateway.DescribeBudgets",
        "Content-Type": "application/json",
    }
    return post_api_response(url_path, headers, request_body)


@pytest.fixture
def api_response_with_invalid_token(
    url_path: str, headers_with_invalid_token: Any, request_body: Any
) -> Any:
    """
    Makes an API request with an invalid Bearer token in the headers.
    """
    return post_api_response(url_path, headers_with_invalid_token, request_body)


@pytest.fixture
def api_response_with_non_admin_token(
    url_path: str, headers_with_non_admin_token: Any, request_body: Any
) -> Any:
    """
    Makes an API request with a non-admin Bearer token in the headers.
    """
    return post_api_response(url_path, headers_with_non_admin_token, request_body)


@pytest.fixture
def api_response_with_create_budgets_target(
    url_path: str,
    headers_with_create_budgets_target: Any,
    create_budget_request_body: Any,
) -> Any:
    """
    Makes an API request with the `X-Amz-Target` header set to `AWSBudgetServiceGateway.CreateBudget`
    """
    base_url = os.environ.get("BASE_URL")
    if not base_url:
        raise ValueError("BASE_URL environment variable is not set")

    url = f"{base_url}{url_path}"
    response = requests.post(
        url,
        headers=headers_with_create_budgets_target,
        json=create_budget_request_body,
        verify=False,
    )
    return response


@pytest.fixture
def url_path() -> str:
    return "/awsproxy/budgets"


@pytest.fixture
def headers(admin_bearer_token: str) -> Any:
    return {
        "X-Amz-Target": "AWSBudgetServiceGateway.DescribeBudgets",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_bearer_token}",
    }


@pytest.fixture
def headers_with_invalid_token() -> Any:
    return {
        "X-Amz-Target": "AWSBudgetServiceGateway.DescribeBudgets",
        "Content-Type": "application/json",
        "Authorization": "Bearer invalid_token",
    }


@pytest.fixture
def headers_with_non_admin_token(non_admin_bearer_token: str) -> Any:
    return {
        "X-Amz-Target": "AWSBudgetServiceGateway.DescribeBudgets",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {non_admin_bearer_token}",
    }


@pytest.fixture
def headers_with_create_budgets_target(admin_bearer_token: str) -> Any:
    return {
        "X-Amz-Target": "AWSBudgetServiceGateway.CreateBudgets",
        "Content-Type": "application/x-amz-json-1.1",
        "Authorization": f"Bearer {admin_bearer_token}",
    }


@pytest.fixture
def request_body(account_id: str) -> Any:
    return {
        "AccountId": account_id,
    }


@pytest.fixture
def create_budget_request_body(account_id: str) -> Any:
    return {
        "AccountId": account_id,
        "Budget": {
            "BudgetName": "Example Budget",
            "BudgetType": "COST",
            "TimeUnit": "MONTHLY",
            "BudgetLimit": {"Amount": "100", "Unit": "USD"},
            "CostFilters": {"Service": "Amazon Elastic Compute Cloud - Compute"},
        },
    }


@pytest.fixture
def account_id() -> str:
    """
    Retrieves the AWS account ID from the `ACCOUNT_ID` environment variable.
    """
    account_id = os.environ.get("ACCOUNT_ID")
    if not account_id:
        raise ValueError("ACCOUNT_ID environment variable is not set")
    return account_id


@pytest.fixture
def admin_bearer_token() -> str:
    """
    Retrieves the admin Bearer token from the `ADMIN_BEARER_TOKEN` environment variable.
    """
    admin_bearer_token = os.environ.get("ADMIN_BEARER_TOKEN")
    if not admin_bearer_token:
        raise ValueError("ADMIN_BEARER_TOKEN environment variable is not set")
    return admin_bearer_token


@pytest.fixture
def non_admin_bearer_token() -> str:
    """
    Retrieves the non-admin Bearer token from the `NON_ADMIN_BEARER_TOKEN` environment variable.
    """
    non_admin_bearer_token = os.environ.get("NON_ADMIN_BEARER_TOKEN")
    if not non_admin_bearer_token:
        raise ValueError("NON_ADMIN_BEARER_TOKEN environment variable is not set")
    return non_admin_bearer_token


def test_budgets_response(api_response: Any) -> None:
    """
    Test the structure of the API response for listing budgets.

    Args:
        api_response (Any): The API response to be tested.

    Raises:
        AssertionError: If the response structure is invalid.
    """
    assert "Budgets" in api_response, "Invalid API response: 'Budgets' key not found"

    budgets = api_response["Budgets"]
    assert isinstance(
        budgets, list
    ), "Invalid API response: 'Budgets' value is not a list"


def test_missing_bearer_token(api_response_without_token: Any) -> None:
    """
    Test the behavior when a bearer token is missing in the request to list budgets.

    This test case verifies that the API correctly handles and responds to requests
    without a valid bearer token, ensuring proper authentication checks are in place.

    Expected behavior:
    - The request should be rejected
    - An appropriate error response should be returned (e.g., 401 Unauthorized)
    - No budget information should be exposed to unauthenticated requests
    """
    assert (
        api_response_without_token.status_code == 401
    ), "Expected 401 Unauthorized status code"


def test_invalid_bearer_token(api_response_with_invalid_token: Any) -> None:
    """
    Test the behavior when an invalid bearer token is provided in the request to list budgets.

    This test case verifies that the API correctly handles and responds to requests
    with an invalid bearer token, ensuring proper authentication validation is in place.

    Expected behavior:
    - The request should be rejected
    - An appropriate error response should be returned (401 Unauthorized)
    - No budget information should be exposed to requests with invalid authentication
    """
    assert (
        api_response_with_invalid_token.status_code == 401
    ), "Expected 401 Unauthorized status code"


def test_non_admin_bearer_token(api_response_with_non_admin_token: Any) -> None:
    """
    Test the API's response when a non-admin user attempts to list budgets.

    This test case verifies that the API correctly handles requests from authenticated
    users who do not have admin privileges. It ensures that proper access control is
    in place to restrict budget information to authorized personnel only.

    Expected behavior:
    - The request should be authenticated but denied due to insufficient permissions
    - A 403 Forbidden status code should be returned
    - An appropriate error message should be included in the response
    - No budget information should be exposed to non-admin users
    """
    assert (
        api_response_with_non_admin_token.status_code == 403
    ), "Expected 403 Forbidden status code"
    assert (
        "Forbidden" in api_response_with_non_admin_token.text
    ), "Expected AccessDeniedException in response"


def test_create_budgets_bad_request(
    api_response_with_create_budgets_target: Any,
) -> None:
    """
    Test the request is rejected when creating budget

    The proxy API is a read only API and does not allow resource creation
    This test case verifies that the API correctly relays reject from AWS Services.
    AWS Budget create throw AccessDenied as a 400 error code
    See official documentation https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/API_budgets_CreateBudget.html#API_budgets_CreateBudget_Errors

    Expected behavior:
    - The request should be rejected
    - A 400 Bad Request status code should be returned
    - No budget should be created as a result of this request
    """
    assert (
        api_response_with_create_budgets_target.status_code == 400
    ), "Expected 400 Bad Request status code"
