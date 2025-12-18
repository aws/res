#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import random
import time
import boto3
from res.utils import logging_utils, cluster_settings_utils
from res.utils import instance_metadata_utils
from res.resources import cluster_settings

logger = logging_utils.get_logger("bootstrap")

def setup():
    logger.info("Setting Network Interface Tags")
    env = os.environ
    cluster_name = env.get("IDEA_CLUSTER_NAME")
    module_name = env.get("IDEA_MODULE_NAME")
    module_id = env.get("IDEA_MODULE_ID")
    aws_region = env.get("AWS_REGION")

    custom_aws_tags = cluster_settings_utils.convert_custom_tags_to_dict_list(
        cluster_settings.get_setting("global-settings.custom_tags")
    )

    combined_tags = [
        {'Key': 'res:EnvironmentName', 'Value': cluster_name},
        {'Key': 'res:ModuleName', 'Value': module_name},
        {'Key': 'res:ModuleId', 'Value': module_id},
        {'Key': 'Name', 'Value': cluster_name + '/' + module_id + '  Network Interface'},
        *custom_aws_tags,
    ]

    aws_instance_id = instance_metadata_utils.get_instance_id()
    ec2_client = boto3.client('ec2', region_name=aws_region)

    try:
        response = ec2_client.describe_network_interfaces(
            Filters=[
                {
                    'Name': 'attachment.instance-id',
                    'Values': [aws_instance_id]
                }
            ]
        )

        interfaces = [interface['NetworkInterfaceId'] for interface in response['NetworkInterfaces']]
        logger.info(f"interfaces: {interfaces}")

        if not interfaces:
            logger.info("No network interfaces found for this instance")
            return

        def tag_interfaces():
            for eni_id in interfaces:
                ec2_client.create_tags(
                    Resources=[eni_id],
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

                tag_interfaces()
                logger.info("Implemented network interface tags successfully" + (" after retry" if retry_count > 0 else ""))
                success = True

            except Exception as e:
                retry_count += 1
                logger.error(f"Error tagging network interfaces: {str(e)}")
                if retry_count > max_retries:
                    logger.error(f"Failed to tag network interfaces after {max_retries} attempts")
    except Exception as e:
        logger.error(f"Error describing network interfaces: {str(e)}")
