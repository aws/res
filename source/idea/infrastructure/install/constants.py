#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from aws_cdk import aws_lambda

INSTALLER_ECR_REPO_NAME_SUFFIX = "-installer-ecr"
RES_COMMON_LAMBDA_RUNTIME = aws_lambda.Runtime.PYTHON_3_11
SHARED_RES_LIBRARY_LAMBDA_LAYER_RUNTIME = aws_lambda.Runtime.PYTHON_3_9
SHARED_RES_LIBRARY_LAMBDA_LAYER_NAME = "shared_res_library_layer"
API_PROXY_LAMBDA_LAYER_NAME = "api_proxy_dependencies"
