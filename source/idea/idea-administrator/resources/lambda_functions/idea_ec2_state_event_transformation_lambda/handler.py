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
EC2 State event transformation
This function is triggered every time a state change event is triggered by an EC2 instance tagged
with IDEA_CLUSTER. It repackages the event, appends tag information and then publishes an 'Ec2.StateChangeEvent'
intended for the different modules that have subscribed to this event within the cluster
"""
import boto3
import os
import json
import logging
import re

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sns_client = boto3.client('sns')
ec2_resource = boto3.resource('ec2')


def handler(event, _):
    try:
        detail_type = event['detail-type']
        if detail_type != 'EC2 Instance State-change Notification':
            logger.error(f'ERROR. Invalid detail type {detail_type}')
            return

        cluster_name_tag_key = os.environ.get('IDEA_CLUSTER_NAME_TAG_KEY')
        cluster_name_tag_value = os.environ.get('IDEA_CLUSTER_NAME_TAG_VALUE')
        idea_tag_prefix = os.environ.get('IDEA_TAG_PREFIX')

        instance_id = event['detail']['instance-id']
        state = event['detail']['state']
        ec2instance = ec2_resource.Instance(instance_id)
        event['detail']['tags'] = {}
        cluster_match = False

        message_attributes = {}
        for tags in ec2instance.tags:
            if tags["Key"].startswith(idea_tag_prefix):
                event['detail']['tags'][tags["Key"]] = tags["Value"]
                message_attributes[re.sub(r"[^a-zA-Z0-9_\-\.]+","_",tags["Key"]).strip()] = {
                        'DataType': 'String',
                        'StringValue': tags["Value"]
                        }

            if tags["Key"] == cluster_name_tag_key and tags["Value"] == cluster_name_tag_value:
                cluster_match = True

        if not cluster_match:
            logger.info(f'tag_key(s): {cluster_name_tag_key} and tag_value(s): {cluster_name_tag_value} on instance-id: {instance_id} not found. NO=OP.')
            return

        forwarding_event = {
            'header': {
                'namespace': 'Ec2.StateChangeEvent',
                'request_id': instance_id
            },
            'payload': event['detail']
        }

        logger.info(f'forwarding ec2-state-event for {instance_id} for state {state}')
        forwarding_topic_arn = os.environ.get('IDEA_EC2_STATE_SNS_TOPIC_ARN')
        response = sns_client.publish(
            TopicArn=forwarding_topic_arn,
            MessageStructure='json',
            MessageAttributes=message_attributes,
            Message=json.dumps({
                'default': json.dumps(forwarding_event),
                'sqs': forwarding_event,
            }))

        logger.info(response)
    except Exception as e:
        logger.exception(f'Error in Handling ec2 state change event: {event}, error: {e}')
