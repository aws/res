#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict

from aws_cdk import aws_lambda

RES_ECR_REPO_NAME_SUFFIX = "-res-ecr"
RES_COMMON_LAMBDA_RUNTIME = aws_lambda.Runtime.PYTHON_3_12
SHARED_RES_LIBRARY_LAMBDA_LAYER_NAME = "shared_res_library_layer"
API_PROXY_LAMBDA_LAYER_NAME = "api_proxy_dependencies"
OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX = " - Optional"
PROXY_URL_REGEX = "^((https|http):\/\/(?:(?:\d{1,3}\.){3}\d{1,3}|\[(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\]):(\d+))?$"

API_GATEWAY_CUSTOM_CREDENTIAL_BROKER_STAGE = "prod"
API_GATEWAY_CUSTOM_CREDENTIAL_BROKER_RESOURCE = "ObjectStorageTempCredentials"

API_GATEWAY_VDI_HELPER_STAGE = "prod"
API_GATEWAY_VDI_HELPER_RESOURCE = "VDIOperations"

OBJECT_STORAGE_CUSTOM_PROJECT_NAME_PREFIX = "PROJECT_NAME_PREFIX"
OBJECT_STORAGE_CUSTOM_PROJECT_NAME_AND_USERNAME_PREFIX = (
    "PROJECT_NAME_AND_USERNAME_PREFIX"
)
OBJECT_STORAGE_NO_CUSTOM_PREFIX = "NO_CUSTOM_PREFIX"

LOG_RETENTION_ROLE_NAME = "log-retention"

RES_TAG_PREFIX = "res:"
RES_TAG_ENVIRONMENT_NAME = RES_TAG_PREFIX + "EnvironmentName"
RES_TAG_MODULE_NAME = RES_TAG_PREFIX + "ModuleName"
RES_TAG_MODULE_ID = RES_TAG_PREFIX + "ModuleId"
RES_TAG_NODE_TYPE = RES_TAG_PREFIX + "NodeType"
RES_TAG_MODULE_VERSION = RES_TAG_PREFIX + "ModuleVersion"
RES_TAG_NAME = "Name"

NODE_TYPE_INFRA = "infra"
NODE_TYPE_APP = "app"
ARTIFACTS_BUCKET_PREFIX_NAME = "research-engineering-studio"

OS_AMAZONLINUX2 = "amazonlinux2"
OS_AMAZONLINUX2023 = "amzn2023"

# Caveat definitions
#
CAVEATS = dict[str, Any]()
#
# SSM service discovery namespace is not available
#
CAVEATS["SSM_DISCOVERY_RESTRICTED_REGION_LIST"] = [
    "af-south-1",
    "ap-northeast-3",
    "eu-south-1",
    "me-central-1",
    "me-south-1",
    "us-gov-east-1",
    "us-gov-west-1",
]
CAVEATS["SSM_DISCOVERY_FALLBACK_REGION"] = "us-east-1"


#
# Kinesis streams does not support StreamData in CloudFormation
#
CAVEATS["KINESIS_STREAMS_CLOUDFORMATION_UNSUPPORTED_STREAMMODEDETAILS_REGION_LIST"] = [
    "us-gov-east-1",
    "us-gov-west-1",
]

#
# Route53 cross-zone Alias records are not permitted
# (creates CNAME records instead)
#
CAVEATS["ROUTE53_CROSS_ZONE_ALIAS_RESTRICTED_REGION_LIST"] = [
    "us-gov-east-1",
    "us-gov-west-1",
]

#
# FIPS endpoint is default
#
CAVEATS["COGNITO_REQUIRE_FIPS_ENDPOINT_REGION_LIST"] = [
    "us-gov-east-1",
    "us-gov-west-1",
]

#
# Cognito Advanced Security is not available
#
CAVEATS["COGNITO_ADVANCED_SECURITY_UNAVAIL_REGION_LIST"] = [
    "us-gov-east-1",
    "us-gov-west-1",
]

#
# No SQS FIFO queues
#
CAVEATS["SQS_NO_FIFO_SUPPORT_REGION_LIST"] = ["us-gov-east-1", "us-gov-west-1"]

#
# No SNS FIFO queues
#
CAVEATS["SNS_NO_FIFO_SUPPORT_REGION_LIST"] = ["us-gov-east-1", "us-gov-west-1"]

MODULE_CLUSTER = "cluster"
MODULE_SHARED_STORAGE = "shared-storage"
MODULE_BASTION_HOST = "bastion-host"
MODULE_CLUSTER_MANAGER = "cluster-manager"
MODULE_ID_VDC_CONTROLLER = "vdc"
MODULE_NAME_VDC_CONTROLLER = "virtual-desktop-controller"

STORAGE_PROVIDER_S3_BUCKET = "s3_bucket"
