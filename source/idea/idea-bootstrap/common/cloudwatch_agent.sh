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

# Begin: Install CloudWatch Agent
set -x

while getopts o:r:n:s: opt
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

SUB_DIR=""
if [[ $BASE_OS =~ ^(amzn2|rhel8|rhel9)$ ]]; then
  SUB_DIR="red_hat"
elif [[ $BASE_OS =~ ^(ubuntu2204)$ ]]; then
  SUB_DIR="debian"
else
  log_warning "Base OS not supported."
  exit 1
fi
source "${SCRIPT_DIR}/../common/$SUB_DIR/cloudwatch_agent.sh"

CLOUDWATCH_AGENT_BOOTSTRAP_DIR="/root/bootstrap/amazon-cloudwatch-agent"
mkdir -p ${CLOUDWATCH_AGENT_BOOTSTRAP_DIR}
function get_cloudwatch_agent_download_link() {
  local AWS=$(command -v aws)
  local DOWNLOAD_LINK=$($AWS dynamodb get-item \
                                --region "$AWS_REGION" \
                                --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                --key '{"key": {"S": "global-settings.package_config.amazon_cloudwatch_agent.download_link"}}' \
                                --output text \
                                | awk '/VALUE/ {print $2}')
  if [[ "${DOWNLOAD_LINK}" != "True" ]]; then
    echo -n "${DOWNLOAD_LINK}"
    return 0
  fi
  local DOWNLOAD_LINK_PATTERN=$($AWS dynamodb get-item \
                                --region "$AWS_REGION" \
                                --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                --key '{"key": {"S": "global-settings.package_config.amazon_cloudwatch_agent.download_link_pattern"}}' \
                                --output text \
                                | awk '/VALUE/ {print $2}')
  local DOWNLOAD_LINK_TXT=${CLOUDWATCH_AGENT_BOOTSTRAP_DIR}/cloudwatch_download_link.txt
  echo -n ${DOWNLOAD_LINK_PATTERN} > $DOWNLOAD_LINK_TXT
  sed -i "s/%region%/${AWS_REGION}/g" $DOWNLOAD_LINK_TXT
  update_cloudwatch_agent_download_link_txt $DOWNLOAD_LINK_TXT
  cat $DOWNLOAD_LINK_TXT
}

if ! pre_installed; then
  CLOUDWATCH_AGENT_DOWNLOAD_LINK="$(get_cloudwatch_agent_download_link)"
  CLOUDWATCH_AGENT_PACKAGE_NAME="$(basename ${CLOUDWATCH_AGENT_DOWNLOAD_LINK})"
  pushd ${CLOUDWATCH_AGENT_BOOTSTRAP_DIR}
  wget "${CLOUDWATCH_AGENT_DOWNLOAD_LINK}"
  install_cloudwatch_agent ${CLOUDWATCH_AGENT_PACKAGE_NAME}
  popd
fi
# End: Install CloudWatch Agent
