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
MODULE_ID="vdi-app"

while getopts m:g:p:e:n:o:i:h:t:u:a: opt
do
    case "${opt}" in
        m) MODULE_ID=${OPTARG};;
        g) GPU_FAMILY=${OPTARG};;
        p) PREBAKING_AMI=${OPTARG};;
        e) ENVIRONMENT_NAME=${OPTARG};;
        n) PROJECT_NAME=${OPTARG};;
        o) SESSION_OWNER=${OPTARG};;
        i) SESSION_ID=${OPTARG};;
        h) HIBERNATION_ENABLED=${OPTARG};;
        t) BOOTSTRAP_TOKEN=${OPTARG};;
        u) CUSTOM_BROKER_URL=${OPTARG};;
        a) AWS_REGION=${OPTARG};;
        ?) echo "Invalid option for install.sh script: -${opt}."
           exit 1;;
    esac
done

echo $BOOTSTRAP_TOKEN > /root/bootstrap/broker_token

if [[ ! $GPU_FAMILY =~ ^(NONE|NVIDIA|AMD)$ ]]; then
  echo "ERROR: -g argument must be either NONE, NVIDIA, or AMD (GPU Instance)."
  exit 1
fi

if [[ ! $PREBAKING_AMI =~ ^(true|false)$ ]]; then
  echo "ERROR: -p argument must be either true or false."
  exit 1
fi

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

if [[ ! -f ${INSTALL_FINISHED_LOCK} ]]; then

  source "${SCRIPT_DIR}/../../common/linux/bootstrap_common.sh"

  BASE_OS=$(get_base_os)

  timestamp=$(date +%s)
  echo "Installation logged in /root/bootstrap/logs/install.log.${timestamp}"
  echo "Installing...."
  exec > /root/bootstrap/logs/install.log.${timestamp} 2>&1

  if [[ ! $BASE_OS =~ ^(amzn2|amzn2023|rhel8|rhel9|ubuntu2204|rocky9)$ ]]; then
    echo "ERROR: Base OS not supported."
    exit 1
  fi

  echo -n "no" > ${BOOTSTRAP_DIR}/reboot_required.txt

  if [[ ! -f ${BOOTSTRAP_DIR}/res_installed_all_packages.log ]]; then
    # Disable SSM agent if exists to avoid unexpected reboot during installation
    # Don't disable ssm during pre baking AMI since it uses SSM to run remote commands
    if [[ $PREBAKING_AMI == "false" ]]; then
      /bin/bash  "${SCRIPT_DIR}/../../common/linux/disable_amazon_ssm_agent.sh" -o $BASE_OS -s "${SCRIPT_DIR}/.."
    fi

    # Complete unfinished transactions
    /bin/bash  "${SCRIPT_DIR}/../../common/linux/complete_unfinished_transactions.sh" -o $BASE_OS -s "${SCRIPT_DIR}/.."

    if [[ $BASE_OS =~ ^(ubuntu2204)$ ]]; then
      apt update
    fi

    /bin/bash "${SCRIPT_DIR}/../../common/linux/install_common.sh" -s "${SCRIPT_DIR}/.." -i "false"

    # Begin: Install NFS Utils and dependency items
    /bin/bash "${SCRIPT_DIR}/../../common/linux/nfs_utils.sh" -o $BASE_OS -s "${SCRIPT_DIR}/.."
    # End: Install NFS Utils and dependency items

    # Begin : Install SSSD packages
    /bin/bash "${SCRIPT_DIR}/../../common/linux/sssd.sh" -o $BASE_OS -s "${SCRIPT_DIR}/.."
    # End: Install SSSD packages

    # Begin: Install S3 Mountpoint
    /bin/bash "${SCRIPT_DIR}/../../common/linux/s3_mountpoint.sh" -o $BASE_OS -s "${SCRIPT_DIR}/.."
    # End: Install S3 Mountpoint

    if [[ $GPU_FAMILY =~ ^(NVIDIA|AMD)$ ]]; then
        # Begin: Disable Nouveau Drivers
        /bin/bash "${SCRIPT_DIR}/../../common/linux/disable_nouveau_drivers.sh" -o $BASE_OS -g $GPU_FAMILY -s "${SCRIPT_DIR}/.."
        # End: Disable Nouveau Drivers
    else
      log_info "GPU InstanceType not detected. Skipping disabling of Nouveau Drivers..."
    fi

    # Begin: Install vdi helper requirements
    idea_pip install --user -r ${SCRIPT_DIR}/../../vdi-helper/requirements.txt
    # End: Install vdi helper requirements

    # Begin : Install Fsx Lustre client
    /bin/bash "${SCRIPT_DIR}/../../common/linux/fsx_lustre_client.sh" -o $BASE_OS -s "${SCRIPT_DIR}/.."
    # End: Install Fsx Lustre client

    # Begin : Install Host Modules
    /bin/bash "${SCRIPT_DIR}/../../common/linux/host_modules.sh" -o $BASE_OS -s "${SCRIPT_DIR}/.."
    # End: Install Host Modules

    if [[ "${PREBAKING_AMI}" == "true" ]] && [ -f ${SCRIPT_DIR}/../../../requirements.txt ]; then
      idea_pip install -r ${SCRIPT_DIR}/../../../requirements.txt
    fi

    if [[ $BASE_OS =~ ^(rhel8|rhel9|rocky9)$ ]] && [[ $HIBERNATION_ENABLED == True ]]; then
      # Begin: Install and enable hibernate agent
      /bin/bash "${SCRIPT_DIR}/../../common/linux/red_hat/hibinit_agent.sh"
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
  /bin/bash ${SCRIPT_DIR}/../../virtual-desktop-host/linux/install_post_reboot.sh -m "${MODULE_ID}" -g "${GPU_FAMILY}" -p "${PREBAKING_AMI}" -e "${ENVIRONMENT_NAME}" -n "${PROJECT_NAME}" -o "${SESSION_OWNER}" -i "${SESSION_ID}" -t "${CUSTOM_BROKER_URL}"
fi
