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

# Begin: DCV Session Manager Agent
set -x

while getopts o:r:n:g:s: opt
do
    case "${opt}" in
        o) BASE_OS=${OPTARG};;
        r) AWS_REGION=${OPTARG};;
        n) RES_ENVIRONMENT_NAME=${OPTARG};;
        s) SCRIPT_DIR=${OPTARG};;
    esac
done

if [[ -z "$BASE_OS" || -z "$AWS_REGION" || -z "$RES_ENVIRONMENT_NAME" || -z "$SCRIPT_DIR" ]]; then
  echo "One or more of the required parameters is not provided..."
  exit 1
fi

source "$SCRIPT_DIR/../common/bootstrap_common.sh"

function download_nice_dcv_session_manager_agent () {
  local AWS=$(command -v aws)
  local DCV_GPG_KEY_DCV_AGENT=$($AWS dynamodb get-item \
                              --region "$AWS_REGION" \
                              --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                              --key '{"key": {"S": "global-settings.package_config.dcv.gpg_key"}}' \
                              --output text \
                              | awk '/VALUE/ {print $2}')
  local machine=$(uname -m) #x86_64 or aarch64
  local DCV_SESSION_MANAGER_AGENT_X86_64_URL
  local DCV_SESSION_MANAGER_AGENT_X86_64_VERSION
  local DCV_SESSION_MANAGER_AGENT_X86_64_SHA256_HASH
  local DCV_SESSION_MANAGER_AGENT_AARCH64_URL
  local DCV_SESSION_MANAGER_AGENT_AARCH64_VERSION
  local DCV_SESSION_MANAGER_AGENT_AARCH64_SHA256_HASH
  if [[ $machine == "x86_64" ]]; then
    case $BASE_OS in
      amzn2|centos7|rhel7)
        DCV_SESSION_MANAGER_AGENT_X86_64_URL=$($AWS dynamodb get-item \
                                --region "$AWS_REGION" \
                                --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                --key '{"key": {"S": "global-settings.package_config.dcv.agent.x86_64.linux.al2_rhel_centos7.url"}}' \
                                --output text \
                                | awk '/VALUE/ {print $2}')
        DCV_SESSION_MANAGER_AGENT_X86_64_VERSION=$($AWS dynamodb get-item \
                                --region "$AWS_REGION" \
                                --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                --key '{"key": {"S": "global-settings.package_config.dcv.agent.x86_64.linux.al2_rhel_centos7.version"}}' \
                                --output text \
                                | awk '/VALUE/ {print $2}')
        DCV_SESSION_MANAGER_AGENT_X86_64_SHA256_HASH=$($AWS dynamodb get-item \
                                --region "$AWS_REGION" \
                                --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                --key '{"key": {"S": "global-settings.package_config.dcv.agent.x86_64.linux.al2_rhel_centos7.sha256sum"}}' \
                                --output text \
                                | awk '/VALUE/ {print $2}')
        ;;
      rhel8|rhel9)
        DCV_SESSION_MANAGER_AGENT_X86_64_URL=$($AWS dynamodb get-item \
                                --region "$AWS_REGION" \
                                --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                --key '{"key": {"S": "global-settings.package_config.dcv.agent.x86_64.linux.rhel_centos_rocky'${BASE_OS:4:1}'.url"}}' \
                                --output text \
                                | awk '/VALUE/ {print $2}')
        DCV_SESSION_MANAGER_AGENT_X86_64_VERSION=$($AWS dynamodb get-item \
                                --region "$AWS_REGION" \
                                --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                --key '{"key": {"S": "global-settings.package_config.dcv.agent.x86_64.linux.rhel_centos_rocky'${BASE_OS:4:1}'.version"}}' \
                                --output text \
                                | awk '/VALUE/ {print $2}')
        DCV_SESSION_MANAGER_AGENT_X86_64_SHA256_HASH=$($AWS dynamodb get-item \
                                --region "$AWS_REGION" \
                                --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                --key '{"key": {"S": "global-settings.package_config.dcv.agent.x86_64.linux.rhel_centos_rocky'${BASE_OS:4:1}'.sha256sum"}}' \
                                --output text \
                                | awk '/VALUE/ {print $2}')
        ;;
      *)
        log_warning "Base OS not supported."
        exit 1
        ;;
    esac
  else
    case $BASE_OS in
      amzn2|centos7|rhel7)
        DCV_SESSION_MANAGER_AGENT_AARCH64_URL=$($AWS dynamodb get-item \
                                --region "$AWS_REGION" \
                                --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                --key '{"key": {"S": "global-settings.package_config.dcv.agent.aarch64.linux.al2_rhel_centos7.url"}}' \
                                --output text \
                                | awk '/VALUE/ {print $2}')
        DCV_SESSION_MANAGER_AGENT_AARCH64_VERSION=$($AWS dynamodb get-item \
                                --region "$AWS_REGION" \
                                --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                --key '{"key": {"S": "global-settings.package_config.dcv.agent.aarch64.linux.al2_rhel_centos7.version"}}' \
                                --output text \
                                | awk '/VALUE/ {print $2}')
        DCV_SESSION_MANAGER_AGENT_AARCH64_SHA256_HASH=$($AWS dynamodb get-item \
                                --region "$AWS_REGION" \
                                --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                --key '{"key": {"S": "global-settings.package_config.dcv.agent.aarch64.linux.al2_rhel_centos7.sha256sum"}}' \
                                --output text \
                                | awk '/VALUE/ {print $2}')
        ;;
      rhel8|rhel9)
        DCV_SESSION_MANAGER_AGENT_AARCH64_URL=$($AWS dynamodb get-item \
                                --region "$AWS_REGION" \
                                --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                --key '{"key": {"S": "global-settings.package_config.dcv.agent.aarch64.linux.rhel_centos_rocky'${BASE_OS:4:1}'.url"}}' \
                                --output text \
                                | awk '/VALUE/ {print $2}')
        DCV_SESSION_MANAGER_AGENT_AARCH64_VERSION=$($AWS dynamodb get-item \
                                --region "$AWS_REGION" \
                                --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                --key '{"key": {"S": "global-settings.package_config.dcv.agent.aarch64.linux.rhel_centos_rocky'${BASE_OS:4:1}'.version"}}' \
                                --output text \
                                | awk '/VALUE/ {print $2}')
        DCV_SESSION_MANAGER_AGENT_AARCH64_SHA256_HASH=$($AWS dynamodb get-item \
                                --region "$AWS_REGION" \
                                --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                --key '{"key": {"S": "global-settings.package_config.dcv.agent.aarch64.linux.rhel_centos_rocky'${BASE_OS:4:1}'.sha256sum"}}' \
                                --output text \
                                | awk '/VALUE/ {print $2}')
        ;;
      *)
        log_warning "Base OS not supported."
        exit 1
        ;;
    esac
  fi

  rpm --import ${DCV_GPG_KEY_DCV_AGENT}
  machine=$(uname -m) #x86_64 or aarch64
  AGENT_URL=""
  AGENT_VERSION=""
  AGENT_SHA256_HASH=""
  if [[ $machine == "x86_64" ]]; then
    # x86_64
    AGENT_URL=${DCV_SESSION_MANAGER_AGENT_X86_64_URL}
    AGENT_VERSION=${DCV_SESSION_MANAGER_AGENT_X86_64_VERSION}
    AGENT_SHA256_HASH=${DCV_SESSION_MANAGER_AGENT_X86_64_SHA256_HASH}
  else
    # aarch64
    AGENT_URL=${DCV_SESSION_MANAGER_AGENT_AARCH64_URL}
    AGENT_VERSION=${DCV_SESSION_MANAGER_AGENT_AARCH64_VERSION}
    AGENT_SHA256_HASH=${DCV_SESSION_MANAGER_AGENT_AARCH64_SHA256_HASH}
  fi

  wget ${AGENT_URL}
  if [[ $(sha256sum nice-dcv-session-manager-agent-${AGENT_VERSION}.rpm | awk '{print $1}') != ${AGENT_SHA256_HASH} ]];  then
    echo -e "FATAL ERROR: Checksum for DCV Session Manager Agent failed. File may be compromised." > /etc/motd
    exit 1
  fi
}

function install_nice_dcv_session_manager_agent () {
  yum install -y nice-dcv-session-manager-agent-${AGENT_VERSION}.rpm
  log_info "# installing dcv agent complete ..."
  rm -rf nice-dcv-session-manager-agent-${AGENT_VERSION}.rpm
}

if [[ $BASE_OS =~ ^(amzn2|centos7|rhel7|rhel8|rhel9)$ ]]; then
  if [[ -z "$(rpm -qa nice-dcv-session-manager-agent)" ]]; then
    download_nice_dcv_session_manager_agent
    install_nice_dcv_session_manager_agent
  else
    log_info "Found nice-dcv-session-manager-agent pre-installed... skipping installation..."
  fi
else
  log_warning "Base OS not supported."
  exit 1
fi

# END: DCV Session Manager Agent
