#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from ideasdk.config.cluster_config import ClusterConfig
from ideasdk.metrics.cloudwatch.cloudwatch_agent_config import (
    CloudWatchAgentConfigOptions,
    CloudWatchAgentConfig,
    CloudWatchAgentLogsOptions,
    CloudWatchAgentLogFileOptions,
)

from ideabootstrap.common.constants import (
    LINUX_CLOUDWATCH_AGENT_CONFIG_FILE_PATH,
    WINDOWS_CLOUDWATCH_AGENT_CONFIG_FILE_PATH,
    LINUX_CLOUDWATCH_AGENT_CTL_PATH,
    WINDOWS_CLOUDWATCH_AGENT_CTL_PATH,
    LINUX_BOOTSTRAP_LOG_FILES,
    WINDOWS_BOOTSTRAP_LOG_FILES,
    LINUX_DCV_LOG_FILES,
    WINDOWS_DCV_LOG_FILES,
)
from ideabootstrap.bootstrap_common import get_base_os
from res.utils import logging_utils

import os
import subprocess
import json

logger = logging_utils.get_logger("bootstrap")


def setup(log_files=None):
    env = os.environ
    module_id = env.get("IDEA_MODULE_ID")
    base_os = get_base_os()
    cluster_name = env.get("IDEA_CLUSTER_NAME")
    module_name = env.get("IDEA_MODULE_NAME")
    aws_region = env.get("AWS_REGION")
    idea_session_id = env.get("IDEA_SESSION_ID")

    logger.info(f"Setting CloudWatch Agent configuration for OS: {base_os}")

    log_group_name = f"/{cluster_name}/{module_name}"
    if not log_files:
        if not idea_session_id:
            log_files = [
                CloudWatchAgentLogFileOptions(
                    file_path=LINUX_BOOTSTRAP_LOG_FILES,
                    log_group_name=log_group_name,
                    log_stream_name="application_{ip_address}",
                    retention_in_days=90,
                )
            ]
        else:
            bootstrap_file_path = (
                WINDOWS_BOOTSTRAP_LOG_FILES
                if base_os == "windows"
                else LINUX_BOOTSTRAP_LOG_FILES
            )
            dcv_file_path = (
                WINDOWS_DCV_LOG_FILES if base_os == "windows" else LINUX_DCV_LOG_FILES
            )

            log_files = [
                CloudWatchAgentLogFileOptions(
                    file_path=bootstrap_file_path,
                    log_group_name=log_group_name,
                    log_stream_name=f"{idea_session_id}/bootstrap/logs",
                    retention_in_days=90,
                ),
                CloudWatchAgentLogFileOptions(
                    file_path=dcv_file_path,
                    log_group_name=log_group_name,
                    log_stream_name=f"{idea_session_id}/nice/dcv/log",
                    retention_in_days=90,
                ),
            ]

    try:
        cloudwatch_agent_config = CloudWatchAgentConfig(
            cluster_config=ClusterConfig(
                aws_region=aws_region, cluster_name=cluster_name, module_id=module_id
            ),
            options=CloudWatchAgentConfigOptions(
                module_id=module_id,
                base_os=base_os,
                enable_logs=True,
                logs=CloudWatchAgentLogsOptions(
                    default_log_stream_name=module_name + "_default_{ip_address}",
                    files=log_files,
                    force_flush_interval=5,
                ),
                enable_metrics=False,
            ),
        ).build()

        cloudwatch_config_file_path = (
            WINDOWS_CLOUDWATCH_AGENT_CONFIG_FILE_PATH
            if base_os == "windows"
            else LINUX_CLOUDWATCH_AGENT_CONFIG_FILE_PATH
        )
        cloudwatch_ctl_path = (
            WINDOWS_CLOUDWATCH_AGENT_CTL_PATH
            if base_os == "windows"
            else LINUX_CLOUDWATCH_AGENT_CTL_PATH
        )
        commands = []
        if base_os == "windows":
            commands = ["powershell", "-ExecutionPolicy", "Bypass", "-File"]

        logger.info(f"Writing CloudWatch Agent into file {cloudwatch_config_file_path}")

        # Using utf-8 encoding for windows
        with open(cloudwatch_config_file_path, "w", encoding="utf-8") as f:
            json.dump(cloudwatch_agent_config, f, indent=4)

        result = subprocess.run(
            commands
            + [
                cloudwatch_ctl_path,
                "-a",
                "fetch-config",
                "-m",
                "ec2",
                "-s",
                "-c",
                f"file:{cloudwatch_config_file_path}",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            logger.info(f"CloudWatch agent enabled successfully")

    except Exception as e:
        logger.error(f"Error setting CloudWatch Agent configuration: {str(e)}")
