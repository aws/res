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

logging.getLogger().setLevel(logging.INFO)


def handler(event, context):
    """
    Tag EC2 Resource
    """
    http_client = HttpClient()
    try:
        logging.info(f'ReceivedEvent: {event}')

        resource_id = event['ResourceProperties']['ResourceId']
        tags = event['ResourceProperties']['Tags']

        ec2_client = boto3.client('ec2')
        ec2_client.create_tags(
            Resources=[resource_id],
            Tags=tags
        )

        http_client.send_cfn_response(CfnResponse(
            context=context,
            event=event,
            status=CfnResponseStatus.SUCCESS,
            data={},
            physical_resource_id=resource_id
        ))
    except Exception as e:
        logging.exception(f'Failed to Tag EC2 Resource: {e}')
        http_client.send_cfn_response(CfnResponse(
            context=context,
            event=event,
            status=CfnResponseStatus.FAILED,
            data={
                'error': str(e)
            },
            physical_resource_id=str(e)
        ))
