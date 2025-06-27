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

INSTALL_SSM_AGENT="true"

while getopts s:i: opt
do
  case "${opt}" in
    s) SCRIPT_DIR=${OPTARG};;
    i) INSTALL_SSM_AGENT=${OPTARG};;
    ?) echo "Invalid option for install_common.sh script: -${opt}."
      exit 1;;
  esac
done

if [[ -z "$SCRIPT_DIR" ]]; then
  echo "One or more of the required parameters is not provided..."
  exit 1
fi

if [[ ! $INSTALL_SSM_AGENT =~ ^(true|false)$ ]]; then
  echo "ERROR: -i argument must be either true or false."
  exit 1
fi

source "${SCRIPT_DIR}/../common/linux/bootstrap_common.sh"
source "${SCRIPT_DIR}/../common/linux/config_common.sh"

BASE_OS=$(get_base_os)

# Begin: Install yq
/bin/bash "${SCRIPT_DIR}/../common/linux/yq.sh" -s "${SCRIPT_DIR}"
# Begin: Install yq

if [[ "${INSTALL_SSM_AGENT}" == "true" ]]; then
  # Begin: Install AWS Systems Manager Agent
  /bin/bash "${SCRIPT_DIR}/../common/linux/aws_ssm.sh" -o $BASE_OS -s "${SCRIPT_DIR}"
  # End: Install AWS Systems Manager Agent
fi

# Begin: Install EPEL Repo
/bin/bash "${SCRIPT_DIR}/../common/linux/epel_repo.sh" -o $BASE_OS -s "${SCRIPT_DIR}"
# End: Install EPEL Repo

# Begin: Install jq
/bin/bash "${SCRIPT_DIR}/../common/linux/jq.sh" -o $BASE_OS -s "${SCRIPT_DIR}"
# End: Install jq

# Begin: Install System Packages
/bin/bash "${SCRIPT_DIR}/../common/linux/system_packages.sh" -o $BASE_OS -s "${SCRIPT_DIR}"
# End: Install System Packages

# Begin: Install CloudWatch Agent
/bin/bash "${SCRIPT_DIR}/../common/linux/cloudwatch_agent.sh" -o $BASE_OS -s "${SCRIPT_DIR}"
# End: Install CloudWatch Agent

# Begin: Install Python
/bin/bash "${SCRIPT_DIR}/../common/linux/python.sh" -o $BASE_OS -s "${SCRIPT_DIR}"
# End: Install Python
