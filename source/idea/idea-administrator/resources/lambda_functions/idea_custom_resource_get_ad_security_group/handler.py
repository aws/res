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

PHYSICAL_RESOURCE_ID = 'ad-controller-security-group-id'


def handler(event, context):

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
        directory_id = resource_properties.get('DirectoryId')
        logger.info('AD DirectoryId: ' + directory_id)

        ds_client = boto3.client('ds')
        response = ds_client.describe_directories(
            DirectoryIds=[directory_id]
        )

        directories = response.get('DirectoryDescriptions', [])

        security_group_id = None
        if len(directories) > 0:
            directory = directories[0]
            vpc_settings = directory.get('VpcSettings', {})
            security_group_id = vpc_settings.get('SecurityGroupId', None)

        if security_group_id is None:
            msg = f'Could not find SecurityGroupId for DirectoryId: {directory_id}'
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
                    'SecurityGroupId': security_group_id
                },
                physical_resource_id=PHYSICAL_RESOURCE_ID
            ))
    except Exception as e:
        error_message = f'Failed to get SecurityGroupId for Directory: {e}'
        logger.exception(error_message)
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
