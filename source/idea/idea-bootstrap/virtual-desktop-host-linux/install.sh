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

CONFIGURE_FOR_RES_VDI=0
GPU_FAMILY="NONE"
while getopts r:n:v:g: opt
do
    case "${opt}" in
        r) AWS_REGION=${OPTARG};;
        n) RES_ENVIRONMENT_NAME=${OPTARG};;
        v) CONFIGURE_FOR_RES_VDI=${OPTARG};;
        g) GPU_FAMILY=${OPTARG};;
        ?) echo "Invalid option for install.sh script: -${opt}."
           exit 1;;
    esac
done

if [[ -z "$AWS_REGION" || -z "$RES_ENVIRONMENT_NAME" ]]; then
  echo "ERROR: One or more of the required parameters is not provided..."
  exit 1
fi

if [[ ! $CONFIGURE_FOR_RES_VDI =~ ^(0|1)$ ]]; then
  echo "ERROR: -v argument must be either 0 or 1 (Configure for RES VDI)."
  exit 1
fi

if [[ ! $GPU_FAMILY =~ ^(NONE|NVIDIA|AMD)$ ]]; then
  echo "ERROR: -g argument must be either NONE, NVIDIA, or AMD (GPU Instance)."
  exit 1
fi

if [[ -f /etc/os-release ]]; then
  OS_RELEASE_ID=$(grep -E '^(ID)=' /etc/os-release | awk -F'"' '{print $2}')
  OS_RELEASE_VERSION_ID=$(grep -E '^(VERSION_ID)=' /etc/os-release | awk -F'"' '{print $2}')
  BASE_OS=$(echo $OS_RELEASE_ID${OS_RELEASE_VERSION_ID%%.*})
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

if [[ ! $BASE_OS =~ ^(amzn2|centos7|rhel7|rhel8|rhel9)$ ]]; then 
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
PATH=/bin:/usr/bin:/sbin:/usr/sbin:/usr/local/bin
## [END] RES Environment VDI Installation
")

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Merge Environments
/bin/bash  "${SCRIPT_DIR}/../common/merge_environments.sh" -r "${curr_environment}" -o /etc/environment

source /etc/environment

source "${SCRIPT_DIR}/../common/bootstrap_common.sh"

echo -n "no" > ${BOOTSTRAP_DIR}/reboot_required.txt

if [[ ! -f ${BOOTSTRAP_DIR}/res_installed_all_packages.log ]]; then

  # Begin: Install AWS Systems Manager Agent
  /bin/bash "${SCRIPT_DIR}/../common/aws_ssm.sh" -o $RES_BASE_OS -r $AWS_REGION -n $RES_ENVIRONMENT_NAME -s "${SCRIPT_DIR}"
  # End: Install AWS Systems Manager Agent
  
  yum install -y deltarpm
  yum -y upgrade

  # Begin: Install EPEL Repo
  /bin/bash "${SCRIPT_DIR}/../common/epel_repo.sh" -o $RES_BASE_OS -s "${SCRIPT_DIR}"
  # End: Install EPEL Repo

  # Begin: Install System Packages
  /bin/bash "${SCRIPT_DIR}/../common/system_packages.sh" -o $RES_BASE_OS -r $AWS_REGION -n $RES_ENVIRONMENT_NAME -s "${SCRIPT_DIR}"
  # End: Install System Packages

  # Begin: Install NFS Utils and dependency items
  /bin/bash "${SCRIPT_DIR}/../common/nfs_utils.sh" -o $RES_BASE_OS -s "${SCRIPT_DIR}"
  # End: Install NFS Utils and dependency items

  # Begin: Install CloudWatch Agent
  /bin/bash "${SCRIPT_DIR}/../common/cloudwatch_agent.sh" -o $RES_BASE_OS -r $AWS_REGION -n $RES_ENVIRONMENT_NAME -s "${SCRIPT_DIR}"
  # End: Install CloudWatch Agent

  # Begin: Install jq
  /bin/bash "${SCRIPT_DIR}/../common/jq.sh" -o $RES_BASE_OS -s "${SCRIPT_DIR}"
  # End: Install jq

  # Begin: Disable SE Linux
  /bin/bash "${SCRIPT_DIR}/../common/disable_se_linux.sh" -o $RES_BASE_OS -s "${SCRIPT_DIR}"
  # End: Disable SE Linux

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

if [[ $CONFIGURE_FOR_RES_VDI == 1 ]]; then 
  REBOOT_REQUIRED=$(cat /root/bootstrap/reboot_required.txt)
  if [[ "${REBOOT_REQUIRED}" == "yes" ]]; then
    log_info "Triggering 1st Reboot Required for RES Configuration for VDI"
    crontab -l | grep -v "idea-reboot-do-not-edit-or-delete-idea-notif.sh" | crontab -
    (crontab -l; echo "@reboot /bin/bash /root/bootstrap/latest/virtual-desktop-host-linux/install_post_reboot.sh -v 1 crontab") | crontab -
    reboot
  else
    /bin/bash /root/bootstrap/latest/virtual-desktop-host-linux/install_post_reboot.sh -v 1
  fi
fi
