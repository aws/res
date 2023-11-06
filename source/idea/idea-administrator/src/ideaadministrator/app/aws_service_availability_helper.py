
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

from ideadatamodel import constants
from ideasdk.utils import Utils
from ideasdk.context import SocaCliContext

from typing import List, Dict
from prettytable import PrettyTable


class AwsServiceAvailabilityHelper:

    def __init__(self, aws_region: str = None, aws_profile: str = None, aws_secondary_profile: str = None):
        if Utils.is_empty(aws_region):
            aws_region = 'us-east-1'

        self.session = Utils.create_boto_session(aws_region=aws_region, aws_profile=aws_profile)
        if aws_region in Utils.get_value_as_list('SSM_DISCOVERY_RESTRICTED_REGION_LIST', constants.CAVEATS, default=[]):
            aws_ssm_region = Utils.get_value_as_string('SSM_DISCOVERY_FALLBACK_REGION', constants.CAVEATS, default='us-east-1')
            self.ssm_session = Utils.create_boto_session(aws_region=aws_ssm_region, aws_profile=aws_secondary_profile)
        else:
            aws_ssm_region = aws_region
            self.ssm_session = self.session

        self.ssm_client = self.ssm_session.client(
            service_name='ssm',
            region_name=aws_ssm_region
        )

        self.context = SocaCliContext()

        self.idea_services = {
            'acm': {
                'title': 'AWS Certificate Manager (ACM)',
                'required': True
            },
            'acm-pca': {
                'title': 'ACM Private CA',
                'required': False
            },
            'aps': {
                'title': 'Amazon Managed Service for Prometheus',
                'required': False
            },
            'backup': {
                'title': 'AWS Backup',
                'required': True
            },
            'budgets': {
                'title': 'AWS Budgets',
                'required': False
            },
            'cloudformation': {
                'title': 'AWS CloudFormation',
                'required': True
            },
            'cloudwatch': {
                'title': 'Amazon CloudWatch',
                'required': True
            },
            'cognito-idp': {
                'title': 'Amazon Cognito - User Pools',
                'required': True
            },
            'ds': {
                'title': 'AWS Directory Service for Microsoft Active Directory',
                'required': False
            },
            'dynamodb': {
                'title': 'Amazon DynamoDB',
                'required': True
            },
            'dynamodbstreams': {
                'title': 'Amazon DynamoDB Streams',
                'required': True
            },
            'ebs': {
                'title': 'Amazon Elastic Block Store (EBS)',
                'required': True
            },
            'ec2': {
                'title': 'Amazon Elastic Compute Cloud (EC2)',
                'required': True
            },
            'efs': {
                'title': 'Amazon Elastic File System (EFS)',
                'required': True
            },
            'elb': {
                'title': 'Amazon Elastic Load Balancing (ELB)',
                'required': True
            },
            'es': {
                'title': 'Amazon OpenSearch Service',
                'required': True
            },
            'eventbridge': {
                'title': 'Amazon EventBridge',
                'required': True
            },
            'events': {
                'title': 'Amazon Events',
                'required': True
            },
            'filecache': {
                'title': 'Amazon File Cache',
                'required': False
            },
            'fsx': {
                'title': 'Amazon FSx',
                'required': False
            },
            'fsx-lustre': {
                'title': 'Amazon FSx for Lustre',
                'required': False
            },
            'fsx-ontap': {
                'title': 'Amazon FSx for NetApp ONTAP',
                'required': False
            },
            'fsx-openzfs': {
                'title': 'Amazon FSx for OpenZFS',
                'required': False
            },
            'fsx-windows': {
                'title': 'Amazon FSx for Windows File Server',
                'required': False
            },
            'grafana': {
                'title': 'Amazon Managed Grafana',
                'required': False
            },
            'iam': {
                'title': 'AWS Identity and Access Management (IAM)',
                'required': True
            },
            'kinesis': {
                'title': 'Amazon Kinesis',
                'required': True
            },
            'kms': {
                'title': 'AWS Key Management Service (KMS)',
                'required': True
            },
            'lambda': {
                'title': 'AWS Lambda',
                'required': True
            },
            'logs': {
                'title': 'Amazon CloudWatch Logs',
                'required': True
            },
            'pricing': {
                'title': 'AWS Pricing API',
                'required': False
            },
            'route53': {
                'title': 'Amazon Route 53',
                'required': True
            },
            'route53resolver': {
                'title': 'Amazon Route 53 Resolver',
                'required': False
            },
            's3': {
                'title': 'Amazon Simple Storage Service (S3)',
                'required': True
            },
            'secretsmanager': {
                'title': 'AWS Secrets Manager',
                'required': True
            },
            'service-quotas': {
                'title': 'AWS Service Quotas',
                'required': True
            },
            'ses': {
                'title': 'Amazon Simple Email Service (SES)',
                'required': False
            },
            'sns': {
                'title': 'Amazon Simple Notification Service (SNS)',
                'required': True
            },
            'sqs': {
                'title': 'Amazon Simple Queue Service (SQS)',
                'required': True
            },
            'ssm': {
                'title': 'AWS Systems Manager (SSM)',
                'required': True
            },
            'sts': {
                'title': 'AWS Security Token Service (STS)',
                'required': True
            },
            'vpc': {
                'title': 'Amazon Virtual Private Cloud (VPC)',
                'required': True
            }
        }
        self.idea_service_names = list(self.idea_services.keys())
        self.idea_service_names.sort()

    def get_available_services(self, aws_region: str) -> Dict:
        result = {}

        next_token = None
        all_services = set()
        while True:

            if next_token is None:
                get_parameters_result = self.ssm_client.get_parameters_by_path(
                    Path=f'/aws/service/global-infrastructure/regions/{aws_region}/services'
                )
            else:
                get_parameters_result = self.ssm_client.get_parameters_by_path(
                    Path=f'/aws/service/global-infrastructure/regions/{aws_region}/services',
                    NextToken=next_token
                )

            parameters = Utils.get_value_as_list('Parameters', get_parameters_result, [])
            for parameter in parameters:
                all_services.add(parameter['Value'])

            next_token = Utils.get_value_as_string('NextToken', get_parameters_result)
            if next_token is None:
                break

        for service in self.idea_services:
            result[service] = service in all_services

        return result

    def get_availability_matrix(self, aws_regions: List[str]) -> List[Dict]:
        matrix = {}
        for aws_region in aws_regions:
            service_map = self.get_available_services(aws_region=aws_region)
            for service, available in service_map.items():
                if service in matrix:
                    region_info = matrix[service]
                else:
                    region_info = {}
                    matrix[service] = region_info
                region_info[aws_region] = available

        result = []
        for service, region_info in matrix.items():
            result.append({
                'service': service,
                'regions': region_info
            })

        result.sort(key=lambda d: d['service'])
        return result

    def print_availability_matrix(self, aws_regions: List[str]):
        with self.context.spinner('building service availability matrix ...'):
            entries = self.get_availability_matrix(aws_regions=aws_regions)

        table = PrettyTable([
            'Service',
            'Required',
            *aws_regions
        ])
        table.align = 'l'
        for entry in entries:
            service_name = entry['service']
            service_info = self.idea_services[service_name]
            service_title = service_info['title']
            required = service_info['required']
            service = f'{service_title} [{service_name}]'
            row = [
                service,
                'Yes' if required else 'No'
            ]
            for region in aws_regions:
                available = entry['regions'][region]
                row.append('Yes' if available else 'No')
            table.add_row(row)
        print(table)

    def print_idea_services(self):
        table = PrettyTable([
            'AWS Service',
            'Name',
            'Required'
        ])
        table.align = 'l'
        for service_name in self.idea_service_names:
            service_info = self.idea_services[service_name]
            table.add_row([
                service_info['title'],
                service_name,
                'Yes' if service_info['required'] else 'No'
            ])
        print(table)


