#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

from ideasdk.protocols import AwsClientProviderProtocol
from ideasdk.aws.aws_endpoints import AwsEndpoints
from ideasdk.aws.instance_metadata_util import InstanceMetadataUtil
from ideadatamodel import SocaBaseModel, exceptions
from ideasdk.utils import Utils

from threading import RLock
from typing import List, Dict, Any, Optional, Set
import botocore.exceptions
from botocore.client import Config

AWS_CLIENT_S3 = 's3'
AWS_CLIENT_EC2 = 'ec2'
AWS_CLIENT_LAMBDA = 'lambda'
AWS_CLIENT_ELBV2 = 'elbv2'
AWS_CLIENT_IAM = 'iam'
AWS_CLIENT_CLOUDFORMATION = 'cloudformation'
AWS_CLIENT_AUTOSCALING = 'autoscaling'
AWS_CLIENT_APPLICATION_AUTOSCALING = 'application-autoscaling'
AWS_CLIENT_SECRETSMANAGER = 'secretsmanager'
AWS_CLIENT_BUDGETS = 'budgets'
AWS_CLIENT_SES = 'ses'
AWS_CLIENT_SQS = 'sqs'
AWS_CLIENT_SERVICE_QUOTAS = 'service-quotas'
AWS_CLIENT_PRICING = 'pricing'
AWS_CLIENT_CLOUDWATCH = 'cloudwatch'
AWS_CLIENT_CLOUDWATCHLOGS = 'logs'
AWS_CLIENT_ES = 'es'
AWS_CLIENT_DS = 'ds'
AWS_CLIENT_FSX = 'fsx'
AWS_CLIENT_EFS = 'efs'
AWS_CLIENT_STS = 'sts'
AWS_CLIENT_ROUTE53 = 'route53'
AWS_CLIENT_EVENTS = 'events'
AWS_CLIENT_SSM = 'ssm'
AWS_CLIENT_ACM = 'acm'
AWS_CLIENT_DYNAMODB = 'dynamodb'
AWS_CLIENT_COGNITO_IDP = 'cognito-idp'
AWS_CLIENT_KINESIS_STREAM = 'kinesis'
AWS_RESOURCE_DYNAMODB_TABLE = 'dynamodb.table'
AWS_RESOURCE_S3_BUCKET = 's3.bucket'
AWS_CLIENT_RESOURCE_GROUPS_TAGGING_API = 'resourcegroupstaggingapi'
AWS_CLIENT_BACKUP = 'backup'
AWS_CLIENT_LAMBDA = 'lambda'

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
    AWS_CLIENT_LAMBDA
}

DEFAULT_PRICING_API_REGION = 'us-east-1'


class AwsServiceEndpoint(SocaBaseModel):
    service_name: Optional[str]
    endpoint_url: Optional[str]

    def __str__(self):
        return f'Service: {self.service_name}, Endpoint Url: {self.endpoint_url}'


class AWSClientProviderOptions(SocaBaseModel):
    profile: Optional[str]
    region: Optional[str]
    pricing_api_region: Optional[str]
    endpoints: Optional[List[AwsServiceEndpoint]]

    @staticmethod
    def default():
        return AWSClientProviderOptions(
            profile=None,
            region=None,
            pricing_api_region=None
        )


class AwsClientProvider(AwsClientProviderProtocol):
    def __init__(self, options: AWSClientProviderOptions = None):
        self._clients: Dict[str, Any] = {}
        self._aws_client_lock = RLock()

        self._aws_endpoints = AwsEndpoints()
        self._instance_metadata = InstanceMetadataUtil()

        if options is None:
            self.options = AWSClientProviderOptions.default()
        else:
            self.options = options

        self._session = Utils.create_boto_session(
            aws_region=self.options.region,
            aws_profile=self.options.profile
        )

    def get_service_endpoint_url(self, service_name: str) -> Optional[AwsServiceEndpoint]:
        if self.options is None:
            return None
        if self.options.endpoints is None:
            return None
        for endpoint in self.options.endpoints:
            if endpoint.service_name == service_name:
                return endpoint
        return None

    def _get_or_build_aws_client(self, service_name, **kwargs):

        region_name = None
        if 'region_name' in kwargs:
            region_name = kwargs['region_name']
        if Utils.is_empty(region_name):
            region_name = self.options.region
        if Utils.is_empty(region_name):
            region_name = self._session.region_name

        if region_name:
            client_key = f'{service_name}.{region_name}'
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
                    config = Config(signature_version='s3v4')
                else:
                    raise exceptions.general_exception(f'aws boto3 resource not implemented for service name: {service_name}')

                aws_endpoint = self.get_service_endpoint_url(inferred_service_name)
                client = self._session.resource(
                    service_name=inferred_service_name,
                    region_name=region_name,
                    endpoint_url=aws_endpoint.endpoint_url if aws_endpoint is not None else None,
                    config=config
                )

            else:
                config = None
                if service_name == AWS_CLIENT_S3:
                    config = Config(signature_version='s3v4')

                aws_endpoint = self.get_service_endpoint_url(service_name)
                client = self._session.client(
                    service_name=service_name,
                    region_name=region_name,
                    endpoint_url=aws_endpoint.endpoint_url if aws_endpoint is not None else None,
                    config=config
                )

            self._clients[client_key] = client
            return client
        finally:
            self._aws_client_lock.release()

    def aws_endpoints(self) -> AwsEndpoints:
        return self._aws_endpoints

    def aws_partition(self) -> str:
        return self._session.get_partition_for_region(self.aws_region())

    def aws_region(self) -> str:
        return Utils.get_as_string(self.options.region, self._session.region_name)

    def aws_account_id(self) -> str:
        result = self.sts().get_caller_identity()
        return Utils.get_value_as_string('Account', result)

    def aws_dns_suffix(self) -> str:
        partition = self.aws_endpoints().get_partition(self.aws_partition())
        return partition.dns_suffix

    def aws_profile(self) -> str:
        return self.options.profile

    def instance_metadata(self) -> InstanceMetadataUtil:
        return self._instance_metadata

    def is_running_in_ec2(self) -> bool:
        return self._instance_metadata.is_running_in_ec2()

    def are_credentials_expired(self) -> bool:
        credentials = self._session.get_credentials()
        if credentials.method == 'shared-credentials-file':
            try:
                self.aws_account_id()
                return False
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == 'ExpiredToken':
                    return True
                else:
                    raise e
        else:
            return credentials.refresh_needed(refresh_in=30)

    def supported_clients(self) -> Set[str]:
        return SUPPORTED_CLIENTS

    def get_client(self, service_name: str, **kwargs):
        if service_name not in SUPPORTED_CLIENTS:
            raise exceptions.general_exception(f'AWS Client: "{service_name}" not supported.')
        return self._get_or_build_aws_client(service_name=service_name, **kwargs)

    def ssm(self):
        return self.get_client(service_name=AWS_CLIENT_SSM)

    def eventbridge(self):
        return self.get_client(service_name=AWS_CLIENT_EVENTS)

    def s3(self):
        return self.get_client(service_name=AWS_CLIENT_S3)

    def s3_bucket(self):
        return self.get_client(service_name=AWS_RESOURCE_S3_BUCKET)

    def route53(self):
        return self.get_client(service_name=AWS_CLIENT_ROUTE53)

    def ec2(self):
        return self.get_client(service_name=AWS_CLIENT_EC2)

    def lambda_(self):
        return self.get_client(service_name=AWS_CLIENT_LAMBDA)

    def elbv2(self):
        return self.get_client(service_name=AWS_CLIENT_ELBV2)

    def iam(self):
        return self.get_client(service_name=AWS_CLIENT_IAM)

    def cloudformation(self):
        return self.get_client(service_name=AWS_CLIENT_CLOUDFORMATION)

    def application_autoscaling(self):
        return self.get_client(service_name=AWS_CLIENT_APPLICATION_AUTOSCALING)

    def autoscaling(self):
        return self.get_client(service_name=AWS_CLIENT_AUTOSCALING)

    def secretsmanager(self):
        return self.get_client(service_name=AWS_CLIENT_SECRETSMANAGER)

    def budgets(self):
        return self.get_client(service_name=AWS_CLIENT_BUDGETS)

    def ses(self, region_name: str = None):
        return self.get_client(service_name=AWS_CLIENT_SES, region_name=region_name)

    def service_quotas(self):
        return self.get_client(service_name=AWS_CLIENT_SERVICE_QUOTAS)

    def pricing(self):
        pricing_api_region = Utils.get_as_string(self.options.pricing_api_region, DEFAULT_PRICING_API_REGION)
        return self.get_client(service_name=AWS_CLIENT_PRICING, region_name=pricing_api_region)

    def sqs(self):
        return self.get_client(service_name=AWS_CLIENT_SQS)

    def cloudwatch(self):
        return self.get_client(service_name=AWS_CLIENT_CLOUDWATCH)

    def logs(self):
        return self.get_client(service_name=AWS_CLIENT_CLOUDWATCHLOGS)

    def efs(self):
        return self.get_client(service_name=AWS_CLIENT_EFS)

    def fsx(self):
        return self.get_client(service_name=AWS_CLIENT_FSX)

    def ds(self):
        return self.get_client(service_name=AWS_CLIENT_DS)

    def es(self):
        return self.get_client(service_name=AWS_CLIENT_ES)

    def sts(self):
        return self.get_client(service_name=AWS_CLIENT_STS)

    def acm(self):
        return self.get_client(service_name=AWS_CLIENT_ACM)

    def dynamodb(self):
        return self.get_client(service_name=AWS_CLIENT_DYNAMODB)

    def dynamodb_table(self):
        return self.get_client(service_name=AWS_RESOURCE_DYNAMODB_TABLE)

    def cognito_idp(self):
        return self.get_client(service_name=AWS_CLIENT_COGNITO_IDP)

    def kinesis(self):
        return self.get_client(service_name=AWS_CLIENT_KINESIS_STREAM)

    def resource_groups_tagging_api(self):
        return self.get_client(service_name=AWS_CLIENT_RESOURCE_GROUPS_TAGGING_API)

    def backup(self):
        return self.get_client(service_name=AWS_CLIENT_BACKUP)

    def aws_lambda(self):
        return self.get_client(service_name=AWS_CLIENT_LAMBDA)
