#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os

BOOTSTRAP_DIR="/root/bootstrap"
SEMAPHORE_DIR="/root/bootstrap/semaphore"
WINDOWS_BOOTSTRAP_DIR = os.path.join(f'{os.environ.get("SystemDrive", "C:")}\\', "Users", "Administrator", "RES", "Bootstrap")

INSTANCE_READY_LOCK=f"{SEMAPHORE_DIR}/instance_ready.lock"
CONFIG_FINISHED_LOCK=f"{SEMAPHORE_DIR}/configure_finished.lock"

WINDOWS_VDI_CONFIG_FINISHED_LOCK="C:\\IDEA\\Semaphore\\vdi_configure_finished.lock"
WINDOWS_VDI_CONFIG_HOST_READY_LOCK="C:\\IDEA\\Semaphore\\vdi_configure_host_ready.lock"
LINUX_VDI_CONFIG_HOST_READY_LOCK="/root/bootstrap/semaphore/linux_vdi_config_host_ready.lock"
LINUX_VDI_CONFIG_FINISHED_LOCK="/root/bootstrap/semaphore/linux_vdi_config.lock"

REBOOT_REQUIRED_FILE_PATH="/root/bootstrap/reboot_required.txt"

LINUX_BOOTSTRAP_LOG_FILES = "/opt/idea/app/logs/**.log"
LINUX_DCV_LOG_FILES = "/var/log/dcv/**.log"
WINDOWS_BOOTSTRAP_LOG_FILES = r"C:\Program Files\RES\app\logs\**.log"
WINDOWS_DCV_LOG_FILES = r"C:\ProgramData\nice\dcv\log\**.log"


LINUX_CLOUDWATCH_AGENT_CONFIG_FILE_PATH="/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json"
LINUX_CLOUDWATCH_AGENT_CTL_PATH="/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl"
WINDOWS_CLOUDWATCH_AGENT_CONFIG_FILE_PATH="C:\\Program Files\\Amazon\\AmazonCloudWatchAgent\\amazon-cloudwatch-agent.json"
WINDOWS_CLOUDWATCH_AGENT_CTL_PATH="C:\\Program Files\\Amazon\\AmazonCloudWatchAgent\\amazon-cloudwatch-agent-ctl.ps1"

