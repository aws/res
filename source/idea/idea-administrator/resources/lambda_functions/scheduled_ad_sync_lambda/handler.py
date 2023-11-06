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
Scheduled ad sync lambda
This function is triggered by an event-bridge event rule periodically. It sends ad-sync task to cluster manager
task queue. Cluster Manager picks up the task and initiates sync from AD.
"""
import json
import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sqs_client = boto3.client('sqs')


def handler(event, _):
    try:
        detail_type = event['detail-type']
        if detail_type != 'Scheduled Event':
            raise Exception('only EventBridge Scheduled Event is supported for the lambda')

        forwarding_event = {
            "name": "adsync.sync-from-ad",
            "payload": {}
        }

        logger.info('Forwarding scheduled ad sync task to cluster manager task queue')
        response = sqs_client.send_message(
            QueueUrl=os.environ.get('RES_CLUSTER_MANAGER_TASKS_QUEUE_URL'),
            MessageBody=json.dumps(forwarding_event),
            MessageGroupId='adsync.sync-from-ad'
        )
        logger.info(response)
    except Exception as e:
        logger.exception(f'error in handling event: {event}, error: {e}')
