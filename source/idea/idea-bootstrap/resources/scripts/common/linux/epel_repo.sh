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

# Begin: Install EPEL Repo
set -x

while getopts o:s: opt
do
  case "${opt}" in
    o) BASE_OS=${OPTARG};;
    s) SCRIPT_DIR=${OPTARG};;
    ?) echo "Invalid option for epel_repo.sh script: -${opt}."
      exit 1;;
  esac
done

if [[ -z "$BASE_OS" || -z "$SCRIPT_DIR" ]]; then
  echo "One or more of the required parameters is not provided..."
  exit 1
fi

source "${SCRIPT_DIR}/../common/linux/bootstrap_common.sh"
source "${SCRIPT_DIR}/../common/linux/config_common.sh"

if [[ ! -f "/etc/yum.repos.d/epel.repo" ]]; then
  case $BASE_OS in
    amzn2|amzn2023)
      rpm -q epel-release
      if [[ "$?" != "0"  ]]; then
        amazon-linux-extras install -y epel
        yum update --security -y
      fi
      ;;
    rhel8|rhel9|rocky9)
      REPO_LINK=($(get_string "package_config.epel_repo.${BASE_OS}"))
      yum -y install "${REPO_LINK}"
      ;;
    *)
      log_warning "Base OS not supported."
      ;;
  esac
fi
# End: Install EPEL Repo
