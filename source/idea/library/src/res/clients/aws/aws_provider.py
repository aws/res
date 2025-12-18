#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
from typing import Any, List, Optional

from .aws_client_provider import AwsClientProvider
from .base import AWSClientProviderOptions, AwsServiceEndpoint

# Global provider instance for lambda container reuse
_aws_provider: Optional[AwsClientProvider] = None


def get_aws_provider() -> AwsClientProvider:
    """
    Get or create a singleton AWS client provider for lambda usage.

    This leverages lambda container reuse to maintain cached clients
    across warm lambda invocations for optimal performance.
    """
    global _aws_provider

    if _aws_provider is None:
        # Get region from environment variables set by lambda runtime
        region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")

        # Create options for provider
        options = AWSClientProviderOptions(
            region=region,
            profile=None,  # Lambda uses IAM roles, no profile needed
            pricing_api_region="us-east-1",  # Pricing API only available in us-east-1
            endpoints=_get_custom_endpoints() if _is_local_dev() else None,
        )

        _aws_provider = AwsClientProvider(options)

    return _aws_provider


def create_aws_provider_with_options(
    options: AWSClientProviderOptions,
) -> AwsClientProvider:
    """
    Create a new AWS client provider with custom options.

    Use this when you need specific configuration that differs from the default.
    Note: This creates a new instance and doesn't use the global cache.
    """
    return AwsClientProvider(options)


def reset_aws_provider() -> None:
    """
    Reset the global AWS provider instance.

    Useful for testing or when you need to force recreation with new settings.
    """
    global _aws_provider
    _aws_provider = None


def _is_local_dev() -> bool:
    """
    Check if running in local development environment.
    """
    return (
        os.environ.get("AWS_SAM_LOCAL") == "true"
        or os.environ.get("LOCALSTACK_HOSTNAME") is not None
        or os.environ.get("LOCAL_DEV") == "true"
    )


def _get_custom_endpoints() -> List[AwsServiceEndpoint]:
    """
    Get custom endpoints for local development.

    Supports LocalStack and other local AWS emulation.
    """
    localstack_host = os.environ.get("LOCALSTACK_HOSTNAME", "localhost")
    localstack_port = os.environ.get("LOCALSTACK_PORT", "4566")
    localstack_url = f"http://{localstack_host}:{localstack_port}"

    # Return common services for LocalStack
    if os.environ.get("LOCALSTACK_HOSTNAME"):
        return [
            AwsServiceEndpoint("s3", localstack_url),
            AwsServiceEndpoint("ec2", localstack_url),
            AwsServiceEndpoint("dynamodb", localstack_url),
            AwsServiceEndpoint("ssm", localstack_url),
            AwsServiceEndpoint("sts", localstack_url),
            AwsServiceEndpoint("iam", localstack_url),
            AwsServiceEndpoint("route53", localstack_url),
            AwsServiceEndpoint("cloudformation", localstack_url),
        ]

    return []


# Convenience functions for common usage patterns


def get_ec2_client() -> Any:
    """Get EC2 client"""
    return get_aws_provider().ec2()


def get_s3_client() -> Any:
    """Get S3 client"""
    return get_aws_provider().s3()


def get_dynamodb_client() -> Any:
    """Get DynamoDB client"""
    return get_aws_provider().dynamodb()


def get_dynamodb_resource() -> Any:
    """Get DynamoDB resource (table interface)"""
    return get_aws_provider().dynamodb_table()


def get_ssm_client() -> Any:
    """Get Systems Manager client"""
    return get_aws_provider().ssm()


def get_route53_client() -> Any:
    """Get Route53 client"""
    return get_aws_provider().route53()


def get_sts_client() -> Any:
    """Get STS client"""
    return get_aws_provider().sts()


# Usage examples in docstring
"""
# Basic Usage Examples:

# 1. Get the default AWS provider
aws = get_aws_provider()
ec2 = aws.ec2()
s3 = aws.s3()

# 2. Use convenience functions
ec2_client = get_ec2_client()
dynamodb = get_dynamodb_resource()

# 3. Custom configuration
options = AWSClientProviderOptions(
    region="us-west-2",
    endpoints=[
        AwsServiceEndpoint("s3", "https://custom-s3-endpoint.com")
    ]
)
custom_aws = create_aws_provider_with_options(options)

# 4. Environment detection and metadata
aws = get_aws_provider()
if aws.is_running_in_ec2():
    region = aws.aws_region()
    account_id = aws.aws_account_id()

# 5. Credential management
if aws.are_credentials_expired():
    # Handle credential refresh if needed
    pass

# 6. Integration with existing lambda code:

# Replace this:
# ec2 = boto3.client("ec2")
# dynamodb = boto3.resource("dynamodb")
# ssm = boto3.client("ssm")

# With this:
# aws = get_aws_provider()
# ec2 = aws.ec2()
# dynamodb = aws.dynamodb_table()  # Resource interface
# ssm = aws.ssm()
"""
