#!/bin/bash
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

set -x

GPU_FAMILY="NONE"

SEMAPHORE_DIR="/root/bootstrap/semaphore"
INSTALL_FINISHED_LOCK="${SEMAPHORE_DIR}/install_finished.lock"

# A flag to indicate if the script is running for prebake VDI AMI, default to true since the builder component
# recipe we published in User Guide did not include this argument.
PREBAKING_AMI="true"

while getopts r:n:g:p: opt
do
    case "${opt}" in
        r) AWS_REGION=${OPTARG};;
        n) RES_ENVIRONMENT_NAME=${OPTARG};;
        g) GPU_FAMILY=${OPTARG};;
        p) PREBAKING_AMI=${OPTARG};;
        ?) echo "Invalid option for install.sh script: -${opt}."
           exit 1;;
    esac
done

if [[ -z "$AWS_REGION" || -z "$RES_ENVIRONMENT_NAME" ]]; then
  echo "ERROR: One or more of the required parameters is not provided..."
  exit 1
fi

if [[ ! $GPU_FAMILY =~ ^(NONE|NVIDIA|AMD)$ ]]; then
  echo "ERROR: -g argument must be either NONE, NVIDIA, or AMD (GPU Instance)."
  exit 1
fi

if [[ ! $PREBAKING_AMI =~ ^(true|false)$ ]]; then
  echo "ERROR: -p argument must be either true or false."
  exit 1
fi

if [[ ! -f ${INSTALL_FINISHED_LOCK} ]]; then

  if [[ -f /etc/os-release ]]; then
    OS_RELEASE_ID=$(grep -E '^(ID)=' /etc/os-release | awk -F'"' '{print $2}')
    OS_RELEASE_VERSION_ID=$(grep -E '^(VERSION_ID)=' /etc/os-release | awk -F'"' '{print $2}')
    BASE_OS=$(echo $OS_RELEASE_ID${OS_RELEASE_VERSION_ID%%.*})
    if [[ -z "${OS_RELEASE_ID}" ]]; then
      # Base OS is Ubuntu
      OS_RELEASE_ID=$(grep -E '^(ID)=' /etc/os-release | awk -F'=' '{print $2}')
      BASE_OS=$(echo $OS_RELEASE_ID$OS_RELEASE_VERSION_ID | sed -e 's/\.//g')
    fi
  elif [[ -f /usr/lib/os-release ]]; then
    OS_RELEASE_ID=$(grep -E '^(ID)=' /usr/lib/os-release | awk -F'"' '{print $2}')
    OS_RELEASE_VERSION_ID=$(grep -E '^(VERSION_ID)=' /usr/lib/os-release | awk -F'"' '{print $2}')
    BASE_OS=$(echo $OS_RELEASE_ID${OS_RELEASE_VERSION_ID%%.*})
  else
    echo "Base OS information on Linux instance cannot be found."
    exit 1
  fi

  timestamp=$(date +%s)
  echo "Installation logged in /root/bootstrap/logs/install.log.${timestamp}"
  echo "Installing...."
  exec > /root/bootstrap/logs/install.log.${timestamp} 2>&1

  if [[ ! $BASE_OS =~ ^(amzn2|rhel8|rhel9|ubuntu2204)$ ]]; then
    echo "ERROR: Base OS not supported."
    exit 1
  fi

  curr_environment=$(echo -e "
  ## [BEGIN] RES Environment VDI Installation - Do Not Delete
  AWS_DEFAULT_REGION=$AWS_REGION
  AWS_REGION=$AWS_REGION
  RES_BASE_OS=$BASE_OS
  GPU_FAMILY=$GPU_FAMILY
  IDEA_CLUSTER_NAME=$RES_ENVIRONMENT_NAME
  BOOTSTRAP_DIR=/root/bootstrap
  PATH=/bin:/usr/bin:/sbin:/usr/sbin:/usr/local/bin:/opt/idea/python/latest/bin
  ## [END] RES Environment VDI Installation
  ")

  SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

  # Merge Environments
  /bin/bash  "${SCRIPT_DIR}/../common/merge_environments.sh" -r "${curr_environment}" -o /etc/environment

  source /etc/environment

  source "${SCRIPT_DIR}/../common/bootstrap_common.sh"

  echo -n "no" > ${BOOTSTRAP_DIR}/reboot_required.txt

  if [[ ! -f ${BOOTSTRAP_DIR}/res_installed_all_packages.log ]]; then
    # Disable SSM agent if exists to avoid unexpected reboot during installation
    # Don't disable ssm during pre baking AMI since it uses SSM to run remote commands
    if [[ $PREBAKING_AMI == "false" ]]; then
      /bin/bash  "${SCRIPT_DIR}/../common/disable_amazon_ssm_agent.sh" -o $BASE_OS -s "${SCRIPT_DIR}"
    fi

    # Complete unfinished transactions
    /bin/bash  "${SCRIPT_DIR}/../common/complete_unfinished_transactions.sh" -o $RES_BASE_OS -s "${SCRIPT_DIR}"

    if [[ $BASE_OS =~ ^(ubuntu2204)$ ]]; then
      apt update
    else
      yum install -y deltarpm

      # Begin: Install EPEL Repo
      /bin/bash "${SCRIPT_DIR}/../common/epel_repo.sh" -o $RES_BASE_OS -s "${SCRIPT_DIR}"
      # End: Install EPEL Repo
    fi

    # Begin: Install jq
    /bin/bash "${SCRIPT_DIR}/../common/jq.sh" -o $RES_BASE_OS -s "${SCRIPT_DIR}"
    # End: Install jq

    # Begin: Install System Packages
    /bin/bash "${SCRIPT_DIR}/../common/system_packages.sh" -o $RES_BASE_OS -r $AWS_REGION -n $RES_ENVIRONMENT_NAME -s "${SCRIPT_DIR}"
    # End: Install System Packages

    # Begin: Install NFS Utils and dependency items
    /bin/bash "${SCRIPT_DIR}/../common/nfs_utils.sh" -o $RES_BASE_OS -s "${SCRIPT_DIR}"
    # End: Install NFS Utils and dependency items

    # Begin: Install CloudWatch Agent
    /bin/bash "${SCRIPT_DIR}/../common/cloudwatch_agent.sh" -o $RES_BASE_OS -r $AWS_REGION -n $RES_ENVIRONMENT_NAME -s "${SCRIPT_DIR}"
    # End: Install CloudWatch Agent

    # Begin: Disable SE Linux
    /bin/bash "${SCRIPT_DIR}/../common/disable_se_linux.sh" -o $RES_BASE_OS -s "${SCRIPT_DIR}"
    # End: Disable SE Linux

    # Begin: Install S3 Mountpoint
    /bin/bash "${SCRIPT_DIR}/../common/s3_mountpoint.sh" -o $RES_BASE_OS -r $AWS_REGION -n $RES_ENVIRONMENT_NAME -s "${SCRIPT_DIR}"
    # End: Install S3 Mountpoint

    # Begin: Install Python
    /bin/bash "${SCRIPT_DIR}/../common/python.sh" -o $RES_BASE_OS -r $AWS_REGION -n $RES_ENVIRONMENT_NAME  -s "${SCRIPT_DIR}" -a "res" -i "/opt/idea/python"
    # End: Install Python

    # Begin: Install Custom Credential Broker requirements
    res_pip install --user -r ${SCRIPT_DIR}/custom-credential-broker/requirements.txt
    # End: Install Custom Credential Broker

    if [[ $GPU_FAMILY =~ ^(NVIDIA|AMD)$ ]]; then
        # Begin: Disable Nouveau Drivers
        /bin/bash "${SCRIPT_DIR}/../nice-dcv-linux/disable_nouveau_drivers.sh" -o $RES_BASE_OS -g $GPU_FAMILY -s "${SCRIPT_DIR}"
        # End: Disable Nouveau Drivers
    else
      log_info "GPU InstanceType not detected. Skipping disabling of Nouveau Drivers..."
    fi

    set_reboot_required "RES software dependencies and packages have been installed, reboot required for changes to take effect..."
  else
     log_info "Found ${BOOTSTRAP_DIR}/res_installed_all_packages.log... skipping package installation..."
  fi

  mkdir -p ${SEMAPHORE_DIR}
  echo $(date +%s) > ${INSTALL_FINISHED_LOCK}

  REBOOT_REQUIRED=$(cat /root/bootstrap/reboot_required.txt)

  # Only reboot when reboot required and not baking on EC2 Image Builder
  # Reboots initiated by the scirpt will make the Image Builder fail
  if [[ "${REBOOT_REQUIRED}" == "yes" && "${PREBAKING_AMI}" == "false" ]]; then
    log_info "Triggering 1st Reboot Required for RES Configuration for VDI"
    echo -n "no" > /root/bootstrap/reboot_required.txt

    reboot

    # Exit to avoid running the rest of script before reboot is completed.
    exit 0
  fi
fi

# Only chain to the next script when we are NOT baking on EC2 Image Builder
# On EC2 Image Builder, the next script will be triggered by the Image Builder itself
if [[ "${PREBAKING_AMI}" == "false" ]]; then
  /bin/bash /root/bootstrap/latest/virtual-desktop-host-linux/install_post_reboot.sh -p $PREBAKING_AMI
fi
