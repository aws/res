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

from ideasdk.utils import Utils
from ideasdk.context import SocaCliContext, SocaContextOptions

from typing import List, Dict, Set

from prettytable import PrettyTable


class VpcEndpointsHelper:

    def __init__(self, aws_region: str, aws_profile: str = None):
        self.aws_region = aws_region
        self.aws_profile = aws_profile

        self.context = SocaCliContext(
            options=SocaContextOptions(
                aws_region=aws_region,
                aws_profile=aws_profile,
                enable_aws_client_provider=True,
                enable_iam_permission_util=True
            )
        )

        aws_dns_suffix = self.context.aws().aws_dns_suffix()
        tokens = aws_dns_suffix.split('.')
        tokens.reverse()
        self.service_name_domain = '.'.join(tokens)

        self.gateway_endpoints = {
            's3': {
                'enabled': True,
                'endpoint_url': None
            },
            'dynamodb': {
                'enabled': True,
                'endpoint_url': None
            }
        }

        self.interface_endpoints = {
            'application-autoscaling': {
                'enabled': True,
                'endpoint_url': None
            },
            'autoscaling': {
                'enabled': True,
                'endpoint_url': None
            },
            'cloudformation': {
                'enabled': True,
                'endpoint_url': None
            },
            'ec2': {
                'enabled': True,
                'endpoint_url': None
            },
            'ec2messages': {
                'enabled': True,
                'endpoint_url': None
            },
            'ebs': {
                'enabled': True,
                'endpoint_url': None
            },
            'elasticfilesystem': {
                'enabled': True,
                'endpoint_url': None
            },
            'elasticfilesystem-fips': {
                'enabled': False,
                'endpoint_url': None
            },
            'elasticloadbalancing': {
                'enabled': True,
                'endpoint_url': None
            },
            'logs': {
                'enabled': True,
                'endpoint_url': None
            },
            'monitoring': {
                'enabled': True,
                'endpoint_url': None
            },
            'secretsmanager': {
                'enabled': True,
                'endpoint_url': None
            },
            'sns': {
                'enabled': True,
                'endpoint_url': None
            },
            'sqs': {
                'enabled': True,
                'endpoint_url': None
            },
            'events': {
                'enabled': True,
                'endpoint_url': None
            },
            'ssm': {
                'enabled': True,
                'endpoint_url': None
            },
            'ssmmessages': {
                'enabled': True,
                'endpoint_url': None
            },
            'fsx': {
                'enabled': True,
                'endpoint_url': None
            },
            'fsx-fips': {
                'enabled': False,
                'endpoint_url': None
            },
            'backup': {
                'enabled': True,
                'endpoint_url': None
            },
            'grafana': {
                'enabled': True,
                'endpoint_url': None
            },
            'acm-pca': {
                'enabled': False,
                'endpoint_url': None
            },
            'kinesis-streams': {
                'enabled': True,
                'endpoint_url': None
            }
        }

    def get_service_name(self, short_name: str):
        return f'{self.service_name_domain}.{self.aws_region}.{short_name}'

    def get_idea_service_names(self) -> Set[str]:
        service_names = set()
        for service_name in self.gateway_endpoints:
            service_names.add(self.get_service_name(service_name))
        for service_name in self.interface_endpoints:
            service_names.add(self.get_service_name(service_name))
        return service_names

    def get_vpc_endpoint_services(self) -> List[Dict]:
        describe_result = self.context.aws().ec2().describe_vpc_endpoint_services()

        service_details = Utils.get_value_as_list('ServiceDetails', describe_result, [])
        service_details_map = {}
        for service_detail in service_details:
            service_name = service_detail['ServiceName']
            if service_name in service_details_map:
                services = service_details_map[service_name]
            else:
                services = []
                service_details_map[service_name] = services
            services.append(service_detail)

        idea_service_names = self.get_idea_service_names()
        result = []
        for service_name in idea_service_names:
            if service_name in service_details_map:
                service_details = service_details_map[service_name]
                for service_detail in service_details:
                    for service_type in service_detail['ServiceType']:
                        result.append({
                            'service_name': service_name,
                            'available': True,
                            'service_type': service_type['ServiceType'],
                            'availability_zones': service_detail['AvailabilityZones']
                        })
            else:
                result.append({
                    'service_name': service_name,
                    'available': False
                })
        return result

    def get_supported_gateway_endpoint_services(self) -> List[str]:
        result = []
        describe_result = self.context.aws().ec2().describe_vpc_endpoint_services(
            Filters=[
                {
                    'Name': 'service-type',
                    'Values': ['Gateway']
                }
            ]
        )
        service_names = Utils.get_value_as_list('ServiceNames', describe_result, [])
        for service_name in self.gateway_endpoints:
            if self.get_service_name(service_name) in service_names:
                result.append(service_name)
        return result

    def get_supported_interface_endpoint_services(self) -> Dict:
        result = {}
        describe_result = self.context.aws().ec2().describe_vpc_endpoint_services(
            Filters=[
                {
                    'Name': 'service-type',
                    'Values': ['Interface']
                }
            ]
        )
        service_names = Utils.get_value_as_list('ServiceNames', describe_result, [])
        for service_name in self.interface_endpoints:
            if self.get_service_name(service_name) in service_names:
                result[service_name] = {
                    'enabled': self.interface_endpoints[service_name]['enabled'],
                    'endpoint_url': None
                }
        return result

    def print_vpc_endpoint_services(self):
        service_details = self.get_vpc_endpoint_services()
        table = PrettyTable([
            'Service Name',
            f'Is Available in {self.aws_region}',
            'Service Type',
            'Availability Zones'
        ])
        table.align = 'l'
        for service_detail in service_details:

            service_name = service_detail['service_name']
            is_available = service_detail['available']

            if is_available:
                service_type = service_detail['service_type']
                availability_zones = ', '.join(service_detail['availability_zones'])
            else:
                service_type = '-'
                availability_zones = '-'

            table.add_row([
                service_name,
                'Yes' if is_available else 'No',
                service_type,
                availability_zones
            ])

        print(table)

    def find_existing_vpc_endpoints(self, vpc_id: str, vpc_endpoint_type: str) -> List[Dict]:
        vpc_endpoints = []
        next_token = None
        while True:

            describe_request = {
                'Filters': [
                    {
                        'Name': 'vpc-id',
                        'Values': [vpc_id]
                    },
                    {
                        'Name': 'vpc-endpoint-type',
                        'Values': [vpc_endpoint_type]
                    }
                ]
            }
            if next_token is not None:
                describe_request['NextToken'] = next_token

            describe_result = self.context.aws().ec2().describe_vpc_endpoints(**describe_request)

            endpoints = Utils.get_value_as_list('VpcEndpoints', describe_result, [])
            vpc_endpoints += endpoints

            next_token = Utils.get_value_as_string('NextToken', describe_result)
            if next_token is None:
                break

        return vpc_endpoints

    def find_existing_gateway_endpoints(self, vpc_id: str) -> Dict:
        endpoints = self.find_existing_vpc_endpoints(vpc_id=vpc_id, vpc_endpoint_type='Gateway')
        result = {}
        for endpoint in endpoints:
            service_name = endpoint['ServiceName']
            short_name = service_name.split('.')[-1]
            result[short_name] = endpoint
        return result

    def is_interface_endpoint_enabled(self, service_name: str):
        if service_name in self.interface_endpoints:
            return self.interface_endpoints[service_name]['enabled']
        return False

    def is_gateway_endpoint_enabled(self, service_name: str):
        if service_name in self.gateway_endpoints:
            return self.gateway_endpoints[service_name]['enabled']
        return False

    def find_missing_gateway_endpoint_services(self, vpc_id: str) -> List[str]:
        existing_endpoints = self.find_existing_gateway_endpoints(vpc_id)
        supported_endpoints = self.get_supported_gateway_endpoint_services()
        missing_endpoints = []
        for service_name in supported_endpoints:
            if service_name in existing_endpoints:
                existing_endpoint = existing_endpoints[service_name]
                if existing_endpoint['State'] not in ('PendingAcceptance', 'Pending', 'Available'):
                    continue
            if not self.is_gateway_endpoint_enabled(service_name):
                continue
            missing_endpoints.append(service_name)
        return missing_endpoints

    def find_existing_interface_endpoints(self, vpc_id: str) -> Dict:
        endpoints = self.find_existing_vpc_endpoints(vpc_id=vpc_id, vpc_endpoint_type='Interface')
        result = {}
        for endpoint in endpoints:
            service_name = endpoint['ServiceName']
            short_name = service_name.split('.')[-1]
            result[short_name] = endpoint
        return result

    def find_missing_interface_endpoint_services(self, vpc_id: str) -> List[str]:
        existing_endpoints = self.find_existing_interface_endpoints(vpc_id)
        supported_endpoints = self.get_supported_interface_endpoint_services()
        missing_endpoints = []
        for service_name in supported_endpoints:
            if service_name in existing_endpoints:
                existing_endpoint = existing_endpoints[service_name]
                if existing_endpoint['State'] not in ('PendingAcceptance', 'Pending', 'Available'):
                    continue
            if not self.is_interface_endpoint_enabled(service_name):
                continue
            missing_endpoints.append(service_name)
        return missing_endpoints
