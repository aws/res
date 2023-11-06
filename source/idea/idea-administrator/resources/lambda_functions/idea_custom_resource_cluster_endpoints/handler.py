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

"""
Cluster Endpoints

This function is used by individual module stacks to expose module API or web endpoints via External and Internal ALBs.
"""
import time

import botocore.exceptions

from idea_lambda_commons import HttpClient, CfnResponse, CfnResponseStatus
import boto3
import logging
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def find_rule_arn(elbv2_client, listener_arn: str, endpoint_name: str):
    describe_rules_result = elbv2_client.describe_rules(
        ListenerArn=listener_arn,
        PageSize=100  # ALB no. of rules limit
    )

    rules = describe_rules_result.get('Rules', [])
    rule_arns = []
    for rule in rules:
        rule_arn = rule.get('RuleArn')
        rule_arns.append(rule_arn)

    # a batch based implementation can caused race conditions during describe_tags operation, as the rule was deleted
    # from another invocation during delete vdc stack operation. switching back to one by one query of tags
    # added sleep to ensure requests are not being throttled
    for rule_arn in rule_arns:
        try:
            describe_tag_results = elbv2_client.describe_tags(
                ResourceArns=[rule_arn]
            )
            tag_descriptions = describe_tag_results.get('TagDescriptions', [])
            for tag_description in tag_descriptions:
                rule_arn = tag_description.get('ResourceArn')
                tags = tag_description.get('Tags', [])
                for tag in tags:
                    if tag.get('Key') == 'res:EndpointName':
                        if endpoint_name == tag.get('Value'):
                            return rule_arn
            time.sleep(1)
        except botocore.exceptions.ClientError as e:
            logger.warning(f'failed to fetch tags for rule arn: {rule_arn} - {e}')
            time.sleep(2)
            continue

    return None


def handler(event: dict, context):
    logger.info(f'ReceivedEvent: {json.dumps(event)}')
    request_type = event.get('RequestType', None)
    resource_properties = event.get('ResourceProperties', {})

    # a unique name identifying the endpoint
    endpoint_name = resource_properties.get('endpoint_name', '__NOT_PROVIDED__')

    client = HttpClient()

    try:

        if endpoint_name is None or endpoint_name == '__NOT_PROVIDED__':
            raise ValueError('endpoint_name is required and cannot be empty')

        # listener arn
        listener_arn = resource_properties.get('listener_arn')
        if listener_arn is None:
            raise ValueError('listener_arn is required and cannot be empty')

        # the module that hosts the web ui will send default_action = True.
        # in the default setup, this will be cluster manager
        default_action = resource_properties.get('default_action', False)

        # a json array structure as per:
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elbv2.html#ElasticLoadBalancingv2.Client.create_rule
        conditions = resource_properties.get('conditions', [])
        if not default_action:
            if conditions is None or len(conditions) == 0:
                raise ValueError('conditions[] is required and cannot be empty')

        # a json array structure as per:
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elbv2.html#ElasticLoadBalancingv2.Client.create_rule
        actions = resource_properties.get('actions', [])
        if not default_action:
            if actions is None or len(actions) == 0:
                raise ValueError('actions[] is required and cannot be empty')

        priority_value = resource_properties.get('priority')
        priority = -1
        if not default_action:
            priority = int(priority_value)
            if priority <= 0:
                raise ValueError('priority must be greater than 0')

        # any applicable tags need to added to the listener rules
        tags = resource_properties.get('tags', {})
        tags['res:EndpointName'] = endpoint_name

        resource_tags = []
        for key, value in tags.items():
            resource_tags.append({
                'Key': key,
                'Value': value
            })

        elbv2_client = boto3.client('elbv2')

        if default_action:
            if request_type in ('Create', 'Update'):
                elbv2_client.modify_listener(
                    ListenerArn=listener_arn,
                    DefaultActions=actions
                )
                logger.info('default action modified')
            else:
                elbv2_client.modify_listener(
                    ListenerArn=listener_arn,
                    DefaultActions=[
                        {
                            'Type': 'fixed-response',
                            'FixedResponseConfig': {
                                'MessageBody': json.dumps({
                                    'success': True,
                                    'message': 'OK'
                                }),
                                'StatusCode': '200',
                                'ContentType': 'application/json'
                            }
                        }
                    ]
                )
                logger.info('default action reset to fixed response')

        elif request_type == 'Create':
            result = elbv2_client.create_rule(
                ListenerArn=listener_arn,
                Conditions=conditions,
                Priority=priority,
                Actions=actions,
                Tags=resource_tags
            )
            rules = result.get('Rules', [])
            rule_arn = rules[0].get('RuleArn')
            logger.info(f'rule created. rule arn: {rule_arn}')

        elif request_type == 'Update':
            rule_arn = find_rule_arn(elbv2_client, listener_arn=listener_arn, endpoint_name=endpoint_name)
            if rule_arn is not None:
                elbv2_client.modify_rule(
                    RuleArn=rule_arn,
                    Conditions=conditions,
                    Actions=actions
                )
                logger.info(f'rule modified. rule arn: {rule_arn}')
            else:
                logger.warning('rule not found for target group. rule update skipped.')

        elif request_type == 'Delete':
            rule_arn = find_rule_arn(elbv2_client, listener_arn=listener_arn, endpoint_name=endpoint_name)
            if rule_arn is not None:
                elbv2_client.delete_rule(
                    RuleArn=rule_arn
                )
                logger.info(f'rule deleted. rule arn: {rule_arn}')
            else:
                logger.warning('rule could not be deleted. rule arn not found for target group')

        client.send_cfn_response(CfnResponse(
            context=context,
            event=event,
            status=CfnResponseStatus.SUCCESS,
            data={},
            physical_resource_id=endpoint_name
        ))

    except Exception as e:
        error_message = f'failed to {request_type} endpoint: {endpoint_name} - {e}'
        logger.exception(error_message)
        client.send_cfn_response(CfnResponse(
            context=context,
            event=event,
            status=CfnResponseStatus.FAILED,
            data={},
            physical_resource_id=endpoint_name,
            reason=error_message
        ))
    finally:
        client.destroy()
