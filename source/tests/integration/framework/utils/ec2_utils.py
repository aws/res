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

import logging
from typing import Any, Dict

import boto3
import pytest

logger = logging.getLogger(__name__)


def cluster_manager_instances(session: pytest.Session) -> list[Dict[str, Any]]:
    environment_name = session.config.getoption("--environment-name")
    region: str = session.config.getoption("--aws-region")

    instances = _all_in_service_instances_from_asgs(
        [f"{environment_name}-cluster-manager-asg"],
        region,
    )
    return instances


def vdc_instances(session: pytest.Session) -> list[Dict[str, Any]]:
    environment_name = session.config.getoption("--environment-name")
    region: str = session.config.getoption("--aws-region")

    instances = _all_in_service_instances_from_asgs(
        [f"{environment_name}-vdc-controller-asg"],
        region,
    )
    return instances


def _all_in_service_instances_from_asgs(
    auto_scaling_group_names: list[str],
    region: str,
) -> list[Dict[str, Any]]:
    session = boto3.session.Session(region_name=region)
    auto_scaling_client = session.client("autoscaling")
    response = auto_scaling_client.describe_auto_scaling_groups(
        AutoScalingGroupNames=auto_scaling_group_names
    )

    instances: list[Dict[str, Any]] = []
    for group in response.get("AutoScalingGroups", []):
        instances = instances + [
            instance
            for instance in group.get("Instances", [])
            if instance.get("LifecycleState") == "InService"
        ]

    return instances


def deregister_ami(image_id: str, region: str = "") -> bool:
    try:
        ec2 = boto3.client("ec2", region_name=region) if region else boto3.client("ec2")
        ec2.deregister_image(ImageId=image_id)
        logger.info(f"Successfully deregistered AMI {image_id}")
        return True
    except Exception as e:
        logger.error(f"Error deregistering AMI {image_id}: {e}")
        return False


def get_latest_x86_amzn2023_ami_id(region: str) -> str:
    """
    Get the latest public x86_64 Amazon Linux 2023 AMI ID for the specified region.

    This function queries the EC2 API to find the most recently created Amazon Linux 2023
    AMI that matches specific criteria (x86_64 architecture, available state, official Amazon AMI).

    Args:
        region: AWS region to search for AMI (e.g., 'us-west-2', 'us-east-1')

    Returns:
        AMI ID string (e.g., 'ami-0abcdef1234567890')

    Raises:
        Exception: If no AMI found or AWS API error occurs
    """
    try:
        ec2 = boto3.client("ec2", region_name=region)

        # Search for the latest Amazon Linux 2023 AMI
        response = ec2.describe_images(
            Filters=[
                {"Name": "name", "Values": ["al2023-ami-*-x86_64"]},
                {"Name": "owner-alias", "Values": ["amazon"]},
                {"Name": "state", "Values": ["available"]},
                {"Name": "architecture", "Values": ["x86_64"]},
            ],
            Owners=["amazon"],
        )

        if not response["Images"]:
            raise Exception(f"No Amazon Linux 2023 AMI found in region {region}")

        # Sort by creation date to get the latest
        sorted_images = sorted(
            response["Images"], key=lambda x: x["CreationDate"], reverse=True  # type: ignore
        )
        latest_ami = sorted_images[0]

        logger.info(
            f"Found latest amzn2023 AMI: {latest_ami['ImageId']} ({latest_ami['Name']}) in region {region}"
        )
        return latest_ami["ImageId"]  # type: ignore

    except Exception as e:
        logger.error(f"Failed to get AMI ID for region {region}: {str(e)}")
        return ""
