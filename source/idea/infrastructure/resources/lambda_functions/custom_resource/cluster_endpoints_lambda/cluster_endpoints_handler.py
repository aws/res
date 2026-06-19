#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
Cluster Endpoints

This function is used by individual module stacks to expose module API or web endpoints via External and Internal ALBs.
"""

import json
import logging
import time
from typing import Any, Dict, Optional

import boto3
import botocore.exceptions
from res.constants import OLD_CUSTOM_TAG_KEYS  # type: ignore
from res.resources import cluster_settings  # type: ignore
from res.utils import cluster_settings_utils  # type: ignore
from res.utils.custom_resource_utils import (  # type: ignore
    CustomResourceResponse,
    send_response,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def find_rule_arn(
    elbv2_client: Any, listener_arn: str, endpoint_name: str
) -> Optional[str]:
    describe_rules_result = elbv2_client.describe_rules(
        ListenerArn=listener_arn, PageSize=100  # ALB no. of rules limit
    )

    rules = describe_rules_result.get("Rules", [])
    rule_arns = []
    for rule in rules:
        rule_arn = rule.get("RuleArn")
        rule_arns.append(rule_arn)

    # a batch based implementation can caused race conditions during describe_tags operation, as the rule was deleted
    # from another invocation during delete vdc stack operation. switching back to one by one query of tags
    # added sleep to ensure requests are not being throttled
    for rule_arn in rule_arns:
        try:
            describe_tag_results = elbv2_client.describe_tags(ResourceArns=[rule_arn])
            tag_descriptions = describe_tag_results.get("TagDescriptions", [])
            for tag_description in tag_descriptions:
                rule_arn = tag_description.get("ResourceArn")
                tags = tag_description.get("Tags", [])
                for tag in tags:
                    if tag.get("Key") == "res:EndpointName":
                        if endpoint_name == tag.get("Value"):
                            return rule_arn  # type: ignore
            time.sleep(1)
        except botocore.exceptions.ClientError as e:
            logger.warning(f"failed to fetch tags for rule arn: {rule_arn} - {e}")
            time.sleep(2)
            continue

    return None


def handler(event: Dict[str, Any], context: Dict[str, Any]) -> None:
    logger.info(f"ReceivedEvent: {json.dumps(event)}")
    request_type = event.get("RequestType", None)
    resource_properties = event.get("ResourceProperties", {})

    # a unique name identifying the endpoint
    endpoint_name = resource_properties.get("endpoint_name", "__NOT_PROVIDED__")
    response = CustomResourceResponse(
        Status="SUCCESS",
        Reason="SUCCESS",
        PhysicalResourceId=event.get("LogicalResourceId", ""),
        StackId=event.get("StackId", ""),
        RequestId=event.get("RequestId", ""),
        LogicalResourceId=event.get("LogicalResourceId", ""),
        Data={},
    )

    try:

        if endpoint_name is None or endpoint_name == "__NOT_PROVIDED__":
            raise ValueError("endpoint_name is required and cannot be empty")

        # listener arn
        listener_arn = resource_properties.get("listener_arn")
        if listener_arn is None:
            raise ValueError("listener_arn is required and cannot be empty")

        # the module that hosts the web ui will send default_action = True.
        # in the default setup, this will be cluster manager
        default_action = resource_properties.get("default_action", False)

        # a json array structure as per:
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elbv2.html#ElasticLoadBalancingv2.Client.create_rule
        conditions = resource_properties.get("conditions", [])
        if not default_action:
            if conditions is None or len(conditions) == 0:
                raise ValueError("conditions[] is required and cannot be empty")

        # a json array structure as per:
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elbv2.html#ElasticLoadBalancingv2.Client.create_rule
        actions = resource_properties.get("actions", [])
        if not default_action:
            if actions is None or len(actions) == 0:
                raise ValueError("actions[] is required and cannot be empty")

        priority_value = resource_properties.get("priority")
        priority = -1
        if not default_action:
            priority = int(priority_value)
            if priority <= 0:
                raise ValueError("priority must be greater than 0")

        # any applicable tags need to added to the listener rules
        tags = resource_properties.get("tags", {})
        tags["res:EndpointName"] = endpoint_name

        resource_tags = []
        for key, value in tags.items():
            resource_tags.append({"Key": key, "Value": value})
        custom_tags = cluster_settings_utils.convert_custom_tags_to_dict_list(
            cluster_settings.get_setting("global-settings.custom_tags")
        )
        resource_tags.extend(custom_tags)
        old_custom_tag_keys_string = resource_properties.get(OLD_CUSTOM_TAG_KEYS, "")
        old_custom_tag_keys = (
            old_custom_tag_keys_string.split(";") if old_custom_tag_keys_string else []
        )

        elbv2_client = boto3.client("elbv2")

        if default_action:
            if request_type in ("Create", "Update"):
                elbv2_client.modify_listener(
                    ListenerArn=listener_arn, DefaultActions=actions
                )
                logger.info("default action modified")
            else:
                elbv2_client.modify_listener(
                    ListenerArn=listener_arn,
                    DefaultActions=[
                        {
                            "Type": "fixed-response",
                            "FixedResponseConfig": {
                                "MessageBody": json.dumps(
                                    {"success": True, "message": "OK"}
                                ),
                                "StatusCode": "200",
                                "ContentType": "application/json",
                            },
                        }
                    ],
                )
                logger.info("default action reset to fixed response")

        elif request_type == "Create":
            result = elbv2_client.create_rule(
                ListenerArn=listener_arn,
                Conditions=conditions,
                Priority=priority,
                Actions=actions,
                Tags=resource_tags,
            )
            rules = result.get("Rules", [])
            rule_arn = rules[0].get("RuleArn")
            logger.info(f"rule created. rule arn: {rule_arn}")

        elif request_type == "Update":
            rule_arn = find_rule_arn(
                elbv2_client, listener_arn=listener_arn, endpoint_name=endpoint_name
            )
            if rule_arn is not None:
                elbv2_client.modify_rule(
                    RuleArn=rule_arn, Conditions=conditions, Actions=actions
                )
                if old_custom_tag_keys:
                    elbv2_client.remove_tags(
                        ResourceArns=[rule_arn], TagKeys=old_custom_tag_keys
                    )
                if resource_tags:
                    elbv2_client.add_tags(ResourceArns=[rule_arn], Tags=resource_tags)

                logger.info(f"rule modified. rule arn: {rule_arn}")
            else:
                logger.warning("rule not found for target group. rule update skipped.")

        elif request_type == "Delete":
            rule_arn = find_rule_arn(
                elbv2_client, listener_arn=listener_arn, endpoint_name=endpoint_name
            )
            if rule_arn is not None:
                elbv2_client.delete_rule(RuleArn=rule_arn)
                logger.info(f"rule deleted. rule arn: {rule_arn}")
            else:
                logger.warning(
                    "rule could not be deleted. rule arn not found for target group"
                )

    except Exception as e:
        error_message = f"failed to {request_type} endpoint: {endpoint_name} - {e}"
        response["Status"] = "FAILED"
        response["Reason"] = error_message

        logging.exception(error_message)

    finally:
        send_response(url=event["ResponseURL"], response=response)
