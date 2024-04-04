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
  echo -n ${DOWNLOAD_LINK_PATTERN} > ${CLOUDWATCH_AGENT_BOOTSTRAP_DIR}/cloudwatch_download_link.txt
  sed -i "s/%region%/${AWS_REGION}/g" ${CLOUDWATCH_AGENT_BOOTSTRAP_DIR}/cloudwatch_download_link.txt
  case $BASE_OS in
    amzn2)
      sed -i 's/%os%/amazon_linux/g' ${CLOUDWATCH_AGENT_BOOTSTRAP_DIR}/cloudwatch_download_link.txt
      sed -i 's/%ext%/rpm/g' ${CLOUDWATCH_AGENT_BOOTSTRAP_DIR}/cloudwatch_download_link.txt
      ;;
    rhel7|rhel8|rhel9)
      sed -i 's/%os%/redhat/g' ${CLOUDWATCH_AGENT_BOOTSTRAP_DIR}/cloudwatch_download_link.txt
      sed -i 's/%ext%/rpm/g' ${CLOUDWATCH_AGENT_BOOTSTRAP_DIR}/cloudwatch_download_link.txt
      ;;
    centos7)
      sed -i 's/%os%/centos/g' ${CLOUDWATCH_AGENT_BOOTSTRAP_DIR}/cloudwatch_download_link.txt
      sed -i 's/%ext%/rpm/g' ${CLOUDWATCH_AGENT_BOOTSTRAP_DIR}/cloudwatch_download_link.txt
      ;;
  esac
  local MACHINE=$(uname -m)
  case $MACHINE in
    aarch64)
      sed -i 's/%architecture%/arm64/g' ${CLOUDWATCH_AGENT_BOOTSTRAP_DIR}/cloudwatch_download_link.txt
      ;;
    x86_64)
      sed -i 's/%architecture%/amd64/g' ${CLOUDWATCH_AGENT_BOOTSTRAP_DIR}/cloudwatch_download_link.txt
      ;;
  esac
  cat ${CLOUDWATCH_AGENT_BOOTSTRAP_DIR}/cloudwatch_download_link.txt
}

rpm -q amazon-cloudwatch-agent
if [[ "$?" != "0"  ]]; then
  CLOUDWATCH_AGENT_DOWNLOAD_LINK="$(get_cloudwatch_agent_download_link)"
  CLOUDWATCH_AGENT_PACKAGE_NAME="$(basename ${CLOUDWATCH_AGENT_DOWNLOAD_LINK})"
  pushd ${CLOUDWATCH_AGENT_BOOTSTRAP_DIR}
  wget "${CLOUDWATCH_AGENT_DOWNLOAD_LINK}"
  rpm -U ./${CLOUDWATCH_AGENT_PACKAGE_NAME}
  popd
fi
# End: Install CloudWatch Agent
