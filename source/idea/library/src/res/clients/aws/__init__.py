#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
AWS Client Provider for RES Library

This module provides a centralized, optimized AWS client provider specifically
designed for RES usage in Lambda functions and other contexts. It offers:

- Client caching and connection pooling
- Thread-safe operations
- Lambda container reuse optimization
- Environment-aware configuration
- LocalStack support for local development

Usage:
    from res.clients.aws import get_aws_provider, get_ec2_client

    # Get full provider
    aws = get_aws_provider()
    ec2 = aws.ec2()

    # Or use convenience functions
    ec2_client = get_ec2_client()
"""

from .aws_client_provider import AwsClientProvider
from .aws_provider import (
    create_aws_provider_with_options,
    get_aws_provider,
    get_dynamodb_client,
    get_dynamodb_resource,
    get_ec2_client,
    get_route53_client,
    get_s3_client,
    get_ssm_client,
    get_sts_client,
    reset_aws_provider,
)
from .base import AWSClientProviderOptions, AwsServiceEndpoint
from .instance_metadata_util import InstanceMetadataUtil

__all__ = [
    # Main provider functions
    "get_aws_provider",
    "create_aws_provider_with_options",
    "reset_aws_provider",
    # Convenience client functions
    "get_ec2_client",
    "get_s3_client",
    "get_dynamodb_client",
    "get_dynamodb_resource",
    "get_ssm_client",
    "get_route53_client",
    "get_sts_client",
    # Classes for advanced usage
    "LambdaAwsClientProvider",
    "AWSClientProviderOptions",
    "AwsServiceEndpoint",
    "InstanceMetadataUtil",
]
