#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Dict, List, Set

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
    Add new ingress rules for the NAT Gateway EIPs in the security group
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
            # Revoke ingress rules for the NAT Gateway EIPs in the security group
            old_properties = (
                event["OldResourceProperties"]
                if event["RequestType"] == "Update"
                else event["ResourceProperties"]
            )
            old_subnet_ids = old_properties["subnet_ids"]
            old_security_group_id = old_properties["security_group_id"]

            # Get EIPs from old subnets
            old_eip_ips = get_eips(old_subnet_ids)

            # Update security group
            old_security_group = ec2_resource.SecurityGroup(old_security_group_id)

            if old_eip_ips:
                try:
                    old_security_group.revoke_ingress(
                        IpPermissions=get_ip_permissions(old_eip_ips)
                    )
                except ClientError as e:
                    error_code = e.response["Error"]["Code"]
                    if error_code == "InvalidPermission.NotFound":
                        logger.info("Rule doesn't exist")
                    else:
                        raise e

        if event["RequestType"] != "Delete":
            # Add new ingress rules for the NAT Gateway EIPs in the security group
            props = event["ResourceProperties"]
            subnet_ids = props["subnet_ids"]
            security_group_id = props["security_group_id"]

            # Get EIPs from subnets
            eip_ips = get_eips(subnet_ids)

            # Update security group
            security_group = ec2_resource.SecurityGroup(security_group_id)

            if eip_ips:
                try:
                    security_group.authorize_ingress(
                        IpPermissions=get_ip_permissions(eip_ips)
                    )
                except ClientError as e:
                    error_code = e.response["Error"]["Code"]
                    if error_code == "InvalidPermission.Duplicate":
                        logger.info("Rule already exists")
                    else:
                        raise e

            response["Data"] = {"EIPs": list(eip_ips)}
    except Exception as e:
        error_message = f"Failed to update ingress rules for the NAT Gateway EIPs in the security group: {str(e)}"
        response["Status"] = "FAILED"
        response["Reason"] = error_message

        logging.exception(error_message)
    finally:
        send_response(url=event["ResponseURL"], response=response)


def get_eips(subnet_ids: List[str]) -> Set[str]:
    ec2_client = boto3.client("ec2")
    eip_ips = set()

    for subnet_id in subnet_ids:
        describe_network_interfaces_response = ec2_client.describe_network_interfaces(
            Filters=[
                {"Name": "subnet-id", "Values": [subnet_id]},
                {"Name": "association.allocation-id", "Values": ["*"]},
            ]
        )

        for interface in describe_network_interfaces_response["NetworkInterfaces"]:
            if "Association" in interface:
                eip_ips.add(interface["Association"]["PublicIp"])

    return eip_ips


def get_ip_permissions(eip_ips: Set[str]) -> List[Dict[str, Any]]:
    return [
        {
            "IpProtocol": "tcp",
            "FromPort": 443,
            "ToPort": 443,
            "IpRanges": [{"CidrIp": f"{ip}/32"} for ip in eip_ips],
        }
    ]
