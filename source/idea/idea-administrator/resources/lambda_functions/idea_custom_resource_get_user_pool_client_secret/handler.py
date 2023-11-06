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

PHYSICAL_RESOURCE_ID = 'user-pool-client-secret'


def handler(event, context):
    http_client = HttpClient()
    client_id = None
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
        user_pool_id = resource_properties.get('UserPoolId')
        client_id = resource_properties.get('ClientId')
        logger.info(f'UserPoolId: {user_pool_id}, ClientId: {client_id}')

        cognito_idp_client = boto3.client('cognito-idp')
        response = cognito_idp_client.describe_user_pool_client(
            UserPoolId=user_pool_id,
            ClientId=client_id
        )

        client = response.get('UserPoolClient', {})
        client_secret = client.get('ClientSecret', None)

        if client_secret is None:
            msg = f'Could not find ClientSecret for ClientId: {client_id}'
            logger.error(msg)
            http_client.send_cfn_response(CfnResponse(
                context=context,
                event=event,
                status=CfnResponseStatus.FAILED,
                data={
                    'error': msg
                },
                physical_resource_id=f'{PHYSICAL_RESOURCE_ID}-{client_id}'
            ))
        else:
            http_client.send_cfn_response(CfnResponse(
                context=context,
                event=event,
                status=CfnResponseStatus.SUCCESS,
                data={
                    'ClientSecret': client_secret
                },
                physical_resource_id=f'{PHYSICAL_RESOURCE_ID}-{client_id}'
            ), log_response=False)  # disable response logging to prevent exposing client secret in logs
    except Exception as e:
        error_message = f'Failed to get ClientSecret for UserPool Client. - {e}'
        logger.exception(error_message)
        if client_id is None:
            client_id = 'failed'
        http_client.send_cfn_response(CfnResponse(
            context=context,
            event=event,
            status=CfnResponseStatus.FAILED,
            data={
                'error': error_message
            },
            physical_resource_id=f'{PHYSICAL_RESOURCE_ID}-{client_id}'
        ))
    finally:
        http_client.destroy()
