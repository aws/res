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

PLATFORM_SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

source "$PLATFORM_SCRIPT_DIR/../../common/bootstrap_common.sh"

function pre_installed() {
  if [[ -z "$(apt -qq list nice-dcv-session-manager-agent)" ]]; then
    return 1
  else
    return 0
  fi
}

function install_nice_dcv_session_manager_agent () {
  local BASE_OS=$1
  local AWS_REGION=$2
  local RES_ENVIRONMENT_NAME=$3

  local AWS=$(command -v aws)
  local DCV_GPG_KEY_DCV_AGENT=$($AWS dynamodb get-item \
                              --region "$AWS_REGION" \
                              --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                              --key '{"key": {"S": "global-settings.package_config.dcv.gpg_key"}}' \
                              --output text \
                              | awk '/VALUE/ {print $2}')
  local machine=$(uname -m) #x86_64 or aarch64
  local AGENT_URL=$($AWS dynamodb get-item \
                          --region "$AWS_REGION" \
                          --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                          --key '{"key": {"S": "global-settings.package_config.dcv.agent.'$machine'.ubuntu.'$BASE_OS'.url"}}' \
                          --output text \
                          | awk '/VALUE/ {print $2}')
  local AGENT_SHA256_URL=$($AWS dynamodb get-item \
                          --region "$AWS_REGION" \
                          --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                          --key '{"key": {"S": "global-settings.package_config.dcv.agent.'$machine'.ubuntu.'$BASE_OS'.sha256sum"}}' \
                          --output text \
                          | awk '/VALUE/ {print $2}')

  wget ${DCV_GPG_KEY_DCV_AGENT}
  gpg --import NICE-GPG-KEY

  wget ${AGENT_URL}
  fileName=$(basename ${AGENT_URL})
  urlSha256Sum=$(wget -O - ${AGENT_SHA256_URL})
  if [[ $(sha256sum ${fileName} | awk '{print $1}') != ${urlSha256Sum} ]];  then
    echo -e "FATAL ERROR: Checksum for DCV Session Manager Agent failed. File may be compromised." > /etc/motd
    exit 1
  fi

  DEBIAN_FRONTEND=noninteractive apt install -y ./${fileName}
  log_info "# installing dcv agent complete ..."
  rm -rf ./${fileName}
}
