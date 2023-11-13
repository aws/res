#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the 'License'). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

from idea_lambda_commons import HttpClient, CfnResponse, CfnResponseStatus
import boto3
import logging
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)

PHYSICAL_RESOURCE_ID = 'opensearch-private-ip-addresses'


def handler(event, context):
    domain_name = None
    http_client = HttpClient()
    try:
        logger.info(f'ReceivedEvent: {json.dumps(event)}')
        request_type = event.get('RequestType')

        if request_type == 'Delete':
            http_client.send_cfn_response(CfnResponse(
                context=context,
                event=event,
                status=CfnResponseStatus.SUCCESS,
                data={},
                physical_resource_id=PHYSICAL_RESOURCE_ID
            ))
            return

        resource_properties = event.get('ResourceProperties', {})
        domain_name = resource_properties.get('DomainName')
        logger.info('OpenSearch DomainName: ' + domain_name)

        ec2_client = boto3.client('ec2')
        response = ec2_client.describe_network_interfaces(Filters=[
            {'Name': 'description', 'Values': [f'ES {domain_name}']},
            {'Name': 'requester-id', 'Values': ['amazon-elasticsearch']}
        ])

        network_interfaces = response.get('NetworkInterfaces', [])
        result = []
        for network_interface in network_interfaces:
            logger.debug(network_interface)
            private_ip_addresses = network_interface.get('PrivateIpAddresses', [])
            for private_ip_address in private_ip_addresses:
                ip_address = private_ip_address.get('PrivateIpAddress', None)
                if ip_address is None:
                    continue
                result.append(ip_address)

        if len(result) == 0:
            msg = 'No IP addresses found'
            logger.error(msg)
            http_client.send_cfn_response(CfnResponse(
                context=context,
                event=event,
                status=CfnResponseStatus.FAILED,
                data={
                    'error': msg
                },
                physical_resource_id=PHYSICAL_RESOURCE_ID
            ))
        else:
            http_client.send_cfn_response(CfnResponse(
                context=context,
                event=event,
                status=CfnResponseStatus.SUCCESS,
                data={
                    'IpAddresses': ','.join(result)
                },
                physical_resource_id=PHYSICAL_RESOURCE_ID
            ))
    except Exception as e:
        logger.exception(f'Failed to get ES Private IP Address: {e}')
        error_message = f'Exception getting private IP addresses for ES soca-{domain_name}'
        http_client.send_cfn_response(CfnResponse(
            context=context,
            event=event,
            status=CfnResponseStatus.FAILED,
            data={
                'error': error_message
            },
            physical_resource_id=PHYSICAL_RESOURCE_ID
        ))
    finally:
        http_client.destroy()
