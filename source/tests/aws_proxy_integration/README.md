# AWS Proxy API Tests

This directory contains a set of pytest tests for the AWS Proxy API. The tests are designed to ensure the correct behavior of the API when listing different resources and handling authentication and authorization.

## Prerequisites

Before running the tests, make sure you have the following prerequisites:

- Python 3.6 or later
- pytest
- requests

## Environment Variables

The tests require several environment variables to be set. Make sure to set the following variables before running the tests:

- `BASE_URL`: The base URL of the API (e.g., `https://res-new-external-alb-123456789.us-east-1.elb.amazonaws.com`).
- `ACCOUNT_ID`: The account ID to be included in the request body.
- `ADMIN_BEARER_TOKEN`: The admin Bearer token for authentication.
- `NON_ADMIN_BEARER_TOKEN`: The non-admin Bearer token for authentication.
- `REGION`: The region you would like to test the Proxy endpoints in. Note it does not need to be the region RES is deployed in.

## Running the Tests

To run the tests, navigate to directory `aws_proxy_integration` file and run the following command: `pytest`

pytest will automatically discover and run all the test functions defined in the test files.

## Security Considerations

The tests handle sensitive data like Bearer tokens by fetching them from environment variables. It's important to keep these environment variables secure and avoid hardcoding sensitive data in the code.

Additionally, the tests use the `verify=False` parameter when making API requests with `requests.post`. This parameter disables SSL/TLS certificate verification, which is not recommended for production environments. In a production environment, you should ensure that the API endpoint uses a valid SSL/TLS certificate and remove the `verify=False` parameter.
