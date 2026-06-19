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
INSTALL_FINISHED_LOCK="${SEMAPHORE_DIR}/install_finished.lock"

# A flag to indicate if the script is running for pre-baking RES ready AMI, default to true since the builder component
# recipe we published in User Guide did not include this argument.
PREBAKING_AMI="true"
# If no component is specified, install dependencies of all the infra hosts
COMPONENT="ALL"
# If no environment name is specified when pre-baking RES ready AMI
ENVIRONMENT_NAME=""
STAGING_BUCKET=""

while getopts p:c:m:e:b: opt
do
  case "${opt}" in
    p) PREBAKING_AMI=${OPTARG};;
    c) COMPONENT=${OPTARG};;
    m) MODULE_ID=${OPTARG};;
    e) ENVIRONMENT_NAME=${OPTARG};;
    b) STAGING_BUCKET=${OPTARG};;
    ?) echo "Invalid option for install.sh script: -${opt}."
      exit 1;;
  esac
done

if [[ ! $PREBAKING_AMI =~ ^(true|false)$ ]]; then
  echo "ERROR: -p argument must be either true or false."
  exit 1
fi

if [[ "${PREBAKING_AMI}" == "false"  ]] && [[ -z "$COMPONENT" || -z "$MODULE_ID" || -z "$ENVIRONMENT_NAME" ]]; then
  echo "ERROR: component, module id and environment name arguments must be provided unless pre-baking RES ready AMI."
  exit 1
fi

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

if [[ ! -f ${INSTALL_FINISHED_LOCK} ]]; then
  source "${SCRIPT_DIR}/../common/linux/bootstrap_common.sh"

  timestamp=$(date +%s)
  echo "Installation logged in /root/bootstrap/logs/install.log.${timestamp}"
  echo "Installing...."
  exec > /root/bootstrap/logs/install.log.${timestamp} 2>&1

  echo -n "no" > ${BOOTSTRAP_DIR}/reboot_required.txt
  /bin/bash "${SCRIPT_DIR}/../common/linux/install_common.sh" -s "${SCRIPT_DIR}"
  source /etc/environment

  if [ "${COMPONENT}" = "ALL" ]; then
    INFRA_HOST_SCRIPTS_ROOT="${SCRIPT_DIR}"
    find ${INFRA_HOST_SCRIPTS_ROOT} -type d -print0 | while IFS= read -r -d $'\0' dir; do
      if [ "${dir}" != "${INFRA_HOST_SCRIPTS_ROOT}" ] && [ -f ${dir}/install.sh ]; then
        /bin/bash "${dir}/install.sh" -s "${SCRIPT_DIR}" -e "${ENVIRONMENT_NAME}" -b "${STAGING_BUCKET}"
      fi
    done
  elif [ -f ${SCRIPT_DIR}/${COMPONENT}/install.sh ]; then
    /bin/bash "${SCRIPT_DIR}/${COMPONENT}/install.sh" -s "${SCRIPT_DIR}" -e "${ENVIRONMENT_NAME}" -b "${STAGING_BUCKET}"
  fi

  if [[ "${PREBAKING_AMI}" == "true" ]] && [ -f ${SCRIPT_DIR}/../../requirements.txt ]; then
    idea_pip install -r ${SCRIPT_DIR}/../../requirements.txt
  fi
  idea_pip install --upgrade setuptools

  mkdir -p ${SEMAPHORE_DIR}
  echo $(date +%s) > ${INSTALL_FINISHED_LOCK}

  REBOOT_REQUIRED=$(cat /root/bootstrap/reboot_required.txt)
  if [[ "${REBOOT_REQUIRED}" == "yes"  && "${PREBAKING_AMI}" == "false" ]]; then
    log_info "Triggering 1st Reboot Required for the host bootstrap"
    echo -n "no" > /root/bootstrap/reboot_required.txt

    reboot
    # Exit to avoid running the rest of script before reboot is completed.
    exit 0
  fi
fi

# Only chain to the next script when we are NOT baking on EC2 Image Builder
if [[ "${PREBAKING_AMI}" == "false" ]]; then
  /bin/bash "${SCRIPT_DIR}/../common/linux/install_app.sh" -s "${SCRIPT_DIR}" -c "${COMPONENT}" -m "${MODULE_ID}" -e "${ENVIRONMENT_NAME}"
fi
