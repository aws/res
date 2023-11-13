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

from idea_lambda_commons import HttpClient, CfnResponse, CfnResponseStatus
import boto3
import logging
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: dict, context):
    """
    Create or Update Cluster Configuration based on key received key value pairs
    """
    logger.info(f'ReceivedEvent: {json.dumps(event)}')
    request_type = event.get('RequestType', None)
    resource_properties = event.get('ResourceProperties', {})
    old_resource_properties = event.get('OldResourceProperties', None)
    cluster_name = resource_properties.get('cluster_name')
    module_id = resource_properties.get('module_id')
    version = resource_properties.get('version')
    stack_name = f'{cluster_name}-{module_id}'
    physical_resource_id = f'{cluster_name}-{module_id}-settings'
    client = HttpClient()
    try:

        dynamodb = boto3.resource('dynamodb')

        cluster_settings_table_name = f'{cluster_name}.cluster-settings'
        cluster_settings_table = dynamodb.Table(cluster_settings_table_name)

        settings = resource_properties.get('settings')
        modules_table_name = f'{cluster_name}.modules'
        modules_table = dynamodb.Table(modules_table_name)

        if request_type == 'Delete':

            for key in settings:
                config_key = f'{module_id}.{key}'
                logger.info(f'deleting config: {config_key}')
                cluster_settings_table.delete_item(
                    Key={
                        'key': config_key
                    }
                )

            modules_table.update_item(
                Key={
                    'module_id': module_id
                },
                UpdateExpression='SET #status=:status, #stack_name=:stack_name, #version=:version',
                ExpressionAttributeNames={
                    '#status': 'status',
                    '#stack_name': 'stack_name',
                    '#version': 'version',
                },
                ExpressionAttributeValues={
                    ':status': 'not-deployed',
                    ':stack_name': None,
                    ':version': None
                }
            )

        else:

            for key in settings:
                value = settings[key]

                config_key = f'{module_id}.{key}'
                logger.info(f'updating config: {config_key} = {value}')
                cluster_settings_table.update_item(
                    Key={
                        'key': config_key
                    },
                    UpdateExpression='SET #value=:value, #source=:source ADD #version :version',
                    ExpressionAttributeNames={
                        '#value': 'value',
                        '#version': 'version',
                        '#source': 'source'
                    },
                    ExpressionAttributeValues={
                        ':value': value,
                        ':source': 'stack',
                        ':version': 1
                    }
                )

            modules_table.update_item(
                Key={
                    'module_id': module_id
                },
                UpdateExpression='SET #status=:status, #stack_name=:stack_name, #version=:version',
                ExpressionAttributeNames={
                    '#status': 'status',
                    '#stack_name': 'stack_name',
                    '#version': 'version',
                },
                ExpressionAttributeValues={
                    ':status': 'deployed',
                    ':stack_name': stack_name,
                    ':version': version
                }
            )

            # in case of a stack Update event, compute a delta using OldResourceProperties
            # and clean up any values that are no longer applicable
            # this takes care of scenarios where a resource was deleted from the updated stack
            if old_resource_properties is not None:
                old_settings = old_resource_properties.get('settings', {})
                settings_to_delete = []
                for old_key in old_settings:
                    if old_key not in settings:
                        settings_to_delete.append(old_key)
                if len(settings_to_delete) > 0:
                    for key in settings_to_delete:
                        config_key = f'{module_id}.{key}'
                        logger.info(f'deleting config: {config_key}')
                        cluster_settings_table.delete_item(
                            Key={
                                'key': config_key
                            }
                        )

        client.send_cfn_response(CfnResponse(
            context=context,
            event=event,
            status=CfnResponseStatus.SUCCESS,
            data={},
            physical_resource_id=physical_resource_id
        ))

    except Exception as e:
        logger.exception(f'failed to update cluster settings for module: {module_id} - {e}')
        client.send_cfn_response(CfnResponse(
            context=context,
            event=event,
            status=CfnResponseStatus.FAILED,
            data={},
            physical_resource_id=physical_resource_id
        ))
    finally:
        client.destroy()
