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
  if [[ -z "$(rpm -qa nice-dcv-session-manager-agent)" ]]; then
    return 1
  else
    return 0
  fi
}

function install_nice_dcv_session_manager_agent () {
  local AWS=$(command -v aws)
  local DCV_GPG_KEY_DCV_AGENT=$($AWS dynamodb get-item \
                              --region "$AWS_REGION" \
                              --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                              --key '{"key": {"S": "global-settings.package_config.dcv.gpg_key"}}' \
                              --output text \
                              | awk '/VALUE/ {print $2}')
  local machine=$(uname -m) #x86_64 or aarch64
  local AGENT_URL=""
  local AGENT_VERSION=""
  local AGENT_SHA256_URL=""
  case $BASE_OS in
    amzn2)
      AGENT_URL=$($AWS dynamodb get-item \
                        --region "$AWS_REGION" \
                        --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                        --key '{"key": {"S": "global-settings.package_config.dcv.agent.'$machine'.linux.al2.url"}}' \
                        --output text \
                        | awk '/VALUE/ {print $2}')
      AGENT_SHA256_URL=$($AWS dynamodb get-item \
                        --region "$AWS_REGION" \
                        --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                        --key '{"key": {"S": "global-settings.package_config.dcv.agent.'$machine'.linux.al2.sha256sum"}}' \
                        --output text \
                        | awk '/VALUE/ {print $2}')
      ;;
    rhel8|rhel9)
      AGENT_URL=$($AWS dynamodb get-item \
                        --region "$AWS_REGION" \
                        --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                        --key '{"key": {"S": "global-settings.package_config.dcv.agent.'$machine'.linux.rhel_centos_rocky'${BASE_OS:4:1}'.url"}}' \
                        --output text \
                        | awk '/VALUE/ {print $2}')
      AGENT_SHA256_URL=$($AWS dynamodb get-item \
                        --region "$AWS_REGION" \
                        --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                        --key '{"key": {"S": "global-settings.package_config.dcv.agent.'$machine'.linux.rhel_centos_rocky'${BASE_OS:4:1}'.sha256sum"}}' \
                        --output text \
                        | awk '/VALUE/ {print $2}')
      ;;
    *)
      log_warning "Base OS not supported."
      exit 1
      ;;
  esac

  rpm --import ${DCV_GPG_KEY_DCV_AGENT}

  wget ${AGENT_URL}
  fileName=$(basename ${AGENT_URL})
  urlSha256Sum=$(wget -O - ${AGENT_SHA256_URL})
  if [[ $(sha256sum ${fileName} | awk '{print $1}') != ${urlSha256Sum} ]];  then
    echo -e "FATAL ERROR: Checksum for DCV Session Manager Agent failed. File may be compromised." > /etc/motd
    exit 1
  fi

  yum install -y ./${fileName}
  log_info "# installing dcv agent complete ..."
  rm -rf ./${fileName}
}
