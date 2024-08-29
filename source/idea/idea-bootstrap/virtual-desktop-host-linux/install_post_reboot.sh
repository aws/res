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

SEMAPHORE_DIR="/root/bootstrap/semaphore"
INSTALL_POST_REBOOT_FINISHED_LOCK="${SEMAPHORE_DIR}/install_post_reboot_finished.lock"

PREBAKING_AMI="true"

while getopts p: opt
do
    case "${opt}" in
        p) PREBAKING_AMI=${OPTARG};;
        ?) echo "Invalid option for install_post_reboot.sh script: -${opt}."
           exit 1;;
    esac
done

if [[ $INSTALL_SCRIPT_EXEC == 0 ]]; then
  echo "ERROR: install.sh must be executed first."
  exit 1
fi

if [[ ! $PREBAKING_AMI =~ ^(true|false)$ ]]; then
  echo "ERROR: -p argument must be either true or false."
  exit 1
fi

if [[ ! -f ${INSTALL_POST_REBOOT_FINISHED_LOCK} ]]; then

  timestamp=$(date +%s)
  echo "Post Reboot Installation logged in /root/bootstrap/logs/install_post_reboot.log.${timestamp}"
  echo "Installing...."
  exec > /root/bootstrap/logs/install_post_reboot.log.${timestamp} 2>&1

  source /etc/environment
  if [[ -f /etc/profile.d/proxy.sh ]]; then
      source /etc/profile.d/proxy.sh
  fi

  echo -n "no" > ${BOOTSTRAP_DIR}/reboot_required.txt

  SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
  source "${SCRIPT_DIR}/../common/bootstrap_common.sh"

  if [[ ! -f ${BOOTSTRAP_DIR}/res_installed_all_packages.log ]]; then
    # Begin: Install Nice DCV Server
    /bin/bash "${SCRIPT_DIR}/../nice-dcv-linux/dcv_server.sh" -o $RES_BASE_OS -r $AWS_REGION -n $IDEA_CLUSTER_NAME -g $GPU_FAMILY -s "${SCRIPT_DIR}"
    # End: Install Nice DCV Server

    # Begin: Install Nice DCV Session Manager Agent
    /bin/bash "${SCRIPT_DIR}/../nice-dcv-linux/dcv_session_manager_agent.sh" -o $RES_BASE_OS -r $AWS_REGION -n $IDEA_CLUSTER_NAME -s "${SCRIPT_DIR}"
    # End: Install Nice DCV Session Manager Agent

    # Begin: Install AWS Systems Manager Agent
    # Install SSM agent at the end to avoid unexpected reboot for security patching
    /bin/bash "${SCRIPT_DIR}/../common/aws_ssm.sh" -o $RES_BASE_OS -r $AWS_REGION -n $IDEA_CLUSTER_NAME -s "${SCRIPT_DIR}"
    # End: Install AWS Systems Manager Agent

    echo "$(date)" >> /root/bootstrap/res_installed_all_packages.log
    set_reboot_required "DCV and any associated GPU drivers have been installed, reboot required for changes to take effect..."
  else
     log_info "Found ${BOOTSTRAP_DIR}/res_installed_all_packages.log... skipping package installation..."
  fi

  mkdir -p ${SEMAPHORE_DIR}
  echo $(date +%s) > ${INSTALL_POST_REBOOT_FINISHED_LOCK}

  REBOOT_REQUIRED=$(cat /root/bootstrap/reboot_required.txt)
  if [[ "${REBOOT_REQUIRED}" == "yes" && "${PREBAKING_AMI}" == "false" ]]; then
    log_info "Triggering 2nd Reboot Required for RES Configuration for VDI"
    echo -n "no" > /root/bootstrap/reboot_required.txt

    reboot

    # Exit to avoid running the rest of script before reboot is completed.
    exit 0
  fi
fi

# Prebake running on EC2 Image Builder does not need to run the configure.sh script
if [[ "${PREBAKING_AMI}" == "false" ]]; then
  /bin/bash /root/bootstrap/latest/virtual-desktop-host-linux/configure.sh
fi
