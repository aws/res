#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Dict, List

import boto3
from botocore.exceptions import ClientError
from res.utils.custom_resource_utils import (  # type: ignore
    CustomResourceResponse,
    send_response,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: Dict[str, Any], context: Dict[str, Any]) -> None:
    """
    Add ingress rules to security groups
    """
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
        ec2_resource = boto3.resource("ec2")

        if event["RequestType"] == "Update" or event["RequestType"] == "Delete":
            # Revoke ingress rules that were added previously
            old_properties = (
                event["OldResourceProperties"]
                if event["RequestType"] == "Update"
                else event["ResourceProperties"]
            )
            old_ingress_rule_mappings = old_properties["ingress_rule_mappings"]
            try:
                for old_ingress_rule_mapping in old_ingress_rule_mappings:
                    for ingress_rule in old_ingress_rule_mapping["ingress_rules"]:
                        ingress_rule["FromPort"] = int(ingress_rule["FromPort"])
                        ingress_rule["ToPort"] = int(ingress_rule["ToPort"])

                    old_security_group = ec2_resource.SecurityGroup(
                        old_ingress_rule_mapping["security_group_id"]
                    )
                    old_security_group.revoke_ingress(
                        IpPermissions=old_ingress_rule_mapping["ingress_rules"]
                    )
            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                if error_code == "InvalidPermission.NotFound":
                    logger.info("Rule doesn't exist")
                else:
                    raise e

        if event["RequestType"] != "Delete":
            # Add new ingress rules
            props = event["ResourceProperties"]
            ingress_rule_mappings = props["ingress_rule_mappings"]
            try:
                for ingress_rule_mapping in ingress_rule_mappings:
                    for ingress_rule in ingress_rule_mapping["ingress_rules"]:
                        ingress_rule["FromPort"] = int(ingress_rule["FromPort"])
                        ingress_rule["ToPort"] = int(ingress_rule["ToPort"])

                    security_group = ec2_resource.SecurityGroup(
                        ingress_rule_mapping["security_group_id"]
                    )
                    security_group.authorize_ingress(
                        IpPermissions=ingress_rule_mapping["ingress_rules"],
                    )
            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                if error_code == "InvalidPermission.Duplicate":
                    logger.info("Rule already exists")
                else:
                    raise e
    except Exception as e:
        error_message = (
            f"Failed to update peer ingress rules for security group: {str(e)}"
        )
        response["Status"] = "FAILED"
        response["Reason"] = error_message

        logging.exception(error_message)
    finally:
        send_response(url=event["ResponseURL"], response=response)
