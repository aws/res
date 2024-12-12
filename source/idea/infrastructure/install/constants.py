#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from aws_cdk import aws_lambda

RES_ECR_REPO_NAME_SUFFIX = "-res-ecr"
RES_COMMON_LAMBDA_RUNTIME = aws_lambda.Runtime.PYTHON_3_11
RES_BACKEND_LAMBDA_RUNTIME = aws_lambda.Runtime.PYTHON_3_12
RES_ADMINISTRATOR_LAMBDA_RUNTIME = aws_lambda.Runtime.PYTHON_3_9
SHARED_RES_LIBRARY_LAMBDA_LAYER_NAME = "shared_res_library_layer"
API_PROXY_LAMBDA_LAYER_NAME = "api_proxy_dependencies"
OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX = " - Optional"
PROXY_URL_REGEX = "^((https|http):\/\/(?:(?:\d{1,3}\.){3}\d{1,3}|\[(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\]):(\d+))?$"
