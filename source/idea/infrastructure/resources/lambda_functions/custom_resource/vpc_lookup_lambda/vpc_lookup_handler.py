#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Dict

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
    Look up the CIDR block and availability zones of the VPC
    """
    resource_properties = event.get("ResourceProperties", {})
    vpc_id = resource_properties.get("vpc_id")
    vdi_subnets = resource_properties.get("subnets")

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
        ec2_client = boto3.client("ec2")

        vpc_response = ec2_client.describe_vpcs(VpcIds=[vpc_id])
        vpc = vpc_response["Vpcs"][0]

        subnet_response = ec2_client.describe_subnets(
            Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
        )

        azs = sorted(
            list(
                set(subnet["AvailabilityZone"] for subnet in subnet_response["Subnets"])
            )
        )

        subnets_response = ec2_client.describe_subnets(
            SubnetIds=vdi_subnets,
        )
        subnet_cidr_blocks = [
            subnet["CidrBlock"] for subnet in subnets_response["Subnets"]
        ]

        response["Data"] = {
            "cidr_block": vpc["CidrBlock"],
            "availability_zones": azs,
            "subnet_cidr_blocks": subnet_cidr_blocks,
        }
    except ClientError as e:
        error_message = f"failed to get VPC details: {e}"
        response["Status"] = "FAILED"
        response["Reason"] = error_message

        logger.exception(error_message)

    finally:
        send_response(url=event["ResponseURL"], response=response)
