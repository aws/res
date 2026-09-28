#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import base64
from typing import Any, Dict, List, Optional, Tuple

import botocore.exceptions
from res import constants
from res.clients.aws.aws_provider import AwsClientProvider
from res.resources import cluster_settings
from res.utils import ec2_utils, logging_utils

logger = logging_utils.get_logger("launch-templates")


def create_for_session(
    virtual_desktop: Dict[str, Any],
    software_stack: Dict[str, Any],
    aws_tags: List[Dict[str, str]],
    metadata_http_tokens: str,
    kms_key_id: str,
    placement: Dict[str, Any],
    user_data: str,
) -> Tuple[str, int]:
    """Create a per-session EC2 launch template. Returns (launch_template_id, version)."""
    server = virtual_desktop.get("server") or {}
    base_os = virtual_desktop.get("base_os", "")
    idea_session_id = virtual_desktop.get("idea_session_id", "")
    cluster_name = cluster_settings.get_setting("cluster.cluster_name")

    ami_id = software_stack.get("ami_id")
    if ami_id and ami_id.startswith("arn:"):
        ami_id = f'resolve:ssm:{ec2_utils.get_systems_manager_parameter(ami_id).get("Name", "")}'

    root_volume_size = server.get("root_volume_size") or {}
    volume_size_value = root_volume_size.get("value", 0)

    # CreateLaunchTemplate requires base64-encoded UserData.
    encoded_user_data = base64.b64encode(user_data.encode("utf-8")).decode("utf-8")

    launch_template_data: Dict[str, Any] = {
        "ImageId": ami_id,
        "UserData": encoded_user_data,
        "IamInstanceProfile": {"Arn": server.get("instance_profile_arn")},
        "BlockDeviceMappings": [
            {
                "DeviceName": ec2_utils.get_ec2_block_device_name(base_os),
                "Ebs": {
                    "DeleteOnTermination": True,
                    "VolumeSize": int(volume_size_value),
                    "Encrypted": constants.DEFAULT_VOLUME_ENCRYPTION_VDI,
                    "KmsKeyId": kms_key_id,
                    "VolumeType": constants.DEFAULT_VOLUME_TYPE_VDI,
                },
            }
        ],
        # SubnetId is supplied per CreateFleet override so a single template
        # can fan out across AZs.
        "NetworkInterfaces": [
            {
                "DeviceIndex": 0,
                "AssociatePublicIpAddress": False,
                "Groups": server.get("security_groups", []),
            }
        ],
        "HibernationOptions": {
            "Configured": bool(virtual_desktop.get("hibernation_enabled"))
        },
        "MetadataOptions": {
            "HttpTokens": metadata_http_tokens,
            "HttpEndpoint": "enabled",
        },
        "Placement": placement,
        "TagSpecifications": [{"ResourceType": "instance", "Tags": aws_tags}],
    }

    key_pair_name = server.get("key_pair_name")
    if key_pair_name:
        launch_template_data["KeyName"] = key_pair_name

    template_name = f"{cluster_name}-{idea_session_id}-lt"
    template_tags = aws_tags + [{"Key": "idea_session_id", "Value": idea_session_id}]

    ec2_client = AwsClientProvider().ec2()
    try:
        response = ec2_client.create_launch_template(
            LaunchTemplateName=template_name,
            LaunchTemplateData=launch_template_data,
            TagSpecifications=[
                {"ResourceType": "launch-template", "Tags": template_tags}
            ],
        )
    except botocore.exceptions.ClientError as err:
        error_code = err.response.get("Error", {}).get("Code", "")
        logger.error(
            f"Failed to create launch template for session {idea_session_id}: {error_code} - {err}"
        )
        raise

    launch_template = response.get("LaunchTemplate", {})
    launch_template_id = launch_template.get("LaunchTemplateId", "")
    version = int(launch_template.get("LatestVersionNumber", 1))
    logger.info(
        f"Created launch template {launch_template_id} (v{version}) for session {idea_session_id}"
    )
    return launch_template_id, version


def delete_for_session(launch_template_id: Optional[str]) -> None:
    """Delete a per-session EC2 launch template. Idempotent."""
    if not launch_template_id:
        return

    ec2_client = AwsClientProvider().ec2()
    try:
        ec2_client.delete_launch_template(LaunchTemplateId=launch_template_id)
        logger.info(f"Deleted launch template {launch_template_id}")
    except botocore.exceptions.ClientError as err:
        error_code = err.response.get("Error", {}).get("Code", "")
        if error_code == "InvalidLaunchTemplateId.NotFound":
            logger.info(f"Launch template {launch_template_id} already deleted")
            return
        logger.warning(
            f"Failed to delete launch template {launch_template_id}: {error_code} - {err}"
        )
