#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import subprocess
from res.utils import logging_utils
from ideabootstrap import bootstrap_common

logger = logging_utils.get_logger("bootstrap")

def _configure_ssm_agent_red_hat():
    try:
        status_result = subprocess.run(["systemctl", "status", "amazon-ssm-agent"], capture_output=True, text=True)

        if status_result.returncode == 0:
            logger.info(f"Amazon-ssm-agent is already running in region.")
            return

        logger.info(f"Enabling amazon-ssm-agent in region")
        enable_result = subprocess.run(["systemctl", "enable", "amazon-ssm-agent"], capture_output=True, text=True, check=False)

        if enable_result.returncode != 0:
            logger.error(f"Error enabling amazon-ssm-agent: {enable_result.stderr}")

        # Restart the agent regardless of enable result
        restart_result = subprocess.run(["systemctl", "restart", "amazon-ssm-agent"], capture_output=True, text=True, check=False)

        if restart_result.returncode != 0:
            logger.error(f"Error restarting amazon-ssm-agent: {restart_result.stderr}")
            return

        logger.info(f"Successfully configured amazon-ssm-agent")

    except Exception as e:
        logger.error(f"Failed to configure amazon-ssm-agent: {str(e)}")


def _configure_ssm_agent_ubuntu():
    try:
        snap_process = subprocess.run(["snap", "services", "amazon-ssm-agent"], capture_output=True, text=True, check=False)
        grep_process = subprocess.run(["grep", "inactive"], input=snap_process.stdout, text=True, capture_output=True)

        if grep_process.returncode == 0:
            logger.info(f"Amazon-ssm-agent is inactive, enabling it now.")
            result = subprocess.run(["snap", "start", "--enable", "amazon-ssm-agent"], capture_output=True, text=True, check=False)

            if result.returncode != 0:
                logger.error(f"Failed to enable amazon-ssm-agent: {result.stderr}")
                return

            logger.info(f"Amazon-ssm-agent has been enabled successfully.")
        else:
            logger.info(f"Amazon-ssm-agent is already enabled.")
    except Exception as e:
        logger.error(f"Exception configuring amazon-ssm-agent: {str(e)}")

def configure():
    env = dict(os.environ)
    base_os = bootstrap_common.get_base_os()
    aws_region = env.get('AWS_REGION')
    module_name = env.get('IDEA_MODULE_NAME')
    cluster_name = env.get('IDEA_CLUSTER_NAME')
    module_id = env.get('IDEA_MODULE_ID')

    logger.info(f"Configuring SSM agent for module: {module_name} in cluster: {cluster_name}, region: {aws_region}, os: {base_os}")

    if base_os in ("amzn2", "amzn2023", "rhel8", "rhel9", "rocky9"):
        _configure_ssm_agent_red_hat()
    elif base_os in ("ubuntu2204", "ubuntu2404"):
        _configure_ssm_agent_ubuntu()
    else:
        logger.warning(f"Base OS: {base_os} is not supported for SSM agent configuration.")
