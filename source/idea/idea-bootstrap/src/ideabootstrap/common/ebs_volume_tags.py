#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import random
import time
import boto3
import json
from res.utils import logging_utils, cluster_settings_utils
from res.utils import instance_metadata_utils
from res.resources import cluster_settings

logger = logging_utils.get_logger("bootstrap")

def setup():
    logger.info("Setting EBS Volume Tags")
    env = os.environ
    cluster_name = env.get("IDEA_CLUSTER_NAME")
    module_name = env.get("IDEA_MODULE_NAME")
    module_id = env.get("IDEA_MODULE_ID")
    aws_region = env.get("AWS_REGION")

    custom_aws_tags = cluster_settings_utils.convert_custom_tags_to_dict_list(
        cluster_settings.get_setting("global-settings.custom_tags")
    )

    combined_tags = [
        {"Key": "res:EnvironmentName", "Value": cluster_name},
        {"Key": "res:ModuleName", "Value": module_name},
        {"Key": "res:ModuleId", "Value": module_id},
        {"Key": "Name", "Value": cluster_name + "/" + module_id + " Root Volume"},
        *custom_aws_tags,
    ]

    aws_instance_id = instance_metadata_utils.get_instance_id()

    ec2_client = boto3.client('ec2', region_name=aws_region)

    try:
        response = ec2_client.describe_volumes(
            Filters=[
                {
                    'Name': 'attachment.instance-id',
                    'Values': [aws_instance_id]
                }
            ]
        )

        volumes = [volume['VolumeId'] for volume in response['Volumes']]

        logger.info(f"volumes: {json.dumps(volumes, indent=2)}")

        if not volumes:
            logger.info("No EBS volumes found for this instance")
            return

        def tag_volumes():
            for ebs_id in volumes:
                ec2_client.create_tags(
                    Resources=[ebs_id],
                    Tags=combined_tags
                )

        max_retries = 5
        retry_count = 0
        success = False

        while retry_count <= max_retries and not success:
            try:
                if retry_count > 0:
                    sleep_time = random.randint(8, 40)  # Between 8 and 40 seconds
                    logger.info(f"({retry_count}/{max_retries}) ec2 tag failed due to EC2 API error, retrying in {sleep_time} seconds ...")
                    time.sleep(sleep_time)

                tag_volumes()
                logger.info("Implemented EBS volumes tags successfully" + (" after retry" if retry_count > 0 else ""))
                success = True

            except Exception as e:
                retry_count += 1
                logger.error(f"Error tagging EBS volumes: {str(e)}")
                if retry_count > max_retries:
                    logger.error(f"Failed to tag EBS volumes after {max_retries} attempts")
    except Exception as e:
        logger.error(f"Error describing EBS volumes: {str(e)}")
