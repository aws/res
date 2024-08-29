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

function update_cloudwatch_agent_download_link_txt() {
  local DOWNLOAD_LINK_TXT=$1

  case $BASE_OS in
    amzn2)
      sed -i 's/%os%/amazon_linux/g' $DOWNLOAD_LINK_TXT
      sed -i 's/%ext%/rpm/g' $DOWNLOAD_LINK_TXT
      ;;
    rhel8|rhel9)
      sed -i 's/%os%/redhat/g' $DOWNLOAD_LINK_TXT
      sed -i 's/%ext%/rpm/g' $DOWNLOAD_LINK_TXT
      ;;
  esac
  local MACHINE=$(uname -m)
  case $MACHINE in
    aarch64)
      sed -i 's/%architecture%/arm64/g' $DOWNLOAD_LINK_TXT
      ;;
    x86_64)
      sed -i 's/%architecture%/amd64/g' $DOWNLOAD_LINK_TXT
      ;;
  esac
}

function install_cloudwatch_agent() {
  local CLOUDWATCH_AGENT_PACKAGE_NAME=$1

  rpm -U ./${CLOUDWATCH_AGENT_PACKAGE_NAME}
}

function pre_installed() {
  rpm -q amazon-cloudwatch-agent
  if [[ "$?" != "0"  ]]; then
    return 1
  else
    return 0
  fi
}
