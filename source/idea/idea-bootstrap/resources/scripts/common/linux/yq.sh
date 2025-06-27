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

# Begin: Install yq
set -x

while getopts s: opt
do
  case "${opt}" in
    s) SCRIPT_DIR=${OPTARG};;
    ?) echo "Invalid option for yq.sh script: -${opt}."
      exit 1;;
  esac
done

if [[ -z "$SCRIPT_DIR" ]]; then
  echo "One or more of the required parameters is not provided..."
  exit 1
fi

source "${SCRIPT_DIR}/../common/linux/bootstrap_common.sh"

function get_yq_download_link() {
  local DOWNLOAD_LINK=""
  local MACHINE=$(uname -m)
  case $MACHINE in
    aarch64)
      DOWNLOAD_LINK="https://github.com/mikefarah/yq/releases/latest/download/yq_linux_arm64"
      ;;
    x86_64)
      DOWNLOAD_LINK="https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64"
      ;;
  esac
  echo $DOWNLOAD_LINK
}

function pre_installed() {
  which yq > /dev/null 2>&1
  if [[ "$?" != "0" ]]; then
    return 1
  else
    return 0
  fi
}

if ! pre_installed; then
  log_info "installing jq"

  YQ_DOWNLOAD_LINK="$(get_yq_download_link)"
  curl -L "${YQ_DOWNLOAD_LINK}" -o /usr/bin/yq &&\
  chmod +x /usr/bin/yq
fi
# End: Install yq
