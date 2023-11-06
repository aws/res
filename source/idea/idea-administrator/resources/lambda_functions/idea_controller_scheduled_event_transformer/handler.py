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
"""
Scheduled event transformer
This function is triggered by an event-bridge event rule periodically. It repackages the event and forwards it to the
Controller Events Queue.
"""
import json
import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sqs_client = boto3.client('sqs')
ec2_resource = boto3.resource('ec2')


def handler(event, _):
    try:
        detail_type = event['detail-type']
        if detail_type != 'Scheduled Event':
            return

        forwarding_event = {
            'event_group_id': 'SCHEDULED_EVENT',
            'event_type': 'SCHEDULED_EVENT',
            'detail': {
                'time': event['time']
            }
        }

        logger.info('Forwarding scheduled event to Controller')
        response = sqs_client.send_message(
            QueueUrl=os.environ.get('IDEA_CONTROLLER_EVENTS_QUEUE_URL'),
            MessageBody=json.dumps(forwarding_event),
            MessageGroupId='SCHEDULED_EVENT'
        )
        logger.info(response)
    except Exception as e:
        logger.exception(f'error in handling scheduled event: {event}, error: {e}')
