#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from threading import RLock
from typing import Any, Dict, List, Optional, Set

import botocore.exceptions
from botocore.client import Config

from .base import (
    AWSClientProviderOptions,
    AwsClientProviderProtocol,
    AwsServiceEndpoint,
    general_exception,
)
from .instance_metadata_util import InstanceMetadataUtil

AWS_CLIENT_S3 = "s3"
AWS_CLIENT_EC2 = "ec2"
AWS_CLIENT_LAMBDA = "lambda"
AWS_CLIENT_ELBV2 = "elbv2"
AWS_CLIENT_IAM = "iam"
AWS_CLIENT_CLOUDFORMATION = "cloudformation"
AWS_CLIENT_AUTOSCALING = "autoscaling"
AWS_CLIENT_APPLICATION_AUTOSCALING = "application-autoscaling"
AWS_CLIENT_SECRETSMANAGER = "secretsmanager"
AWS_CLIENT_BUDGETS = "budgets"
AWS_CLIENT_SES = "ses"
AWS_CLIENT_SQS = "sqs"
AWS_CLIENT_SERVICE_QUOTAS = "service-quotas"
AWS_CLIENT_PRICING = "pricing"
AWS_CLIENT_CLOUDWATCH = "cloudwatch"
AWS_CLIENT_CLOUDWATCHLOGS = "logs"
AWS_CLIENT_ES = "es"
AWS_CLIENT_DS = "ds"
AWS_CLIENT_FSX = "fsx"
AWS_CLIENT_EFS = "efs"
AWS_CLIENT_STS = "sts"
AWS_CLIENT_ROUTE53 = "route53"
AWS_CLIENT_EVENTS = "events"
AWS_CLIENT_SSM = "ssm"
AWS_CLIENT_ACM = "acm"
AWS_CLIENT_DYNAMODB = "dynamodb"
AWS_CLIENT_COGNITO_IDP = "cognito-idp"
AWS_CLIENT_KINESIS_STREAM = "kinesis"
AWS_RESOURCE_DYNAMODB_TABLE = "dynamodb.table"
AWS_RESOURCE_S3_BUCKET = "s3.bucket"
AWS_CLIENT_RESOURCE_GROUPS_TAGGING_API = "resourcegroupstaggingapi"
AWS_CLIENT_BACKUP = "backup"

SUPPORTED_CLIENTS = {
    AWS_CLIENT_S3,
    AWS_RESOURCE_S3_BUCKET,
    AWS_CLIENT_EC2,
    AWS_CLIENT_LAMBDA,
    AWS_CLIENT_ELBV2,
    AWS_CLIENT_IAM,
    AWS_CLIENT_CLOUDFORMATION,
    AWS_CLIENT_APPLICATION_AUTOSCALING,
    AWS_CLIENT_AUTOSCALING,
    AWS_CLIENT_SECRETSMANAGER,
    AWS_CLIENT_BUDGETS,
    AWS_CLIENT_SES,
    AWS_CLIENT_SQS,
    AWS_CLIENT_SSM,
    AWS_CLIENT_SERVICE_QUOTAS,
    AWS_CLIENT_PRICING,
    AWS_CLIENT_CLOUDWATCH,
    AWS_CLIENT_CLOUDWATCHLOGS,
    AWS_CLIENT_ES,
    AWS_CLIENT_EVENTS,
    AWS_CLIENT_DS,
    AWS_CLIENT_FSX,
    AWS_CLIENT_EFS,
    AWS_CLIENT_ROUTE53,
    AWS_CLIENT_STS,
    AWS_CLIENT_ACM,
    AWS_CLIENT_DYNAMODB,
    AWS_RESOURCE_DYNAMODB_TABLE,
    AWS_CLIENT_COGNITO_IDP,
    AWS_CLIENT_KINESIS_STREAM,
    AWS_CLIENT_RESOURCE_GROUPS_TAGGING_API,
    AWS_CLIENT_BACKUP,
}

DEFAULT_PRICING_API_REGION = "us-east-1"


class AwsClientProvider(AwsClientProviderProtocol):
    """
    AWS Client Provider
    """

    def __init__(self, options: Optional[AWSClientProviderOptions] = None):
        self._clients: Dict[str, Any] = {}
        self._aws_client_lock = RLock()
        self._instance_metadata = InstanceMetadataUtil()

        if options is None:
            self.options = AWSClientProviderOptions.default()
        else:
            self.options = options

        import boto3

        session_kwargs: Dict[str, Any] = {}
        if self.options.profile:
            session_kwargs["profile_name"] = self.options.profile
        if self.options.region:
            session_kwargs["region_name"] = self.options.region

        self._session = boto3.Session(**session_kwargs)

    def get_service_endpoint_url(
        self, service_name: str
    ) -> Optional[AwsServiceEndpoint]:
        if self.options is None:
            return None
        if self.options.endpoints is None:
            return None
        for endpoint in self.options.endpoints:
            if endpoint.service_name == service_name:
                return endpoint
        return None

    def _get_or_build_aws_client(self, service_name: str, **kwargs: Any) -> Any:
        region_name = None
        if "region_name" in kwargs:
            region_name = kwargs["region_name"]
        if not region_name:
            region_name = self.options.region
        if not region_name:
            region_name = self._session.region_name

        if region_name:
            client_key = f"{service_name}.{region_name}"
        else:
            client_key = service_name

        if client_key in self._clients:
            return self._clients[client_key]

        try:
            self._aws_client_lock.acquire()

            # check again
            if client_key in self._clients:
                return self._clients[client_key]

            if service_name in (AWS_RESOURCE_DYNAMODB_TABLE, AWS_RESOURCE_S3_BUCKET):
                config = None

                if service_name == AWS_RESOURCE_DYNAMODB_TABLE:
                    inferred_service_name = AWS_CLIENT_DYNAMODB
                elif service_name == AWS_RESOURCE_S3_BUCKET:
                    inferred_service_name = AWS_CLIENT_S3
                    config = Config(signature_version="s3v4")
                else:
                    raise general_exception(
                        f"aws boto3 resource not implemented for service name: {service_name}"
                    )

                aws_endpoint = self.get_service_endpoint_url(inferred_service_name)
                client = self._session.resource(
                    service_name=inferred_service_name,
                    region_name=region_name,
                    endpoint_url=(
                        aws_endpoint.endpoint_url if aws_endpoint is not None else None
                    ),
                    config=config,
                )

            else:
                config = None
                if service_name == AWS_CLIENT_S3:
                    config = Config(signature_version="s3v4")

                aws_endpoint = self.get_service_endpoint_url(service_name)
                client = self._session.client(
                    service_name=service_name,
                    region_name=region_name,
                    endpoint_url=(
                        aws_endpoint.endpoint_url if aws_endpoint is not None else None
                    ),
                    config=config,
                )

            self._clients[client_key] = client
            return client
        finally:
            self._aws_client_lock.release()

    def aws_partition(self) -> str:
        return self._session.get_partition_for_region(self.aws_region())

    def aws_region(self) -> str:
        return str(self.options.region or self._session.region_name)

    def aws_account_id(self) -> str:
        result = self.sts().get_caller_identity()
        return str(result.get("Account", ""))

    def aws_dns_suffix(self) -> str:
        # Simplified - return default for aws partition
        partition = self.aws_partition()
        if partition == "aws-us-gov":
            return "amazonaws-us-gov.com"
        elif partition == "aws-cn":
            return "amazonaws.com.cn"
        else:
            return "amazonaws.com"

    def aws_profile(self) -> str:
        return self.options.profile or ""

    def instance_metadata(self) -> InstanceMetadataUtil:
        return self._instance_metadata

    def is_running_in_ec2(self) -> bool:
        return self._instance_metadata.is_running_in_ec2()

    def are_credentials_expired(self) -> bool:
        credentials = self._session.get_credentials()
        if credentials is None:
            return True
        if credentials.method == "shared-credentials-file":
            try:
                self.aws_account_id()
                return False
            except botocore.exceptions.ClientError as e:
                if e.response["Error"]["Code"] == "ExpiredToken":
                    return True
                else:
                    raise e
        else:
            # Check if credentials have refresh_needed method
            if hasattr(credentials, "refresh_needed"):
                return bool(credentials.refresh_needed(refresh_in=30))
            return False

    def supported_clients(self) -> Set[str]:
        return SUPPORTED_CLIENTS

    def get_client(self, service_name: str, **kwargs: Any) -> Any:
        if service_name not in SUPPORTED_CLIENTS:
            raise general_exception(f'AWS Client: "{service_name}" not supported.')
        return self._get_or_build_aws_client(service_name=service_name, **kwargs)

    # Individual service methods
    def ssm(self) -> Any:
        return self.get_client(service_name=AWS_CLIENT_SSM)

    def eventbridge(self) -> Any:
        return self.get_client(service_name=AWS_CLIENT_EVENTS)

    def s3(self) -> Any:
        return self.get_client(service_name=AWS_CLIENT_S3)

    def s3_bucket(self) -> Any:
        return self.get_client(service_name=AWS_RESOURCE_S3_BUCKET)

    def route53(self) -> Any:
        return self.get_client(service_name=AWS_CLIENT_ROUTE53)

    def ec2(self) -> Any:
        return self.get_client(service_name=AWS_CLIENT_EC2)

    def lambda_(self) -> Any:
        return self.get_client(service_name=AWS_CLIENT_LAMBDA)

    def elbv2(self) -> Any:
        return self.get_client(service_name=AWS_CLIENT_ELBV2)

    def iam(self) -> Any:
        return self.get_client(service_name=AWS_CLIENT_IAM)

    def cloudformation(self) -> Any:
        return self.get_client(service_name=AWS_CLIENT_CLOUDFORMATION)

    def application_autoscaling(self) -> Any:
        return self.get_client(service_name=AWS_CLIENT_APPLICATION_AUTOSCALING)

    def autoscaling(self) -> Any:
        return self.get_client(service_name=AWS_CLIENT_AUTOSCALING)

    def secretsmanager(self) -> Any:
        return self.get_client(service_name=AWS_CLIENT_SECRETSMANAGER)

    def budgets(self) -> Any:
        return self.get_client(service_name=AWS_CLIENT_BUDGETS)

    def ses(self, region_name: Optional[str] = None) -> Any:
        return self.get_client(service_name=AWS_CLIENT_SES, region_name=region_name)

    def service_quotas(self) -> Any:
        return self.get_client(service_name=AWS_CLIENT_SERVICE_QUOTAS)

    def pricing(self) -> Any:
        pricing_api_region = str(
            self.options.pricing_api_region or DEFAULT_PRICING_API_REGION
        )
        return self.get_client(
            service_name=AWS_CLIENT_PRICING, region_name=pricing_api_region
        )

    def sqs(self) -> Any:
        return self.get_client(service_name=AWS_CLIENT_SQS)

    def cloudwatch(self) -> Any:
        return self.get_client(service_name=AWS_CLIENT_CLOUDWATCH)

    def logs(self) -> Any:
        return self.get_client(service_name=AWS_CLIENT_CLOUDWATCHLOGS)

    def efs(self) -> Any:
        return self.get_client(service_name=AWS_CLIENT_EFS)

    def fsx(self) -> Any:
        return self.get_client(service_name=AWS_CLIENT_FSX)

    def ds(self) -> Any:
        return self.get_client(service_name=AWS_CLIENT_DS)

    def es(self) -> Any:
        return self.get_client(service_name=AWS_CLIENT_ES)

    def sts(self) -> Any:
        return self.get_client(service_name=AWS_CLIENT_STS)

    def acm(self) -> Any:
        return self.get_client(service_name=AWS_CLIENT_ACM)

    def dynamodb(self) -> Any:
        return self.get_client(service_name=AWS_CLIENT_DYNAMODB)

    def dynamodb_table(self) -> Any:
        return self.get_client(service_name=AWS_RESOURCE_DYNAMODB_TABLE)

    def cognito_idp(self) -> Any:
        return self.get_client(service_name=AWS_CLIENT_COGNITO_IDP)

    def kinesis(self) -> Any:
        return self.get_client(service_name=AWS_CLIENT_KINESIS_STREAM)

    def resource_groups_tagging_api(self) -> Any:
        return self.get_client(service_name=AWS_CLIENT_RESOURCE_GROUPS_TAGGING_API)

    def backup(self) -> Any:
        return self.get_client(service_name=AWS_CLIENT_BACKUP)

    def aws_lambda(self) -> Any:
        return self.get_client(service_name=AWS_CLIENT_LAMBDA)
